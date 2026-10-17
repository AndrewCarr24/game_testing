// Walk the hall, open the bedroom door (unlocked, no reader), step into the bedroom.
import { chromium } from 'playwright-core';
const out = process.argv[2] || '.';
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 1100, height: 700 } });
p.on('pageerror', (e) => console.log('pageerror:', e.message));
let fails = 0;
const check = (label, ok, detail = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}  ${detail}`); if (!ok) fails++; };
// middle of the hall (glTF z 8), facing the bedroom door at the far end (z 13.3)
await p.goto('http://localhost:8765/viewer/index.html?level=mansion&pos=2.4,1.65,8.0&look=2.4,1.4,13.3');
await p.waitForFunction(() => window.__loaded, null, { timeout: 60000 });
await p.mouse.click(550, 350); await p.waitForTimeout(400);
const S = () => p.evaluate(() => ({ z: window.__player.pos.z, hint: document.getElementById('hint').textContent,
  doorT: window.__interact.items.filter((i) => i.def.type === 'rotate').map((i) => i.t) }));
await p.keyboard.down('KeyW'); await p.waitForTimeout(2200); await p.keyboard.up('KeyW');
let s = await S();
check('walk down the hall and stop at the closed bedroom door', s.z > 11.5 && s.z < 13.1, `z=${s.z.toFixed(2)} hint="${s.hint}"`);
check('the bedroom door offers to open (no keycard needed)', s.hint.includes('Open door'), `hint="${s.hint}"`);
await p.keyboard.press('KeyE'); await p.waitForTimeout(1200);
await p.keyboard.down('KeyW'); await p.waitForTimeout(1500); await p.keyboard.up('KeyW');
s = await S();
check('door opens and the player walks into the bedroom', s.z > 13.6, `z=${s.z.toFixed(2)} doors=${JSON.stringify(s.doorT)}`);
await p.screenshot({ path: `${out}/tour_bedroom.png` });
await b.close();
console.log(fails ? `${fails} failed` : 'all passed');
process.exit(fails ? 1 : 0);
