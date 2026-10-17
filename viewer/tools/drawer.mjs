// Checks the desk drawer: prompt + E toggle behind the desk, no prompt from the
// visitor side or far away. Usage: node drawer.mjs <out-dir>
import { chromium } from 'playwright-core';
const out = process.argv[2] || '.';
const base = 'http://localhost:8765/viewer/index.html?level=office';
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });

async function at(pos, look, label, pressE) {
  const p = await b.newPage({ viewport: { width: 1100, height: 700 } });
  p.on('pageerror', (e) => console.log('pageerror:', e.message));
  await p.goto(`${base}&pos=${pos}&look=${look}`);
  await p.waitForFunction(() => window.__loaded, null, { timeout: 60000 });
  await p.mouse.click(550, 350);
  await p.waitForTimeout(400);
  const drawerZ = () => p.evaluate(() => {
    const it = window.__interact.items[0];
    const v = it.node.getWorldPosition(new it.node.position.constructor());
    return +v.z.toFixed(3);
  });
  const hint = () => p.textContent('#hint');
  console.log(`[${label}] items=${await p.evaluate(() => window.__interact.items.length)} hint="${await hint()}" drawerZ=${await drawerZ()}`);
  if (pressE) {
    await p.keyboard.press('KeyE'); await p.waitForTimeout(900);
    console.log(`[${label}] after E: hint="${await hint()}" drawerZ=${await drawerZ()}`);
    await p.screenshot({ path: `${out}/drawer_${label.replace(/ /g, "_")}.png` });
    if ((await hint()).includes('Take')) {   // the keycard has priority while the drawer is open
      await p.keyboard.press('KeyE'); await p.waitForTimeout(300);
      console.log(`[${label}] took the card: hint="${await hint()}"`);
    }
    await p.keyboard.press('KeyE'); await p.waitForTimeout(900);
    console.log(`[${label}] after closing E: hint="${await hint()}" drawerZ=${await drawerZ()}`);
  }
  await p.close();
}

await at('-0.35,1.6,-2.45', '0.3,0.55,-1.9', 'behind desk', true);
await at('0.3,1.65,-0.55', '0.3,0.7,-1.5', 'visitor side', true);
await at('2.4,1.65,2.2', '0.3,0.7,-1.5', 'across room', true);
await b.close();
