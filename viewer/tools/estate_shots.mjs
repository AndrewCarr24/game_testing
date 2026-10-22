// Screenshots for the estate <-> wilderness link (design/wilderness/estate_link.md): any list of
// page URLs (relative to GT_BASE/viewer/) into one folder, one browser slot (build/locks/browser_N).
//   node viewer/tools/estate_shots.mjs <outdir> name=url [name=url ...]   (W/H env: viewport)
// Waits for window.__loaded, hides the HUD, lets a few frames settle, then shoots the page.
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { ensureServer, BASE } from './server.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const [out, ...pairs] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
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
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
try {
  const page = await b.newPage({ viewport: { width: +(process.env.W || 1600), height: +(process.env.H || 900) } });
  page.on('pageerror', (e) => console.log('pageerror:', e.message));
  page.on('console', (m) => { if (m.type() === 'error' || process.env.LOG) console.log('console:', m.type(), m.text()); });
  for (const p of pairs) {
    const i = p.indexOf('='), name = p.slice(0, i), url = p.slice(i + 1);
    const t0 = Date.now();
    await page.goto(`${BASE}/viewer/${url}`);
    await page.waitForFunction(() => window.__loaded || /error/.test(document.getElementById('hud')?.textContent || '') || /load error/.test(document.getElementById('stats')?.textContent || ''), null, { timeout: 180000 });
    const err = await page.evaluate(() => (window.__loaded ? null : (document.getElementById('hud')?.textContent || document.getElementById('stats')?.textContent)));
    if (err) { console.log(name, 'FAILED:', err); continue; }
    if (!process.env.HUD) await page.addStyleTag({ content: 'body > *:not(canvas) { display: none !important; }' });
    await page.evaluate(() => new Promise((ok) => { let n = 30; const s = () => (n-- > 0 ? requestAnimationFrame(s) : ok()); s(); }));
    await page.waitForTimeout(+(process.env.WAIT || 300));
    await page.screenshot({ path: path.join(out, `${name}.png`) });
    console.log(name, `${Date.now() - t0} ms`);
  }
} finally { await b.close(); stop(); release(); }
