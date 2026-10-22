// The water's own render cost, measured as an in-page A/B (robust on a busy machine): at each view,
// alternate frames with the water group (surface + falls sheet + mist) shown and hidden, timing
// renderer.render + a pixel readback (= finish), and report the medians and the difference.
// Usage: node viewer/tools/wild_water_cost.mjs [--profile soft|gpu] [--views bridge,cascade] [--extra views.json]
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { ensureServer, BASE } from './server.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args.splice(i, 2)[1] : d; };
const profile = opt('--profile', 'soft');
const views = opt('--views', 'bridge,river_gorge,cascade').split(',');
const extraFile = opt('--extra', '');
const extra = extraFile ? JSON.parse(fs.readFileSync(extraFile, 'utf8')) : null;
const P = { gpu: { angle: 'metal', w: 1600, h: 900, dpr: 2, q: 3 }, soft: { angle: 'swiftshader', w: 1280, h: 720, dpr: 1, q: 0 } }[profile];
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
try {
  const page = await (await b.newContext({ viewport: { width: P.w, height: P.h }, deviceScaleFactor: P.dpr })).newPage();
  await page.goto(`${BASE}/viewer/wild.html?world=laurel_fork&t=3&hud=0&q=${P.q}`);
  await page.waitForFunction(() => window.__loaded, null, { timeout: 300000 });
  if (extra) await page.evaluate((ex) => { const W = window.__wild.world;
    for (const [k, v] of Object.entries(ex)) W.views[k] = { pos: v.pos || [v.at[0], W.heightAt(v.at[0], v.at[1]) + (v.eye ?? 1.7), v.at[1]], look: v.look }; }, extra);
  for (const v of views) {
    const r = await page.evaluate(async (v) => {
      const w = window.__wild, { renderer, scene, camera } = window.__three;
      w.fly = true; if (!w.setView(v)) return null;
      await new Promise((ok) => { let n = 0; const f = () => (++n < 10 ? requestAnimationFrame(f) : ok()); requestAnimationFrame(f); });
      w.pause(true);
      const grp = scene.getObjectByName('Wild_WaterGroup'), gl = renderer.getContext(), px = new Uint8Array(4);
      const time = () => { const t0 = performance.now(); renderer.render(scene, camera); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); return performance.now() - t0; };
      const on = [], off = [];
      for (let i = 0; i < 8; i++) { grp.visible = true; on.push(time()); grp.visible = false; off.push(time()); }
      grp.visible = true; w.pause(false);
      const med = (a) => a.sort((x, y) => x - y)[a.length >> 1];
      return { on: med(on), off: med(off) };
    }, v);
    if (!r) { console.log(`${v}: no such view`); continue; }
    console.log(`${v.padEnd(20)} with water ${r.on.toFixed(1)} ms, without ${r.off.toFixed(1)} ms: water costs ${(r.on - r.off).toFixed(1)} ms`);
  }
} finally { await b.close(); stop(); release(); }
