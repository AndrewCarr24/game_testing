import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

// The first-person view model: the player's right hand (and a sleeve) gripping the armed weapon,
// posed in camera space, animated by the weapon's keyframes (viewer/weapons.js) plus idle sway,
// walk bob and look lag.
//
//   const vm = new ViewModel(camera)
//   vm.setWeapon(def, node)    node = the picked-up model (its <Asset>_Grip / _Tip / _Edge empties
//                              give the grip frame), or null for none
//   vm.play(clip)              clip = { duration, keys: [[t, {p:[x,y,z], r:[x,y,z]°}], ...] }
//   vm.freeze(seconds)         hit stop: the animation holds still
//   vm.update(dt, { speed, grounded, lookDelta })
//   vm.light(room)             light it like the room the eye is in (baked SH + env), or outdoors
//
// Everything is one group under the camera (2 draw calls for the hand + sleeve, the weapon's own
// materials). It never clips into walls: its depth is squeezed into the nearest slice of the
// depth range (vertex shader), so the world is always behind it, while its own parts still sort
// against each other. It casts and takes no shadows; it's lit by the current room's baked
// spherical harmonics (no real-time direct light inside sunless rooms).

const D = THREE.MathUtils.degToRad;
const smooth = (t) => t * t * (3 - 2 * t);

// ------------------------------------------------------------------ lighting (shared uniforms)
const U = {
  vmSH: { value: Array.from({ length: 9 }, () => new THREE.Vector3()) },
  vmUseSH: { value: 0 },
  vmDirect: { value: 1 },
};
const _shTarget = Array.from({ length: 9 }, () => new THREE.Vector3());

export function viewModelMaterial(src) {
  const m = src.clone();
  m.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, U);
    // squeeze the depth: NDC z in [-1, 1] -> [-1, -0.6] (nearer than anything in the world)
    shader.vertexShader = shader.vertexShader.replace('#include <project_vertex>',
      '#include <project_vertex>\ngl_Position.z = gl_Position.z * 0.2 - gl_Position.w * 0.8;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <lights_pars_begin>', '#include <lights_pars_begin>\nuniform vec3 vmSH[ 9 ];\nuniform float vmUseSH, vmDirect;')
      .replace('#include <lights_fragment_maps>', [
        '#include <lights_fragment_maps>',
        'if ( vmUseSH > 0.5 ) {',
        '  iblIrradiance = vec3( 0.0 );',
        '  irradiance += shGetIrradianceAt( inverseTransformDirection( geometryNormal, viewMatrix ), vmSH );',
        '}',
      ].join('\n'))
      .replace('#include <lights_fragment_end>', '#include <lights_fragment_end>\nreflectedLight.directDiffuse *= vmDirect;\nreflectedLight.directSpecular *= vmDirect;');
  };
  m.customProgramCacheKey = () => 'viewmodel';
  return m;
}

// ------------------------------------------------------------------ the hand
// Built in the grip frame G: the handle's axis along +Y (toward the blade), the back of the hand
// facing +X, the wrist toward +Z. Four fingers wrap the handle (radius `grip`), the thumb closes
// over the index and middle fingers, the forearm leaves the wrist bent toward the little finger.
function capsule(a, b, r0, r1 = r0) {
  const len = a.distanceTo(b);
  const g = new THREE.CylinderGeometry(r1, r0, len, 12, 1, true);
  const capA = new THREE.SphereGeometry(r0, 12, 7);
  const capB = new THREE.SphereGeometry(r1, 12, 7);
  capA.translate(0, -len / 2, 0); capB.translate(0, len / 2, 0);
  const m = mergeGeometries([g, capA, capB]);
  const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), b.clone().sub(a).normalize());
  m.applyQuaternion(q);
  m.translate((a.x + b.x) / 2, (a.y + b.y) / 2, (a.z + b.z) / 2);
  // its distance field (for the occlusion between parts, buildHand)
  const ab = b.clone().sub(a), l2 = ab.lengthSq(), t = new THREE.Vector3();
  m.userData.sdf = (p) => {
    const h = THREE.MathUtils.clamp(t.copy(p).sub(a).dot(ab) / l2, 0, 1);
    return t.copy(a).addScaledVector(ab, h).distanceTo(p) - (r0 + (r1 - r0) * h);
  };
  return m;
}
function ellipsoid(c, s, rot = null, seg = 16) {
  const g = new THREE.SphereGeometry(1, seg, Math.round(seg * 0.7));
  g.scale(s[0], s[1], s[2]);
  // (scaling a sphere's normals by the scale is wrong for an ellipsoid: n ~ p / s^2)
  const p = g.attributes.position, n = g.attributes.normal;
  for (let i = 0; i < p.count; i++) {
    const v = new THREE.Vector3(p.getX(i) / (s[0] * s[0]), p.getY(i) / (s[1] * s[1]), p.getZ(i) / (s[2] * s[2])).normalize();
    n.setXYZ(i, v.x, v.y, v.z);
  }
  if (rot) g.applyQuaternion(rot);
  g.translate(c.x, c.y, c.z);
  const inv = rot ? rot.clone().invert() : null, t = new THREE.Vector3(), m = Math.min(...s);
  g.userData.sdf = (p) => {
    t.copy(p).sub(c); if (inv) t.applyQuaternion(inv);
    return (Math.hypot(t.x / s[0], t.y / s[1], t.z / s[2]) - 1) * m;
  };
  return g;
}
const V = (x, y, z) => new THREE.Vector3(x, y, z);

export function buildHand({ grip = 0.0115, skin = 0xc29b88, sleeve = 0x23262b, arm: armDir = null } = {}) {
  const parts = [];
  const R = grip + 0.0105;             // the fingers' centre line round the handle
  // fingers: height on the handle, size; joints on a loop round the handle (in the X/Z plane):
  // knuckle at the back-right, then front, left, and the tip back toward the palm
  const fingers = [
    { y: 0.026, k: 1.0, spread: 0.0 },      // index
    { y: 0.007, k: 1.04, spread: 0.0 },     // middle
    { y: -0.012, k: 0.97, spread: 0.0 },    // ring
    { y: -0.029, k: 0.82, spread: 0.0 },    // little
  ];
  for (const f of fingers) {
    const k = f.k, r = 0.0088 * Math.min(1, 0.4 + 0.6 * k);
    const loop = (deg, rad = R) => V(Math.cos(D(deg)) * rad, f.y, -Math.sin(D(deg)) * rad);
    const mcp = V(0.031 * (0.85 + 0.15 * k), f.y + 0.002, -0.006);
    const pip = loop(95 - 8 * (1 - k), R + 0.002);
    const dip = loop(185);
    const tip = loop(250 - 25 * (1 - k), R - 0.001);
    parts.push(capsule(mcp, pip, r * 1.05, r));
    parts.push(capsule(pip, dip, r, r * 0.92));
    parts.push(capsule(dip, tip, r * 0.92, r * 0.82));
    parts[parts.length - 1].userData.tint = [1.04, 0.95, 0.94];
    parts.push(ellipsoid(mcp.clone().add(V(0.004, 0, 0.002)), [0.0105 * k, 0.0098 * k, 0.0105], null, 12));   // the knuckle
    parts[parts.length - 1].userData.tint = [1.05, 0.96, 0.95];
  }
  // palm (the back of the hand faces +X) and the heel of the hand
  parts.push(ellipsoid(V(0.027, -0.002, 0.022), [0.016, 0.046, 0.038]));
  parts.push(ellipsoid(V(0.02, -0.024, 0.034), [0.018, 0.026, 0.03]));      // hypothenar
  // thumb: its base (thenar mass) beside the handle, then over the top of the fingers
  parts.push(ellipsoid(V(0.004, 0.02, 0.03), [0.019, 0.022, 0.026], new THREE.Quaternion().setFromEuler(new THREE.Euler(0.4, 0, 0.3))));
  const t0 = V(0.008, 0.03, 0.022), t1 = V(-0.012, 0.042, 0.0), t2 = V(-0.026, 0.036, -0.016), t3 = V(-0.026, 0.026, -0.032);
  parts.push(capsule(t0, t1, 0.0115, 0.0105), capsule(t1, t2, 0.0105, 0.0095), capsule(t2, t3, 0.0095, 0.0082));
  // wrist and forearm: from the heel of the hand toward the elbow (`armDir`, in G; default: bent
  // ~35 deg toward the little finger)
  const arm = (armDir ? armDir.clone() : V(0.08, -0.55, 0.83)).normalize();
  const wrist = V(0.024, -0.03, 0.036).addScaledVector(arm, 0.022);
  const elbow = wrist.clone().addScaledVector(arm, 0.34);
  parts.push(ellipsoid(wrist, [0.024, 0.03, 0.026]));
  const fore = capsule(wrist, elbow, 0.026, 0.036);
  parts.push(fore);
  // occlusion in the vertex colours: each vertex darkens near the other parts' surfaces (the
  // creases between fingers, where they press on the handle and the palm) and inside the fist
  const handleSdf = (p) => Math.hypot(p.x, p.z) - grip;
  const cols = [];
  const v = new THREE.Vector3();
  parts.forEach((g, i) => {
    g.deleteAttribute('uv');
    const pos = g.attributes.position, col = new Float32Array(pos.count * 3);
    const tint = g.userData.tint || [1, 1, 1];
    for (let k = 0; k < pos.count; k++) {
      v.fromBufferAttribute(pos, k);
      let occ = 0;
      for (let j = 0; j < parts.length; j++) {
        if (j === i || !parts[j].userData.sdf) continue;
        const d = parts[j].userData.sdf(v);
        if (d < 0.009) occ += 0.55 * (1 - Math.max(0, d) / 0.009) ** 2;
      }
      if (Math.abs(v.y) < 0.05) { const d = handleSdf(v); if (d < 0.008) occ += 0.6 * (1 - Math.max(0, d) / 0.008) ** 2; }
      const ao = 1 - Math.min(0.62, occ);
      col[k * 3] = ao * tint[0]; col[k * 3 + 1] = ao * tint[1]; col[k * 3 + 2] = ao * tint[2];
    }
    g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  });
  const skinGeo = mergeGeometries(parts);
  const skinMat = viewModelMaterial(new THREE.MeshStandardMaterial({ color: skin, roughness: 0.52, metalness: 0, vertexColors: true }));
  const hand = new THREE.Mesh(skinGeo, skinMat);
  hand.name = 'ViewModel_Hand';
  // sleeve: a cuff from 8 cm past the wrist up the forearm
  const s0 = wrist.clone().addScaledVector(arm, 0.03), s1 = wrist.clone().addScaledVector(arm, 0.4);
  const sl = new THREE.CylinderGeometry(0.039, 0.045, s0.distanceTo(s1), 18, 3, false);
  // a soft rolled hem: the bottom ring flares out a touch
  const sp = sl.attributes.position;
  for (let i = 0; i < sp.count; i++) if (sp.getY(i) < -s0.distanceTo(s1) / 2 + 1e-4) { sp.setX(i, sp.getX(i) * 0.93); sp.setZ(i, sp.getZ(i) * 0.93); }
  sl.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(V(0, 1, 0), arm));
  sl.translate((s0.x + s1.x) / 2, (s0.y + s1.y) / 2, (s0.z + s1.z) / 2);
  sl.computeVertexNormals();
  const sleeveMesh = new THREE.Mesh(sl, viewModelMaterial(new THREE.MeshStandardMaterial({ color: sleeve, roughness: 0.92 })));
  sleeveMesh.name = 'ViewModel_Sleeve';
  const g = new THREE.Group();
  g.name = 'ViewModel_Arm';
  g.add(hand, sleeveMesh);
  return g;
}

// ------------------------------------------------------------------ pose helpers
const _q = new THREE.Quaternion(), _e = new THREE.Euler();
function lerpPose(keys, t, out) {
  // keys: [[t, {p, r}], ...] sorted; smoothstep between neighbours
  let a = keys[0], b = keys[keys.length - 1];
  for (let i = 0; i < keys.length - 1; i++) if (t >= keys[i][0] && t <= keys[i + 1][0]) { a = keys[i]; b = keys[i + 1]; break; }
  if (t <= keys[0][0]) b = a = keys[0];
  if (t >= keys[keys.length - 1][0]) a = b = keys[keys.length - 1];
  const span = b[0] - a[0], k = span > 0 ? (b[3] === 'linear' ? (t - a[0]) / span : smooth((t - a[0]) / span)) : 0;
  const pa = a[1].p || [0, 0, 0], pb = b[1].p || [0, 0, 0], ra = a[1].r || [0, 0, 0], rb = b[1].r || [0, 0, 0];
  for (let i = 0; i < 3; i++) { out.p[i] = pa[i] + (pb[i] - pa[i]) * k; out.r[i] = ra[i] + (rb[i] - ra[i]) * k; }
  return out;
}

export class ViewModel {
  constructor(camera) {
    this.camera = camera;
    this.root = new THREE.Group();          // the whole view model, under the camera
    this.root.name = 'ViewModel';
    this.root.visible = false;
    this.pivot = new THREE.Group();         // animated: the hold pose + clip + sway
    this.root.add(this.pivot);
    camera.add(this.root);
    this.def = null;
    this.clip = null; this.clipT = 0;
    this.frozen = 0;
    this.equip = 1;                          // 0 = lowered out of view, 1 = up
    this.t = 0;
    this.bob = 0;
    this.lag = new THREE.Vector2();
    this.room = undefined;
    this._pose = { p: [0, 0, 0], r: [0, 0, 0] };
    this.kick = 0;
  }

  setWeapon(def, node) {
    this.pivot.clear();
    this.def = def;
    this.root.visible = !!def;
    if (!def) return;
    const hold = def.hold || {};
    const grip = new THREE.Group();          // the grip frame G (see buildHand)
    grip.name = 'ViewModel_Grip';
    // G in camera space: the hold position, the weapon pointing along hold.aim, the back of the
    // hand toward hold.back, the forearm toward hold.arm (all camera space)
    const aim = V(...(hold.aim || [-0.16, 0.3, -1])).normalize();
    const back = V(...(hold.back || [1, 0.35, 0.3]));
    back.addScaledVector(aim, -back.dot(aim)).normalize();
    const z = new THREE.Vector3().crossVectors(back, aim);
    grip.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(back, aim, z));
    const armG = V(...(hold.arm || [0.42, -0.62, 0.66])).normalize().applyQuaternion(grip.quaternion.clone().invert());
    grip.add(buildHand({ grip: hold.gripRadius ?? 0.0115, skin: hold.skin, sleeve: hold.sleeve, arm: armG }));
    if (node) grip.add(fitWeapon(node, def));
    this.basePos = V(...(hold.pos || [0.2, -0.2, -0.36]));
    this.baseQuat = grip.quaternion.clone();
    this.grip = grip;
    this.pivot.add(grip);
    this.equip = 0;                          // raise it into view
    this.clip = null;
    this.root.traverse((o) => { if (o.isMesh) { o.castShadow = false; o.receiveShadow = false; o.frustumCulled = false; o.renderOrder = 10; } });
  }

  play(clip) { this.clip = clip; this.clipT = 0; this.frozen = 0; }
  freeze(s) { this.frozen = Math.max(this.frozen, s); }
  get busy() { return !!this.clip; }

  // light it like the room the eye is in: that room's SH (smoothly), its panorama; outdoors the
  // scene's environment and the sun
  light(baked, room, roomInfo) {
    const r = room && baked?.rooms?.[room];
    U.vmUseSH.value = r?.sh ? 1 : 0;
    U.vmDirect.value = roomInfo && roomInfo.sun === false ? 0 : 1;
    if (r?.sh) for (let i = 0; i < 9; i++) _shTarget[i].copy(r.sh[i]);
    if (room !== this.room) {
      // a new room: snap the first time, then glide over ~0.3 s (update())
      if (this.room === undefined && r?.sh) for (let i = 0; i < 9; i++) U.vmSH.value[i].copy(_shTarget[i]);
      this.room = room;
      const env = r?.envMap ?? null;
      this.root.traverse((o) => { if (o.isMesh && o.material && o.material.envMap !== env) { o.material.envMap = env; o.material.needsUpdate = true; } });
    }
  }

  update(dt, { speed = 0, grounded = true, lookDelta = null } = {}) {
    if (!this.def) return;
    this.t += dt;
    for (let i = 0; i < 9; i++) U.vmSH.value[i].lerp(_shTarget[i], Math.min(1, dt * 6));
    this.equip = Math.min(1, this.equip + dt / 0.28);
    // the clip, unless held by a hit stop
    let pose = this._pose;
    pose.p.fill(0); pose.r.fill(0);
    if (this.clip) {
      if (this.frozen > 0) this.frozen -= dt;
      else this.clipT += dt;
      if (this.clipT >= this.clip.duration) this.clip = null;
      else lerpPose(this.clip.keys, this.clipT, pose);
    }
    // idle sway (breathing), walk bob, look lag (the hand trails the view a little)
    const w = window.__bench ? 0 : 1;
    const bobAmp = Math.min(1, speed / 3.4) * (grounded ? 1 : 0.2);
    this.bob += dt * (4.2 + speed * 0.9) * (bobAmp > 0.05 ? 1 : 0);
    const sway = [Math.sin(this.t * 1.1) * 0.0025 * w, Math.sin(this.t * 1.7) * 0.002 * w, 0];
    const bob = [Math.cos(this.bob) * 0.011 * bobAmp * w, -Math.abs(Math.sin(this.bob)) * 0.012 * bobAmp * w, 0];
    if (lookDelta) this.lag.lerp(lookDelta.clone().clampScalar(-0.06, 0.06), Math.min(1, dt * 10));
    this.lag.multiplyScalar(Math.max(0, 1 - dt * 8));
    const lower = 1 - smooth(this.equip);                    // equipping: comes up from below
    this.pivot.position.set(
      this.basePos.x + pose.p[0] + sway[0] + bob[0] - this.lag.x * 0.25,
      this.basePos.y + pose.p[1] + sway[1] + bob[1] - lower * 0.25 + this.lag.y * 0.25,
      this.basePos.z + pose.p[2]);
    _e.set(D(pose.r[0]) - lower * 0.9 + this.lag.y * 0.6, D(pose.r[1]) + this.lag.x * 0.6, D(pose.r[2]) + Math.sin(this.t * 0.9) * 0.006 * w, 'XYZ');
    this.pivot.quaternion.setFromEuler(_e);
    // the grip frame turns about its own origin (the handle), the pivot moves it in camera space
    this.grip.position.set(0, 0, 0);
    this.grip.quaternion.copy(this.baseQuat);
  }
}

// the picked-up model in the grip frame: its <Asset>_Grip empty at the origin, grip -> tip along
// +Y, the edge toward -Z (the side the fingers wrap)
function fitWeapon(node, def) {
  const model = node.clone(true);
  model.visible = true;
  model.position.set(0, 0, 0); model.rotation.set(0, 0, 0); model.scale.set(1, 1, 1);
  model.updateMatrixWorld(true);
  const find = (suffix) => { let f = null; model.traverse((o) => { if (!f && o.name.endsWith(suffix)) f = o; }); return f; };
  const g = find('_Grip'), t = find('_Tip'), e = find('_Edge');
  const holder = new THREE.Group();
  holder.add(model);
  if (g && t) {
    const gp = g.getWorldPosition(new THREE.Vector3()), tp = t.getWorldPosition(new THREE.Vector3());
    const ep = e ? e.getWorldPosition(new THREE.Vector3()) : gp.clone().add(V(0, -1, 0));
    const y = tp.clone().sub(gp).normalize();
    const edge = ep.clone().sub(gp); edge.addScaledVector(y, -edge.dot(y)).normalize();
    const zAxis = edge.clone().negate();                  // edge -> -Z
    const x = new THREE.Vector3().crossVectors(y, zAxis).normalize();
    // rotation that takes the model's (x, y, zAxis) frame onto G's axes
    const m = new THREE.Matrix4().makeBasis(x, y, zAxis).invert();
    model.quaternion.setFromRotationMatrix(m);
    model.position.copy(gp).applyQuaternion(model.quaternion).negate();
    if (def.hold?.slide) model.position.addScaledVector(V(0, 1, 0), def.hold.slide);
  }
  return mergeByMaterial(holder);
}

// one mesh per material (a knife's blade, bolster, handle, rivets: 8 meshes -> 3 draw calls)
function mergeByMaterial(root) {
  root.updateMatrixWorld(true);
  const byMat = new Map();
  root.traverse((o) => {
    if (!o.isMesh || !o.visible) return;
    const geo = o.geometry.index ? o.geometry.toNonIndexed() : o.geometry.clone();
    geo.applyMatrix4(o.matrixWorld);
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    const groups = o.geometry.groups.length ? o.geometry.groups : [{ start: 0, count: o.geometry.index ? o.geometry.index.count : geo.attributes.position.count, materialIndex: 0 }];
    for (const gr of groups) {
      const m = mats[gr.materialIndex ?? 0];
      const part = new THREE.BufferGeometry();
      for (const [name, attr] of Object.entries(geo.attributes)) {
        part.setAttribute(name, new THREE.BufferAttribute(attr.array.slice(gr.start * attr.itemSize, (gr.start + gr.count) * attr.itemSize), attr.itemSize, attr.normalized));
      }
      if (!byMat.has(m)) byMat.set(m, []);
      byMat.get(m).push(part);
    }
  });
  const out = new THREE.Group();
  for (const [m, list] of byMat) {
    const keep = Object.keys(list[0].attributes).filter((n) => list.every((g) => g.attributes[n]));
    for (const g of list) for (const n of Object.keys(g.attributes)) if (!keep.includes(n)) g.deleteAttribute(n);
    const mesh = new THREE.Mesh(mergeGeometries(list), viewModelMaterial(m));
    mesh.castShadow = mesh.receiveShadow = false;
    out.add(mesh);
  }
  return out;
}
