import { chromium } from 'playwright-core';
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 1000, height: 700 } });
// look from the spawn straight at the far lounge chair (glTF x=-0.65, z=1.0) and walk into it
await p.goto('http://localhost:8765/viewer/index.html?level=office&pos=2.4,1.65,1.0&look=-3,1.65,1.0');
await p.waitForFunction(() => window.__loaded, null, { timeout: 60000 });
await p.mouse.click(500, 350);
await p.waitForTimeout(300);
const pos = () => p.evaluate(() => window.__camera.position.toArray().map((v) => +v.toFixed(2)));
console.log('locked:', await p.evaluate(() => !!document.pointerLockElement), 'start', await pos());
await p.keyboard.down('KeyW'); await p.waitForTimeout(3000); await p.keyboard.up('KeyW');
console.log('after 3s W toward chair:', await pos());
await b.close();
