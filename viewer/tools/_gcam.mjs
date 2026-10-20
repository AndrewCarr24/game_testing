// screenshots of the standing Grimble from free camera positions (outside the house, no physics)
import { chromium } from 'playwright-core';
const [out, ...views] = process.argv.slice(2);
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 1000, height: 640 } });
p.on('pageerror', (e) => console.log('pageerror:', e.message));
await p.goto(`http://localhost:8765/viewer/index.html?level=mansion&grimble=-32,0,90,0&fx=${process.env.FX ?? 0}`);
await p.waitForFunction(() => window.__loaded, null, { timeout: 90000 });
let i = 0;
for (const v of views) {
  const [px, py, pz, lx, ly, lz] = v.split(',').map(Number);
  await p.evaluate(([px, py, pz, lx, ly, lz]) => {
    const c = window.__camera;
    window.__bench = { frameStart() {}, drive() { c.position.set(px, py, pz); c.lookAt(lx, ly, lz); }, renderStart() {}, frameEnd() {} };
  }, [px, py, pz, lx, ly, lz]);
  await p.waitForTimeout(600);
  await p.screenshot({ path: `${out}_${++i}.png` });
}
await b.close();
