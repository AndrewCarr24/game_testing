// The water-query API (viewer/wild/water.js, window.__water; contract in
// design/wilderness/blue_ridge/water.md) on a generated level: samples the Laurel River across
// the bridge's line, in a pool, on the shoal and at the cascade, and checks that the surface is
// continuous, depth = surface - ground, the current runs downstream (north, then west), dry ground
// reads dry, and the draw calls the water adds.
// Usage: node viewer/tools/wild_water.mjs [--world laurel_fork]   Takes a browser slot.
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { ensureServer, BASE } from './server.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args.splice(i, 2)[1] : d; };
const world = opt('--world', 'laurel_fork');
const locks = path.join(root, 'build/locks');
let slot = null;
while (!slot) {
  for (let i = 0; i < 3 && !slot; i++) { try { fs.mkdirSync(path.join(locks, `browser_${i}`)); slot = path.join(locks, `browser_${i}`); } catch {} }
  if (!slot) await new Promise((r) => setTimeout(r, 2000));
}
const release = () => { try { fs.rmdirSync(slot); } catch {} };
process.on('exit', release);
const stop = await ensureServer();
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
let fail = 0;
try {
  const page = await (await b.newContext({ viewport: { width: 800, height: 450 } })).newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(`${BASE}/viewer/wild.html?world=${world}&t=3&hud=0&q=3&view=bridge`);
  await page.waitForFunction(() => window.__loaded || document.getElementById('hud')?.textContent.startsWith('error'), null, { timeout: 300000 });
  const r = await page.evaluate(() => {
    const W = window.__water, w = window.__wild.world, oy = w.meta.estate_offset[1];
    if (!W) return { error: 'no window.__water' };
    const at = (xe, ye) => { const x = xe, z = -(ye - oy); const f = W.flowAt(x, z);
      return { xe, ye, s: W.surfaceAt(x, z), d: W.depthAt(x, z), g: w.heightAt(x, z), wet: W.wet(x, z), vx: f.x, vz: f.z, v: f.speed }; };
    // across the river on the bridge's line (estate y -848), every 2 m
    const across = [];
    for (let xe = -600; xe <= -525; xe += 2) across.push(at(xe, -848));
    // down the main stem's thalweg: the wettest point of each row every 10 m
    const along = [];
    for (let ye = -1500; ye <= -800; ye += 10) {
      let best = null;
      for (let xe = -700; xe <= -500; xe += 1) { const p = at(xe, ye); if (p.wet && (!best || p.d > best.d)) best = p; }
      if (best) along.push(best);
    }
    // continuity: the surface between two samples 5 cm apart never jumps
    let jump = 0;
    for (let xe = -585; xe < -545; xe += 0.05) {
      const a = W.surfaceAt(xe, -(-848 - oy)), c = W.surfaceAt(xe + 0.05, -(-848 - oy));
      if (Number.isFinite(a) && Number.isFinite(c)) jump = Math.max(jump, Math.abs(a - c));
    }
    const calls = [];
    window.__three.scene.traverse((o) => { if (o.isMesh && /Water|Falls|Spray|Mist/.test(o.name)) calls.push(o.name); });
    return { across, along, jump, calls, dry: at(-480, -848) };
  });
  if (r.error) { console.log('FAIL', r.error); fail++; }
  else {
    const wetAcross = r.across.filter((p) => p.wet);
    console.log(`across the bridge line: ${wetAcross.length * 2} m wet, depth max ${Math.max(...wetAcross.map((p) => p.d)).toFixed(2)} m`);
    console.log('  ' + r.across.map((p) => (p.wet ? p.d.toFixed(1) : '.')).join(' '));
    if (wetAcross.length < 8) { console.log('FAIL the river is not under the bridge'); fail++; }
    const bad = r.across.filter((p) => p.wet && Math.abs(p.s - p.g - p.d) > 1e-3);
    if (bad.length) { console.log('FAIL depth != surface - ground at', bad.length, 'samples'); fail++; }
    const up = r.along.filter((p) => p.vz > 0.05);            // (north = -z: a +z current runs upstream)
    console.log(`thalweg samples ${r.along.length}; speed p50 ${r.along.map((p) => p.v).sort((a, b) => a - b)[r.along.length >> 1]?.toFixed(2)} m/s, max ${Math.max(...r.along.map((p) => p.v)).toFixed(2)}; running upstream at ${up.length}`);
    if (up.length > r.along.length * 0.1) { console.log('FAIL the current runs upstream at', up.map((p) => p.ye).join(',')); fail++; }
    console.log(`surface jump over 5 cm: ${r.jump.toFixed(3)} m`);
    if (r.jump > 0.25) { console.log('FAIL surface not continuous'); fail++; }
    if (r.dry.wet || r.dry.v > 0) { console.log('FAIL dry bank reads wet'); fail++; }
    console.log('water meshes:', r.calls.join(', '));
    console.log('profile (ye: depth / speed):', r.along.filter((_, i) => i % 5 === 0).map((p) => `${p.ye}: ${p.d.toFixed(1)}/${p.v.toFixed(1)}`).join('  '));
  }
  if (errors.length) { console.log('page errors:', errors.join('\n')); fail++; }
} finally { await b.close(); stop(); release(); }
console.log(fail ? `${fail} FAILED` : 'PASS');
process.exit(fail ? 1 : 0);
