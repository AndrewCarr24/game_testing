// The floating stair: from the entry floor, up 26 steps to the upper gallery. Usage: node tour.mjs [out-dir]
import { chromium } from 'playwright-core';
import { level, room, url } from './level.mjs';
const out = process.argv[2] || '.';
const upper = room('ugallery_s');
// stair runs along the entry's north wall (glTF z ≈ 11.85) from x = -6 (bottom) east to x = 1.5
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 1100, height: 700 } });
p.on('pageerror', (e) => console.log('pageerror:', e.message));
let fails = 0;
const check = (label, ok, detail = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}  ${detail}`); if (!ok) fails++; };
await p.goto(url([-7.2, 1.65, 11.85], [3.0, 3.0, 11.85]));
await p.waitForFunction(() => window.__loaded, null, { timeout: 60000 });
await p.mouse.click(550, 350); await p.waitForTimeout(400);
const S = () => p.evaluate(() => window.__player.pos.toArray());
await p.screenshot({ path: `${out}/stair_bottom.png` });
// per-frame trace of the feet while on the stair: the climb must be a glide along the slope
// (the invisible ramp), not an 18 cm pop per tread, and the way down must never leave the ground
const trace = () => p.evaluate(() => {
  window.__trace = [];
  const tick = () => { const pl = window.__player; window.__trace.push([pl.pos.x, pl.pos.y, pl.grounded]); window.__traceRaf = requestAnimationFrame(tick); };
  tick();
});
const stopTrace = () => p.evaluate(() => { cancelAnimationFrame(window.__traceRaf); return window.__trace; });
const ramp = level.ramps[0];
const slope = (ramp.y[1] - ramp.y[0]) / (ramp.x[1] - ramp.x[0]);
const onStair = (t) => t.filter(([x]) => x > ramp.x[0] + 0.3 && x < ramp.x[1] - 0.3);
const jolt = (t) => Math.max(0, ...t.slice(1).map(([x, y], i) => Math.abs((y - t[i][1]) - slope * (x - t[i][0]))));
// walk until past the top step (by position, so the test doesn't depend on walking speed)
await trace();
await p.keyboard.down('ShiftLeft'); await p.keyboard.down('KeyW');
await p.waitForFunction(() => window.__player.pos.x > 2.5, null, { timeout: 15000 }).catch(() => {});
await p.keyboard.up('KeyW'); await p.keyboard.up('ShiftLeft'); await p.waitForTimeout(300);
const up = onStair(await stopTrace());
let s = await S();
check('run up the stair to the landing', Math.abs(s[1] - upper.y) < 0.05 && s[0] > 1.4, `feet=${s[1].toFixed(2)} x=${s[0].toFixed(2)}`);
check('the climb is smooth', up.length > 10 && jolt(up) < 0.03, `${up.length} frames, worst off-slope jump ${jolt(up).toFixed(3)} m`);
// back down (camera west), then up again
await p.evaluate(([x, y, z]) => window.__camera.lookAt(x, y, z), [-20, s[1] + 1.0, 11.85]);
await trace();
await p.keyboard.down('KeyW');
await p.waitForFunction(() => window.__player.pos.x < -6.8, null, { timeout: 15000 }).catch(() => {});
await p.keyboard.up('KeyW'); await p.waitForTimeout(300);
const down = onStair(await stopTrace());
s = await S();
check('walk down to the entry floor', Math.abs(s[1]) < 0.05, `feet=${s[1].toFixed(2)} x=${s[0].toFixed(2)}`);
check('the descent is smooth and grounded', down.length > 10 && jolt(down) < 0.03 && down.every((f) => f[2]),
  `${down.length} frames, worst ${jolt(down).toFixed(3)} m, airborne frames ${down.filter((f) => !f[2]).length}`);
await p.evaluate(([x, y, z]) => window.__camera.lookAt(x, y, z), [20, 3.0, 11.85]);
await p.keyboard.down('KeyW');
await p.waitForFunction(() => window.__player.pos.x > 2.5, null, { timeout: 15000 }).catch(() => {});
await p.keyboard.up('KeyW'); await p.waitForTimeout(300);
s = await S();
check('walk up the stair to the landing', Math.abs(s[1] - upper.y) < 0.05 && s[0] > 1.4, `feet=${s[1].toFixed(2)} x=${s[0].toFixed(2)}`);
// turn north (glTF -z) and step off the landing into the upper gallery
await p.evaluate(([x, y, z]) => window.__camera.lookAt(x, y, z), [s[0], upper.y + 1.6, upper.cz - 5]);
await p.keyboard.down('KeyW'); await p.waitForTimeout(1000); await p.keyboard.up('KeyW');
s = await S();
check('step off the landing into the upper gallery', s[2] < upper.z1 - 0.3 && Math.abs(s[1] - upper.y) < 0.05, `z=${s[2].toFixed(2)} (gallery ${upper.z0}..${upper.z1})`);
await p.evaluate(([x, y, z]) => window.__camera.lookAt(x, y, z), [0, 2.0, 16]);
await p.waitForTimeout(200);
await p.screenshot({ path: `${out}/stair_top.png` });
await b.close();
console.log(fails ? `${fails} failed` : 'all passed');
process.exit(fails ? 1 : 0);
