import * as THREE from 'three';

// The Grimble (specs.md "grimble"): a 7.3 m cloaked creature that walks in from far out on the
// west garden's axis, up to the great room's glass, then over and over: knocks three times,
// waves, stands staring at the player (head and eyes follow them) for a while.
//
// Outdoors nothing is baked for a moving thing, so it's lit by the real-time sun plus the sky
// as its environment (the rooms' probes would light it like the entry hall). It casts no
// real-time shadow (the shadow map only redraws when rooms toggle); a soft blob decal sits
// under its feet instead, since the lawn is drawn unlit.
//
// Animations come from the asset (Walk, Knock, Wave, Idle); without them it glides (the
// static model), which is enough to test the route.

const DEFAULTS = {
  delay: 8,            // s after the level is in
  stride: 4.2,         // m per Walk cycle (grimble_rig.py: feet planted, no sliding at 1.5 m/s)
  cycle: 2.8,          // s per Walk cycle
  reach: 2.05,         // m from its origin to where its knuckles meet the glass
  taps: [1.25, 1.95, 2.65],   // s into Knock when the knuckles hit the glass
  shake: 0.035,        // m camera shudder per tap for a player within shakeRange
  shakeRange: 14,
  waveTime: 5,         // s of waving
  stare: [10, 18],     // s it stands staring before it knocks again (random in this range)
  fade: 0.5,           // s cross-fade between actions
  turnRate: 1.2,       // rad/s it can turn while walking
  headLimit: 0.6,      // rad the head may turn toward the player (the hood is rigid with it)
  eyeLimit: 0.5,       // rad the eyes may turn on top of the head
};

// materials for outdoors: the sky as environment; single-sided (the export marks them double-
// sided, and the cloak is a thin closed shell: its inner faces, lit with flipped normals, showed
// as bright slivers along every fold edge); the eyes reflect the sky less (a blue sheen)
//
// Detail maps (the asset's material contract, blender/assets/grimble.py): a material whose
// extras carry `detail = {normal, uv, scale, blend: "udn"}` gets that tiling normal map on top of
// its unique baked normal map (whiteout/UDN blend: the two tangent-space x/y offsets add). The
// detail texture is read from the asset's texture folder, on the UV set `uv` (world scale).
const detailCache = new Map();
function addDetailNormal(m, base) {
  const d = m.userData.detail;
  if (!d || !m.normalMap || m.userData._detail) return;
  m.userData._detail = true;
  if (!detailCache.has(d.normal)) {
    const t = new THREE.TextureLoader().load(`${base}textures/${d.normal}.webp`);
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.colorSpace = THREE.NoColorSpace;
    t.flipY = false;                     // glTF UV convention
    t.anisotropy = 4;
    detailCache.set(d.normal, t);
  }
  const tex = detailCache.get(d.normal);
  m.onBeforeCompile = (shader) => {
    shader.uniforms.detailNormalMap = { value: tex };
    shader.uniforms.detailScale = { value: d.scale ?? 0.35 };
    // the detail UVs: the same set the base colour map reads when it's on that channel
    const uvVar = m.map && m.map.channel === (d.uv ?? 1) ? 'vMapUv' : 'vNormalMapUv';
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <normalmap_pars_fragment>', '#include <normalmap_pars_fragment>\nuniform sampler2D detailNormalMap;\nuniform float detailScale;')
      .replace('normal = normalize( tbn * mapN );', [
        'vec3 detN = texture2D( detailNormalMap, ' + uvVar + ' ).xyz * 2.0 - 1.0;',
        'mapN = normalize( vec3( mapN.xy + detN.xy * detailScale, mapN.z ) );',
        'normal = normalize( tbn * mapN );',
      ].join('\n'));
  };
  m.customProgramCacheKey = () => 'grimble-detail';
  m.needsUpdate = true;
}

export function prepareGrimble(root, envMap, base = '../assets/models/') {
  root.traverse((o) => {
    if (!o.isMesh) return;
    o.castShadow = false;
    o.receiveShadow = false;
    o.frustumCulled = false;            // skinned bounds don't follow the animation
    for (const m of [o.material].flat()) {
      m.envMap = envMap;
      m.side = THREE.FrontSide;
      m.envMapIntensity = o.userData.look ? 0.45 : 1.0;
      addDetailNormal(m, base);
    }
  });
}

export class Grimble {
  // route: [[x, z], ...] in glTF metres, the last point on the glass line (x = glass);
  // ground(x, z) -> y of the ground there
  constructor(scene, gltf, { route, ground, envMap, opts = {} }) {
    this.o = { ...DEFAULTS, ...opts };
    this.root = gltf.scene;
    const ud = this.root.userData;
    for (const k of ['stride', 'cycle']) if (ud[k]) this.o[k] = ud[k];
    if (ud.knockReach) this.o.reach = ud.knockReach;
    this.ground = ground;
    prepareGrimble(this.root, envMap, opts.base);
    // the route stops short of the glass by the knock reach, so the knuckles land on it
    const pts = route.map(([x, z]) => new THREE.Vector2(x, z));
    const last = pts[pts.length - 1], prev = pts[pts.length - 2];
    const dir = last.clone().sub(prev).normalize();
    this.stand = last.clone().addScaledVector(dir, -this.o.reach);
    this.path = [...pts.slice(0, -1), this.stand];
    this.lens = this.path.slice(1).map((p, i) => p.distanceTo(this.path[i]));
    this.total = this.lens.reduce((a, b) => a + b, 0);
    this.s = 0;                                // distance walked
    this.heading = Math.atan2(this.path[1].x - this.path[0].x, this.path[1].y - this.path[0].y);
    this.state = 'wait';
    this.t = 0;
    this.root.visible = false;
    scene.add(this.root);
    this.place();

    this.mixer = new THREE.AnimationMixer(this.root);
    this.actions = Object.fromEntries(gltf.animations.map((c) => [c.name, this.mixer.clipAction(c)]));
    if (this.actions.Knock) { this.actions.Knock.setLoop(THREE.LoopOnce); this.actions.Knock.clampWhenFinished = true; }
    this.current = null;
    this.head = this.root.getObjectByName('Head');
    // the head bone's own axes point along the bone: find which of its local directions is
    // the creature's forward in the bind pose (before any animation runs)
    if (this.head) {
      this.root.updateMatrixWorld(true);
      const fwd = new THREE.Vector3(0, 0, 1).applyQuaternion(this.root.getWorldQuaternion(new THREE.Quaternion()));
      this.headFwd = fwd.applyQuaternion(this.head.getWorldQuaternion(new THREE.Quaternion()).invert());
    }
    this.eyes = [];
    this.root.traverse((o) => { if (o.userData.look) this.eyes.push({ o, rest: o.quaternion.clone() }); });
    this.blob = blobShadow(scene);
    window.__grimble = this;
  }

  play(name) {
    const next = this.actions[name];
    if (!next || next === this.current) return;
    next.reset().play();
    if (this.current) next.crossFadeFrom(this.current, this.o.fade, false);
    this.current = next;
  }

  // position along the route
  place() {
    let s = Math.min(this.s, this.total), i = 0;
    while (i < this.lens.length - 1 && s > this.lens[i]) { s -= this.lens[i]; i++; }
    const p = this.path[i].clone().lerp(this.path[i + 1], this.lens[i] ? s / this.lens[i] : 1);
    this.root.position.set(p.x, this.ground(p.x, p.y), p.y);
    this.seg = i;
  }

  update(dt, player) {
    if (window.__bench) return;      // benchmarks and screenshots run without it (repeatable views)
    const o = this.o;
    this.t += dt;
    if (this.state === 'wait') {
      if (this.t < o.delay) return;
      this.root.visible = true;
      this.state = 'walk';
      this.t = 0;
      this.play('Walk');
    }
    if (this.state === 'walk') {
      this.s += (o.stride / o.cycle) * dt;
      this.place();
      // turn toward the current segment (front = local +z in glTF)
      const a = this.path[this.seg], b = this.path[this.seg + 1];
      const want = Math.atan2(b.x - a.x, b.y - a.y);
      let d = want - this.heading;
      d = Math.atan2(Math.sin(d), Math.cos(d));
      this.heading += Math.sign(d) * Math.min(Math.abs(d), o.turnRate * dt);
      if (this.s >= this.total) { this.state = 'knock'; this.t = 0; this.play(this.actions.Knock ? 'Knock' : 'Idle'); }
    } else if (this.state === 'knock') {
      const len = this.actions.Knock?.getClip().duration ?? 3.5;
      for (const at of o.taps) if (this.t >= at && this.t - dt < at) this._shake = 1;
      if (this.t >= len) { this.state = 'wave'; this.t = 0; this.play('Wave'); }
    } else if (this.state === 'wave') {
      if (this.t >= o.waveTime) {
        this.state = 'watch'; this.t = 0; this.play('Idle');
        this.stareFor = o.stare[0] + Math.random() * (o.stare[1] - o.stare[0]);
      }
    } else if (this.state === 'watch') {
      // ... and again: knock, wave, stare; after a few rounds (if it can hunt) it breaks in
      if (this.t >= this.stareFor) {
        this.loops = (this.loops ?? 0) + 1;
        if (this.hunt && this.loops >= this.hunt.o.loopsBeforeSmash) { this.state = 'inside'; this.hunt.start(); }
        else { this.state = 'knock'; this.t = 0; this.play('Knock'); }
      }
    } else if (this.state === 'inside') {
      this.hunt.update(dt, player, this.playerObj);
    }
    this.root.rotation.y = this.heading;
    this.mixer.update(dt);
    this.lookAt(player);
    this.blob.position.set(this.root.position.x, this.root.position.y + 0.02, this.root.position.z);
    this.blob.visible = this.root.visible;
  }

  // the glass shudders under each tap: a short decaying jolt of the camera when the player is near
  shakeCamera(camera, dt) {
    if (!this._shake) return;
    const d = camera.position.distanceTo(this.root.position);
    if (d < this.o.shakeRange) {
      const a = this.o.shake * this._shake * (1 - d / this.o.shakeRange);
      camera.position.x += (Math.random() - 0.5) * a;
      camera.position.y += (Math.random() - 0.5) * a;
    }
    this._shake = Math.max(0, this._shake - dt * 6);
  }

  // once it has stopped, the head turns toward the player (on top of the animation) and the eyes
  // follow; while walking it looks where it's going
  lookAt(player) {
    if (!player || this.state === 'walk' || this.state === 'wait') return;
    if (this.state === 'inside' && !['chase', 'swipe', 'reachUp'].includes(this.hunt.state)) return;
    this.root.updateMatrixWorld(true);
    // crawling, the hood is as wide as the openings: only the eyes follow the player then
    const crawling = this.state === 'inside' && this.hunt.state !== 'reachUp';
    if (this.head && !crawling) turnToward(this.head, player, this.o.headLimit, this.headFwd);
    for (const e of this.eyes) {
      e.o.quaternion.copy(e.rest);
      e.o.updateMatrixWorld(true);
      turnToward(e.o, player, this.o.eyeLimit);
    }
  }
}

// rotate `node` (forward = `localFwd` in its own axes) toward a world point, at most `limit`
// radians away from where the animation left it
const _q = new THREE.Quaternion(), _p = new THREE.Vector3(), _w = new THREE.Quaternion();
function turnToward(node, target, limit, localFwd = new THREE.Vector3(0, 0, 1)) {
  node.getWorldPosition(_p);
  node.getWorldQuaternion(_w);
  const fwd = localFwd.clone().applyQuaternion(_w);
  const to = target.clone().sub(_p).normalize();
  const angle = fwd.angleTo(to);
  if (angle < 1e-4) return;
  _q.setFromUnitVectors(fwd, to);
  if (angle > limit) _q.slerp(new THREE.Quaternion(), 1 - limit / angle);
  // world-space delta -> the node's parent space
  const parentQ = node.parent ? node.parent.getWorldQuaternion(new THREE.Quaternion()) : new THREE.Quaternion();
  const local = parentQ.clone().invert().multiply(_q).multiply(parentQ);
  node.quaternion.premultiply(local);
  node.updateMatrixWorld(true);
}

function blobShadow(scene) {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d');
  const grad = g.createRadialGradient(64, 64, 4, 64, 64, 64);
  grad.addColorStop(0, 'rgba(0,0,0,0.55)');
  grad.addColorStop(0.6, 'rgba(0,0,0,0.25)');
  grad.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = grad;
  g.fillRect(0, 0, 128, 128);
  const tex = new THREE.CanvasTexture(c);
  const m = new THREE.Mesh(new THREE.PlaneGeometry(6, 5), new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false }));
  m.rotation.x = -Math.PI / 2;
  m.renderOrder = 1;
  m.visible = false;
  scene.add(m);
  return m;
}
