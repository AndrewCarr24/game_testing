// Before/after report for the quality loop: cost metrics side by side with the budgets,
// and a pixel diff per screenshot. Writes build/bench/<after>/compare.html: flip between
// before and after with the space bar (D = diff heatmap, arrows = previous/next view).
//
// Usage: node viewer/tools/compare.mjs [before=baseline] [after=latest]
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { ensureServer, BASE } from './server.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../..');
const [before = 'baseline', after = 'latest'] = process.argv.slice(2);
const dirOf = (l) => path.join(root, 'build/bench', l);
const budgets = JSON.parse(fs.readFileSync(path.join(here, 'budgets.json'), 'utf8'));
const get = (o, k) => k.split('.').reduce((v, p) => (v == null ? v : v[p]), o);

// ---------------------------------------------------------------- numbers
const METRICS = [
  ['fps', 'fps', +1], ['frameMs.p95', 'frame p95 ms', -1], ['gpuMs.p95', 'GPU p95 ms', -1], ['gpuMs.p50', 'GPU p50 ms', -1],
  ['hitches', 'hitches >50 ms', -1], ['drawCalls.mean', 'draw calls mean', -1], ['drawCalls.max', 'draw calls max', -1],
  ['triangles.max', 'triangles max', -1], ['load.downloadMB', 'download MB', -1], ['load.textureMB', 'textures MB', -1],
  ['load.seconds', 'load s', -1],
];
const rows = [];
for (const prof of ['gpu', 'soft']) {
  const f = (l) => path.join(dirOf(l), `stats-${prof}.json`);
  if (!fs.existsSync(f(before)) || !fs.existsSync(f(after))) continue;
  const A = JSON.parse(fs.readFileSync(f(before))), B = JSON.parse(fs.readFileSync(f(after)));
  for (const [k, name, better] of METRICS) {
    const a = get(A, k), b = get(B, k), limit = budgets[prof]?.[k];
    if (a == null && b == null) continue;
    const delta = a ? ((b - a) / a) * 100 : 0;
    rows.push({ prof, name, a, b, delta, better, limit, ok: limit == null || (b != null && b <= limit) });
  }
}

// ---------------------------------------------------------------- pixels
const shotsA = path.join(dirOf(before), 'shots'), shotsB = path.join(dirOf(after), 'shots');
const names = fs.existsSync(shotsA) && fs.existsSync(shotsB)
  ? fs.readdirSync(shotsB).filter((n) => n.endsWith('.png') && fs.existsSync(path.join(shotsA, n))).map((n) => n.slice(0, -4)) : [];
const diffDir = path.join(dirOf(after), `diff-${before}`);
fs.mkdirSync(diffDir, { recursive: true });
const stop = await ensureServer();
const b = await chromium.launch({ channel: 'chrome' });
const page = await b.newPage();
await page.goto(`${BASE}/build/bench/`);
const diffs = [];
for (const n of names) {
  const r = await page.evaluate(async ([ua, ub]) => {
    const load = (u) => new Promise((ok, no) => { const i = new Image(); i.onload = () => ok(i); i.onerror = no; i.src = u; });
    const [ia, ib] = await Promise.all([load(ua), load(ub)]);
    const w = ia.width, h = ia.height;
    const px = (img) => { const c = new OffscreenCanvas(w, h); const g = c.getContext('2d'); g.drawImage(img, 0, 0, w, h); return g.getImageData(0, 0, w, h).data; };
    const a = px(ia), bb = px(ib);
    const out = new OffscreenCanvas(w, h), g = out.getContext('2d'), od = g.createImageData(w, h);
    let sum = 0, changed = 0;
    for (let i = 0; i < a.length; i += 4) {
      const d = Math.max(Math.abs(a[i] - bb[i]), Math.abs(a[i + 1] - bb[i + 1]), Math.abs(a[i + 2] - bb[i + 2]));
      sum += d; if (d > 12) changed++;
      // heatmap over a dimmed copy of the after image: red = changed
      const grey = (bb[i] + bb[i + 1] + bb[i + 2]) / 12;
      const k = Math.min(1, d / 48);
      od.data[i] = grey + (255 - grey) * k; od.data[i + 1] = grey * (1 - k); od.data[i + 2] = grey * (1 - k); od.data[i + 3] = 255;
    }
    g.putImageData(od, 0, 0);
    const blob = await out.convertToBlob({ type: 'image/png' });
    const buf = new Uint8Array(await blob.arrayBuffer());
    let s = ''; for (let i = 0; i < buf.length; i += 0x8000) s += String.fromCharCode(...buf.subarray(i, i + 0x8000));
    return { mean: sum / (a.length / 4), changed: changed / (a.length / 4), png: btoa(s) };
  }, [`${BASE}/build/bench/${before}/shots/${n}.png`, `${BASE}/build/bench/${after}/shots/${n}.png`]);
  fs.writeFileSync(path.join(diffDir, `${n}.png`), Buffer.from(r.png, 'base64'));
  diffs.push({ name: n, mean: +r.mean.toFixed(2), changed: +(r.changed * 100).toFixed(1) });
}
await b.close();
stop();
diffs.sort((x, y) => y.changed - x.changed);

// ---------------------------------------------------------------- console + html
for (const r of rows) {
  const d = r.a ? `${r.delta >= 0 ? '+' : ''}${r.delta.toFixed(1)}%` : '';
  console.log(`${r.ok ? '     ' : 'OVER '} [${r.prof}] ${r.name.padEnd(16)} ${String(r.a).padStart(9)} -> ${String(r.b).padStart(9)}  ${d.padStart(7)}${r.limit != null ? `  (budget ${r.limit})` : ''}`);
}
console.log(`views changed (pixels differing > 12/255): ${diffs.map((d) => `${d.name} ${d.changed}%`).join(', ') || 'none'}`);

const rel = (l) => path.relative(dirOf(after), path.join(dirOf(l), 'shots')).split(path.sep).join('/');
const html = `<!doctype html><html><head><meta charset="utf-8"><title>${before} vs ${after}</title>
<style>
:root { color-scheme: dark; --bg: #121315; --panel: #1c1e21; --text: #e6e6e6; --dim: #8b9096; --bad: #ff6b5e; --good: #6bd38a; --accent: #f2c14e; }
* { box-sizing: border-box; } body { margin: 0; background: var(--bg); color: var(--text); font: 14px/1.4 -apple-system, system-ui, sans-serif; }
header { padding: 14px 20px; display: flex; gap: 24px; align-items: baseline; flex-wrap: wrap; }
h1 { font-size: 16px; margin: 0; } .dim { color: var(--dim); }
table { border-collapse: collapse; margin: 0 20px 12px; font-variant-numeric: tabular-nums; }
td, th { padding: 3px 12px; text-align: right; border-bottom: 1px solid #26292d; } th { color: var(--dim); font-weight: 500; } td:first-child, th:first-child { text-align: left; }
.over { color: var(--bad); font-weight: 600; } .better { color: var(--good); } .worse { color: var(--bad); }
main { display: grid; grid-template-columns: 1fr 240px; gap: 12px; padding: 0 20px 20px; }
#stage { position: relative; background: #000; } #stage img { width: 100%; display: block; }
#tag { position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,.7); padding: 4px 10px; border-radius: 4px; font-weight: 600; }
#tag.after { color: var(--accent); }
nav { max-height: 80vh; overflow: auto; } nav div { padding: 6px 8px; border-radius: 4px; cursor: pointer; display: flex; justify-content: space-between; }
nav div.sel { background: var(--panel); outline: 1px solid #3a3e44; } nav span { color: var(--dim); }
kbd { background: var(--panel); border: 1px solid #3a3e44; border-radius: 3px; padding: 0 5px; }
@media (max-width: 800px) { main { grid-template-columns: 1fr; } }
</style></head><body>
<header><h1>${before} → ${after}</h1><span class="dim"><kbd>space</kbd> before / after · <kbd>D</kbd> diff · <kbd>←</kbd><kbd>→</kbd> view</span></header>
<table><tr><th>metric</th><th>profile</th><th>${before}</th><th>${after}</th><th>change</th><th>budget</th></tr>
${rows.map((r) => {
  const cls = !r.a || Math.abs(r.delta) < 3 ? '' : (r.delta * r.better > 0 ? 'better' : 'worse');
  return `<tr><td>${r.name}</td><td>${r.prof}</td><td>${r.a ?? ''}</td><td class="${r.ok ? '' : 'over'}">${r.b ?? ''}</td><td class="${cls}">${r.a ? (r.delta >= 0 ? '+' : '') + r.delta.toFixed(1) + '%' : ''}</td><td>${r.limit ?? ''}</td></tr>`;
}).join('')}</table>
<main><div id="stage"><img id="img"><div id="tag"></div></div>
<nav id="nav">${diffs.map((d, i) => `<div data-i="${i}">${d.name}<span>${d.changed}%</span></div>`).join('')}</nav></main>
<script>
const views = ${JSON.stringify(diffs.map((d) => d.name))};
const src = { before: (n) => '${rel(before)}/' + n + '.png', after: (n) => '${rel(after)}/' + n + '.png', diff: (n) => 'diff-${before}/' + n + '.png' };
let i = 0, mode = 'after';
const img = document.getElementById('img'), tag = document.getElementById('tag');
function show() {
  const n = views[i]; if (!n) return;
  img.src = src[mode](n); tag.textContent = n + ' · ' + (mode === 'before' ? '${before}' : mode === 'after' ? '${after}' : 'diff');
  tag.className = mode;
  document.querySelectorAll('nav div').forEach((d) => d.classList.toggle('sel', +d.dataset.i === i));
}
for (const n of views) for (const k of ['before', 'after']) new Image().src = src[k](n);   // preload so flipping is instant
addEventListener('keydown', (e) => {
  if (e.code === 'Space') { mode = mode === 'after' ? 'before' : 'after'; e.preventDefault(); }
  else if (e.code === 'KeyD') mode = mode === 'diff' ? 'after' : 'diff';
  else if (e.code === 'ArrowRight' || e.code === 'ArrowDown') { i = (i + 1) % views.length; e.preventDefault(); }
  else if (e.code === 'ArrowLeft' || e.code === 'ArrowUp') { i = (i - 1 + views.length) % views.length; e.preventDefault(); }
  else return;
  show();
});
document.getElementById('nav').addEventListener('click', (e) => { const d = e.target.closest('div[data-i]'); if (d) { i = +d.dataset.i; show(); } });
img.addEventListener('click', () => { mode = mode === 'after' ? 'before' : 'after'; show(); });
show();
</script></body></html>`;
fs.writeFileSync(path.join(dirOf(after), 'compare.html'), html);
console.log(`report: ${BASE}/build/bench/${after}/compare.html`);
