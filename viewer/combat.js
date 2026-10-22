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
//         facing() -> Vector3 | yaw horizontal unit vector it looks along, or its yaw in radians
//                                   (direction (sin, 0, cos)); needed for takedowns
//         aware / unaware           bool, or fn(attacker) -> bool: does it know the attacker is
//                                   there? An unaware target hit from behind by a weapon with a
//                                   `takedown` damage dies outright (the stealth takedown).
//                                   Neither given = aware (no takedowns)
//       `alive` may be a getter (combat then never sets it; health <= 0 must make it false)
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
//                                   (knife) exclude = a Set of targets to skip (already hit by this
//                                   swing: a slash sweeps in steps), quiet = no 'attack' event
//                                   (the swing emits one itself when it ends)
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
    t.team ??= t.kind === 'player' ? 'player' : 'invader';
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
      if (target.health <= 0) setDead(target);
    }
    const taken = typeof r === 'number' ? r : before - target.health;
    if (target.health <= 0 && target.alive) setDead(target);
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
    // aware (bool | fn(attacker)) or unaware (bool | fn(attacker)); unknown counts as aware
    const aware = target.unaware !== undefined
      ? !(typeof target.unaware === 'function' ? target.unaware(from) : target.unaware)
      : typeof target.aware === 'function' ? target.aware(from) : target.aware;
    if (aware !== false) return false;
    let f = target.facing();
    if (typeof f === 'number') f = { x: Math.sin(f), z: Math.cos(f) };   // a yaw (radians, 0 = +z)
    _v.copy(from.position()).sub(target.position()).setY(0);
    if (_v.lengthSq() < 1e-6) return false;
    _v.normalize();
    return f.x * _v.x + f.z * _v.z < -0.34;          // behind: more than ~110 deg off its facing
  }

  attack({ from = null, origin, dir, weapon = null, range = weapon?.range ?? 1.4, arc = weapon?.arc ?? 60,
    damage = weapon?.damage ?? 25, takedown = weapon?.takedown ?? 0, maxTargets = weapon?.maxTargets ?? 1,
    height = 0.6, exclude = null, quiet = false } = {}) {
    from = from != null ? this.get(from) : null;
    const aim = _w.copy(dir).normalize().clone();
    const cosHalf = Math.cos((arc / 2) * DEG);
    const cands = [];
    for (const t of this.targets) {
      if (!t.alive || t === from || (from && t.team === from.team && !weapon?.friendly)) continue;
      if (exclude?.has(t)) continue;            // (knife) already hit by this swing
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
    if (!quiet) this.emit('attack', { from, origin: origin.clone(), dir: aim, weapon: weapon?.id ?? weapon, hits });
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

  // nearest wall / prop / glass along a ray. Skipped: seeThrough boxes (rails, boundaries), boxes
  // the origin is inside, and characters' own boxes: a Box3 a target pushes into the colliders
  // should carry `owner` = the target (the fast path); an untagged box round a living target's
  // middle is recognised too. Rays meet the target's cylinder instead.
  raycast(origin, dir, range = 100) {
    _ray.set(origin, dir);
    let best = null;
    for (const c of this.colliders) {
      if (c.seeThrough || c.owner) continue;
      if (c.containsPoint(origin)) continue;
      // cheap reject: the box's distance from the origin
      if (c.distanceToPoint(origin) > range) continue;
      if (!_ray.intersectBox(c, _hit)) continue;
      const s = _hit.distanceTo(origin);
      if (s <= range && (!best || s < best.distance) && !this.bodyBox(c)) best = { point: _hit.clone(), distance: s, box: c };
    }
    if (best) best.normal = boxNormal(best.point, best.box);
    return best;
  }

  // is this collider a character's (it holds a living target's mid-body point)?
  bodyBox(c) {
    for (const t of this.targets) {
      if (!t.alive) continue;
      const p = t.position();
      _v.set(p.x, p.y + t.height / 2, p.z);
      if (c.containsPoint(_v) && c.max.x - c.min.x < 2 * t.radius + 0.6 && c.max.z - c.min.z < 2 * t.radius + 0.6) return true;
    }
    return false;
  }

  lineOfSight(a, b) {
    _v.copy(b).sub(a);
    const len = _v.length();
    if (len < 1e-4) return true;
    const hit = this.raycast(a, _v.divideScalar(len).clone(), len);
    return !hit || hit.distance >= len - 0.05;
  }
}

// alive = false, also on a target whose `alive` is a getter (it then keeps its own state)
function setDead(t) {
  try { t.alive = false; } catch { /* read-only: the target decides */ }
}

// a standard target (a dummy, a test, a simple prop): health, death, callbacks
export function makeTarget({ id, kind = 'dummy', team = 'invader', position, radius = 0.3, height = 1.8,
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

// ------------------------------------------------------------------ the player's health
// The player as a combat target, the damage feedback and death. No numbers, no bars:
//   a red edge vignette (a flash per hit, a slow pulse while badly hurt), a wedge at the edge of
//   the view pointing at where the hit came from, the view jolts away from it, heavy breathing at
//   low health; out of combat (no damage taken or dealt for `regenDelay` s) health comes back
//   slowly. At 0: the player falls (an endless knockdown), the screen fades to black and one
//   button restarts the run (reloads the page). ?god=1: hits show but never kill (playtesting).
//
//   const vitals = new PlayerVitals({ combat, player, camera })
//   vitals.target          the player's combat target (id 'player')
//   vitals.update(dt)      each frame; vitals.beginView() / endView(dt) around the frame's
//                          camera work (the jolt is an offset taken off again next frame)
export class PlayerVitals {
  constructor({ combat, player, camera, maxHealth = 100, regenDelay = 7, regenRate = 3.5, god = false }) {
    Object.assign(this, { combat, player, camera, regenDelay, regenRate, god });
    this.dead = false;
    this.flash = 0;            // the vignette's hit flash (0..1)
    this.indicators = [];      // { el, from: Vector3 | null, dir, t }
    this.kick = { pitch: 0, roll: 0 };
    this._applied = null;
    this.deathT = 0;
    const self = this;
    this.target = combat.register({
      id: 'player', kind: 'player', team: 'player', radius: 0.3, maxHealth, health: maxHealth, alive: true,
      get height() { return player.height ?? 1.8; },
      position: () => player.pos.clone(),
      facing: () => { const d = camera.getWorldDirection(new THREE.Vector3()); d.y = 0; return d.normalize(); },
      aware: true,
      hit(damage, info) { return self.onHit(damage, info); },
    });
    this.ui();
  }

  get health() { return this.target.health; }
  heal(n) { if (!this.dead) this.target.health = Math.min(this.target.maxHealth, this.target.health + n); }

  onHit(damage, info = {}) {
    const t = this.target;
    if (this.dead) return 0;
    const before = t.health;
    t.health = Math.max(this.god ? 1 : 0, t.health - damage);
    if (t.health <= 0) t.alive = false;
    // where it came from: the attacker's position, else the blow's direction reversed
    const from = info.from?.position ? info.from.position() : null;
    const dir = from ? from.clone().sub(this.player.pos).setY(0).normalize()
      : info.dir ? info.dir.clone().negate().setY(0).normalize() : null;
    this.flash = Math.min(1, this.flash + 0.35 + damage / 60);
    if (dir) this.indicate(dir, from);
    // the jolt: up and rolled away from the side it came from
    const side = dir ? this.sideOf(dir) : 1;
    this.kick.pitch += THREE.MathUtils.degToRad(1.5 + damage * 0.12);
    this.kick.roll += THREE.MathUtils.degToRad(1 + damage * 0.1) * -side;
    sfxPlay('player_hurt', null);
    if (!t.alive) this.die(from, dir);
    return before - t.health;
  }

  // +1 = the hit came from the player's right, -1 = the left
  sideOf(dir) {
    const f = this.camera.getWorldDirection(new THREE.Vector3()).setY(0).normalize();
    return f.x * dir.z - f.z * dir.x < 0 ? -1 : 1;
  }

  indicate(dir, from) {
    const el = document.createElement('div');
    el.className = 'cb-ind';
    this.indEl.appendChild(el);
    this.indicators.push({ el, dir: dir.clone(), from: from?.clone() ?? null, t: 0 });
    if (this.indicators.length > 4) this.indicators.shift().el.remove();
  }

  die(from, dir) {
    this.dead = true;
    this.deathT = 0;
    const at = from ?? (dir ? this.player.pos.clone().add(dir) : null);
    if (this.player.down) this.player.down.duration = Infinity;      // already on the floor: stays there
    else this.player.knockDown(at, { duration: Infinity, shove: 2.2, roll: 84 });
    this.player.dead = true;
    sfxPlay('body_fall', null, { delay: 0.35 });
    this.deathEl.classList.add('on');
    // nothing else on screen: the HUD (prompts, crosshair, inventory, the dev links) goes
    document.body.classList.add('cb-dead');
  }

  restart() { location.reload(); }

  ui() {
    if (!document.getElementById('cb-style')) {
      const st = document.createElement('style');
      st.id = 'cb-style';
      st.textContent = `
        #cb-vig { position: absolute; inset: 0; pointer-events: none; opacity: 0;
          background: radial-gradient(ellipse at center, rgba(120,0,0,0) 52%, rgba(120,0,0,.42) 78%, rgba(70,0,0,.85) 100%); }
        #cb-ind { position: absolute; left: 50%; top: 50%; width: 0; height: 0; pointer-events: none; }
        .cb-ind { position: absolute; left: -70px; top: -230px; width: 140px; height: 60px; transform-origin: 70px 230px;
          background: radial-gradient(ellipse at 50% 100%, rgba(200,20,10,.75), rgba(200,20,10,0) 70%);
          clip-path: polygon(0 100%, 50% 0, 100% 100%, 50% 78%); }
        #cb-death { position: absolute; inset: 0; display: none; align-items: center; justify-content: center;
          background: #000; opacity: 0; transition: opacity 2.4s ease-in; }
        #cb-death.on { display: flex; }
        body.cb-dead > :not(canvas):not(#cb-death):not(#cb-vig):not(script):not(style) { visibility: hidden !important; }
        #cb-death button { opacity: 0; transition: opacity .8s; pointer-events: none; font: 600 15px system-ui, sans-serif; letter-spacing: .22em;
          color: #ddd; background: transparent; border: 1px solid rgba(255,255,255,.45); border-radius: 4px; padding: 12px 30px; cursor: pointer; }
        #cb-death button.show { opacity: 1; pointer-events: auto; }
        #cb-death button:hover, #cb-death button:focus { border-color: #fff; color: #fff; outline: none; }`;
      document.head.appendChild(st);
    }
    const mk = (id, html = '') => { const d = document.createElement('div'); d.id = id; d.innerHTML = html; document.body.appendChild(d); return d; };
    this.vigEl = mk('cb-vig');
    this.indEl = mk('cb-ind');
    this.deathEl = mk('cb-death', '<button type="button">RESTART</button>');
    this.button = this.deathEl.querySelector('button');
    // (the page's own click starts pointer lock: keep it away from the death screen)
    this.deathEl.addEventListener('click', (e) => e.stopPropagation());
    this.button.addEventListener('click', (e) => { e.stopPropagation(); this.restart(); });
  }

  beginView() {
    if (this._applied) { this.camera.quaternion.multiply(this._applied.invert()); this._applied = null; }
  }
  endView(dt) {
    const k = this.kick;
    k.pitch *= Math.max(0, 1 - dt * 7);
    k.roll *= Math.max(0, 1 - dt * 6);
    if (this.player.isDown || Math.abs(k.pitch) + Math.abs(k.roll) < 1e-5) return;
    this._applied = new THREE.Quaternion().setFromEuler(new THREE.Euler(k.pitch, 0, k.roll, 'YXZ'));
    this.camera.quaternion.multiply(this._applied);
  }

  update(dt) {
    const t = this.target;
    // regenerate, slowly, once out of combat
    if (!this.dead && t.health < t.maxHealth && this.combat.lastCombat('player') > this.regenDelay)
      t.health = Math.min(t.maxHealth, t.health + this.regenRate * dt);
    this.flash = Math.max(0, this.flash - dt * 1.6);
    const low = this.dead ? 0 : Math.max(0, (40 - t.health) / 40);
    const pulse = low > 0 ? 0.75 + 0.25 * Math.sin(performance.now() / 1000 * Math.PI * 2 * (0.9 + low * 0.6)) : 0;
    const vig = Math.min(1, this.flash + low * 0.75 * pulse);
    if (Math.abs((this._vig ?? -1) - vig) > 0.003) { this.vigEl.style.opacity = vig.toFixed(3); this._vig = vig; }
    // hit direction wedges: they follow the source as the player turns, then fade (~1.4 s)
    const f = this.camera.getWorldDirection(new THREE.Vector3()).setY(0).normalize();
    for (let i = this.indicators.length - 1; i >= 0; i--) {
      const ind = this.indicators[i];
      ind.t += dt;
      if (ind.t > 1.4 || this.dead) { ind.el.remove(); this.indicators.splice(i, 1); continue; }
      const d = ind.from ? ind.from.clone().sub(this.player.pos).setY(0).normalize() : ind.dir;
      const ang = Math.atan2(f.x * d.z - f.z * d.x, f.x * d.x + f.z * d.z);
      ind.el.style.transform = `rotate(${(ang * 180 / Math.PI).toFixed(1)}deg)`;
      ind.el.style.opacity = (1 - Math.max(0, ind.t - 0.5) / 0.9).toFixed(3);
    }
    this.breathing(dt, this.dead ? 0 : low);
    if (this.dead) {
      this.deathT += dt;
      if (this.deathT > 0.05 && !this._faded) { this._faded = true; this.deathEl.style.opacity = '0.94'; if (document.pointerLockElement) document.exitPointerLock(); }
      if (this.deathT > 2.6 && !this.button.classList.contains('show')) { this.button.classList.add('show'); this.button.focus(); }
    }
  }

  // heavy breathing under ~40 health: band-passed noise in an in-out rhythm, louder and faster
  // the lower it gets (synthesised: no sample needed)
  breathing(dt, amount) {
    const s = window.__sfx;
    this.breathLevel = amount;
    if (!s?.running || !s.ctx) return;
    const c = s.ctx;
    if (!this.breath) {
      if (amount <= 0) return;
      const len = c.sampleRate * 2, buf = c.createBuffer(1, len, c.sampleRate), d = buf.getChannelData(0);
      for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
      const src = c.createBufferSource(); src.buffer = buf; src.loop = true;
      const bp = c.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 850; bp.Q.value = 0.7;
      const lp = c.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 2600;
      const g = c.createGain(); g.gain.value = 0;
      src.connect(bp).connect(lp).connect(g).connect(s.master ?? c.destination);
      src.start();
      this.breath = { src, bp, g, phase: 0 };
    }
    const b = this.breath;
    const rate = 0.45 + amount * 0.35;                       // breaths per second
    b.phase = (b.phase + dt * rate) % 1;
    // in (brighter) for 40% of the cycle, out (longer, darker) for 55%, then a pause
    const ph = b.phase, env = ph < 0.4 ? Math.sin((ph / 0.4) * Math.PI) * 0.8 : ph < 0.95 ? Math.sin(((ph - 0.4) / 0.55) * Math.PI) : 0;
    b.bp.frequency.setTargetAtTime(ph < 0.4 ? 1100 : 700, c.currentTime, 0.05);
    b.g.gain.setTargetAtTime(env * amount * 0.22, c.currentTime, 0.03);
  }
}

function sfxPlay(name, pos, opts) {
  const s = window.__sfx;
  if (!s?.play) return null;
  const fb = { player_hurt: ['hit', { rate: 0.75, db: -3 }], body_fall: ['fall', {}] }[name];
  if (s.manifest && !s.manifest.sounds?.[name] && fb) return s.play(fb[0], pos, { ...fb[1], ...opts });
  return s.play(name, pos, opts);
}
