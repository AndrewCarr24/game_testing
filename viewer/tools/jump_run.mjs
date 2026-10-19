// Play test: run (Shift+W held) and tap Space the way a person does (~70 ms), many times,
// across rooms with rugs and thresholds; report taps that didn't jump.
// Usage: node viewer/tools/jump_run.mjs
import { chromium } from 'playwright-core';
import { url } from './level.mjs';
const RUNS = [   // start eye position, look target (glTF), seconds of running
  { name: 'great room (rugs)', pos: [-16.5, 1.65, -3.5], look: [-23, 1.5, 6] },
  { name: 'entry -> gallery', pos: [0, 1.65, 18.5], look: [4.75, 1.5, 8] },
  { name: 'kitchen', pos: [-8, 1.65, -13], look: [6, 1.5, -18] },
  { name: 'office (rug edges)', pos: [1.5, 6.25, -11.5], look: [12, 6, -19] },
];
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 1100, height: 700 } });
p.on('pageerror', (e) => console.log('pageerror:', e.message));
let total = 0, missed = 0;
for (const r of RUNS) {
  await p.goto(url(r.pos, r.look));
  await p.waitForFunction(() => window.__loaded, null, { timeout: 90000 });
  await p.mouse.click(550, 350); await p.waitForTimeout(500);
  // per-frame log of grounded / vertical speed, kept in the page
  await p.evaluate(() => {
    const pl = window.__player; window.__log = [];
    const tick = () => { window.__log.push([performance.now(), pl.grounded ? 1 : 0, pl.vel.y, pl.pos.y]); requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  });
  await p.keyboard.down('ShiftLeft'); await p.keyboard.down('KeyW');
  await p.waitForTimeout(300);
  const taps = [];
  for (let i = 0; i < 6; i++) {
    await p.waitForTimeout(250 + Math.random() * 250);
    const t0 = await p.evaluate(() => performance.now());
    await p.keyboard.down('Space'); await p.waitForTimeout(70); await p.keyboard.up('Space');
    const t1 = await p.evaluate(() => performance.now());
    taps.push([t0, t1]);
    await p.waitForTimeout(650);        // let the jump land
  }
  await p.keyboard.up('KeyW'); await p.keyboard.up('ShiftLeft');
  const log = await p.evaluate(() => window.__log);
  let m = 0;
  for (const [t0, t1] of taps) {
    const during = log.filter((f) => f[0] >= t0 && f[0] <= t1 + 34);
    const jumped = log.some((f) => f[0] >= t0 && f[0] <= t1 + 50 && f[2] > 3);
    const groundedFrames = during.filter((f) => f[1]).length;
    if (!jumped) { m++; console.log(`  MISS in ${r.name}: ${during.length} frames during the tap, grounded in ${groundedFrames}`); }
  }
  const running = log.filter((f) => Math.abs(f[2]) < 0.6);   // not mid-jump
  const air = running.filter((f) => !f[1]).length;
  console.log(`${r.name}: ${taps.length - m}/${taps.length} taps jumped; not-grounded while running on the floor: ${air}/${running.length} frames`);
  total += taps.length; missed += m;
}
console.log(missed ? `${missed}/${total} taps missed` : `all ${total} taps jumped`);
await b.close();
