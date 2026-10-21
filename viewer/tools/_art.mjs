import { chromium } from 'playwright-core';
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 400, height: 300 } });
await p.goto((process.env.GT_BASE || 'http://localhost:8765') + '/viewer/index.html?level=mansion&grimble=0');
await p.waitForFunction(() => window.__loaded, null, { timeout: 90000 });
console.log(await p.evaluate(() => { const out = []; window.__three.scene.traverse((o) => { if (o.isMesh && /entry.*_Art$|dining_M_Art.*_Art$/.test(o.name)) { const m = o.material, g = o.geometry; const uv1 = g.attributes.uv1; let mn = [9, 9], mx = [-9, -9]; if (uv1) for (let i = 0; i < uv1.count; i++) { mn[0] = Math.min(mn[0], uv1.getX(i)); mn[1] = Math.min(mn[1], uv1.getY(i)); mx[0] = Math.max(mx[0], uv1.getX(i)); mx[1] = Math.max(mx[1], uv1.getY(i)); }
  out.push(`${o.name} vis=${o.visible} map=${m.map?.name} img=${m.map?.image?.width} lm=${!!m.lightMap} lmI=${m.lightMapIntensity} col=${m.color?.getHexString()} uv1 ${mn.map((v) => v.toFixed(3))}..${mx.map((v) => v.toFixed(3))} emis=${m.emissive?.getHexString()}`); } }); return out.join('\n'); }));
await b.close();
