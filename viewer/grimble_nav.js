import * as THREE from 'three';

// Where the crawling Grimble can go: a 2D grid over the ground floor's main spaces (great room,
// entry, galleries, courtyard, kitchen, dining), the lawn it comes in from and the grounds round
// the house (outdoor areas). A cell is open when it's inside an allowed area and no collider in
// the crawl's height band (it climbs over sofas and tables, not cabinets and walls) comes within
// its body radius. The side rooms need no rule of their own: their doorways are too narrow for
// it. A* over 8 neighbours, with a per-cell extra cost (`cost`: where it got jammed is made
// expensive for a while, so the next plan goes another way).
// flood() keeps only the cells connected to where it is (reach): every path, the nearest-cell
// lookups and the random prowl spots stay inside that, so it never plans for a pocket it can't
// get to (a player out of reach gets a path to the nearest place it can go).

export const MAIN_SPACES = ['great_room', 'entry', 'gallery_s', 'gallery_n', 'gallery_w', 'gallery_e',
  'courtyard', 'kitchen', 'dining'];
export const DOUBLE_HEIGHT = ['great_room', 'entry', 'courtyard'];

const NB = [[1, 0, 1], [-1, 0, 1], [0, 1, 1], [0, -1, 1], [1, 1, 1.414], [1, -1, 1.414], [-1, 1, 1.414], [-1, -1, 1.414]];

export class NavGrid {
  // boxes: THREE.Box3 colliders (shell + props); areas: [[x0, z0, x1, z1], ...] where it may be
  constructor(boxes, areas, { cell = 0.4, radius = 0.85, band = [1.3, 2.9], bounds } = {}) {
    this.cell = cell;
    this.radius = radius;
    this.band = band;
    const b = bounds ?? areas.reduce((a, r) => [Math.min(a[0], r[0]), Math.min(a[1], r[1]), Math.max(a[2], r[2]), Math.max(a[3], r[3])],
      [Infinity, Infinity, -Infinity, -Infinity]);
    this.x0 = b[0]; this.z0 = b[1];
    this.w = Math.ceil((b[2] - b[0]) / cell); this.h = Math.ceil((b[3] - b[1]) / cell);
    const n = this.w * this.h;
    this.open = new Uint8Array(n);
    for (const r of areas) {
      const i0 = Math.max(0, Math.ceil((r[0] - this.x0) / cell - 0.5)), i1 = Math.min(this.w - 1, Math.floor((r[2] - this.x0) / cell - 0.5));
      const j0 = Math.max(0, Math.ceil((r[1] - this.z0) / cell - 0.5)), j1 = Math.min(this.h - 1, Math.floor((r[3] - this.z0) / cell - 0.5));
      for (let j = j0; j <= j1; j++) this.open.fill(1, j * this.w + i0, j * this.w + i1 + 1);
    }
    this.blocked = new Uint8Array(n);
    this.cost = new Uint8Array(n);
    // A* scratch, reused between plans (a generation stamp marks what this plan has touched)
    this._g = new Float32Array(n); this._came = new Int32Array(n); this._stamp = new Uint32Array(n); this._closed = new Uint32Array(n); this._gen = 0;
    this.addBoxes(boxes);
  }

  // what stops it: anything reaching above band[0] (walls, cabinets, tall plants) that starts
  // below band[1] (lintels over the openings are higher); low furniture it crawls over
  addBoxes(boxes) {
    const [lo, hi] = this.band, r = this.radius;
    for (const c of boxes) {
      if (c.isEmpty?.() || c.max.y < lo || c.min.y > hi) continue;
      this.mark(c.min.x - r, c.min.z - r, c.max.x + r, c.max.z + r, 1);
    }
  }

  mark(x0, z0, x1, z1, v) {
    const i0 = Math.max(0, Math.floor((x0 - this.x0) / this.cell)), i1 = Math.min(this.w - 1, Math.floor((x1 - this.x0) / this.cell));
    const j0 = Math.max(0, Math.floor((z0 - this.z0) / this.cell)), j1 = Math.min(this.h - 1, Math.floor((z1 - this.z0) / this.cell));
    for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) this.blocked[j * this.w + i] = v;
  }

  // a hole it made (the smashed glass): open whatever its colliders blocked there
  clear(x0, z0, x1, z1) { this.mark(x0, z0, x1, z1, 0); }

  idx(x, z) {
    const i = Math.floor((x - this.x0) / this.cell), j = Math.floor((z - this.z0) / this.cell);
    return i < 0 || j < 0 || i >= this.w || j >= this.h ? -1 : j * this.w + i;
  }
  walkable(k) { return k >= 0 && this.open[k] && !this.blocked[k] && (!this.reach || this.reach[k] === 1); }

  // the cells connected to (x, z) (8-neighbour, no corner cutting): `reach`, and a list of them
  flood(x, z) {
    this.reach = null;
    const s = this.nearest(x, z);
    if (s < 0) return 0;
    const W = this.w, reach = new Uint8Array(this.open.length), list = [s];
    reach[s] = 1;
    for (let n = 0; n < list.length; n++) {
      const k = list[n], i = k % W, j = Math.floor(k / W);
      for (const [di, dj] of NB) {
        const ii = i + di, jj = j + dj;
        if (ii < 0 || jj < 0 || ii >= W || jj >= this.h) continue;
        const kk = jj * W + ii;
        if (reach[kk] || !this.walkable(kk)) continue;
        if (di && dj && (!this.walkable(j * W + ii) || !this.walkable(jj * W + i))) continue;
        reach[kk] = 1; list.push(kk);
      }
    }
    this.reach = reach;
    this.reachList = list;
    return list.length;
  }
  // metres from each reachable cell to the nearest cell it can't stand on (8-neighbour steps):
  // where there's room for it to turn round
  // (a two-pass chamfer distance transform: linear in the grid's size, which outdoors is big)
  clearance() {
    const W = this.w, H = this.h, n = this.open.length, d = new Float32Array(n), c1 = this.cell, c2 = this.cell * Math.SQRT2;
    for (let k = 0; k < n; k++) d[k] = this.walkable(k) ? Infinity : 0;
    for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
      const k = j * W + i;
      let v = d[k];
      if (!v) continue;
      if (i > 0) v = Math.min(v, d[k - 1] + c1);
      if (j > 0) {
        v = Math.min(v, d[k - W] + c1);
        if (i > 0) v = Math.min(v, d[k - W - 1] + c2);
        if (i < W - 1) v = Math.min(v, d[k - W + 1] + c2);
      }
      d[k] = v;
    }
    for (let j = H - 1; j >= 0; j--) for (let i = W - 1; i >= 0; i--) {
      const k = j * W + i;
      let v = d[k];
      if (!v) continue;
      if (i < W - 1) v = Math.min(v, d[k + 1] + c1);
      if (j < H - 1) {
        v = Math.min(v, d[k + W] + c1);
        if (i < W - 1) v = Math.min(v, d[k + W + 1] + c2);
        if (i > 0) v = Math.min(v, d[k + W - 1] + c2);
      }
      d[k] = v;
    }
    this.clear = d;
    // routes keep to the middle of narrow ways and wide of corners (its long body cuts inside
    // the head's track round a corner): extra cost close to the edge of where it can go
    const base = this.base = new Uint8Array(n);
    for (let k = 0; k < n; k++) { const v = d[k]; base[k] = v < 0.25 ? 3 : v < 0.45 ? 2 : v < 0.7 ? 1 : 0; }
    return d;
  }

  // breadth-first from (x, z) over walkable cells to the first one `accept`s (within maxCells)
  search(x, z, accept, maxCells = 6000) {
    const s = this.nearest(x, z);
    if (s < 0) return -1;
    const W = this.w, seen = new Set([s]), list = [s];
    for (let h = 0; h < list.length && h < maxCells; h++) {
      const k = list[h];
      if (accept(k)) return k;
      const i = k % W, j = Math.floor(k / W);
      for (const [di, dj] of NB) {
        const ii = i + di, jj = j + dj;
        if (ii < 0 || jj < 0 || ii >= W || jj >= this.h) continue;
        const kk = jj * W + ii;
        if (seen.has(kk) || !this.walkable(kk)) continue;
        seen.add(kk); list.push(kk);
      }
    }
    return -1;
  }

  centre(k) { return new THREE.Vector2(this.x0 + ((k % this.w) + 0.5) * this.cell, this.z0 + (Math.floor(k / this.w) + 0.5) * this.cell); }

  // the walkable cell nearest to (x, z), searching outward up to maxR metres; with `prefer`
  // (cell centre x, z -> bool) the nearest one it accepts, if there is one within maxR
  nearest(x, z, maxR = 12, prefer = null) {
    if (prefer) {
      const k = this._nearest(x, z, maxR, prefer);
      if (k >= 0) return k;
    }
    return this._nearest(x, z, maxR, null);
  }

  _nearest(x, z, maxR, prefer) {
    const ok = (kk) => this.walkable(kk) && (!prefer || prefer(this.x0 + ((kk % this.w) + 0.5) * this.cell, this.z0 + (Math.floor(kk / this.w) + 0.5) * this.cell));
    const k = this.idx(x, z);
    if (ok(k)) return k;
    const ci = Math.floor((x - this.x0) / this.cell), cj = Math.floor((z - this.z0) / this.cell);
    const R = Math.ceil(maxR / this.cell);
    let best = -1, bd = Infinity;
    for (let r = 1; r <= R && best < 0; r++) {
      for (let dj = -r; dj <= r; dj++) for (let di = -r; di <= r; di++) {
        if (Math.max(Math.abs(di), Math.abs(dj)) !== r) continue;
        const i = ci + di, j = cj + dj;
        if (i < 0 || j < 0 || i >= this.w || j >= this.h) continue;
        const kk = j * this.w + i;
        const d = di * di + dj * dj;
        if (d >= bd || !ok(kk)) continue;
        bd = d; best = kk;
      }
    }
    return best;
  }

  // A* from (x, z) to the walkable cell nearest the goal (or to cell `goalK`); a list of Vector2
  // waypoints, smoothed. `prefer` picks the start cell (e.g. one in the room it's in, not the
  // nearest across a wall). this.lastLen: the route's length in metres.
  path(from, to, prefer = null, goalK = -1) {
    const s = this.nearest(from.x, from.y, 12, prefer), g = goalK >= 0 && this.walkable(goalK) ? goalK : this.nearest(to.x, to.y, 40);
    this.lastLen = 0;
    if (s < 0 || g < 0) return null;
    if (s === g) return [this.centre(g)];
    const W = this.w, cost = this.cost, base = this.base ?? cost;
    const gScore = this._g, came = this._came, stamp = this._stamp, closed = this._closed;
    const gen = ++this._gen;
    const gx = g % W, gy = Math.floor(g / W);
    const hcost = (k) => { const dx = Math.abs((k % W) - gx), dy = Math.abs(Math.floor(k / W) - gy); return Math.max(dx, dy) + 0.414 * Math.min(dx, dy); };
    const heap = new MinHeap();
    gScore[s] = 0; came[s] = -1; stamp[s] = gen; heap.push(s, hcost(s));
    let found = false, iter = 0;
    const maxIter = Math.min(400000, W * this.h);
    while (heap.size && iter++ < maxIter) {
      const k = heap.pop();
      if (k === g) { found = true; break; }
      if (closed[k] === gen) continue;
      closed[k] = gen;
      const i = k % W, j = Math.floor(k / W);
      for (const [di, dj, c] of NB) {
        const ii = i + di, jj = j + dj;
        if (ii < 0 || jj < 0 || ii >= W || jj >= this.h) continue;
        const kk = jj * W + ii;
        if (!this.walkable(kk) || closed[kk] === gen) continue;
        if (di && dj && (!this.walkable(j * W + ii) || !this.walkable(jj * W + i))) continue;   // no corner cutting
        const ng = gScore[k] + c * (1 + cost[kk] + (base === cost ? 0 : base[kk]));
        if (stamp[kk] !== gen || ng < gScore[kk]) { stamp[kk] = gen; gScore[kk] = ng; came[kk] = k; heap.push(kk, ng + hcost(kk)); }
      }
    }
    if (!found) return null;
    const cells = [];
    for (let k = g; k !== -1; k = came[k]) cells.push(k);
    cells.reverse();
    // string-pull: keep a waypoint only where the straight line to the next kept one leaves open
    // (and not jam-costed) cells
    const pts = cells.map((k) => this.centre(k));
    const out = [pts[0]];
    let a = 0;
    for (let b = 2; b < pts.length; b++) if (!this.clearLine(pts[a], pts[b], true)) { out.push(pts[b - 1]); a = b - 1; }
    out.push(pts[pts.length - 1]);
    for (let i = 1; i < out.length; i++) this.lastLen += out[i].distanceTo(out[i - 1]);
    return out;
  }

  // jammed here: cells within r m cost `v` extra (0 clears them)
  markCost(x, z, r, v) {
    const R = Math.ceil(r / this.cell), ci = Math.floor((x - this.x0) / this.cell), cj = Math.floor((z - this.z0) / this.cell);
    for (let dj = -R; dj <= R; dj++) for (let di = -R; di <= R; di++) {
      const i = ci + di, j = cj + dj;
      if (i < 0 || j < 0 || i >= this.w || j >= this.h || di * di + dj * dj > R * R) continue;
      const k = j * this.w + i;
      this.cost[k] = v ? Math.max(this.cost[k], v) : 0;
    }
  }

  // from (x, z) along (dx, dz) over walkable cells, at most `max` m: where it has to stop
  march(x, z, dx, dz, max) {
    const L = Math.hypot(dx, dz) || 1, ux = dx / L, uz = dz / L, st = this.cell * 0.5;
    let d = 0;
    while (d + st <= max && this.walkable(this.idx(x + ux * (d + st), z + uz * (d + st)))) d += st;
    return new THREE.Vector2(x + ux * d, z + uz * d);
  }

  // (cheap: nor through jammed cells, nor closer to the edge than its two ends are)
  clearLine(a, b, cheap = false) {
    const d = a.distanceTo(b), steps = Math.ceil(d / (this.cell * 0.5)), B = this.base;
    const lim = cheap && B ? Math.max(B[this.idx(a.x, a.y)] ?? 0, B[this.idx(b.x, b.y)] ?? 0) : 9;
    for (let s = 1; s < steps; s++) {
      const t = s / steps, k = this.idx(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t);
      if (!this.walkable(k) || (cheap && (this.cost[k] || (B && B[k] > lim)))) return false;
    }
    return true;
  }
}

class MinHeap {
  constructor() { this.k = []; this.p = []; }
  get size() { return this.k.length; }
  push(k, p) {
    const K = this.k, P = this.p;
    K.push(k); P.push(p);
    let i = K.length - 1;
    while (i > 0) {
      const u = (i - 1) >> 1;
      if (P[u] <= P[i]) break;
      [K[u], K[i]] = [K[i], K[u]]; [P[u], P[i]] = [P[i], P[u]]; i = u;
    }
  }
  pop() {
    const K = this.k, P = this.p, top = K[0], lk = K.pop(), lp = P.pop();
    if (K.length) {
      K[0] = lk; P[0] = lp;
      let i = 0;
      for (;;) {
        const l = 2 * i + 1, r = l + 1;
        let m = i;
        if (l < K.length && P[l] < P[m]) m = l;
        if (r < K.length && P[r] < P[m]) m = r;
        if (m === i) break;
        [K[m], K[i]] = [K[i], K[m]]; [P[m], P[i]] = [P[i], P[m]]; i = m;
      }
    }
    return top;
  }
}
