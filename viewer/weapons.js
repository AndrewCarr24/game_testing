import * as THREE from 'three';
import { ViewModel, viewModelMaterial } from './weapons_viewmodel.js';
import { makeTarget } from './combat.js';

// The player's weapons: data definitions (WEAPONS), the controller that attacks with the armed
// one (Weapons), and a stand-in target to practise on (spawnDummy). Combat itself (targets,
// damage, sweeps, shots, events) is viewer/combat.js; design notes: design/combat.md.
//
// A weapon is a pickup whose interact definition names it (`weapon: '<id>'`, or its item id is
// a WEAPONS key). Armed (inventory), it shows in the first-person view model and:
//   melee   click / Enter = the primary attack, right click = the secondary; from behind an
//           unaware target (combat.canTakedown) the primary becomes the takedown
//   gun     (designed, no gun asset yet) click = fire, right click held = aim down sights,
//           R = reload; ammo from inventory items (`ammo.item`), recoil kicks the view
// Adding a melee weapon = a WEAPONS entry + a pickup asset with `weapon` in its interact dict
// (and _Grip / _Tip / _Edge empties for the view model).
//
// Times are seconds, distances metres, angles degrees. Attack keys are view-model poses
// relative to the hold pose: [t, { p: [x, y, z] (camera space), r: [pitch, yaw, roll] }].

const STAB_KEYS = [
  [0.0, {}],
  [0.07, { p: [0.015, -0.025, 0.07], r: [-6, -4, 8] }],         // draw back
  [0.15, { p: [-0.075, 0.04, -0.3], r: [-9, 6, -4] }, 'linear'], // thrust, the tip to the centre
  [0.21, { p: [-0.07, 0.035, -0.28], r: [-8, 5, -4] }],
  [0.5, {}],
];
const SLASH_KEYS = [
  [0.0, {}],
  [0.1, { p: [0.09, 0.07, 0.02], r: [8, -32, -42] }],             // wind up to the right, blade back
  [0.25, { p: [-0.2, -0.04, -0.12], r: [-6, 40, 30] }, 'linear'], // sweep across, right to left
  [0.32, { p: [-0.22, -0.06, -0.1], r: [-8, 44, 34] }],
  [0.62, {}],
];
const TAKEDOWN_KEYS = [
  [0.0, {}],
  [0.12, { p: [-0.04, 0.13, 0.05], r: [22, 6, -10] }],           // raised, the tip back
  [0.2, { p: [-0.08, -0.05, -0.27], r: [-62, 8, -6] }, 'linear'],   // driven down and in
  [0.42, { p: [-0.08, -0.06, -0.26], r: [-62, 8, -6] }],
  [0.8, {}],
];
const SWING_KEYS = [   // a club (bat, pan, poker): big wind-up over the shoulder, a heavy sweep
  [0.0, {}],
  [0.16, { p: [0.12, 0.14, 0.06], r: [30, -40, -50] }],
  [0.33, { p: [-0.25, -0.08, -0.15], r: [-20, 55, 40] }, 'linear'],
  [0.4, { p: [-0.27, -0.1, -0.13], r: [-22, 58, 42] }],
  [0.85, {}],
];

export const WEAPONS = {
  kitchen_knife: {
    id: 'kitchen_knife', kind: 'melee', name: "Chef's knife",
    // the view model: grip frame at `pos` (camera space), the blade along `aim`, the back of the hand toward `back`
    hold: { pos: [0.18, -0.18, -0.38], aim: [-0.2, 0.32, -1], back: [0.4, 0.45, 1], arm: [0.5, -0.6, 0.6], gripRadius: 0.0115 },
    attacks: {
      primary: { name: 'stab', damage: 55, range: 1.05, arc: 26, hitAt: 0.15, duration: 0.5, cooldown: 0.52, keys: STAB_KEYS },
      secondary: { name: 'slash', damage: 38, range: 1.2, arc: 100, maxTargets: 2, hitAt: 0.2, duration: 0.62, cooldown: 0.66, keys: SLASH_KEYS },
      takedown: { name: 'takedown', damage: 100, range: 1.25, arc: 50, hitAt: 0.2, duration: 0.8, cooldown: 0.9, keys: TAKEDOWN_KEYS },
    },
    hitStop: 0.075,            // the view model holds still for this long on a hit (0.13 takedown)
    kick: 0.9,                 // the view's jolt on a hit (degrees)
    noise: 0.6,                // a hit's noise (window.__noise); swings are silent
    sfx: { swing: 'knife_swing', hit: 'knife_hit', wall: 'knife_wall', takedown: 'knife_takedown' },
  },

  // ---- more melee weapons: data only, until their assets exist (a pickup with `weapon: '<id>'`)
  bat: {
    id: 'bat', kind: 'melee', name: 'Baseball bat',
    hold: { pos: [0.24, -0.26, -0.42], aim: [-0.35, 0.75, -0.55], back: [1, 0.2, 0.4], gripRadius: 0.015 },
    attacks: {
      primary: { name: 'swing', damage: 35, range: 1.7, arc: 110, maxTargets: 2, hitAt: 0.3, duration: 0.85, cooldown: 0.95, keys: SWING_KEYS },
      secondary: { name: 'jab', damage: 15, range: 1.3, arc: 30, hitAt: 0.15, duration: 0.5, cooldown: 0.55, keys: STAB_KEYS, stagger: 1 },
    },
    hitStop: 0.11, kick: 1.8, noise: 0.9,
    sfx: { swing: 'bat_swing', hit: 'bat_hit', wall: 'bat_hit' },
  },
  frying_pan: {
    id: 'frying_pan', kind: 'melee', name: 'Frying pan',
    hold: { pos: [0.22, -0.24, -0.4], aim: [-0.3, 0.6, -0.75], back: [1, 0.3, 0.3], gripRadius: 0.012 },
    attacks: {
      primary: { name: 'swing', damage: 30, range: 1.45, arc: 100, hitAt: 0.27, duration: 0.8, cooldown: 0.9, keys: SWING_KEYS },
    },
    hitStop: 0.1, kick: 1.5, noise: 1.1,              // a pan rings out
    sfx: { swing: 'bat_swing', hit: 'pan_hit', wall: 'pan_hit' },
  },
  fireplace_poker: {
    id: 'fireplace_poker', kind: 'melee', name: 'Fireplace poker',
    hold: { pos: [0.22, -0.24, -0.4], aim: [-0.25, 0.55, -0.8], back: [1, 0.3, 0.3], gripRadius: 0.009 },
    attacks: {
      primary: { name: 'swing', damage: 40, range: 1.6, arc: 90, hitAt: 0.28, duration: 0.8, cooldown: 0.9, keys: SWING_KEYS },
      secondary: { name: 'thrust', damage: 30, range: 1.5, arc: 20, hitAt: 0.16, duration: 0.55, cooldown: 0.6, keys: STAB_KEYS },
    },
    hitStop: 0.09, kick: 1.3, noise: 0.8,
    sfx: { swing: 'bat_swing', hit: 'bat_hit', wall: 'pan_hit' },
  },

  // ---- guns (the armory, later): the schema the controller already reads. No asset, no view model yet.
  // pistol: {
  //   id: 'pistol', kind: 'gun', name: 'Pistol',
  //   hold: { pos, aim, back, gripRadius },  ads: { pos: [0, -0.07, -0.3], fov: 50, time: 0.18 },
  //   damage: 34, range: 60, rate: 0.16 (s between shots), auto: false, pellets: 1,
  //   spread: { hip: 3.5, ads: 0.6, move: 2 },          // degrees (full cone); + move while walking
  //   recoil: { pitch: 2.4, yaw: 0.7, recover: 9 },     // degrees per shot; recover: 1/s back toward the aim
  //   ammo: { item: 'ammo_9mm', mag: 15 }, reload: 1.5,
  //   noise: 2.5, sfx: { fire: 'gunshot', empty: 'gun_empty', reload: 'gun_reload' },
  // },
};

// a sound by name, or a stand-in from the existing sprite while the combat sounds aren't in it
const FALLBACK = {
  knife_swing: ['throw', { rate: 1.5, db: -6 }], knife_hit: ['hit', { rate: 1.25, db: -2 }],
  knife_wall: ['pickup_metal', { rate: 1.3, db: -4 }], knife_takedown: ['hit', { rate: 0.9 }],
  bat_swing: ['throw', { rate: 0.9 }], bat_hit: ['hit', { rate: 0.8 }], pan_hit: ['pickup_metal', { rate: 0.7 }],
  body_fall: ['fall', {}], player_hurt: ['hit', { rate: 0.75, db: -3 }],
  gunshot: ['shatter', { rate: 0.5 }], gun_empty: ['switch_off', {}], gun_reload: ['use', {}],
};
export function sfx(name, position = null, opts = {}) {
  const s = window.__sfx;
  if (!s?.play) return null;
  if (s.manifest && !s.manifest.sounds?.[name] && FALLBACK[name]) {
    s.log?.push?.({ t: Math.round(performance.now()), name, as: FALLBACK[name][0] });
    return s.play(FALLBACK[name][0], position, { ...FALLBACK[name][1], ...opts });
  }
  return s.play(name, position, opts);
}

export function weaponFor(def) {
  if (!def) return null;
  return WEAPONS[def.weapon] ?? WEAPONS[def.item] ?? null;
}

const _dir = new THREE.Vector3(), _q0 = new THREE.Quaternion(), _q1 = new THREE.Quaternion();

export class Weapons {
  // combat: viewer/combat.js; player: viewer/player.js; vitals: the player's PlayerVitals (its target)
  constructor({ combat, camera, inventory, player, noise = null, baked = null, culler = null, level = null,
    canAct = () => true, hidden = () => false }) {
    Object.assign(this, { combat, camera, inventory, player, noise, baked, culler, level, canAct, hidden });
    this.known = new Set();   // weapon ids seen in the inventory (a new one is armed on pickup)
    this.vm = new ViewModel(camera);
    this.id = null;
    this.def = null;
    this.cooldown = 0;
    this.pending = null;      // the attack waiting for its hit frame
    this.lastLook = camera.quaternion.clone();
    this.attacks = 0;         // counters (tests)
    this.ammo = {};           // guns: rounds in the magazine per weapon id
    this.ads = false;
    this.recoil = new THREE.Vector2();
    this.viewKick = new THREE.Vector2();
    window.addEventListener('mousedown', (e) => this.mouse(e, true));
    window.addEventListener('mouseup', (e) => this.mouse(e, false));
    window.addEventListener('contextmenu', (e) => { if (this.def && document.pointerLockElement) e.preventDefault(); });
  }

  get player_target() { return this.combat.get('player'); }
  isWeapon(id) { return !!weaponFor(this.inventory.get(id)?.def); }

  // Hand (viewer/items.js) asks: draw the armed item as a weapon? -> the view model takes it
  show(id, node) {
    const def = id ? weaponFor(this.inventory.get(id)?.def) : null;
    if (def === this.def) return !!def;
    this.id = def ? id : null;
    this.def = def;
    this.pending = null;
    this.vm.setWeapon(def, def ? node : null);
    if (def && def.kind === 'gun') this.ammo[def.id] ??= def.ammo?.mag ?? 0;
    return !!def;
  }

  mouse(e, down) {
    if (!this.def || !document.pointerLockElement || !this.canAct()) { if (!down && e.button === 2) this.ads = false; return; }
    if (e.button === 0 && down) this.attack('primary');
    if (e.button === 2) {
      if (this.def.kind === 'gun') this.ads = down;
      else if (down) this.attack('secondary');
    }
  }

  // the weapons carried, in the order they were picked up
  carried() { return this.inventory.ids().filter((id) => this.isWeapon(id)); }

  // keys: 1-4 arm the nth weapon carried (again: put it away), R reloads a gun. True if handled.
  key(code) {
    const m = /^Digit([1-4])$/.exec(code);
    if (m) {
      const id = this.carried()[+m[1] - 1];
      if (!id) return false;
      if (this.inventory.armed === id) this.inventory.holster();
      else { this.inventory.armed = id; this.inventory.changed(); }
      return true;
    }
    if (code === 'KeyR' && this.def?.kind === 'gun') return this.reload(), true;
    return false;
  }

  // what the armed weapon would do now (the prompt under the crosshair, the crosshair's cue)
  target() {
    const me = this.player_target;
    if (!me || !this.def || this.def.kind !== 'melee' || !this.def.attacks.takedown) return null;
    const a = this.def.attacks.takedown;
    const eye = this.camera.position, fwd = this.camera.getWorldDirection(_dir);
    for (const t of this.combat.living((t) => t.team !== me.team)) {
      const p = t.position();
      const c = new THREE.Vector3(p.x, THREE.MathUtils.clamp(eye.y, p.y + 0.3, p.y + t.height - 0.2), p.z);
      const to = c.sub(eye), d = to.length();
      if (d - t.radius > a.range) continue;
      if (to.normalize().dot(fwd) < Math.cos(THREE.MathUtils.degToRad(a.arc / 2 + 10))) continue;
      if (this.combat.canTakedown(t, me) && this.combat.lineOfSight(eye, p.clone().setY(eye.y))) return t;
    }
    return null;
  }
  hint() {
    if (!this.def) return null;
    if (this.def.kind === 'gun') return `Fire · right-click aim${this.ammo[this.def.id] ? '' : ' · empty'}`;
    if (this.target()) return 'Takedown';
    const a = this.def.attacks;
    return `${cap(a.primary.name)}${a.secondary ? ` · right-click ${a.secondary.name}` : ''}`;
  }

  attack(which = 'primary') {
    const def = this.def;
    if (!def || this.cooldown > 0 || this.pending || this.player.isDown || !this.canAct()) return false;
    if (def.kind === 'gun') return this.fire();
    const me = this.player_target;
    let a = def.attacks[which] ?? def.attacks.primary;
    let victim = null;
    if (which === 'primary' && def.attacks.takedown) {
      victim = this.target();
      if (victim) a = def.attacks.takedown;
    }
    this.attacks++;
    this.cooldown = a.cooldown;
    this.vm.play({ duration: a.duration, keys: a.keys });
    this.pending = { a, t: 0, victim, which, me };
    if (a.name !== 'takedown') sfx(def.sfx?.swing, null, { delay: Math.max(0, a.hitAt - 0.1) });
    return true;
  }

  strike(p) {
    const { a, victim, me } = p, def = this.def;
    const origin = this.camera.position.clone();
    const dir = this.camera.getWorldDirection(new THREE.Vector3());
    let hits;
    if (a.name === 'takedown' && victim?.alive && this.combat.canTakedown(victim, me)) {
      // the stealth takedown: the marked target, whatever the sweep finds
      const point = victim.position().clone().setY(origin.y - 0.15);
      const r = this.combat.hit(victim, Math.max(a.damage, victim.health), {
        from: me, dir: dir.clone().setY(0).normalize(), weapon: def.id, part: 'body', point, stealth: true, kind: 'melee' });
      hits = r ? [{ target: victim, point, damage: r.damage, part: 'body', stealth: true, killed: r.killed }] : [];
      this.combat.emit('attack', { from: me, origin, dir, weapon: def.id, hits, takedown: true });
    } else {
      hits = this.combat.attack({ from: me, origin, dir, weapon: def, range: a.range, arc: a.arc, damage: a.damage,
        takedown: 0, maxTargets: a.maxTargets ?? 1 });
    }
    if (hits.length) {
      const at = hits[0].point;
      const stealth = hits.some((h) => h.stealth);
      sfx(stealth ? def.sfx?.takedown ?? def.sfx?.hit : def.sfx?.hit, at);
      this.noise?.emit({ position: at.clone(), loudness: stealth ? def.noise * 0.5 : def.noise, source: 'melee', weapon: def.id });
      this.vm.freeze(stealth ? 0.13 : def.hitStop);
      this.viewKick.set((Math.random() - 0.5) * def.kick, def.kick * (stealth ? 1.4 : 1));
    } else {
      // the blade meets a wall or a counter in reach: a clink, a small jolt
      const wall = this.combat.raycast(origin, dir, a.range * 0.9);
      if (wall) {
        sfx(def.sfx?.wall, wall.point);
        this.vm.freeze(def.hitStop * 0.6);
        this.viewKick.set(0, def.kick * 0.4);
        this.noise?.emit({ position: wall.point.clone(), loudness: 0.3, source: 'melee_wall', weapon: def.id });
      }
    }
    this.lastHits = hits;
    return hits;
  }

  // ---- guns (designed for the armory; no gun is in the level yet)
  fire() {
    const def = this.def, me = this.player_target;
    const mag = this.ammo[def.id] ?? 0;
    if (mag <= 0) { sfx(def.sfx?.empty, null); this.cooldown = 0.25; return false; }
    this.ammo[def.id] = mag - 1;
    this.cooldown = def.rate ?? 0.2;
    const moving = Math.hypot(this.player.vel.x, this.player.vel.z) > 0.5;
    const spread = (this.ads ? def.spread?.ads ?? 0.5 : def.spread?.hip ?? 3) + (moving ? def.spread?.move ?? 0 : 0);
    const origin = this.camera.position.clone(), dir = this.camera.getWorldDirection(new THREE.Vector3());
    const res = this.combat.shoot({ from: me, origin, dir, spread, range: def.range ?? 60, damage: def.damage ?? 30, weapon: def.id, pellets: def.pellets ?? 1 });
    this.noise?.emit({ position: origin.clone(), loudness: def.noise ?? 2.5, source: 'gunshot', weapon: def.id });
    sfx(def.sfx?.fire ?? 'gunshot', origin);
    const r = def.recoil || {};
    this.recoil.x += (Math.random() - 0.5) * 2 * (r.yaw ?? 0.6);
    this.recoil.y += r.pitch ?? 2;
    this.attacks++;
    this.lastShot = res;
    return res;
  }
  reload() {
    const def = this.def;
    if (def?.kind !== 'gun' || !def.ammo) return false;
    const need = def.ammo.mag - (this.ammo[def.id] ?? 0), have = this.inventory.count(def.ammo.item);
    const n = Math.min(need, have);
    if (n <= 0) return false;
    for (let i = 0; i < n; i++) this.inventory.remove(def.ammo.item);
    this.ammo[def.id] += n;
    this.cooldown = def.reload ?? 1.5;
    sfx(def.sfx?.reload, null);
    return true;
  }

  // the view: a hit's jolt and a gun's recoil (degrees, decaying); begin() takes last frame's off
  beginView() {
    if (this._applied) { this.camera.quaternion.multiply(_q0.copy(this._applied).invert()); this._applied = null; }
  }
  endView(dt) {
    const k = this.viewKick, r = this.recoil;
    const pitch = THREE.MathUtils.degToRad(k.y + r.y), yaw = THREE.MathUtils.degToRad(k.x + r.x);
    k.multiplyScalar(Math.max(0, 1 - dt * 14));
    r.multiplyScalar(Math.max(0, 1 - dt * (this.def?.recoil?.recover ?? 9)));
    if (Math.abs(pitch) + Math.abs(yaw) < 1e-5 || this.player.isDown) return;
    this._applied = new THREE.Quaternion().setFromEuler(new THREE.Euler(pitch, yaw, 0, 'YXZ'));
    this.camera.quaternion.multiply(this._applied);
  }

  update(dt) {
    // a weapon just picked up is armed straight away, if nothing else is in hand
    for (const id of this.carried()) if (!this.known.has(id)) {
      this.known.add(id);
      if (!this.inventory.armed) { this.inventory.armed = id; this.inventory.changed(); }
    }
    for (const d of this.combat.dummies || []) d.update(dt);
    this.cooldown = Math.max(0, this.cooldown - dt);
    if (this.pending) {
      const p = this.pending;
      if (!(this.vm.frozen > 0)) p.t += dt;
      if (p.t >= p.a.hitAt) { this.pending = null; this.strike(p); }
    }
    // how far the view turned since last frame (the hand lags behind it)
    const q = this.camera.quaternion;
    _q1.copy(this.lastLook).invert().multiply(q);
    const e = new THREE.Euler().setFromQuaternion(_q1, 'YXZ');
    this.lastLook.copy(q);
    if (this.culler) {
      const room = this.culler.here?.name ?? null;
      this.vm.light(this.baked, room, room ? this.level?.rooms?.[room] : null);
    }
    this.vm.root.visible = !!this.def && !this.player.isDown && !this.hidden();
    this.vm.update(dt, {
      speed: Math.hypot(this.player.vel.x, this.player.vel.z), grounded: this.player.grounded,
      lookDelta: new THREE.Vector2(e.y, e.x),
    });
  }
}
const cap = (s) => s[0].toUpperCase() + s.slice(1);

// ------------------------------------------------------------------ a practice dummy
// A mannequin (a capsule body and a head) that takes hits and dies: a stand-in target until
// the invaders are in. It faces `rotationY` (degrees, 0 = +z) and is unaware unless `aware`.
// Hit: a flash and a wobble away from the blow; dead: it topples over the way it was hit.
export function spawnDummy({ scene, combat, colliders = null, position, rotationY = 0, aware = false, id = null, health = 100 }) {
  const root = new THREE.Group();
  root.name = 'Combat_Dummy';
  const mat = new THREE.MeshStandardMaterial({ color: 0xc9c2b6, roughness: 0.55, emissive: 0x000000 });
  const dark = new THREE.MeshStandardMaterial({ color: 0x2a2c30, roughness: 0.7 });
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.2, 1.0, 6, 16), mat);
  body.position.y = 0.2 + 0.5 + 0.1;
  body.scale.set(1, 1, 0.75);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.12, 20, 14), mat);
  head.position.set(0, 1.62, 0);
  const nose = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.03, 0.06), dark);   // which way it faces
  nose.position.set(0, 1.62, 0.12);
  const base = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.25, 0.1, 20), dark);
  base.position.y = 0.05;
  const tilt = new THREE.Group();
  tilt.add(body, head, nose);
  root.add(base, tilt);
  root.position.copy(position);
  root.rotation.y = THREE.MathUtils.degToRad(rotationY);
  root.traverse((o) => { if (o.isMesh) o.castShadow = o.receiveShadow = true; });
  scene.add(root);
  let collider = null;
  if (colliders) {
    collider = new THREE.Box3(new THREE.Vector3(position.x - 0.22, position.y, position.z - 0.22), new THREE.Vector3(position.x + 0.22, position.y + 1.8, position.z + 0.22));
    colliders.push(collider);
  }
  const state = { flash: 0, wobble: new THREE.Vector3(), wobbleV: new THREE.Vector3(), fall: 0, fallAxis: null };
  const facing = () => new THREE.Vector3(Math.sin(root.rotation.y), 0, Math.cos(root.rotation.y));
  const t = makeTarget({
    id: id ?? `dummy_${Math.random().toString(36).slice(2, 7)}`, kind: 'dummy', team: 'invader',
    position: () => root.position.clone(), radius: 0.24, height: 1.75, maxHealth: health, health,
    facing, aware,
    onHit: (tt, dmg, info) => {
      state.flash = 1;
      const d = info?.dir ? info.dir.clone().setY(0).normalize() : facing().negate();
      state.wobbleV.addScaledVector(d, 2.2 + dmg / 25);
      tt.lastHit = { damage: dmg, stealth: !!info?.stealth, part: info?.part };
    },
    onDeath: (tt, info) => {
      const d = info?.dir ? info.dir.clone().setY(0).normalize() : facing().negate();
      state.fallAxis = new THREE.Vector3(d.z, 0, -d.x).normalize();   // topple along the blow
      state.fallDir = d;
      if (collider) { const i = colliders.indexOf(collider); if (i >= 0) colliders.splice(i, 1); }
      setTimeout(() => sfx('body_fall', root.position.clone().setY(root.position.y + 0.3)), 380);
    },
  });
  t.root = root;
  if (collider) collider.owner = t;     // (combat's rays meet the body, not this box)
  t.update = (dt) => {
    state.flash = Math.max(0, state.flash - dt * 5);
    mat.emissive.setRGB(0.35 * state.flash, 0.02 * state.flash, 0.0);
    // a damped spring tilts it away from the blow and back
    state.wobbleV.addScaledVector(state.wobble, -60 * dt).multiplyScalar(Math.max(0, 1 - dt * 7));
    state.wobble.addScaledVector(state.wobbleV, dt);
    if (state.fallAxis) state.fall = Math.min(1, state.fall + dt / 0.55);
    const local = state.wobble.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), -root.rotation.y);
    tilt.rotation.set(local.z * 0.12, 0, -local.x * 0.12);
    if (state.fallAxis) {
      const ax = state.fallAxis.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), -root.rotation.y);
      const k = state.fall * state.fall;                       // falls faster as it goes
      tilt.quaternion.setFromAxisAngle(ax, k * Math.PI / 2 * 0.96);
      tilt.position.y = 0.1 * k;
    }
  };
  t.setAware = (v) => { t.aware = v; };
  t.remove = () => { scene.remove(root); combat.unregister(t); if (collider) { const i = colliders.indexOf(collider); if (i >= 0) colliders.splice(i, 1); } };
  combat.register(t);
  (combat.dummies ??= []).push(t);
  return t;
}
export { viewModelMaterial };
