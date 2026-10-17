// Download size + render cost of a level. Usage: node perf.mjs <url> [width height pixelRatio]
import { chromium } from 'playwright-core';
const [url, w = 1600, h = 900, dpr = 2] = process.argv.slice(2);
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const ctx = await b.newContext({ viewport: { width: +w, height: +h }, deviceScaleFactor: +dpr });
const p = await ctx.newPage();
let bytes = 0; const files = {};
p.on('response', async (r) => {
  if (!r.url().includes('localhost')) return;
  try { const n = (await r.body()).length; bytes += n; files[r.url().split('/').pop().split('?')[0]] = n; } catch {}
});
await p.goto(url);
await p.waitForFunction(() => window.__loaded, null, { timeout: 90000 });
await p.waitForTimeout(1000);
const r = await p.evaluate(() => {
  const { renderer, scene, camera } = window.__three;
  const gl = renderer.getContext();
  const px = renderer.getDrawingBufferSize(new (camera.position.constructor.prototype.constructor.__proto__.constructor === Object ? Object : camera.position.constructor)());
  renderer.info.autoReset = false; renderer.info.reset();
  renderer.render(scene, camera);
  const calls = renderer.info.render.calls, tris = renderer.info.render.triangles;
  renderer.info.autoReset = true;
  // texture memory estimate: every texture uploaded, w*h*4 bytes * 4/3 for mips
  const seen = new Set(); let texBytes = 0;
  scene.traverse((o) => { if (!o.material) return; for (const k of Object.keys(o.material)) {
    const t = o.material[k]; if (t && t.isTexture && t.image && !seen.has(t)) { seen.add(t);
      const im = t.image; texBytes += (im.width || 0) * (im.height || 0) * 4 * 1.33; } } });
  for (let i = 0; i < 5; i++) { renderer.render(scene, camera); } gl.finish();
  const t0 = performance.now(); const N = 60;
  for (let i = 0; i < N; i++) { renderer.render(scene, camera); } gl.finish();
  const ms = (performance.now() - t0) / N;
  return { calls, tris, textures: seen.size, texMB: +(texBytes / 1e6).toFixed(1), msPerFrame: +ms.toFixed(2),
           buffer: `${gl.drawingBufferWidth}x${gl.drawingBufferHeight}`, shadowAuto: renderer.shadowMap.autoUpdate };
});
console.log(JSON.stringify({ downloadMB: +(bytes / 1e6).toFixed(2), ...r }));
console.log(Object.entries(files).sort((a, c) => c[1] - a[1]).slice(0, 12).map(([k, v]) => `${k} ${(v / 1e6).toFixed(2)}MB`).join(' | '));
await b.close();
