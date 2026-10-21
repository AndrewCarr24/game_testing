import * as THREE from 'three';
import { NavGrid, MAIN_SPACES, DOUBLE_HEIGHT } from './grimble_nav.js';

// The Grimble inside: after a few rounds of knocking it smashes the great room's west glass and
// crawls through the main spaces hunting the player. It can't fit through the side rooms'
// doors (the nav grid simply has no way in), so they're safe; from the double-height rooms it
// can rear up and swipe at the upper gallery over the balustrades. A swipe knocks the player
// down; they get up again. A player out on the grounds is hunted there too (before the break-in
// it drops to all fours and comes after them; back inside, it breaks in after them).
//
// What it knows comes only from its senses (never the player's true position):
// - sight: a ray from its head to the player's eye, stopped by the house's walls, shut doors,
//   closed blinds and (for a crouched player) furniture they duck behind, or tall furniture;
//   glass and balustrades don't stop it. It looks ahead (a cone of 2 x `fov`) and senses
//   anyone within `closeSense` m all round. Seeing isn't instant: a notice meter (`aware`) fills
//   faster the closer, brighter (lights, the flashlight) and faster-moving the player is, slower
//   when they're crouched, still or in the dark; it falls again out of sight. A hidden player
//   (`player.hidden`, a hiding spot) can't be seen, but it goes and sniffs where it saw them go.
// - hearing: window.__noise events (thrown things, running footsteps), muffled by each wall
//   between; each is a lead {pos, time, loudness} that expires after `noiseLife` s; a newer or
//   louder one replaces the current lead. Loud or close ones it rushes to.
//
// States: smash -> chase (sees you, or runs to where it last saw you, then on along the way you
// were heading for `pushOn` s) -> search (2-4 places near the loss it couldn't see from there:
// round corners, doorways; it waits at a side room's door it saw you near) -> prowl (rooms
// weighted by how long since it was there, side-room doors, and the last loss, which it keeps
// coming back to for a while) | investigate (a noise) | wait (out of reach: at a side room's
// door facing in, below the balustrade, at the stair's foot) | swipe | reachUp.
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
// Its own body blocks its plans (it can't crawl back over itself); when that forces a long
// detour it turns round on the spot where there's room, or goes on to the nearest place there
// is, turns there and comes back.

const DEFAULTS = {
  loopsBeforeSmash: 2,     // knock-wave-stare rounds at the glass before it breaks in
  crawlStride: 3.0, crawlCycle: 1.6,      // m / s per Crawl cycle (asset userData overrides)
  fastStride: 4.4, fastCycle: 1.2,        // CrawlFast
  smashHit: 1.2,           // s into Smash when the glass breaks
  swipeHit: 0.7, swipeReach: 2.8, swipeLen: 1.6,
  reachHit: 1.6, reachLen: 3.0, reachUp: 2.2,   // horizontal reach of ReachUp (m)
  sight: 40, hearing: 36,  // m (hearing: for a loudness-1 noise, along the way it could walk or muffled through walls)
  fov: 1.45,               // rad: half its forward cone of sight (~165 degrees in all)
  closeSense: 3.5,         // m all round within which it senses you (nothing solid between)
  noticeAt10: 0.9,         // s to notice a lit, still-ish, standing player 10 m ahead (~ distance)
  forget: 0.3,             // /s the notice meter falls while it can't see you
  turnRate: 2.4,           // rad/s the head end turns
  pushOn: 2.0,             // s on along your last heading after reaching where it lost you
  pursueMax: 15,           // s at most getting to where it lost you
  noiseLife: 20,           // s a heard noise stays a lead
  muffle: 0.6,             // loudness kept through each wall between a noise and it
  rushLoud: 0.55,          // a lead this loud (after muffling), or within rushNear m: full speed
  rushNear: 12,
  waitDoor: [15, 30],      // s at a side room's door it saw you go into / near
  waitBelow: [20, 40],     // s below the balustrade after you've stepped back from it
  waitStair: [10, 18],     // s at the stair's foot after that
  searchPoints: [2, 4],    // places it checks after losing you
  searchRate: 2.4,         // Crawl playback rate while searching (prowling: prowlRate)
  prowlRate: [1.6, 2.6],
  lossBias: 60,            // s over which a loss's pull on its prowling widens out
  lossKeep: 240,           // s a loss keeps pulling it back
  cooldown: 3.5,           // s after a hit before it can hit again
  getaway: 3.5,            // ... and s after the player is back on their feet (2 s felt relentless:
                           //   standing still, the player was knocked down every ~5 s)
  crawlRate: 2.0,          // playback rate of Crawl / CrawlFast (speed scales with it, so no sliding):
  fastRate: 2.6,           //   ~1.2 m/s prowling, ~4.7 m/s chasing (the player walks 3.4, runs 6.8)
  upperY: 3.5,             // player feet above this = on the upper floor
  strikeRange: 1.6,        // m beyond its head within which it swipes
  lookAhead: 2.0,          // m along the path it steers at
  maxBend: 1.1,            // rad between the chest and the hindquarters
  maxSwing: 3.0,           // rad/s the hindquarters may swing round (no snapping round at doorways)
  navMargin: 0.12,         // the route keeps (half width - this) off walls; the circles do the rest
  outdoor: true,           // hunt the grounds too (level.grimble.outdoor rects, or the lawn inside the hedge)
};

// the lawn inside the perimeter hedge (plan.GROUNDS: hedge x +-70, z +-62, 1.4 m thick), round
// the house (x +-26, z +-20): where it may go outdoors when the level doesn't say
const HEDGE = [-68.5, -60.5, 68.5, 60.5], HOUSE = [-26, -20, 26, 20];
const TERRACES = [[-31, 20, 31, 25], [-31, -25, 31, -20], [-31, -20, -26, 20], [26, -20, 31, 20]];
const LAWN_Y = -0.08;
const rand = (a, b) => a + Math.random() * (b - a);
const inRect = (r, x, z, m = 0) => x >= r[0] - m && x <= r[2] + m && z >= r[1] - m && z <= r[3] + m;
const LOCO = ['Crawl', 'CrawlFast', 'CrawlIdle'];

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
  // interact: viewer/interactables.js (its doors' leaves block sight and swipes while shut)
  constructor(grimble, { level, colliders, scene, interact = null, sightBlockers = () => [], opts = {} }) {
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
    this.interact = interact;
    this.sightBlockers = sightBlockers;
    this.measureBody();
    // the shell's colliders: walls for its body and its swipes; for its sight, not the glass
    // (house.py tags glazing `glass`; older levels: the 0.12 m thick window boxes) nor the
    // balustrades' invisible anti-vault boxes (tagged seeThrough, or thin 2.2 m tall boxes)
    const rail = (c) => c.seeThrough || (Math.abs(c.max[1] - c.min[1] - 2.2) < 0.05 &&
      Math.min(c.max[0] - c.min[0], c.max[2] - c.min[2]) <= 0.12);
    const glass = (c) => c.glass || (Math.abs(Math.min(c.max[0] - c.min[0], c.max[2] - c.min[2]) - 0.12) < 0.006 && c.max[1] - c.min[1] > 1);
    const box = (c) => Object.assign(new THREE.Box3(new THREE.Vector3(...c.min), new THREE.Vector3(...c.max)), { glass: glass(c) });
    this.walls = level.colliders.filter((c) => !rail(c)).map(box);
    this.sightWalls = this.walls.filter((w) => !w.glass);
    // the grounds (level.grounds, with their colliders in `colliders`, tagged `kind`): heights,
    // where outdoors is, the zones it prowls outside
    const G = level.grounds;
    this.grounds = {
      lawn: G?.lawn ?? LAWN_Y, terrace: G?.terrace ?? 0, house: G?.house ?? HOUSE, bounds: G?.bounds ?? HEDGE,
      terraces: G?.terraces ?? TERRACES,
      zones: Object.entries(G?.zones ?? Object.fromEntries(Object.entries(level.zones ?? {}).map(([k, z]) => [k, z.rect]))).filter(([k]) => k !== 'planting'),
    };
    // furniture (props, the grounds' furniture and hedges): what a crouched player can duck
    // behind; tall pieces hide anyone. Not what a sight line passes (seeThrough: the boundary,
    // water) nor the ground itself, nor moving parts (doors are handled as doors)
    const own = new Set([...(interact?.items ?? []).map((i) => i.collider), ...(interact?.reactors ?? []).map((r) => r.collider)].filter(Boolean));
    const cover = colliders.slice(level.colliders.length).filter((c) => !own.has(c) && !c.isEmpty() && !c.seeThrough && c.kind !== 'ground' && c.max.y > 0.5);
    this.coverTall = cover.filter((c) => c.max.y > 1.9);
    this.coverLow = cover.filter((c) => c.max.y <= 1.9);
    // outdoors its body is kept out of the hedges, walls and furniture of the grounds too
    this.groundSolid = colliders.filter((c) => c.kind && c.kind !== 'ground' && c.max.y > 1.3 && c.min.y < 2.8);
    this.allRooms = Object.entries(level.rooms).map(([name, r]) => ({ name, rect: r.rect, floor: r.floor ?? 0, height: r.height ?? 4.2, sun: r.sun }));
    this.rooms = MAIN_SPACES.filter((r) => level.rooms[r]).map((r) => level.rooms[r].rect);
    const areas = this.rooms.slice();
    this.breakable = (level.breakables || [])[0];
    if (this.breakable) {           // the lawn in front of the glass it breaks, so it can come through
      const b = this.breakable, z0 = Math.min(b.min[2], b.max[2]), z1 = Math.max(b.min[2], b.max[2]);
      areas.push([Math.min(b.min[0], b.max[0]) - 6, z0 - 1, Math.max(b.min[0], b.max[0]) + 0.5, z1 + 1]);
    }
    // outdoors: the level's walkable rects for it (level.grimble.outdoor), else the grounds inside
    // the hedge round the house (level.grounds.bounds / house); the grounds' colliders in
    // `colliders` (hedges, walls, furniture, water) keep it out of what it can't cross
    const B = this.grounds.bounds, H = this.grounds.house;
    this.outdoorAreas = !this.o.outdoor ? [] : level.grimble?.outdoor ?? [
      [B[0], B[1], H[0], B[3]], [H[2], B[1], B[2], B[3]], [H[0], B[1], H[2], H[1]], [H[0], H[3], H[2], B[3]]];
    areas.push(...this.outdoorAreas);
    this.nav = new NavGrid(colliders, areas, { cell: 0.2, radius: this.body.w - this.o.navMargin });
    // what its body is kept out of: the shell's walls (not the glass it breaks through)
    const b = this.breakable;
    this.gapBox = b && new THREE.Box3(new THREE.Vector3(Math.min(b.min[0], b.max[0]) - 0.3, 0, Math.min(b.min[2], b.max[2])),
      new THREE.Vector3(Math.max(b.min[0], b.max[0]) + 0.3, 9, Math.max(b.min[2], b.max[2])));
    // (as for its routes: it climbs over what is lower than 1.3 m, e.g. the stair's bottom treads)
    this.solid = this.walls.filter((c) => c.max.y > 1.3 && c.min.y < 2.8 && !(this.gapBox && this.gapBox.intersectsBox(c) && c.max.x - c.min.x < 0.5))
      .concat(this.groundSolid);
    this.double = DOUBLE_HEIGHT.filter((r) => level.rooms[r]).map((r) => level.rooms[r].rect);
    this.doorways = this.findDoorways(level);
    // the stair's foot (its ramp's low end), where it waits for someone who went upstairs
    const ramp = (level.ramps || [])[0];
    if (ramp) {
      const lowX = ramp.y[0] < ramp.y[1] ? ramp.x[0] : ramp.x[1], dir = Math.sign(ramp.x[1] - ramp.x[0]) * (ramp.y[0] < ramp.y[1] ? 1 : -1);
      this.stairFoot = new THREE.Vector2(lowX - dir * 1.2, (ramp.z[0] + ramp.z[1]) / 2);
      this.stairUp = new THREE.Vector2(dir, 0);
    }
    this.state = null;
    this.t = 0;
    this.time = 0;
    this.hitAt = -1e9;
    this.chain = null;
    this.bodyYaw = null;
    this.pathAt = -1e9;
    this.stats = { unsticks: 0, replans: 0, fails: 0, heard: 0, sightings: 0 };
    this.reset();
    // the player can't walk into it: three boxes round the chain's points, added to the shared
    // colliders (so thrown things bounce off it too); parked under the ground until it's inside
    // (a fourth round its face: the head reaches past the front box, and a player pressed up to it
    // ended up with the camera inside its head)
    this.blockers = [0, 1, 2, 3].map(() => new THREE.Box3(new THREE.Vector3(0, -101, 0), new THREE.Vector3(0, -100, 0)));
    colliders.push(...this.blockers);
    window.__noise?.on?.((n) => this.hear(n));
    this._ray = new THREE.Ray();
    window.__hunt = this;
  }

  // forget everything it knows (tests teleport it)
  reset() {
    this.path = null; this.goal = null; this.goalK = -1; this.goalOff = 0; this.arrived = false;
    this.lastSeen = null; this.lastSeenY = 0; this.seenAt = -1e9; this.seenNow = false; this.aware = 0;
    this.trackV = new THREE.Vector2(); this._prevSight = null;
    this.heard = []; this.lead = null; this.leadNew = false; this.noise = null;
    this.pursuit = null; this.search = null; this.waiting = null; this.inv = null; this.prowlGoal = null; this.pause = null;
    this.hideSpot = null; this.glimpse = null; this.lossPos = null; this.lossAt = -1e9; this.lastReturn = -1e9;
    this.turnAt = null; this.stage = null; this.cantTurn = false; this._turnTry = 0; this._jam = null;
    this.unstickUntil = 0; this.planFails = 0; this.watchFrom = null; this.breakIn = null;
    for (const j of this.jams ?? []) this.nav.markCost(j.x, j.z, 1.6, 0);
    this.jams = [];
    this.upperWait = null;
    this.rate = this.o.crawlRate;
  }

  // the side rooms' doors (door props on a main space's edge with a side room behind them):
  // {pos (the door), into (unit vector into the side room), room (side room), main (main room)}
  findDoorways(level) {
    const out = [];
    const roomAt = (x, z) => this.allRooms.find((r) => r.floor < 1 && inRect(r.rect, x, z));
    for (const p of level.props || []) {
      if (!/(^|_)door/.test(p.asset) || p.position[1] > 1 || p.attach) continue;
      const [x, , z] = p.position;
      for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const a = roomAt(x - dx * 0.7, z - dz * 0.7), s = roomAt(x + dx * 0.7, z + dz * 0.7);
        if (a && s && MAIN_SPACES.includes(a.name) && !MAIN_SPACES.includes(s.name)) {
          out.push({ pos: new THREE.Vector2(x, z), into: new THREE.Vector2(dx, dz), room: s.name, main: a.name });
          break;
        }
      }
    }
    return out;
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


  start() { this.set('smash'); this.g.play('Smash'); }

  // before the break-in: it saw the player out on the grounds. It drops to all fours (Smash,
  // turned toward them, no glass) and hunts them outside; the house stays shut to it until
  // it breaks in after them.
  startOutside(eye) {
    this.outsideStart = true;
    this.lastSeen = new THREE.Vector2(eye.x, eye.z); this.seenAt = this.time; this.lastSeenY = 0; this.aware = 1;
    this.start();
  }

  set(state) {
    if (state !== this.state) {
      this.t = 0;
      this.pause = null;
      this.goalFailed = false;
      if (state !== 'chase') { this.pursuit = null; this.turnAt = null; }
      if (state !== 'wait') this.waiting = null;
      if (state !== 'search') this.search = null;
      if (state !== 'investigate') this.inv = null;
      if (state !== 'prowl') this.prowlGoal = null;
    }
    this.state = state;
  }

  // a test or a scripted moment: it has just seen the player there
  sawPlayer(p, y = 0) {
    this.lastSeen = p.clone(); this.lastSeenY = y; this.seenAt = this.time; this.aware = 1;
    this.set('chase');
  }
  // stand still for s seconds (still looking and listening)
  hold(s) { this.set('wait'); this.waiting = { kind: 'hold', until: this.time + s, at: null }; this.startScan(); }

  // ---------------------------------------------------------------- perception
  headPos() {
    if (!this.chain) return this.root.position.clone().add(new THREE.Vector3(0, 5.5, 0));
    return new THREE.Vector3(this.chain.hd.x, this.state === 'reachUp' ? 5.5 : 2.2, this.chain.hd.y);
  }

  // shut doors: their leaves' colliders while settled (a swinging leaf has none)
  doorBoxes() {
    const out = [];
    for (const it of this.interact?.items ?? []) if (it.collider && it.def.type === 'rotate' && !it.collider.isEmpty()) out.push(it.collider);
    return out;
  }

  // is the segment a -> b blocked by any of these boxes (one containing `a` doesn't count)?
  blocked(a, b, boxes, margin = 0.3) {
    const to = b.clone().sub(a), d = to.length();
    if (d < 1e-6) return false;
    this._ray.set(a, to.divideScalar(d));
    const lo = new THREE.Vector3().copy(a).min(b), hi = new THREE.Vector3().copy(a).max(b), hit = new THREE.Vector3();
    for (const w of boxes) {
      if (w.max.x < lo.x || w.min.x > hi.x || w.max.y < lo.y || w.min.y > hi.y || w.max.z < lo.z || w.min.z > hi.z) continue;
      if (w.containsPoint(a)) continue;
      if (this._ray.intersectBox(w, hit) && hit.distanceTo(a) < d - margin) return true;
    }
    return false;
  }

  // can a sight line pass from a to b? (walls, shut doors, closed blinds; not glass or rails;
  // `crouch`: furniture the eye at b is ducked behind; tall furniture always)
  sightClear(a, b, crouch = false) {
    if (this.blocked(a, b, this.sightWalls) || this.blocked(a, b, this.doorBoxes(), 0.1) || this.blocked(a, b, this.sightBlockers(), 0.1)) return false;
    if (this.blocked(a, b, this.coverTall, 0.05)) return false;
    if (!crouch) return true;
    // cover: a piece close in front of a crouched eye whose top is near it hides it (they duck
    // right down behind it: as if it were half a metre taller)
    const near = [];
    for (const c of this.coverLow) {
      if (c.max.y >= b.y - 0.35 && c.min.y < b.y && c.distanceToPoint(b) < 1.5) {
        near.push(new THREE.Box3(c.min, new THREE.Vector3(c.max.x, Math.max(c.max.y, b.y + 0.5), c.max.z)));
      }
    }
    return !this.blocked(a, b, near, 0.05);
  }
  // (the old name, for tests: the geometric line of sight from its head to an eye)
  sees(eye) { return eye.distanceTo(this.headPos()) <= this.o.sight && this.sightClear(this.headPos(), eye, !!this._crouch); }

  // how lit the player is: the flashlight, daylight in a room with sun, or the room's lights
  // (lights_<room> signal) and power; dark ~0.35
  // (with the house / lighting systems: window.__house.lightAt(pos) 0..1, else
  // window.__lighting.isDark(room))
  lit(feet) {
    if (window.__flashlight?.on) return 1.6;
    const v = window.__house?.lightAt?.(new THREE.Vector3(feet.x, feet.y + 1.2, feet.z));
    if (typeof v === 'number' && isFinite(v)) return 0.35 + 0.65 * Math.min(1, Math.max(0, v));
    const r = this.roomAt(feet.x, feet.z, feet.y);
    if (r && window.__lighting?.isDark) return window.__lighting.isDark(r.name) ? 0.35 : 1;
    if (!r || r.sun !== false) return 1;
    const sig = window.__signals;
    if (sig?.get?.('power') === false) return 0.35;
    const k = `lights_${r.name}`;
    return sig?.has?.(k) && !sig.get(k) ? 0.35 : 1;
  }

  roomAt(x, z, y = 0) { return this.allRooms.find((r) => y >= r.floor - 0.5 && y < r.floor + r.height && inRect(r.rect, x, z)); }
  inHouse(x, z) { return inRect(this.grounds.house, x, z, 0.1); }
  groundY(x, z) { const g = this.grounds; return this.inHouse(x, z) ? 0 : g.terraces.some((t) => inRect(t, x, z)) ? g.terrace : g.lawn; }
  // somewhere on its grid (the walk-in starts beyond the hedge, off it)
  onGrid() { return this.nav.nearest(this.root.position.x, this.root.position.z, 3) >= 0; }

  // every frame: what it sees of the player (the notice meter), what it remembers of them
  perceive(dt, eye, player) {
    const o = this.o, feet = player?.pos ?? new THREE.Vector3(eye.x, eye.y - 1.65, eye.z);
    const head = this.headPos(), d = head.distanceTo(eye);
    const hidden = !!player?.hidden, crouch = !!player?.crouching;
    this._crouch = crouch;
    let vis = false, T = Infinity;
    if (!hidden && d <= o.sight && this.state !== 'smash') {
      const c = this.chain, fy = this.frontYaw();
      const off = Math.abs(wrap(Math.atan2(eye.x - c.hd.x, eye.z - c.hd.y) - fy));
      const flat = Math.hypot(eye.x - c.hd.x, eye.z - c.hd.y);
      const close = flat <= o.closeSense;
      if ((off <= o.fov || close || this.state === 'reachUp') && this.sightClear(head, eye, crouch)) {
        vis = true;
        // seconds to notice: ~ distance, x posture / movement / light, much less once it's after you
        const v = player?.vel ? Math.hypot(player.vel.x, player.vel.z) : 1.5;
        T = o.noticeAt10 * Math.max(0.12, flat / 10);
        T *= crouch ? 1.8 : 1;
        T *= v < 0.3 ? 1.4 : v > 5 ? 0.6 : 1;
        T /= this.lit(feet);
        if (off > o.fov) T = Math.max(T, 0.5);                    // sensed, not looked at
        if (close) T = Math.min(T, 0.35);
        const alert = this.time - this.seenAt < 10 || ['chase', 'search', 'investigate'].includes(this.state);
        if (alert) T *= 0.4;
      }
    }
    if (vis) this.aware = Math.min(1, this.aware + dt / T);
    else this.aware = Math.max(0, this.aware - o.forget * dt);
    // once it has you it keeps you through a flicker of the sight line (a balustrade post, its
    // own head bobbing): 0.25 s
    if (vis && this.aware >= 1) this._visAt = this.time;
    const seen = !hidden && this.aware > 0.9 && this.time - (this._visAt ?? -1e9) < 0.25;
    this.seenNow = seen;
    if (seen) {
      const p = new THREE.Vector2(feet.x, feet.z);
      // how they're moving (from what it sees): the heading it follows when it loses them
      if (this._prevSight && this.time - this._prevSight.t < 0.3 && this.time > this._prevSight.t) {
        const v = p.clone().sub(this._prevSight.p).divideScalar(this.time - this._prevSight.t);
        this.trackV.lerp(v, 0.25);
      } else if (!this._prevSight || this.time - this._prevSight.t > 1) this.trackV.set(0, 0);
      this._prevSight = { p, t: this.time };
      if (this.time - this.seenAt > 1) this.stats.sightings++;
      this.lastSeen = p; this.lastSeenY = feet.y; this.seenAt = this.time;
      this.glimpse = null; this.hideSpot = null; this.leadNew = false;   // (what it sees beats what it heard)
    } else if (vis && this.aware > 0.3) {
      this.glimpse = { p: new THREE.Vector2(eye.x, eye.z), y: eye.y, t: this.time };   // something there...
    }
    // it saw them go into a hiding spot: it knows where (and goes to sniff at it)
    if (hidden && !this._wasHidden && this.time - this.seenAt < 1.5) {
      this.hideSpot = { p: new THREE.Vector2(feet.x, feet.z), t: this.time };
      this.lastSeen = this.hideSpot.p.clone(); this.lastSeenY = feet.y;
    }
    this._wasHidden = hidden;
    // leads expire
    if (this.lead && this.time - this.lead.time > o.noiseLife) { this.lead = null; this.leadNew = false; }
    this.heard = this.heard.filter((n) => this.time - n.time < o.noiseLife);
    this.noise = this.lead?.pos ?? null;
  }

  // walls between two points (each muffles a sound)
  wallsBetween(a, b) {
    const to = b.clone().sub(a), d = to.length();
    if (d < 1e-6) return 0;
    const ray = new THREE.Ray(a, to.divideScalar(d)), hit = new THREE.Vector3(), hits = [];
    // (each room has its own lining, so a wall is two boxes back to back: hits within 0.5 m are one wall)
    for (const w of this.walls) if (!w.containsPoint(a) && !w.containsPoint(b) && ray.intersectBox(w, hit) && hit.distanceTo(a) < d) hits.push([hit.distanceTo(a), w.glass ? 0.5 : 1]);
    for (const w of this.doorBoxes()) if (ray.intersectBox(w, hit) && hit.distanceTo(a) < d) hits.push([hit.distanceTo(a), 0.7]);
    hits.sort((p, q) => p[0] - q[0]);
    let n = 0, last = -1e9, lastW = 0;
    for (const [t, w] of hits) {
      if (t - last < 0.5) { if (w > lastW) { n += w - lastW; lastW = w; } continue; }
      n += w; last = t; lastW = w;
    }
    return n;
  }

  hear(n) {
    if (!this.chain || this.state === 'smash') return;
    const p = n.position, head = this.headPos();
    const at = new THREE.Vector3(p.x, Math.max(p.y ?? 0.5, 0.3), p.z);
    const d = Math.hypot(p.x - head.x, p.z - head.z), L0 = n.loudness ?? 1, range = this.o.hearing * L0;
    if (d > range) return;
    // how far the sound has to go: straight through the walls between (each muffles it), or
    // round through the open ways it could walk, then through whatever is left (a side room's door)
    const m = this.o.muffle;
    let eff = d / Math.pow(m, Math.min(4, this.wallsBetween(new THREE.Vector3(head.x, 1.6, head.z), at)));
    if (eff > range && this.chain) {
      const to = new THREE.Vector2(p.x, p.z), gk = this.goalCell(to, p.y > 3.5 ? 0 : p.y);
      const P = gk >= 0 ? this.nav.path(this.chain.hd, to, null, gk) : null;
      if (P) {
        const end = this.nav.centre(gk), tail = this.wallsBetween(new THREE.Vector3(end.x, 1.6, end.y), at);
        eff = Math.min(eff, (this.nav.lastLen + end.distanceTo(to)) / Math.pow(m, Math.min(4, tail)));
      }
    }
    if (eff > range) return;
    const loud = L0 * Math.min(1, d / Math.max(eff, 1e-3));
    const rec = { pos: new THREE.Vector2(p.x, p.z), y: p.y ?? 0, time: this.time, loud, d: eff, source: n.source };
    this.heard.push(rec);
    this.stats.heard++;
    // a newer lead takes over unless the current one is much more compelling (louder, nearer, fresh)
    const pri = (r) => r.loud / (1 + r.d / 15) * (1 - (this.time - r.time) / this.o.noiseLife);
    if (!this.lead || pri(rec) >= 0.5 * pri(this.lead)) { this.lead = rec; this.leadNew = true; this.noise = rec.pos; }
  }

  // where its eyes go (viewer/grimble.js): the player while it sees them, else what it's after
  get lookTarget() {
    if (this.seenNow && this._eye) return this._eye;
    const P = (p, y = 1.5) => new THREE.Vector3(p.x, y, p.y);
    if (this.glimpse && this.time - this.glimpse.t < 1.5) return new THREE.Vector3(this.glimpse.p.x, this.glimpse.y, this.glimpse.p.y);
    if (this.state === 'chase' && this.lastSeen) return P(this.lastSeen, this.lastSeenY + 1.5);
    if (this.state === 'investigate' && this.lead) return P(this.lead.pos, 1.0);
    if (this.state === 'wait' && this.waiting?.at) return P(this.waiting.at, this.waiting.y ?? 1.5);
    return null;
  }

  // before the break-in, at the glass or walking in: can it see the player (standing, its head
  // up high)? (grimble.js: its eyes follow them only then; a player outside starts the hunt)
  seesFromOutside(eye) {
    const head = this.root.position.clone(); head.y = 5.6;
    if (head.distanceTo(eye) > this.o.sight) return false;
    return this.sightClear(head, eye, !!this._crouch) && !this.blocked(head, eye, this.doorBoxes(), 0.1);
  }
  playerOutside(feet) { return !this.inHouse(feet.x, feet.z) && inRect(this.grounds.bounds, feet.x, feet.z) && feet.y < 2; }

  // nothing solid between its head end and the player (it can't swipe through a wall, a shut door or glass)
  clearTo(feet, fromY = 1.2) {
    return this.clearBetween(new THREE.Vector3(this.chain.hd.x, fromY, this.chain.hd.y), new THREE.Vector3(feet.x, feet.y + 1.0, feet.z));
  }

  clearBetween(a, b) {
    return !this.blocked(a, b, this.walls, 0.1) &&!this.blocked(a, b, this.doorBoxes(), 0.05);
  }

  // in a double-height room, at least m inside it (a doorway's cells are on both rooms' edges)
  inDouble(x, z, m = 0.4) { return this.double.some((r) => x >= r[0] + m && x <= r[2] - m && z >= r[1] + m && z <= r[3] - m); }
  roomOf(x, z) { return this.rooms.find((r) => x >= r[0] && x <= r[2] && z >= r[1] && z <= r[3]); }
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
    this.root.position.y = this.groundY(this.root.position.x, this.root.position.z);
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

  // ---------------------------------------------------------------- movement
  // the cell to head for when going to `t`: t's own cell if it can stand there, else one in the
  // same room that can see t (not the nearest one across a wall), else a side room's doorway, else
  // whatever is nearest. (cached per spot)
  goalCell(t, y = 0) {
    const n = this.nav, key = `${Math.round(t.x * 4)},${Math.round(t.y * 4)},${Math.round(y)}`;
    if (this._gc?.key === key && this._gc.gen === this._navGen) return this._gc.k;
    let k = n.idx(t.x, t.y);
    if (!n.walkable(k)) {
      const room = this.roomAt(t.x, t.y, y > 3.5 ? 0 : y);
      const from = new THREE.Vector3(t.x, 1.5, t.y);
      const sees = (x, z) => !this.blocked(from, new THREE.Vector3(x, 1.5, z), this.sightWalls, 0.1);
      k = -1;
      if (room && MAIN_SPACES.includes(room.name)) k = n._nearest(t.x, t.y, 8, (x, z) => inRect(room.rect, x, z) && sees(x, z));
      if (k < 0 && room && !MAIN_SPACES.includes(room.name)) {
        // a side room: the doorway into it nearest to t (outside it, facing in)
        const doors = this.doorways.filter((d) => d.room === room.name).sort((a, b) => a.pos.distanceTo(t) - b.pos.distanceTo(t));
        for (const d of doors) {
          const p = d.pos.clone().addScaledVector(d.into, -1.2);
          k = n._nearest(p.x, p.y, 4, (x, z) => !this.roomAt(x, z) || MAIN_SPACES.includes(this.roomAt(x, z).name));
          if (k >= 0) break;
        }
      }
      if (k < 0) k = n._nearest(t.x, t.y, 8, sees);
      if (k < 0) k = n.nearest(t.x, t.y, 40);
    }
    this._gc = { key, k, gen: this._navGen };
    return k;
  }

  // plan a route for the head end to `target` (y: its floor height, for which room it's in)
  goTo(target, y = 0) {
    const c = this.chain, n = this.nav, from = c ? c.hd : this.pos2();
    // start in the room its head is in (the nearest cell may be across a glass wall)
    const room = this.roomOf(from.x, from.y);
    const prefer = room ? (x, z) => x >= room[0] && x <= room[2] && z >= room[1] && z <= room[3] : null;
    const gk = this.goalCell(target, y);
    this.goal = target.clone(); this.goalK = gk; this.goalY = y; this.peek = false;
    this.goalOff = gk >= 0 ? n.centre(gk).distanceTo(target) : Infinity;
    this.pathAt = this.time;
    this.pathI = 0;
    this.arrived = false;
    this.stats.replans++;
    // its own body is in the way; after two failed plans in a row, plan without it
    let P = this.planFails >= 2 ? n.path(from, target, prefer, gk) : this.withOwnBody(() => n.path(from, target, prefer, gk));
    let len = n.lastLen;
    if (!P) {
      this.planFails++; this.stats.fails++;
      this.path = null;
      return false;
    }
    this.planFails = 0;
    this.turning = false;
    let free = false;
    if (c && len > 4) {
      // the body forces a long detour (the way is back over itself): turn round on the spot if
      // there's room here, else on to the nearest place there is, turn there, and come back
      const F = n.path(from, target, prefer, gk), lenF = n.lastLen;
      if (F && len > lenF * 1.4 + 6) {
        if (this.roomHere()) { P = F; len = lenF; this.turnAt = null; free = true; }
        else {
          if (!this.turnAt || this.time - this.turnAtT > 12) { this.turnAt = this.turnSpot(); this.turnAtT = this.time; }
          if (this.turnAt && c.hd.distanceTo(this.turnAt) > 1.0) {
            const T = this.withOwnBody(() => n.path(from, this.turnAt, prefer));
            if (T) { this.path = T; this.pathLen = n.lastLen; this.turning = true; return true; }
          }
        }
      } else this.turnAt = null;
    }
    // the way there is a long way round for somewhere close (round the kitchen island, the
    // courtyard): rather, the nearest place it can get to quickly that sees the spot (it peeks)
    const straight = from.distanceTo(target);
    if (c && straight < 15 && len > 3 * straight + 10) {
      const t3 = new THREE.Vector3(target.x, 1.5, target.y), body = (f) => (free ? f() : this.withOwnBody(f));
      const k = body(() => n.search(from.x, from.y, (kk) => {
        const p = n.centre(kk);
        return p.distanceTo(target) < 4 && !this.blocked(new THREE.Vector3(p.x, 1.5, p.y), t3, this.sightWalls, 0.1);
      }, 8000));
      if (k >= 0) {
        const Q = body(() => n.path(from, n.centre(k), prefer, k));
        if (Q && n.lastLen < len * 0.6) { P = Q; len = n.lastLen; this.goalK = k; this.goalOff = n.centre(k).distanceTo(target); this.peek = true; }
      }
    }
    this.path = P;
    this.pathLen = len;
    return true;
  }

  roomHere() {
    const n = this.nav, c = this.chain, kq = n.idx(c.q.x, c.q.y);
    return n.clear && kq >= 0 && n.clear[kq] >= Math.max(this.body.Lf, this.body.Lb) + this.body.r + 0.15 - n.radius;
  }

  // its own body is in the way (it can't crawl back over itself): the cells under its
  // hindquarters and spine are blocked while `fn` plans (not those right under its head)
  withOwnBody(fn) {
    const c = this.chain, saved = [];
    if (c) {
      const n = this.nav;
      const blockAround = (p, rad) => {
        const R = Math.ceil(rad / n.cell), ci = Math.floor((p.x - n.x0) / n.cell), cj = Math.floor((p.y - n.z0) / n.cell);
        for (let dj = -R; dj <= R; dj++) for (let di = -R; di <= R; di++) {
          const i = ci + di, j = cj + dj;
          if (i < 0 || j < 0 || i >= n.w || j >= n.h || (di * di + dj * dj) * n.cell * n.cell > rad * rad) continue;
          const x = n.x0 + (i + 0.5) * n.cell, z = n.z0 + (j + 0.5) * n.cell;
          if (Math.hypot(x - c.hd.x, z - c.hd.y) < 0.9) continue;
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

  // metres left along the path from the head end
  remaining() {
    const P = this.path, h = this.chain.hd;
    if (!P || !P.length) return 0;
    const i = Math.min(this.pathI + 1, P.length - 1);
    let r = h.distanceTo(P[i]);
    for (let k = i; k < P.length - 1; k++) r += P[k].distanceTo(P[k + 1]);
    return r;
  }

  speed(fast) {
    const o = this.o;
    return fast ? (o.fastStride / o.fastCycle) * o.fastRate : (o.crawlStride / o.crawlCycle) * this.rate;
  }

  // the crawl loops: no flicker between moving and stopping (a switch holds 0.4 s)
  anim(name, force = false) {
    const cur = this.g.current?.getClip().name;
    if (cur === name) return;
    if (!force && LOCO.includes(cur) && LOCO.includes(name) && this.time - (this._animAt ?? -1e9) < 0.4) return;
    this._animAt = this.time;
    if (name === 'Crawl' && this.g.actions.Crawl) this.g.actions.Crawl.timeScale = this.rate;
    this.g.play(name);
  }

  follow(dt, fast) {
    if (!this.path || !this.path.length) return true;
    const o = this.o, c = this.chain;
    const end = this.path[this.path.length - 1];
    if (c.hd.distanceTo(end) < 0.7) { this.path = null; return true; }
    const target = this.carrot(o.lookAhead);
    const off = this.turnHead(target, dt);
    // forward along its facing, slowing in a tight turn; a target behind it: turn on the spot
    const k = off > 1.9 ? 0 : Math.max(0.3, Math.cos(Math.min(off, Math.PI / 2)));
    const step = this.speed(fast) * dt * k;
    c.hd.x += Math.sin(c.hf) * step;
    c.hd.y += Math.cos(c.hf) * step;
    if (!fast && this.g.actions.Crawl) this.g.actions.Crawl.timeScale = this.rate;
    this.anim(fast ? 'CrawlFast' : 'Crawl');
    return false;
  }

  // keep a route to `target` and follow it: 'moving' | 'arrived' | 'nopath'. It replans when the
  // target moves (> `moveTol` m; at most every `every` s), when it has no route, after a jam.
  // Once there it stays put until the target moves (no stop-start flicker).
  travel(dt, target, fast, { y = 0, every = 0.5, moveTol = 0.8 } = {}) {
    const dg = this.goal ? this.goal.distanceTo(target) : Infinity;
    if (this.unstickUntil > this.time) { this.reverse(dt); return 'moving'; }
    if (dg > 3 || (dg > moveTol && this.time - this.pathAt > every) ||(!this.path && !this.arrived && this.time - this.pathAt > 0.4) || this._replan) {
      this._replan = false;
      if (!this.goTo(target, y)) return 'nopath';
    }
    if (this.arrived && !this.path) return 'arrived';
    if (!this.path) return 'nopath';
    if (this.follow(dt, fast)) {
      if (this.turning) { this.turning = false; this.turnAt = null; this._replan = true; return 'moving'; }
      this.arrived = true;
      return 'arrived';
    }
    return 'moving';
  }

  // backing out of a jam: the hindquarters lead for a moment, then it replans
  reverse(dt) {
    const c = this.chain, B = this.body;
    const back = c.b.clone().sub(c.q).normalize();
    c.b.addScaledVector(back, 1.2 * dt);
    const k = c.q.clone().sub(c.b); c.q.copy(c.b).addScaledVector(k, B.Lb / (k.length() || 1));
    const f = c.hd.clone().sub(c.q); c.hd.copy(c.q).addScaledVector(f, B.Lf / (f.length() || 1));
    c.hf = this.frontYaw();
    this.anim('Crawl', true);
  }

  // stopped: face a point (turning the head end), or look round (a slow sweep about `base`)
  face(dt, p, rate = 1.6) {
    if (p && this.chain.hd.distanceTo(p) > 0.3) this.turnHead(p, dt, rate);
    this.anim('CrawlIdle');
  }
  scan(dt, base, amp = 0.9, period = 4.5) {
    const a = base + amp * Math.sin((2 * Math.PI * (this.time - (this._scanT ?? 0))) / period), c = this.chain;
    this.turnHead(new THREE.Vector2(c.hd.x + Math.sin(a) * 3, c.hd.y + Math.cos(a) * 3), dt, 1.1);
    this.anim('CrawlIdle');
  }
  startScan() { this._scanT = this.time; this._scanBase = this.frontYaw(); }

  // ---------------------------------------------------------------- the brain
  update(dt, eye, player) {
    const o = this.o, g = this.g;
    this.time += dt;
    this.t += dt;
    this._eye = eye;
    const feet = player?.pos ?? eye;
    if (this.state === 'smash') {
      // (breaking in) the glass goes at smashHit; (out on the grounds) it drops to all fours, turning toward them
      if (this.outsideStart && this.lastSeen && this.t < o.smashHit) {
        const want = Math.atan2(this.lastSeen.x - this.root.position.x, this.lastSeen.y - this.root.position.z);
        const d = wrap(want - g.heading);
        g.heading += Math.sign(d) * Math.min(Math.abs(d), 2.0 * dt);
      }
      if (this.t >= o.smashHit && !this.broken && !this.outsideStart) { this.broken = true; this.onBreak?.(); this.openGap(); }
      const len = g.actions.Smash?.getClip().duration ?? 2.5;
      if (this.t >= len) {
        const first = !this.chain;
        if (this.outsideStart && first) this.prepareNav();
        this.outsideStart = false;
        this.startChain();
        this.path = null; this.goal = null;
        if (first && !this.lastSeen) this.set('prowl');
        else this.set('chase');
      }
      if (!this.chain) { g.root.rotation.y = g.heading; return; }
      this.placeRoot();
      return;
    }
    this.perceive(dt, eye, player);
    // after a knockdown the player gets `getaway` s on their feet before it can hit them again
    if (player?.knocked) this._wasDown = true;
    else if (this._wasDown) { this._wasDown = false; this.upAt = this.time; }
    this.canHit = this.time - this.hitAt > o.cooldown && this.time - (this.upAt ?? -1e9) > o.getaway && !player?.knocked && !player?.hidden;
    const pp = new THREE.Vector2(feet.x, feet.z);
    const upper = feet.y > o.upperY;
    const tip = this.tip();
    const headDist = tip.distanceTo(pp);
    // which room its head is in: when it was last there (prowling goes where it hasn't been)
    const here = this.prowlRoomAt(this.chain.hd.x, this.chain.hd.y);
    if (here) here.visited = this.time;
    switch (this.state) {
      case 'swipe': case 'reachUp': {
        const hitT = this.state === 'swipe' ? o.swipeHit : o.reachHit;
        const len = this.state === 'swipe' ? o.swipeLen : o.reachLen;
        if (this.seenNow) this.turnHead(pp, dt);
        else if (this.lastSeen) this.turnHead(this.lastSeen, dt);
        if (!this.hitDone && this.t >= hitT) {
          this.hitDone = true;
          const vertOk = this.state === 'swipe' ? !upper : upper;
          // (the reach: claws come over the balustrade from above the upper floor)
          const inReach = this.state === 'swipe' ? headDist <= o.strikeRange + 0.6 && this.clearTo(feet)
            : headDist <= o.reachUp + 0.9 && this.clearTo(feet, feet.y + 1.6);
          if (inReach && vertOk && !player?.hidden && player?.knockDown) {
            const from = new THREE.Vector3(this.chain.hd.x, feet.y, this.chain.hd.y);
            player.knockDown(from);
            this.hitAt = this.time;
          }
        }
        if (this.t >= len) { this.set('chase'); this.pursuit = null; this.path = null; this.goal = null; }
        break;
      }
      default: this.brain(dt, feet, pp, upper, headDist);
    }
    this.solveChain();
    this.limitSwing(dt);
    this.chain.hf = this.frontYaw();      // its facing is its chest's (walls may have stopped a turn)
    this.checkJam();
    this.placeRoot();
    this.updateBlockers(player);
  }

  brain(dt, feet, pp, upper, headDist) {
    const o = this.o, c = this.chain, seen = this.seenNow;
    if (this.unstickUntil > this.time) { this.reverse(dt); return; }
    if (seen && this.canHit) {
      // close enough to strike? (measured from its head; next to any part of it, behind it too: it whips round)
      const nearBody = Math.min(c.hd.distanceTo(pp), c.q.distanceTo(pp), c.b.distanceTo(pp)) <= this.body.r + 1.2;
      const close = !upper && (headDist <= o.strikeRange || nearBody) && this.clearTo(feet);
      // (right behind it in a gallery: it can't turn round there, so it doesn't try on the spot;
      // the chase takes it on to somewhere it can, its own body in the way)
      const behind = Math.abs(wrap(Math.atan2(pp.x - c.q.x, pp.y - c.q.y) - this.frontYaw())) > 1.9;
      if (close && !(behind && this.cantTurn)) {
        const off = this.turnHead(pp, dt, o.turnRate * 2);
        if (off < 0.6) { this.strike('swipe'); return; }
        this._turnTry = (this._turnTry || 0) + dt;
        if (this._turnTry > 0.6) { this.cantTurn = true; this._turnTry = 0; }
        this.anim('CrawlIdle');
        return;
      }
      if (!behind) this.cantTurn = false;
      this._turnTry = 0;
      // reach up from where its head is, only with all of it in a double-height room (rearing up
      // anywhere else goes through a ceiling)
      if (upper && headDist <= o.reachUp + 0.5 && this.inDouble(c.q.x, c.q.y) && this.inDouble(c.b.x, c.b.y) &&
        this.clearTo(feet, feet.y + 1.6) && this.turnHead(pp, dt) < 0.5) { this.strike('reachUp'); return; }
    }
    // out on the grounds with the house still shut to it, and they're inside: break in
    if (!this.broken && this.breakable && this.lastSeen && this.inHouse(this.lastSeen.x, this.lastSeen.y) && this.time - this.seenAt < 60) {
      this.breakInStep(dt); return;
    }
    if (seen) { this.chaseSeen(dt, pp, feet.y); return; }
    // a fresh noise: a lead to follow (while it's after you, it's where you are now)
    if (this.leadNew) {
      this.leadNew = false;
      const L = this.lead;
      if (this.state === 'chase' && L.loud >= 0.2 && L.time > this.seenAt) {
        this.lastSeen = L.pos.clone(); this.lastSeenY = L.y > 3.5 ? 4.6 : 0;
        this.pursuit = null; this.trackV.set(0, 0);
      } else if (this.state !== 'chase') { this.set('investigate'); this.inv = { lead: L, t0: this.time, tries: 0 }; }
    }
    switch (this.state) {
      case 'chase': this.pursue(dt); break;
      case 'investigate': this.investigate(dt); break;
      case 'search': this.searchStep(dt); break;
      case 'wait': this.waitStep(dt); break;
      default: this.prowl(dt);
    }
  }

  // it sees them: after them at full speed (or to the nearest place below them, upstairs)
  chaseSeen(dt, pp, y) {
    const c = this.chain;
    if (this.state !== 'chase') { this.set('chase'); this.path = null; this.goal = null; }
    this.pursuit = null;
    let target = pp;
    const spot = y > this.o.upperY ? this.reachSpot(pp, y) : null;
    if (spot) target = this.staged(spot, pp);
    const r = this.travel(dt, target, true, { y: y > this.o.upperY ? 0 : y });
    // the only way there is a long way round (through glass, across the courtyard): it watches a
    // moment before going round
    if (r === 'moving' && this.pathLen > Math.max(3 * c.hd.distanceTo(target), c.hd.distanceTo(target) + 10)) {
      if (!this.watchFrom) this.watchFrom = this.time;
      if (this.time - this.watchFrom < 3) { this.face(dt, pp); return; }
    } else if (r !== 'moving') this.watchFrom = null;
    if (r !== 'moving') this.face(dt, pp, 2.4);
  }

  // come at a reach spot from inside the room: arriving head-first from a doorway leaves the body
  // under a low ceiling, so first go deeper in (away from the player), then turn back
  staged(spot, p) {
    const c = this.chain, inRoom = this.inDouble(c.q.x, c.q.y) && this.inDouble(c.b.x, c.b.y);
    if (!inRoom && !this.stage && c.hd.distanceTo(spot) < 1.2) {
      const u = spot.clone().sub(p).normalize(), L = this.body.Lf + this.body.Lb + 1.6;
      this.stage = this.nav.centre(this.nav.nearest(spot.x + u.x * L, spot.y + u.y * L, 4));
    }
    if (this.stage && c.hd.distanceTo(this.stage) < 1.0) this.stage = null;
    return this.stage ?? spot;
  }

  // lost sight: to where it last saw them (fast), on the way they were heading for a moment,
  // then search. The clock starts when it gets there.
  pursue(dt) {
    const o = this.o, c = this.chain;
    if (!this.lastSeen) { this.set('prowl'); return; }
    const P = this.pursuit ??= { t0: this.time, phase: 'go', target: this.lastSeen.clone(), y: this.lastSeenY, v: this.trackV.clone() };
    if (P.y > o.upperY) { this.pursueUpper(dt, P); return; }
    if (P.phase === 'go') {
      const r = this.travel(dt, P.target, true);
      if ((r === 'nopath' && this.time - P.t0 > 1.5) || this.goalFailed) { this.goalFailed = false; this.startSearch(P.target, null); return; }
      if (r === 'arrived' || this.time - P.t0 > o.pursueMax) {
        // they went somewhere it can't follow (a side room): wait at the door, facing in
        // (or it peeked from the nearest place it could get to quickly: a look, then a search)
        if (this.goalOff > 1.5) {
          const door = !this.peek && this.doorwayNear(P.target);
          if (door) this.startWait('door', door.pos, rand(...o.waitDoor), () => this.startSearch(P.target, null, 2));
          else this.startWait('peek', P.target, rand(3, 5), () => this.startSearch(P.target, null));
          return;
        }
        // it saw them hide here: sniff at it
        if (this.hideSpot) { this.startWait('sniff', this.hideSpot.p, rand(5, 8), () => this.startSearch(P.target, null, 2)); this.hideSpot = null; return; }
        if (P.v.length() > 0.8) {
          P.phase = 'push'; P.t1 = this.time;
          P.push = this.nav.march(c.hd.x, c.hd.y, P.v.x, P.v.y, P.v.length() * o.pushOn + 2);
          return;
        }
        this.startSearch(P.target, null);
      }
      return;
    }
    if (P.phase === 'push') {
      const r = this.travel(dt, P.push, true);
      if (r !== 'moving' || this.time - P.t1 > o.pushOn) this.startSearch(P.target, P.v.clone().normalize());
    }
  }

  // they were upstairs: below the balustrade where it reaches up from, a long wait looking up;
  // then the stair's foot; then a search there
  pursueUpper(dt, P) {
    const o = this.o;
    // (the long wait below is one wait, however often it rears up to probe in between)
    let U = this.upperWait;
    if (!U || U.target.distanceTo(P.target) > 5 || this.time > U.until + 20) U = this.upperWait = { target: P.target.clone(), until: this.time + 1e9 };
    if (P.phase === 'stair' || this.time > U.until) { this.toStair(dt, P); return; }
    // where it reaches up from: below them, or (stepped back from the edge) below the nearest
    // edge of the void to them
    let spot = this.reachSpot(P.target, P.y), aim = P.target;
    if (!spot) {
      const edges = this.double.map((d) => new THREE.Vector2(Math.min(Math.max(P.target.x, d[0] + 0.5), d[2] - 0.5), Math.min(Math.max(P.target.y, d[1] + 0.5), d[3] - 0.5)))
        .sort((a, b) => a.distanceTo(P.target) - b.distanceTo(P.target));
      for (const r of edges) {
        if (r.distanceTo(P.target) > 6) break;
        const a = r.clone().lerp(P.target, Math.min(1, 1.5 / Math.max(0.1, r.distanceTo(P.target))));
        spot = this.reachSpot(a, P.y);
        if (spot) { aim = a; break; }
      }
    }
    if (!spot) { this.toStair(dt, P); return; }
    const r = this.travel(dt, this.staged(spot, aim), true);
    if (r === 'arrived' && !this.stage) {
      if (U.until > 1e8) U.until = this.time + rand(...o.waitBelow);
      this.startWait('below', P.target, Math.max(0.5, U.until - this.time), () => { this.set('chase'); this.pursuit = { t0: this.time, phase: 'stair', target: P.target, y: P.y, v: new THREE.Vector2() }; }, P.y + 1.6);
      this.waiting.aim = aim;
    } else if (r === 'nopath' || this.time - P.t0 > o.pursueMax + 10) this.toStair(dt, P);
  }
  toStair(dt, P) {
    if (!this.stairFoot) { this.startSearch(P.target, null); return; }
    P.phase = 'stair';
    const r = this.travel(dt, this.stairFoot, false);
    if (r === 'arrived' || r === 'nopath') {
      const up = this.stairFoot.clone().addScaledVector(this.stairUp, 6);
      this.startWait('stair', up, rand(...this.o.waitStair), () => this.startSearch(this.stairFoot, null, 2), 3);
    }
  }

  doorwayNear(p, r = 7) {
    let best = null, bd = r;
    for (const d of this.doorways) { const e = d.pos.distanceTo(p); if (e < bd) { bd = e; best = d; } }
    return best;
  }

  startWait(kind, at, secs, then, y = 1.5) {
    this.set('wait');
    this.waiting = { kind, at: at ? at.clone() : null, y, until: this.time + secs, then };
    this.startScan();
    this.path = null; this.goal = null;
  }
  waitStep(dt) {
    const W = this.waiting;
    if (!W) { this.set('prowl'); return; }
    if (this.time >= W.until) { const f = W.then; this.waiting = null; if (f) f(); else this.set('prowl'); return; }
    // below the balustrade: every so often it rears up and swipes over it where it last saw them
    // (rearing up, it sees over the edge)
    if (W.kind === 'below' && this.canHit) {
      W.probe ??= this.time + rand(0.6, 1.5);
      const c = this.chain, aim = W.aim ?? W.at;
      if (this.time > W.probe && this.tip().distanceTo(aim) <= this.o.reachUp + 1.0 && this.inDouble(c.q.x, c.q.y) && this.inDouble(c.b.x, c.b.y)) {
        if (this.turnHead(aim, dt) < 0.5) { W.probe = this.time + rand(6, 10); this.strike('reachUp'); this.stats.probes = (this.stats.probes ?? 0) + 1; return; }
        this.anim('CrawlIdle');
        return;
      }
    }
    // something half-seen: look at it
    if (this.glimpse && this.time - this.glimpse.t < 1) { this.face(dt, this.glimpse.p); return; }
    if (!W.at) { this.scan(dt, this._scanBase, 0.7, 6); return; }
    // face it, peering a little to either side
    const c = this.chain, base = Math.atan2(W.at.x - c.hd.x, W.at.y - c.hd.y);
    this.scan(dt, base, W.kind === 'sniff' ? 0.25 : 0.4, 5);
  }

  // ---- search: the places near the loss it couldn't see, doorways, on along the heading
  startSearch(L, heading, n = null) {
    const o = this.o;
    this.lossPos = L.clone(); this.lossAt = this.time; this.lastReturn = this.time;
    const pts = this.planSearch(L, heading, n ?? Math.round(rand(o.searchPoints[0], o.searchPoints[1] + 0.99) - 0.49));
    this.set('search');
    this.search = { pts, i: 0, phase: 'go', t: this.time };
    this.rate = o.searchRate;
    this.path = null; this.goal = null;
  }
  planSearch(L, H, n) {
    const nav = this.nav, from = new THREE.Vector3(L.x, 2.2, L.y), cands = [];
    const out = !this.inHouse(L.x, L.y), R = 14;
    for (let dz = -R; dz <= R; dz += 1.4) for (let dx = -R; dx <= R; dx += 1.4) {
      const d = Math.hypot(dx, dz);
      if (d > R || d < 2.5) continue;
      const k = nav.idx(L.x + dx, L.y + dz);
      if (!nav.walkable(k) || (!out && !this.inHouse(L.x + dx, L.y + dz))) continue;
      const p = nav.centre(k);
      const to = new THREE.Vector3(p.x, 1.6, p.y);
      const hidden = this.blocked(from, to, this.sightWalls) || this.blocked(from, to, this.doorBoxes(), 0.1);
      let s = (hidden ? 2 : 0.2) - d / R;
      if (H) s += 1.5 * ((p.x - L.x) * H.x + (p.y - L.y) * H.y) / d;
      cands.push({ at: p, s, kind: 'look', dwell: rand(1.5, 3) });
    }
    for (const d of this.doorways) {
      const e = d.pos.distanceTo(L);
      if (e > R) continue;
      const k = this.goalCell(d.pos);
      if (k < 0) continue;
      const near = e < 7;
      cands.push({ at: nav.centre(k), face: d.pos, s: 2.5 + (near ? 2 : 0) - e / R, kind: 'door', dwell: near ? rand(...this.o.waitDoor) * 0.6 : rand(3, 5) });
    }
    cands.sort((a, b) => b.s - a.s);
    const pick = [];
    let tried = 0;
    for (const c of cands) {
      if (pick.length >= n || tried > 14) break;
      if (pick.some((p) => p.at.distanceTo(c.at) < 5)) continue;
      // not somewhere behind it that its own body would make a lap of the house to get to
      tried++;
      const P = this.withOwnBody(() => nav.path(this.chain.hd, c.at));
      if (!P || nav.lastLen > 2.5 * this.chain.hd.distanceTo(c.at) + 8) continue;
      pick.push(c);
    }
    // nearest first, then on from each
    const ordered = [], left = pick.slice();
    let at = this.chain.hd;
    while (left.length) {
      left.sort((a, b) => a.at.distanceTo(at) - b.at.distanceTo(at));
      const p = left.shift(); ordered.push(p); at = p.at;
    }
    return ordered;
  }
  searchStep(dt) {
    const S = this.search;
    if (!S || S.i >= S.pts.length) { this.set('prowl'); return; }
    const pt = S.pts[S.i];
    if (this.glimpse && this.time - this.glimpse.t < 1) { this.face(dt, this.glimpse.p); return; }
    if (S.phase === 'go') {
      const r = this.travel(dt, pt.at, false);
      if (r === 'arrived' || (r === 'nopath' && this.time - S.t > 2) || this.time - S.t > 25 || this.goalFailed) {
        this.goalFailed = false;
        S.phase = 'look'; S.until = this.time + pt.dwell; this.startScan();
      }
      return;
    }
    if (this.time < S.until) {
      if (pt.face) { const c = this.chain; this.scan(dt, Math.atan2(pt.face.x - c.hd.x, pt.face.y - c.hd.y), 0.35, 5); }
      else this.scan(dt, this._scanBase, 1.1, 4);
      return;
    }
    S.i++; S.phase = 'go'; S.t = this.time;
  }

  // ---- a noise: go and see (fast if it was loud or near); a short search round it
  investigate(dt) {
    const I = this.inv, o = this.o;
    if (!I || !I.lead) { this.set('prowl'); return; }
    const L = I.lead, fast = L.loud >= o.rushLoud || L.d < o.rushNear;
    if (!fast) this.rate = 2.4;
    const r = this.travel(dt, L.pos, fast, { y: L.y > 3.5 ? 4.6 : 0 });
    if (r === 'nopath') {
      if (this.time - I.t0 > 1 + I.tries) { I.tries++; this.goal = null; }
      if (I.tries > 3) { this.lead = null; this.set('prowl'); }
      return;
    }
    if (r === 'arrived' || this.time - I.t0 > 40 || this.goalFailed) {
      this.goalFailed = false;
      const heard = L.pos.clone();
      if (this.lead === L) this.lead = null;
      if (this.goalOff > 1.5) {
        const door = this.doorwayNear(heard);
        this.startWait('door', door ? door.pos : heard, L.loud >= o.rushLoud ? rand(10, 16) : rand(6, 10), () => this.startSearch(heard, null, 2));
      } else this.startSearch(heard, null, 2);
    }
  }

  // ---- prowl: room to room, by how long since it was in each, the side rooms' doors, and the
  // last place it lost someone (strongly at first, then widening out; it keeps coming back)
  prowlRoomAt(x, z) { return this.prowlRooms?.find((r) => inRect(r.rect, x, z)); }
  setupRooms() {
    const n = this.nav, R = [];
    for (const name of MAIN_SPACES) {
      const r = this.level.rooms[name];
      if (r) R.push({ name, rect: r.rect, cells: [], visited: -1e9, doors: this.doorways.filter((d) => d.main === name), out: false });
    }
    // outdoors: the grounds' zones and the terraces round the house
    const outRooms = [...this.grounds.zones, ...this.grounds.terraces.map((t, i) => [`terrace_${i}`, t])];
    for (const [name, rect] of outRooms) R.push({ name, rect, cells: [], visited: -1e9, doors: [], out: true });
    for (const k of n.reachList ?? []) {
      const p = n.centre(k), r = R.find((rr) => inRect(rr.rect, p.x, p.y));
      if (r && (!n.clear || n.clear[k] >= 0.25)) r.cells.push(k);
    }
    this.prowlRooms = R.filter((r) => r.cells.length > 20);
  }
  pickProwl() {
    const o = this.o, here = this.prowlRoomAt(this.chain.hd.x, this.chain.hd.y);
    // indoors unless it last had someone outside
    const outside = !!this.lastSeen && !this.inHouse(this.lastSeen.x, this.lastSeen.y) && this.time - this.seenAt < 180;
    const rooms = this.prowlRooms.filter((r) => r.out === outside && r !== here);
    if (!rooms.length) return null;
    const lossOn = this.lossPos && this.time - this.lossAt < o.lossKeep;
    let room = null;
    // every so often, back to where it lost them
    if (lossOn && this.time - this.lastReturn > rand(45, 75)) {
      this.lastReturn = this.time;
      const cd = (r) => Math.hypot(Math.max(r.rect[0] - this.lossPos.x, 0, this.lossPos.x - r.rect[2]), Math.max(r.rect[1] - this.lossPos.y, 0, this.lossPos.y - r.rect[3]));
      room = rooms.slice().sort((a, b) => cd(a) - cd(b))[0] ?? null;   // (the nearest it prowls to where it lost them)
      if (room === here) room = null;
    }
    if (!room) {
      const w = rooms.map((r) => {
        let v = (0.3 + Math.min(1, (this.time - r.visited) / 90)) * (1 + 0.5 * r.doors.length) * Math.sqrt(r.cells.length / 400);
        if (lossOn) {
          const cx = (r.rect[0] + r.rect[2]) / 2, cz = (r.rect[1] + r.rect[3]) / 2, d = Math.hypot(cx - this.lossPos.x, cz - this.lossPos.y);
          const widen = 6 + 30 * Math.min(1, (this.time - this.lossAt) / o.lossBias);
          v *= 1 + 4 * Math.exp(-d / widen);
        }
        return v;
      });
      let s = Math.random() * w.reduce((a, b) => a + b, 0);
      room = rooms[rooms.length - 1];
      for (let i = 0; i < rooms.length; i++) { s -= w[i]; if (s <= 0) { room = rooms[i]; break; } }
    }
    // a side room's door (sniffs there, facing in) or somewhere in the room
    if (room.doors.length && Math.random() < 0.4) {
      const d = room.doors[Math.floor(Math.random() * room.doors.length)], k = this.goalCell(d.pos);
      if (k >= 0) return { at: this.nav.centre(k), face: d.pos, kind: 'door', dwell: rand(3, 6), room };
    }
    const k = room.cells[Math.floor(Math.random() * room.cells.length)];
    return { at: this.nav.centre(k), kind: 'spot', dwell: Math.random() < 0.6 ? rand(1, 4) : 0, room };
  }
  prowl(dt) {
    if (!this.prowlRooms) this.setupRooms();
    if (this.glimpse && this.time - this.glimpse.t < 1) { this.face(dt, this.glimpse.p); return; }
    if (this.pause) {
      if (this.time < this.pause.until) {
        if (this.pause.face) { const c = this.chain; this.scan(dt, Math.atan2(this.pause.face.x - c.hd.x, this.pause.face.y - c.hd.y), 0.3, 5); }
        else if (this.pause.scan) this.scan(dt, this._scanBase, 1.0, 5);
        else this.anim('CrawlIdle');
        return;
      }
      this.pause = null;
    }
    let G = this.prowlGoal;
    if (!G) {
      for (let tries = 0; tries < 4 && !G; tries++) {
        G = this.pickProwl();
        if (!G) break;
        // (not the long way round to somewhere close)
        if (!this.goTo(G.at) || this.pathLen > Math.max(3 * this.chain.hd.distanceTo(G.at), 12)) G = null;
      }
      if (!G) { this.pause = { until: this.time + 1, scan: true }; this.startScan(); return; }
      this.prowlGoal = G;
      this.rate = rand(...this.o.prowlRate);
      G.t0 = this.time;
    }
    const r = this.travel(dt, G.at, false);
    if (r === 'arrived' || r === 'nopath' || this.goalFailed || this.time - G.t0 > 60) {
      this.goalFailed = false;
      this.prowlGoal = null;
      if (r === 'arrived' && (G.dwell || G.face)) { this.pause = { until: this.time + G.dwell, face: G.face, scan: Math.random() < 0.7 }; this.startScan(); }
    }
  }

  // ---- out on the grounds, and they're in the house: to the great room's glass, and through it
  breakInStep(dt) {
    const b = this.breakable, zc = (b.min[2] + b.max[2]) / 2, x = Math.min(b.min[0], b.max[0]);
    const at = new THREE.Vector2(x - 1.5, zc), c = this.chain;
    if (this.state !== 'chase') this.set('chase');
    const r = this.travel(dt, at, true);
    if (r === 'moving') return;
    const off = this.turnHead(new THREE.Vector2(x + 10, zc), dt);
    this.anim('CrawlIdle');
    if (off < 0.15) {
      this.g.heading = c.hf;
      this.set('smash');
      this.g.play('Smash');
    }
  }

  // ---------------------------------------------------------------- jams, body
  // a route, a crawl, and no progress along it in 3 s (rocking back and forth included): back
  // up, make that spot expensive for a while, plan the same goal again (3 jams: give it up)
  checkJam() {
    const moving = this.path && LOCO.slice(0, 2).includes(this.g.current?.getClip().name) && !(this.unstickUntil > this.time) &&
      ['chase', 'search', 'prowl', 'investigate', 'wait'].includes(this.state);
    if (!moving) { this._jam = null; return; }
    const rem = this.remaining();
    if (!this._jam || this._jam.goal !== this.goal || rem < this._jam.best - 0.8) { this._jam = { best: rem, t: this.time, goal: this.goal }; return; }
    if (this.time - this._jam.t > 3.0 && rem > 1.5) {
      const hd = this.chain.hd;
      this.stats.unsticks++;
      this.nav.markCost(hd.x, hd.y, 1.6, 6);
      this.jams.push({ x: hd.x, z: hd.y, until: this.time + 25 });
      this.unstickUntil = this.time + 1.0;
      this.path = null; this._replan = true;
      this._jamGoal = this._jamGoal?.goal === this.goal ? { goal: this.goal, n: this._jamGoal.n + 1 } : { goal: this.goal, n: 1 };
      if (this._jamGoal.n >= 3) { this.goalFailed = true; this._jamGoal = null; }
      this._jam = null;
    }
    // expired jam marks
    if (this.jams.length && this.jams[0].until < this.time) {
      const j = this.jams.shift();
      this.nav.markCost(j.x, j.z, 1.6, 0);
      for (const k of this.jams) this.nav.markCost(k.x, k.z, 1.6, 6);
    }
  }

  // the hindquarters swing round at most maxSwing rad/s (they used to snap round at doorways)
  limitSwing(dt) {
    const c = this.chain, hr = this.rearYaw();
    if (this._hr != null && dt > 0) {
      const d = wrap(hr - this._hr), lim = this.o.maxSwing * dt;
      if (Math.abs(d) > lim) {
        const a = this._hr + Math.sign(d) * lim, B = this.body;
        c.b.set(c.q.x - Math.sin(a) * B.Lb, c.q.y - Math.cos(a) * B.Lb);
        const p = this.pushCircle(c.b, B.r); c.b.x += p[0]; c.b.y += p[1];
        const m2 = c.q.clone().add(c.b).multiplyScalar(0.5), p2 = this.pushCircle(m2, B.r); c.b.x += p2[0]; c.b.y += p2[1];
        const k = c.b.clone().sub(c.q); c.b.copy(c.q).addScaledVector(k, B.Lb / (k.length() || 1));
      }
    }
    this._hr = this.rearYaw();
  }

  updateBlockers(player) {
    const c = this.chain, s = this.body.r * 0.8, h = this.state === 'reachUp' ? 6 : 2.5;
    [c.hd, c.q, c.b].forEach((p, i) => {
      this.blockers[i].min.set(p.x - s, 0, p.y - s);
      this.blockers[i].max.set(p.x + s, h, p.y + s);
      player?.pushOutOf?.(this.blockers[i]);
    });
    const t = this.tip(), f = c.hd.clone().sub(c.q).normalize(), fs = 0.55;
    const fx = t.x - f.x * 0.35, fz = t.y - f.y * 0.35;
    this.blockers[3].min.set(fx - fs, 0, fz - fs);
    this.blockers[3].max.set(fx + fs, h, fz + fs);
    player?.pushOutOf?.(this.blockers[3]);
  }

  strike(kind) {
    this.set(kind);
    this.hitDone = false;
    this.path = null;
    this.anim(kind === 'swipe' ? 'Swipe' : 'ReachUp', true);
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
  // (the window's collider spans all its bays: what's left of it either side of the hole stays
  // solid to swipes; sight goes through glass anyway)
  openGap() {
    const b = this.breakable;
    if (b) {
      this.nav.clearArea(Math.min(b.min[0], b.max[0]) - 1.5, Math.min(b.min[2], b.max[2]), Math.max(b.min[0], b.max[0]) + 1.5, Math.max(b.min[2], b.max[2]));
      const g = this.gapBox, keep = [];
      for (const w of this.walls) {
        if (!w.glass || !g.intersectsBox(w)) { keep.push(w); continue; }
        const alongZ = w.max.z - w.min.z > w.max.x - w.min.x, lo = alongZ ? 'z' : 'x';
        if (w.min[lo] < g.min[lo]) { const p = w.clone(); p.max[lo] = g.min[lo]; p.glass = true; keep.push(p); }
        if (w.max[lo] > g.max[lo]) { const p = w.clone(); p.min[lo] = g.max[lo]; p.glass = true; keep.push(p); }
      }
      this.walls = keep;
    }
    this.prepareNav();
  }

  // the cells it can get to from where it is now (and the rooms it prowls, the turn spots)
  prepareNav() {
    this.nav.flood(this.root.position.x, this.root.position.z);
    this.nav.clearance();
    this.prowlRooms = null;
    this._navGen = (this._navGen ?? 0) + 1;
  }
}

// Footsteps the Grimble can hear: a soft noise every stride while the player runs (walking is
// near-silent, crouching silent). Call update() every frame.
export class Footsteps {
  constructor(noise, { run = 0.5, walk = 0.12 } = {}) { this.noise = noise; this.o = { run, walk }; this.t = 0; }
  update(dt, player) {
    if (!player || player.isDown || player.hidden || player.crouching || !player.grounded) { this.t = 0; return; }
    const v = Math.hypot(player.vel.x, player.vel.z);
    if (v < 0.8) { this.t = 0; return; }
    const running = v > 4.5;
    this.t += dt;
    const every = running ? 0.32 : 0.5;
    if (this.t < every) return;
    this.t = 0;
    const loud = running ? this.o.run : this.o.walk;
    if (loud > 0) this.noise?.emit({ position: player.pos.clone(), loudness: loud, source: 'footsteps' });
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
