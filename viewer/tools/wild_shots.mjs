// Eye-height screenshots of a generated wilderness level (viewer/wild.html?world=<name>): one
// per named view in its world.json (the brief's moments: the gate, the meadow edge, Poplar Cove,
// the falls, the footlog, a laurel hell, each lookout looking back at the house, the Gap).
// Usage: node viewer/tools/wild_shots.mjs [label] [--world laurel_fork] [--views a,b] [--profile gpu|soft] [--qs "&veg=0"]
// Output: build/wilderness/<world>/shots/<label>/<view>.png (+ errors.txt). Takes a browser slot.
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { ensureServer, BASE } from './server.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args.splice(i, 2)[1] : d; };
const world = opt('--world', 'laurel_fork');
const only = opt('--views', '');
const profile = opt('--profile', 'gpu');
const qs = opt('--qs', process.env.WILD_QS || '');
const label = args[0] || 'latest';
const out = path.join(root, 'build/wilderness', world, 'shots', label);
fs.mkdirSync(out, { recursive: true });
const P = { gpu: { angle: 'metal', w: 1600, h: 900, dpr: 1.5 }, soft: { angle: 'swiftshader', w: 1280, h: 720, dpr: 1 } }[profile];

const locks = path.join(root, 'build/locks');
let slot = null;
while (!slot) {
  for (let i = 0; i < 3 && !slot; i++) { try { fs.mkdirSync(path.join(locks, `browser_${i}`)); slot = path.join(locks, `browser_${i}`); } catch {} }
  if (!slot) await new Promise((r) => setTimeout(r, 2000));
}
const release = () => { try { fs.rmdirSync(slot); } catch {} };
process.on('exit', release);
const stop = await ensureServer();
const b = await chromium.launch({ channel: 'chrome', args: [`--use-angle=${P.angle}`, '--enable-unsafe-swiftshader'] });
const errors = [];
let report = null;
try {
  const page = await (await b.newContext({ viewport: { width: P.w, height: P.h }, deviceScaleFactor: P.dpr })).newPage();
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') errors.push(`${m.type()}: ${m.text().slice(0, 400)}`); });
  const t0 = Date.now();
  await page.goto(`${BASE}/viewer/wild.html?world=${world}&t=3&hud=0&q=3${qs}`);
  await page.waitForFunction(() => window.__loaded || document.getElementById('hud')?.textContent.startsWith('error'), null, { timeout: 300000 });
  const hud = await page.evaluate(() => document.getElementById('hud').textContent);
  if (hud.startsWith('error')) throw new Error(hud);
  console.log(`loaded in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
  const names = await page.evaluate(() => Object.keys(window.__wild.world.views));
  const meta = await page.evaluate(() => { const w = window.__wild; const by = w.downloadBy();
    return { textureMB: w.textureMB(), textures: w.textureList(), downloadMB: +Object.values(by).reduce((a, b) => a + b, 0).toFixed(2), downloadBy: by }; });
  console.log(`textures ${meta.textureMB} MB, download ${meta.downloadMB} MB ${JSON.stringify(meta.downloadBy)}`);
  report = { meta, views: {} };
  const views = only ? only.split(',') : names.filter((n) => !['open', 'forest', 'ridge', 'spawn'].includes(n));
  for (const v of views) {
    const info = await page.evaluate(async (v) => {
      const w = window.__wild, { renderer, scene, camera } = window.__three;
      w.fly = true;
      if (!w.setView(v)) return null;
      // warm up: forest cells, props, impostor cross-fades settle
      await new Promise((ok) => { let n = 0; const f = () => (++n < 12 ? requestAnimationFrame(f) : ok()); requestAnimationFrame(f); });
      w.pause(true);
      const s = w.stats();
      const url = renderer.domElement.toDataURL('image/png');
      w.pause(false);
      return { url, calls: s.calls, tris: s.triangles, pos: s.pos, callsBy: s.callsBy };
    }, v);
    if (!info) { console.log(`  ${v}: no such view`); continue; }
    fs.writeFileSync(path.join(out, `${v}.png`), Buffer.from(info.url.split(',')[1], 'base64'));
    console.log(`  ${v.padEnd(12)} calls ${info.calls}  tris ${(info.tris / 1000).toFixed(0)}k  at ${info.pos}`);
    if (process.env.WILD_CALLS) console.log('     ' + info.callsBy.join(' '));
    report.views[v] = { calls: info.calls, tris: info.tris, callsBy: info.callsBy };
  }
} catch (e) {
  errors.push('fatal: ' + e.message);
  console.log('FAILED', e.message);
} finally {
  fs.writeFileSync(path.join(out, 'errors.txt'), errors.join('\n'));
  if (report) fs.writeFileSync(path.join(out, 'stats.json'), JSON.stringify(report, null, 1));
  if (errors.length) console.log(errors.slice(0, 20).join('\n'));
  await b.close(); stop(); release();
}
