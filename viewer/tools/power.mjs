// Power and darkness as gameplay (viewer/house.js), played in the real level from the player's
// eye: the house starts powered with the main fuse in; the Grimble's break-in (faked here by a
// stand-in window.__hunt, or the real one with `real`) flickers the lights and trips the power
// and blows the fuse; the garage goes dark, the motors (blinds, garage door) stop, the switches
// say "no power", the isolator says "No main fuse"; the flashlight (picked up in the mudroom,
// F) lights the dark and its beam on the Grimble sends a `light` cue (not through a wall); the
// spare fuse is in the garage's steel locker (a key chain away); fuse in + isolator on = power
// back, rooms lit; a timed trip later (fuse intact) is undone at the isolator alone.
// ITEMS OFF (the default build: blender/levels/caches.py ITEMS, no flashlight, no spare fuse;
// a GT_ITEMS=1 build runs all of the above): the break-in trip (?breaktrip=1) only drops the
// isolator, the fuse survives (house.js never blows a fuse that has no spare), the isolator alone
// brings the power back; no flashlight hint; the timed trips as before.
// Screenshots: <out>/power_*.png. Usage: node viewer/tools/power.mjs [out-dir=build/power] [real]
import { chromium } from 'playwright-core';
import fs from 'fs';
import { level, prop, props, fromProp, url, room } from './level.mjs';
const [out = 'build/power', mode = ''] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
fs.mkdirSync('build/locks', { recursive: true });
let slot = null;
while (slot === null) {
  for (let i = 0; i < 3 && slot === null; i++) { try { fs.mkdirSync(`build/locks/browser_${i}`); slot = i; } catch {} }
  if (slot === null) await new Promise((ok) => setTimeout(ok, 3000));
}
process.on('exit', () => { try { fs.rmdirSync(`build/locks/browser_${slot}`); } catch {} });

const breaker = prop('ix_breaker_panel');
const eyeBreaker = fromProp(breaker, [0, -0.85, 0.2]);         // in front of it, eye 1.65 m
const lookIso = fromProp(breaker, [0, 0, 0.275]);              // the isolator (top)
const lookSlot = fromProp(breaker, [0, 0, -0.25]);             // the fuse carrier (bottom)
const garage = room('garage');
const flash = props('ix_flashlight')[0];
const ITEMS_ON = !!flash || props('ix_fuse').length > 0 || level.props.some((q) => q.lock);
console.log(`items ${ITEMS_ON ? 'ON (GT_ITEMS=1 build)' : 'OFF: no flashlight, no spare fuse'}`);

const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 1100, height: 700 } });
p.on('pageerror', (e) => console.log('pageerror:', e.message));
p.on('console', (m) => { if (m.type() === 'error') console.log('console:', m.text()); });
p.on('response', (r) => { if (r.status() >= 400) console.log('http', r.status(), r.url()); });
let fails = 0;
const check = (label, ok, detail = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}  ${detail}`); if (!ok) fails++; };
const real = mode === 'real';
await p.goto(url(eyeBreaker, lookIso) + (real ? '&grimble=house&gdelay=0&hunt=now' : '&grimble=0') + '&trips=0&breaktrip=1');
await p.waitForFunction(() => window.__loaded && window.__house, null, { timeout: 120000 });
await p.evaluate(() => document.querySelectorAll('#hud,#stats').forEach((e) => (e.style.display = 'none')));
await p.mouse.click(550, 350); await p.waitForTimeout(500);
const press = async (k, wait = 350) => { await p.keyboard.press(k); await p.waitForTimeout(wait); };
const hint = () => p.textContent('#hint');
const toast = () => p.evaluate(() => window.__toast());
const shot = (name) => p.screenshot({ path: `${out}/power_${name}.png` });
const teleport = (pos, look) => p.evaluate(([pos, look]) => {
  window.__player.pos.set(pos[0], pos[1] - 1.65, pos[2]); window.__player.vel.set(0, 0, 0);
  window.__player.syncCamera(); window.__camera.lookAt(...look);
}, [pos, look]).then(() => p.waitForTimeout(250));   // (the hint follows on the next frames)
const S = () => p.evaluate(() => {
  const s = window.__signals, h = window.__house;
  return { power: s.get('power'), fuse: s.get('fuse_garage'), flashlight: s.get('flashlight'),
           garage: +h.level('garage').toFixed(3), kitchen: +h.level('kitchen').toFixed(3), courtyard: +h.level('courtyard').toFixed(3),
           lightGarage: +h.lightAt({ x: 19.75, y: 1.6, z: 10 }).toFixed(3), dimmer: h.state().dimmer,
           inv: window.__inventory.ids(), armed: window.__inventory.armed };
});
// the mean brightness of the frame (0..255): is it dark?
const brightness = () => p.evaluate(() => {
  const c = window.__three.renderer.domElement, w = 64, h = 40;
  const t = document.createElement('canvas'); t.width = w; t.height = h;
  const g = t.getContext('2d'); g.drawImage(c, 0, 0, w, h);
  const d = g.getImageData(0, 0, w, h).data; let s = 0;
  for (let i = 0; i < d.length; i += 4) s += 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];
  return +(s / (w * h)).toFixed(1);
});
const armItem = async (id) => {
  await press('KeyI', 200);
  const ids = await p.evaluate(() => window.__inventory.ids());
  for (let i = 0; i < ids.indexOf(id); i++) await press('ArrowDown', 80);
  await press('Enter', 250);
};

// ---------------------------------------------------------------- start: powered, fuse in
let s = await S();
check('power starts on with the main fuse in', s.power === true && s.fuse === true, JSON.stringify(s));
check('the fallback dimmer is active (baked level)', s.dimmer === true);
await teleport(eyeBreaker, lookSlot);
check('the fuse carrier reads "Main fuse in place"', (await hint()).includes('Main fuse in place'), `hint="${await hint()}"`);
await teleport(eyeBreaker, lookIso);
check('the isolator offers "Switch the power off"', (await hint()).includes('Switch the power off'), `hint="${await hint()}"`);
const view = [garage.cx + 4, 1.65, garage.z0 + 7];        // a wide view of the garage, toward the cars
const viewLook = [garage.cx - 3, 1.0, garage.z0 + 2];
await teleport(view, viewLook); await p.waitForTimeout(400);
await shot('1_garage_lit');
const lit = await brightness();

// ---------------------------------------------------------------- the break-in trips the power
if (real) {
  // the real Grimble: skip its walk-in, it knocks a round and smashes the glass
  await p.evaluate(() => { const g = window.__grimble; g.state = 'walk'; g.root.visible = true; g.s = g.total; g.place(); });
  await p.waitForFunction(() => window.__hunt?.broken, null, { timeout: 90000 });
} else {
  // a stand-in for the hunt (grimble_hunt.js): broken in, prowling, somewhere in the great room
  await p.evaluate(async () => {
    const THREE = await import('three');
    window.__hunt = { broken: true, state: 'prowl', root: { position: new THREE.Vector3(-20, 0, 0) } };
  });
}
await p.waitForTimeout(700);
s = await S();
check('mid-flicker: still powered, lights flickering', s.power === true && (await p.evaluate(() => window.__house.state().tripping)), JSON.stringify(s));
await p.waitForTimeout(1600);
s = await S();
if (ITEMS_ON) check('after the flicker: power out, main fuse blown', s.power === false && s.fuse === false, JSON.stringify(s));
else check('after the flicker: power out, the main fuse survives (no spare in the house)', s.power === false && s.fuse === true, JSON.stringify(s));
check('toast "Power out"', (await toast()).includes('Power out'), `toast="${await toast()}"`);
check('the windowless garage is black; the courtyard keeps its daylight', s.garage < 0.05 && s.courtyard === 1 && s.kitchen > 0.2 && s.kitchen < 0.6, JSON.stringify(s));
await p.waitForTimeout(300);
await shot('2_garage_dark');
const dark = await brightness();
check('the garage view is much darker', dark < lit * 0.35, `lit=${lit} dark=${dark}`);

// ---------------------------------------------------------------- what needs power, without it
await teleport(eyeBreaker, lookIso);
if (ITEMS_ON) {
  check('the isolator (dropped to off) asks for the fuse', (await hint()).includes('No main fuse'), `hint="${await hint()}"`);
  await press('KeyE');
  check('E: "No main fuse", power stays off', (await toast()).includes('No main fuse') && (await S()).power === false, `toast="${await toast()}"`);
  await teleport(eyeBreaker, lookSlot);
  check('the empty carrier asks for a fuse', (await hint()).includes('needs a fuse'), `hint="${await hint()}"`);
} else {
  check('the isolator (dropped to off) offers "Switch the power on"', (await hint()).includes('Switch the power on'), `hint="${await hint()}"`);
  await teleport(eyeBreaker, lookSlot);
  check('the carrier still reads "Main fuse in place"', (await hint()).includes('Main fuse in place'), `hint="${await hint()}"`);
}
// motors: the office blinds (lowered from the tablet / a switch elsewhere) don't move without power
const motor = await p.evaluate(async () => {
  const it = window.__interact, blinds = it.reactors.filter((r) => r.signal === 'blinds_office');
  window.__signals.set('blinds_office', true);
  await new Promise((ok) => setTimeout(ok, 1500));
  return { n: blinds.length, t: Math.max(...blinds.map((r) => r.t)), motor: blinds.every((r) => r.motor) };
});
check('the blinds motor does nothing without power', motor.n > 0 && motor.motor && motor.t === 0, JSON.stringify(motor));
const sw = props('ix_switch').find((q) => q.room === 'garage');
await teleport(fromProp(sw, [0, -0.7, 0.55]), fromProp(sw, [0, 0, 0]));
check('the garage light switch says "no power"', (await hint()).includes('no power'), `hint="${await hint()}"`);
await press('KeyE');
check('E on it: "No power"', (await toast()).includes('No power'), `toast="${await toast()}"`);
await press('KeyE');

// ---------------------------------------------------------------- items off: no flashlight; the isolator alone
if (!ITEMS_ON) {
  await teleport(view, viewLook); await p.waitForTimeout(200);
  check('no "F flashlight" hint, no battery meter', !(await hint()).includes('flashlight') &&
    !(await p.evaluate(() => document.getElementById('battery').classList.contains('show'))), `hint="${await hint()}"`);
  await teleport(eyeBreaker, lookIso);
  await press('KeyE', 900);
  s = await S();
  check('E at the isolator: power back on, the garage lit again', s.power === true && s.garage > 0.99, JSON.stringify(s));
  check('toast "Power on"', (await toast()).includes('Power on'), `toast="${await toast()}"`);
  const back = await p.evaluate(async () => {
    await new Promise((ok) => setTimeout(ok, 2500));
    const t = Math.min(...window.__interact.reactors.filter((r) => r.signal === 'blinds_office').map((r) => r.t));
    window.__signals.set('blinds_office', false);
    return t;
  });
  check('the blinds called for in the dark come down once there is power', back === 1, `t=${back}`);
  await teleport(view, viewLook); await p.waitForTimeout(400);
  await shot('6_garage_restored');
}
if (ITEMS_ON) {
// ---------------------------------------------------------------- the flashlight in the dark
if (flash) await teleport(fromProp(flash, [0, -0.6, 0.73]), fromProp(flash, [0, 0, 0]));   // (none: it's attached inside the locker)
await p.waitForTimeout(200);
const fh = flash ? await hint() : '';
if (fh.includes('Take') || fh.includes('Pick')) await press('KeyE');
else {   // (it's in the garage locker, behind a key chain: open it as if unlocked)
  await p.evaluate(() => { const I = window.__interact, it = I.items.find((i) => i.def.item === 'flashlight'); if (it.host) { it.host.locked = false; I.use(it.host, null); } });
  await p.waitForTimeout(1500);
  await p.evaluate(() => { const it = window.__interact.items.find((i) => i.def.item === 'flashlight'); window.__interact.use(it, null); window.__inventory.changed(); });
}
check('picked up the flashlight', (await S()).inv.includes('flashlight'), `hint was "${fh}"`);
await teleport(view, viewLook); await p.waitForTimeout(200);
check('the walk hint shows F for the flashlight', (await hint()).includes('F flashlight'), `hint="${await hint()}"`);
await press('KeyF', 500);
s = await S();
check('F turns it on (signal flashlight)', s.flashlight === true, JSON.stringify(s));
await shot('3_garage_flashlight');
const torch = await brightness();
check('the beam lights the dark garage', torch > dark * 1.3, `dark=${dark} torch=${torch}`);

// the light cue: the Grimble (stand-in) in the beam, then behind a wall
const cue = await p.evaluate(async ([gx, gz, wx, wz]) => {
  const THREE = await import('three');
  const real = window.__hunt;
  const fake = { broken: true, state: 'prowl', root: { position: new THREE.Vector3(gx, 0, gz) } };
  window.__hunt = fake;
  const got = [];
  const off = window.__noise.on((n) => got.push(n.source));
  await new Promise((ok) => setTimeout(ok, 1300));
  const inBeam = got.filter((x) => x === 'light').length;
  got.length = 0;
  fake.root.position.set(wx, 0, wz);   // the other side of the garage's north wall (the mudroom)
  await new Promise((ok) => setTimeout(ok, 1300));
  const behind = got.filter((x) => x === 'light').length;
  off();
  window.__hunt = real;
  return { inBeam, behind };
}, [viewLook[0], viewLook[2], garage.cx, garage.z0 - 3]);
check('the beam on the Grimble sends a light cue; through a wall it does not', cue.inBeam >= 1 && cue.behind === 0, JSON.stringify(cue));

// ---------------------------------------------------------------- the spare fuse (in the garage locker)
// (getting it is a key chain, blender/levels/caches.py, walked by locks.mjs; here: open the
// locker as if unlocked and take the fuse)
const fuseHost = await p.evaluate(() => {
  const I = window.__interact, it = I.items.find((i) => i.def.item === 'fuse');
  if (!it) return null;
  if (it.host) { it.host.locked = false; I.use(it.host, null); }
  return it.host ? it.host.node.name : 'none';
});
check('the spare fuse is in the garage locker', /Locker/i.test(fuseHost ?? ''), `host=${fuseHost}`);
await p.waitForTimeout(1500);
await p.evaluate(() => { const I = window.__interact, it = I.items.find((i) => i.def.item === 'fuse'); I.use(it, null); window.__inventory.changed(); });
check('took the fuse', (await S()).inv.includes('fuse'), `toast="${await toast()}"`);

// ---------------------------------------------------------------- fuse in, isolator on: power back
await teleport(eyeBreaker, lookSlot);
await armItem('fuse');
check('armed fuse: "Enter · Insert fuse"', (await hint()).includes('Insert fuse'), `hint="${await hint()}"`);
await press('Enter');
s = await S();
check('Enter puts the fuse in (power still off until the isolator)', s.fuse === true && s.power === false && !s.inv.includes('fuse'), JSON.stringify(s));
await teleport(eyeBreaker, lookIso);
check('the isolator now offers "Switch the power on"', (await hint()).includes('Switch the power on'), `hint="${await hint()}"`);
await press('KeyE', 900);
s = await S();
check('E: power back on, the garage lit again', s.power === true && s.garage > 0.99, JSON.stringify(s));
check('toast "Power on"', (await toast()).includes('Power on'), `toast="${await toast()}"`);
const back = await p.evaluate(async () => {
  await new Promise((ok) => setTimeout(ok, 2500));
  const t = Math.min(...window.__interact.reactors.filter((r) => r.signal === 'blinds_office').map((r) => r.t));
  window.__signals.set('blinds_office', false);
  return t;
});
check('the blinds called for in the dark come down once there is power', back === 1, `t=${back}`);
await press('KeyF', 200);   // flashlight off
await teleport(view, viewLook); await p.waitForTimeout(400);
await shot('6_garage_restored');
}   // (ITEMS_ON)

// ---------------------------------------------------------------- a timed trip: the isolator alone
if (!real) {
  await p.evaluate(() => { const h = window.__house; h.tripEvery = [600, 600]; h.nextTrip = 0.05; });
  await p.waitForTimeout(2200);
  s = await S();
  check('a timed trip while it prowls: power out, the fuse survives', s.power === false && s.fuse === true, JSON.stringify(s));
  await teleport(eyeBreaker, lookIso);
  await press('KeyE', 600);
  check('the isolator alone brings it back', (await S()).power === true, `toast="${await toast()}"`);
  // the player may also cut it on purpose (hide in the dark)
  await press('KeyE', 600);
  check('switching it off by hand works (no fuse lost)', (await S()).power === false && (await S()).fuse === true);
  await press('KeyE', 600);
}

// ---------------------------------------------------------------- the battery behind the keycard door
if (ITEMS_ON) {
const bat = await p.evaluate(() => {
  const it = window.__interact.items.find((i) => i.def.item === 'battery' && i.host && /Nightstand_Drawer$/.test(i.host.node.name) && !/Guest/.test(i.host.node.name));
  return it ? it.host.node.name : null;
});
check('a spare battery rides in the primary bedroom nightstand drawer', !!bat, `host=${bat}`);
}

await b.close();
console.log(fails ? `${fails} failed` : 'all passed');
process.exit(fails ? 1 : 0);
