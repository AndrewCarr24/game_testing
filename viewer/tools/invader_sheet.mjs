// Contact sheet of the invader (viewer/invader_view.html): clips at given times from given views,
// rendered in one page and composed into one PNG.
//   GT_BASE=http://localhost:8826 node viewer/tools/invader_sheet.mjs out.png "<spec>" [cols] [query]
// spec: ';'-separated cells "Clip@t1,t2,...:view[:upper]" (t = seconds, or 'f0.25' = fraction of
// the clip); a cell per time. view: front side back three head hands feet far.
// Example: "Walk@f0,f0.25,f0.5,f0.75:side;Idle@0:front"
import fs from 'fs';
import { chromium } from 'playwright-core';

const [out = 'build/invader/sheet.png', spec = 'Idle@0:three', cols = '6', qs = ''] = process.argv.slice(2);
const base = process.env.GT_BASE || 'http://localhost:8826';
fs.mkdirSync(out.split('/').slice(0, -1).join('/') || '.', { recursive: true });

let slot = null;
for (let tries = 0; slot === null; tries++) {
  for (let i = 0; i < 3 && slot === null; i++) { try { fs.mkdirSync(`build/locks/browser_${i}`); slot = i; } catch {} }
  if (slot === null) { if (tries > 600) throw new Error('no browser slot'); await new Promise((r) => setTimeout(r, 2000)); }
}
const release = () => { try { fs.rmdirSync(`build/locks/browser_${slot}`); } catch {} };
process.on('exit', release);

const cells = [];
for (const part of spec.split(';').filter(Boolean)) {
  const [ct, view = 'three', upper = '', opts = ''] = part.split(':');
  const [clip, times = '0'] = ct.split('@');
  for (const t of times.split(',')) cells.push({ clip, t, view, upper, opts });
}
const W = 360, H = 460;
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
try {
  const p = await b.newPage({ viewport: { width: W, height: H } });
  p.on('pageerror', (e) => console.log('pageerror:', e.message));
  p.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log('console:', m.text()); });
  await p.goto(`${base}/viewer/invader_view.html?t=0${qs ? '&' + qs : ''}`);
  await p.waitForFunction(() => window.__loaded, null, { timeout: 90000 });
  await p.evaluate(() => { document.getElementById('ui').style.display = 'none'; document.getElementById('stats').style.display = 'none'; });
  const shots = [];
  for (const c of cells) {
    const url = await p.evaluate(({ clip, t, view, upper, opts }) => {
      const I = window.__inv;
      const o = Object.fromEntries(opts.split(',').filter(Boolean).map((kv) => kv.split('=')));
      I.inv.setOutfit(o.outfit || I.asset.defaultOutfit());
      I.inv.setHead(o.head || 'none');
      I.inv.setWeapon(o.weapon || null);
      I.setLod(o.lod ? +o.lod : 0);
      const dur = I.asset.clips[clip]?.duration ?? 0;
      const time = t.startsWith('f') ? parseFloat(t.slice(1)) * dur : parseFloat(t);
      I.pose(clip, time, upper || null);
      I.view(view);
      I.renderer.render(I.scene, I.camera);
      return I.renderer.domElement.toDataURL('image/png');
    }, c);
    shots.push({ ...c, url });
  }
  const n = +cols;
  const rows = Math.ceil(shots.length / n);
  const sheet = await b.newPage({ viewport: { width: W * n, height: H * rows } });
  await sheet.setContent(`<body style="margin:0;background:#111;display:grid;grid-template-columns:repeat(${n},${W}px)">` +
    shots.map((s) => `<div style="position:relative;width:${W}px;height:${H}px"><img src="${s.url}" style="width:${W}px;height:${H}px;display:block">` +
      `<span style="position:absolute;left:6px;top:4px;color:#fff;font:13px sans-serif;text-shadow:0 0 3px #000">${s.clip}${s.upper ? '|' + s.upper : ''} @${s.t} ${s.view} ${s.opts}</span></div>`).join('') + '</body>');
  await sheet.waitForTimeout(300);
  await sheet.screenshot({ path: out, fullPage: true });
  console.log('SHEET', out, shots.length, 'cells');
} finally {
  await b.close();
  release();
}
