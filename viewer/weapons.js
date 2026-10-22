import * as THREE from 'three';
import { ViewModel, viewModelMaterial } from './weapons_viewmodel.js';
import { makeTarget } from './combat.js';

// The player's weapons: data definitions (WEAPONS), the controller that attacks with the armed
// one (Weapons), and a stand-in target to practise on (spawnDummy). Combat itself (targets,
// damage, sweeps, shots, events) is viewer/combat.js; design notes: design/combat.md.
//
// A weapon is a pickup whose interact definition names it (`weapon: '<id>'`, or its item id is
// a WEAPONS key). Armed (inventory), it shows in the first-person view model and Enter attacks
// with it (no mouse buttons: the input stays on the keyboard):
//   melee   Enter = its one attack (the knife: a slash); from behind an unaware target
//           (combat.canTakedown) the same swing is a takedown when the weapon has `takedown`
//   gun     (designed, no gun asset yet) Enter = fire, R = reload; ammo from inventory items
//           (`ammo.item`), recoil kicks the view
// Adding a melee weapon = a WEAPONS entry + a pickup asset with `weapon` in its interact dict
// (and _Grip / _Tip / _Edge empties for the view model).
//
// Times are seconds, distances metres, angles degrees. An attack's keys are view-model poses
// relative to the hold pose: [t, { p: [x, y, z] (camera space), r: [pitch, yaw, roll] (the arm
// about the grip), w: [flex (palm-ward +), deviation (toward the thumb +), twist] (the wrist bones) }, ease],
// ease = 'linear' | 'in' (accelerating) | 'out' (decelerating) | smoothstep (default).
// Its `sweep` is where the blade travels in the view while it can hit: from / to = [yaw, pitch]
// (degrees off the view's centre, + = right / up) between t0 and t1; each frame the step swept
// since the last one is a melee cone (combat.attack), every target at most once per swing.

// the knife's slash, right to left and a little down: a short wind-up (the arm draws back to the
// right, the wrist cocks), the cut (fast, accelerating into the centre), the follow-through past
// the left of the view (the wrist rolls over), a beat, the recovery back to the guard
const SLASH_KEYS = [
  [0.0, {}],
  [0.13, { p: [0.055, 0.045, 0.0], r: [8, -26, -22], w: [-30, 20, -10] }, 'out'],   // anticipation: drawn back, wrist cocked
  [0.2, { p: [-0.03, 0.005, -0.07], r: [-2, 10, 8], w: [0, -4, 4] }, 'in'],          // the cut, mid-arc (fastest)
  [0.27, { p: [-0.15, -0.04, -0.05], r: [-8, 38, 26], w: [22, -22, 16] }, 'out'],    // follow-through
  [0.36, { p: [-0.16, -0.05, -0.04], r: [-9, 41, 29], w: [25, -24, 18] }],           // the beat
  [0.66, {}],                                                                         // recovery
];
const SWING_KEYS = [   // a club (bat, pan, poker): big wind-up over the shoulder, a heavy sweep
  [0.0, {}],
  [0.16, { p: [0.12, 0.14, 0.06], r: [30, -40, -50] }, 'out'],
  [0.33, { p: [-0.25, -0.08, -0.15], r: [-20, 55, 40] }, 'in'],
  [0.4, { p: [-0.27, -0.1, -0.13], r: [-22, 58, 42] }],
  [0.85, {}],
];
const SWING_SWEEP = { t0: 0.2, t1: 0.36, from: [40, 12], to: [-45, -10] };

export const WEAPONS = {
  kitchen_knife: {
    id: 'kitchen_knife', kind: 'melee', name: "Chef's knife",
    // the view model (camera space, m): the grip (the handle's centre) at `pos`, the forearm leaving
    // the wrist along `arm`, the back of the hand toward `back`; `wrist` = the guard's wrist bend
    // [flex, deviation, twist] deg; `run` = the pose added while running
    hold: { pos: [0.13, -0.108, -0.33], arm: [0.38, -0.5, 0.78], back: [0.28, 0.75, 0.6], wrist: [0, 3, 0], gripRadius: 0.0115 },
    // one attack, Enter: the slash. 55 a hit (two kill), up to 2 targets in its arc
    attack: { name: 'slash', damage: 55, range: 1.25, maxTargets: 2, duration: 0.66, cooldown: 0.62, keys: SLASH_KEYS,
      sweep: { t0: 0.15, t1: 0.27, from: [34, 9], to: [-42, -11] }, swingSfxAt: 0.12, view: [-0.5, 1.1, 0.9] },
    // the same slash from behind an unaware target (combat.canTakedown): it dies outright
    takedown: { damage: 100, range: 1.3, arc: 60 },
    hitStop: 0.075,            // the view model holds still for this long on a hit (0.13 takedown)
    kick: 0.9,                 // the view's jolt on a hit (degrees)
    noise: 0.6,                // a hit's noise (window.__noise); swings are silent
    reach: 0.9,                // a wall or counter nearer than this in the blade's path stops it (a clink)
    sfx: { swing: 'knife_swing', hit: 'knife_hit', wall: 'knife_wall', takedown: 'knife_takedown' },
  },

  // ---- more melee weapons: data only, until their assets exist (a pickup with `weapon: '<id>'`)
  bat: {
    id: 'bat', kind: 'melee', name: 'Baseball bat',
    hold: { pos: [0.24, -0.26, -0.42], aim: [-0.35, 0.75, -0.55], back: [1, 0.2, 0.4], gripRadius: 0.015 },
    attack: { name: 'swing', damage: 35, range: 1.7, maxTargets: 2, duration: 0.85, cooldown: 0.95, keys: SWING_KEYS, sweep: SWING_SWEEP },
    hitStop: 0.11, kick: 1.8, noise: 0.9,
    sfx: { swing: 'bat_swing', hit: 'bat_hit', wall: 'bat_hit' },
  },
  frying_pan: {
    id: 'frying_pan', kind: 'melee', name: 'Frying pan',
    hold: { pos: [0.22, -0.24, -0.4], aim: [-0.3, 0.6, -0.75], back: [1, 0.3, 0.3], gripRadius: 0.012 },
    attack: { name: 'swing', damage: 30, range: 1.45, duration: 0.8, cooldown: 0.9, keys: SWING_KEYS, sweep: SWING_SWEEP },
    hitStop: 0.1, kick: 1.5, noise: 1.1,              // a pan rings out
    sfx: { swing: 'bat_swing', hit: 'pan_hit', wall: 'pan_hit' },
  },
  fireplace_poker: {
    id: 'fireplace_poker', kind: 'melee', name: 'Fireplace poker',
    hold: { pos: [0.22, -0.24, -0.4], aim: [-0.25, 0.55, -0.8], back: [1, 0.3, 0.3], gripRadius: 0.009 },
    attack: { name: 'swing', damage: 40, range: 1.6, duration: 0.8, cooldown: 0.9, keys: SWING_KEYS, sweep: SWING_SWEEP },
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
const D = THREE.MathUtils.degToRad;

export class Weapons {
  // combat: viewer/combat.js; player: viewer/player.js; vitals: the player's PlayerVitals (its target)
  constructor({ combat, camera, inventory, player, noise = null, baked = null, culler = null, level = null, load = null,
    canAct = () => true, hidden = () => false }) {
    Object.assign(this, { combat, camera, inventory, player, noise, baked, culler, level, canAct, hidden });
    this.known = new Set();   // weapon ids seen in the inventory (a new one is armed on pickup)
    this.vm = new ViewModel(camera, { load });   // load(url) -> gltf: the arm asset (viewmodel_arm.gltf)
    this.id = null;
    this.def = null;
    this.cooldown = 0;
    this.pending = null;      // the attack waiting for its hit frame
    this.lastLook = camera.quaternion.clone();
    this.attacks = 0;         // counters (tests)
    this.ammo = {};           // guns: rounds in the magazine per weapon id
    this.recoil = new THREE.Vector2();
    this.viewKick = new THREE.Vector2();
    // (no mouse buttons: Enter attacks, index.html useArmed -> attack())
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

  // the target a takedown would kill now (an unaware one in reach, the player behind it): the
  // prompt under the crosshair says so and the crosshair turns gold
  target() {
    const me = this.player_target;
    const td = this.def?.takedown;
    if (!me || !td || this.def.kind !== 'melee') return null;
    const eye = this.camera.position, fwd = this.camera.getWorldDirection(_dir);
    for (const t of this.combat.living((t) => t.team !== me.team)) {
      const p = t.position();
      const c = new THREE.Vector3(p.x, THREE.MathUtils.clamp(eye.y, p.y + 0.3, p.y + t.height - 0.2), p.z);
      const to = c.sub(eye), d = to.length();
      if (d - t.radius > td.range) continue;
      if (to.normalize().dot(fwd) < Math.cos(D(td.arc / 2 + 10))) continue;
      if (this.combat.canTakedown(t, me) && this.combat.lineOfSight(eye, p.clone().setY(eye.y))) return t;
    }
    return null;
  }
  hint() {
    if (!this.def) return null;
    if (this.def.kind === 'gun') return `Fire${this.ammo[this.def.id] ? '' : ' · empty'}`;
    if (this.target()) return 'Takedown';
    return cap(this.def.attack.name);
  }

  // Enter: the armed weapon's one attack (a gun fires). From behind an unaware target the same
  // swing is a takedown (marked now, killed when the blade's sweep reaches it)
  attack() {
    const def = this.def;
    if (!def || this.cooldown > 0 || this.pending || this.player.isDown || !this.canAct()) return false;
    if (def.kind === 'gun') return this.fire();
    const me = this.player_target;
    const a = def.attack;
    const victim = def.takedown ? this.target() : null;
    this.attacks++;
    this.cooldown = a.cooldown;
    this.vm.play({ duration: a.duration, keys: a.keys, trail: a.sweep });
    this.pending = { a, t: 0, u: 0, victim, me, hit: new Set(), hits: [], wall: null, view: this.camera.quaternion.clone() };
    sfx(def.sfx?.swing, null, { delay: Math.max(0, a.swingSfxAt ?? a.sweep.t0 - 0.03) });
    return true;
  }

  // the blade's direction in the view at sweep progress u (0..1): yaw / pitch off the view's
  // centre (+ = right / up), eased like the arm (fast through the middle)
  sweepDir(sw, u, q, out = new THREE.Vector3()) {
    const k = u * u * (3 - 2 * u);
    const yaw = sw.from[0] + (sw.to[0] - sw.from[0]) * k, pitch = sw.from[1] + (sw.to[1] - sw.from[1]) * k;
    return out.set(Math.sin(D(yaw)) * Math.cos(D(pitch)), Math.sin(D(pitch)), -Math.cos(D(yaw)) * Math.cos(D(pitch))).applyQuaternion(q);
  }

  // one frame of the swing's sweep: the arc from the last step to this one is a melee cone.
  // The view's turn during the swing carries the arc with it (q = the camera now)
  sweep(p) {
    const { a, me } = p, def = this.def, sw = a.sweep;
    const u = THREE.MathUtils.clamp((p.t - sw.t0) / (sw.t1 - sw.t0), 0, 1);
    if (u <= p.u || p.wall) return;
    const q = this.camera.quaternion, origin = this.camera.position.clone();
    const d0 = this.sweepDir(sw, p.u, q), d1 = this.sweepDir(sw, u, q);
    const dir = d0.clone().add(d1).normalize();
    const step = THREE.MathUtils.radToDeg(d0.angleTo(d1));
    const left = (a.maxTargets ?? 1) - p.hits.length;
    let hits = [];
    // the marked takedown: killed when the blade reaches it, whatever its health
    const v = p.victim;
    if (v && !p.hit.has(v)) {
      const at = v.position().clone().setY(origin.y - 0.15);
      const to = at.clone().sub(origin).normalize();
      const right = new THREE.Vector3(1, 0, 0).applyQuaternion(q), fwd = new THREE.Vector3(0, 0, -1).applyQuaternion(q);
      const yaw = THREE.MathUtils.radToDeg(Math.atan2(to.dot(right), to.dot(fwd)));
      const yNow = sw.from[0] + (sw.to[0] - sw.from[0]) * (u * u * (3 - 2 * u));
      if ((yNow <= yaw || u >= 1) && v.alive && this.combat.canTakedown(v, me)) {
        p.hit.add(v);
        const r = this.combat.hit(v, Math.max(def.takedown.damage, v.health), {
          from: me, dir: to.clone().setY(0).normalize(), weapon: def.id, part: 'body', point: at, stealth: true, kind: 'melee' });
        if (r) hits.push({ target: v, point: at, damage: r.damage, part: 'body', stealth: true, killed: r.killed });
      }
    }
    if (left > hits.length) {
      hits = hits.concat(this.combat.attack({ from: me, origin, dir, weapon: def, range: a.range, arc: step + 2 * (a.width ?? 9),
        damage: a.damage, takedown: def.takedown?.damage ?? 0, maxTargets: left - hits.length, exclude: p.hit, quiet: true }));
    }
    p.u = u;
    if (hits.length) {
      for (const h of hits) p.hit.add(h.target);
      const first = !p.hits.length;
      p.hits.push(...hits);
      const at = hits[0].point, stealth = hits.some((h) => h.stealth);
      sfx(stealth ? def.sfx?.takedown ?? def.sfx?.hit : def.sfx?.hit, at);
      this.noise?.emit({ position: at.clone(), loudness: stealth ? def.noise * 0.5 : def.noise, source: 'melee', weapon: def.id });
      // hit stop: the arm holds on contact (the first one longest), the view jolts
      this.vm.freeze(stealth ? 0.13 : first ? def.hitStop : def.hitStop * 0.5);
      this.viewKick.set((Math.random() - 0.5) * def.kick, def.kick * (stealth ? 1.4 : 1));
      return;
    }
    // the blade meets a wall or a counter in its path before any target: a clink, it stops
    if (!p.hits.length && def.reach) {
      const wall = this.combat.raycast(origin, d1, def.reach);
      if (wall) {
        p.wall = wall;
        sfx(def.sfx?.wall, wall.point);
        this.vm.freeze(def.hitStop * 0.8);
        this.vm.bounce?.();
        this.viewKick.set(0, def.kick * 0.4);
        this.noise?.emit({ position: wall.point.clone(), loudness: 0.3, source: 'melee_wall', weapon: def.id });
      }
    }
  }

  // the swing is over: one 'attack' event with everything it hit
  endSwing(p) {
    this.lastHits = p.hits;
    this.combat.emit('attack', { from: p.me, origin: this.camera.position.clone(), dir: this.camera.getWorldDirection(new THREE.Vector3()),
      weapon: this.def?.id, hits: p.hits, takedown: p.hits.some((h) => h.stealth), wall: !!p.wall });
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
    // the body goes with a swing: the view leans a degree or so the way the blade travels (the
    // attack's `view`: [pitch, yaw, roll] deg at the cut's middle, a bell over the sweep)
    const vm = this.vm, a = this.def?.attack, sv = a?.view;
    let sp = 0, sy = 0, sr = 0;
    if (sv && vm.clip?.trail && !vm.scrubbing && !window.__bench) {
      const sw = a.sweep, mid = (sw.t0 + sw.t1) / 2, w = (sw.t1 - sw.t0) * 0.9;
      const g = Math.exp(-(((vm.clipT - mid) / w) ** 2));
      sp = sv[0] * g; sy = sv[1] * g; sr = sv[2] * g;
    }
    const pitch = THREE.MathUtils.degToRad(k.y + r.y + sp), yaw = THREE.MathUtils.degToRad(k.x + r.x + sy), roll = THREE.MathUtils.degToRad(sr);
    k.multiplyScalar(Math.max(0, 1 - dt * 14));
    r.multiplyScalar(Math.max(0, 1 - dt * (this.def?.recoil?.recover ?? 9)));
    if (Math.abs(pitch) + Math.abs(yaw) + Math.abs(roll) < 1e-5 || this.player.isDown) return;
    this._applied = new THREE.Quaternion().setFromEuler(new THREE.Euler(pitch, yaw, roll, 'YXZ'));
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
      this.sweep(p);
      if (p.t >= p.a.sweep.t1 || p.wall) { this.pending = null; this.endSwing(p); }
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
