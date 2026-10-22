// Wilderness runtime benchmark (viewer/wild_proto.html): per named view (open meadow, densest
// forest, ridge, trail start) a static hold then a 360° pan, timing every uncapped frame (frame
// interval, GPU timer query where available, culling CPU), draw calls and triangles; then a run
// along the trail on viewer/player.js (ground following checked every frame). Plus load time,
// download, GPU texture MB and the shipped size the generated data would have.
//
// Usage: node viewer/tools/wild_bench.mjs [label] [--profile gpu|soft|gpu,soft] [--views a,b]
//   gpu  = Metal 1600x900 DPR 2 (the page caps rendering at 1.5x -> 2400x1350)
//   soft = SwiftShader 1280x720 DPR 1 (no GPU; stand-in for weak hardware)
// WILD_QS="&trees=20000" appends to the page URL (A/B runs); WILD_QS="&world=laurel_fork" benches a
// generated level (its views open / forest / ridge / spawn = meadow edge, Poplar Cove, Painted Rock,
// the gate; the walk follows its route A). Takes a browser slot
// (build/locks/browser_0..2). Output: build/wild_bench/<label>/stats-<profile>.json + <view>-<profile>.png
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { ensureServer, BASE } from './server.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../..');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args.splice(i, 2)[1] : d; };
const profiles = opt('--profile', 'gpu,soft').split(',');
const views = opt('--views', 'open,forest,ridge,spawn').split(',');
const noWalk = args.includes('--no-walk'); if (noWalk) args.splice(args.indexOf('--no-walk'), 1);
const label = args[0] || 'latest';
const outDir = path.join(root, 'build/wild_bench', label);
fs.mkdirSync(outDir, { recursive: true });

const PROFILES = {
  // q: the quality level the page picks by itself there (fixed, so the governor can't step
  // down between views); WILD_QS="&q=N" overrides
  gpu: { angle: 'metal', w: 1600, h: 900, dpr: 2, hold: 2.5, spin: 5, run: 12, q: 3 },
  soft: { angle: 'swiftshader', w: 1280, h: 720, dpr: 1, hold: 4, spin: 8, run: 12, q: 0 },
};

// one browser at a time per slot
const locks = path.join(root, 'build/locks');
let slot = null;
for (let t = 0; !slot; t++) {
  for (let i = 0; i < 3 && !slot; i++) { try { fs.mkdirSync(path.join(locks, `browser_${i}`)); slot = path.join(locks, `browser_${i}`); } catch {} }
  if (!slot) { if (t === 0) console.log('waiting for a browser slot...'); await new Promise((r) => setTimeout(r, 2000)); }
}
const release = () => { try { fs.rmdirSync(slot); } catch {} };
process.on('exit', release);
process.on('SIGINT', () => { release(); process.exit(130); });

const stop = await ensureServer();
try {
  for (const name of profiles) {
    const s = await run(name, PROFILES[name]);
    fs.writeFileSync(path.join(outDir, `stats-${name}.json`), JSON.stringify(s, null, 1));
    report(s);
  }
} finally { stop(); release(); }

async function run(name, P) {
  const b = await chromium.launch({ channel: 'chrome', args: [`--use-angle=${P.angle}`, '--enable-unsafe-swiftshader',
    '--disable-gpu-vsync', '--disable-frame-rate-limit', '--enable-precise-memory-info'] });
  const ctx = await b.newContext({ viewport: { width: P.w, height: P.h }, deviceScaleFactor: P.dpr });
  const page = await ctx.newPage();
  page.on('pageerror', (e) => console.log('pageerror:', e.message));
  page.on('console', (m) => { if (m.type() === 'error' && !/404/.test(m.text())) console.log('console:', m.text().slice(0, 300)); });
  const t0 = Date.now();
  const qs = process.env.WILD_QS || '';
  await page.goto(`${BASE}/viewer/wild_proto.html?t=3${/[?&]q=/.test(qs) ? '' : `&q=${P.q}`}${qs}`);
  await page.waitForFunction(() => window.__loaded, null, { timeout: 300000 });
  const loadSeconds = (Date.now() - t0) / 1000;
  console.log(`[${name}] loaded in ${loadSeconds.toFixed(1)} s`);

  const info = await page.evaluate(async () => {
    const w = window.__wild, { renderer } = window.__three, gl = renderer.getContext();
    const dbg = gl.getExtension('WEBGL_debug_renderer_info');
    const urls = new Map(); let external = 0;
    for (const e of performance.getEntriesByType('resource')) {
      if (e.name.startsWith(location.origin)) urls.set(e.name, e.encodedBodySize); else external += e.encodedBodySize || 0;
    }
    const counts = Object.fromEntries(Object.entries(w.world.species).map(([k, a]) => [k, a.length / 6]));
    return {
      gpu: dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : '?', buffer: `${gl.drawingBufferWidth}x${gl.drawingBufferHeight}`,
      downloadMB: +([...urls.values()].reduce((a, c) => a + c, 0) / 1e6).toFixed(2), files: urls.size, externalMB: +(external / 1e6).toFixed(2),
      textureMB: w.textureMB(), timings: w.timings, quality: w.quality.level, softwareGPU: w.softwareGPU, msaa: gl.getContextAttributes().antialias, counts, colliders: w.colliders,
      programs: renderer.info.programs.length, geometries: renderer.info.memory.geometries,
      heapMB: performance.memory ? +(performance.memory.usedJSHeapSize / 1e6).toFixed(0) : null,
      shipping: await w.shippingEstimate(),
      tris: Object.fromEntries(w.forest.species.map((s) => [s.name, s.tris])),
    };
  });

  const results = {};
  for (const v of views) {
    const r = await page.evaluate(async ({ v, hold, spin }) => {
      const w = window.__wild, { renderer, camera } = window.__three, gl = renderer.getContext();
      const ext = gl.getExtension('EXT_disjoint_timer_query_webgl2');
      w.fly = true;
      w.setView(v);
      const view = w.world.views[v];
      const yaw0 = Math.atan2(view.look[2] - view.pos[2], view.look[0] - view.pos[0]), pitch = view.look[1] - view.pos[1];
      // warm up (shader programs, buffers)
      await new Promise((ok) => { let n = 0; const f = () => (++n < 20 ? requestAnimationFrame(f) : ok()); requestAnimationFrame(f); });
      const f = { t: [], interval: [], gpu: [], cpu: [], calls: [], tris: [], cull: [] };
      const pending = [];
      const poll = () => {
        while (pending.length) {
          const [q, i] = pending[0];
          if (!gl.getQueryParameter(q, gl.QUERY_RESULT_AVAILABLE)) break;
          if (!gl.getParameter(ext.GPU_DISJOINT_EXT)) f.gpu[i] = gl.getQueryParameter(q, gl.QUERY_RESULT) / 1e6;
          gl.deleteQuery(q); pending.shift();
        }
      };
      let start = null, last = 0, ts = 0, query = null, done;
      const finished = new Promise((ok) => (done = ok));
      window.__bench = {
        frameStart() { ts = performance.now(); if (start === null) { start = ts; last = ts; } if (ext) poll(); },
        drive() {
          const t = (ts - start) / 1000;
          const a = t < hold ? yaw0 : yaw0 + ((t - hold) / spin) * Math.PI * 2;
          camera.position.set(...view.pos);
          camera.lookAt(view.pos[0] + Math.cos(a) * 10, view.pos[1] + pitch, view.pos[2] + Math.sin(a) * 10);
        },
        renderStart() { if (ext) { query = gl.createQuery(); gl.beginQuery(ext.TIME_ELAPSED_EXT, query); } },
        frameEnd() {
          const i = f.interval.length;
          if (ext) { gl.endQuery(ext.TIME_ELAPSED_EXT); pending.push([query, i]); }
          const s = w.stats();
          f.t.push((ts - start) / 1000); f.interval.push(ts - last); last = ts; f.gpu.push(null);
          f.calls.push(renderer.info.render.calls); f.tris.push(renderer.info.render.triangles); f.cull.push(s.cullMs);
          if ((ts - start) / 1000 > hold + spin) { const no = () => {}; window.__bench = { frameStart: poll, drive: no, renderStart: no, frameEnd: no }; setTimeout(done, 300); }
        },
      };
      await finished;
      window.__bench = null;
      // synchronous timing: N frames each followed by a readback, in the view's
      // direction and 3 more quarter turns; the loop is paused meanwhile
      w.pause(true);
      const N = /SwiftShader/i.test(gl.getParameter(gl.getExtension('WEBGL_debug_renderer_info')?.UNMASKED_RENDERER_WEBGL ?? gl.RENDERER)) ? 3 : 30;
      const finishMs = [], px = new Uint8Array(4);
      // (a 1-pixel readback: gl.finish() returns at once through ANGLE / SwiftShader here)
      const sync = () => gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
      for (let q = 0; q < 4; q++) {
        const a = yaw0 + (q * Math.PI) / 2;
        camera.position.set(...view.pos);
        camera.lookAt(view.pos[0] + Math.cos(a) * 10, view.pos[1] + pitch, view.pos[2] + Math.sin(a) * 10);
        w.cull(); renderer.render(window.__three.scene, camera); sync();
        const t0 = performance.now();
        for (let i = 0; i < N; i++) { w.cull(); renderer.render(window.__three.scene, camera); sync(); }
        finishMs.push(+((performance.now() - t0) / N).toFixed(2));
      }
      w.pause(false);
      w.setView(v);
      const s = w.stats();
      return { f, hold, stats: s, finishMs };
    }, { v, hold: P.hold, spin: P.spin });
    await shot(page, path.join(outDir, `${v}-${name}.png`));
    results[v] = { ...summarise(r), stats: r.stats, finishMs: { dirs: r.finishMs, max: Math.max(...r.finishMs), mean: +(r.finishMs.reduce((a, b) => a + b, 0) / 4).toFixed(2) } };
    const s = results[v];
    console.log(`  ${v.padEnd(7)} render+finish ${s.finishMs.mean} ms (max dir ${s.finishMs.max}), hold mean ${s.hold.meanMs} ms (gpu ${s.hold.gpuMs?.p50 ?? '-'}), spin p95 ${s.spin.frameMs.p95} ms, calls ${s.all.calls.max}, tris ${(s.all.tris.max / 1000).toFixed(0)}k, cull ${s.all.cullMs.p95} ms`);
  }

  if (noWalk) { await b.close(); return { label, profile: name, date: new Date().toISOString(), qs: process.env.WILD_QS || '', viewport: `${P.w}x${P.h}@${P.dpr}`, load: { seconds: +loadSeconds.toFixed(1) }, ...info, views: results }; }
  // run along the trail from the spawn on the player (ground following, trunk colliders)
  await page.evaluate(() => { const w = window.__wild; w.fly = false; w.setView('spawn'); });
  await page.keyboard.down('KeyW'); await page.keyboard.down('ShiftLeft');
  const walk = await page.evaluate(async (secs) => {
    const w = window.__wild, { camera } = window.__three, pl = window.__player, world = w.world;
    const trail = (z) => 120 * Math.sin(z / 300) + 40 * Math.sin(z / 97) + 60;     // world.js's trail
    const route = w.world.routes?.A;                     // a generated level: its route A from the gate
    let rk = 0;
    const ahead = () => {
      for (let q = rk, bd = 1e9; q < Math.min(route.length, rk + 30); q++) { const d = Math.hypot(route[q][0] - pl.pos.x, route[q][1] - pl.pos.z); if (d < bd) { bd = d; rk = q; } }
      return route[Math.min(route.length - 1, rk + 3)];
    };
    const out = { interval: [], dy: [], speed: [], calls: [], tris: [] };
    let last = performance.now(), t0 = last, prev = pl.pos.clone();
    await new Promise((ok) => {
      const f = () => {
        const now = performance.now();
        if (route) { const [x, z] = ahead(); camera.lookAt(x, camera.position.y, z); }
        else { const z = pl.pos.z - 25, x = trail(z); camera.lookAt(x, camera.position.y, z); }
        out.interval.push(now - last); last = now;
        out.dy.push(pl.pos.y - world.heightAt(pl.pos.x, pl.pos.z));
        out.speed.push(pl.pos.distanceTo(prev) / Math.max(1e-3, out.interval.at(-1) / 1000)); prev = pl.pos.clone();
        const s = w.stats(); out.calls.push(s.calls); out.tris.push(s.triangles);
        if (now - t0 < secs * 1000) requestAnimationFrame(f); else ok();
      };
      requestAnimationFrame(f);
    });
    out.distance = Math.hypot(pl.pos.x - w.world.views.spawn.pos[0], pl.pos.z - w.world.views.spawn.pos[2]);
    return out;
  }, P.run);
  await page.keyboard.up('KeyW'); await page.keyboard.up('ShiftLeft');
  await shot(page, path.join(outDir, `walk-${name}.png`));
  await b.close();
  const ws = walk.interval.slice(5);
  const walkStats = { frames: walk.interval.length, frameMs: stat(ws), distanceM: +walk.distance.toFixed(1),
    feetAboveGround: { min: +Math.min(...walk.dy.slice(5)).toFixed(3), max: +Math.max(...walk.dy.slice(5)).toFixed(3) },
    calls: { max: Math.max(...walk.calls) }, tris: { max: Math.max(...walk.tris) } };
  console.log(`  walk    ${walkStats.distanceM} m, frame p95 ${walkStats.frameMs.p95} ms, feet-ground ${walkStats.feetAboveGround.min}..${walkStats.feetAboveGround.max} m`);
  return { label, profile: name, date: new Date().toISOString(), qs: process.env.WILD_QS || '', viewport: `${P.w}x${P.h}@${P.dpr}`,
    load: { seconds: +loadSeconds.toFixed(1) }, ...info, views: results, walk: walkStats };
}

// the canvas itself (preserveDrawingBuffer): page screenshots wait for a compositor frame that a
// software renderer may not deliver in time; no HUD in the picture (its numbers are in the JSON)
async function shot(page, file) {
  const url = await page.evaluate(() => { window.__wild.pause(true); const u = window.__three.renderer.domElement.toDataURL('image/png'); window.__wild.pause(false); return u; });
  fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
}

function stat(arr) {
  const s = arr.filter((v) => v != null).sort((a, c) => a - c);
  if (!s.length) return null;
  const q = (p) => +s[Math.min(s.length - 1, Math.floor(p * s.length))].toFixed(2);
  return { p50: q(0.5), p95: q(0.95), max: q(1), n: s.length };
}

function summarise({ f, hold }) {
  const idx = [...f.interval.keys()].slice(1);
  const pick = (a, sel) => idx.filter(sel).map((i) => a[i]);
  const H = (i) => f.t[i] <= hold, S = (i) => f.t[i] > hold, A = () => true;
  const mean = (a) => (a.length ? +(a.reduce((x, y) => x + y, 0) / a.length).toFixed(2) : null);
  const part = (sel) => ({ frameMs: stat(pick(f.interval, sel)), meanMs: mean(pick(f.interval, sel)), gpuMs: stat(pick(f.gpu, sel)), cullMs: stat(pick(f.cull, sel)),
    calls: { max: Math.max(...pick(f.calls, sel)), p50: stat(pick(f.calls, sel))?.p50 }, tris: { max: Math.max(...pick(f.tris, sel)), p50: stat(pick(f.tris, sel))?.p50 } });
  return { hold: part(H), spin: part(S), all: part(A) };
}

function report(s) {
  console.log(`\n== ${s.profile}: ${s.gpu} ${s.buffer}  load ${s.load.seconds} s  download ${s.downloadMB} MB (+${s.externalMB} MB three.js CDN)  textures ${s.textureMB} MB`);
  console.log(`   quality q${s.quality}${s.softwareGPU ? ' (software GPU)' : ''}, MSAA ${s.msaa}`);
  console.log(`   instances ${JSON.stringify(s.counts)}  shipping ${JSON.stringify(s.shipping)}`);
  console.log('   view      render+finish mean/max   spin p50/p95/max      gpu p50   calls max  tris max   cull p95');
  for (const [v, r] of Object.entries(s.views))
    console.log(`   ${v.padEnd(8)}  ${String(r.finishMs.mean).padStart(7)} / ${String(r.finishMs.max).padEnd(12)} ${String(r.spin.frameMs.p50).padStart(6)} / ${String(r.spin.frameMs.p95).padStart(6)} / ${String(r.spin.frameMs.max).padEnd(7)} ${String(r.all.gpuMs?.p50 ?? '-').padStart(7)}   ${String(r.all.calls.max).padStart(5)}   ${String((r.all.tris.max / 1000).toFixed(0) + 'k').padStart(7)}   ${r.all.cullMs.p95}`);
}
