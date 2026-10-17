// Full loop: locked door -> drawer -> keycard -> unlock -> walk through. Usage: node keycard_door.mjs [out-dir]
import { chromium } from 'playwright-core';
const out = process.argv[2] || '.';
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 1100, height: 700 } });
p.on('pageerror', (e) => console.log('pageerror:', e.message));
let fails = 0;
const check = (label, ok, detail = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}  ${detail}`); if (!ok) fails++; };

// start in front of the door, inside the office (door centre is x=2.4, z=3.1; the room is z < 3.0)
await p.goto('http://localhost:8765/viewer/index.html?level=office&pos=2.4,1.65,2.1&look=2.4,1.2,3.1');
await p.waitForFunction(() => window.__loaded, null, { timeout: 60000 });
await p.mouse.click(550, 350); await p.waitForTimeout(500);

const S = () => p.evaluate(() => {
  const door = window.__interact.items.find((i) => i.def.type === 'rotate');
  const drawer = window.__interact.items.find((i) => i.def.type === 'slide');
  const card = window.__interact.items.find((i) => i.def.type === 'pickup');
  return {
    hint: document.getElementById('hint').textContent, toast: window.__toast(),
    inv: document.getElementById('inventory').textContent,
    doorT: door.t, doorLocked: door.locked, led: '#' + door.indicator.material.emissive.getHexString(),
    drawerT: drawer.t, cardTaken: card.taken, z: window.__player.pos.z,
  };
});
const teleport = (pos, look) => p.evaluate(([pos, look]) => {
  window.__player.pos.set(pos[0], 0, pos[2]); window.__player.syncCamera(); window.__camera.lookAt(...look);
}, [pos, look]);
const press = async (k, wait = 1100) => { await p.keyboard.press(k); await p.waitForTimeout(wait); };

let s = await S();
check('door starts locked with a red light', s.doorLocked === 'keycard' && s.led.startsWith('#ff'), `hint="${s.hint}" led=${s.led}`);
await press('KeyE'); s = await S();
check('E without the card: locked message, door stays shut', s.toast.startsWith('Locked') && s.doorT === 0, `toast="${s.toast}"`);
await p.screenshot({ path: `${out}/door_locked.png` });

await teleport([-0.35, 0, -2.45], [0.3, 0.55, -1.9]);    // behind the desk
await p.waitForTimeout(300); s = await S();
check('card not takeable while the drawer is shut', s.hint.includes('Open drawer'), `hint="${s.hint}"`);
await press('KeyE', 900); s = await S();
check('drawer opens and offers the card', s.drawerT === 1 && s.hint.includes('Take keycard'), `hint="${s.hint}"`);
await p.screenshot({ path: `${out}/card_in_drawer.png` });
await press('KeyE', 400); s = await S();
check('card picked up into the inventory', s.cardTaken && s.inv.includes('Keycard') && s.toast.includes('Picked up'), `inv="${s.inv}" toast="${s.toast}"`);
check('after taking it, E goes back to the drawer', s.hint.includes('Close drawer'), `hint="${s.hint}"`);

await teleport([2.4, 0, 2.1], [2.4, 1.2, 3.1]);           // back to the door
await p.waitForTimeout(300); s = await S();
check('door now offers to unlock', s.hint.includes('Unlock with keycard'), `hint="${s.hint}"`);
await press('KeyE', 1300); s = await S();
const g = parseInt(s.led.slice(3, 5), 16), r = parseInt(s.led.slice(1, 3), 16);
check('unlocks: green light, door swings fully open', !s.doorLocked && g > 2 * r && s.doorT === 1, `toast="${s.toast}" led=${s.led} t=${s.doorT}`);
await p.screenshot({ path: `${out}/door_open.png` });

await p.keyboard.down('KeyW'); await p.waitForTimeout(1000); await p.keyboard.up('KeyW');
s = await S();
check('walk through the doorway into the corridor', s.z > 3.4, `z=${s.z.toFixed(2)}`);
await p.evaluate(() => window.__camera.lookAt(2.4, 1.2, 2.0));    // turn round to face the door
await p.waitForTimeout(300); s = await S();
check('door can be closed from the corridor side', s.hint.includes('Close door'), `hint="${s.hint}"`);
await press('KeyE', 1300); s = await S();
check('door closes', s.doorT === 0, `t=${s.doorT}`);
await p.screenshot({ path: `${out}/corridor.png` });
await b.close();
console.log(fails ? `${fails} failed` : 'all passed');
process.exit(fails ? 1 : 0);
