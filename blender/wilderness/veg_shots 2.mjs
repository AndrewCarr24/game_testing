// Screenshots of viewer/wild_veg.html for the vegetation spike doc (build/wilderness/veg/previews/viewer_*.png).
//   node blender/wilderness/veg_shots.mjs [name=querystring ...]
// Takes one of the shared browser slots build/locks/browser_0..2; serves the project on :8765 if needed.
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
const shots = process.argv.slice(2).length ? process.argv.slice(2) : [
  'fir_row=species=fir&mode=row&dist=26&wind=0',
  'ash_row=species=ash&mode=row&dist=24&wind=0',
  'shrub_row=species=shrub&mode=row&dist=5&wind=0',
  'fern_row=species=fern&mode=row&dist=3&wind=0',
  'fir_imp_close=species=fir&mode=single&lod=3&dist=22&wind=0',
  'fir_lod0_close=species=fir&mode=single&lod=0&dist=22&wind=0',
  'forest=mode=forest&n=1500&wind=0',
];
const out = 'build/wilderness/veg/previews';
fs.mkdirSync(out, { recursive: true });
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal', '--enable-unsafe-swiftshader'] });
const results = {};
try {
  for (const s of shots) {
    const [name, qs] = s.split(/=(.*)/s);
    const vw = /(^|&)vw=(\d+)/.exec(qs), vh = /(^|&)vh=(\d+)/.exec(qs);
    const p = await b.newPage({ viewport: { width: vw ? +vw[2] : 1600, height: vh ? +vh[2] : 900 } });
    p.on('pageerror', (e) => console.log('pageerror:', e.message));
    p.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log('console:', m.text()); });
    await p.goto(`${BASE}/viewer/wild_veg.html?${qs}`);
    await p.waitForFunction(() => window.__loaded || document.getElementById('stats').textContent.startsWith('load error'), null, { timeout: 90000 });
    await p.waitForTimeout(/(^|&)wait=(\d+)/.exec(qs)?.[2] ? +/(^|&)wait=(\d+)/.exec(qs)[2] : 2500);
    const stats = await p.textContent('#stats');
    results[name] = stats;
    console.log(name, '\n' + stats);
    const crop = /(^|&)crop=(\d+)/.exec(qs);      // crop=N: an N x N square from the centre (distant single trees)
    const full = /(^|&)full=1/.test(qs);           // full=1: the whole page (mode=sheet)
    const file = name.includes('/') ? name : `${out}/viewer_${name}.png`;
    await p.screenshot({ path: file, fullPage: full, ...(crop ? { clip: { x: 800 - crop[2] / 2, y: 450 - crop[2] / 2, width: +crop[2], height: +crop[2] } } : {}) });
    await p.close();
  }
} finally {
  await b.close(); stop(); release();
}
fs.writeFileSync(`${out}/viewer_stats.json`, JSON.stringify(results, null, 1));
