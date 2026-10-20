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

const DEFAULTS = {
  loopsBeforeSmash: 2,     // knock-wave-stare rounds at the glass before it breaks in
  crawlStride: 3.0, crawlCycle: 1.6,      // m / s per Crawl cycle (asset userData overrides)
  fastStride: 4.4, fastCycle: 1.2,        // CrawlFast
  smashHit: 1.2,           // s into Smash when the glass breaks
  swipeHit: 0.7, swipeReach: 2.8, swipeLen: 1.6,
  reachHit: 1.6, reachLen: 3.0, reachUp: 2.2,   // horizontal reach of ReachUp (m)
  sight: 40, hearing: 30,  // m
  turnRate: 2.4,           // rad/s
  memory: 6,               // s it keeps chasing where it last saw you
  cooldown: 3.5,           // s after a hit before it can hit again
  crawlRate: 2.0,          // playback rate of Crawl / CrawlFast (speed scales with it, so no sliding):
  fastRate: 2.4,           //   ~1.2 m/s prowling, ~4.5 m/s chasing (the player walks 3.4, runs 6.8)
  upperY: 3.5,             // player feet above this = on the upper floor
};

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
    // walls for sight: the shell's colliders only (props don't hide you from it)
    this.walls = level.colliders.map((c) => new THREE.Box3(new THREE.Vector3(...c.min), new THREE.Vector3(...c.max)));
    const areas = MAIN_SPACES.filter((r) => level.rooms[r]).map((r) => level.rooms[r].rect);
    this.breakable = (level.breakables || [])[0];
    if (this.breakable) {           // the lawn in front of the glass it breaks, so it can come through
      const b = this.breakable, z0 = Math.min(b.min[2], b.max[2]), z1 = Math.max(b.min[2], b.max[2]);
      areas.push([Math.min(b.min[0], b.max[0]) - 6, z0 - 1, Math.max(b.min[0], b.max[0]) + 0.5, z1 + 1]);
    }
    this.nav = new NavGrid(colliders, areas);
    this.double = DOUBLE_HEIGHT.filter((r) => level.rooms[r]).map((r) => level.rooms[r].rect);
    this.state = null;
    this.t = 0;
    this.path = null;
    this.lastSeen = null;
    this.seenAt = -1e9;
    this.time = 0;
    this.hitAt = -1e9;
    this.noise = null;
    window.__noise?.on?.((n) => this.hear(n));
    this._ray = new THREE.Ray();
    window.__hunt = this;
  }

  get root() { return this.g.root; }
  pos2() { return new THREE.Vector2(this.root.position.x, this.root.position.z); }

  hear(n) {
    const p = n.position, d = Math.hypot(p.x - this.root.position.x, p.z - this.root.position.z);
    if (d <= this.o.hearing * (n.loudness ?? 1)) this.noise = new THREE.Vector2(p.x, p.z);
  }

  start() { this.set('smash'); this.g.play('Smash'); }

  set(state) { this.state = state; this.t = 0; }

  // ---------------------------------------------------------------- perception
  sees(eye) {
    const head = this.root.position.clone().add(new THREE.Vector3(0, 2.4, 0));
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

  inDouble(x, z) { return this.double.some((r) => x >= r[0] && x <= r[2] && z >= r[1] && z <= r[3]); }

  // ---------------------------------------------------------------- movement
  goTo(target) {
    this.path = this.nav.path(this.pos2(), target);
    this.pathAt = this.time;
    return !!this.path;
  }

  follow(dt, fast) {
    if (!this.path || !this.path.length) return true;
    const o = this.o, speed = fast ? (o.fastStride / o.fastCycle) * o.fastRate : (o.crawlStride / o.crawlCycle) * o.crawlRate;
    const p = this.pos2(), next = this.path[0];
    const d = p.distanceTo(next);
    if (d < 0.4) { this.path.shift(); return !this.path.length; }
    this.turnToward(next, dt);
    // move along its facing once roughly lined up, so it doesn't sidestep
    const want = Math.atan2(next.x - p.x, next.y - p.y);
    const off = Math.abs(Math.atan2(Math.sin(want - this.g.heading), Math.cos(want - this.g.heading)));
    const step = Math.min(d, speed * dt * Math.max(0, Math.cos(Math.min(off, Math.PI / 2))));
    this.root.position.x += Math.sin(this.g.heading) * step;
    this.root.position.z += Math.cos(this.g.heading) * step;
    this.root.position.y = 0;
    this.g.play(fast ? 'CrawlFast' : 'Crawl');
    return false;
  }

  turnToward(target, dt) {
    const p = this.pos2();
    const want = Math.atan2(target.x - p.x, target.y - p.y);
    let d = want - this.g.heading;
    d = Math.atan2(Math.sin(d), Math.cos(d));
    this.g.heading += Math.sign(d) * Math.min(Math.abs(d), this.o.turnRate * dt);
    return Math.abs(d);
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
    const dist = this.pos2().distanceTo(pp);
    const canHit = this.time - this.hitAt > o.cooldown && !player?.knocked;

    switch (this.state) {
      case 'smash': {
        if (this.t >= o.smashHit && !this.broken) { this.broken = true; this.onBreak?.(); this.openGap(); }
        const len = g.actions.Smash?.getClip().duration ?? 2.5;
        if (this.t >= len) { this.set('prowl'); this.path = null; this.dropStaff(); }
        break;
      }
      case 'swipe': case 'reachUp': {
        const hitT = this.state === 'swipe' ? o.swipeHit : o.reachHit;
        const len = this.state === 'swipe' ? o.swipeLen : o.reachLen;
        this.turnToward(pp, dt);
        if (!this.hitDone && this.t >= hitT) {
          this.hitDone = true;
          const reach = this.state === 'swipe' ? o.swipeReach + 0.6 : o.reachUp + 0.9;
          const vertOk = this.state === 'swipe' ? !upper : upper;
          if (dist <= reach && vertOk && player?.knockDown) {
            const from = new THREE.Vector3(this.root.position.x, feet.y, this.root.position.z);
            player.knockDown(from);
            this.hitAt = this.time;
          }
        }
        if (this.t >= len) this.set(seen ? 'chase' : 'search');
        break;
      }
      default: {
        // close enough to strike?
        if (seen && canHit) {
          if (!upper && dist <= o.swipeReach && this.turnToward(pp, dt) < 0.5) { this.strike('swipe'); break; }
          if (upper && dist <= o.reachUp + 0.5 && this.inDouble(this.root.position.x, this.root.position.z)
            && this.turnToward(pp, dt) < 0.5) { this.strike('reachUp'); break; }
        }
        if (seen || this.time - this.seenAt < o.memory) {
          // chase toward the player (or the nearest place below them), re-planning twice a second
          const target = this.lastSeen;
          if (seen && !upper && dist <= o.swipeReach * 0.85) { this.lurk(dt, pp); this.state = 'chase'; break; }   // close: hold and strike
          if (!this.path || this.time - this.pathAt > 0.5) this.goTo(target);
          if (!this.path) { this.lurk(dt, pp); break; }
          const arrived = this.follow(dt, true);
          if (arrived) this.lurk(dt, pp);
          this.state = 'chase';
        } else if (this.noise) {
          if (this.state !== 'search' || !this.path) { this.goTo(this.noise); this.set('search'); }
          if (this.follow(dt, false)) { this.noise = null; this.path = null; this.set('prowl'); this.idleFor = 3; }
        } else {
          // prowl: wander between random open places in the main spaces, pausing to sniff
          if (this.state !== 'prowl') { this.set('prowl'); this.path = null; }
          if (this.idleFor > 0) { this.idleFor -= dt; g.play('CrawlIdle'); break; }
          if (!this.path) { if (!this.goTo(this.randomSpot())) this.idleFor = 1; }
          else if (this.follow(dt, false)) { this.path = null; this.idleFor = 2 + Math.random() * 4; }
        }
      }
    }
    // speed of the cycles matches the ground covered (no sliding)
    g.root.rotation.y = g.heading;
  }

  // out of reach (a side room, upstairs away from the balustrade): wait near, watching
  lurk(dt, pp) {
    this.turnToward(pp, dt);
    this.g.play('CrawlIdle');
  }

  strike(kind) {
    this.set(kind);
    this.hitDone = false;
    this.path = null;
    this.g.play(kind === 'swipe' ? 'Swipe' : 'ReachUp');
  }

  randomSpot() {
    for (let i = 0; i < 40; i++) {
      const k = Math.floor(Math.random() * this.nav.open.length);
      if (this.nav.walkable(k)) return this.nav.centre(k);
    }
    return this.pos2();
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

  // the smashed bays become passable
  openGap() {
    const b = this.breakable;
    if (b) this.nav.clear(Math.min(b.min[0], b.max[0]) - 1.5, Math.min(b.min[2], b.max[2]), Math.max(b.min[0], b.max[0]) + 1.5, Math.max(b.min[2], b.max[2]));
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
