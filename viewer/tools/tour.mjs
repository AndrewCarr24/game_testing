// The floating stair: from the entry floor, up 26 steps to the upper gallery. Usage: node tour.mjs [out-dir]
import { chromium } from 'playwright-core';
import { room, url } from './level.mjs';
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
await p.keyboard.down('KeyW'); await p.waitForTimeout(5200); await p.keyboard.up('KeyW');
let s = await S();
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
