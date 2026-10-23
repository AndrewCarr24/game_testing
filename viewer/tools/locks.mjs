// Locks, keys and caches (blender/levels/caches.py). 1) Every lock in the level has its key
// somewhere in the house, every key opens something, and every locked thing says what it needs.
// 2) Walks one full chain the way a player does: garage workbench drawer -> cellar key ->
// wine room climate cabinet (locked; arm the key, Enter, E) -> locker key -> garage steel locker
// (locked) -> fuse, flashlight and battery. Usage: node locks.mjs [out-dir]
// ITEMS OFF (the default build, blender/levels/caches.py ITEMS; GT_ITEMS=1 builds run the chain
// above): no locks and no keys anywhere; the drawer, the cabinet and the locker open with E and
// hold nothing to take.
import { chromium } from 'playwright-core';
import fs from 'fs';
import { level, prop, fromProp, url } from './level.mjs';
const ITEMS_ON = level.props.some((q) => q.lock || /^(ix_flashlight|ix_fuse|ix_battery|keycard|ix_key_)/.test(q.asset));
const out = process.argv[2] || 'build/locks_chain';   // (not build/locks: that's the run-slot directory)
fs.mkdirSync(out, { recursive: true });
const bench = prop('garage_workbench'), cabinet = prop('dining_climate_wall'), locker = prop('ix_gun_locker');

const lockDir = (i) => `build/locks/browser_${i}`;
let slot = -1;
for (let t = 0; slot < 0; t++) {
  for (let i = 0; i < 3 && slot < 0; i++) { try { fs.mkdirSync(lockDir(i)); slot = i; } catch { /* taken */ } }
  if (slot < 0) { if (t % 30 === 0) console.log('waiting for a browser slot'); await new Promise((r) => setTimeout(r, 2000)); }
}
const release = () => { try { fs.rmdirSync(lockDir(slot)); } catch { /* gone */ } };
process.on('exit', release);

const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 1100, height: 700 } });
p.on('pageerror', (e) => console.log('pageerror:', e.message));
let fails = 0;
const check = (label, ok, detail = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}  ${detail}`); if (!ok) fails++; };

const benchEye = fromProp(bench, [0, 1.15, 1.65]), benchLook = fromProp(bench, [0, 0.4, 0.75]);
await p.goto(url(benchEye, benchLook) + '&grimble=0');
await p.waitForFunction(() => window.__loaded, null, { timeout: 90000 });
await p.mouse.click(550, 350); await p.waitForTimeout(500);

// ------------------------------------------------------------------ every lock has a key, and says so
const audit = await p.evaluate(() => {
  const it = window.__interact;
  const keys = it.items.filter((i) => i.def.type === 'pickup' && /^(key_|keycard$)/.test(i.def.item));
  const locks = it.items.filter((i) => i.lockKey);
  return {
    keys: keys.map((k) => k.def.item),
    locks: locks.map((l) => ({ key: l.lockKey, node: l.node.name, locked: l.locked, prompt: it.prompt(l), name: it.itemName(l.lockKey) })),
  };
});
console.log(`keys: ${audit.keys.join(', ')}`);
for (const l of audit.locks) console.log(`  lock ${l.node} <- ${l.key}: "${l.prompt}"`);
const lockKeys = new Set(audit.locks.map((l) => l.key));
if (!ITEMS_ON) {
  check('items off: no locks and no keys in the level', audit.locks.length === 0 && audit.keys.length === 0 && !level.props.some((q) => q.lock),
    `locks=${audit.locks.length} keys=${audit.keys.join(',')}`);
}
if (ITEMS_ON) {
check('every lock has its key in the level', audit.locks.every((l) => audit.keys.includes(l.key)),
  audit.locks.filter((l) => !audit.keys.includes(l.key)).map((l) => l.key).join(','));
check('every key opens something', audit.keys.every((k) => lockKeys.has(k)), audit.keys.filter((k) => !lockKeys.has(k)).join(','));
check('every lock starts locked and names its key ("Locked · needs the ...")',
  audit.locks.length >= 5 && audit.locks.every((l) => l.locked && l.prompt === `Locked · needs the ${l.name}`),
  `${audit.locks.length} locks`);
}

const S = () => p.evaluate(() => {
  const it = window.__interact;
  const find = (fn) => it.items.find(fn);
  const drawer = find((i) => i.node.name === 'GarageWorkbench_Drawer');
  const cab = find((i) => i.node.name === 'DiningClimateWall_Door');
  const lock = find((i) => i.node.name === 'IX_GunLocker_Door');
  return {
    hint: document.getElementById('hint').textContent, toast: window.__toast(),
    inv: window.__inventory.ids(), armed: window.__inventory.armed,
    drawerT: drawer?.t, cabT: cab?.t, cabLocked: cab?.locked, lockerT: lock?.t, lockerLocked: lock?.locked,
  };
});
const teleport = (pos, look) => p.evaluate(([pos, look]) => {
  window.__player.pos.set(pos[0], pos[1] - 1.65, pos[2]); window.__player.vel.set(0, 0, 0);
  window.__player.syncCamera(); window.__camera.lookAt(...look);
}, [pos, look]);
const press = async (k, wait = 1100) => { await p.keyboard.press(k); await p.waitForTimeout(wait); };
const arm = async (id) => {
  await press('KeyI', 250);
  const ids = await p.evaluate(() => window.__inventory.ids());
  const sel = await p.evaluate(() => window.__inventory.sel);
  for (let i = sel; i < ids.indexOf(id); i++) await press('ArrowDown', 80);
  for (let i = sel; i > ids.indexOf(id); i--) await press('ArrowUp', 80);
  await press('Enter', 300);
};

if (!ITEMS_ON) {
  // the same three places, unlocked and empty (E opens; nothing offered)
  let s = await S();
  await press('KeyE', 900); s = await S();
  check('the workbench drawer opens and holds nothing to take', s.drawerT === 1 && !s.hint.includes('Take'), `hint="${s.hint}"`);
  await p.screenshot({ path: `${out}/off_1_workbench_drawer.png` });
  await teleport(fromProp(cabinet, [-0.5, -1.15, 1.65]), fromProp(cabinet, [-0.5, 0, 1.2])); await p.waitForTimeout(400); s = await S();
  check('the climate cabinet is not locked: "Open"', !s.cabLocked && !s.hint.includes('Locked'), `hint="${s.hint}"`);
  await press('KeyE', 1200); s = await S();
  check('E opens its glass door; nothing to take', s.cabT === 1 && !s.hint.includes('Take'), `t=${s.cabT} hint="${s.hint}"`);
  await p.screenshot({ path: `${out}/off_2_cabinet_open.png` });
  await teleport(fromProp(locker, [0.15, -1.25, 1.65]), fromProp(locker, [0.1, 0, 1.1])); await p.waitForTimeout(400); s = await S();
  check('the garage locker is not locked', !s.lockerLocked && !s.hint.includes('Locked'), `hint="${s.hint}"`);
  await press('KeyE', 1100); s = await S();
  check('E opens it: empty', s.lockerT === 1 && !s.hint.includes('Take') && s.inv.length === 0, `hint="${s.hint}" inv=${s.inv}`);
  await p.screenshot({ path: `${out}/off_3_locker_open.png` });
  await b.close();
  console.log(fails ? `${fails} failed` : 'all passed (items off; the key chain needs a GT_ITEMS=1 build)');
  process.exit(fails ? 1 : 0);
}

// ------------------------------------------------------------------ 1: the cellar key in the workbench drawer
let s = await S();
check('the workbench drawer is shut: nothing to take yet', s.hint.includes('Open drawer') && !s.hint.includes('Take'), `hint="${s.hint}"`);
await press('KeyE', 900); s = await S();
check('E opens the drawer: the cellar key is offered', s.drawerT === 1 && s.hint.includes('Take cellar key'), `hint="${s.hint}"`);
await p.screenshot({ path: `${out}/1_workbench_drawer.png` });
await press('KeyE', 400); s = await S();
check('E takes the cellar key', s.inv.includes('key_cellar') && s.toast.includes('Cellar key'), `inv=${s.inv} toast="${s.toast}"`);

// ------------------------------------------------------------------ 2: the climate cabinet in the wine room
const cabEye = fromProp(cabinet, [-0.5, -1.15, 1.65]), cabLook = fromProp(cabinet, [-0.5, 0, 1.2]);
await teleport(cabEye, cabLook); await p.waitForTimeout(400); s = await S();
check('the cabinet is locked and the player is told to arm the key they carry', s.cabLocked && s.hint.includes('Locked · arm the cellar key'), `hint="${s.hint}"`);
await press('KeyE', 400); s = await S();
check('E on it: still shut, the toast says how', s.cabT === 0 && s.toast.includes('arm the cellar key'), `toast="${s.toast}"`);
await p.screenshot({ path: `${out}/2_cabinet_locked.png` });
check('the locker key behind the glass cannot be taken yet', !s.hint.includes('Take locker key'), `hint="${s.hint}"`);
await arm('key_cellar'); s = await S();
check('armed cellar key: "Enter · Unlock cabinet"', s.armed === 'key_cellar' && s.hint.includes('Enter · Unlock cabinet'), `hint="${s.hint}"`);
await press('Enter', 400); s = await S();
check('Enter unlocks the cabinet', !s.cabLocked && s.toast === 'Cabinet unlocked', `toast="${s.toast}"`);
await press('KeyE', 1200); s = await S();
check('E opens the glass door; the locker key is offered', s.cabT === 1 && s.hint.includes('Take locker key'), `t=${s.cabT} hint="${s.hint}"`);
await p.screenshot({ path: `${out}/3_cabinet_open.png` });
await press('KeyE', 400); s = await S();
check('E takes the locker key', s.inv.includes('key_locker'), `inv=${s.inv}`);
await press('Backspace', 300);

// ------------------------------------------------------------------ 3: the steel locker in the garage
const lockEye = fromProp(locker, [0.15, -1.25, 1.65]), lockLook = fromProp(locker, [0.1, 0, 1.1]);
await teleport(lockEye, lockLook); await p.waitForTimeout(400); s = await S();
check('the locker is locked', s.lockerLocked && s.hint.includes('Locked'), `hint="${s.hint}"`);
await p.screenshot({ path: `${out}/4_locker_locked.png` });
await arm('key_locker'); s = await S();
check('armed locker key: "Enter · Unlock locker"', s.hint.includes('Enter · Unlock locker'), `hint="${s.hint}"`);
await press('Enter', 400); s = await S();
check('Enter unlocks it', !s.lockerLocked && s.toast === 'Locker unlocked', `toast="${s.toast}"`);
await press('KeyE', 1100); s = await S();
check('E opens it: something to take', s.lockerT === 1 && s.hint.includes('Take'), `hint="${s.hint}"`);
await p.screenshot({ path: `${out}/5_locker_open.png` });
for (let i = 0; i < 3; i++) await press('KeyE', 350);
s = await S();
check('the fuse, the flashlight and a battery are in the inventory',
  ['fuse', 'flashlight', 'battery'].every((id) => s.inv.includes(id)), `inv=${s.inv}`);
await p.screenshot({ path: `${out}/6_locker_emptied.png` });
await b.close();
console.log(fails ? `${fails} failed` : 'all passed');
process.exit(fails ? 1 : 0);
