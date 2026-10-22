// A generated wilderness world from files (blender/wilderness/levels/<level>_world.py writes
// build/wilderness/<name>/world/): the same World shape as world.js's synthetic one (its header
// is the contract), plus what a real level carries:
//
//   speciesInfo   {id: {kind, tier, height, width, trunk, tint_rgb, bloom, veg_ids, count}}; the
//                 instances (species[id]) are x, y, z, size, rotY, seed (size: x the nominal
//                 height / width, so a species can be drawn with any model)
//   thicket       Uint8Array(res²): 255 = laurel hell (solid), 128 = tunnel (crouch), 0 = open
//   water         Float32Array(res²): water surface height, NaN = dry
//   backdrop      {res, cell, extent, heights: Float32Array, color: Uint8Array RGB}
//   colliders     Float32Array(n * 6): AABBs (min xyz, max xyz) in world coords
//   props, estate, routes, spawn, look, haze, checks: world.json as written
//
// Frame: three.js, terrain centred on the origin (x east, y up, z south); the estate (house at
// estate (0, 0)) sits at z = -estate_offset[1] ... see world.json "frame".

import { fetchPNG } from './png.js';

export async function loadWorld(name, base = '../build/wilderness') {
  const T = {};
  let t0 = performance.now();
  const tick = (k) => { const t = performance.now(); T[k] = +(t - t0).toFixed(0); t0 = t; };
  const dir = `${base}/${name}/world/`;
  const meta = await (await fetch(dir + 'world.json')).json();
  tick('json');
  // the light map is GPU-only: shipped as WebP (lossy colour, lossless alpha) and decoded by the
  // browser without premultiplying; everything the CPU reads stays exact PNG (png.js)
  const lightFile = meta.light_file || 'light.png';
  const lightJob = lightFile.endsWith('.webp')
    ? fetch(dir + lightFile).then((r) => r.blob()).then((b) => createImageBitmap(b, { premultiplyAlpha: 'none', colorSpaceConversion: 'none' }))
    : fetchPNG(dir + lightFile);
  const [hp, sp, tp, wp, bh, bc, lp] = await Promise.all([...['height16.png', 'splat.png', 'thicket.png', 'water16.png',
    'backdrop16.png', 'backdrop.png'].map((f) => fetchPNG(dir + f)), lightJob]);
  tick('png');
  const { res, size, spacing, mapRes } = meta;
  const half = size / 2;
  const heights = new Float32Array(res * res);
  const hs = (meta.height.max - meta.height.min) / 65535;
  for (let k = 0; k < heights.length; k++) heights[k] = hp.data[k] * hs + meta.height.min;
  const water = new Float32Array(res * res);
  const ws = (meta.water.max - meta.water.min) / 65534;
  for (let k = 0; k < water.length; k++) water[k] = wp.data[k] ? (wp.data[k] - 1) * ws + meta.water.min : NaN;
  const bres = bh.width, bheights = new Float32Array(bres * bres), bs = (meta.backdrop.max - meta.backdrop.min) / 65535;
  for (let k = 0; k < bheights.length; k++) bheights[k] = bh.data[k] * bs + meta.backdrop.min;
  tick('decode');

  // instances: uint16 x 6 -> float x, y, z, size, rotY, seed (+ the bloom index in the seed's
  // integer part, from the species table); ground cover ("xz4"): x, z, size << 8 | rot, seed,
  // its y from the heightfield
  const species = {};
  const hmin = meta.height.min, hrange = meta.height.max - meta.height.min;
  const hAt = (x, z) => {
    let fx = (x + half) / spacing, fz = (z + half) / spacing;
    fx = Math.min(res - 1.001, Math.max(0, fx)); fz = Math.min(res - 1.001, Math.max(0, fz));
    const i = Math.floor(fx), j = Math.floor(fz), u = fx - i, v = fz - j, k = i + j * res;
    const a = heights[k] + (heights[k + 1] - heights[k]) * u, b = heights[k + res] + (heights[k + res + 1] - heights[k + res]) * u;
    return a + (b - a) * v;
  };
  await Promise.all(Object.entries(meta.species).map(async ([id, info]) => {
    if (!info.count) { species[id] = new Float32Array(0); return; }
    const buf = await (await fetch(dir + info.file)).arrayBuffer();
    const q = new Uint16Array(buf), xz4 = info.fmt === 'xz4', w = xz4 ? 4 : 6, n = q.length / w, a = new Float32Array(n * 6);
    // (instances outside the square, the ring's forest, carry their own bounds, three.js frame)
    const B = info.bounds, bx = B ? [B.x[0], B.x[1] - B.x[0]] : [-half, size], bz = B ? [B.z[0], B.z[1] - B.z[0]] : [-half, size];
    const bh = B ? [B.h[0], B.h[1] - B.h[0]] : [hmin, hrange];
    const bloom = info.bloom || 0;
    for (let i = 0; i < n; i++) {
      const o = i * w, d = i * 6;
      a[d] = (q[o] / 65535) * bx[1] + bx[0];
      a[d + 2] = (q[o + 1] / 65535) * bz[1] + bz[0];
      if (xz4) {
        a[d + 1] = hAt(a[d], a[d + 2]) - 0.05;
        a[d + 3] = (q[o + 2] >> 8) / 100;
        a[d + 4] = ((q[o + 2] & 255) / 256) * Math.PI * 2;
        a[d + 5] = q[o + 3] / 65535 * 0.999 + bloom;
      } else {
        a[d + 1] = (q[o + 2] / 65535) * bh[1] + bh[0];
        a[d + 3] = q[o + 3] / 10000;
        a[d + 4] = (q[o + 4] / 65535) * Math.PI * 2;
        a[d + 5] = q[o + 5] / 65535 * 0.999 + bloom;
      }
    }
    species[id] = a;
  }));
  // colliders: uint16 over their own range (colliders_q), else float32
  let colliders;
  if (meta.colliders_q) {
    const { file, lo, hi } = meta.colliders_q;
    const q = new Uint16Array(await (await fetch(dir + file)).arrayBuffer());
    colliders = new Float32Array(q.length);
    for (let k = 0; k < q.length; k++) { const c = k % 3; colliders[k] = lo[c] + (q[k] / 65535) * (hi[c] - lo[c]); }
  } else colliders = new Float32Array(await (await fetch(dir + 'colliders.bin')).arrayBuffer());
  tick('instances');

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
  const cellAt = (x, z) => {
    const i = Math.round((x + half) / spacing), j = Math.round((z + half) / spacing);
    return i < 0 || j < 0 || i >= res || j >= res ? -1 : i + j * res;
  };
  const waterAt = (x, z) => { const k = cellAt(x, z); return k < 0 ? NaN : water[k]; };
  // estate frame (house at the origin, y north) <-> world
  const [ex, ey] = meta.estate_offset;
  const fromEstate = (x, y, h) => [x, h, -(y - ey)];
  const views = meta.views;
  return {
    name, meta, size, res, spacing, mapRes, heights, splat: sp.data, light: lp.data || null, lightImage: lp.data ? null : lp, species, speciesInfo: meta.species,
    thicket: tp.data, water, waterAt, cellAt, colliders, props: meta.props, estate: meta.estate, routes: meta.routes,
    backdrop: { res: bres, ...meta.backdrop, heights: bheights, color: bc.data }, look: meta.look, haze: meta.haze,
    views, spawn: meta.spawn, heightAt, normalAt, fromEstate, timings: T, seed: 0,
  };
}
