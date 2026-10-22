import * as THREE from 'three';
import { install as installSounds } from './invaders_audio.js';

// The first five (design/invaders/behaviour.md, "The first five"): they arrive together on foot
// up the drive from the gate, walk to the front door in a loose group (the leader in front), stop
// on the step and ring the doorbell. Then they wait, ring again, knock, try the handle, look in
// through the glass beside the door, and split up round the house to look in the windows and try
// the other doors. Nobody answers: they break in (the front door kicked in, the great room's
// glass smashed, the mudroom's side door kicked in) and the hunt begins (the squad's own brains,
// viewer/invaders_brain.js, from there on).
//
// Branches (each one ends the slow part and hands them to their brains, which keep what they
// know):
//   answered  the player opens a door they're at: a beat, then in through it
//   seen      one of them sees the player through the glass (the senses never stop): before they
//             reach the door they keep coming (and ring anyway, once, shorter waits); at the door
//             they stop and stare in, the gunmen aim through the glass, then the door is kicked in
//   heard     a noise inside (running, a thrown thing, a device): they look toward it; a second
//             one and they come in
//   outside   the player is seen outside: straight to the hunt (they shoot)
//   hit       one of them is hurt: the hunt
//   open      a prober finds a door the player left open: in through it, the rest follow
//   hid       hidden (a closet, under a bed): nothing to see; they break in and sweep
//
// The exterior doors are locked to them while this runs (`latched`: the nav treats them as
// locked, so no path goes through them); the player opens them from inside as usual, which
// unlocks that door for good. A kick (the brain's breach) or the smashed glass gets them in.
//
// It drives the five through their brains' `scene` state: the brain still perceives (sight,
// hearing, the squad's radio) and calls think() here instead of its own state machine; movement,
// facing and poses are set here every frame. URL: ?seq=0 off · ?seq=N first sighting at the gate
// after N s (default 30) · ?seq=now (2 s) · ?seq=manual (tests call start()) · ?seqk=K the waits
// times K · ?seqfrom=gate|court|step where they start. window.__invaders.opening: this.

const V3 = THREE.Vector3;
const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
const yawTo = (from, to) => Math.atan2(to.x - from.x, to.z - from.z);
const rand = (a, b) => a + Math.random() * (b - a);

// the five: role, look (outfit, head; viewer/invader_asset.js), size, where they walk in the
// group (metres behind the leader, to his right +), how they stand
export const CAST = [
  { key: 'leader', role: 'leader', look: { outfit: 'Navy', head: 'cap' }, holstered: true, slot: [0, 0], idle: 'Idle' },
  { key: 'gunA', role: 'gun', look: { outfit: 'Charcoal', head: 'mask+hood' }, slot: [1.8, -1.35], idle: 'Idle' },
  { key: 'gunB', role: 'gun', look: { outfit: 'Olive', head: 'hood' }, slot: [2.4, 1.45], idle: 'Idle' },
  { key: 'bat', role: 'bat', look: { outfit: 'Charcoal', head: 'none' }, scale: 1.07, slot: [3.9, -0.55], idle: 'Idle' },
  { key: 'knife', role: 'knife', look: { outfit: 'Olive', head: 'mask' }, scale: 0.95, slot: [4.7, 0.85], idle: 'IdleAlert' },
];

// the timeline (seconds; ?seqk scales the waits, not the walking)
export const T = {
  gather: 2.5,       // on the step, before the first ring
  wait1: 10,         // after the first ring
  wait2: 8,          // after the second
  knockWait: 5,      // after knocking
  peer: 8,           // two of them look in through the glass beside the door
  probeMax: 80,      // round the house, at most
  stare: 3.5,        // seen through the glass: they stare, then come in
  beat: 0.8,         // the door opens: a beat before they move
  heardGap: 3,       // a second noise this long after the first: they come in
};

// world (glTF) points: the front door is at z = 20 (+z is south, toward the drive and the gate)
const P = {
  gate: new V3(19.75, 0, 56.0),       // just inside the drive's gate (estate_link.js GATE: z 62)
  court: new V3(19.0, 0, 40.0),       // the drive's mouth on the motor court
  via: new V3(4.0, 0, 29.0),          // the entry path from the court, between the bollards
  bell: new V3(1.65, 1.3, 20.0),      // the door surround (no button model: where a finger meets it)
  door: new V3(0, 1.2, 20.0),
  peerL: new V3(-3.75, 0, 20.47), peerR: new V3(3.75, 0, 20.47),   // (mid-bay: the mullions are 1.5 m apart)
};
// where each stands on the step (under the canopy), and what it faces
const STEP = {
  leader: { at: [1.95, 20.8], face: [1.55, 18] },      // beside the door (its leaves swing out)
  gunA: { at: [-2.5, 22.05], face: [-0.5, 19] },
  gunB: { at: [3.4, 22.45], face: [1.5, 19] },
  bat: { at: [-0.85, 23.25], face: [0, 19] },
  knife: { at: [1.9, 23.85], face: [1, 19] },
};

export class Opening {
  constructor(sq, params = new URLSearchParams()) {
    this.sq = sq;
    const q = params.get('seq');
    this.k = Math.max(0.05, +(params.get('seqk') ?? 1) || 1);
    this.from = params.get('seqfrom') ?? 'gate';
    this.delay = q === 'now' ? 2 : Number.isFinite(+q) && q !== null && q !== '' ? +q : 30;
    this.manual = q === 'manual';
    this.t = 0;
    this.phase = this.manual ? 'off' : 'waiting';
    this.cast = {};
    this.timeline = [];
    this.rings = 0; this.knocks = 0; this.handles = 0;
    this.reason = null;
    this.trail = [];
    this.heardN = 0;
    installSounds(window.__sfx, { inHouse: (p) => sq.world.nav.inHouse(p.x, p.z, 0.2) });
    this.setupDoors();
  }

  // ---------------------------------------------------------------- the doors
  // every door on the outer wall is locked to them (the player opens them from inside)
  setupDoors() {
    const nav = this.sq.world.nav, H = nav.houseRect;
    const outer = (c) => Math.abs(c.x - H[0]) < 0.6 || Math.abs(c.x - H[2]) < 0.6 || Math.abs(c.y - H[1]) < 0.8 || Math.abs(c.y - H[3]) < 0.8;
    this.outer = nav.doors.filter((d) => d.layer === 'ground' && outer(d.centre));
    for (const d of this.outer) {
      if (d._latchWrapped) continue;
      const orig = d.locked;
      d.locked = () => orig() || !!d.latched;
      d._latchWrapped = true;
    }
    this.latch(false);
  }
  latch(on) {
    for (const d of this.outer) d.latched = on && !d.isOpen() && !d.opening();
    this.sq.world.nav.components();
  }
  entry(name) { return this.sq.entries.find((e) => e.name === name) ?? null; }
  leaves(E) { return E?.door ? this.outer.filter((d) => d.centre.distanceTo(E.door.centre) < 2.2) : []; }
  entryOpen(E) {
    if (!E) return false;
    if (E.smash) return this.sq.glassBroken;
    const L = this.leaves(E);
    return L.length > 0 && L.some((d) => !d.latched);
  }
  // a door the player opened (they can't): unlocked for good
  watchDoors() {
    let changed = false;
    for (const d of this.outer) {
      if (!d.latched || !(d.opening() || d.isOpen())) continue;
      d.latched = false; changed = true;
      this.sq.event('seq_door', { door: d.name, by: 'player' });
      this.doorOpened(d);
    }
    if (changed) this.sq.world.nav.components();
  }

  // ---------------------------------------------------------------- start, reset
  start({ from = this.from } = {}) {
    this.sq.clear();
    this.t = 0; this.phaseT = 0; this.timeline = []; this.trail = [];
    this.rings = 0; this.knocks = 0; this.handles = 0; this.heardN = 0; this.reason = null;
    this.knowsHome = false; this.seenBy = null; this.stareT = 0; this.bellDead = false; this.lastSeenT = null; this.heardAt = null; this.jobs = null;
    this.latch(true);
    const lead0 = from === 'court' ? P.court : P.gate;
    const head = yawTo(lead0, P.via);
    this.cast = {};
    for (const c of CAST) {
      let at;
      if (from === 'step') { const s = STEP[c.key]; at = new V3(s.at[0], 0, s.at[1]); }
      else at = this.slotAt(lead0, head, c.slot);
      const a = this.sq.spawn(c.role, { at, yaw: from === 'step' ? Math.PI : head, extra: { cast: c.key, look: c.look, holstered: !!c.holstered, scale: c.scale ?? 1, idleClip: c.idle } });
      if (!a) continue;
      a.set('scene', 'opening');
      a.cue = { mode: 'hold' };
      this.cast[c.key] = a;
    }
    this.set(from === 'step' ? 'gather' : 'approach');
    if (from === 'step') this.phaseT = T.gather * this.k;
  }
  reset() { this.cast = {}; this.phase = this.manual ? 'off' : 'done'; this.latch(false); }

  set(phase, why = null) {
    if (this.phase === phase) return;
    this.phase = phase; this.phaseT = 0; this.sub = {};
    this.timeline.push({ t: +this.t.toFixed(2), phase, why });
    this.sq.event('seq', { phase, why });
  }
  get members() { return Object.values(this.cast).filter((a) => a.alive && a.state === 'scene'); }
  get active() { return !['off', 'waiting', 'done'].includes(this.phase); }
  // the doorbell's own noise (their ring): not something to investigate
  ownRing() { return this.active || this.t - (this.ringAt ?? -1e9) < 8; }

  // ---------------------------------------------------------------- per frame (the squad's update)
  update(dt) {
    this.t += dt; this.phaseT += dt;
    if (this.phase === 'waiting') { if (this.t >= this.delay) this.start(); return; }
    if (!this.active) return;
    this.watchDoors();
    const K = this.k, c = this.cast, L = c.leader;
    // someone left the script (hit, a breach finished, the brain took over): see below
    for (const a of Object.values(c)) if (a.alive && a.state !== 'scene' && a.state !== 'breach' && !a.handed) this.left(a);
    switch (this.phase) {
      case 'approach': this.approach(dt); break;
      case 'gather':
        if (this.phaseT >= T.gather * K || this.allAt(0.7)) this.set('ring');
        break;
      case 'ring':
        // the leader presses the bell (OpenDoor's reach), the chime inside
        if (!this.sub.pressed) { this.pose(L, 'OpenDoor', 0.78); this.sub.pressed = true; }
        if (!this.sub.rung && this.phaseT > 0.42) { this.sub.rung = true; this.ring(); }
        if (this.phaseT > 1.2) this.set(this.rings >= 2 ? 'wait2' : 'wait1');
        break;
      case 'wait1': this.waiting(dt, this.knowsHome ? T.wait1 * 0.45 : T.wait1, this.knowsHome ? 'knock' : 'ring'); break;
      case 'wait2': this.waiting(dt, T.wait2, 'knock'); break;
      case 'knock': this.knock(dt); break;
      case 'handle': this.handle(dt); break;
      case 'peer': this.peer(dt); break;
      case 'split': this.split(dt); break;
      case 'probe': this.probe(dt); break;
      case 'stare': this.stare(dt); break;
      case 'answered': this.answered(dt); break;
      case 'breakin': this.breakin(dt); break;
    }
    for (const a of this.members) this.drive(a, dt);
    if (this.active && this.phase !== 'approach' && !this.members.length && !Object.values(c).some((a) => a.alive && a.state === 'breach')) this.set('done', this.reason);
  }

  // ---- the walk up the drive: the leader along his route, the rest in their places behind him
  approach(dt) {
    const L = this.cast.leader;
    if (!L?.alive) { this.goIn('leader down'); return; }
    this.sub.wp ??= this.from === 'court' ? 1 : 0;
    const route = [P.court, P.via, this.stepPoint('leader')];
    const target = route[this.sub.wp];
    L.cue = { mode: 'go', to: target, speed: 1.35, tol: this.sub.wp < 2 ? 1.5 : 0.35, face: new V3(STEP.leader.face[0], 0, STEP.leader.face[1]) };
    if (Math.hypot(L.pos.x - target.x, L.pos.z - target.z) < (this.sub.wp < 2 ? 1.6 : 0.4)) {
      if (this.sub.wp < 2) this.sub.wp++;
      else { this.set('gather'); for (const a of this.members) if (a !== L) a.cue = this.stepCue(a.cast); return; }
    }
    // the leader's trail: where the others walk (behind him, to the sides)
    const last = this.trail[this.trail.length - 1];
    if (!last || last.distanceTo(L.pos) > 0.3) { this.trail.push(L.pos.clone()); if (this.trail.length > 200) this.trail.shift(); }
    const near = Math.hypot(L.pos.x - P.door.x, L.pos.z - P.door.z) < 7;
    for (const a of this.members) {
      if (a === L) continue;
      // the last few metres: each to its own place on the step
      if (near) { a.cue = this.stepCue(a.cast); continue; }
      const c = CAST.find((x) => x.key === a.cast);
      const sway = Math.sin(this.t * 0.37 + a.id * 1.7) * 0.3;
      a.cue = { mode: 'follow', to: this.trailPoint(c.slot[0], c.slot[1] + sway), lead: L };
    }
  }
  stepPoint(key) { const s = STEP[key]; return new V3(s.at[0], 0, s.at[1]); }
  stepCue(key) { const s = STEP[key]; return { mode: 'go', to: this.stepPoint(key), speed: 1.4, tol: 0.3, face: new V3(s.face[0], 0, s.face[1]) }; }
  // a place `back` m behind the leader along his trail, `side` m to his right
  trailPoint(back, side) {
    const L = this.cast.leader, tr = this.trail;
    let p = L.pos.clone(), dir = new V3(Math.sin(L.yaw), 0, Math.cos(L.yaw)), left = back;
    for (let i = tr.length - 1; i >= 0 && left > 0; i--) {
      const seg = tr[i].distanceTo(p);
      if (seg < 1e-4) continue;
      const d = new V3().subVectors(p, tr[i]).normalize();
      if (seg >= left) { p = p.clone().addScaledVector(d, -left); dir = d; left = 0; break; }
      p = tr[i].clone(); dir = d; left -= seg;
    }
    if (left > 0) p.addScaledVector(dir, -left);
    return this.onNav(p.x - dir.z * side, p.z + dir.x * side, p);
  }
  slotAt(lead, head, [back, side]) {
    const fx = Math.sin(head), fz = Math.cos(head);
    return this.onNav(lead.x - fx * back - fz * side, lead.z - fz * back + fx * side, lead);
  }
  onNav(x, z, fallback) {
    const nav = this.sq.world.nav, G = nav.layers[0], k = nav.nearest(G, x, z, 1.2);
    if (k < 0) return fallback.clone();
    const c = nav.xz(k);
    return new V3(c.x, nav.floorY(G, c.x, c.y), c.y);
  }
  allAt(tol) { return this.members.every((a) => !a.cue?.to || Math.hypot(a.pos.x - a.cue.to.x, a.pos.z - a.cue.to.z) < tol); }

  // ---- the doorbell
  ring() {
    const S = this.sq.signals, live = S && S.get('power') !== false;
    this.rings++;
    this.ringAt = this.t;
    if (!live) { this.sq.event('seq_ring', { n: this.rings, dead: true }); this.bellDead = true; return; }
    // (still ringing from the last press: press again)
    if (S.get('doorbell')) S.set('doorbell', false);
    S.set('doorbell', true);
    this.sq.event('seq_ring', { n: this.rings });
  }
  waiting(dt, secs, next) {
    const K = this.k, c = this.cast;
    // body language while they wait: the bat looks back down the drive, the knife scans, the
    // second gunman shifts and looks along the glass
    if (!this.sub.looks) {
      this.sub.looks = true;
      this.glanceAt(c.bat, P.gate, rand(2.5, 4) * K, 3);
      this.glanceAt(c.gunB, new V3(9, 1.6, 20), rand(4, 6) * K, 2.5);
      this.glanceAt(c.gunA, new V3(-12, 1.6, 22), rand(1.5, 3) * K, 2);
      this.glanceAt(c.leader, new V3(0.5, 4.5, 18), rand(3, 5) * K, 2.2);     // up at the house
    }
    if (this.phaseT >= secs * K) this.set(next === 'ring' && this.bellDead ? 'knock' : next);
  }
  glanceAt(a, p, after, dur) {
    if (!a) return;
    (a.glances ??= []).push({ at: this.t + after, until: this.t + after + dur, p: p.clone() });
  }

  // ---- knocking on the door's glass, then the handle
  knock(dt) {
    const L = this.cast.leader, S = this.sub;
    S.n ??= 0; S.next ??= 0;
    const raps = this.bellDead ? 3 : 2;      // (a dead bell: they knock longer, harder)
    if (S.n < raps && this.phaseT >= S.next) {
      this.pose(L, 'OpenDoor', 0.5, `knock${S.n}`, 1.3);
      window.__sfx?.play?.('door_knock', P.door.clone().setX(0.6), { db: this.bellDead ? 3 : 0 });
      this.sq.noise?.emit?.({ position: P.door.clone(), loudness: 0.9, source: 'door_knock', team: 'invader' });
      this.knocks++;
      this.sq.event('seq_knock', { n: this.knocks });
      S.n++; S.next = this.phaseT + 1.6;
    }
    if (S.n >= raps && this.phaseT >= S.next + T.knockWait * this.k * (this.knowsHome ? 0.5 : 1)) this.set('handle');
  }
  handle(dt) {
    const L = this.cast.leader, S = this.sub;
    if (!S.go) {
      S.go = true;
      L.cue = { mode: 'go', to: new V3(0.45, 0, 20.75), speed: 1.2, tol: 0.25, face: new V3(0.45, 0, 18) };
    }
    if (!S.tried && L.cue.mode === 'go' && Math.hypot(L.pos.x - 0.45, L.pos.z - 20.75) < 0.35) {
      S.tried = true; S.at = this.phaseT;
      this.pose(L, 'OpenDoor', 1.4, 'handle');
    }
    if (S.tried && !S.rattled && this.phaseT - S.at > 0.75) {
      S.rattled = true;
      this.handles++;
      window.__sfx?.play?.('door_locked', new V3(0.3, 1.0, 20), { db: 4 });
      this.sq.noise?.emit?.({ position: P.door.clone(), loudness: 0.5, source: 'door_handle', team: 'invader' });
      this.sq.event('seq_handle', { door: 'entry' });
    }
    if (S.rattled && this.phaseT - S.at > 2.2) this.set(this.knowsHome ? 'stare' : 'peer', this.knowsHome ? 'knows someone is home' : null);
    if (!S.tried && this.phaseT > 6) { S.tried = true; S.at = this.phaseT; }
  }

  // ---- two of them look in through the glass beside the door; the leader steps back
  peer(dt) {
    const c = this.cast, S = this.sub;
    if (!S.go) {
      S.go = true;
      if (c.knife) c.knife.cue = { mode: 'go', to: P.peerR.clone(), speed: 1.3, tol: 0.25, face: new V3(3.75, 0, 10), peer: true };
      if (c.gunA) c.gunA.cue = { mode: 'go', to: P.peerL.clone(), speed: 1.3, tol: 0.25, face: new V3(-3.75, 0, 10), peer: true };
      if (c.leader) c.leader.cue = { mode: 'go', to: new V3(0.6, 0, 22.4), speed: 1.0, tol: 0.3, face: new V3(0.6, 0, 18) };
      // the bat turns to watch the drive; the second gunman along the front, east
      if (c.bat) this.glanceAt(c.bat, P.court.clone().setY(1.6), 0.5, 4);
    }
    if (this.phaseT >= T.peer * this.k + 3) this.set('split');
  }

  // ---- the leader points them round the house
  split(dt) {
    const c = this.cast, S = this.sub;
    if (!S.signalled) { S.signalled = true; if (c.leader) { c.leader.cue = { ...c.leader.cue, face: new V3(-12, 0, 24) }; this.pose(c.leader, 'Signal', 1.7); } }
    if (this.phaseT > 0.6 && !S.sent) {
      S.sent = true;
      this.routes = this.probeRoutes();
      for (const [key, stops] of Object.entries(this.routes)) {
        const a = c[key];
        if (a?.alive && a.state === 'scene') { a.route = stops; a.stopI = 0; a.cue = null; }
      }
    }
    if (this.phaseT > 1.7) this.set('probe');
  }
  // who goes where: the leader keeps the front (the garage door, then back to the glass); the
  // first gunman and the bat round the west to the great room's glass; the knife round the east to
  // the mudroom's window and side door; the second gunman on round the north (the kitchen's and
  // the dining room's terrace doors)
  probeRoutes() {
    const E = (n) => this.entry(n), out = (e, m) => (e ? this.onNav(e.centre.x + e.normal.x * m, e.centre.y + e.normal.y * m, new V3(e.centre.x, 0, e.centre.y)) : null);
    const face = (e) => (e ? new V3(e.centre.x, 0, e.centre.y) : null);
    const stop = (at, faceP, dwell, door = null, extra = {}) => (at ? { at, face: faceP, dwell, door, ...extra } : null);
    const glass = E('glass'), kitchen = E('kitchen'), dining = E('dining'), mud = E('mudroom'), garage = E('garage');
    const gC = glass ? new V3(glass.centre.x, 0, glass.centre.y) : new V3(-26, 0, 0);
    const routes = {
      leader: [stop(out(garage, 1.2), face(garage), 4), stop(P.peerL.clone(), new V3(-3.75, 0, 10), 999, null, { peer: true })],
      gunA: [stop(new V3(gC.x - 1.25, 0, gC.z - 2.4), new V3(gC.x + 5, 0, gC.z - 2.4), 999, null, { peer: true, aimReady: true })],
      bat: [stop(new V3(gC.x - 1.2, 0, gC.z + 1.6), new V3(gC.x + 5, 0, gC.z + 1.6), 999, null, { peer: true })],
      knife: [stop(new V3(27.25, 0, -5.25), new V3(20, 0, -5.25), 6, null, { peer: true }), stop(out(mud, 0.75), face(mud), 999, mud, { peer: true })],
      gunB: [stop(new V3(-1 + 4.5, 0, -21.3), new V3(3.5, 0, -14), 5, null, { peer: true }), stop(out(kitchen, 0.8), face(kitchen), 3, kitchen), stop(out(dining, 0.8), face(dining), 999, dining)],
    };
    for (const k of Object.keys(routes)) routes[k] = routes[k].filter(Boolean);
    return routes;
  }
  probe(dt) {
    let done = 0, n = 0;
    for (const a of this.members) {
      if (!a.route) continue;
      n++;
      const s = a.route[a.stopI];
      if (!s) { done++; continue; }
      if (!a.cue || a.cue.stop !== s) a.cue = { mode: 'go', to: s.at, speed: a.cast === 'leader' ? 1.3 : 1.8, tol: 0.35, face: s.face, stop: s, peer: s.peer, aimReady: s.aimReady };
      const there = Math.hypot(a.pos.x - s.at.x, a.pos.z - s.at.z) < 0.5;
      if (there && s.arrived == null) s.arrived = this.t;
      if (s.arrived == null) continue;
      const since = this.t - s.arrived;
      // a door to try: the handle at 1.2 s
      if (s.door && !s.tried && since > 1.2) {
        s.tried = true;
        if (this.entryOpen(s.door)) { this.reason = 'open door'; this.sq.event('seq_open', { door: s.door.name, id: a.id }); this.goIn('found an open door', { via: s.door, by: a }); return; }
        this.pose(a, 'OpenDoor', 1.4, `handle${a.stopI}`);
        this.handles++;
        const c = s.door.centre;
        window.__sfx?.play?.('door_locked', new V3(c.x, 1.0, c.y), { db: 4 });
        this.sq.noise?.emit?.({ position: new V3(c.x, 1.0, c.y), loudness: 0.5, source: 'door_handle', team: 'invader' });
        this.sq.event('seq_handle', { door: s.door.name, id: a.id });
      }
      if (since >= s.dwell * (s.dwell < 900 ? this.k : 1) + (s.door ? 1.6 : 0)) a.stopI++;
      if (s.dwell >= 900 && since > 4 * this.k) done++;      // (at its last place: done, it waits there)
    }
    if ((n && done >= n) || this.phaseT > T.probeMax)this.goIn('nobody answered');
  }

  // ---------------------------------------------------------------- what they sense (from the brain)
  // the brain's think() while in `scene`, after perceive(): sight, hearing, a hiding spot seen
  think(a, dt, ctx) {
    if (!this.active) { this.handOff(a); return; }
    if (a.leadNew) { a.leadNew = false; this.heard(a, a.lead, ctx); }
    if (a.hideSeen) { this.reason = 'saw them hide'; this.goIn('saw them hide'); return; }
    if (a.seenNow) this.seen(a, ctx);
  }

  seen(a, ctx) {
    const P0 = ctx.player.pos;
    a.glance = { yaw: yawTo(a.pos, P0), until: a.time + 1.2, p: P0.clone() };
    if (!this.seenBy) { this.seenBy = a; this.seenT = this.t; this.sq.event('seq_seen', { id: a.id, cast: a.cast, phase: this.phase, outside: ctx.playerOutside, d: +a.pos.distanceTo(P0).toFixed(1) }); }
    this.lastSeenT = this.t;
    if (ctx.playerOutside) { this.goIn('seen outside', { hunt: true }); return; }
    if (['breakin', 'answered', 'stare'].includes(this.phase)) return;
    if (!this.knowsHome) {
      this.knowsHome = true;
      // he points at the glass; the others look where he points
      this.pose(a, 'Signal', 1.0, 'point');
      for (const b of this.members) if (b !== a) this.glanceAt(b, P0.clone().setY(P0.y + 1.5), rand(0.3, 0.8), 2.5);
    }
    // at the door they keep to it (watching you through the glass, waiting for you to open: the
    // waits are shorter, no second ring); once they'd given up on the door: they stare, then in
    if (['peer', 'split', 'probe'].includes(this.phase)) this.set('stare', a.cast);
  }

  heard(a, lead, ctx) {
    if (!lead || ['breakin', 'answered'].includes(this.phase)) return;
    if (lead.source === 'doorbell' || lead.source === 'door_knock' || lead.source === 'door_handle') return;
    const nav = this.sq.world.nav;
    if (lead.source === 'gunshot') { this.knowsHome = true; a.told({ pos: lead.pos, t: a.time, src: 'noise' }); this.goIn('a gunshot', { hunt: true }); return; }
    // something inside the house (or near it)
    if (!nav.inHouse(lead.pos.x, lead.pos.z, 2)) return;
    if (this.t - (this.heardAt ?? -1e9) < 1.0) return;     // (one noise is heard by several)
    this.heardN++;
    const first = this.heardN === 1 || this.t - this.heardAt > 20;
    this.heardAt = this.t;
    this.knowsHome = true;
    this.sq.event('seq_heard', { id: a.id, source: lead.source, n: this.heardN, at: [+lead.pos.x.toFixed(1), +lead.pos.z.toFixed(1)] });
    for (const b of this.members) this.glanceAt(b, lead.pos.clone().setY(1.4), rand(0.1, 0.5), 2.5);
    if (!first && ['ring', 'wait1', 'wait2', 'knock', 'handle', 'peer', 'split', 'probe', 'stare'].includes(this.phase)) {
      for (const b of this.members) b.told({ pos: lead.pos.clone(), t: b.time, src: 'noise' });
      this.goIn('heard someone');
    }
  }

  // a door the player opened: near them, it's an answer; else a prober will find it open
  doorOpened(d) {
    const near = this.members.filter((a) => Math.hypot(a.pos.x - d.centre.x, a.pos.z - d.centre.y) < 6);
    if (!near.length || ['breakin', 'answered'].includes(this.phase)) return;
    this.answeredAt = d;
    this.set('answered', d.name);
  }
  answered(dt) {
    const d = this.answeredAt, c = new V3(d.centre.x, 0, d.centre.y);
    // the beat: they turn to the door; the leader steps up to it
    if (!this.sub.turned) {
      this.sub.turned = true;
      for (const a of this.members) { a.cue = { mode: 'hold', face: c }; }
      const L = this.cast.leader;
      if (L?.state === 'scene' && L.pos.distanceTo(c) < 6) L.cue = { mode: 'go', to: c.clone().add(new V3(0, 0, 0.9 * Math.sign(L.pos.z - c.z || 1))), speed: 1.4, tol: 0.3, face: c };
    }
    if (this.phaseT >= T.beat) this.goIn('the door was opened', { via: this.sq.entries.find((e) => e.door && this.leaves(e).includes(d)) ?? null });
  }

  // ---- seen through the glass: they stare in (the gunmen aim), then the door is kicked in
  stare(dt) {
    const P0 = this.sq.player.pos;
    for (const a of this.members) {
      const near = a.pos.distanceTo(P0) < 22;
      if (!near) continue;
      a.cue = { ...(a.cue?.mode === 'go' && a.pos.distanceTo(a.cue.to) > 0.5 ? a.cue : { mode: 'hold' }), face: P0.clone(), stareAim: a.gun && a !== this.cast.leader };
    }
    if (this.phaseT >= T.stare * Math.max(0.5, this.k)) this.goIn('seen through the glass');
  }

  // ---------------------------------------------------------------- going in
  // the slow part is over: who gets them in where. `via`: an entry already open (go through it);
  // `hunt`: no ceremony (seen outside, a gunshot): straight to their brains
  goIn(reason, { via = null, by = null, hunt = false } = {}) {
    if (['breakin', 'done'].includes(this.phase)) return;
    this.reason ??= reason;
    this.set('breakin', reason);
    const c = this.cast, front = this.entry('entry'), glass = this.entry('glass'), mud = this.entry('mudroom');
    this.jobs = new Map();
    for (const a of this.members) { a.anim.aim = 0; a.holstered = false; }
    if (hunt) { for (const a of this.members) this.handOff(a, null); return; }
    // the second gunman stays outside: a watcher on the nearer post (the front door's, or the
    // north terrace's)
    const B = c.gunB;
    if (B?.state === 'scene') {
      const posts = [front?.post, this.entry('kitchen')?.post].filter(Boolean).sort((p, q) => p.at.distanceTo(B.pos) - q.at.distanceTo(B.pos));
      this.jobs.set(B, { kind: 'watch', post: posts[0] });
    }
    if (via && this.entryOpen(via)) {
      for (const a of this.members) if (!this.jobs.has(a)) this.jobs.set(a, { kind: 'wait' });
      return;
    }
    // the front door: kicked in by the leader (or whoever is nearest it)
    const nearFront = this.members.filter((a) => !this.jobs.has(a) && front).sort((p, q) => p.pos.distanceTo(front.outside) - q.pos.distanceTo(front.outside));
    const kicker = c.leader && c.leader.state === 'scene' && c.leader.pos.distanceTo(front?.outside ?? c.leader.pos) < 16 ? c.leader : nearFront[0];
    if (front && kicker && !this.entryOpen(front)) this.jobs.set(kicker, { kind: 'kick', E: front, at: new V3(front.door.centre.x, 0, front.door.centre.y + 0.85) });
    // the great room's glass: the bat, if he's round there
    if (glass && c.bat?.state === 'scene' && !this.jobs.has(c.bat) && c.bat.pos.distanceTo(glass.outside) < 14) this.jobs.set(c.bat, { kind: 'smash', E: glass });
    // the mudroom's side door: the knife, if he's at it
    if (mud && c.knife?.state === 'scene' && !this.jobs.has(c.knife) && c.knife.pos.distanceTo(mud.outside) < 6) {
      const n = new V3(mud.normal.x, 0, mud.normal.y);
      this.jobs.set(c.knife, { kind: 'kick', E: mud, at: new V3(mud.centre.x, 0, mud.centre.y).addScaledVector(n, 0.85) });
    }
    for (const a of this.members) if (!this.jobs.has(a)) this.jobs.set(a, { kind: 'wait' });
    this.sq.event('seq_jobs', { jobs: [...this.jobs].map(([a, j]) => `${a.cast}:${j.kind}${j.E ? '@' + j.E.name : ''}`).join(' ') });
  }
  breakin(dt) {
    for (const [a, j] of this.jobs ?? []) {
      if (!a.alive || a.handed) continue;
      if (j.kind === 'watch') { this.handOff(a, null, { watch: j.post }); continue; }
      if (j.kind === 'smash') { this.handOff(a, j.E); continue; }
      if (j.kind === 'kick') {
        const D = j.E.door;
        if (!j.started) {
          if (a.state !== 'scene') continue;
          a.cue = { mode: 'go', to: j.at, speed: 2.0, tol: 0.3, face: new V3(D.centre.x, 0, D.centre.y) };
          if (Math.hypot(a.pos.x - j.at.x, a.pos.z - j.at.z) < 0.45 || this.phaseT > 25) {
            j.started = true;
            a.startBreach(D);                        // the brain's breach: four kicks, loud
            this.sq.event('seq_kick', { id: a.id, door: D.name });
          }
          continue;
        }
        // kicked in (the brain's breach unlocked it and came back to `scene`)
        if (a.state === 'scene' && !D.locked()) { for (const d of this.leaves(j.E)) d.latched = false; this.sq.world.nav.components(); this.handOff(a, j.E, { through: true }); }
        continue;
      }
      // waiting for a way in: the nearest open one
      const open = this.sq.entries.filter((e) => this.entryOpen(e)).sort((p, q) => p.outside.distanceTo(a.pos) - q.outside.distanceTo(a.pos));
      if (open.length) this.handOff(a, open[0], { through: a.pos.distanceTo(open[0].outside) < 4 });
      // nothing open after 15 s (the kicker saw the player and turned to fight, or fell): in by the
      // front door anyway (their brain's arrival kicks in a door that's locked to them)
      else if (this.phaseT > 15) this.handOff(a, this.entry('entry'));
      else if (a.state === 'scene' && (!a.cue || a.cue.mode !== 'hold')) a.cue = { mode: 'hold', face: a.cue?.face ?? P.door };
    }
  }

  // to its brain: in through entry E (`through`: it's at the door: straight in), a watcher's post,
  // or (no entry) whatever its brain makes of what it knows
  handOff(a, E = null, { through = false, watch = null } = {}) {
    if (a.handed || !a.alive) return;
    a.handed = true;
    a.cue = null; a.pose = null; a.route = null; a.glances = null; a.holstered = false; a.steering = false;
    a.idleClip = a.cast === 'knife' ? 'IdleAlert' : null;
    a.anim.aim = 0;
    if (watch) { a.role = 'watcher'; a.post = watch; a.set('post', 'opening'); }
    else if (E) { a.entry = E; a.inside = false; a.set('arrive', 'opening'); if (through) a.sub = { phase: 'in' }; }
    else if (a.know && a.time - a.know.t < 30) a.set('pursue', 'opening');
    else { a.entry = this.entry('entry'); a.set('arrive', 'opening'); }
    this.sq.event('seq_handoff', { id: a.id, cast: a.cast, to: a.state, entry: E?.name ?? null });
  }
  // it left the script on its own (hit: its brain took over): everyone else goes too
  left(a) {
    a.handed = true;
    a.holstered = false; a.pose = null; a.steering = false;
    if (!['breakin', 'done'].includes(this.phase)) { this.sq.event('seq_left', { id: a.id, state: a.state }); this.goIn(a.state === 'flee' || a.lastHitAt != null ? 'one of them was hurt' : 'one left', { hunt: a.lastHitAt != null }); }
  }

  // ---------------------------------------------------------------- moving them (every frame)
  pose(a, name, secs, key = name, rate = 1) { if (a?.alive) a.pose = { name, key: `${key}${this.t.toFixed(2)}`, until: this.t + secs / rate, rate }; }
  drive(a, dt) {
    if (a.pose && this.t >= a.pose.until) a.pose = null;
    const c = a.cue ?? { mode: 'hold' };
    a.steering = false;
    let moving = false;
    if (c.mode === 'follow' && c.to) {
      // keep its place: straight at it when the way is open, along a path when it isn't
      const L = this.sq.world.nav.layers[0], d = Math.hypot(c.to.x - a.pos.x, c.to.z - a.pos.z);
      const lv = c.lead?.moveSpeed ?? 1.3;
      if (d > 0.25) {
        const v = Math.min(2.4, Math.max(0, lv + (d - 0.3) * 0.8));
        if (d < 9 && this.sq.world.nav.clearWalk(L, a.pos.x, a.pos.z, c.to.x, c.to.z)) { a.path = null; a.steering = true; a.steer(dt, c.to.x, c.to.z, v); }
        else a.goTo(c.to, Math.max(1.3, v), { moveTol: 0.5, every: 0.6 });
        moving = true;
      } else { a.path = null; a.moveSpeed *= Math.max(0, 1 - dt * 6); a.yawTo(c.lead?.yaw ?? a.yaw, dt, 3); }
    } else if (c.mode === 'go' && c.to) {
      const r = a.goTo(c.to, c.speed ?? 1.4, { moveTol: c.tol ?? 0.35 });
      moving = r === 'moving' || r === 'planning';
      // (the last bit straight: the nav's cells are 0.25 m)
      if (r !== 'moving' && Math.hypot(c.to.x - a.pos.x, c.to.z - a.pos.z) > (c.tol ?? 0.35) && Math.hypot(c.to.x - a.pos.x, c.to.z - a.pos.z) < 1.2 && r !== 'planning') { a.path = null; a.steering = true; a.steer(dt, c.to.x, c.to.z, 0.8); moving = true; }
    } else { a.path = null; }
    // standing: turn to what it faces; the head to what it's glancing at. Someone seen inside
    // while they wait at the door: they watch them through the glass
    const g = (a.glances ?? []).find((x) => this.t >= x.at && this.t < x.until);
    const watch = this.knowsHome && this.t - (this.lastSeenT ?? -1e9) < 3 && ['gather', 'ring', 'wait1', 'wait2', 'knock'].includes(this.phase) && !a.pose;
    if (!moving) {
      if (watch) a.yawTo(yawTo(a.pos, this.sq.player.pos), dt, 2.0);
      else if (c.face) a.yawTo(yawTo(a.pos, c.face), dt, 2.4);
      if (g) a.turnLook(yawTo(a.pos, g.p), dt, 3);
      else if (a.glance && a.time < a.glance.until) a.turnLook(a.glance.yaw, dt, 4);
      else if (c.peer) a.turnLook(a.yaw + Math.sin(this.t * 0.6 + a.id) * 0.5, dt, 1.5);
      else a.turnLook(a.yaw + Math.sin(this.t * 0.25 + a.id * 2) * 0.25, dt, 1.2);
    } else if (g) a.turnLook(yawTo(a.pos, g.p), dt, 3);
    else if (a.glance && a.time < a.glance.until) a.turnLook(a.glance.yaw, dt, 4);
    // guns: low ready, raised while staring in at someone
    if (a.gun) a.anim.aim = c.stareAim ? Math.min(1, a.anim.aim + dt * 2) : Math.max(0, a.anim.aim - dt * 2);
    if (a.glances) a.glances = a.glances.filter((x) => x.until > this.t);
  }

  // ---------------------------------------------------------------- tests
  summary() {
    return { phase: this.phase, t: +this.t.toFixed(1), reason: this.reason, rings: this.rings, knocks: this.knocks, handles: this.handles, knowsHome: !!this.knowsHome, seenBy: this.seenBy?.cast ?? null,
      cast: Object.fromEntries(Object.entries(this.cast).map(([k, a]) => [k, { id: a.id, state: a.state, pos: [+a.pos.x.toFixed(2), +a.pos.z.toFixed(2)], alive: a.alive }])), timeline: this.timeline };
  }
}
