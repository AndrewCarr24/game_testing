// Frame cost of many invaders in viewer/invader_view.html: the crowd path (?crowd=N, instanced, GPU
// skinned from the bone texture) against N SkinnedMeshes (?skinned=N, a mixer each).
//   GT_BASE=http://localhost:8826 node viewer/tools/invader_perf.mjs [N] [W H] [metal|swiftshader]
// Prints per mode: mean / p95 frame ms (rAF, uncapped by vsync is not possible here: rAF at 60/120 Hz,
// so CPU ms per frame is measured too), draw calls, triangles, and a screenshot in build/invader/.
import fs from 'fs';
import { chromium } from 'playwright-core';

const [N = '50', W = '1600', H = '900', gpu = 'metal'] = process.argv.slice(2);
const base = process.env.GT_BASE || 'http://localhost:8826';
fs.mkdirSync('build/invader', { recursive: true });
let slot = null;
for (let tries = 0; slot === null; tries++) {
  for (let i = 0; i < 3 && slot === null; i++) { try { fs.mkdirSync(`build/locks/browser_${i}`); slot = i; } catch {} }
  if (slot === null) { if (tries > 600) throw new Error('no browser slot'); await new Promise((r) => setTimeout(r, 2000)); }
}
const release = () => { try { fs.rmdirSync(`build/locks/browser_${slot}`); } catch {} };
process.on('exit', release);

const args = gpu === 'swiftshader' ? ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] : ['--use-angle=metal'];
const b = await chromium.launch({ channel: 'chrome', args: [...args, '--disable-gpu-vsync', '--disable-frame-rate-limit'] });
try {
  for (const mode of [`crowd=${N}`, `crowd=${N}&crowdlod=2`, `skinned=${N}`, `skinned=${N}&herdlod=1`]) {
    const p = await b.newPage({ viewport: { width: +W, height: +H } });
    p.on('pageerror', (e) => console.log('pageerror:', e.message));
    await p.goto(`${base}/viewer/invader_view.html?${mode}`);
    await p.waitForFunction(() => window.__loaded, null, { timeout: 90000 });
    await p.waitForTimeout(1500);
    const r = await p.evaluate(() => new Promise((ok) => {
      const I = window.__inv;
      const dts = [], cpu = [];
      let last = performance.now();
      const step = () => {
        const t0 = performance.now();
        dts.push(t0 - last); last = t0;
        if (dts.length < 240) requestAnimationFrame(step);
        else {
          dts.sort((a, b) => a - b);
          const info = I.renderer.info.render;
          ok({ mean: dts.reduce((a, b) => a + b, 0) / dts.length, p95: dts[Math.floor(dts.length * 0.95)], calls: info.calls, tris: info.triangles });
        }
      };
      requestAnimationFrame(step);
    }));
    // CPU cost of the animation update alone (mixers vs one uniform)
    const upd = await p.evaluate(() => {
      const I = window.__inv;
      const t0 = performance.now();
      for (let k = 0; k < 100; k++) { for (const h of I.herd) h.update(1 / 60, I.camera.position); if (I.crowd) I.crowd.update(1 / 60); }
      return (performance.now() - t0) / 100;
    });
    const shot = `build/invader/perf_${mode.replace(/[=&]/g, '_')}.png`;
    await p.screenshot({ path: shot });
    console.log(`${mode.padEnd(26)} frame ${r.mean.toFixed(2)} ms (p95 ${r.p95.toFixed(2)}), anim update ${upd.toFixed(3)} ms, ` +
      `draw calls ${r.calls}, triangles ${r.tris}  ${shot}`);
    await p.close();
  }
} finally {
  await b.close();
  release();
}
