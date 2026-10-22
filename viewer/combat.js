import * as THREE from 'three';

// Combat: who can be hurt, melee sweeps, hitscan shots, and the events the HUD, sound and AI
// listen to. One instance per level, `window.__combat` (index.html). Contract: prompts/wave2.md
// "Combat contract"; design notes: design/combat.md.
//
//   window.__combat
//     .targets                      every registered target (alive or dead)
//     .register(target) -> target   a target is
//         { id, kind: 'player'|'invader'|'dummy', team, position() -> Vector3 (feet centre),
//           radius, height, health, maxHealth, alive, hit(damage, info) }
//       optional:
//         facing() -> Vector3       horizontal unit vector it looks along (needed for takedowns)
//         aware                     bool, or fn(attacker) -> bool: does it know the attacker is
//                                   there? An unaware target hit from behind by a weapon with a
//                                   `takedown` damage dies outright (the stealth takedown)
//         parts                     { head: k, body: k, legs: k } damage multipliers for shots
//       target.hit(damage, info) applies the damage to itself (health -= damage, alive = false at
//       0, its own stagger / call-out / ragdoll) and may return the damage it took (armour);
//       combat reads `health` / `alive` afterwards and raises the events. `makeTarget(opts)`
//       builds a standard one. info = { from, dir, weapon, part, point, stealth, kind: 'melee'|'shot' }
//     .unregister(target | id)
//     .get(id)
//     .hit(target, damage, info) -> { target, damage, killed } | null
//                                   damage through target.hit + events (anything can call it:
//                                   a fall, a fire, an explosion)
//     .attack({ from, origin, dir, weapon, range, arc, damage, takedown, maxTargets, height })
//                                   melee sweep -> [{ target, point, damage, part, stealth, killed }]
//                                   from = the attacker's target (or id; null = the world)
//                                   origin = Vector3 (the attacker's eye / shoulder), dir = unit
//                                   aim; range m (to the target's surface), arc = full cone in
//                                   degrees; takedown = damage from behind an unaware target
//                                   (default: weapon.takedown); maxTargets default 1
//     .shoot({ from, origin, dir, spread, range, damage, weapon, pellets })
//                                   hitscan vs the level's colliders (window.__colliders: walls,
//                                   props, glass; `seeThrough` rails / boundaries are passed) and
//                                   the targets -> { target, point, normal, distance, part, wall,
//                                   glass, killed, dir } (pellets > 1: an array, one per pellet).
//                                   Emits `shot` (for tracers, impacts, noise: the shooter emits
//                                   its own gunshot noise, combat doesn't, so a silenced weapon
//                                   can stay quiet)
//     .canTakedown(target, from) -> bool
//     .lineOfSight(a, b) -> bool    no wall / prop between two points (glass blocks; seeThrough doesn't)
//     .raycast(origin, dir, range) -> { point, normal, distance, box } | null   (walls only)
//     .on(event, fn) -> off()       events:
//         'hit'        { target, damage, from, weapon, part, point, dir, stealth, kind, killed }
//         'kill'       { target, from, weapon, stealth }
//         'shot'       { from, origin, dir, point, target, wall, glass, distance, weapon }
//         'attack'     { from, origin, dir, weapon, hits }   (every swing, hit or miss)
//         'playerDown' { target, from, weapon }               (the player's health reached 0)
//     .lastCombat(id) -> seconds since that target last dealt or took damage (regeneration)

const _v = new THREE.Vector3(), _w = new THREE.Vector3(), _ray = new THREE.Ray(), _hit = new THREE.Vector3();
const DEG = Math.PI / 180;

export class Combat {
  constructor({ colliders = null } = {}) {
    this._colliders = colliders;
    this.targets = [];
    this.handlers = {};
    this.time = 0;
    this._last = new Map();      // target id -> time of its last fight (gave or took damage)
  }

  get colliders() { return this._colliders || window.__colliders || []; }
  set colliders(c) { this._colliders = c; }

  // ------------------------------------------------------------------ targets
  register(t) {
    if (!t || t.id == null) throw new Error('combat.register: a target needs an id');
    this.unregister(t.id);
    t.kind ??= 'invader';
    t.team ??= t.kind === 'player' ? 'player' : 'invaders';
    t.maxHealth ??= 100;
    t.health ??= t.maxHealth;
    t.alive ??= t.health > 0;
    t.radius ??= 0.3;
    t.height ??= 1.8;
    this.targets.push(t);
    return t;
  }
  unregister(t) {
    const id = typeof t === 'object' ? t?.id : t;
    const i = this.targets.findIndex((x) => x.id === id);
    if (i >= 0) this.targets.splice(i, 1);
  }
  get(id) { return typeof id === 'object' ? id : this.targets.find((t) => t.id === id) ?? null; }
  living(filter = () => true) { return this.targets.filter((t) => t.alive && filter(t)); }

  on(event, fn) {
    (this.handlers[event] ??= []).push(fn);
    return () => { const l = this.handlers[event]; const i = l.indexOf(fn); if (i >= 0) l.splice(i, 1); };
  }
  emit(event, data) {
    for (const fn of (this.handlers[event] || []).slice()) {
      try { fn(data); } catch (e) { console.error(`combat '${event}' handler`, e); }
    }
    for (const fn of (this.handlers['*'] || []).slice()) {
      try { fn(event, data); } catch (e) { console.error('combat * handler', e); }
    }
  }

  update(dt) { this.time += dt; }
  lastCombat(id) { const t = this._last.get(typeof id === 'object' ? id?.id : id); return t == null ? Infinity : this.time - t; }

  // ------------------------------------------------------------------ damage
  hit(target, damage, info = {}) {
    target = this.get(target);
    if (!target || !target.alive || !(damage > 0)) return null;
    const from = info.from != null ? this.get(info.from) : null;
    const before = target.health;
    const r = target.hit(damage, { ...info, from });
    // a target whose hit() doesn't keep its own health: combat does it
    if (target.health === before && typeof r !== 'number' && r !== false) {
      target.health = Math.max(0, before - damage);
      if (target.health <= 0) target.alive = false;
    }
    const taken = typeof r === 'number' ? r : before - target.health;
    if (target.health <= 0 && target.alive) target.alive = false;
    const killed = !target.alive;
    this._last.set(target.id, this.time);
    if (from) this._last.set(from.id, this.time);
    const ev = { target, damage: taken, from, weapon: info.weapon ?? null, part: info.part ?? 'body', point: info.point ?? null,
      dir: info.dir ?? null, stealth: !!info.stealth, kind: info.kind ?? 'melee', killed };
    this.emit('hit', ev);
    if (killed) {
      this.emit('kill', { target, from, weapon: ev.weapon, stealth: ev.stealth });
      if (target.kind === 'player') this.emit('playerDown', { target, from, weapon: ev.weapon });
    }
    return { target, damage: taken, killed };
  }

  // ------------------------------------------------------------------ melee
  // An unaware target, attacked from behind (the attacker within ~110 deg of straight behind it)
  canTakedown(target, from) {
    target = this.get(target); from = this.get(from);
    if (!target?.alive || !from || typeof target.facing !== 'function') return false;
    const aware = typeof target.aware === 'function' ? target.aware(from) : target.aware;
    if (aware !== false) return false;              // unknown awareness counts as aware
    const f = target.facing();
    _v.copy(from.position()).sub(target.position()).setY(0);
    if (_v.lengthSq() < 1e-6) return false;
    _v.normalize();
    return f.x * _v.x + f.z * _v.z < -0.34;          // behind: more than ~110 deg off its facing
  }

  attack({ from = null, origin, dir, weapon = null, range = weapon?.range ?? 1.4, arc = weapon?.arc ?? 60,
    damage = weapon?.damage ?? 25, takedown = weapon?.takedown ?? 0, maxTargets = weapon?.maxTargets ?? 1,
    height = 0.6 } = {}) {
    from = from != null ? this.get(from) : null;
    const aim = _w.copy(dir).normalize().clone();
    const cosHalf = Math.cos((arc / 2) * DEG);
    const cands = [];
    for (const t of this.targets) {
      if (!t.alive || t === from || (from && t.team === from.team && !weapon?.friendly)) continue;
      const p = t.position();
      // nearest point of the target's vertical axis to the swing's origin (clamped to its body)
      const y = THREE.MathUtils.clamp(origin.y, p.y + Math.min(t.radius, t.height / 2), p.y + t.height - Math.min(t.radius, t.height / 2));
      const c = new THREE.Vector3(p.x, y, p.z);
      const to = c.clone().sub(origin);
      const dist = to.length();
      if (dist - t.radius > range) continue;
      if (Math.abs(origin.y - y) > height + t.radius) continue;
      // inside the cone, measured to the body's near edge (a wide body is easier to clip)
      const dirTo = dist > 1e-4 ? to.clone().divideScalar(dist) : aim.clone();
      const edge = Math.atan2(t.radius, Math.max(dist, 1e-3));
      const angle = Math.acos(THREE.MathUtils.clamp(dirTo.dot(aim), -1, 1));
      if (Math.cos(Math.max(0, angle - edge)) < cosHalf && dist > t.radius) continue;
      if (!this.lineOfSight(origin, c)) continue;
      const point = dist > t.radius ? origin.clone().addScaledVector(dirTo, dist - t.radius) : c.clone();
      cands.push({ t, dist, point, dirTo });
    }
    cands.sort((a, b) => a.dist - b.dist);
    const hits = [];
    for (const { t, point, dirTo } of cands.slice(0, maxTargets)) {
      const stealth = takedown > 0 && this.canTakedown(t, from);
      const part = partAt(t, point.y);
      const r = this.hit(t, stealth ? Math.max(takedown, damage) : damage, {
        from, dir: dirTo.clone().setY(0).normalize(), weapon: weapon?.id ?? weapon, part, point, stealth, kind: 'melee' });
      if (r) hits.push({ target: t, point, damage: r.damage, part, stealth, killed: r.killed });
    }
    this.emit('attack', { from, origin: origin.clone(), dir: aim, weapon: weapon?.id ?? weapon, hits });
    return hits;
  }

  // ------------------------------------------------------------------ hitscan
  shoot({ from = null, origin, dir, spread = 0, range = 80, damage = 30, weapon = null, pellets = 1 } = {}) {
    if (pellets > 1) {
      const out = [];
      for (let i = 0; i < pellets; i++) out.push(this.shoot({ from, origin, dir, spread, range, damage, weapon, pellets: 1 }));
      return out;
    }
    from = from != null ? this.get(from) : null;
    const d = jitter(dir.clone().normalize(), spread);
    const wall = this.raycast(origin, d, range);
    let best = null;
    for (const t of this.targets) {
      if (!t.alive || t === from || (from && t.team === from.team)) continue;
      const s = rayCylinder(origin, d, t);
      if (s != null && s <= range && (!best || s < best.s)) best = { t, s };
    }
    let res;
    if (best && (!wall || best.s < wall.distance)) {
      const point = origin.clone().addScaledVector(d, best.s);
      const part = partAt(best.t, point.y);
      const k = best.t.parts?.[part] ?? 1;
      const r = this.hit(best.t, damage * k, { from, dir: d.clone(), weapon: weapon?.id ?? weapon, part, point, kind: 'shot' });
      res = { target: best.t, point, normal: d.clone().negate(), distance: best.s, part, wall: false, glass: false, killed: !!r?.killed, dir: d };
    } else if (wall) {
      res = { target: null, point: wall.point, normal: wall.normal, distance: wall.distance, part: null, wall: true, glass: !!wall.box.glass, killed: false, dir: d };
    } else {
      res = { target: null, point: origin.clone().addScaledVector(d, range), normal: null, distance: range, part: null, wall: false, glass: false, killed: false, dir: d };
    }
    if (from) this._last.set(from.id, this.time);
    this.emit('shot', { from, origin: origin.clone(), dir: d, point: res.point, target: res.target, wall: res.wall, glass: res.glass, distance: res.distance, weapon: weapon?.id ?? weapon });
    return res;
  }

  // nearest wall / prop / glass along a ray (seeThrough boxes and boxes the origin is inside skipped)
  raycast(origin, dir, range = 100) {
    _ray.set(origin, dir);
    let best = null;
    for (const c of this.colliders) {
      if (c.seeThrough) continue;
      if (c.containsPoint(origin)) continue;
      // cheap reject: the box's distance from the origin
      if (c.distanceToPoint(origin) > range) continue;
      if (!_ray.intersectBox(c, _hit)) continue;
      const s = _hit.distanceTo(origin);
      if (s <= range && (!best || s < best.distance)) best = { point: _hit.clone(), distance: s, box: c };
    }
    if (best) best.normal = boxNormal(best.point, best.box);
    return best;
  }

  lineOfSight(a, b) {
    _v.copy(b).sub(a);
    const len = _v.length();
    if (len < 1e-4) return true;
    const hit = this.raycast(a, _v.divideScalar(len).clone(), len);
    return !hit || hit.distance >= len - 0.05;
  }
}

// a standard target (a dummy, a test, a simple prop): health, death, callbacks
export function makeTarget({ id, kind = 'dummy', team = 'invaders', position, radius = 0.3, height = 1.8,
  maxHealth = 100, health = maxHealth, facing = null, aware = undefined, parts = null, onHit = null, onDeath = null } = {}) {
  const t = {
    id, kind, team, radius, height, maxHealth, health, alive: health > 0, parts,
    position: typeof position === 'function' ? position : () => position.clone(),
    hit(damage, info) {
      if (!t.alive) return 0;
      const before = t.health;
      t.health = Math.max(0, t.health - damage);
      if (t.health <= 0) t.alive = false;
      onHit?.(t, damage, info);
      if (!t.alive) onDeath?.(t, info);
      return before - t.health;
    },
  };
  if (facing) t.facing = facing;
  if (aware !== undefined) t.aware = aware;
  return t;
}

// head / body / legs by height on the target
function partAt(t, y) {
  const h = (y - t.position().y) / t.height;
  return h > 0.84 ? 'head' : h < 0.45 ? 'legs' : 'body';
}

// ray vs a vertical cylinder standing on the target's feet: distance along the ray or null
function rayCylinder(o, d, t) {
  const p = t.position(), r = t.radius, y0 = p.y, y1 = p.y + t.height;
  const ox = o.x - p.x, oz = o.z - p.z;
  const a = d.x * d.x + d.z * d.z, b = 2 * (ox * d.x + oz * d.z), c = ox * ox + oz * oz - r * r;
  let best = null;
  if (a > 1e-9) {
    const disc = b * b - 4 * a * c;
    if (disc >= 0) {
      const sq = Math.sqrt(disc);
      for (const s of [(-b - sq) / (2 * a), (-b + sq) / (2 * a)]) {
        if (s < 0) continue;
        const y = o.y + d.y * s;
        if (y >= y0 && y <= y1) { best = s; break; }
      }
    }
  }
  // the caps (shooting down at the top of a head, or from below)
  if (Math.abs(d.y) > 1e-6) for (const yc of [y0, y1]) {
    const s = (yc - o.y) / d.y;
    if (s < 0 || (best != null && s >= best)) continue;
    const x = ox + d.x * s, z = oz + d.z * s;
    if (x * x + z * z <= r * r) best = s;
  }
  return best;
}

function jitter(d, spreadDeg) {
  if (!(spreadDeg > 0)) return d;
  // uniform inside a cone of half-angle spread/2
  const half = (spreadDeg / 2) * DEG;
  const cos = 1 - Math.random() * (1 - Math.cos(half)), sin = Math.sqrt(1 - cos * cos), phi = Math.random() * Math.PI * 2;
  const up = Math.abs(d.y) < 0.99 ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(1, 0, 0);
  const u = new THREE.Vector3().crossVectors(d, up).normalize(), v = new THREE.Vector3().crossVectors(d, u);
  return d.clone().multiplyScalar(cos).addScaledVector(u, sin * Math.cos(phi)).addScaledVector(v, sin * Math.sin(phi)).normalize();
}

function boxNormal(p, b) {
  const d = [
    [p.x - b.min.x, -1, 0, 0], [b.max.x - p.x, 1, 0, 0], [p.y - b.min.y, 0, -1, 0],
    [b.max.y - p.y, 0, 1, 0], [p.z - b.min.z, 0, 0, -1], [b.max.z - p.z, 0, 0, 1],
  ].sort((a, c) => Math.abs(a[0]) - Math.abs(c[0]))[0];
  return new THREE.Vector3(d[1], d[2], d[3]);
}
