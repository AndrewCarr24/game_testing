// Uncapped frame rate of viewer/wild_veg.html (forest mode) on Metal and SwiftShader, plus attribute checks.
//   node blender/wilderness/veg_perf.mjs [querystring]
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { chromium } from 'playwright-core';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
process.chdir(root);
const { ensureServer, BASE } = await import(path.join(root, 'viewer/tools/server.mjs'));
let slot = null;
while (slot === null) {
  for (let i = 0; i < 3 && slot === null; i++) { try { fs.mkdirSync(`build/locks/browser_${i}`); slot = i; } catch {} }
  if (slot === null) await new Promise((r) => setTimeout(r, 2000));
}
const release = () => { try { fs.rmdirSync(`build/locks/browser_${slot}`); } catch {} };
process.on('exit', release);
const stop = await ensureServer();
const qs = process.argv[2] || 'mode=forest&n=1500&wind=1';
const out = {};
try {
  for (const [prof, angle, w, h] of [['gpu', 'metal', 1600, 900], ['soft', 'swiftshader', 1280, 720]]) {
    const b = await chromium.launch({ channel: 'chrome', args: [`--use-angle=${angle}`, '--enable-unsafe-swiftshader', '--disable-gpu-vsync', '--disable-frame-rate-limit'] });
    const p = await b.newPage({ viewport: { width: w, height: h } });
    p.on('pageerror', (e) => console.log('pageerror:', e.message));
    p.on('console', (m) => { if (m.type() === 'error') console.log('console:', m.text()); });
    await p.goto(`${BASE}/viewer/wild_veg.html?${qs}`);
    await p.waitForFunction(() => window.__loaded, null, { timeout: 120000 });
    await p.waitForTimeout(1500);
    const r = await p.evaluate(async () => {
      const t = []; let last = performance.now();
      await new Promise((res) => { const f = (now) => { t.push(now - last); last = now; if (t.length < 240) requestAnimationFrame(f); else res(); }; requestAnimationFrame(f); });
      t.sort((a, b) => a - b);
      const attrs = Object.fromEntries(Object.entries(window.__veg).map(([k, v]) => [k, Object.keys(v.lods[0][0].geometry.attributes)]));
      return { p50: t[t.length >> 1], p95: t[Math.floor(t.length * 0.95)], stats: document.getElementById('stats').textContent, attrs, gl: (() => { const c = document.querySelector('canvas').getContext('webgl2'); const e = c.getExtension('WEBGL_debug_renderer_info'); return e ? c.getParameter(e.UNMASKED_RENDERER_WEBGL) : '?'; })() };
    });
    out[prof] = r;
    console.log(prof, r.gl, `p50 ${r.p50.toFixed(2)} ms  p95 ${r.p95.toFixed(2)} ms`, '\n' + r.stats);
    if (prof === 'gpu') console.log('attributes', JSON.stringify(r.attrs));
    await b.close();
  }
} finally { stop(); release(); }
fs.writeFileSync('build/wilderness/veg/previews/viewer_perf.json', JSON.stringify(out, null, 1));
