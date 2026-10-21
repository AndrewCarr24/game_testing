// Vase: pick up from the coffee table, arm it, throw it at a wall, it shatters.
// Usage: node throw.mjs [out-dir]
import { chromium } from 'playwright-core';
import { prop, fromProp, room, url } from './level.mjs';
const out = process.argv[2] || '.';
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 1100, height: 700 } });
p.on('pageerror', (e) => console.log('pageerror:', e.message));
let fails = 0;
const check = (label, ok, detail = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}  ${detail}`); if (!ok) fails++; };

// beside the vase on the coffee table, looking down at it
const vase = prop('vase');
const office = room(vase.room);
await p.goto(url(fromProp(vase, [0.0, 0.85, 1.65]), fromProp(vase, [0, 0, 0.1])));
await p.waitForFunction(() => window.__loaded, null, { timeout: 60000 });
await p.mouse.click(550, 350); await p.waitForTimeout(500);
const S = () => p.evaluate(() => ({
  hint: document.getElementById('hint').textContent, toast: window.__toast(),
  armed: window.__inventory.armed, has: window.__inventory.has('vase'),
  flying: window.__throwables.flying.length,
  shards: window.__throwables.shards.reduce((n, g) => n + g.parts.length, 0),
  resting: window.__throwables.shards.reduce((n, g) => n + g.parts.filter((s) => s.resting).length, 0),
  lowest: Math.min(...window.__throwables.shards.flatMap((g) => g.parts.map((s) => s.p.y)), 99),
}));
const press = async (k, wait = 400) => { await p.keyboard.press(k); await p.waitForTimeout(wait); };

let s = await S();
check('vase on the table offers to be taken', s.hint.includes('Take glass vase'), `hint="${s.hint}"`);
await p.screenshot({ path: `${out}/vase_on_table.png` });
await press('KeyE'); s = await S();
check('E picks it up', s.has && s.toast.includes('Glass vase'), `toast="${s.toast}"`);
await press('KeyI', 250);
const ids = await p.evaluate(() => window.__inventory.ids());
// choose the vase with the down arrow if it isn't the first item
for (let i = 0; i < ids.indexOf('vase'); i++) { await p.keyboard.press('ArrowDown'); await p.waitForTimeout(100); }
await press('Enter'); s = await S();
check('armed from the inventory', s.armed === 'vase' && s.hint.includes('Throw glass vase'), `armed=${s.armed} hint="${s.hint}"`);
await p.screenshot({ path: `${out}/vase_in_hand.png` });

// face the room's west wall and throw
await p.evaluate(([x, y, z]) => window.__camera.lookAt(x, y, z), [office.x0, office.y + 1.5, vase.position[2]]);   // the room's west wall
await p.waitForTimeout(200);
await press('Enter', 120); s = await S();
check('Enter throws it: out of the inventory, in the air', !s.has && s.armed === null && (s.flying === 1 || s.shards > 0), `flying=${s.flying} shards=${s.shards}`);
await p.waitForTimeout(250);
await p.screenshot({ path: `${out}/vase_shatter.png` });
await p.waitForTimeout(2500); s = await S();
check('it shattered and the shards came to rest on the floor', s.shards > 20 && s.resting > s.shards * 0.8 && s.lowest > office.y - 0.01 && s.lowest < office.y + 0.1,
      `shards=${s.shards} resting=${s.resting} lowest y=${s.lowest.toFixed(3)}`);
await p.evaluate(([x, y, z]) => window.__camera.lookAt(x, y, z), [office.x0 + 0.5, office.y, vase.position[2]]);
await p.waitForTimeout(200);
await p.screenshot({ path: `${out}/vase_shards.png` });
await b.close();
console.log(fails ? `${fails} failed` : 'all passed');
process.exit(fails ? 1 : 0);
