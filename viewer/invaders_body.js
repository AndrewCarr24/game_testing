import * as THREE from 'three';

// The invaders' bodies. Until the rigged character lands (assets/models/invader.gltf,
// design/invaders/character.md) every invader is a stand-in: a capsule torso, a head (balaclava
// or a pale mask), two-segment arms and legs, the weapon in the right hand, a blob shadow. All of
// them are drawn instanced: one InstancedMesh per part kind (torso, head, limbs, each weapon,
// shadow) = 8 draw calls however many there are. Posed procedurally from the brain's `anim`
// (walk cycle from the distance moved, aim, swing, kick, stagger, crouch, death fall).
// No shadow casting (50 casters would redraw the sun's shadow map); the colour is scaled by the
// light where they stand (window.__house.lightAt), so in a dark room they're dark shapes.
//
// The rigged character, when it lands: what the brain drives, by the names below (one edit here).
// CLIPS: brain anim state -> clip name in invader.gltf; SOCKETS: weapon attach bones.
export const CLIPS = {
  idle: 'Idle', walk: 'Walk', run: 'Run', crouch: 'CrouchIdle', crouchWalk: 'CrouchWalk',
  aim: 'Aim', shoot: 'Shoot', swing: 'Swing', stab: 'Stab', kick: 'Kick', hit: 'HitReact', die: 'Death', open: 'OpenDoor',
};
export const SOCKETS = { handR: 'Socket_HandR', handL: 'Socket_HandL', head: 'Head' };

const TORSO = [0x2b2d31, 0x1f2328, 0x3a3f2e, 0x262c3a, 0x3b2f2a, 0x2f3236, 0x45403a];
const LEGS = [0x1c1d20, 0x24262b, 0x2d2b26, 0x1e2430];
const HEAD = [0x141414, 0x1a1a1c, 0xd6d0c2, 0x141414, 0xc9c2b2];
const ROLE_TORSO = { leader: 0x5a4a3a, watcher: 0x2f3a2c };

const _m = new THREE.Matrix4(), _r = new THREE.Matrix4(), _t = new THREE.Matrix4(), _s = new THREE.Matrix4();
const _q = new THREE.Quaternion(), _e = new THREE.Euler(), _v = new THREE.Vector3(), _one = new THREE.Vector3(1, 1, 1);
const _c = new THREE.Color();
const smooth = (t) => t * t * (3 - 2 * t);

// a joint frame: parent * T(x, y, z) * R(euler XYZ)
function joint(parent, x, y, z, rx = 0, ry = 0, rz = 0, out = new THREE.Matrix4()) {
  _e.set(rx, ry, rz, 'YXZ');
  _q.setFromEuler(_e);
  out.compose(_v.set(x, y, z), _q, _one);
  return out.premultiply(parent);
}

export class InvaderBodies {
  constructor(scene, max = 60) {
    this.scene = scene;
    this.max = max;
    const mat = (o = {}) => new THREE.MeshStandardMaterial({ roughness: 0.85, metalness: 0.0, ...o });
    const limb = new THREE.CylinderGeometry(0.5, 0.42, 1, 8, 1).translate(0, -0.5, 0);
    const torso = new THREE.CapsuleGeometry(0.17, 0.36, 3, 10).scale(1.3, 1, 0.78);
    const head = new THREE.SphereGeometry(0.115, 12, 9).scale(0.92, 1.08, 1.0);
    // weapons: long axis along +z, the grip at the origin
    const rifle = merge([box(0.05, 0.09, 0.78, 0, 0, 0.3), box(0.045, 0.14, 0.05, 0, -0.08, 0.0), box(0.04, 0.07, 0.22, 0, -0.01, -0.15)]);
    const pistol = merge([box(0.035, 0.05, 0.2, 0, 0.03, 0.06), box(0.032, 0.11, 0.04, 0, -0.03, 0.0)]);
    const bat = new THREE.CylinderGeometry(0.036, 0.016, 0.84, 8, 1).rotateX(Math.PI / 2).translate(0, 0, 0.36);
    const knife = merge([box(0.012, 0.035, 0.2, 0, 0, 0.13), box(0.024, 0.03, 0.1, 0, 0, -0.02)]);
    const shadow = new THREE.CircleGeometry(0.42, 16).rotateX(-Math.PI / 2);
    const make = (geo, material, count, name) => {
      const m = new THREE.InstancedMesh(geo, material, count);
      m.name = name;
      m.count = 0;
      m.castShadow = false; m.receiveShadow = false;
      m.frustumCulled = false;
      m.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      m.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(count * 3), 3);
      scene.add(m);
      return m;
    };
    this.meshes = {
      torso: make(torso, mat(), max, 'Invaders_Torso'),
      head: make(head, mat({ roughness: 0.7 }), max, 'Invaders_Head'),
      limb: make(limb, mat(), max * 8, 'Invaders_Limbs'),
      rifle: make(rifle, mat({ roughness: 0.5, metalness: 0.4 }), max, 'Invaders_Rifle'),
      pistol: make(pistol, mat({ roughness: 0.5, metalness: 0.4 }), max, 'Invaders_Pistol'),
      bat: make(bat, mat({ roughness: 0.6 }), max, 'Invaders_Bat'),
      knife: make(knife, mat({ roughness: 0.3, metalness: 0.8 }), max, 'Invaders_Knife'),
      shadow: make(shadow, new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.28, depthWrite: false }), max, 'Invaders_Shadow'),
    };
    this.meshes.shadow.renderOrder = 1;
    this.list = [];
  }

  add(a) {
    const i = this.list.length;
    const pick = (arr) => arr[(a.id * 7 + 3) % arr.length];
    a.look = {
      torso: new THREE.Color(ROLE_TORSO[a.role] ?? pick(TORSO)),
      legs: new THREE.Color(pick(LEGS)),
      head: new THREE.Color(HEAD[(a.id * 5 + 1) % HEAD.length]),
      scale: 0.94 + ((a.id * 13) % 10) / 100,
    };
    this.list.push(a);
    return i;
  }
  remove(a) { this.list = this.list.filter((b) => b !== a); }

  update(agents, dt) {
    const M = this.meshes;
    let nT = 0, nL = 0, nW = { rifle: 0, pistol: 0, bat: 0, knife: 0 }, nS = 0;
    const root = new THREE.Matrix4(), hips = new THREE.Matrix4(), chest = new THREE.Matrix4(), j1 = new THREE.Matrix4(), j2 = new THREE.Matrix4(), hand = new THREE.Matrix4();
    const put = (mesh, i, m, color, light) => { mesh.setMatrixAt(i, m); _c.copy(color).multiplyScalar(light); mesh.setColorAt(i, _c); };
    const inst = (J, r, len) => _s.makeScale(r * 2, len, r * 2).premultiply(J);
    for (const a of this.list) {
      if (nT >= this.max) break;
      const A = a.anim, L = a.look, light = Math.min(1.15, 0.25 + 0.85 * (a.light ?? 1)) * (a.alive ? 1 : 0.8);
      // the walk cycle: from how far it moved
      const sp = a.moveSpeed ?? 0, run = Math.min(1, Math.max(0, (sp - 2.2) / 2.5));
      A.phase += (sp * dt) / (1.25 + 0.75 * run) * Math.PI;
      const amp = Math.min(1, sp / 1.4) * (0.42 + 0.3 * run);
      const s = Math.sin(A.phase), c = Math.cos(A.phase);
      const crouch = a.crouch > 0.5 ? 1 : 0;
      const stag = a.staggerUntil > a.time ? smooth(Math.min(1, (a.staggerUntil - a.time) / 0.4)) : 0;
      // the fall: pitched back about the feet over 0.7 s, then lying there
      const die = a.alive ? 0 : smooth(Math.min(1, A.die));
      root.compose(_v.set(a.pos.x, a.pos.y, a.pos.z), _q.setFromEuler(_e.set(0, a.alive ? a.yaw : a.dieYaw ?? a.yaw, 0)), _v.clone().setScalar(L.scale));
      if (die) root.multiply(_r.makeRotationX(-die * 1.45)).multiply(_t.makeTranslation(0, -die * 0.12, 0));
      const hipY = 0.94 - crouch * 0.42 + Math.abs(c) * 0.03 * amp;
      joint(root, 0, hipY, 0, run * 0.12 + crouch * 0.25 - stag * 0.25, 0, 0, hips);
      joint(hips, 0, 0.3, 0, run * 0.08 - stag * 0.15, 0, s * 0.05 * amp, chest);
      // torso + head
      put(M.torso, nT, _m.copy(chest).multiply(_t.makeTranslation(0, 0, 0)), L.torso, light);
      const hy = Math.max(-1.1, Math.min(1.1, Math.atan2(Math.sin(a.lookYaw - a.yaw), Math.cos(a.lookYaw - a.yaw))));
      joint(chest, 0, 0.42, 0.01, -stag * 0.3, a.alive ? hy : 0, 0, j1);
      put(M.head, nT, j1, L.head, light);
      // legs: hip swing, knee bend (crouch: knees forward)
      const legs = [[-1, s], [1, -s]];
      for (const [side, sw] of legs) {
        let hipA = -sw * amp * 1.05, knee = Math.max(0, sw) * amp * 1.2 + 0.05;
        if (crouch) { hipA = -1.25; knee = 1.9; }
        if (A.kick >= 0 && side === 1) { const k = Math.sin(Math.min(1, A.kick) * Math.PI); hipA = -1.3 * k; knee = 0.9 * (1 - k); }
        joint(hips, side * 0.1, -0.02, 0, hipA, 0, side * 0.03, j1);
        put(M.limb, nL++, inst(j1, 0.08, 0.46), L.legs, light);
        joint(j1, 0, -0.46, 0, knee, 0, 0, j2);
        put(M.limb, nL++, inst(j2, 0.065, 0.47), L.legs, light * 0.8);
      }
      // arms: swing with the walk; raised to aim (both hands on a rifle); the bat's swing
      const aim = A.aim ?? 0, pitch = a.aimPitch ?? 0;
      let rS = s * amp * 0.8, rE = -0.25, rY = 0, rZ = 0;
      let lS = -s * amp * 0.8, lE = -0.25, lY = 0, lZ = 0;
      if (a.gun) {
        // low ready while alert, up to the shoulder to aim
        const ready = Math.max(aim, a.sq?.alert > 0.5 ? 0.35 : 0.12);
        rS = rS * (1 - ready) + (-1.45 - pitch) * ready; rE = -0.25 * (1 - ready) - 0.12 * ready; rY = 0.12 * ready;
        if (a.weaponName === 'rifle') { lS = lS * (1 - ready) + (-1.25 - pitch) * ready; lE = -0.25 - 0.55 * ready; lY = -0.55 * ready; }
      } else if (A.swing >= 0) {
        const W = a.weapon, wu = (W.windup ?? 0.4) / ((W.windup ?? 0.4) + (W.recover ?? 0.5)), t = A.swing;
        if (a.weaponName === 'knife') {
          const k = t < wu ? smooth(t / wu) : 1 - smooth((t - wu) / (1 - wu));
          rS = -0.4 + 0.6 * (t < wu ? k : 0) - 1.1 * (t >= wu ? k : 0); rE = -1.2 + 1.0 * (t >= wu ? k : 0);
        } else {
          // over the right shoulder, then across
          const up = t < wu ? smooth(t / wu) : 1 - smooth(Math.min(1, (t - wu) / 0.25));
          const across = t < wu ? 0 : smooth(Math.min(1, (t - wu) / 0.22));
          rS = -2.4 * up - 1.2 * across * (1 - up); rE = -0.9 * up; rY = 0.8 * up - 1.2 * across; rZ = -0.4 * up;
          lS = rS * 0.8; lE = -0.6; lY = -0.3 * up - 0.6 * across;
        }
      } else if (!a.gun && a.sq?.alert > 0.5) { rS = -0.5 + rS * 0.5; rE = -0.9; }
      if (stag) { rS += 0.5 * stag; lS += 0.5 * stag; }
      for (const [side, S, E, Y, Z] of [[1, rS, rE, rY, rZ], [-1, lS, lE, lY, lZ]]) {
        joint(chest, side * 0.215, 0.33, 0, S, Y, side * 0.08 + Z, j1);
        put(M.limb, nL++, inst(j1, 0.06, 0.3), L.torso, light);
        joint(j1, 0, -0.3, 0, E, 0, 0, j2);
        put(M.limb, nL++, inst(j2, 0.05, 0.28), L.torso, light * 0.9);
        if (side === 1) joint(j2, 0, -0.28, 0, Math.PI / 2, 0, 0, hand);
      }
      const W = M[a.weaponName];
      if (W && nW[a.weaponName] < this.max) {
        // (the gun's barrel along the forearm, the bat's barrel too)
        W.setMatrixAt(nW[a.weaponName], hand);
        W.setColorAt(nW[a.weaponName], _c.set(a.weaponName === 'bat' ? 0x6b4a2e : a.weaponName === 'knife' ? 0x9aa0a6 : 0x1a1b1d).multiplyScalar(light));
        nW[a.weaponName]++;
      }
      // the blob shadow (on the floor under it; stretched when it lies there)
      _m.compose(_v.set(a.pos.x, a.pos.y + 0.012, a.pos.z), _q.setFromEuler(_e.set(0, a.yaw, 0)), _v.clone().set(1, 1, 1 + die * 1.6));
      if (die) _m.multiply(_t.makeTranslation(0, 0, -0.5 * die));
      M.shadow.setMatrixAt(nS++, _m);
      nT++;
    }
    M.torso.count = M.head.count = nT; M.limb.count = nL; M.shadow.count = nS;
    for (const k of Object.keys(nW)) M[k].count = nW[k];
    for (const m of Object.values(M)) { m.instanceMatrix.needsUpdate = true; if (m.instanceColor) m.instanceColor.needsUpdate = true; }
  }

  dispose() { for (const m of Object.values(this.meshes)) { this.scene.remove(m); m.geometry.dispose(); m.material.dispose(); } }
}

function box(w, h, d, x, y, z) { return new THREE.BoxGeometry(w, h, d).translate(x, y, z); }
// a few non-indexed boxes into one geometry (positions + normals)
function merge(geos) {
  const parts = geos.map((g) => (g.index ? g.toNonIndexed() : g));
  const n = parts.reduce((s, g) => s + g.attributes.position.count, 0);
  const pos = new Float32Array(n * 3), nor = new Float32Array(n * 3);
  let o = 0;
  for (const g of parts) { pos.set(g.attributes.position.array, o * 3); nor.set(g.attributes.normal.array, o * 3); o += g.attributes.position.count; }
  const out = new THREE.BufferGeometry();
  out.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  out.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
  return out;
}
