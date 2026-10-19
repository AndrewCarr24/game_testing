// Performance benchmark: a scripted run through the house at the player's run speed
// (bench_route.mjs), timing every frame, plus load cost. Writes
// build/bench/<label>/stats-<profile>.json, prints a summary with budget checks
// (budgets.json) and appends one line to bench_history.jsonl.
//
// Usage: node viewer/tools/bench.mjs [label] [--profile gpu|soft|gpu,soft]
//   gpu  = this Mac's GPU (Metal), 1600x900 at DPR 2 (the game caps rendering at 1.5x)
//   soft = SwiftShader (no GPU, CPU rendering) at 1280x720: a stand-in for weak hardware
// Frames are uncapped (no vsync), so frame time is the real cost, not 1/60 s.
// BENCH_QS="&tm=agx" appends to the page's query string (A/B tests of viewer switches).
import { chromium } from 'playwright-core';
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { ROUTE, RUN } from './bench_route.mjs';
import { ensureServer, BASE } from './server.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../..');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args.splice(i, 2)[1] : d; };
const profiles = opt('--profile', 'gpu,soft').split(',');
const label = args[0] || 'latest';
const outDir = path.join(root, 'build/bench', label);
fs.mkdirSync(outDir, { recursive: true });

const PROFILES = {
  gpu: { angle: 'metal', w: 1600, h: 900, dpr: 2 },
  soft: { angle: 'swiftshader', w: 1280, h: 720, dpr: 1 },
};
const budgets = JSON.parse(fs.readFileSync(path.join(here, 'budgets.json'), 'utf8'));
let commit = '?';
try { commit = execSync('git rev-parse --short HEAD', { cwd: root }).toString().trim()
  + (execSync('git status --porcelain', { cwd: root }).toString().trim() ? '+dirty' : ''); } catch {}

const stop = await ensureServer();
for (const name of profiles) {
  const s = await run(name, PROFILES[name]);
  fs.writeFileSync(path.join(outDir, `stats-${name}.json`), JSON.stringify(s, null, 1));
  report(s);
  fs.appendFileSync(path.join(here, 'bench_history.jsonl'), JSON.stringify({
    date: s.date, commit, label, profile: name, fps: s.fps, frameP95: s.frameMs.p95, gpuP95: s.gpuMs.p95,
    hitches: s.hitches, callsMax: s.drawCalls.max, trisMax: s.triangles.max,
    downloadMB: s.load.downloadMB, textureMB: s.load.textureMB, loadS: s.load.seconds,
  }) + '\n');
}
stop();

async function run(name, P) {
  const b = await chromium.launch({ channel: 'chrome', args: [
    `--use-angle=${P.angle}`, '--enable-unsafe-swiftshader', '--disable-gpu-vsync', '--disable-frame-rate-limit',
    '--enable-precise-memory-info'] });
  const ctx = await b.newContext({ viewport: { width: P.w, height: P.h }, deviceScaleFactor: P.dpr });
  const page = await ctx.newPage();
  page.on('pageerror', (e) => console.log('pageerror:', e.message));
  // the browser keeps 250 resource timings by default; the house loads ~430 files
  await page.addInitScript(() => performance.setResourceTimingBufferSize(10000));
  const t0 = Date.now();
  await page.goto(`${BASE}/viewer/index.html?level=mansion${process.env.BENCH_QS || ''}`);
  await page.waitForFunction(() => window.__loaded, null, { timeout: 300000 });
  const loadSeconds = (Date.now() - t0) / 1000;
  await page.waitForTimeout(1000);
  process.stdout.write(`[${name}] loaded in ${loadSeconds.toFixed(1)} s, running the route...`);

  const raw = await page.evaluate(async ({ route, speed }) => {
    const { renderer, scene, camera } = window.__three;
    const gl = renderer.getContext();
    const V = camera.position.constructor;
    // ---- timeline: per waypoint an optional spin, then a straight move to the next one
    const pts = route.map((w) => new V(...w.p));
    const items = []; let dist = 0;
    const dirOf = (i) => (i + 1 < pts.length ? pts[i + 1].clone().sub(pts[i]) : pts[i].clone().sub(pts[i - 1]));
    for (let i = 0; i < pts.length; i++) {
      if (route[i].spin) items.push({ spin: true, at: pts[i], dur: route[i].spin, a0: Math.atan2(dirOf(i).z, dirOf(i).x) });
      if (i + 1 < pts.length) {
        const len = pts[i].distanceTo(pts[i + 1]);
        items.push({ a: pts[i], b: pts[i + 1], len, s0: dist, dur: len / speed });
        dist += len;
      }
    }
    const total = items.reduce((t, it) => t + it.dur, 0);
    const moves = items.filter((it) => !it.spin);
    const along = (s) => {     // point at path distance s
      for (const m of moves) if (s <= m.s0 + m.len) return m.a.clone().lerp(m.b, Math.max(0, (s - m.s0) / m.len));
      return pts[pts.length - 1].clone();
    };
    const pose = (t) => {
      for (const it of items) {
        if (t > it.dur) { t -= it.dur; continue; }
        const u = t / it.dur;
        if (it.spin) {
          const a = it.a0 + u * Math.PI * 2;
          return [it.at, it.at.clone().add(new V(Math.cos(a), -0.1, Math.sin(a)))];
        }
        const p = it.a.clone().lerp(it.b, u);
        const look = along(it.s0 + u * it.len + 2.5);
        look.y -= 0.15;
        if (look.distanceTo(p) < 0.1) look.add(it.b.clone().sub(it.a).normalize());
        return [p, look];
      }
      return [pts[pts.length - 1], along(dist + 1)];
    };
    // ---- per-frame recording
    const ext = gl.getExtension('EXT_disjoint_timer_query_webgl2');
    const f = { t: [], interval: [], cpu: [], submit: [], gpu: [], calls: [], tris: [], x: [], y: [], z: [] };
    const pending = [];
    const poll = () => {
      while (pending.length) {
        const [q, i] = pending[0];
        if (!gl.getQueryParameter(q, gl.QUERY_RESULT_AVAILABLE)) break;
        if (!gl.getParameter(ext.GPU_DISJOINT_EXT)) f.gpu[i] = gl.getQueryParameter(q, gl.QUERY_RESULT) / 1e6;
        gl.deleteQuery(q); pending.shift();
      }
    };
    let start = null, last = 0, ts = 0, tr = 0, query = null, done;
    const finished = new Promise((ok) => (done = ok));
    window.__bench = {
      frameStart() {
        ts = performance.now();
        if (start === null) { start = ts; last = ts; }
        if (ext) poll();
      },
      drive() {
        const t = (ts - start) / 1000;
        const [p, look] = pose(t);
        camera.position.copy(p);
        camera.lookAt(look);
        const pl = window.__player;   // keep the player (physics, culling) where the camera is
        pl.pos.set(p.x, p.y - pl.eye, p.z); pl.vel.set(0, 0, 0);
      },
      renderStart() {
        tr = performance.now();
        if (ext) { query = gl.createQuery(); gl.beginQuery(ext.TIME_ELAPSED_EXT, query); }
      },
      frameEnd() {
        const te = performance.now();
        const i = f.interval.length;
        if (ext) { gl.endQuery(ext.TIME_ELAPSED_EXT); pending.push([query, i]); }
        f.t.push((ts - start) / 1000); f.interval.push(ts - last); last = ts;
        f.cpu.push(tr - ts); f.submit.push(te - tr); f.gpu.push(null);
        f.calls.push(renderer.info.render.calls); f.tris.push(renderer.info.render.triangles);
        f.x.push(camera.position.x); f.y.push(camera.position.y); f.z.push(camera.position.z);
        if ((ts - start) / 1000 > total) { const no = () => {}; window.__bench = { frameStart: poll, drive: no, renderStart: no, frameEnd: no }; setTimeout(done, 300); }
      },
    };
    await finished;
    window.__bench = null;
    // texture memory estimate: every texture any material uses, w*h*4 bytes, +1/3 for mips
    const tex = new Set(); let texBytes = 0;
    scene.traverse((o) => { if (!o.material) return; for (const m of [].concat(o.material)) for (const v of Object.values(m)) {
      if (v && v.isTexture && v.image && !tex.has(v)) { tex.add(v); texBytes += (v.image.width || 0) * (v.image.height || 0) * 4 * 1.33; } } });
    const dbg = gl.getExtension('WEBGL_debug_renderer_info');
    // unique bytes fetched from our own server (a texture shared by several assets downloads once)
    const urls = new Map();
    for (const e of performance.getEntriesByType('resource')) if (e.name.startsWith(location.origin)) urls.set(e.name, e.encodedBodySize);
    return {
      bytes: [...urls.values()].reduce((a, c) => a + c, 0), files: urls.size,
      f, total, gpuTimer: !!ext,
      gpuName: dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : '?',
      buffer: `${gl.drawingBufferWidth}x${gl.drawingBufferHeight}`,
      textureMB: texBytes / 1e6, programs: renderer.info.programs.length,
      geometries: renderer.info.memory.geometries, textures: renderer.info.memory.textures,
      heapMB: performance.memory ? performance.memory.usedJSHeapSize / 1e6 : null,
      rooms: Object.entries(window.__level.rooms).map(([n, r]) => ({ n, rect: r.rect, floor: r.floor })),
    };
  }, { route: ROUTE, speed: RUN });
  await b.close();
  console.log(` ${raw.f.interval.length} frames`);
  return summarise(name, P, raw, loadSeconds);
}

function summarise(name, P, raw, loadSeconds) {
  const { f } = raw;
  const n = f.interval.length;
  const idx = [...Array(n).keys()].slice(1);            // frame 0 has no interval
  const pct = (arr, q) => { const s = arr.filter((v) => v != null).sort((a, c) => a - c); return s.length ? +s[Math.min(s.length - 1, Math.floor(q * s.length))].toFixed(2) : null; };
  const stat = (arr) => ({ p50: pct(arr, 0.5), p95: pct(arr, 0.95), p99: pct(arr, 0.99), max: pct(arr, 1) });
  const mean = (arr) => +(arr.reduce((a, c) => a + c, 0) / arr.length).toFixed(1);
  const pick = (a) => idx.map((i) => a[i]);
  const roomAt = (i) => {
    let best = null;
    for (const r of raw.rooms) {
      const [x0, z0, x1, z1] = r.rect;
      if (f.x[i] >= x0 && f.x[i] <= x1 && f.z[i] >= z0 && f.z[i] <= z1 && f.y[i] >= r.floor && (!best || r.floor > best.floor)) best = r;
    }
    return best ? best.n : 'outside';
  };
  const perRoom = {};
  for (const i of idx) {
    const r = (perRoom[roomAt(i)] ??= { frames: 0, frame: [], gpu: [], calls: 0, tris: 0 });
    r.frames++; r.frame.push(f.interval[i]); r.gpu.push(f.gpu[i]); r.calls = Math.max(r.calls, f.calls[i]); r.tris = Math.max(r.tris, f.tris[i]);
  }
  const seconds = idx.reduce((t, i) => t + f.interval[i], 0) / 1000;
  return {
    label, profile: name, date: new Date().toISOString(), commit, gpu: raw.gpuName, buffer: raw.buffer,
    route: { seconds: +raw.total.toFixed(1), speed: RUN },
    load: { seconds: +loadSeconds.toFixed(1), downloadMB: +(raw.bytes / 1e6).toFixed(2), files: raw.files, textureMB: +raw.textureMB.toFixed(0) },
    frames: n, fps: +(idx.length / seconds).toFixed(1),
    frameMs: stat(pick(f.interval)), gpuMs: raw.gpuTimer ? stat(pick(f.gpu)) : null,
    cpuMs: stat(pick(f.cpu)), submitMs: stat(pick(f.submit)),
    hitches: idx.filter((i) => f.interval[i] > 50).length,
    drawCalls: { mean: mean(pick(f.calls)), p95: pct(pick(f.calls), 0.95), max: Math.max(...pick(f.calls)) },
    triangles: { mean: Math.round(mean(pick(f.tris))), max: Math.max(...pick(f.tris)) },
    programs: raw.programs, geometries: raw.geometries, textures: raw.textures,
    heapMB: raw.heapMB && +raw.heapMB.toFixed(0),
    perRoom: Object.fromEntries(Object.entries(perRoom).map(([k, r]) => [k,
      { frames: r.frames, frameP95: pct(r.frame, 0.95), gpuP95: pct(r.gpu, 0.95), callsMax: r.calls, trisMax: r.tris }])),
    worst: idx.sort((a, c) => f.interval[c] - f.interval[a]).slice(0, 8).map((i) => ({
      t: +f.t[i].toFixed(1), room: roomAt(i), frameMs: +f.interval[i].toFixed(1),
      gpuMs: f.gpu[i] != null ? +f.gpu[i].toFixed(2) : null, cpuMs: +f.cpu[i].toFixed(2), calls: f.calls[i], tris: f.tris[i] })),
  };
}

// a budget is "metric path": limit (the metric must not exceed it)
export function checkBudgets(s) {
  const b = budgets[s.profile] || {};
  return Object.entries(b).filter(([k]) => !k.startsWith('_')).map(([k, limit]) => {
    const v = k.split('.').reduce((o, p) => (o == null ? o : o[p]), s);
    return { metric: k, value: v, limit, ok: v != null && v <= limit };
  });
}

function report(s) {
  const g = s.gpuMs ? `gpu p50 ${s.gpuMs.p50} / p95 ${s.gpuMs.p95} ms · ` : '';
  console.log(`[${s.profile}] ${s.gpu} ${s.buffer}
  load ${s.load.seconds} s · download ${s.load.downloadMB} MB · textures ~${s.load.textureMB} MB
  ${s.frames} frames in ${s.route.seconds} s · ${s.fps} fps · frame p50 ${s.frameMs.p50} / p95 ${s.frameMs.p95} / max ${s.frameMs.max} ms
  ${g}cpu p95 ${s.cpuMs.p95} ms · submit p95 ${s.submitMs.p95} ms · hitches (>50 ms) ${s.hitches}
  draw calls mean ${s.drawCalls.mean} / max ${s.drawCalls.max} · triangles max ${s.triangles.max} · programs ${s.programs} · heap ${s.heapMB} MB`);
  const rooms = Object.entries(s.perRoom).sort((a, c) => (c[1].frameP95 ?? 0) - (a[1].frameP95 ?? 0)).slice(0, 5);
  console.log('  slowest rooms (frame p95 ms):', rooms.map(([k, r]) => `${k} ${r.frameP95}`).join(', '));
  for (const c of checkBudgets(s)) console.log(`  ${c.ok ? 'PASS' : 'FAIL'}  ${c.metric} = ${c.value} (budget ${c.limit})`);
}
