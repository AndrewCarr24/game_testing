import * as THREE from 'three';
import { BoxGrid } from './invaders_nav.js';
import { buildWorld } from './invaders_world.js';
import { Invader, SENSE, WEAPONS } from './invaders_brain.js';
import { InvaderBodies } from './invaders_body.js';
import { InvaderFx } from './invaders_fx.js';

export { buildWorld };

// Invaders: waves of armed intruders in the house (design/invaders/behaviour.md).
//
// They arrive in waves (WAVES: at time `at` s the squad is topped up to `n` alive, capped at 50;
// the dead don't come back), through the entries (the front door, the terrace doors, the garage,
// the mudroom's side door, the great room's glass, smashed if it's still whole); some stay outside
// as watchers on the doors and the facades. The squad shares what they know: a shout reaches
// those in earshot at once, the radio everyone else after `radio` s (longer without the leader);
// the leader (while alive) turns each new contact into orders: the nearest few go there, a couple
// of gunmen hold sightlines round it, the rest keep sweeping. Rooms cleared, hiding spots checked
// and noises being looked into are shared, so they spread out instead of bunching.
//
// Cost: AI LOD (senses + brain every frame near the player or in a fight, every 3rd frame within
// 45 m, every 8th beyond; staggered by id), a path planner with a per-frame budget, bodies drawn
// instanced (invaders_body.js: a handful of draw calls for all of them).
//
// URL: ?invaders=0 off, ?invaders=N N at once (no waves), ?invaders=debug the overlay (cones,
// paths, states; also ?invdebug=1), ?waves=fast (the schedule at a tenth), ?waves=0 (none),
// ?waves=K (the schedule times K). window.__invaders: this.

export const WAVES = [{ at: 60, n: 6 }, { at: 300, n: 20 }, { at: 600, n: 50 }];
// who comes in each wave (watchers stay outside); a wave tops up with its mix, in this order
const MIX = [
  ['watcher', 'leader', 'bat', 'watcher', 'bat', 'knife'],                          // the first six
  ['gun', 'bat', 'watcher', 'knife', 'gun', 'bat', 'watcher', 'gun', 'knife', 'bat', 'watcher', 'gun', 'knife', 'bat'],
  ['gun', 'bat', 'knife', 'watcher', 'gun', 'bat', 'knife', 'gun', 'bat', 'watcher', 'knife', 'gun', 'bat', 'gun', 'knife', 'watcher'],
];
export const MAX = 50;
const rand = (a, b) => a + Math.random() * (b - a);
const V3 = THREE.Vector3;
const _a = new V3(), _b = new V3(), _ray = new THREE.Ray(), _hit = new V3();

export class Invaders {
  constructor({ scene, camera, player, level, colliders, interact, signals, noise, hiding, params = new URLSearchParams(), breakGlass = null, harmless = false }) {
    Object.assign(this, { scene, camera, player, level, colliders, interact, signals, noise, hiding });
    this.breakGlassHook = breakGlass;
    this._harmless = harmless;
    this.time = 0; this.frame = 0;
    const t0 = performance.now();
    this.world = buildWorld({ level, colliders, interact, signals });
    this.buildMs = performance.now() - t0;
    this.agents = [];
    this.intel = [];            // [{pos, t, src, by}]
    this.alert = 0;             // 0 calm .. 1 contact lately
    this.cleared = new Map();   // room -> time
    this.claims = new Map();    // room -> Set(agent) sweeping it
    this.spotAt = new Map();    // spot node -> time checked
    this.noiseClaims = new Map();
    this.queue = [];
    this.pending = [];
    this.radioQ = [];
    this.leader = null;
    this.glassBroken = false;
    this.stats = { spawned: 0, killed: 0, shots: 0, hits: 0, playerHits: 0, damage: 0, swings: 0, reports: 0, shouts: 0, radio: 0, orders: 0, planMs: 0, plans: 0, thinkMs: 0, frames: 0, maxMs: 0 };
    this.events = [];
    this.opts = { radio: 1.6, radioNoLeader: 4.0, shout: 20 };
    // (the character workstream's posed test form, ?invaders=x,z,rot,Clip;..., isn't ours)
    const q = params.getAll('invaders').filter((v) => !/,[A-Z][A-Za-z]+/.test(v)).join(',').split(',').filter(Boolean);
    this.debug = q.includes('debug') || params.get('invdebug') === '1';
    const n = q.map(Number).find((v) => Number.isFinite(v) && v > 0);
    const wq = params.get('waves');
    const k = wq === 'fast' ? 0.1 : Number.isFinite(+wq) && +wq > 0 ? +wq : 1;
    this.waves = wq === '0' || n ? [] : WAVES.map((w) => ({ ...w, at: w.at * k }));
    this.waveI = 0;
    this.immediate = n ? Math.min(MAX, n) : 0;
    this.setupRooms();
    this.setupEntries();
    // bodies: the stand-in at once; the rigged character (invaders_rig.js) when it has loaded,
    // if it's there (?invbody=stand keeps the stand-in)
    this.bodies = new InvaderBodies(scene, MAX + 8);
    if (params.get('invbody') !== 'stand') {
      import('./invaders_rig.js').then(({ loadRig }) => loadRig(scene, MAX + 8)).then((rig) => {
        rig.tune(WEAPONS);
        const stand = this.bodies;
        this.bodies = rig;
        for (const a of this.agents) rig.add(a);
        stand.dispose();
        this.event('rig', {});
      }).catch((e) => console.info('[inv] rigged invader not available, stand-ins:', e?.message ?? e));
    }
    this.fx = new InvaderFx(scene, camera, { debug: this.debug });
    noise?.on?.((ev) => this.onNoise(ev));
    this.combat = null;
    this.playerBox = new THREE.Box3();
    window.__invaders = this;
  }

  // no damage while the bench / shots drive the camera (their routes must not die)
  get harmless() { return this._harmless || !!window.__bench; }

  // ---------------------------------------------------------------- combat (viewer/combat.js)
  // (re)register every live invader whenever window.__combat changes (the real one may land later)
  syncCombat() {
    const C = window.__combat;
    if (!C || C === this.combat) return;
    this.combat = C;
    for (const a of this.agents) if (a.alive) C.register?.(a.target());
    C.on?.('playerDown', () => { this.playerGone = true; this.event('playerDown', {}); });
    C.on?.('hit', (e) => {
      if (e?.target?.kind === 'player') { this.stats.playerHits++; this.stats.damage += e.damage ?? 0; this.event('playerHit', { damage: e.damage, weapon: e.weapon }); }
    });
  }

  // ---------------------------------------------------------------- the level: rooms, entries, posts
  setupRooms() {
    const nav = this.world.nav;
    this.rooms = [];
    for (const r of this.world.rooms) {
      const L = r.floor > 2 ? nav.layers[1] : nav.layers[0];
      const cells = nav.cellsIn(L, [r.rect[0] + 0.3, r.rect[1] + 0.3, r.rect[2] - 0.3, r.rect[3] - 0.3], 1.0);
      if (cells.length < 4) continue;
      const area = (r.rect[2] - r.rect[0]) * (r.rect[3] - r.rect[1]);
      this.rooms.push({ ...r, L, cells, area, centre: new V3((r.rect[0] + r.rect[2]) / 2, r.floor, (r.rect[1] + r.rect[3]) / 2), spots: [] });
    }
    this.spots = [];
    try { this.spots = this.hiding?.spots?.() ?? []; } catch (e) { console.warn('[inv] hiding spots', e); }
    for (const s of this.spots) {
      const room = this.roomOf(s.exit);
      s.room = room?.name ?? null;
      room?.spots.push(s);
    }
  }
  roomOf(p) { return this.rooms.find((r) => p.y >= r.floor - 0.6 && p.y < r.floor + r.height && p.x >= r.rect[0] && p.x <= r.rect[2] && p.z >= r.rect[1] && p.z <= r.rect[3]) ?? null; }
  inHouseP(p) { return this.world.nav.inHouse(p.x, p.z, 0.05); }

  // the ways in: every door on the house's outer wall (and the great room's glass), with a point
  // outside it, one inside, where invaders for it appear (out of sight) and where its watcher stands
  setupEntries() {
    const nav = this.world.nav, H = nav.houseRect, out = [];
    const ground = nav.layers[0];
    const near = (x, z, r = 3) => { const k = nav.nearest(ground, x, z, r); return k >= 0 ? nav.xz(k) : null; };
    const side = (c) => {
      if (Math.abs(c.x - H[0]) < 0.6) return new THREE.Vector2(-1, 0);
      if (Math.abs(c.x - H[2]) < 0.6) return new THREE.Vector2(1, 0);
      if (Math.abs(c.y - H[1]) < 0.8) return new THREE.Vector2(0, -1);
      if (Math.abs(c.y - H[3]) < 0.8) return new THREE.Vector2(0, 1);
      return null;
    };
    for (const d of nav.doors) {
      if (d.layer !== 'ground') continue;
      const n = side(d.centre);
      if (!n) continue;
      // (paired leaves: one entry for both)
      if (out.some((e) => e.door && e.centre.distanceTo(d.centre) < 2.2)) continue;
      const room = d.name.split('@')[1]?.replace(/\[.*/, '') ?? d.name;
      out.push(this.makeEntry(/Garage/i.test(d.name) ? 'garage' : room, d.centre, n, { door: d }));
    }
    for (const b of this.level.breakables ?? []) {
      const c = new THREE.Vector2((b.min[0] + b.max[0]) / 2, (b.min[2] + b.max[2]) / 2), n = side(c);
      if (n) out.push(this.makeEntry('glass', c, n, { smash: true, breakable: b }));
    }
    for (const e of out) {
      const o = near(e.outside.x, e.outside.z, 4), i = near(e.inside.x, e.inside.z, 4);
      if (o) e.outside.set(o.x, nav.floorY(ground, o.x, o.y), o.y);
      if (i) e.inside.set(i.x, 0, i.y);
    }
    this.entries = out.filter((e) => e.spawn.length);
    // facade posts (watchers covering the windows of each side)
    this.facades = [
      { name: 'south', at: new V3(-12, 0, 31), yaw: Math.PI },
      { name: 'north', at: new V3(-8, 0, -32), yaw: 0 },
      { name: 'west', at: new V3(-38, 0, -10), yaw: Math.PI / 2 },
      { name: 'east', at: new V3(37, 0, 8), yaw: -Math.PI / 2 },
    ].map((f) => { const p = near(f.at.x, f.at.z, 6); if (p) f.at.set(p.x, nav.floorY(ground, p.x, p.y), p.y); return { ...f, amp: 0.7, facade: true }; });
  }
  makeEntry(name, c, n, extra) {
    const nav = this.world.nav, ground = nav.layers[0];
    const e = { name, centre: c.clone(), normal: n.clone(), ...extra,
      outside: new V3(c.x + n.x * 3.2, 0, c.y + n.y * 3.2), inside: new V3(c.x - n.x * 4, 0, c.y - n.y * 4), spawn: [] };
    if (extra.smash) { e.inside.set(c.x - n.x * 5, 0, c.y - n.y * 5); e.outside.set(c.x + n.x * 1.6, 0, c.y + n.y * 1.6); }
    // spawn points: 20-30 m out from the door (round its sides), on the nav, connected to the door
    const sOut = nav.cellFor(e.outside.x, 0, e.outside.z, 4);
    for (const [dist, sd] of [[24, 0], [26, 7], [26, -7], [30, 3], [30, -3], [20, 10], [20, -10], [16, 4], [16, -4], [14, 8], [14, -8]]) {
      const x = c.x + n.x * dist + n.y * sd, z = c.y + n.y * dist - n.x * sd;
      const k = nav.nearest(ground, x, z, 5);
      if (k >= 0 && nav.connected(k, sOut)) { const p = nav.xz(k); e.spawn.push(new V3(p.x, nav.floorY(ground, p.x, p.y), p.y)); }
    }
    // its watcher: ~11 m out, a little to one side, facing the door
    const wx = c.x + n.x * 11 + n.y * 2.5, wz = c.y + n.y * 11 - n.x * 2.5;
    const k = nav.nearest(ground, wx, wz, 5);
    if (k >= 0) { const p = nav.xz(k); e.post = { at: new V3(p.x, nav.floorY(ground, p.x, p.y), p.y), yaw: Math.atan2(c.x - p.x, c.y - p.y), amp: 0.45, entry: name }; }
    return e;
  }

  // ---------------------------------------------------------------- spawning
  // a new invader of `role` at an entry (or at a given place: `at`, `inside` = already in).
  spawn(role = 'bat', { entry = null, at = null, layer = 'ground', post = null, weapon = null, inside = false, yaw = null } = {}) {
    if (this.agents.filter((a) => a.alive).length >= MAX) return null;
    let E = entry ? (typeof entry === 'string' ? this.entries.find((e) => e.name === entry) : entry) : null;
    if (!at) {
      E ??= this.pickEntry(role);
      at = this.spawnPoint(E);
    }
    const a = new Invader(this, { role, pos: at.clone(), layer, entry: inside || role === 'watcher' ? null : E, weapon });
    if (role === 'watcher') a.post = post ?? this.pickPost(E);
    if (inside) { a.inside = true; a.set('sweep'); }
    a.yaw = a.lookYaw = yaw ?? (E ? Math.atan2(E.centre.x - at.x, E.centre.y - at.z) : 0);
    if (role === 'leader' && !this.leader?.alive) { this.leader = a; a.isLeader = true; }
    this.agents.push(a);
    this.stats.spawned++;
    this.combat?.register?.(a.target());
    this.bodies.add(a);
    this.event('spawn', { id: a.id, role, entry: E?.name ?? null });
    return a;
  }
  // the entries in turn (a watcher to a door nobody covers yet)
  pickEntry(role) {
    const list = this.entries;
    if (!list.length) return null;
    if (!this.agents.length) return list.find((e) => e.name === 'entry') ?? list[0];   // (the front door first)
    const useCount = (e) => this.agents.filter((a) => a.alive && (a.entry === e || a.post?.entry === e.name)).length;
    const ok = role === 'watcher' ? list.filter((e) => !this.agents.some((a) => a.alive && a.post?.entry === e.name)) : list;
    return (ok.length ? ok : list).slice().sort((a, b) => useCount(a) - useCount(b) + (Math.random() - 0.5) * 0.8)[0];
  }
  pickPost(E) {
    if (E?.post && !this.agents.some((a) => a.alive && a.post === E.post)) return E.post;
    const free = [...this.entries.map((e) => e.post).filter(Boolean), ...this.facades].find((p) => !this.agents.some((a) => a.alive && a.post === p));
    return free ?? E?.post ?? this.facades[0];
  }
  // a spawn point for an entry that the player can't see now (else the farthest)
  spawnPoint(E) {
    const eye = this.camera.position, pts = E?.spawn ?? [];
    if (!pts.length) return this.entries[0]?.spawn[0]?.clone() ?? new V3(0, 0, 40);
    const unseen = pts.filter((p) => p.distanceTo(eye) > 12 && !this.sightClear(_a.set(p.x, p.y + 1.6, p.z), eye, false));
    const L = unseen.length ? unseen : pts.slice().sort((a, b) => b.distanceTo(eye) - a.distanceTo(eye)).slice(0, 2);
    const p = L[Math.floor(Math.random() * L.length)].clone();
    p.x += rand(-0.5, 0.5); p.z += rand(-0.5, 0.5);
    return p;
  }
  // top up to n alive (a wave), a few at a time, spread over the entries
  topUp(n, mixI) {
    const alive = this.agents.filter((a) => a.alive).length + this.pending.length;
    const want = Math.min(MAX, n) - alive;
    // (the mixes in order, whatever the wave: the first six always bring the leader)
    this.mixN ??= 0;
    const roleFor = (n) => (n < 6 ? MIX[0][n] : n < 20 ? MIX[1][n - 6] : MIX[2][(n - 20) % MIX[2].length]);
    for (let i = 0; i < want; i++) this.pending.push({ role: roleFor(this.mixN++), at: this.time + Math.floor(i / 3) * 1.6 + rand(0, 0.6) });
    this.event('wave', { n, adding: Math.max(0, want) });
  }

  // ---------------------------------------------------------------- shared knowledge
  // an invader has the player at p (its eyes, a hit, a hiding spot): shout + radio, and orders
  report(by, p, src, urgent = false) {
    this.stats.reports++;
    const t = this.time;
    this.alert = 1;
    const last = this.intel[this.intel.length - 1];
    const fresh = !last || t - last.t > 3 || last.pos.distanceTo(p) > 4 || urgent;
    if (last && !fresh) { last.pos.copy(p); last.t = t; }
    else this.intel.push({ pos: p.clone(), t, src, by: by.id });
    if (this.intel.length > 40) this.intel.shift();
    // a shout: those in earshot know at once; the radio gets to the rest (once a second per invader)
    if (t - (by.shoutAt ?? -1e9) > 1.0 || urgent) {
      by.shoutAt = t;
      if (fresh) { this.stats.shouts++; window.__sfx?.play?.('invader_shout', by.pos); }
      const delay = this.leader?.alive ? this.opts.radio : this.opts.radioNoLeader;
      for (const a of this.agents) {
        if (a === by || !a.alive) continue;
        if (a.pos.distanceTo(by.pos) < this.opts.shout && this.wallsBetween(a.eyePos(_a), by.eyePos(_b)) <= 1.5) a.told({ pos: p, t, src: 'shout' });
        else this.radioQ.push({ a, at: t + delay * rand(0.8, 1.3), info: { pos: p.clone(), t, src: 'radio' } });
      }
    }
    if (fresh && t - (this.orderAt ?? -1e9) > 3) { this.orderAt = t; this.giveOrders(p, by); }
  }

  // the leader's orders for a contact at p: the nearest few go there, gunmen hold sightlines;
  // without a leader everyone near enough just goes (and they bunch)
  giveOrders(p, by) {
    const lead = this.leader?.alive ? this.leader : null;
    const delay = lead ? this.opts.radio : this.opts.radioNoLeader;
    const free = this.agents.filter((a) => a.alive && a !== by && a.role !== 'watcher' && !['engage', 'chase', 'strike', 'flee', 'dead', 'breach', 'cover', 'check'].includes(a.state));
    const dist = (a) => a.pos.distanceTo(p) + Math.abs(a.pos.y - p.y) * 3;
    free.sort((a, b) => dist(a) - dist(b));
    const orders = [];
    if (lead) {
      const melee = free.filter((a) => !a.gun), guns = free.filter((a) => a.gun);
      melee.slice(0, 3).forEach((a) => orders.push([a, { kind: 'respond', why: 'ordered' }]));
      guns.slice(0, 2).forEach((a) => orders.push([a, { kind: 'respond', why: 'ordered' }]));
      for (const a of guns.slice(2, 4)) {
        const h = this.holdPoint(a, p);
        if (h) orders.push([a, { kind: 'hold', at: h.at, yaw: h.yaw, until: this.time + rand(25, 45), why: 'sightline' }]);
      }
    } else free.filter((a) => dist(a) < 28).forEach((a) => orders.push([a, { kind: 'respond', why: 'heard' }]));
    for (const [a, o] of orders) this.radioQ.push({ a, at: this.time + delay * rand(0.7, 1.1), order: o, info: { pos: p.clone(), t: this.time, src: 'order' } });
    this.stats.orders += orders.length;
    if (orders.length) this.event('orders', { n: orders.length, leader: !!lead });
    if (lead && orders.length) window.__sfx?.play?.('invader_shout', lead.pos);
  }

  // a place 6-14 m from p (same floor) with a clear look at it, near a wall (its back covered)
  holdPoint(a, p) {
    const nav = this.world.nav, L = nav.layerAt(p.x, p.y, p.z), me = nav.cellFor(a.pos.x, a.pos.y, a.pos.z);
    const eye = new V3(p.x, p.y + 1.2, p.z);
    let best = null, bs = -Infinity;
    for (let i = 0; i < 18; i++) {
      const ang = (i / 18) * Math.PI * 2 + rand(0, 0.3), r = rand(6, 14);
      const k = nav.nearest(L, p.x + Math.sin(ang) * r, p.z + Math.cos(ang) * r, 1.5);
      if (k < 0 || !nav.connected(k, me)) continue;
      const c = nav.xz(k), y = nav.floorY(L, c.x, c.y), from = new V3(c.x, y + 1.6, c.y);
      if (this.world.sight.blocked(from, eye, 0.2)) continue;
      const wall = L.clear[k - L.off] < 1.2 ? 1 : 0;
      const s = wall - Math.abs(r - 9) * 0.1 - from.distanceTo(a.pos) * 0.02 - this.agents.filter((b) => b.alive && b.state === 'hold' && b.sub?.at?.distanceTo(from) < 4).length * 2;
      if (s > bs) { bs = s; best = { at: new V3(c.x, y, c.y), yaw: Math.atan2(p.x - c.x, p.z - c.y) }; }
    }
    return best;
  }

  // the radio (delayed messages); invaders that died meanwhile don't pass anything on
  updateRadio() {
    if (!this.radioQ.length) return;
    const keep = [];
    for (const m of this.radioQ) {
      if (m.at > this.time) { keep.push(m); continue; }
      if (!m.a.alive) continue;
      this.stats.radio++;
      m.a.told(m.info);
      if (m.order) m.a.order = m.order;
    }
    this.radioQ = keep;
  }

  // ---- rooms to sweep, searches, spots
  nextRoom(a) {
    const nav = this.world.nav, me = nav.cellFor(a.pos.x, a.pos.y, a.pos.z);
    const lk = this.intel[this.intel.length - 1];
    let best = null, bs = -Infinity;
    for (const r of this.rooms) {
      if (!this.inHouseP(r.centre)) continue;
      if (!nav.connected(me, r.cells[0])) continue;
      const since = this.time - (this.cleared.get(r.name) ?? -1e9);
      const claimed = [...(this.claims.get(r.name) ?? [])].filter((b) => b.alive && b !== a && b.sub?.room === r.name).length;
      const d = a.pos.distanceTo(r.centre) + Math.abs(a.pos.y - r.floor) * 12;
      let s = Math.min(1, since / 150) * 3 - d / 25 - claimed * 2.5 + Math.sqrt(r.area) / 10 + Math.random() * 0.8;
      if (lk && this.time - lk.t < 120) s += 2.5 * Math.exp(-r.centre.distanceTo(lk.pos) / 12);
      if (r.name === a.lastRoom) s -= 5;
      if (s > bs) { bs = s; best = r; }
    }
    if (best) { (this.claims.get(best.name) ?? this.claims.set(best.name, new Set()).get(best.name)).add(a); a.lastRoom = best.name; }
    return best?.name ?? null;
  }
  // a room's sweep: a few points spread through it (far apart), its hiding spots (some), nearest first
  roomPlan(a, name) {
    const r = this.rooms.find((q) => q.name === name), nav = this.world.nav;
    if (!r) return [];
    const n = Math.max(2, Math.min(6, Math.round(Math.sqrt(r.area) / 3.2)));
    const pts = [];
    for (let i = 0; i < n; i++) {
      let bk = -1, bd = -Infinity;
      for (const k of r.cells) {
        const c = nav.xz(k);
        const score = i === 0 ? -Math.hypot(c.x - a.pos.x, c.y - a.pos.z) + (r.L.clear[k - r.L.off] > 0.8 ? 3 : 0)
          : Math.min(...pts.map((p) => Math.hypot(p.at.x - c.x, p.at.z - c.y)));
        if (score > bd) { bd = score; bk = k; }
      }
      const c = nav.xz(bk);
      pts.push({ at: new V3(c.x, r.floor, c.y), room: name });
    }
    const lk = this.intel[this.intel.length - 1];
    for (const s of r.spots) {
      if (this.time - (this.spotAt.get(s.node) ?? -1e9) < 90) continue;
      const hot = lk && this.time - lk.t < 45 && lk.pos.distanceTo(s.exit) < 10;
      if (Math.random() < (hot ? 0.85 : 0.35)) pts.push({ spot: s, at: s.exit.clone() });
    }
    return order(pts, a.pos);
  }
  // round a loss at p: the room it's in and the nearest others, a point or two each, the spots near p
  searchPlan(a, p) {
    const nav = this.world.nav, out = [];
    const rooms = this.rooms.filter((r) => Math.abs(r.floor - (p.y > 3 ? 4.6 : 0)) < 1 && rectDist(r.rect, p) < 12)
      .sort((x, y) => rectDist(x.rect, p) - rectDist(y.rect, p)).slice(0, 3);
    for (const r of rooms) {
      const cs = r.cells.filter((k) => { const c = nav.xz(k); return Math.hypot(c.x - p.x, c.y - p.z) < 10; });
      for (let i = 0; i < Math.min(2, cs.length); i++) {
        const c = nav.xz(cs[Math.floor(Math.random() * cs.length)]);
        // (where it can't see from p: round a corner)
        const hidden = this.world.sight.blocked(_a.set(p.x, p.y + 1.5, p.z), _b.set(c.x, r.floor + 1.5, c.y), 0.2);
        if (hidden || i === 0) out.push({ at: new V3(c.x, r.floor, c.y), room: r.name, dwell: rand(1.5, 3) });
      }
    }
    for (const s of this.spots) {
      if (s.exit.distanceTo(p) > 9 || this.time - (this.spotAt.get(s.node) ?? -1e9) < 60) continue;
      if (Math.random() < 0.7) out.push({ spot: s, at: s.exit.clone() });
    }
    return order(out, a.pos).slice(0, 7);
  }
  roomCleared(room, a) { this.cleared.set(room, this.time); this.claims.get(room)?.delete(a); }
  spotChecked(s) { this.spotAt.set(s.node, this.time); }
  searched() {}
  arrived(a) { this.event('inside', { id: a.id }); }

  // noises: who goes to look (2 per noise, 4 for loud ones)
  claimNoise(a, L) {
    if (!L) return false;
    const key = `${Math.round(L.pos.x / 4)},${Math.round(L.pos.z / 4)},${Math.round(L.pos.y / 3)}`;
    let set = this.noiseClaims.get(key);
    if (!set || this.time - set.t > 20) { set = { t: this.time, who: new Set() }; this.noiseClaims.set(key, set); }
    for (const b of set.who) if (!b.alive || b.state !== 'investigate') set.who.delete(b);
    if (set.who.size >= (L.loud >= 1.5 ? 4 : 2)) return false;
    set.who.add(a);
    L.key = key;
    this.event('investigate', { id: a.id, source: L.source, at: [+L.pos.x.toFixed(1), +L.pos.z.toFixed(1)] });
    return true;
  }
  releaseNoise(a, L) { this.noiseClaims.get(L?.key)?.who.delete(a); }

  onNoise(ev) {
    if (!ev?.position || ev.team === 'invader') return;
    // (our own gunshots, if viewer/combat.js emits them for us)
    if (ev.source === 'gunshot' && this.lastShots?.some((s) => this.time - s.t < 0.3 && s.p.distanceTo(ev.position) < 1.5)) return;
    const p = ev.position, L0 = ev.loudness ?? 1, at = new V3(p.x, Math.max(p.y ?? 0.5, 0.3), p.z);
    const range = SENSE.hearing * L0, nav = this.world.nav;
    let field = null;
    for (const a of this.agents) {
      if (!a.alive) continue;
      const head = a.eyePos(_a), d = head.distanceTo(at);
      if (d > range) continue;
      // straight through the walls between (each muffles it), or round by the open ways (doorways,
      // the galleries; one walking-distance flood per noise, shared by everyone)
      const walls = Math.min(4, this.wallsBetween(head, at));
      let eff = d / Math.pow(SENSE.muffle, walls);
      if (eff > range && walls > 0) {
        field ??= nav.distField(nav.cellFor(at.x, Math.max(0, at.y - 0.5), at.z, 2), range);
        eff = Math.min(eff, field(nav.cellFor(a.pos.x, a.pos.y, a.pos.z, 1)) * 1.15);
      }
      if (eff > range) continue;
      a.hear({ pos: at.clone(), y: at.y, loud: L0 * Math.min(1, d / Math.max(eff, 1e-3)), d: eff, source: ev.source ?? 'noise' });
    }
  }

  // walls between two points: each lining pair counts once (glass half, a shut door 0.7)
  wallsBetween(a, b) {
    const hits = this.world.walls.hits(a, b), d = a.distanceTo(b);
    _ray.set(a, _b.subVectors(b, a).normalize());
    for (const c of this.doorBoxes()) if (_ray.intersectBox(c, _hit) && _hit.distanceTo(a) < d) hits.push([_hit.distanceTo(a), { door: true }]);
    hits.sort((p, q) => p[0] - q[0]);
    let n = 0, last = -1e9, lastW = 0;
    for (const [t, w] of hits) {
      const v = w.door ? 0.7 : w.glass ? 0.5 : 1;
      if (t - last < 0.5) { if (v > lastW) { n += v - lastW; lastW = v; } continue; }
      n += v; last = t; lastW = v;
    }
    return n;
  }

  // ---------------------------------------------------------------- sight, fire, melee
  // the doors' leaves as they are now (shut or open; none while swinging), and the closed blinds
  doorBoxes() {
    if (this._dbFrame === this.frame) return this._db;
    this._dbFrame = this.frame;
    this._db = [];
    for (const D of this.world.doors) { const c = D.kind === 'item' ? D.it.collider : D.r.collider; if (c && !c.isEmpty()) this._db.push(c); }
    this._blinds = this.interact?.sightBlockers ? this.interact.sightBlockers() : [];
    return this._db;
  }
  boxesBlock(a, b, boxes, margin = 0.1) {
    const d = a.distanceTo(b);
    if (!boxes.length || d < 1e-6) return false;
    _ray.set(a, _b.subVectors(b, a).divideScalar(d));
    for (const w of boxes) if (!w.containsPoint(a) && _ray.intersectBox(w, _hit) && _hit.distanceTo(a) < d - margin) return true;
    return false;
  }
  sightClear(a, b, crouch = false) {
    const W = this.world;
    if (W.sight.blocked(a, b, 0.1)) return false;
    if (this.boxesBlock(a, b, this.doorBoxes(), 0.1) || this.boxesBlock(a, b, this._blinds ?? [], 0.1)) return false;
    if (W.coverTall.blocked(a, b, 0.05)) return false;
    if (!crouch) return true;
    // ducked behind low furniture close in front of the eye (as if it were half a metre taller)
    const near = W.coverLow.near(b.x, b.z, 1.5, b.y - 2, b.y, this._near ??= []);
    const tall = [];
    for (const c of near) if (c.max.y >= b.y - 0.35 && c.min.y < b.y && c.distanceToPoint(b) < 1.5) tall.push(new THREE.Box3(c.min, new V3(c.max.x, Math.max(c.max.y, b.y + 0.5), c.max.z)));
    return !this.boxesBlock(a, b, tall, 0.05);
  }
  // a clear line of fire: no wall, glass, shut door, furniture or teammate in the way
  // (true, or why not: 'wall' | 'mate')
  lineOfFire(a, m, aim) {
    if (this.world.solid.blocked(m, aim, 0.25)) return 'wall';
    if (this.boxesBlock(m, aim, this.doorBoxes(), 0.1)) return 'wall';
    const d = m.distanceTo(aim), dir = _b.subVectors(aim, m).divideScalar(d || 1);
    for (const o of this.agents) {
      if (o === a || !o.alive) continue;
      const t = (o.pos.x - m.x) * dir.x + (o.pos.z - m.z) * dir.z;
      if (t < 0.2 || t > d - 0.3) continue;
      const px = m.x + dir.x * t, pz = m.z + dir.z * t, py = m.y + dir.y * t;
      if (Math.hypot(o.pos.x - px, o.pos.z - pz) < 0.45 && py > o.pos.y && py < o.pos.y + 1.85) return 'mate';
    }
    return true;
  }
  fire(a, m, aim, spread) {
    const dir = aim.clone().sub(m).normalize();
    // the spread: a direction within the cone (triangular distribution per axis)
    const u = new V3(-dir.z, 0, dir.x).normalize(), v = new V3().crossVectors(dir, u);
    dir.addScaledVector(u, (Math.random() + Math.random() - 1) * spread).addScaledVector(v, (Math.random() + Math.random() - 1) * spread).normalize();
    const W = a.weapon;
    const res = window.__combat?.shoot?.({ from: a.target(), origin: m.clone(), dir, spread: 0, range: W.range, damage: this.harmless ? 0 : W.damage, weapon: a.weaponName });
    const end = res?.point ?? m.clone().addScaledVector(dir, W.range);
    const hitT = res?.target ?? res?.hit?.target ?? null;
    this.stats.shots++;
    if (hitT) { this.stats.hits++; a.stats.hits++; }
    this.fx.tracer(m, end, !!hitT);
    a.anim.shotAt = a.time;
    this.lastShots ??= [];
    this.lastShots.push({ t: this.time, p: m.clone() });
    if (this.lastShots.length > 20) this.lastShots.shift();
    window.__sfx?.play?.('gunshot', m);
    // every gunshot is loud (the contract); tagged with the team so they don't chase their own shots
    window.__noise?.emit({ position: m.clone(), loudness: 2.5, source: 'gunshot', team: 'invader' });
    this.event('shot', { id: a.id, hit: !!hitT, d: +a.pos.distanceTo(this.player.pos).toFixed(1) });
    return res;
  }
  melee(a, W) {
    const origin = a.pos.clone(); origin.y += 1.2;
    const dir = new V3(Math.sin(a.lookYaw), 0, Math.cos(a.lookYaw));
    // nothing solid between it and its target (no swinging through a wall or a shut door)
    // (combat.attack checks the line of sight through the level's colliders itself)
    const res = window.__combat?.attack?.({ from: a.target(), origin, dir, weapon: a.weaponName, range: W.range, arc: W.arc, damage: this.harmless ? 0 : W.damage });
    const hits = Array.isArray(res) ? res : res?.hits ?? (res?.target ? [res] : []);
    this.stats.swings++;
    if (hits.length) { window.__sfx?.play?.(W.hitSfx, a.pos); window.__noise?.emit({ position: origin, loudness: 0.6, source: 'melee', team: 'invader' }); }
    this.event('swing', { id: a.id, hit: hits.length > 0 });
    return hits.length > 0;
  }

  // cover from a threat at p: a cell within 6 m where a crouched (low cover) or standing (a corner)
  // eye can't be seen from p
  findCover(a, p) {
    if (this.time - (a.coverAt ?? -1e9) < 2.5) return null;
    a.coverAt = this.time;
    const nav = this.world.nav, L = nav.layers.find((l) => l.name === a.layer) ?? nav.layers[0];
    const threat = new V3(p.x, p.y + 1.5, p.z);
    let best = null, bs = -Infinity;
    for (let i = 0; i < 20; i++) {
      const ang = Math.random() * Math.PI * 2, r = rand(1.5, 6);
      const k = nav.nearest(L, a.pos.x + Math.sin(ang) * r, a.pos.z + Math.cos(ang) * r, 0.8);
      if (k < 0) continue;
      const c = nav.xz(k), y = nav.floorY(L, c.x, c.y);
      if (this.sightClear(threat, new V3(c.x, y + 1.0, c.y), false)) continue;
      const crouch = this.sightClear(threat, new V3(c.x, y + 1.6, c.y), false);     // low cover: up to shoot
      const s = (crouch ? 1.5 : 1) - Math.hypot(c.x - a.pos.x, c.y - a.pos.z) * 0.15 - (Math.hypot(c.x - p.x, c.y - p.z) < 5 ? 2 : 0);
      if (s > bs) { bs = s; best = { at: new V3(c.x, y, c.y), crouch }; }
    }
    return best;
  }

  // ---- doors, glass, hiding, fleeing
  // may it kick in a locked door to get there? (only after the player, where it last knew them)
  breachOK(a, target) {
    if (!target || !a.know || this.time - a.know.t > 90) return false;
    return target.distanceTo(a.know.pos) < 3;
  }
  breakDoor(D) {
    if (D.it) {
      D.it.locked = false;
      D.it.indicator?.material?.emissive?.setRGB?.(0.05, 1.0, 0.25);
    }
    D.open();
    this.world.nav.components();
    this.event('breach', { door: D.name });
  }
  doorOpened(D, a) { this.event('door', { door: D.name, id: a.id }); }
  breakGlass() {
    if (this.glassBroken) return;
    this.breakGlassHook?.();
    this.onGlassBroken();
  }
  // the great room's glass is gone (an invader's bat or the Grimble): walkable through the hole
  onGlassBroken() {
    if (this.glassBroken) return;
    this.glassBroken = true;
    const b = this.level.breakables?.[0];
    if (!b) return;
    const nav = this.world.nav, G = nav.layers[0], r = nav.radius;
    const x0 = Math.min(b.min[0], b.max[0]) - 0.6, x1 = Math.max(b.min[0], b.max[0]) + 0.6;
    const z0 = Math.min(b.min[2], b.max[2]), z1 = Math.max(b.min[2], b.max[2]);
    // re-mark the cells there from the colliders as they are now (the hole was cut out of them)
    nav.fill(G, x0, z0, x1, z1, (L, k) => (L.blocked[k] = 0));
    for (const c of this.colliders) {
      if (c.isEmpty() || c.max.y < 0.3 || c.min.y > 1.9 || c.max.x + r < x0 || c.min.x - r > x1 || c.max.z + r < z0 || c.min.z - r > z1) continue;
      if (this.isOwnBox(c)) continue;
      nav.fill(G, Math.max(x0, c.min.x - r), Math.max(z0, c.min.z - r), Math.min(x1, c.max.x + r), Math.min(z1, c.max.z + r), (L, k) => (L.blocked[k] = 1));
    }
    nav.clearance();
    nav.components();
    this.world.solid = new BoxGrid(this.world.solid.boxes.filter((c) => !c.isEmpty() && c.max.y > -50));
    this.event('glass', {});
  }
  isOwnBox(c) {
    if (this.interact?.items.some((i) => i.collider === c) || this.interact?.reactors.some((r) => r.collider === c)) return true;
    return c.max.y < -50;
  }
  dragOut(a, spot) {
    this.event('found', { id: a.id, spot: spot.name });
    try { this.hiding?.leave?.({ instant: true }); } catch (e) { console.warn('[inv] drag out', e); }
    this.player.hidden = false;
  }
  fleeTarget(a, from) {
    let best = null, bd = -1;
    for (const e of this.entries) for (const s of e.spawn.slice(0, 2)) { const d = s.distanceTo(from); if (d > bd) { bd = d; best = s; } }
    return best?.clone() ?? a.pos.clone();
  }
  onDeath(a, info) {
    this.stats.killed++;
    this.event('death', { id: a.id, role: a.role, by: info?.weapon ?? null });
    if (a === this.leader) { this.leader = null; this.event('leader_down', { id: a.id }); }
    // those near hear it and come to look
    for (const b of this.agents) if (b.alive && b.pos.distanceTo(a.pos) < 18) b.hear({ pos: a.pos.clone().setY(a.pos.y + 0.5), y: a.pos.y, loud: 1, d: b.pos.distanceTo(a.pos), source: 'body_fall' });
    window.__combat?.unregister?.(a.target());
    for (const set of this.claims.values()) set.delete(a);
  }

  // ---------------------------------------------------------------- movement helpers
  // a body circle out of walls, furniture and door leaves (between the knees and the head)
  pushOut(a) {
    const r = a.radius, near = this.world.body.near(a.pos.x, a.pos.z, r + 0.05, a.pos.y + 0.35, a.pos.y + 1.7, this._pnear ??= []);
    for (const c of this.doorBoxes()) if (c.max.y > a.pos.y + 0.35 && c.min.y < a.pos.y + 1.7 && c.distanceToPoint(_a.set(a.pos.x, c.min.y + 0.1, a.pos.z)) < r + 0.1) near.push(c);
    for (let it = 0; it < 2; it++) {
      let px = 0, pz = 0;
      for (const c of near) {
        const cx = Math.min(Math.max(a.pos.x, c.min.x), c.max.x), cz = Math.min(Math.max(a.pos.z, c.min.z), c.max.z);
        const dx = a.pos.x - cx, dz = a.pos.z - cz, d = Math.hypot(dx, dz);
        if (d >= r) continue;
        if (d > 1e-6) { px += (dx / d) * (r - d); pz += (dz / d) * (r - d); continue; }
        const sx = a.pos.x - c.min.x < c.max.x - a.pos.x ? c.min.x - r - a.pos.x : c.max.x + r - a.pos.x;
        const sz = a.pos.z - c.min.z < c.max.z - a.pos.z ? c.min.z - r - a.pos.z : c.max.z + r - a.pos.z;
        if (Math.abs(sx) < Math.abs(sz)) px += sx; else pz += sz;
      }
      a.pos.x += px; a.pos.z += pz;
      if (!px && !pz) break;
    }
  }
  // agents keep apart (a spatial hash of 1 m cells)
  separate(dt) {
    const H = this._sep ??= new Map(), key = (x, z) => (Math.floor(x) + 512) * 4096 + (Math.floor(z) + 512);
    H.clear();
    for (const a of this.agents) if (a.alive) { const k = key(a.pos.x, a.pos.z); (H.get(k) ?? H.set(k, []).get(k)).push(a); }
    for (const a of this.agents) {
      if (!a.alive) continue;
      const i = Math.floor(a.pos.x), j = Math.floor(a.pos.z);
      for (let dj = -1; dj <= 1; dj++) for (let di = -1; di <= 1; di++) {
        for (const b of H.get(key(i + di, j + dj)) ?? []) {
          if (b.id <= a.id || Math.abs(b.pos.y - a.pos.y) > 1) continue;
          const dx = b.pos.x - a.pos.x, dz = b.pos.z - a.pos.z, d = Math.hypot(dx, dz), m = 0.62;
          if (d >= m || d < 1e-5) continue;
          const push = (m - d) * 0.5 * Math.min(1, dt * 10), ux = dx / d, uz = dz / d;
          // (the one standing still gives way less: it's holding a spot)
          const wa = a.moveSpeed > 0.2 ? 1 : 0.4, wb = b.moveSpeed > 0.2 ? 1 : 0.4;
          a.pos.x -= ux * push * wa; a.pos.z -= uz * push * wa;
          b.pos.x += ux * push * wb; b.pos.z += uz * push * wb;
        }
      }
    }
  }

  // ---- the path planner: queued, a per-frame budget (time and count), fights first
  requestPath(a, target, opts = {}) {
    a.planning = true;
    const i = this.queue.findIndex((q) => q.a === a);
    const q = { a, target: target.clone(), opts };
    if (i >= 0) this.queue[i] = q; else this.queue.push(q);
  }
  plan(budgetMs = 2.0, maxN = 6) {
    const t0 = performance.now(), nav = this.world.nav;
    let n = 0;
    if (this.queue.length > 1) this.queue.sort((p, q) => p.a.tier - q.a.tier);
    while (this.queue.length && n < maxN && performance.now() - t0 < budgetMs) {
      const { a, target, opts } = this.queue.shift();
      if (!a.alive) { a.planning = false; continue; }
      const s = nav.cellFor(a.pos.x, a.pos.y, a.pos.z, 2);
      let g = nav.cellFor(target.x, target.y, target.z, 4), partial = false;
      // (a goal in another component: the nearest cell of ours to it; breach plans go through locked doors)
      if (g >= 0 && s >= 0 && !opts.breach && !nav.connected(s, g)) {
        const L = nav.layerOf(g), p = nav.xz(g);
        g = nav.nearest(L, p.x, p.y, 6, (k) => nav.connected(s, k));
        partial = true;
      }
      const path = s >= 0 && g >= 0 ? nav.path(s, g, { breach: !!opts.breach, maxIter: a.tier === 0 ? 80000 : 40000 }) : null;
      if (path) { path[0].x = a.pos.x; path[0].z = a.pos.z; path.partial = partial; }
      a.gotPath(path);
      n++;
    }
    const ms = performance.now() - t0;
    this.stats.planMs += ms; this.stats.plans += n;
    return ms;
  }

  // ---------------------------------------------------------------- per frame
  update(dt) {
    if (!dt) return;
    const t0 = performance.now();
    this.time += dt; this.frame++;
    this.syncCombat();
    // waves
    if (this.immediate) { const n = this.immediate; this.immediate = 0; this.topUp(n, 2); this.pending.forEach((p, i) => (p.at = this.time + (i % 6) * 0.05)); }
    while (this.waveI < this.waves.length && this.time >= this.waves[this.waveI].at) { this.topUp(this.waves[this.waveI].n, this.waveI); this.waveI++; }
    if (this.pending.length) {
      const due = this.pending.filter((p) => p.at <= this.time);
      if (due.length) { this.pending = this.pending.filter((p) => p.at > this.time); for (const p of due) this.spawn(p.role); }
    }
    this.updateRadio();
    this.alert = Math.max(0, this.alert - dt / 90);
    if (this.frame % 30 === 0) this.world.nav.checkLocks();
    const P = this.player, eye = this.camera.position;
    const C = window.__combat;
    const gone = !!this.playerGone || !!P.dead || !!window.__vitals?.dead;
    const ctx = { player: P, eye, playerGone: gone, lit: this.lit(P.pos, true), playerOutside: !this.inHouseP(P.pos), tier: 0 };
    // AI LOD: the brain and senses every frame for those near or fighting, less often for the rest
    for (const a of this.agents) {
      const d = a.pos.distanceTo(P.pos);
      const busy = ['engage', 'chase', 'strike', 'cover', 'breach', 'check'].includes(a.state) || a.time - a.seenAt < 5;
      a.tier = !a.alive ? 3 : d < 22 || busy ? 0 : d < 45 ? 1 : 2;
      a.acc += dt;
      const every = [1, 3, 8, 15][a.tier];
      if ((this.frame + a.id) % every === 0) { ctx.tier = a.tier; a.think(a.acc, ctx); a.acc = 0; }
      if (a.tier < 2) a.move(dt, ctx);
      else { a.macc = (a.macc ?? 0) + dt; if ((this.frame + a.id) % 2 === 0) { a.move(a.macc, ctx); a.macc = 0; } }
      if (a.alive && (this.frame + a.id) % 10 === 0) a.light = this.lit(a.pos);
    }
    this.separate(dt);
    this.plan();
    // the player can't walk through them
    if (!gone) for (const a of this.agents) {
      if (!a.alive || Math.abs(a.pos.x - P.pos.x) > 1 || Math.abs(a.pos.z - P.pos.z) > 1 || Math.abs(a.pos.y - P.pos.y) > 1.5) continue;
      this.playerBox.min.set(a.pos.x - 0.24, a.pos.y, a.pos.z - 0.24);
      this.playerBox.max.set(a.pos.x + 0.24, a.pos.y + 1.8, a.pos.z + 0.24);
      P.pushOutOf?.(this.playerBox);
    }
    const ms = performance.now() - t0;
    this.stats.thinkMs += ms; this.stats.frames++; this.stats.maxMs = Math.max(this.stats.maxMs, ms);
    this.bodies.update(this.agents, dt, this.camera);
    this.fx.update(dt, this.debug ? this.agents : null, this);
  }

  // how lit a spot is (window.__house: the rooms' lights and daylight); 0.35 dark .. 1 (the
  // player's flashlight: 1.6)
  lit(feet, isPlayer = false) {
    if (isPlayer && window.__flashlight?.on) return 1.6;
    const v = window.__house?.lightAt?.(_a.set(feet.x, feet.y + 1.2, feet.z));
    return typeof v === 'number' && isFinite(v) ? 0.35 + 0.65 * Math.min(1, Math.max(0, v)) : 1;
  }

  event(kind, data) {
    this.events.push({ t: +this.time.toFixed(2), kind, ...data });
    if (this.events.length > 4000) this.events.splice(0, 1000);
  }
  log() {}

  // ---------------------------------------------------------------- tests / tools
  alive() { return this.agents.filter((a) => a.alive); }
  summary() {
    const by = {};
    for (const a of this.agents) by[a.state] = (by[a.state] ?? 0) + 1;
    const f = Math.max(1, this.stats.frames);
    return { t: +this.time.toFixed(1), alive: this.alive().length, states: by, alert: +this.alert.toFixed(2), msPerFrame: +(this.stats.thinkMs / f).toFixed(3), stats: { ...this.stats }, nav: { ...this.world.nav.stats } };
  }
  // remove everyone (tests)
  clear() {
    for (const a of this.agents) { window.__combat?.unregister?.(a.target()); this.bodies.remove(a); }
    this.agents = []; this.leader = null; this.intel = []; this.radioQ = []; this.queue = []; this.pending = [];
    this.cleared.clear(); this.claims.clear(); this.spotAt.clear(); this.noiseClaims.clear(); this.alert = 0; this.playerGone = false;
    this.orderAt = -1e9; this.lastShots = [];
  }
}

function order(pts, from) {
  const out = [], left = pts.slice();
  let at = from;
  while (left.length) {
    left.sort((a, b) => a.at.distanceTo(at) - b.at.distanceTo(at));
    const p = left.shift(); out.push(p); at = p.at;
  }
  return out;
}
function rectDist(r, p) { return Math.hypot(Math.max(r[0] - p.x, 0, p.x - r[2]), Math.max(r[1] - p.z, 0, p.z - r[3])); }
