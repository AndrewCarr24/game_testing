// Desk drawer: prompt + E toggle behind the desk, no prompt from the visitor side or
// far away. Positions come from the level file. Usage: node drawer.mjs [out-dir]
import { chromium } from 'playwright-core';
import { prop, fromProp, url } from './level.mjs';
const out = process.argv[2] || '.';
const desk = prop('desk');
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });

async function at(pos, look, label, pressE) {
  const p = await b.newPage({ viewport: { width: 1100, height: 700 } });
  p.on('pageerror', (e) => console.log('pageerror:', e.message));
  await p.goto(url(pos, look));
  await p.waitForFunction(() => window.__loaded, null, { timeout: 60000 });
  await p.mouse.click(550, 350);
  await p.waitForTimeout(400);
  const drawer = () => p.evaluate(() => {
    const it = window.__interact.items.find((i) => i.node.name === 'Desk_Drawer');
    return +it.t.toFixed(2);
  });
  const hint = () => p.textContent('#hint');
  console.log(`[${label}] hint="${await hint()}" drawer=${await drawer()}`);
  if (pressE) {
    await p.keyboard.press('KeyE'); await p.waitForTimeout(900);
    console.log(`[${label}] after E: hint="${await hint()}" drawer=${await drawer()}`);
    await p.screenshot({ path: `${out}/drawer_${label.replace(/ /g, '_')}.png` });
    if ((await hint()).includes('Take')) {   // the keycard has priority while the drawer is open
      await p.keyboard.press('KeyE'); await p.waitForTimeout(300);
      console.log(`[${label}] took the card: hint="${await hint()}"`);
    }
    await p.keyboard.press('KeyE'); await p.waitForTimeout(900);
    console.log(`[${label}] after closing E: hint="${await hint()}" drawer=${await drawer()}`);
  }
  await p.close();
}

await at(fromProp(desk, [-0.65, 0.95, 1.6]), fromProp(desk, [0, 0.43, 0.55]), 'behind desk', true);
await at(fromProp(desk, [0, -1.25, 1.65]), fromProp(desk, [0, 0, 0.7]), 'visitor side', true);
await at(fromProp(desk, [-3, -5.5, 1.65]), fromProp(desk, [0, 0, 0.7]), 'across room', true);
await b.close();
