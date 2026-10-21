import * as THREE from 'three';
import { NavGrid, MAIN_SPACES, DOUBLE_HEIGHT } from './grimble_nav.js';

// The Grimble inside: after a few rounds of knocking it smashes the great room's west glass and
// crawls through the main spaces hunting the player. It can't fit through the side rooms'
// doors (the nav grid simply has no way in), so they're safe; from the double-height rooms it
// can rear up and swipe at the upper gallery over the balustrades. A swipe knocks the player
// down; they get up again.
//
// States: smash -> enter (crawl in) -> chase (sees the player) | search (last seen / a noise)
// | prowl (wander) | wait (player out of reach: lurk near them) | swipe | reachUp | recover.
// It sees the player when a ray from its head reaches their eye past the house's walls and
// any closed blinds (furniture doesn't hide you from something this size), within `sight` m.
//
// The body. On all fours it is ~5 m long and ~2.6 m wide, in galleries 3.2 m wide: a rigid
// footprint can't turn their corners. So it moves like a long animal, a chain of three points
// on the floor: the head end (`hd`, steered along the path), the spine's base (`q`, the bend)
// and the hindquarters (`b`), each following the one in front at a fixed distance
// (follow-the-leader). Circles along the chain are pushed out of the walls every frame (walls
// are never switched off), and the skeleton is bent to match after the animation runs: the root
// lies along the hindquarters (q - b) and Spine1-3 turn the chest onto the head end (hd - q); the
// staff, which the right hand drags, is turned back the same way so it trails the hindquarters.
// It steers at a point ~2 m ahead along its path (pure pursuit), so it never circles a waypoint.

const DEFAULTS = {
  loopsBeforeSmash: 2,     // knock-wave-stare rounds at the glass before it breaks in
  crawlStride: 3.0, crawlCycle: 1.6,      // m / s per Crawl cycle (asset userData overrides)
  fastStride: 4.4, fastCycle: 1.2,        // CrawlFast
  smashHit: 1.2,           // s into Smash when the glass breaks
  swipeHit: 0.7, swipeReach: 2.8, swipeLen: 1.6,
  reachHit: 1.6, reachLen: 3.0, reachUp: 2.2,   // horizontal reach of ReachUp (m)
  sight: 40, hearing: 30,  // m
  turnRate: 2.4,           // rad/s the head end turns
  memory: 6,               // s it keeps chasing where it last saw you
  cooldown: 3.5,           // s after a hit before it can hit again
  getaway: 2.0,            // ... and s after the player is back on their feet
  crawlRate: 2.0,          // playback rate of Crawl / CrawlFast (speed scales with it, so no sliding):
  fastRate: 2.6,           //   ~1.2 m/s prowling, ~5 m/s chasing (the player walks 3.4, runs 6.8)
  upperY: 3.5,             // player feet above this = on the upper floor
  strikeRange: 1.6,        // m beyond its head within which it swipes
  lookAhead: 2.0,          // m along the path it steers at
  maxBend: 1.1,            // rad between the chest and the hindquarters
  navMargin: 0.12,         // the route keeps (half width - this) off walls; the circles do the rest
};

const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
const _q = new THREE.Quaternion(), _pq = new THREE.Quaternion(), _up = new THREE.Vector3(0, 1, 0);

// a bone pose() turns: if the animation doesn't key it (the Staff in some clips), the mixer
// leaves last frame's turned value there, so put back what it was before the turn first
function unturn(bone) {
  if (!bone) return;
  const u = bone.userData;
  if (u.turned && bone.quaternion.equals(u.turned)) bone.quaternion.copy(u.before);
  if (u.moved && bone.position.equals(u.moved)) bone.position.copy(u.beforeP);
  u.before = bone.quaternion.clone();
  u.beforeP = bone.position.clone();
}
function markTurned(bone) { if (bone) { bone.userData.turned = bone.quaternion.clone(); bone.userData.moved = bone.position.clone(); } }

// turn a bone by `a` radians about the world vertical, about its own origin
function yawBone(bone, a) {
  if (!bone || Math.abs(a) < 1e-5) return;
  bone.parent.getWorldQuaternion(_pq);
  _q.setFromAxisAngle(_up, a);
  _q.premultiply(_pq.clone().invert()).multiply(_pq);
  bone.quaternion.premultiply(_q);
  bone.updateMatrixWorld(true);
}

// ... about a world point instead (the staff turns in the hand that holds it, not about its own
// origin, which is its far end)
function yawAbout(bone, a, pivot) {
  if (!bone || Math.abs(a) < 1e-5) return;
  const p = bone.getWorldPosition(new THREE.Vector3()).sub(pivot), c = Math.cos(a), s = Math.sin(a);
  const np = new THREE.Vector3(pivot.x + p.x * c + p.z * s, pivot.y + p.y, pivot.z - p.x * s + p.z * c);
  bone.position.copy(bone.parent.worldToLocal(np));
  yawBone(bone, a);
}

export class GrimbleHunt {
  constructor(grimble, { level, colliders, scene, sightBlockers = () => [], opts = {} }) {
    this.g = grimble;
    this.o = { ...DEFAULTS, ...opts };
    const ud = grimble.root.userData;
    for (const [k, u] of [['crawlStride', 'crawlStride'], ['crawlCycle', 'crawlCycle'], ['fastStride', 'fastStride'],
      ['fastCycle', 'fastCycle'], ['smashHit', 'smashHit'], ['swipeHit', 'swipeHit'], ['swipeReach', 'swipeReach'],
      ['reachHit', 'reachHit'], ['reachUp', 'reachUpReach']]) if (ud[u] !== undefined) this.o[k] = ud[u];
    for (const n of ['Smash', 'Swipe', 'ReachUp']) {
      const a = grimble.actions[n];
      if (a) { a.setLoop(THREE.LoopOnce); a.clampWhenFinished = true; }
    }
    if (grimble.actions.Crawl) grimble.actions.Crawl.timeScale = this.o.crawlRate;
    if (grimble.actions.CrawlFast) grimble.actions.CrawlFast.timeScale = this.o.fastRate;
    this.level = level;
    this.scene = scene;
    this.sightBlockers = sightBlockers;
    this.measureBody();
    // walls for sight: the shell's colliders only (props don't hide you from it)
    // (not the balustrades' invisible anti-vault boxes: it sees over a glass rail. They're
    // tagged seeThrough in the level, or recognised as thin 2.2 m-tall boxes in older levels)
    const rail = (c) => c.seeThrough || (Math.abs(c.max[1] - c.min[1] - 2.2) < 0.05 &&
      Math.min(c.max[0] - c.min[0], c.max[2] - c.min[2]) <= 0.12);
    this.walls = level.colliders.filter((c) => !rail(c))
      .map((c) => new THREE.Box3(new THREE.Vector3(...c.min), new THREE.Vector3(...c.max)));
    this.rooms = MAIN_SPACES.filter((r) => level.rooms[r]).map((r) => level.rooms[r].rect);
    const areas = this.rooms.slice();
    this.breakable = (level.breakables || [])[0];
    if (this.breakable) {           // the lawn in front of the glass it breaks, so it can come through
      const b = this.breakable, z0 = Math.min(b.min[2], b.max[2]), z1 = Math.max(b.min[2], b.max[2]);
      areas.push([Math.min(b.min[0], b.max[0]) - 6, z0 - 1, Math.max(b.min[0], b.max[0]) + 0.5, z1 + 1]);
    }
    this.nav = new NavGrid(colliders, areas, { cell: 0.2, radius: this.body.w - this.o.navMargin });
    // what its body is kept out of: the shell's walls (not the glass it breaks through)
    const b = this.breakable;
    const gap = b && new THREE.Box3(new THREE.Vector3(Math.min(b.min[0], b.max[0]) - 0.3, 0, Math.min(b.min[2], b.max[2])),
      new THREE.Vector3(Math.max(b.min[0], b.max[0]) + 0.3, 9, Math.max(b.min[2], b.max[2])));
    this.solid = this.walls.filter((c) => c.max.y > 0.4 && c.min.y < 2.8 && !(gap && gap.intersectsBox(c) && c.max.x - c.min.x < 0.5));
    this.double = DOUBLE_HEIGHT.filter((r) => level.rooms[r]).map((r) => level.rooms[r].rect);
    this.state = null;
    this.t = 0;
    this.path = null;
    this.lastSeen = null;
    this.seenAt = -1e9;
    this.time = 0;
    this.hitAt = -1e9;
    this.noise = null;
    this.chain = null;
    this.bodyYaw = null;
    this.pathAt = -1e9;
    this.stats = { unsticks: 0, replans: 0 };
    // the player can't walk into it: three boxes round the chain's points, added to the shared
    // colliders (so thrown things bounce off it too); parked under the ground until it's inside
    this.blockers = [0, 1, 2].map(() => new THREE.Box3(new THREE.Vector3(0, -101, 0), new THREE.Vector3(0, -100, 0)));
    colliders.push(...this.blockers);
    window.__noise?.on?.((n) => this.hear(n));
    this._ray = new THREE.Ray();
    window.__hunt = this;
  }

  // the crawl's proportions, measured off the skinned mesh in the Crawl loop (root-local, front
  // +z): front tip, back of the cloak, half width, the staff's tail, and the spine's base (the
  // bend). The chain and its circles are laid out from these.
  measureBody() {
    const g = this.g, a = g.actions.Crawl, ud = g.root.userData;
    const spine = ['Spine1', 'Spine2', 'Spine3'].map((n) => g.root.getObjectByName(n));
    this.spine = spine;
    this.staffBone = g.root.getObjectByName('Staff');
    let zf = -1e9, zb = 1e9, w = 0, zs = 1e9, xs = 0, zp = 0, np = 0, tailI = -1, far = 0;
    this.hand = g.root.getObjectByName('HandR');
    if (a && spine[0]) {
      const meshes = [];
      g.root.traverse((o) => { if (o.isSkinnedMesh) meshes.push(o); });
      const pos0 = g.root.position.clone(), rot0 = g.root.rotation.y;
      g.root.position.set(0, 0, 0); g.root.rotation.set(0, 0, 0);
      g.mixer.stopAllAction();
      a.reset().play();
      const T = a.getClip().duration / a.timeScale, v = new THREE.Vector3();
      for (let s = 0; s < 6; s++) {
        g.mixer.setTime((T * s) / 6);
        g.root.updateMatrixWorld(true);
        const hand = this.hand ? this.hand.getWorldPosition(new THREE.Vector3()) : null;
        for (const m of meshes) {
          const staff = /Staff/.test(m.name), P = m.geometry.attributes.position;
          for (let i = 0; i < P.count; i += 9) {
            v.fromBufferAttribute(P, i); m.applyBoneTransform(i, v); v.applyMatrix4(m.matrixWorld);
            if (staff) {
              if (v.z < zs) { zs = v.z; xs = v.x; }
              // the staff's far end: its vertex farthest from the hand holding it
              if (s === 0 && hand) { const d = v.distanceTo(hand); if (d > far) { far = d; tailI = i; this.staffMesh = m; } }
              continue;
            }
            zf = Math.max(zf, v.z); zb = Math.min(zb, v.z); w = Math.max(w, Math.abs(v.x));
          }
        }
        zp += spine[0].getWorldPosition(v).z; np++;
      }
      a.stop();
      g.mixer.stopAllAction();
      g.mixer.setTime(0);
      g.current = null;
      g.root.position.copy(pos0); g.root.rotation.y = rot0;
      zp /= np;
    } else {
      zf = ud.bodyFront ?? 2.4; zb = -(ud.bodyBack ?? 2.4); w = ud.bodyHalfWidth ?? 1.3; zs = zb; zp = -0.4;
    }
    // the chain: the head end's circle reaches the front tip, the hindquarters' circle the cloak's back
    const r = w;
    const zh = Math.max(zp + 0.8, zf - r), zr = Math.min(zp - 0.4, zb + r);
    this.body = { zf, zb, w, r, zp, zh, zr, Lf: zh - zp, Lb: zp - zr, staffTail: [xs, zs], tailR: 0.25 };
    this.staffTailI = tailI;
  }

  get root() { return this.g.root; }
  pos2() { return new THREE.Vector2(this.root.position.x, this.root.position.z); }

  hear(n) {
    const p = n.position, d = Math.hypot(p.x - this.root.position.x, p.z - this.root.position.z);
    if (d <= this.o.hearing * (n.loudness ?? 1)) this.noise = new THREE.Vector2(p.x, p.z);
  }

  start() { this.set('smash'); this.g.play('Smash'); }

  set(state) { this.state = state; this.t = 0; }

  // ---------------------------------------------------------------- the body chain
  // lay the chain out straight along the root's heading (after Smash, in the crawl rest pose)
  startChain() {
    const B = this.body, h = this.g.heading, f = new THREE.Vector2(Math.sin(h), Math.cos(h)), R = this.pos2();
    const q = R.clone().addScaledVector(f, B.zp);
    this.chain = { hd: q.clone().addScaledVector(f, B.Lf), q, b: q.clone().addScaledVector(f, -B.Lb), hf: h };
    this.placeRoot();
  }

  frontYaw() { const c = this.chain; return Math.atan2(c.hd.x - c.q.x, c.hd.y - c.q.y); }
  rearYaw() { const c = this.chain; return Math.atan2(c.q.x - c.b.x, c.q.y - c.b.y); }
  // the front tip (its claws / face) on the floor
  tip() {
    const c = this.chain, h = this.frontYaw(), d = this.body.zf - this.body.zh;
    return new THREE.Vector2(c.hd.x + Math.sin(h) * d, c.hd.y + Math.cos(h) * d);
  }

  // turn the head end by up to `rate * dt` toward a point (it swings about the spine's base);
  // returns how far off it still is
  turnHead(target, dt, rate = this.o.turnRate) {
    const c = this.chain;
    const want = Math.atan2(target.x - c.hd.x, target.y - c.hd.y);
    const d = wrap(want - c.hf);
    const s = Math.sign(d) * Math.min(Math.abs(d), rate * dt);
    c.hf += s;
    // the front segment swings with it
    const v = c.hd.clone().sub(c.q), cs = Math.cos(s), sn = Math.sin(s);
    // (yaw a: x' = x cos a + z sin a, z' = -x sin a + z cos a for atan2(x, z) headings)
    c.hd.set(c.q.x + v.x * cs + v.y * sn, c.q.y - v.x * sn + v.y * cs);
    return Math.abs(d) - Math.abs(s);
  }

  // push a circle (centre p, radius r) out of the walls; returns the push
  pushCircle(p, r) {
    let px = 0, pz = 0;
    for (const c of this._near) {
      const cx = Math.min(Math.max(p.x + px, c.min.x), c.max.x), cz = Math.min(Math.max(p.y + pz, c.min.z), c.max.z);
      const dx = p.x + px - cx, dz = p.y + pz - cz, d = Math.hypot(dx, dz);
      if (d >= r) continue;
      if (d > 1e-6) { px += (dx / d) * (r - d); pz += (dz / d) * (r - d); continue; }
      // centre inside a (thin) wall box: out the side the spine's base is on
      const sx = (this.chain.q.x < (c.min.x + c.max.x) / 2) ? c.min.x - r - (p.x + px) : c.max.x + r - (p.x + px);
      const sz = (this.chain.q.y < (c.min.z + c.max.z) / 2) ? c.min.z - r - (p.y + pz) : c.max.z + r - (p.y + pz);
      if (Math.abs(sx) < Math.abs(sz)) px += sx; else pz += sz;
    }
    return [px, pz];
  }

  // follow-the-leader + the walls, a few rounds
  solveChain() {
    const c = this.chain, B = this.body, r = B.r;
    const R = B.Lf + B.Lb + r + 1.5;
    this._near = this.solid.filter((w) => w.distanceToPoint(new THREE.Vector3(c.q.x, Math.min(Math.max(1.2, w.min.y), w.max.y), c.q.y)) < R);
    const follow = () => {
      const f = c.q.clone().sub(c.hd); const lf = f.length() || 1;
      c.q.copy(c.hd).addScaledVector(f, B.Lf / lf);
      const k = c.b.clone().sub(c.q); const lb = k.length() || 1;
      c.b.copy(c.q).addScaledVector(k, B.Lb / lb);
      // the bend: past maxBend the hindquarters swing round (it pivots on the spine's base)
      const hf = this.frontYaw(), hr = this.rearYaw(), bend = wrap(hf - hr);
      if (Math.abs(bend) > this.o.maxBend) {
        const a = hf - Math.sign(bend) * this.o.maxBend;
        c.b.set(c.q.x - Math.sin(a) * B.Lb, c.q.y - Math.cos(a) * B.Lb);
      }
    };
    const add = (p, d, s = 1) => { p.x += d[0] * s; p.y += d[1] * s; };
    for (let it = 0; it < 3; it++) {
      follow();
      add(c.hd, this.pushCircle(c.hd, r));
      const m1 = c.hd.clone().add(c.q).multiplyScalar(0.5), d1 = this.pushCircle(m1, r);
      add(c.hd, d1); add(c.q, d1);
      add(c.q, this.pushCircle(c.q, r));
      const m2 = c.q.clone().add(c.b).multiplyScalar(0.5), d2 = this.pushCircle(m2, r);
      add(c.q, d2); add(c.b, d2);
      add(c.b, this.pushCircle(c.b, r));
      const t = this.staffTailPoint(), dt = this.pushCircle(t, B.tailR);
      add(c.b, dt);
    }
    follow();
  }

  staffTailPoint() {
    const c = this.chain, hr = this.rearYaw(), [xs, zs] = this.body.staffTail;
    const lz = zs - this.body.zp;        // relative to the spine's base, along the hindquarters
    // local (x, z) -> world for heading hr: x axis = (cos hr, -sin hr), z axis = (sin hr, cos hr)
    return new THREE.Vector2(c.q.x + Math.cos(hr) * xs + Math.sin(hr) * lz, c.q.y - Math.sin(hr) * xs + Math.cos(hr) * lz);
  }

  // the root lies along the hindquarters with the spine's base on q
  placeRoot() {
    const c = this.chain, hr = this.rearYaw();
    this.root.position.x = c.q.x - Math.sin(hr) * this.body.zp;
    this.root.position.z = c.q.y - Math.cos(hr) * this.body.zp;
    this.root.position.y = 0;
    this.bodyYaw = hr;
    this.g.heading = c.hf;
  }

  // after the animation: bend the spine onto the head end, and the staff back onto the hindquarters
  pose() {
    if (!this.chain || this.state === 'smash') return;
    const bend = wrap(this.frontYaw() - this.rearYaw());
    for (const b of [...this.spine, this.staffBone]) unturn(b);
    this.root.updateMatrixWorld(true);
    const share = [0.4, 0.35, 0.25];
    this.spine.forEach((b, i) => yawBone(b, bend * share[i]));
    const grip = this.hand ? this.hand.getWorldPosition(new THREE.Vector3()) : null;
    if (grip) yawAbout(this.staffBone, -bend, grip);
    this.spine.forEach(markTurned);
    markTurned(this.staffBone);
    // the dragged staff's tip skates along a wall rather than going into it: swing the staff
    // about the hand by however much the walls push its tip
    const m = this.staffMesh, sb = this.staffBone;
    if (!m || !sb || !grip || this.staffTailI < 0 || !this._near) return;
    const v = new THREE.Vector3().fromBufferAttribute(m.geometry.attributes.position, this.staffTailI);
    m.applyBoneTransform(this.staffTailI, v); v.applyMatrix4(m.matrixWorld);
    // points along the shaft (a door jamb catches its middle, a wall its tip)
    let da = 0;
    // (and the bit of shaft ahead of the hand)
    for (const f of [-0.35, -0.2, 0.25, 0.4, 0.55, 0.7, 0.85, 1.0]) {
      const x = grip.x + (v.x - grip.x) * f, z = grip.z + (v.z - grip.z) * f;
      const d = this.pushCircle(new THREE.Vector2(x, z), 0.16);
      if (!d[0] && !d[1]) continue;
      const a = wrap(Math.atan2(x + d[0] - grip.x, z + d[1] - grip.z) - Math.atan2(x - grip.x, z - grip.z));
      if (Math.abs(a) > Math.abs(da)) da = a;
    }
    this.staffDa = da;
    if (!da) return;
    yawAbout(sb, Math.sign(da) * Math.min(Math.abs(da) * 1.15, 1.2), grip);
    markTurned(sb);
  }

  // ---------------------------------------------------------------- perception
  sees(eye) {
    const head = this.root.position.clone().add(new THREE.Vector3(0, 2.4, 0));
    if (this.chain) head.set(this.chain.hd.x, 2.2, this.chain.hd.y);
    const to = eye.clone().sub(head), d = to.length();
    if (d > this.o.sight) return false;
    this._ray.set(head, to.normalize());
    const hit = new THREE.Vector3();
    for (const b of this.walls.concat(this.sightBlockers())) {
      if (b.containsPoint(head)) continue;
      if (this._ray.intersectBox(b, hit) && hit.distanceTo(head) < d - 0.3) return false;
    }
    return true;
  }

  // nothing solid between its head end and the player (it can't swipe through a wall)
  clearTo(feet, fromY = 1.2) {
    return this.clearBetween(new THREE.Vector3(this.chain.hd.x, fromY, this.chain.hd.y), new THREE.Vector3(feet.x, feet.y + 1.0, feet.z));
  }

  clearBetween(a, b) {
    const to = b.clone().sub(a), d = to.length();
    this._ray.set(a, to.normalize());
    const hit = new THREE.Vector3();
    for (const w of this.walls) {
      if (w.containsPoint(a)) continue;
      if (this._ray.intersectBox(w, hit) && hit.distanceTo(a) < d - 0.1) return false;
    }
    return true;
  }

  // in a double-height room, at least m inside it (a doorway's cells are on both rooms' edges)
  inDouble(x, z, m = 0.4) { return this.double.some((r) => x >= r[0] + m && x <= r[2] - m && z >= r[1] + m && z <= r[3] - m); }
  roomOf(x, z) { return this.rooms.find((r) => x >= r[0] && x <= r[2] && z >= r[1] && z <= r[3]); }

  // ---------------------------------------------------------------- movement
  goTo(target) {
    const c = this.chain, from = c ? c.hd : this.pos2();
    // start in the room its head is in (the nearest cell may be across a glass wall)
    const room = this.roomOf(from.x, from.y);
    const prefer = room ? (x, z) => x >= room[0] && x <= room[2] && z >= room[1] && z <= room[3] : null;
    this.path = this.withOwnBody(() => this.nav.path(from, target, prefer));
    this.pathAt = this.time;
    this.pathI = 0;
    this.goal = target.clone();
    this.stats.replans++;
    return !!this.path;
  }

  // its own body is in the way (it can't crawl back over itself): the cells under its
  // hindquarters and spine are blocked while `fn` plans
  withOwnBody(fn) {
    const c = this.chain, saved = [];
    if (c) {
      const n = this.nav;
      const blockAround = (p, rad) => {
        const R = Math.ceil(rad / n.cell), ci = Math.floor((p.x - n.x0) / n.cell), cj = Math.floor((p.y - n.z0) / n.cell);
        for (let dj = -R; dj <= R; dj++) for (let di = -R; di <= R; di++) {
          const i = ci + di, j = cj + dj;
          if (i < 0 || j < 0 || i >= n.w || j >= n.h || (di * di + dj * dj) * n.cell * n.cell > rad * rad) continue;
          const k = j * n.w + i;
          if (!n.blocked[k]) { saved.push(k); n.blocked[k] = 1; }
        }
      };
      blockAround(c.b, this.body.r);
      blockAround(c.q.clone().add(c.b).multiplyScalar(0.5), this.body.r * 0.9);
      blockAround(c.q, Math.min(this.body.r, this.body.Lf - 0.35));
    }
    try { return fn(); } finally { for (const k of saved) this.nav.blocked[k] = 0; }
  }

  // the nearest place ahead with room to turn round in (pivoting on its spine's base)
  turnSpot() {
    const n = this.nav, c = this.chain;
    if (!n.clear) return null;
    const need = Math.max(this.body.Lf, this.body.Lb) + this.body.r + 0.15 - n.radius;
    const k = this.withOwnBody(() => n.search(c.hd.x, c.hd.y, (kk) => n.clear[kk] >= need));
    return k >= 0 ? n.centre(k) : null;
  }

  // the point `look` metres along the path ahead of the head end's closest point on it
  carrot(look) {
    const P = this.path, h = this.chain.hd;
    if (P.length === 1) return P[0];
    let bi = this.pathI, bt = 0, bd = Infinity;
    for (let i = this.pathI; i < P.length - 1 && i < this.pathI + 4; i++) {
      const a = P[i], s = P[i + 1].clone().sub(a), L2 = s.lengthSq() || 1;
      const t = Math.min(1, Math.max(0, h.clone().sub(a).dot(s) / L2));
      const d = a.clone().addScaledVector(s, t).distanceTo(h);
      if (d < bd) { bd = d; bi = i; bt = t; }
    }
    this.pathI = bi;
    let left = look, i = bi, at = P[i].clone().lerp(P[i + 1], bt);
    while (i < P.length - 1) {
      const seg = P[i + 1].distanceTo(at);
      if (seg >= left) return at.lerp(P[i + 1], left / seg);
      left -= seg; at = P[i + 1].clone(); i++;
    }
    return P[P.length - 1];
  }

  follow(dt, fast) {
    if (!this.path || !this.path.length) return true;
    const o = this.o, c = this.chain;
    const speed = fast ? (o.fastStride / o.fastCycle) * o.fastRate : (o.crawlStride / o.crawlCycle) * o.crawlRate;
    const end = this.path[this.path.length - 1];
    if (c.hd.distanceTo(end) < 0.7) { this.path = null; return true; }
    const target = this.carrot(o.lookAhead);
    const off = this.turnHead(target, dt);
    // forward along its facing, slowing in a tight turn; a target behind it: turn on the spot
    const k = off > 1.9 ? 0 : Math.max(0.3, Math.cos(Math.min(off, Math.PI / 2)));
    const step = speed * dt * k;
    c.hd.x += Math.sin(c.hf) * step;
    c.hd.y += Math.cos(c.hf) * step;
    this.g.play(fast ? 'CrawlFast' : 'Crawl');
    return false;
  }

  // backing out of a jam: the hindquarters lead for a moment, then it replans
  reverse(dt) {
    const c = this.chain, B = this.body;
    const back = c.b.clone().sub(c.q).normalize();
    c.b.addScaledVector(back, 1.2 * dt);
    const k = c.q.clone().sub(c.b); c.q.copy(c.b).addScaledVector(k, B.Lb / (k.length() || 1));
    const f = c.hd.clone().sub(c.q); c.hd.copy(c.q).addScaledVector(f, B.Lf / (f.length() || 1));
    c.hf = this.frontYaw();
    this.g.play('Crawl');
  }

  // ---------------------------------------------------------------- the brain
  update(dt, eye, player) {
    const o = this.o, g = this.g;
    this.time += dt;
    this.t += dt;
    const feet = player?.pos ?? eye;
    const pp = new THREE.Vector2(feet.x, feet.z);
    const upper = feet.y > o.upperY;
    const seen = this.state !== 'smash' && this.sees(eye);
    if (seen) { this.lastSeen = pp.clone(); this.seenAt = this.time; }
    // after a knockdown the player gets `getaway` s on their feet before it can hit them again
    if (player?.knocked) this._wasDown = true;
    else if (this._wasDown) { this._wasDown = false; this.upAt = this.time; }
    const canHit = this.time - this.hitAt > o.cooldown && this.time - (this.upAt ?? -1e9) > o.getaway && !player?.knocked;

    if (this.state === 'smash') {
      if (this.t >= o.smashHit && !this.broken) { this.broken = true; this.onBreak?.(); this.openGap(); }
      const len = g.actions.Smash?.getClip().duration ?? 2.5;
      if (this.t >= len) { this.set('prowl'); this.path = null; this.startChain(); }
      g.root.rotation.y = g.heading;
      return;
    }
    const tip = this.tip();
    const headDist = tip.distanceTo(pp);
    switch (this.state) {
      case 'swipe': case 'reachUp': {
        const hitT = this.state === 'swipe' ? o.swipeHit : o.reachHit;
        const len = this.state === 'swipe' ? o.swipeLen : o.reachLen;
        this.turnHead(pp, dt);
        if (!this.hitDone && this.t >= hitT) {
          this.hitDone = true;
          const vertOk = this.state === 'swipe' ? !upper : upper;
          // (the reach: claws come over the balustrade from above the upper floor)
          const inReach = this.state === 'swipe' ? headDist <= o.strikeRange + 0.6 && this.clearTo(feet)
            : headDist <= o.reachUp + 0.9 && this.clearTo(feet, feet.y + 1.6);
          if (inReach && vertOk && player?.knockDown) {
            const from = new THREE.Vector3(this.chain.hd.x, feet.y, this.chain.hd.y);
            player.knockDown(from);
            this.hitAt = this.time;
          }
        }
        if (this.t >= len) this.set(seen ? 'chase' : 'search');
        break;
      }
      default: {
        if (this.unstickUntil > this.time) { this.reverse(dt); break; }
        // close enough to strike? (measured from its head; up close it turns on the player fast
        // and swipes whether or not it "sees" them)
        // (next to any part of it, behind it too: it whips round)
        const c = this.chain, nearBody = Math.min(c.hd.distanceTo(pp), c.q.distanceTo(pp), c.b.distanceTo(pp)) <= this.body.r + 1.2;
        const close = !upper && (headDist <= o.strikeRange || nearBody) && this.clearTo(feet);
        // (a player right behind it in a gallery: it can't turn round there, so it doesn't try on
        // the spot; the chase below takes it on to somewhere it can, its own body in the way)
        const behind = Math.abs(wrap(Math.atan2(pp.x - c.q.x, pp.y - c.q.y) - this.frontYaw())) > 1.9;
        if (close && canHit && !(behind && this.cantTurn)) {
          const off = this.turnHead(pp, dt, o.turnRate * 2);
          if (off < 0.6) { this.strike('swipe'); break; }
          // the head end didn't swing (walls): give up turning here
          this._turnTry = (this._turnTry || 0) + dt;
          if (this._turnTry > 0.6) { this.cantTurn = true; this._turnTry = 0; }
          g.play('CrawlIdle');
          break;
        }
        if (!behind) this.cantTurn = false;
        this._turnTry = 0;
        if (behind && this.cantTurn && this.time - this.seenAt > 0.3) { this.lastSeen = pp.clone(); this.seenAt = this.time; }
        // (just under the balustrade it can't see up over the edge: it knows they're there)
        if ((seen || this.time - this.seenAt < o.memory) && canHit) {
          // reach up from where its head is, and only with its head under open sky / a double-height void
          // (all of it in the double-height room: rearing up to full height anywhere else goes
          // through a ceiling)
          const c = this.chain;
          if (upper && headDist <= o.reachUp + 0.5 && this.inDouble(c.q.x, c.q.y) &&
            this.inDouble(c.b.x, c.b.y) && this.clearTo(feet, feet.y + 1.6) && this.turnHead(pp, dt) < 0.5) {
            this.strike('reachUp'); break;
          }
        }
        if (seen || this.time - this.seenAt < o.memory) {
          // chase toward the player (or the nearest place below them), re-planning twice a second
          // upstairs: the place to reach up from is the nearest spot in a double-height room
          let target = this.lastSeen;
          // they're behind it and there's no room to turn here (a gallery): on to the nearest
          // place there is, turn there, come back (rather than all the way round the ring)
          const n = this.nav, kq = n.idx(c.q.x, c.q.y);
          const roomHere = n.clear && kq >= 0 && n.clear[kq] >= Math.max(this.body.Lf, this.body.Lb) + this.body.r + 0.15 - n.radius;
          if (behind && !roomHere && !upper) {
            if (!this.turnAt) this.turnAt = this.turnSpot();
            if (this.turnAt && c.hd.distanceTo(this.turnAt) > 1.0) target = this.turnAt;
          } else this.turnAt = null;
          const spot = upper ? this.reachSpot(this.lastSeen, feet.y) : null;
          if (spot) {
            // come at it from inside the room: arriving head-first from a doorway leaves the body
            // under a low ceiling, so first go deeper in (away from the player), then turn back
            const c = this.chain, inRoom = this.inDouble(c.q.x, c.q.y) && this.inDouble(c.b.x, c.b.y);
            if (!inRoom && !this.stage && c.hd.distanceTo(spot) < 1.2) {
              const u = spot.clone().sub(this.lastSeen).normalize();
              this.stage = this.nav.centre(this.nav.nearest(spot.x + u.x * (this.body.Lf + this.body.Lb + 1.6), spot.y + u.y * (this.body.Lf + this.body.Lb + 1.6), 4));
              this.pathAt = -1e9;
            }
            if (this.stage && c.hd.distanceTo(this.stage) < 1.0) { this.stage = null; this.pathAt = -1e9; }
            target = this.stage ?? spot;
          } else this.stage = null;
          if (this.state !== 'chase') this.path = null;
          this.state = 'chase';
          if (this.time - this.pathAt > 0.5) this.goTo(target);
          if (!this.path || this.follow(dt, true)) this.lurk(dt, pp);
        } else if (this.noise) {
          if (this.state !== 'search' || !this.path) { this.set('search'); if (!this.goTo(this.noise)) this.noise = null; }
          if (this.follow(dt, false)) { this.noise = null; this.path = null; this.set('prowl'); this.idleFor = 3; }
        } else {
          // prowl: wander between random places it can reach in the main spaces, pausing to sniff
          if (this.state !== 'prowl') { this.set('prowl'); this.path = null; }
          if (this.idleFor > 0) { this.idleFor -= dt; g.play('CrawlIdle'); break; }
          if (!this.path) { if (!this.goTo(this.randomSpot())) this.idleFor = 0.3; }
          else if (this.follow(dt, false)) { this.path = null; this.idleFor = 2 + Math.random() * 4; }
        }
      }
    }
    this.solveChain();
    this.chain.hf = this.frontYaw();      // its facing is its chest's (walls may have stopped a turn)
    // jammed (a path to follow, still far from it, under 0.4 m of progress in 2.5 s): back up and replan
    const moving = this.path && ['chase', 'search', 'prowl'].includes(this.state) && !(this.unstickUntil > this.time);
    const hd = this.chain.hd;
    if (!moving || !this._prog || hd.distanceTo(this._prog.at) > 0.4) this._prog = { at: hd.clone(), t: this.time };
    else if (this.time - this._prog.t > 2.5 && this.goal && hd.distanceTo(this.goal) > 2.5) {
      this.unstickUntil = this.time + 1.0; this.path = null; this.stats.unsticks++; this._prog = null;
    }
    this.placeRoot();
    this.updateBlockers(player);
  }

  updateBlockers(player) {
    const c = this.chain, s = this.body.r * 0.8, h = this.state === 'reachUp' ? 6 : 2.5;
    [c.hd, c.q, c.b].forEach((p, i) => {
      this.blockers[i].min.set(p.x - s, 0, p.y - s);
      this.blockers[i].max.set(p.x + s, h, p.y + s);
      player?.pushOutOf?.(this.blockers[i]);
    });
  }

  // out of reach (a side room, upstairs away from the balustrade): wait near, watching
  lurk(dt, pp) {
    if (!this.cantTurn) this.turnHead(pp, dt);
    this.g.play('CrawlIdle');
  }

  strike(kind) {
    this.set(kind);
    this.hitDone = false;
    this.path = null;
    this.g.play(kind === 'swipe' ? 'Swipe' : 'ReachUp');
  }

  // the walkable cell in a double-height room nearest a player on the upper floor, close enough
  // that the claws get to them from there (its head end there, the tip toward them)
  reachSpot(p, y0 = 4.6) {
    const key = `${Math.round(p.x * 2)},${Math.round(p.y * 2)},${Math.round(y0)}`;
    if (this._reachKey === key) return this._reach;
    const maxD = this.o.reachUp + 0.5 + (this.body.zf - this.body.zh) - 0.2;
    const n = this.nav, R = Math.ceil(maxD / n.cell), ci = Math.floor((p.x - n.x0) / n.cell), cj = Math.floor((p.y - n.z0) / n.cell);
    const cands = [];
    for (let dj = -R; dj <= R; dj++) for (let di = -R; di <= R; di++) {
      const i = ci + di, j = cj + dj;
      if (i < 0 || j < 0 || i >= n.w || j >= n.h) continue;
      const k = j * n.w + i;
      if (!n.walkable(k)) continue;
      const c = n.centre(k), d = c.distanceTo(p);
      if (d >= maxD || !this.inDouble(c.x, c.y)) continue;
      // its head end there, facing the player: the rest of the body has to be in the room too
      const ux = (c.x - p.x) / (d || 1), uz = (c.y - p.y) / (d || 1), back = this.body.Lf + this.body.Lb + 0.6;
      if (this.inDouble(c.x + ux * back, c.y + uz * back)) cands.push([d, c]);
    }
    // nearest first; the first the claws can get to the player from (no glass or wall between)
    cands.sort((a, b) => a[0] - b[0]);
    let best = null;
    for (const [, c] of cands) {
      if (this.clearBetween(new THREE.Vector3(c.x, y0 + 1.6, c.y), new THREE.Vector3(p.x, y0 + 1.0, p.y))) { best = c; break; }
    }
    this._reachKey = key; this._reach = best;
    return best;
  }

  // a random place it can get to, preferably a good walk away
  randomSpot() {
    const L = this.nav.reachList, here = this.chain ? this.chain.hd : this.pos2();
    if (!L || !L.length) return here.clone();
    let c = null;
    for (let i = 0; i < 20; i++) {
      c = this.nav.centre(L[Math.floor(Math.random() * L.length)]);
      if (c.distanceTo(here) > 6) break;
    }
    return c;
  }

  // Smash leaves the staff lying where it fell; the crawl loops are in place, so it's copied out
  // of the skinned mesh as a static prop (posed vertices baked once) and the skinned one hidden
  dropStaff() {
    const staff = this.root.getObjectByName('Grimble_Staff');
    if (!staff || this.staffProp) return;
    const meshes = [];
    staff.traverse((o) => { if (o.isMesh) meshes.push(o); });
    this.root.updateMatrixWorld(true);
    for (const m of meshes) {
      const src = m.geometry, pos = src.attributes.position, out = new Float32Array(pos.count * 3), v = new THREE.Vector3();
      for (let i = 0; i < pos.count; i++) {
        v.fromBufferAttribute(pos, i);
        if (m.isSkinnedMesh) m.applyBoneTransform(i, v);
        v.applyMatrix4(m.matrixWorld);
        out.set([v.x, v.y, v.z], i * 3);
      }
      const geo = new THREE.BufferGeometry();
      for (const k of Object.keys(src.attributes)) if (!['position', 'skinIndex', 'skinWeight', 'normal', 'tangent'].includes(k)) geo.setAttribute(k, src.attributes[k]);
      geo.setAttribute('position', new THREE.BufferAttribute(out, 3));
      if (src.index) geo.setIndex(src.index);
      geo.computeVertexNormals();
      const prop = new THREE.Mesh(geo, m.material);
      prop.name = 'Grimble_Staff_Dropped';
      this.scene.add(prop);
      this.staffProp = prop;
      m.visible = false;
    }
  }

  // the smashed bays become passable; from then on it plans only where it can get to from here
  openGap() {
    const b = this.breakable;
    if (b) this.nav.clear(Math.min(b.min[0], b.max[0]) - 1.5, Math.min(b.min[2], b.max[2]), Math.max(b.min[0], b.max[0]) + 1.5, Math.max(b.min[2], b.max[2]));
    this.nav.flood(this.root.position.x, this.root.position.z);
    this.nav.clearance();
  }
}

// Shatter a breakable pane (level.breakables: its meshes are named after it): hide the glass
// and the mullions in it and throw a burst of shards that fall and settle on the floor.
export function shatter(scene, breakable) {
  const meshes = [];
  scene.traverse((o) => { if (o.isMesh && o.name.startsWith(breakable.name)) meshes.push(o); });
  for (const m of meshes) m.visible = false;
  const lo = new THREE.Vector3(...breakable.min), hi = new THREE.Vector3(...breakable.max);
  const n = 160;
  const geo = new THREE.BufferGeometry();
  const tri = [];
  for (let i = 0; i < n; i++) {
    const s = 0.08 + Math.random() * 0.25;
    tri.push(0, 0, 0, s, 0, s * 0.3, s * 0.2, 0, s);
  }
  geo.setAttribute('position', new THREE.Float32BufferAttribute(tri, 3));
  geo.computeVertexNormals();
  const mat = new THREE.MeshStandardMaterial({ color: 0x9fb5b5, roughness: 0.05, metalness: 0.1, transparent: true, opacity: 0.55, side: THREE.DoubleSide });
  const shards = [];
  const group = new THREE.Group();
  for (let i = 0; i < n; i++) {
    const g2 = new THREE.BufferGeometry();
    g2.setAttribute('position', new THREE.Float32BufferAttribute(tri.slice(i * 9, i * 9 + 9), 3));
    g2.computeVertexNormals();
    const m = new THREE.Mesh(g2, mat);
    m.position.set(THREE.MathUtils.lerp(lo.x, hi.x, Math.random()), lo.y + Math.random() * (hi.y - lo.y) * 0.6,
      THREE.MathUtils.lerp(lo.z, hi.z, Math.random()));
    shards.push({ m, v: new THREE.Vector3(2 + Math.random() * 4, Math.random() * 2, (Math.random() - 0.5) * 3), spin: new THREE.Vector3().random().multiplyScalar(8) });
    group.add(m);
  }
  scene.add(group);
  let t = 0;
  return (dt) => {          // call every frame until it returns false
    t += dt;
    for (const s of shards) {
      if (s.m.position.y <= 0.01) continue;
      s.v.y -= 9.8 * dt;
      s.m.position.addScaledVector(s.v, dt);
      s.m.rotation.x += s.spin.x * dt; s.m.rotation.y += s.spin.y * dt;
      if (s.m.position.y <= 0.01) { s.m.position.y = 0.01; s.m.rotation.set(-Math.PI / 2, 0, Math.random() * 6); }
    }
    return t < 4;
  };
}
