import * as THREE from 'three';

// Crowd path for the invader (design/invaders/character.md "Crowds"): many invaders drawn as a few
// InstancedMeshes, skinned on the GPU from a bone animation texture (assets/models/invader_anim.*,
// written by blender/assets/invader_crowd.py). One draw call per (outfit, LOD) body batch and per
// weapon / head-attachment kind, no AnimationMixer, no per-invader bone updates on the CPU.
//
// three.js 0.160 has no skinned instancing (InstancedMesh ignores skinning; BatchedMesh has none),
// so this is a small onBeforeCompile on the asset's own MeshStandardMaterial: the vertex's skinning
// matrix is fetched from the texture (4 joints x 2 frames, lerped) before three's instancing.
//
//   const crowd = await InvaderCrowd.load(asset, '../assets/models/invader_anim.json', { lod: 1, max: 64 });
//   scene.add(crowd.mesh);
//   const id = crowd.add({ position, rotationY, outfit: 'Navy', clip: 'Walk', weapon: 'Rifle', head: 'cap' });
//   crowd.set(id, { clip: 'Run', time: 0 });  crowd.update(dt);

const LOD_NAMES = ['Invader_Body_LOD0', 'Invader_Body_LOD1', 'Invader_Body_LOD2'];

function skinChunk(rigid) {
  // aAnim: x = first row of the clip, y = frame count, z = loop (1) / clamp (0), w = time offset (s)
  return `
    uniform sampler2D batTex;
    uniform float batTime;
    uniform float batFps;
    attribute vec4 aAnim;
    attribute float aSpeed;
    ${rigid ? '' : 'attribute vec4 skinIndex; attribute vec4 skinWeight;'}
    mat4 batJoint(float row, float j) {
      int x = int(j) * 3; int y = int(row);
      vec4 r0 = texelFetch(batTex, ivec2(x, y), 0);
      vec4 r1 = texelFetch(batTex, ivec2(x + 1, y), 0);
      vec4 r2 = texelFetch(batTex, ivec2(x + 2, y), 0);
      return mat4(r0.x, r1.x, r2.x, 0.0,  r0.y, r1.y, r2.y, 0.0,  r0.z, r1.z, r2.z, 0.0,  r0.w, r1.w, r2.w, 1.0);
    }
    mat4 batSkin() {
      float f = max(batTime - aAnim.w, 0.0) * aSpeed * batFps;
      float n = aAnim.y;
      float f0, f1, k;
      if (aAnim.z > 0.5) { f = mod(f, n); f0 = floor(f); f1 = mod(f0 + 1.0, n); k = f - f0; }
      else { f = min(f, n - 1.0); f0 = floor(f); f1 = min(f0 + 1.0, n - 1.0); k = f - f0; }
      float r0 = aAnim.x + f0, r1 = aAnim.x + f1;
      ${rigid
        ? 'float j = float(BAT_RIGID); return batJoint(r0, j) * (1.0 - k) + batJoint(r1, j) * k;'
        : `mat4 m = mat4(0.0);
      for (int i = 0; i < 4; i++) {
        float j = skinIndex[i], w = skinWeight[i];
        if (w > 0.0) m += (batJoint(r0, j) * (1.0 - k) + batJoint(r1, j) * k) * w;
      }
      return m;`}
    }`;
}

function patch(material, tex, uniforms, rigidJoint = null) {
  const m = material.clone();
  m.onBeforeCompile = (shader) => {
    shader.uniforms.batTex = { value: tex };
    shader.uniforms.batTime = uniforms.time;
    shader.uniforms.batFps = uniforms.fps;
    const rigid = rigidJoint !== null;
    shader.vertexShader = (rigid ? `#define BAT_RIGID ${rigidJoint}\n` : '') + shader.vertexShader
      .replace('#include <common>', '#include <common>\n' + skinChunk(rigid))
      .replace('#include <beginnormal_vertex>', '#include <beginnormal_vertex>\nmat4 batM = batSkin();\nobjectNormal = mat3(batM) * objectNormal;\n#ifdef USE_TANGENT\nobjectTangent = mat3(batM) * objectTangent;\n#endif')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\ntransformed = (batM * vec4(transformed, 1.0)).xyz;');
  };
  m.customProgramCacheKey = () => `invader-bat-${rigidJoint}`;
  return m;
}

export class InvaderCrowd {
  static async load(asset, url, opts = {}) {
    const meta = await (await fetch(url)).json();
    const buf = await (await fetch(url.replace(/\.json$/, '.bin'))).arrayBuffer();
    return new InvaderCrowd(asset, meta, new Uint16Array(buf), opts);
  }

  constructor(asset, meta, halfs, { lod = 1, max = 64 } = {}) {
    this.asset = asset;
    this.meta = meta;
    this.max = max;
    const tex = new THREE.DataTexture(halfs, meta.width, meta.height, THREE.RGBAFormat, THREE.HalfFloatType);
    tex.minFilter = tex.magFilter = THREE.NearestFilter;
    tex.needsUpdate = true;
    this.tex = tex;
    this.uniforms = { time: { value: 0 }, fps: { value: meta.fps } };
    this.mesh = new THREE.Group();
    this.mesh.name = 'InvaderCrowd';
    this.items = [];
    this.batches = new Map();       // key -> { mesh, ids: [] }
    // source geometries: body LOD, weapons, attachments
    const src = {};
    asset.gltf.scene.traverse((o) => { if (o.isMesh) src[o.name] = o; });
    this.src = src;
    this.lodName = LOD_NAMES[lod];
    this.order = meta.joints;
    this.socketRow = meta.joints.length + meta.extra.indexOf('Socket_Hand_R');

  }

  // a geometry in the model frame with skinIndex remapped to the texture's joints
  _bodyGeometry(name) {
    const o = this.src[name];
    const g = o.geometry.clone();
    if (g.attributes.skinIndex && o.skeleton) {
      // this mesh's skin joint order -> the texture's joint order
      const remap = o.skeleton.bones.map((b) => Math.max(0, this.order.indexOf(b.name)));
      const si = g.attributes.skinIndex;
      for (let i = 0; i < si.count * 4; i++) si.array[i] = remap[si.array[i]] ?? 0;
      si.needsUpdate = true;
    }
    return g;
  }

  _batch(key, make) {
    if (this.batches.has(key)) return this.batches.get(key);
    const { geometry, material } = make();
    geometry.setAttribute('aAnim', new THREE.InstancedBufferAttribute(new Float32Array(this.max * 4), 4));
    geometry.setAttribute('aSpeed', new THREE.InstancedBufferAttribute(new Float32Array(this.max).fill(1), 1));
    const mesh = new THREE.InstancedMesh(geometry, material, this.max);
    mesh.count = 0;
    mesh.frustumCulled = false;
    mesh.name = `InvaderCrowd_${key}`;
    this.mesh.add(mesh);
    const b = { mesh, ids: [] };
    this.batches.set(key, b);
    return b;
  }

  _bodyBatch(outfit) {
    return this._batch(`body_${outfit}`, () => ({
      geometry: this._bodyGeometry(this.lodName),
      material: patch(this.asset.outfitMaterial(outfit) || this.src[this.lodName].material, this.tex, this.uniforms),
    }));
  }

  _partBatch(name) {
    const o = this.src[name];
    if (!o) return null;
    if (o.isSkinnedMesh) {          // head attachments: skinned (rigid on Head / Neck / Chest)
      return this._batch(name, () => ({ geometry: this._bodyGeometry(name), material: patch(o.material, this.tex, this.uniforms) }));
    }
    // weapons: rigid on the right-hand socket row; geometry in the weapon's own frame
    return this._batch(name, () => ({ geometry: o.geometry.clone(), material: patch(o.material, this.tex, this.uniforms, this.socketRow) }));
  }

  // opts: position (Vector3), rotationY, outfit, clip, time (s offset), speed, weapon, head ('cap', 'mask+hood', ...)
  add(opts = {}) {
    const id = this.items.length;
    const it = { id, slots: [], ...opts };
    this.items.push(it);
    this._place(it);
    return id;
  }

  _place(it) {
    const outfit = it.outfit || this.asset.defaultOutfit();
    const parts = [this._bodyBatch(outfit)];
    if (it.weapon) parts.push(this._partBatch(`Invader_${it.weapon}`));
    for (const h of String(it.head || '').split('+').filter((x) => x && x !== 'none')) {
      parts.push(this._partBatch(`Invader_${h[0].toUpperCase()}${h.slice(1)}`));
    }
    it.slots = parts.filter(Boolean).map((b) => {
      const k = b.mesh.count++;
      b.ids.push(it.id);
      return { b, k };
    });
    this.set(it.id, it);
  }

  set(id, opts = {}) {
    const it = Object.assign(this.items[id], opts);
    const clip = this.meta.clips[it.clip || 'Idle'];
    const m = new THREE.Matrix4().compose(it.position || new THREE.Vector3(),
      new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), it.rotationY || 0), new THREE.Vector3(1, 1, 1));
    if (opts.clip !== undefined && opts.time === undefined) it.time = this.uniforms.time.value;   // start the new clip now
    for (const { b, k } of it.slots) {
      b.mesh.setMatrixAt(k, m);
      b.mesh.instanceMatrix.needsUpdate = true;
      const a = b.mesh.geometry.attributes.aAnim;
      a.setXYZW(k, clip.start, clip.frames, clip.loop ? 1 : 0, it.time || 0);
      a.needsUpdate = true;
      const s = b.mesh.geometry.attributes.aSpeed;
      s.setX(k, it.speed ?? 1);
      s.needsUpdate = true;
    }
  }

  // demo: n invaders on a grid, a mix of clips, outfits, weapons and headgear
  spawnGrid(n, spacing = 1.6) {
    const clips = ['Idle', 'IdleAlert', 'Walk', 'Search', 'HoldRifle', 'AimRifle', 'Run', 'CrouchWalk', 'HoldPistol', 'Drag'];
    const outfits = (this.asset.meta.outfits || []).map((o) => o.name);
    const heads = ['none', 'cap', 'mask', 'hood', 'mask+hood', 'none'];
    const side = Math.ceil(Math.sqrt(n));
    let seed = 7;
    const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    for (let i = 0; i < n; i++) {
      const clip = clips[i % clips.length];
      const weapon = /Rifle/.test(clip) ? 'Rifle' : /Pistol/.test(clip) ? 'Pistol' : rnd() < 0.3 ? 'Bat' : null;
      this.add({
        position: new THREE.Vector3((i % side - (side - 1) / 2) * spacing, 0, (Math.floor(i / side) - (side - 1) / 2) * spacing),
        rotationY: (rnd() - 0.5) * 1.2, outfit: outfits[i % outfits.length], clip, time: -rnd() * 3,
        speed: 0.9 + rnd() * 0.2, weapon, head: heads[i % heads.length],
      });
    }
  }

  update(dt) { this.uniforms.time.value += dt; }
}
