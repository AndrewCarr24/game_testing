import { chromium } from 'playwright-core';
const [url, angle, w, h, dpr] = process.argv.slice(2);
const b = await chromium.launch({ channel: 'chrome', args: [`--use-angle=${angle}`, '--enable-unsafe-swiftshader', '--disable-gpu-vsync', '--disable-frame-rate-limit'] });
const ctx = await b.newContext({ viewport: { width: +w, height: +h }, deviceScaleFactor: +dpr });
const p = await ctx.newPage();
await p.goto(url);
await p.waitForFunction(() => window.__loaded, null, { timeout: 120000 });
await p.waitForTimeout(1500);
const r = await p.evaluate(() => new Promise((ok) => {
  const gl = window.__three.renderer.getContext();
  const dbg = gl.getExtension('WEBGL_debug_renderer_info');
  const gpu = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : '?';
  let n = 0; const t0 = performance.now();
  const tick = () => { n++; if (performance.now() - t0 < 4000) requestAnimationFrame(tick); else ok({ fps: +(n / ((performance.now() - t0) / 1000)).toFixed(1), gpu }); };
  requestAnimationFrame(tick);
}));
console.log(JSON.stringify(r));
await b.close();
