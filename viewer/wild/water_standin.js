// The river's physics, derived from the level's own water raster (world.water: the surface height
// per heightfield vertex, NaN = dry) until the water-look workstream's viewer/wild/water.js lands.
// Same three functions as theirs, so it drops in (main.js: `window.__water || makeWaterStandin`):
//
//   surfaceAt(x, z)  water surface height (m), NaN where dry (bilinear; a dry corner takes the wet
//                    corners' mean, as buildWater does, so the depth has no 1.5 m cell steps)
//   depthAt(x, z)    surface - bed (>= 0; 0 where dry)
//   flowAt(x, z, out?) {x, z, speed}: the current, m/s (three.js frame)
//
// Direction: downstream along the channel. A local surface gradient is noise in the pools (their
// slope is 0-0.0015 and water16 quantises at ~3 mm), so a distance-to-outlet field over the wet
// cells (16-neighbour Dijkstra from where each water body leaves the square, or its lowest cell)
// gives "downstream" everywhere; its negative gradient is the direction.
// Speed: from the surface slope along that direction (a regression of level against downstream
// distance over the cells within 6 m, so a knick step reads as a rapid, not a single-cell spike):
// v = 10 sqrt(slope), at least 0.25, at most 7 m/s; slower in the shallows (bank friction:
// x sqrt(depth / 0.8), at least x0.35). Pools ~0.4 m/s, runs 1-1.7, the shoals 2-3, the Narrows
// ledge and cascade 4-7.
// Cost: ~20-40 ms once at load (the ~21k wet cells of Laurel Fork Cove), ~0.5 MB.

export function makeWaterStandin(world) {
  const { res, spacing, size, water, heights } = world, half = size / 2, n = res * res;
  // wet cells (the surface over the bed) -> compact index
  const id = new Int32Array(n).fill(-1), cells = [];
  for (let k = 0; k < n; k++) if (Number.isFinite(water[k])) { id[k] = cells.length; cells.push(k); }
  const m = cells.length;
  const lvl = new Float32Array(m), dist = new Float64Array(m).fill(Infinity);
  for (let c = 0; c < m; c++) lvl[c] = water[cells[c]];

  // seeds: per connected body, its cells on the square's edge within 1 m of the lowest edge level
  // (where it leaves), else its lowest cell
  const comp = new Int32Array(m).fill(-1), N8 = [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]];
  const seeds = [];
  for (let c0 = 0, nc = 0; c0 < m; c0++) {
    if (comp[c0] >= 0) continue;
    const stack = [c0], body = []; comp[c0] = nc;
    while (stack.length) {
      const c = stack.pop(); body.push(c);
      const k = cells[c], i = k % res, j = (k / res) | 0;
      for (const [di, dj] of N8) {
        const a = i + di, b = j + dj;
        if (a < 0 || b < 0 || a >= res || b >= res) continue;
        const cc = id[a + b * res];
        if (cc >= 0 && comp[cc] < 0) { comp[cc] = nc; stack.push(cc); }
      }
    }
    const edge = body.filter((c) => { const k = cells[c], i = k % res, j = (k / res) | 0; return i === 0 || j === 0 || i === res - 1 || j === res - 1; });
    if (edge.length) { const lo = Math.min(...edge.map((c) => lvl[c])); for (const c of edge) if (lvl[c] < lo + 1) seeds.push(c); }
    else { let lo = body[0]; for (const c of body) if (lvl[c] < lvl[lo]) lo = c; seeds.push(lo); }
    nc++;
  }
  // Dijkstra (binary heap) over the wet cells; 16 neighbours (the knight's moves too): an 8-way
  // chamfer bends "downstream" to 45-degree steps, this is within ~1.5% of straight
  const N16 = [...N8, [2, 1], [1, 2], [-1, 2], [-2, 1], [-2, -1], [-1, -2], [1, -2], [2, -1]];
  const heap = [], push = (d, c) => { heap.push([d, c]); let i = heap.length - 1;
    while (i > 0) { const p = (i - 1) >> 1; if (heap[p][0] <= heap[i][0]) break; [heap[p], heap[i]] = [heap[i], heap[p]]; i = p; } };
  const pop = () => { const top = heap[0], last = heap.pop();
    if (heap.length) { heap[0] = last; let i = 0; for (;;) { const l = 2 * i + 1, r = l + 1; let s = i;
      if (l < heap.length && heap[l][0] < heap[s][0]) s = l; if (r < heap.length && heap[r][0] < heap[s][0]) s = r;
      if (s === i) break; [heap[s], heap[i]] = [heap[i], heap[s]]; i = s; } }
    return top; };
  for (const c of seeds) { dist[c] = 0; push(0, c); }
  while (heap.length) {
    const [d, c] = pop();
    if (d > dist[c]) continue;
    const k = cells[c], i = k % res, j = (k / res) | 0;
    for (const [di, dj] of N16) {
      const a = i + di, b = j + dj;
      if (a < 0 || b < 0 || a >= res || b >= res) continue;
      const cc = id[a + b * res];
      if (cc < 0) continue;
      const nd = d + spacing * Math.hypot(di, dj);
      if (nd < dist[cc]) { dist[cc] = nd; push(nd, cc); }
    }
  }

  // per cell: direction (-grad dist, central differences over wet neighbours) and speed
  const fx = new Float32Array(m), fz = new Float32Array(m), sp = new Float32Array(m);
  const R = 4, K = 10;   // cells: the 6 m regression window; v = K sqrt(slope)
  for (let c = 0; c < m; c++) {
    const k = cells[c], i = k % res, j = (k / res) | 0;
    const D = (a, b) => { if (a < 0 || b < 0 || a >= res || b >= res) return NaN; const cc = id[a + b * res]; return cc < 0 ? NaN : dist[cc]; };
    const d0 = dist[c];
    const xp = D(i + 1, j), xm = D(i - 1, j), zp = D(i, j + 1), zm = D(i, j - 1);
    const gx = Number.isFinite(xp) && Number.isFinite(xm) ? (xp - xm) / 2 : Number.isFinite(xp) ? xp - d0 : Number.isFinite(xm) ? d0 - xm : 0;
    const gz = Number.isFinite(zp) && Number.isFinite(zm) ? (zp - zm) / 2 : Number.isFinite(zp) ? zp - d0 : Number.isFinite(zm) ? d0 - zm : 0;
    const L = Math.hypot(gx, gz) || 1;
    fx[c] = -gx / L; fz[c] = -gz / L;
    // slope: level against downstream distance, the cells within R
    let s0 = 0, sd = 0, sl = 0, sdd = 0, sdl = 0;
    for (let b = j - R; b <= j + R; b++) for (let a = i - R; a <= i + R; a++) {
      if (a < 0 || b < 0 || a >= res || b >= res || (a - i) ** 2 + (b - j) ** 2 > R * R) continue;
      const cc = id[a + b * res];
      if (cc < 0 || !Number.isFinite(dist[cc])) continue;
      const x = dist[cc], y = lvl[cc];
      s0++; sd += x; sl += y; sdd += x * x; sdl += x * y;
    }
    const v = s0 > 2 ? sdd - (sd * sd) / s0 : 0;
    const slope = v > 1e-3 ? Math.max(0, (sdl - (sd * sl) / s0) / v) : 0;   // level rises with distance upstream
    const depth = Math.max(0, lvl[c] - heights[k]);
    sp[c] = Math.min(7, Math.max(0.25, K * Math.sqrt(slope))) * Math.max(0.35, Math.min(1, Math.sqrt(depth / 0.8)));
  }
  // smoothed over 4.5 m: the distance field's 8-way chamfer directions (22.5 degree steps) and the
  // per-cell slope noise
  const sx = new Float32Array(m), sz = new Float32Array(m), ss = new Float32Array(m), R2 = 3;
  for (let c = 0; c < m; c++) {
    const k = cells[c], i = k % res, j = (k / res) | 0;
    let ax = 0, az = 0, as = 0, nw = 0;
    for (let b = j - R2; b <= j + R2; b++) for (let a = i - R2; a <= i + R2; a++) {
      if (a < 0 || b < 0 || a >= res || b >= res || (a - i) ** 2 + (b - j) ** 2 > R2 * R2) continue;
      const cc = id[a + b * res];
      if (cc < 0) continue;
      ax += fx[cc]; az += fz[cc]; as += sp[cc]; nw++;
    }
    const L = Math.hypot(ax, az) || 1;
    sx[c] = ax / L; sz[c] = az / L;
    ss[c] = Math.min(sp[c] * 1.5, as / nw);           // (a shallow margin stays slower than the channel)
  }
  fx.set(sx); fz.set(sz); sp.set(ss);

  // bilinear lookups over the vertex grid (dry corners take the wet corners' mean)
  const corners = (x, z) => {
    let gx = (x + half) / spacing, gz = (z + half) / spacing;
    gx = Math.min(res - 1.001, Math.max(0, gx)); gz = Math.min(res - 1.001, Math.max(0, gz));
    const i = Math.floor(gx), j = Math.floor(gz), u = gx - i, v = gz - j, k = i + j * res;
    return [[k, (1 - u) * (1 - v)], [k + 1, u * (1 - v)], [k + res, (1 - u) * v], [k + res + 1, u * v]];
  };
  const surfaceAt = (x, z) => {
    const C = corners(x, z);
    let wsum = 0, lsum = 0, mean = 0, nw = 0;
    for (const [k] of C) if (Number.isFinite(water[k])) { mean += water[k]; nw++; }
    if (!nw) return NaN;
    mean /= nw;
    for (const [k, w] of C) { lsum += (Number.isFinite(water[k]) ? water[k] : mean) * w; wsum += w; }
    return lsum / wsum;
  };
  const depthAt = (x, z) => { const s = surfaceAt(x, z); return Number.isFinite(s) ? Math.max(0, s - world.heightAt(x, z)) : 0; };
  const flowAt = (x, z, out = { x: 0, z: 0, speed: 0 }) => {
    let vx = 0, vz = 0, ws = 0;
    for (const [k, w] of corners(x, z)) { const c = id[k]; if (c < 0 || w <= 0) continue; vx += fx[c] * sp[c] * w; vz += fz[c] * sp[c] * w; ws += w; }
    if (ws > 0) { vx /= ws; vz /= ws; }
    out.x = vx; out.z = vz; out.speed = Math.hypot(vx, vz);
    return out;
  };
  return { surfaceAt, depthAt, flowAt, standin: true, stats: { wetCells: m, seeds: seeds.length } };
}
