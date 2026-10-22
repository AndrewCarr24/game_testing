// Synthetic wilderness data: heightfield, splat masks, baked light, scattered trees and
// undergrowth. Stand-in for the real terrain generator's output; the runtime only depends on
// the World shape below, so swapping in real data means filling the same fields from files:
//
//   size          world extent in metres (square, centred on the origin)
//   res           height samples per side (vertex-aligned: x = -size/2 + i * spacing)
//   heights       Float32Array(res * res), metres, row-major (i along +x, j along +z)
//   mapRes        texels per side of the splat / light maps (texel centres, cover `size`)
//   splat         Uint8Array(mapRes² * 4): r grass, g forest floor, b rock; 1-r-g-b = scree/path;
//                 a = macro colour variation
//   light         Uint8Array(mapRes² * 4): r sun on the ground (n.l x terrain shadow), g canopy
//                 shadow (1 = no tree shadow), b sky visibility, a terrain shadow alone
//   species       {name: Float32Array(n * 6)}: x, y, z, scale, rotY, seed per instance
//   views         {name: {pos: [x,y,z], look: [x,y,z]}} named benchmark views
//
// Everything is deterministic for a given seed. Times are logged into world.timings.

import { makeNoise, rng, smoothstep, clamp01 } from './noise.js';

export const SUN = [-0.9398, 0.3199, 0.12];       // toward the sun (viewer/sky.js, the golden look)

export const SPECIES_INFO = {
  // crown centre height / radius (m, at scale 1), trunk radius for colliders
  broadleaf: { crownH: 9, crownR: 4.2, trunkR: 0.28 },
  conifer: { crownH: 8, crownR: 2.6, trunkR: 0.25 },
  pine: { crownH: 15, crownR: 3.2, trunkR: 0.22 },
  fern: { crownH: 0.5, crownR: 0.6, trunkR: 0 },
  tuft: { crownH: 0.3, crownR: 0.4, trunkR: 0 },
};

export function generateWorld({ size = 2048, res = 2049, mapRes = 1024, seed = 7, trees = 40000, bushes = 120000 } = {}) {
  const T = {};
  let t0 = performance.now();
  const tick = (k) => { const t = performance.now(); T[k] = +(t - t0).toFixed(0); t0 = t; };
  const N = makeNoise(seed), N2 = makeNoise(seed * 31 + 5);
  const half = size / 2, spacing = size / (res - 1);

  // ---- heights: large forms on a coarse grid, upsampled, plus fine detail per sample
  const river = (x) => 250 * Math.sin(x / 420) + 90 * Math.sin(x / 170 + 1.0) - 120;
  const trail = (z) => 120 * Math.sin(z / 300) + 40 * Math.sin(z / 97) + 60;
  const C = 4, cres = Math.floor(size / C) + 1;
  const coarse = new Float32Array(cres * cres);
  for (let j = 0; j < cres; j++) for (let i = 0; i < cres; i++) {
    const x = -half + i * C, z = -half + j * C;
    const wx = x + 120 * N.fbm(x / 700, z / 700, 2), wz = z + 120 * N.fbm(x / 700 + 9, z / 700 - 4, 2);
    const mountains = smoothstep(-0.25, 0.35, N2.fbm(wx / 1400, wz / 1400, 2) + (-z / size) * 0.9);
    let h = 45 * N.fbm(wx / 900, wz / 900, 4) + 170 * Math.pow(N.ridged(wx / 650, wz / 650, 5), 1.7) * mountains;
    const d = Math.abs(z - river(x));
    const floor = 8 + 6 * N.fbm(x / 300, 3, 2);
    h = floor + (h - floor) * smoothstep(15, 260, d) - 3.5 * (1 - smoothstep(4, 14, d));
    const e = Math.max(Math.abs(x), Math.abs(z)) / half;   // the rim: a bowl of hills at the world edge
    h += 140 * smoothstep(0.8, 1.0, e) * (0.7 + 0.3 * N.fbm(x / 200, z / 200, 2));
    coarse[i + j * cres] = h;
  }
  tick('coarse');
  const heights = new Float32Array(res * res);
  for (let j = 0; j < res; j++) {
    const z = -half + j * spacing, cj = Math.min(cres - 2, Math.floor((z + half) / C)), fz = (z + half) / C - cj;
    for (let i = 0; i < res; i++) {
      const x = -half + i * spacing, ci = Math.min(cres - 2, Math.floor((x + half) / C)), fx = (x + half) / C - ci;
      const k = ci + cj * cres;
      const h0 = coarse[k] + (coarse[k + 1] - coarse[k]) * fx, h1 = coarse[k + cres] + (coarse[k + cres + 1] - coarse[k + cres]) * fx;
      const td = Math.abs(x - trail(z));
      heights[i + j * res] = h0 + (h1 - h0) * fz + 1.6 * N2.fbm(x / 35, z / 35, 3) + 0.3 * N2.perlin(x / 7, z / 7)
        - 0.25 * (1 - smoothstep(1.0, 2.5, td));
    }
  }
  tick('heights');

  const heightAt = (x, z) => {
    let fx = (x + half) / spacing, fz = (z + half) / spacing;
    fx = Math.min(res - 1.001, Math.max(0, fx)); fz = Math.min(res - 1.001, Math.max(0, fz));
    const i = Math.floor(fx), j = Math.floor(fz), u = fx - i, v = fz - j, k = i + j * res;
    const a = heights[k] + (heights[k + 1] - heights[k]) * u, b = heights[k + res] + (heights[k + res + 1] - heights[k + res]) * u;
    return a + (b - a) * v;
  };
  const normalAt = (x, z, e = 1) => {
    const dx = heightAt(x + e, z) - heightAt(x - e, z), dz = heightAt(x, z + e) - heightAt(x, z - e);
    const l = Math.hypot(dx, 2 * e, dz);
    return [-dx / l, (2 * e) / l, -dz / l];
  };

  // ---- masks on the map grid (2 m texels)
  const M = mapRes, ts = size / M;
  const forest = new Float32Array(M * M), slopeA = new Float32Array(M * M), hm = new Float32Array(M * M);
  for (let j = 0; j < M; j++) for (let i = 0; i < M; i++) {
    const x = -half + (i + 0.5) * ts, z = -half + (j + 0.5) * ts, k = i + j * M;
    const n = normalAt(x, z, ts);
    const slope = Math.sqrt(1 - n[1] * n[1]) / n[1];            // tan of the slope angle
    slopeA[k] = slope; hm[k] = heightAt(x, z);
    const e = Math.max(Math.abs(x), Math.abs(z)) / half;
    const nf = N.fbm(x / 350 + 50, z / 350, 4) + 0.3 * N.fbm(x / 80, z / 80 + 20, 2);
    const td = Math.abs(x - trail(z)), rd = Math.abs(z - river(x));
    forest[k] = smoothstep(-0.12, 0.18, nf) * (1 - smoothstep(0.7, 1.1, slope)) * (1 - smoothstep(0.93, 0.99, e))
      * smoothstep(3, 9, td) * smoothstep(10, 30, rd) * (1 - smoothstep(190, 260, hm[k]));
  }
  tick('masks');

  const splat = new Uint8Array(M * M * 4);
  for (let j = 0; j < M; j++) for (let i = 0; i < M; i++) {
    const x = -half + (i + 0.5) * ts, z = -half + (j + 0.5) * ts, k = i + j * M;
    const s = slopeA[k];
    let rock = smoothstep(0.6, 0.95, s + 0.15 * N2.fbm(x / 40, z / 40, 2)) + 0.6 * smoothstep(200, 260, hm[k]);
    const td = Math.abs(x - trail(z)), rd = Math.abs(z - river(x));
    let path = Math.max(1 - smoothstep(1.2, 2.6, td + 0.6 * N2.perlin(x / 3, z / 3)), 1 - smoothstep(5, 9, rd));
    let floor = smoothstep(0.15, 0.6, forest[k] + 0.2 * N2.fbm(x / 25, z / 25, 2));
    rock = clamp01(rock); path = clamp01(path) * (1 - rock);
    floor = floor * (1 - rock) * (1 - path);
    const grass = clamp01(1 - rock - path - floor);
    splat[k * 4] = grass * 255; splat[k * 4 + 1] = floor * 255; splat[k * 4 + 2] = rock * 255;
    splat[k * 4 + 3] = 128 + 127 * N.fbm(x / 60, z / 60, 3);
  }
  tick('splat');

  // ---- scatter trees: jittered 4 m grid, accepted by forest density scaled to the target count
  const r = rng(seed + 101);
  const maskAt = (x, z) => {
    const i = Math.min(M - 1, Math.max(0, Math.floor((x + half) / ts))), j = Math.min(M - 1, Math.max(0, Math.floor((z + half) / ts)));
    return i + j * M;
  };
  const S = 4, g = Math.floor(size / S);
  let sum = 0;
  for (let j = 0; j < g; j++) for (let i = 0; i < g; i++) sum += forest[maskAt(-half + (i + 0.5) * S, -half + (j + 0.5) * S)];
  const k = Math.min(1, trees / Math.max(1, sum));
  const lists = { broadleaf: [], conifer: [], pine: [], fern: [], tuft: [] };
  for (let j = 0; j < g; j++) for (let i = 0; i < g; i++) {
    const x = -half + (i + r()) * S, z = -half + (j + r()) * S;
    const f = forest[maskAt(x, z)];
    if (r() >= f * k) continue;
    const h = heightAt(x, z);
    const alt = h + 25 * N2.fbm(x / 150, z / 150, 2);
    const v = N.fbm(x / 200 - 30, z / 200, 2);
    const sp = alt > 95 + 30 * v ? (v > 0.15 ? 'pine' : 'conifer') : v > 0.18 ? 'conifer' : v < -0.25 ? 'pine' : 'broadleaf';
    lists[sp].push(x, h - 0.15, z, 0.75 + 0.55 * r() * r() + 0.15 * r(), r() * Math.PI * 2, r());
  }
  // undergrowth: ferns in the forest, grass tufts in the open
  const B = 2.5, gb = Math.floor(size / B);
  const pb = bushes / (gb * gb * 0.55);
  for (let j = 0; j < gb; j++) for (let i = 0; i < gb; i++) {
    const x = -half + (i + r()) * B, z = -half + (j + r()) * B;
    const mk = maskAt(x, z), f = forest[mk];
    if (splat[mk * 4 + 2] > 120 || splat[mk * 4 + 2] + splat[mk * 4] + splat[mk * 4 + 1] < 140) continue;   // not on rock or the path
    const fern = f > 0.35;
    if (r() >= pb * (fern ? 1.2 : 0.6)) continue;
    lists[fern ? 'fern' : 'tuft'].push(x, heightAt(x, z) - 0.05, z, 0.7 + 0.6 * r(), r() * Math.PI * 2, r());
  }
  const species = Object.fromEntries(Object.entries(lists).map(([n, a]) => [n, new Float32Array(a)]));
  tick('scatter');

  // ---- baked light (the wilderness analogue of the grounds' vertex bake): sun n.l, soft
  // terrain shadow marched toward the sun, sky visibility from local concavity, tree shadows
  const L = SUN, lh = Math.hypot(L[0], L[2]), lx = L[0] / lh, lz = L[2] / lh, tanE = L[1] / lh;
  const blur = (src, rad) => {          // separable box blur on the map grid
    const tmp = new Float32Array(M * M), out = new Float32Array(M * M), w = 2 * rad + 1;
    for (let j = 0; j < M; j++) { let s = 0; for (let i = -rad; i <= rad; i++) s += src[Math.min(M - 1, Math.max(0, i)) + j * M];
      for (let i = 0; i < M; i++) { tmp[i + j * M] = s / w; s += src[Math.min(M - 1, i + rad + 1) + j * M] - src[Math.max(0, i - rad) + j * M]; } }
    for (let i = 0; i < M; i++) { let s = 0; for (let j = -rad; j <= rad; j++) s += tmp[i + Math.min(M - 1, Math.max(0, j)) * M];
      for (let j = 0; j < M; j++) { out[i + j * M] = s / w; s += tmp[i + Math.min(M - 1, j + rad + 1) * M] - tmp[i + Math.max(0, j - rad) * M]; } }
    return out;
  };
  const b4 = blur(hm, 4), b16 = blur(hm, 16);
  const steps = []; for (let t = 3; t < 1000; t *= 1.13) steps.push(t);
  const sunG = new Float32Array(M * M), shadow = new Float32Array(M * M), sky = new Float32Array(M * M);
  for (let j = 0; j < M; j++) for (let i = 0; i < M; i++) {
    const x = -half + (i + 0.5) * ts, z = -half + (j + 0.5) * ts, kk = i + j * M;
    const n = normalAt(x, z, ts);
    const ndl = Math.max(0, n[0] * L[0] + n[1] * L[1] + n[2] * L[2]);
    const h0 = hm[kk] + 0.3;
    let s = 1;
    if (ndl > 0) for (const t of steps) {
      const hs = heightAt(x + lx * t, z + lz * t), ray = h0 + t * tanE;
      s = Math.min(s, clamp01((ray - hs) / (0.04 * t) + 0.5));   // penumbra widens with distance
      if (s <= 0 || ray > 420) break;
    }
    shadow[kk] = s; sunG[kk] = ndl * s;
    sky[kk] = clamp01(0.5 + 0.5 * n[1]) * clamp01(1 - 0.06 * (b4[kk] - hm[kk]) - 0.012 * (b16[kk] - hm[kk]));
  }
  tick('light');
  const canopy = new Float32Array(M * M).fill(1);
  const stamp = (cx, cz, ax, az, ra, rb, amount, target) => {   // soft ellipse, major axis (ax, az)
    const R = Math.max(ra, rb), i0 = Math.floor((cx - R + half) / ts), i1 = Math.ceil((cx + R + half) / ts);
    const j0 = Math.floor((cz - R + half) / ts), j1 = Math.ceil((cz + R + half) / ts);
    for (let j = Math.max(0, j0); j <= Math.min(M - 1, j1); j++) for (let i = Math.max(0, i0); i <= Math.min(M - 1, i1); i++) {
      const dx = -half + (i + 0.5) * ts - cx, dz = -half + (j + 0.5) * ts - cz;
      const u = (dx * ax + dz * az) / ra, v = (-dx * az + dz * ax) / rb, d = u * u + v * v;
      if (d < 1) target[i + j * M] *= 1 - amount * (1 - d) * (1 - d);
    }
  };
  for (const sp of ['broadleaf', 'conifer', 'pine']) {
    const a = species[sp], info = SPECIES_INFO[sp];
    for (let q = 0; q < a.length; q += 6) {
      const sc = a[q + 3], hc = info.crownH * sc, rc = info.crownR * sc, off = hc / tanE;
      stamp(a[q] - lx * off, a[q + 2] - lz * off, lx, lz, rc / Math.sin(Math.atan(tanE)) * 0.9, rc, 0.7, canopy);
      stamp(a[q], a[q + 2], 1, 0, rc * 1.6, rc * 1.6, 0.25, sky);
    }
  }
  const light = new Uint8Array(M * M * 4);
  for (let q = 0; q < M * M; q++) {
    light[q * 4] = sunG[q] * 255; light[q * 4 + 1] = Math.max(0.08, canopy[q]) * 255;
    light[q * 4 + 2] = sky[q] * 255; light[q * 4 + 3] = shadow[q] * 255;
  }
  tick('canopy');

  // ---- named views for the benchmark: open meadow, densest forest, highest ridge
  const inner = 0.62 * half;
  let open = null, dense = null, ridge = null;
  for (let z = -inner; z <= inner; z += 32) for (let x = -inner; x <= inner; x += 32) {
    let f = 0, sl = 0;
    for (let dz = -40; dz <= 40; dz += 20) for (let dx = -40; dx <= 40; dx += 20) { const mk = maskAt(x + dx, z + dz); f += forest[mk]; sl = Math.max(sl, slopeA[mk]); }
    const h = heightAt(x, z);
    if (sl < 0.25 && (!open || f < open.f || (f === open.f && h < open.h))) open = { x, z, f, h };
    if (sl < 0.35 && (!dense || f > dense.f)) dense = { x, z, f, h };
    if (sl < 0.6 && f < 1.5 && (!ridge || h > ridge.h)) ridge = { x, z, h };   // a bare crest (f: forest summed over 25 samples)
  }
  const eye = (x, z) => [x, heightAt(x, z) + 1.65, z];
  const toward = (p, tx, tz, dy = 0) => { const d = Math.hypot(tx - p[0], tz - p[2]) || 1; return [p[0] + (tx - p[0]) / d * 10, p[1] + dy, p[2] + (tz - p[2]) / d * 10]; };
  const views = {};
  { const p = eye(open.x, open.z); views.open = { pos: p, look: toward(p, ridge.x, ridge.z, 0.6) }; }
  { const p = eye(dense.x, dense.z); views.forest = { pos: p, look: toward(p, dense.x + 7, dense.z + 3, -0.2) }; }
  { // the ridge: look out along the most open azimuth (lowest horizon), slightly down
    const p = eye(ridge.x, ridge.z);
    let best = null;
    for (let a = 0; a < 24; a++) {
      const th = (a / 24) * Math.PI * 2, dx = Math.cos(th), dz = Math.sin(th);
      let m = -Infinity;
      for (let t = 30; t < 900; t *= 1.15) m = Math.max(m, (heightAt(p[0] + dx * t, p[2] + dz * t) - p[1]) / t);
      if (!best || m < best.m) best = { m, dx, dz };
    }
    views.ridge = { pos: p, look: [p[0] + best.dx * 10, p[1] - 0.9, p[2] + best.dz * 10] };
  }
  const spawnZ = half * 0.7, sx = trail(spawnZ);
  views.spawn = { pos: eye(sx, spawnZ), look: toward(eye(sx, spawnZ), trail(spawnZ - 30), spawnZ - 30) };
  tick('views');

  return { size, res, spacing, mapRes, heights, splat, light, species, views, heightAt, normalAt, timings: T, seed };
}
