import * as THREE from 'three';

// Where the invaders (human-sized) can walk: the whole house on both floors, the stair between
// them, the side rooms (their doors are wide enough for a person) and the grounds round the house.
//
// Three layers of one global 2D grid (same origin and cell everywhere, so a cell (i, j) is the
// same spot on every layer):
//   ground  y ~ 0 (the house's ground floor, the terraces, the lawn out to the approach)
//   upper   y = 4.6: only cells over a floor slab (a collider whose top is at the upper floor
//           height): the upper rooms, the galleries and the stair's landing; not the voids over
//           the double-height rooms
//   stair   the ramp over the treads (level.ramps): its height is the ramp's lerp; it joins the
//           ground layer at its foot and the upper layer at its top
// A cell is blocked when a static collider reaches into the body's height band above that
// layer's floor ([floor + 0.3, floor + 1.9], so rugs and thresholds don't block and furniture
// does) within `radius` of it. Interactables' own colliders (door leaves, the garage door) are
// left out of the static grid: doors are portals. A door's cells (its shut leaf, swept by the
// radius) carry the door's id; a locked door is impassable, a shut one costs a little extra
// (agents open it on the way through: invaders_brain.js).
//
// A* over (layer, cell) with 8 neighbours (no corner cutting) plus the stair links; the result is
// string-pulled within a layer and keeps a waypoint at every door and every layer change.
// `BoxGrid` indexes boxes in 2 m columns for the rays (sight, line of fire, wall muffling).

export const UPPER_Y = 4.6;
const NB = [[1, 0, 1], [-1, 0, 1], [0, 1, 1], [0, -1, 1], [1, 1, 1.4142], [1, -1, 1.4142], [-1, 1, 1.4142], [-1, -1, 1.4142]];

// ------------------------------------------------------------------ boxes in columns, for rays
export class BoxGrid {
  constructor(boxes, { cell = 2 } = {}) {
    this.cell = cell;
    this.boxes = boxes.filter((b) => !b.isEmpty());
    let x0 = Infinity, z0 = Infinity, x1 = -Infinity, z1 = -Infinity;
    for (const b of this.boxes) { x0 = Math.min(x0, b.min.x); z0 = Math.min(z0, b.min.z); x1 = Math.max(x1, b.max.x); z1 = Math.max(z1, b.max.z); }
    if (!this.boxes.length) { x0 = z0 = 0; x1 = z1 = 1; }
    this.x0 = x0; this.z0 = z0;
    this.w = Math.max(1, Math.ceil((x1 - x0) / cell)); this.h = Math.max(1, Math.ceil((z1 - z0) / cell));
    this.cells = Array.from({ length: this.w * this.h }, () => []);
    this.boxes.forEach((b, n) => {
      const i0 = this.ci(b.min.x), i1 = this.ci(b.max.x), j0 = this.cj(b.min.z), j1 = this.cj(b.max.z);
      for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) this.cells[j * this.w + i].push(n);
    });
    this.stamp = new Uint32Array(this.boxes.length);
    this.gen = 0;
    this._ray = new THREE.Ray();
    this._hit = new THREE.Vector3();
  }
  ci(x) { return Math.min(this.w - 1, Math.max(0, Math.floor((x - this.x0) / this.cell))); }
  cj(z) { return Math.min(this.h - 1, Math.max(0, Math.floor((z - this.z0) / this.cell))); }

  // every box the segment a -> b may touch (columns along it, Amanatides-Woo), once each
  each(a, b, fn) {
    const gen = ++this.gen, W = this.w, C = this.cell;
    let i = this.ci(a.x), j = this.cj(a.z);
    const ie = this.ci(b.x), je = this.cj(b.z);
    const dx = b.x - a.x, dz = b.z - a.z;
    const si = Math.sign(dx), sj = Math.sign(dz);
    const tdx = si ? Math.abs(C / dx) : Infinity, tdz = sj ? Math.abs(C / dz) : Infinity;
    const fx = (a.x - this.x0) / C - Math.floor((a.x - this.x0) / C), fz = (a.z - this.z0) / C - Math.floor((a.z - this.z0) / C);
    let tx = si > 0 ? (1 - fx) * tdx : si < 0 ? fx * tdx : Infinity;
    let tz = sj > 0 ? (1 - fz) * tdz : sj < 0 ? fz * tdz : Infinity;
    for (let guard = 0; guard < 400; guard++) {
      for (const n of this.cells[j * W + i]) {
        if (this.stamp[n] === gen) continue;
        this.stamp[n] = gen;
        if (fn(this.boxes[n]) === true) return true;
      }
      if (i === ie && j === je) break;
      if (tx < tz) { if (tx > 1) break; i += si; tx += tdx; } else { if (tz > 1) break; j += sj; tz += tdz; }
      if (i < 0 || j < 0 || i >= W || j >= this.h) break;
    }
    return false;
  }

  // is a -> b blocked (a hit closer than |ab| - margin; a box containing `a` doesn't count)?
  blocked(a, b, margin = 0.1, skip = null) {
    const to = this._d ??= new THREE.Vector3();
    to.subVectors(b, a);
    const d = to.length();
    if (d < 1e-6) return false;
    this._ray.set(a, to.divideScalar(d));
    const lo = Math.min(a.y, b.y), hi = Math.max(a.y, b.y);
    return this.each(a, b, (w) => {
      if (w.max.y < lo || w.min.y > hi) return false;
      if (skip && skip(w)) return false;
      if (w.containsPoint(a)) return false;
      return !!(this._ray.intersectBox(w, this._hit) && this._hit.distanceTo(a) < d - margin);
    });
  }

  // the hits along a -> b, [distance, box] sorted (for counting walls between)
  hits(a, b) {
    const to = new THREE.Vector3().subVectors(b, a), d = to.length(), out = [];
    if (d < 1e-6) return out;
    this._ray.set(a, to.divideScalar(d));
    const lo = Math.min(a.y, b.y), hi = Math.max(a.y, b.y);
    this.each(a, b, (w) => {
      if (w.max.y < lo || w.min.y > hi || w.containsPoint(a) || w.containsPoint(b)) return false;
      if (this._ray.intersectBox(w, this._hit)) { const t = this._hit.distanceTo(a); if (t < d) out.push([t, w]); }
      return false;
    });
    return out.sort((p, q) => p[0] - q[0]);
  }

  // boxes whose xz footprint comes within r of (x, z), vertical span overlapping [y0, y1]
  near(x, z, r, y0, y1, out = []) {
    out.length = 0;
    const gen = ++this.gen, i0 = this.ci(x - r), i1 = this.ci(x + r), j0 = this.cj(z - r), j1 = this.cj(z + r);
    for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) for (const n of this.cells[j * this.w + i]) {
      if (this.stamp[n] === gen) continue;
      this.stamp[n] = gen;
      const b = this.boxes[n];
      if (b.max.y < y0 || b.min.y > y1 || b.min.x > x + r || b.max.x < x - r || b.min.z > z + r || b.max.z < z - r) continue;
      out.push(b);
    }
    return out;
  }
}

// ------------------------------------------------------------------ the layered grid
class Layer {
  constructor(name, nav, rect, floor) {
    this.name = name; this.floor = floor;
    const c = nav.cell;
    this.i0 = Math.floor((rect[0] - nav.X0) / c); this.j0 = Math.floor((rect[1] - nav.Z0) / c);
    this.w = Math.ceil((rect[2] - nav.X0) / c) - this.i0; this.h = Math.ceil((rect[3] - nav.Z0) / c) - this.j0;
    this.n = this.w * this.h;
    this.open = new Uint8Array(this.n);
    this.blocked = new Uint8Array(this.n);
    this.base = new Uint8Array(this.n);     // extra cost near walls (routes keep off them)
    this.door = new Int16Array(this.n).fill(-1);
    this.off = 0;                           // index of its first cell in the nav's id space
  }
}

export class HouseNav {
  // boxes: the static colliders (shell + props + grounds; not interactables' own); doors: portals
  // [{box (shut leaf, world), open(), isOpen(), locked()}]
  constructor({ boxes, level, doors = [], cell = 0.25, radius = 0.28, ground = [-50, -45, 50, 50] }) {
    this.cell = cell; this.radius = radius;
    this.X0 = Math.floor(ground[0] / cell) * cell; this.Z0 = Math.floor(ground[1] / cell) * cell;
    this.level = level;
    this.ramp = (level.ramps || [])[0] ?? null;
    const G = level.grounds ?? {};
    this.houseRect = G.house ?? [-26, -20, 26, 20];
    this.terraces = G.terraces ?? [];
    this.lawnY = G.lawn ?? -0.08; this.terraceY = G.terrace ?? 0;
    const H = this.houseRect;
    this.layers = [new Layer('ground', this, ground, 0), new Layer('upper', this, [H[0], H[1], H[2], H[3]], UPPER_Y)];
    if (this.ramp) {
      const R = this.ramp;
      this.layers.push(new Layer('stair', this, [Math.min(...R.x) - 0.3, Math.min(...R.z) - 0.3, Math.max(...R.x) + 0.3, Math.max(...R.z) + 0.3], 0));
    }
    let off = 0;
    for (const L of this.layers) { L.off = off; off += L.n; }
    this.N = off;
    this.cost = new Uint8Array(this.N);     // dynamic extra cost (jams; crowding)
    this.build(boxes);
    this.doors = [];
    for (const d of doors) this.addDoor(d);
    this.clearance();
    this.links();
    this.components();
    // A* scratch
    this._g = new Float32Array(this.N); this._came = new Int32Array(this.N); this._stamp = new Uint32Array(this.N); this._closed = new Uint32Array(this.N); this._gen = 0;
    this.heap = new Heap(4096);
    this.stats = { plans: 0, expanded: 0, ms: 0, fails: 0 };
  }

  // ---- ids
  layerOf(id) { const L = this.layers; return id >= L[1].off ? (L[2] && id >= L[2].off ? L[2] : L[1]) : L[0]; }
  id(L, x, z) {
    const i = Math.floor((x - this.X0) / this.cell) - L.i0, j = Math.floor((z - this.Z0) / this.cell) - L.j0;
    return i < 0 || j < 0 || i >= L.w || j >= L.h ? -1 : L.off + j * L.w + i;
  }
  xz(id, out = new THREE.Vector2()) {
    const L = this.layerOf(id), k = id - L.off;
    return out.set(this.X0 + (L.i0 + (k % L.w) + 0.5) * this.cell, this.Z0 + (L.j0 + Math.floor(k / L.w) + 0.5) * this.cell);
  }
  rampH(x) {
    const R = this.ramp, t = (x - R.x[0]) / (R.x[1] - R.x[0]);
    return R.y[0] + (R.y[1] - R.y[0]) * Math.min(1, Math.max(0, t));
  }
  onRamp(x, z, m = 0) {
    const R = this.ramp;
    return !!R && x >= Math.min(...R.x) - m && x <= Math.max(...R.x) + m && z >= Math.min(...R.z) - m && z <= Math.max(...R.z) + m;
  }
  inHouse(x, z, m = 0) { const H = this.houseRect; return x >= H[0] - m && x <= H[2] + m && z >= H[1] - m && z <= H[3] + m; }
  // the height of the floor under (x, z) on layer L
  floorY(L, x, z) {
    if (L.name === 'upper') return UPPER_Y;
    if (L.name === 'stair') return this.rampH(x);
    if (this.inHouse(x, z)) return 0;
    return this.terraces.some((t) => x >= t[0] && x <= t[2] && z >= t[1] && z <= t[3]) ? this.terraceY : this.lawnY;
  }
  // which layer a point (feet) is on
  layerAt(x, y, z) {
    if (this.ramp && this.onRamp(x, z) && y > 0.25 && y < UPPER_Y - 0.25) return this.layers[2];
    return y > UPPER_Y - 1.0 ? this.layers[1] : this.layers[0];
  }
  idAt(x, y, z) { return this.id(this.layerAt(x, y, z), x, z); }

  // (breach: a locked door counts as passable: it can be kicked in)
  walkable(id, breach = false) {
    if (id < 0) return false;
    const L = this.layerOf(id), k = id - L.off;
    if (!L.open[k] || L.blocked[k]) return false;
    const d = L.door[k];
    return d < 0 || breach || !this.doors[d].locked();
  }

  // connected components with the doors as they are now (locked ones closed): a plan to another
  // component fails at once instead of searching the whole house. Recomputed when a lock changes.
  components() {
    const comp = this.comp ??= new Int32Array(this.N);
    comp.fill(-1);
    let c = 0;
    const list = new Int32Array(this.N);
    for (let s = 0; s < this.N; s++) {
      if (comp[s] >= 0 || !this.walkable(s)) continue;
      let n = 0; list[n++] = s; comp[s] = c;
      for (let h = 0; h < n; h++) {
        const id = list[h], L = this.layerOf(id), k = id - L.off, i = k % L.w, j = (k - i) / L.w;
        for (let q = 0; q < 4; q++) {
          const ii = i + NB[q][0], jj = j + NB[q][1];
          if (ii < 0 || jj < 0 || ii >= L.w || jj >= L.h) continue;
          const nid = L.off + jj * L.w + ii;
          if (comp[nid] < 0 && this.walkable(nid)) { comp[nid] = c; list[n++] = nid; }
        }
        const ln = this.link.get(id);
        if (ln) for (const nid of ln) if (comp[nid] < 0 && this.walkable(nid)) { comp[nid] = c; list[n++] = nid; }
      }
      c++;
    }
    this.compCount = c;
    this.lockKey = this.doors.map((d) => (d.locked() ? 1 : 0)).join('');
    return c;
  }
  // call now and then: recompute the components when a door's lock changed
  checkLocks() {
    const key = this.doors.map((d) => (d.locked() ? 1 : 0)).join('');
    if (key !== this.lockKey) this.components();
  }
  connected(a, b) { return a >= 0 && b >= 0 && (!this.comp || this.comp[a] === this.comp[b]); }

  // ---- building
  build(boxes) {
    const r = this.radius, c = this.cell;
    const [G, U, S] = this.layers;
    G.open.fill(1);
    // the upper floor: cells over a slab whose top is at the upper floor height
    for (const b of boxes) {
      if (b.max.y < UPPER_Y - 0.12 || b.max.y > UPPER_Y + 0.08 || b.max.y - b.min.y > 1.0) continue;
      this.fill(U, b.min.x, b.min.z, b.max.x, b.max.z, (L, k) => (L.open[k] = 1), true);
    }
    if (S) {
      const R = this.ramp;
      this.fill(S, Math.min(...R.x), Math.min(...R.z), Math.max(...R.x), Math.max(...R.z), (L, k) => (L.open[k] = 1), true);
      // (the stair's own cells are carved out of the upper layer: no slab there anyway)
    }
    // (secret passage) rooms off the nav (mansion.json rooms[r].nav === false: below ground; the
    // shaft that stands in the den): every cell of a layer whose floor lies in their height span
    for (const r of Object.values(this.level.rooms ?? {})) {
      if (r.nav !== false) continue;
      for (const L of [G, U]) {
        if (L.floor < r.floor - 0.05 || L.floor > r.floor + r.height) continue;
        this.fill(L, r.rect[0], r.rect[1], r.rect[2], r.rect[3], (LL, k) => (LL.blocked[k] = 1));
      }
    }
    for (const b of boxes) {
      if (b.isEmpty()) continue;
      for (const L of [G, U]) {
        const lo = L.floor + 0.3, hi = L.floor + 1.9;
        if (b.max.y < lo || b.min.y > hi) continue;
        this.fill(L, b.min.x - r, b.min.z - r, b.max.x + r, b.max.z + r, (LL, k) => (LL.blocked[k] = 1));
      }
      if (S) {
        // the stair: the band rides on the ramp's height at each cell
        if (b.max.x + r < S.i0 * c + this.X0 || b.min.x - r > (S.i0 + S.w) * c + this.X0) continue;
        this.fill(S, b.min.x - r, b.min.z - r, b.max.x + r, b.max.z + r, (LL, k) => {
          const x = this.X0 + (LL.i0 + (k % LL.w) + 0.5) * c, h = this.rampH(x);
          if (b.max.y >= h + 0.3 && b.min.y <= h + 1.9) LL.blocked[k] = 1;
        });
      }
    }
  }
  // cells of layer L overlapping a rect (centres inside it with `centres`)
  fill(L, x0, z0, x1, z1, fn, centres = false) {
    const c = this.cell;
    const ia = Math.max(0, (centres ? Math.ceil((x0 - this.X0) / c - 0.5) : Math.floor((x0 - this.X0) / c)) - L.i0);
    const ib = Math.min(L.w - 1, (centres ? Math.floor((x1 - this.X0) / c - 0.5) : Math.floor((x1 - this.X0) / c)) - L.i0);
    const ja = Math.max(0, (centres ? Math.ceil((z0 - this.Z0) / c - 0.5) : Math.floor((z0 - this.Z0) / c)) - L.j0);
    const jb = Math.min(L.h - 1, (centres ? Math.floor((z1 - this.Z0) / c - 0.5) : Math.floor((z1 - this.Z0) / c)) - L.j0);
    for (let j = ja; j <= jb; j++) for (let i = ia; i <= ib; i++) fn(L, j * L.w + i);
  }

  // a door: its shut leaf's cells (swept by the radius, along the wall it closes) become its portal
  addDoor(d) {
    const id = this.doors.length, b = d.box, r = this.radius + 0.05;
    const L = b.min.y > UPPER_Y - 1 ? this.layers[1] : this.layers[0];
    d.id = id; d.layer = L.name;
    d.centre = new THREE.Vector2((b.min.x + b.max.x) / 2, (b.min.z + b.max.z) / 2);
    // the leaf's across-wall direction: its thin axis
    d.normal = b.max.x - b.min.x < b.max.z - b.min.z ? new THREE.Vector2(1, 0) : new THREE.Vector2(0, 1);
    d.width = Math.max(b.max.x - b.min.x, b.max.z - b.min.z);
    this.doors.push(d);
    let n = 0;
    this.fill(L, b.min.x - r, b.min.z - r, b.max.x + r, b.max.z + r, (LL, k) => { if (LL.door[k] < 0) { LL.door[k] = id; n++; } });
    d.cells = n;
    return d;
  }
  doorAt(id) { if (id < 0) return null; const L = this.layerOf(id), k = L.door[id - L.off]; return k >= 0 ? this.doors[k] : null; }

  // metres to the nearest blocked cell (per layer, chamfer): base cost near walls
  clearance() {
    for (const L of this.layers) {
      const W = L.w, H = L.h, d = new Float32Array(L.n), c1 = this.cell, c2 = c1 * Math.SQRT2;
      for (let k = 0; k < L.n; k++) d[k] = L.open[k] && !L.blocked[k] ? Infinity : 0;
      for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
        const k = j * W + i; let v = d[k]; if (!v) continue;
        if (i > 0) v = Math.min(v, d[k - 1] + c1);
        if (j > 0) { v = Math.min(v, d[k - W] + c1); if (i > 0) v = Math.min(v, d[k - W - 1] + c2); if (i < W - 1) v = Math.min(v, d[k - W + 1] + c2); }
        d[k] = v;
      }
      for (let j = H - 1; j >= 0; j--) for (let i = W - 1; i >= 0; i--) {
        const k = j * W + i; let v = d[k]; if (!v) continue;
        if (i < W - 1) v = Math.min(v, d[k + 1] + c1);
        if (j < H - 1) { v = Math.min(v, d[k + W] + c1); if (i < W - 1) v = Math.min(v, d[k + W + 1] + c2); if (i > 0) v = Math.min(v, d[k + W - 1] + c2); }
        d[k] = v;
      }
      L.clear = d;
      for (let k = 0; k < L.n; k++) { const v = d[k]; L.base[k] = v < 0.2 ? 2 : v < 0.45 ? 1 : 0; }
    }
  }

  // the stair's links: its low cells to the ground cells there, its top cells to the landing
  links() {
    this.link = new Map();       // id -> [ids]
    const S = this.layers[2];
    if (!S) return;
    const add = (a, b) => { (this.link.get(a) ?? this.link.set(a, []).get(a)).push(b); (this.link.get(b) ?? this.link.set(b, []).get(b)).push(a); };
    const [G, U] = this.layers, p = new THREE.Vector2();
    let lo = 0, hi = 0;
    for (let k = 0; k < S.n; k++) {
      const id = S.off + k;
      if (!this.walkable(id)) continue;
      this.xz(id, p);
      const h = this.rampH(p.x);
      const T = h < 0.32 ? G : h > UPPER_Y - 0.32 ? U : null;
      if (!T) continue;
      for (let dj = -1; dj <= 1; dj++) for (let di = -1; di <= 1; di++) {
        const t = this.id(T, p.x + di * this.cell, p.y + dj * this.cell);
        if (t >= 0 && this.walkable(t)) { add(id, t); if (T === G) lo++; else hi++; }
      }
    }
    this.linkCount = { lo, hi };
  }

  // ---- queries
  // the walkable cell nearest (x, z) on layer L within maxR m (optionally one `accept` takes)
  nearest(L, x, z, maxR = 3, accept = null) {
    const ok = (id) => id >= 0 && this.walkable(id) && (!accept || accept(id));
    const k0 = this.id(L, x, z);
    if (ok(k0)) return k0;
    const R = Math.ceil(maxR / this.cell);
    let best = -1, bd = Infinity;
    for (let r = 1; r <= R && best < 0; r++) {
      for (let dj = -r; dj <= r; dj++) for (let di = -r; di <= r; di++) {
        if (Math.max(Math.abs(di), Math.abs(dj)) !== r) continue;
        const id = this.id(L, x + di * this.cell, z + dj * this.cell), d = di * di + dj * dj;
        if (d < bd && ok(id)) { bd = d; best = id; }
      }
    }
    return best;
  }
  // a point (feet x, y, z) -> its cell (on its layer, else the nearest walkable one there)
  cellFor(x, y, z, maxR = 3) {
    const L = this.layerAt(x, y, z);
    let k = this.nearest(L, x, z, maxR);
    if (k < 0 && L.name === 'stair') k = this.nearest(this.layers[y > 2.3 ? 1 : 0], x, z, maxR);
    return k;
  }

  // A* from cell s to cell g. Options: maxIter (expansions), doorCost (a shut door's extra),
  // avoid(id) -> extra cost. Returns [{x, z, layer, door}] waypoints or null; this.lastLen = m
  path(s, g, { maxIter = 60000, doorCost = 3, avoid = null, breach = false, hw = 1.4 } = {}) {
    const t0 = performance.now();
    this.lastLen = 0;
    this.stats.plans++;
    const W = breach ? (id) => this.walkable(id, true) : (id) => this.walkable(id);
    if (s < 0 || g < 0 || !W(s) || !W(g) || (!breach && this.comp && this.comp[s] !== this.comp[g])) { this.stats.fails++; return null; }
    const gScore = this._g, came = this._came, stamp = this._stamp, closed = this._closed, cost = this.cost;
    const gen = ++this._gen, heap = this.heap;
    heap.clear();
    const gp = this.xz(g, new THREE.Vector2()), gx = gp.x / this.cell, gz = gp.y / this.cell;
    const gL = this.layerOf(g);
    const gY = gL.name === 'upper' ? UPPER_Y : 0;
    const stairP = this.ramp ? new THREE.Vector2(this.ramp.x[0], (this.ramp.z[0] + this.ramp.z[1]) / 2) : null;
    const hcost = (id, L, x, z) => {
      // octile to the goal; a floor change has to go by the stair: via its foot / top
      const fY = L.name === 'upper' ? UPPER_Y : L.name === 'stair' ? 2 : 0;
      if (stairP && Math.abs(fY - gY) > 3) {
        const sx = stairP.x / this.cell, sz = stairP.y / this.cell;
        const a = oct(x - sx, z - sz), b = oct(sx - gx, sz - gz);
        return a + b;
      }
      return oct(x - gx, z - gz);
    };
    const pos = new THREE.Vector2();
    this.xz(s, pos);
    gScore[s] = 0; came[s] = -1; stamp[s] = gen;
    heap.push(s, hcost(s, this.layerOf(s), pos.x / this.cell, pos.y / this.cell));
    let found = false, iter = 0;
    while (heap.size && iter++ < maxIter) {
      const id = heap.pop();
      if (id === g) { found = true; break; }
      if (closed[id] === gen) continue;
      closed[id] = gen;
      const L = this.layerOf(id), k = id - L.off, i = k % L.w, j = (k - i) / L.w;
      const step = (nid, c) => {
        if (closed[nid] === gen || !W(nid)) return;
        const NL = this.layerOf(nid), nk = nid - NL.off;
        let w = c * (1 + cost[nid] + NL.base[nk]);
        const dr = NL.door[nk];
        if (dr >= 0 && L.door[k] !== dr && !this.doors[dr].isOpen()) w += this.doors[dr].locked() ? 40 : doorCost;
        if (avoid) w += avoid(nid);
        const ng = gScore[id] + w;
        if (stamp[nid] !== gen || ng < gScore[nid]) {
          stamp[nid] = gen; gScore[nid] = ng; came[nid] = id;
          const ni = (nk % NL.w) + NL.i0, nj = Math.floor(nk / NL.w) + NL.j0;
          heap.push(nid, ng + hw * hcost(nid, NL, ni + 0.5 + this.X0 / this.cell, nj + 0.5 + this.Z0 / this.cell));
        }
      };
      for (let q = 0; q < 8; q++) {
        const di = NB[q][0], dj = NB[q][1];
        const ii = i + di, jj = j + dj;
        if (ii < 0 || jj < 0 || ii >= L.w || jj >= L.h) continue;
        const nid = L.off + jj * L.w + ii;
        if (di && dj && (!W(L.off + j * L.w + ii) || !W(L.off + jj * L.w + i))) continue;
        step(nid, NB[q][2]);
      }
      const ln = this.link.get(id);
      if (ln) for (const nid of ln) step(nid, 1.2);
    }
    this.stats.expanded += iter;
    this.stats.ms += performance.now() - t0;
    if (!found) { this.stats.fails++; return null; }
    const cells = [];
    for (let id = g; id !== -1; id = came[id]) cells.push(id);
    cells.reverse();
    return this.pull(cells);
  }

  // string-pull: drop cells while the straight line stays on walkable cells of one layer; keep
  // a waypoint at each layer change and on each door (its centre, so the leaf is passed square)
  pull(cells) {
    const P = (id) => { const v = this.xz(id); const L = this.layerOf(id); return { x: v.x, z: v.y, layer: L.name, id, door: null }; };
    const out = [P(cells[0])];
    let a = 0;
    for (let b = 1; b < cells.length; b++) {
      const La = this.layerOf(cells[a]), Lb = this.layerOf(cells[b]);
      const dB = this.doorAt(cells[b]), dPrev = this.doorAt(cells[b - 1]);
      if (Lb !== La) { if (b - 1 > a) out.push(P(cells[b - 1])); out.push(P(cells[b])); a = b; continue; }
      if (dB && dB !== dPrev) {
        // entering a door: a waypoint just before, the door's centre, then on
        if (b - 1 > a) out.push(P(cells[b - 1]));
        const w = { x: dB.centre.x, z: dB.centre.y, layer: Lb.name, id: cells[b], door: dB };
        out.push(w);
        // skip on to the first cell past the door
        let e = b; while (e + 1 < cells.length && this.doorAt(cells[e + 1]) === dB) e++;
        if (e + 1 < cells.length) { out.push(P(cells[e + 1])); a = e + 1; b = e + 1; }
        else a = e;
        continue;
      }
      if (b - a >= 2 && !this.lineOK(cells[a], cells[b])) { out.push(P(cells[b - 1])); a = b - 1; }
    }
    const last = P(cells[cells.length - 1]);
    if (out[out.length - 1].id !== last.id) out.push(last);
    for (let i = 1; i < out.length; i++) this.lastLen += Math.hypot(out[i].x - out[i - 1].x, out[i].z - out[i - 1].z);
    return out;
  }
  // the straight line between two cells of one layer stays on walkable, wall-clear cells, not
  // through a door's cells
  lineOK(a, b) {
    const L = this.layerOf(a), pa = this.xz(a), pb = this.xz(b);
    const d = pa.distanceTo(pb), n = Math.ceil(d / (this.cell * 0.5));
    const lim = Math.max(L.base[a - L.off], L.base[b - L.off]);
    for (let s = 1; s < n; s++) {
      const t = s / n, id = this.id(L, pa.x + (pb.x - pa.x) * t, pa.y + (pb.y - pa.y) * t);
      if (!this.walkable(id) || this.cost[id] || L.base[id - L.off] > lim || L.door[id - L.off] >= 0) return false;
    }
    return true;
  }

  // a straight walk from (x, z) toward (tx, tz) on layer L is open (no blocked cells)?
  clearWalk(L, x, z, tx, tz) {
    const d = Math.hypot(tx - x, tz - z), n = Math.ceil(d / (this.cell * 0.5));
    for (let s = 1; s <= n; s++) { const t = s / n; if (!this.walkable(this.id(L, x + (tx - x) * t, z + (tz - z) * t))) return false; }
    return true;
  }

  // walking distances from cell s out to maxD m (sound going round through the open ways; a shut
  // door passes it with `doorPenalty` m extra): returns id -> metres (Infinity beyond)
  distField(s, maxD, doorPenalty = 4) {
    const N = this.N;
    this._dd ??= new Float32Array(N); this._ds ??= new Uint32Array(N); this._dgen = (this._dgen ?? 0) + 1;
    const dist = this._dd, stamp = this._ds, gen = this._dgen, heap = this._dheap ??= new Heap(4096), c = this.cell;
    heap.clear();
    const get = (id) => (id >= 0 && stamp[id] === gen ? dist[id] : Infinity);
    if (s < 0 || !this.walkable(s, true)) return get;
    dist[s] = 0; stamp[s] = gen; heap.push(s, 0);
    let n = 0;
    while (heap.size && n++ < 200000) {
      const id = heap.pop(), d0 = dist[id];
      if (d0 > maxD) break;
      const L = this.layerOf(id), k = id - L.off, i = k % L.w, j = (k - i) / L.w;
      const relax = (nid, w) => {
        if (!this.walkable(nid, true)) return;
        const NL = this.layerOf(nid), dr = NL.door[nid - NL.off];
        if (dr >= 0 && L.door[k] !== dr && !this.doors[dr].isOpen()) w += doorPenalty;
        const nd = d0 + w;
        if (stamp[nid] !== gen || nd < dist[nid]) { stamp[nid] = gen; dist[nid] = nd; heap.push(nid, nd); }
      };
      for (let q = 0; q < 8; q++) {
        const ii = i + NB[q][0], jj = j + NB[q][1];
        if (ii < 0 || jj < 0 || ii >= L.w || jj >= L.h) continue;
        relax(L.off + jj * L.w + ii, NB[q][2] * c);
      }
      const ln = this.link.get(id);
      if (ln) for (const nid of ln) relax(nid, c * 1.2);
    }
    return get;
  }

  // flood from a cell: which ids are connected (for tests / spawn validation)
  flood(s) {
    const seen = new Uint8Array(this.N), list = [s];
    if (s < 0) return seen;
    seen[s] = 1;
    for (let h = 0; h < list.length; h++) {
      const id = list[h], L = this.layerOf(id), k = id - L.off, i = k % L.w, j = (k - i) / L.w;
      for (const [di, dj] of NB) {
        const ii = i + di, jj = j + dj;
        if (ii < 0 || jj < 0 || ii >= L.w || jj >= L.h) continue;
        const nid = L.off + jj * L.w + ii;
        if (!seen[nid] && this.walkable(nid)) { seen[nid] = 1; list.push(nid); }
      }
      for (const nid of this.link.get(id) ?? []) if (!seen[nid] && this.walkable(nid)) { seen[nid] = 1; list.push(nid); }
    }
    this.reachCount = list.length;
    return seen;
  }

  // random walkable cells inside a rect on a layer (for search / sweep points)
  cellsIn(L, rect, step = 1.0) {
    const out = [];
    for (let z = rect[1] + step / 2; z < rect[3]; z += step) for (let x = rect[0] + step / 2; x < rect[2]; x += step) {
      const id = this.id(L, x, z);
      if (id >= 0 && this.walkable(id) && L.clear[id - L.off] > 0.25) out.push(id);
    }
    return out;
  }
}

const oct = (dx, dz) => { dx = Math.abs(dx); dz = Math.abs(dz); return Math.max(dx, dz) + 0.4142 * Math.min(dx, dz); };

class Heap {
  constructor(cap) { this.k = new Int32Array(cap); this.p = new Float32Array(cap); this.size = 0; }
  clear() { this.size = 0; }
  push(key, pri) {
    if (this.size === this.k.length) {
      const k = new Int32Array(this.k.length * 2), p = new Float32Array(this.k.length * 2);
      k.set(this.k); p.set(this.p); this.k = k; this.p = p;
    }
    const K = this.k, P = this.p;
    let i = this.size++;
    while (i > 0) {
      const u = (i - 1) >> 1;
      if (P[u] <= pri) break;
      K[i] = K[u]; P[i] = P[u]; i = u;
    }
    K[i] = key; P[i] = pri;
  }
  pop() {
    const K = this.k, P = this.p, top = K[0], n = --this.size;
    if (n > 0) {
      const lk = K[n], lp = P[n];
      let i = 0;
      for (;;) {
        const l = 2 * i + 1;
        if (l >= n) break;
        const r = l + 1, m = r < n && P[r] < P[l] ? r : l;
        if (P[m] >= lp) break;
        K[i] = K[m]; P[i] = P[m]; i = m;
      }
      K[i] = lk; P[i] = lp;
    }
    return top;
  }
}
