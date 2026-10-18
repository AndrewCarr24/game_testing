// Full loop: the primary bedroom door is locked -> office desk drawer -> keycard ->
// arm it -> unlock -> open -> walk in -> close and lock again. Usage: node keycard_door.mjs [out-dir]
import { chromium } from 'playwright-core';
import { level, prop, fromProp, url } from './level.mjs';
const out = process.argv[2] || '.';
const door = level.props.find((p) => p.lock === 'keycard');
const desk = prop('desk');
// the locked door swings toward its local +y (the gallery); stand 1.6 m out on that side
const front = fromProp(door, [0.0, 1.6, 1.65]);
const doorLook = fromProp(door, [0.55, 0, 1.2]);
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 1100, height: 700 } });
p.on('pageerror', (e) => console.log('pageerror:', e.message));
let fails = 0;
const check = (label, ok, detail = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}  ${detail}`); if (!ok) fails++; };

await p.goto(url(front, doorLook));
await p.waitForFunction(() => window.__loaded, null, { timeout: 60000 });
await p.mouse.click(550, 350); await p.waitForTimeout(500);
const S = () => p.evaluate(() => {
  const door = window.__interact.items.find((i) => i.lockKey === 'keycard');
  const drawer = window.__interact.items.find((i) => i.node.name === 'Desk_Drawer');
  const card = window.__interact.items.find((i) => i.def.item === 'keycard');
  return {
    hint: document.getElementById('hint').textContent, toast: window.__toast(),
    inv: document.getElementById('inventory').textContent,
    doorT: door.t, doorLocked: door.locked, led: '#' + door.indicator.material.emissive.getHexString(),
    drawerT: drawer.t, cardTaken: card.taken, pos: window.__player.pos.toArray(),
  };
});
const teleport = (pos, look) => p.evaluate(([pos, look]) => {
  window.__player.pos.set(pos[0], pos[1] - 1.65, pos[2]); window.__player.vel.set(0, 0, 0);
  window.__player.syncCamera(); window.__camera.lookAt(...look);
}, [pos, look]);
const press = async (k, wait = 1100) => { await p.keyboard.press(k); await p.waitForTimeout(wait); };
const dist = (a, c) => Math.hypot(a[0] - c[0], a[2] - c[2]);

let s = await S();
check('bedroom door starts locked with a red light', s.doorLocked === true && s.led.startsWith('#ff'), `hint="${s.hint}" led=${s.led}`);
await press('KeyE'); s = await S();
check('E without the card: locked message, door stays shut', s.toast.startsWith('Locked') && s.doorT === 0, `toast="${s.toast}"`);
await p.screenshot({ path: `${out}/door_locked.png` });

await teleport(fromProp(desk, [-0.65, 0.95, 1.6]), fromProp(desk, [0, 0.43, 0.55]));   // behind the office desk
await p.waitForTimeout(300); s = await S();
check('card not takeable while the drawer is shut', s.hint.includes('Open drawer'), `hint="${s.hint}"`);
await press('KeyE', 900); s = await S();
check('drawer opens and offers the card', s.drawerT === 1 && s.hint.includes('Take keycard'), `hint="${s.hint}"`);
await p.screenshot({ path: `${out}/card_in_drawer.png` });
await press('KeyE', 400); s = await S();
check('card picked up into the inventory', s.cardTaken && s.inv.includes('Keycard') && s.toast.includes('Picked up'), `inv="${s.inv}" toast="${s.toast}"`);

await teleport(front, doorLook);
await p.waitForTimeout(300);
await press('KeyE', 400); s = await S();
check('carrying the card but not armed: told to arm it', s.toast.includes('arm the keycard') && s.doorLocked, `toast="${s.toast}"`);
await press('KeyI', 300);
const panel = await p.evaluate(() => document.getElementById('inv-panel').classList.contains('open'));
await press('Enter', 400); s = await S();
const armed = await p.evaluate(() => window.__inventory.armed);
check('I opens the inventory, Enter arms the keycard', panel && armed === 'keycard' && s.inv.includes('ARMED'), `armed=${armed}`);
check('armed card at the door offers Enter to unlock', s.hint.includes('Enter · Unlock door'), `hint="${s.hint}"`);
await press('Enter', 400); s = await S();
const g = parseInt(s.led.slice(3, 5), 16), r = parseInt(s.led.slice(1, 3), 16);
check('Enter unlocks: green light, door still shut', !s.doorLocked && g > 2 * r && s.doorT === 0, `toast="${s.toast}" led=${s.led}`);
await press('KeyE', 1300); s = await S();
check('E then opens it', s.doorT === 1, `t=${s.doorT}`);
await p.screenshot({ path: `${out}/door_open.png` });

// walk through: toward the door's local -y (into the bedroom)
const inside = fromProp(door, [0.0, -1.5, 1.65]);
await p.evaluate((t) => window.__camera.lookAt(t[0], t[1], t[2]), inside);
// ~3 m, whatever the walking speed (close enough to the door to reach it from inside)
const walkMs = (3.0 / (await p.evaluate(() => window.__player.o.walk))) * 1000;
await p.keyboard.down('KeyW'); await p.waitForTimeout(walkMs); await p.keyboard.up('KeyW');
s = await S();
check('walk through the doorway into the bedroom', dist(s.pos, inside) < dist(s.pos, front) && dist(s.pos, front) > 2.0,
      `${dist(s.pos, front).toFixed(2)} m from the gallery spot`);
await p.evaluate((t) => window.__camera.lookAt(t[0], t[1], t[2]), fromProp(door, [0.55, 0, 1.2]));
await p.waitForTimeout(300);
await press('KeyE', 1300); s = await S();
check('close it from the bedroom side', s.doorT === 0, `t=${s.doorT} hint="${s.hint}"`);
await press('Enter', 400); s = await S();
check('and lock it again with the armed card', s.doorLocked && s.toast.includes('Door locked'), `toast="${s.toast}"`);
await press('Backspace', 300);
check('Delete (Backspace on a Mac) puts the card away', (await p.evaluate(() => window.__inventory.armed)) === null);
await b.close();
console.log(fails ? `${fails} failed` : 'all passed');
process.exit(fails ? 1 : 0);
