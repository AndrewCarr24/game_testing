// Sound effects (viewer/audio.js): triggers every sound the game makes, the way a player would
// (keys, walking, throwing) where it can and through the game's state where it must (power,
// blinds, the Grimble fast-forwarded to the glass), and checks each one reached window.__sfx
// (its call log) with audio actually running, the loops that should be on are, and the console
// stays clean. It can't listen: the levels are checked offline by tools/build_audio.py --report
// (the sprite) and here (the synthesised loops' RMS / peak).
// Usage: GT_BASE=http://localhost:<port> node viewer/tools/sfx.mjs [out-dir]
import fs from 'fs';
import { chromium } from 'playwright-core';
import { level, room } from './level.mjs';

const out = process.argv[2] || 'build/sfx';
fs.mkdirSync(out, { recursive: true });
const BASE = process.env.GT_BASE || 'http://localhost:8765';
fs.mkdirSync('build/locks', { recursive: true });
let slot = null;
while (slot === null) {
  for (let i = 0; i < 3 && slot === null; i++) { try { fs.mkdirSync(`build/locks/browser_${i}`); slot = i; } catch {} }
  if (slot === null) await new Promise((ok) => setTimeout(ok, 3000));
}
process.on('exit', () => { try { fs.rmdirSync(`build/locks/browser_${slot}`); } catch {} });

let fails = 0;
const check = (label, ok, detail = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}  ${detail}`); if (!ok) fails++; };
const errors = [];
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal', '--autoplay-policy=no-user-gesture-required'] });

async function open(qs, pos, look) {
  const p = await b.newPage({ viewport: { width: 960, height: 600 } });
  p.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));
  p.on('console', (m) => { if ((m.type() === 'error' && !/favicon/.test(m.location()?.url ?? '')) || (m.type() === 'warning' && /sfx/.test(m.text()))) errors.push(`console ${m.type()}: ${m.text()}`); });
  await p.goto(`${BASE}/viewer/index.html?level=mansion&pos=${pos.join(',')}&look=${look.join(',')}${qs}`);
  await p.waitForFunction(() => window.__loaded, null, { timeout: 120000 });
  await p.mouse.click(480, 300);           // the gesture that starts audio (and locks the pointer)
  await p.waitForFunction(() => window.__sfx?.buffer && Object.keys(window.__sfx.loopBuffers).length === 6, null, { timeout: 20000 });
  return p;
}
const wait = (p, ms) => p.waitForTimeout(ms);
const since = (p, mark) => p.evaluate((m) => window.__sfx.log.filter((e) => e.t >= m && !e.muted).map((e) => e.name), mark);
const now = (p) => p.evaluate(() => performance.now());
const teleport = (p, eye, look) => p.evaluate(([e, l]) => {
  const pl = window.__player;
  pl.pos.set(e[0], e[1] - pl.eye, e[2]); pl.vel.set(0, 0, 0); pl.syncCamera(); window.__camera.lookAt(...l);
}, [eye, look]);
const hint = (p) => p.evaluate(() => document.getElementById('hint').textContent);
const hold = async (p, keys, ms) => { for (const k of keys) await p.keyboard.down(k); await wait(p, ms); for (const k of [...keys].reverse()) await p.keyboard.up(k); };
// stand where E reaches an item matching `pick` (source of a predicate on interact items) with
// the crosshair on it, and the game's own hint offering it; returns the eye position or null
async function faceItem(p, pick) {
  const cands = await p.evaluate((src) => {
    const ix = window.__interact, pl = window.__player, cam = window.__camera, fwd = cam.getWorldDirection(cam.position.clone());
    const out = [];
    ix.items.forEach((it, i) => {
      if (!eval(src)(it) || !ix.available(it)) return;
      const c = ix.centre(it);
      for (const d of [0.8, 1.0, 0.6, 1.2]) for (let k = 0; k < 8; k++) {
        const a = (k / 8) * Math.PI * 2;
        const eye = c.clone().add({ x: Math.sin(a) * d, y: 0, z: Math.cos(a) * d });
        eye.y = (c.y > 4.2 ? 4.6 : 0) + 1.65;
        pl.pos.set(eye.x, eye.y - 1.65, eye.z);
        if (pl.overlapping(pl.pos).length) continue;
        pl.syncCamera(); cam.lookAt(c);
        if (ix.nearest(cam.position, cam.getWorldDirection(fwd)) === it) out.push({ i, eye: eye.toArray(), look: c.toArray() });
      }
    });
    return out.slice(0, 12);
  }, pick);
  for (const c of cands) {
    await teleport(p, c.eye, c.look);
    await wait(p, 250);
    const ok = await p.evaluate((i) => {
      const it = window.__interact.items[i];
      return document.getElementById('hint').textContent.includes(`E · ${window.__interact.prompt(it)}`);
    }, c.i);
    if (ok) return c.eye;
  }
  return null;
}
const pressE = async (p, ms = 900) => { await p.keyboard.press('KeyE'); await wait(p, ms); };
const has = (list, name) => list.includes(name);

// ================================================================ the house
const entry = room('entry');
let p = await open('&grimble=0', level.spawn.position, level.spawn.lookAt);
let s = await p.evaluate(() => ({ state: window.__sfx.ctx.state, offset: window.__sfx.offset, voices: window.__sfx.voices.length }));
check('audio runs after the first click, the sprite is decoded and lined up', s.state === 'running' && Math.abs(s.offset) < 0.1, JSON.stringify(s));

// the floors: what each room's footsteps sound like (off its rugs)
const floors = await p.evaluate(() => Object.fromEntries(window.__sfx.surfaces.rooms.map((r) => [r.name, r.surface])));
console.log('floors:', JSON.stringify(floors));
check('room floors classified (stone entry/great room/kitchen, oak galleries, tile bath/mudroom, rubber gym, concrete garage)',
  floors.entry === 'stone' && floors.great_room === 'stone' && floors.kitchen === 'stone' && floors.gallery_n === 'wood' && floors.primary_bath === 'tile' &&
  floors.mudroom === 'tile' && floors.gym === 'rubber' && floors.garage === 'concrete', JSON.stringify(floors));
const out1 = await p.evaluate(() => [window.__sfx.surfaces.at({ x: 0, y: 0, z: 23 }), window.__sfx.surfaces.at({ x: 60, y: 0, z: 70 }), window.__sfx.surfaces.at({ x: 20, y: 0, z: 35 }), window.__sfx.surfaces.rugs.size]);
check('outdoors: terrace stone, lawn grass, drive gravel; rugs mapped', out1[0] === 'stone' && out1[1] === 'grass' && out1[2] === 'gravel' && out1[3] > 50, JSON.stringify(out1));

// walking, then running down the west gallery (oak), jumping
const gw = room('gallery_w');
await teleport(p, [gw.cx, 1.65, gw.z0 + 0.6], [gw.cx, 1.65, gw.z1]);
await wait(p, 200);
let m = await now(p);
await hold(p, ['KeyW'], 1500);
await hold(p, ['ShiftLeft', 'KeyW'], 1000);
let calls = await since(p, m);
const steps = calls.filter((n) => n.startsWith('step_'));
check('walking and running on oak: footsteps at a human cadence', steps.length >= 5 && steps.length <= 12 && steps.every((n) => n === 'step_wood'), `${steps.length} steps in 2.5 s: ${steps.join(' ')}`);
m = await now(p);
await hold(p, ['Space'], 120); await wait(p, 1100);   // (a tap as long as a person's: the game reads keys per frame)
calls = await since(p, m);
check('a jump: jump, then land', has(calls, 'jump') && has(calls, 'land'), calls.join(' '));

// the courtyard's stone paving
const cy = room('courtyard');
await teleport(p, [cy.x0 + 1, 1.65, cy.cz + 0.3], [cy.x1, 1.65, cy.cz + 0.3]);
m = await now(p);
await hold(p, ['KeyW'], 1000);
calls = await since(p, m);
check('the courtyard is stone', calls.filter((n) => n === 'step_stone').length >= 2, calls.join(' '));
const rug = await p.evaluate(() => { const k = [...window.__sfx.surfaces.rugs].find((c) => c.endsWith(',0')).split(',').map(Number); return [(k[0] + 0.5) * 0.25, (k[1] + 0.5) * 0.25]; });
const onRug = await p.evaluate(([x, z]) => window.__sfx.surfaces.at({ x, y: 0.01, z }), rug);
check('a rug cell reads as rug', onRug === 'rug', `${onRug} at ${rug}`);

// doors: open (E), close (E: the latch at the end of the swing); the keycard door is locked
let eye = await faceItem(p, "(i) => i.def.type === 'rotate' && /^Door/.test(i.node.name) && !i.locked");
check('found a door to open', !!eye, JSON.stringify(eye));
if (eye) {
  m = await now(p); await pressE(p, 1500); await pressE(p, 2000);
  calls = await since(p, m);
  check('door: opens and closes with a latch', has(calls, 'door_open') && has(calls, 'door_close'), calls.join(' '));
}
eye = await faceItem(p, "(i) => i.locked");
if (eye) { m = await now(p); await pressE(p, 600); calls = await since(p, m); check('a locked door rattles', has(calls, 'door_locked'), calls.join(' ')); }
else check('found the locked door', false);
// the keycard unlocks it: beeps
await p.evaluate(() => { const it = window.__interact.items.find((i) => i.lockKey === 'keycard'); it.locked = false; });
await wait(p, 300); calls = await since(p, m);
check('unlocking with the keycard beeps', has(calls, 'keycard_unlock'), calls.join(' '));

// a drawer
eye = await faceItem(p, "(i) => i.def.type === 'slide'");
if (eye) {
  m = await now(p); await pressE(p, 900);
  const card = await p.evaluate(() => document.getElementById('hint').textContent.includes('Take'));
  if (card) await pressE(p, 500);
  await pressE(p, 900);
  calls = await since(p, m);
  check('drawer: slides open and shut', has(calls, 'drawer_open') && has(calls, 'drawer_close'), calls.join(' '));
} else check('found a drawer', false);

// a light switch (and its rocker's partner clicks with it), then the breaker via power
eye = await faceItem(p, "(i) => i.def.type === 'switch' && /^lights_/.test(i.signal)");
if (eye) {
  m = await now(p); await pressE(p, 400); await pressE(p, 400);
  calls = await since(p, m);
  check('light switch: click on, click off', has(calls, 'switch_on') && has(calls, 'switch_off'), calls.join(' '));
} else check('found a light switch', false);
m = await now(p);
await p.evaluate(() => window.__signals.set('power', false)); await wait(p, 2500);
await p.evaluate(() => window.__signals.set('power', true)); await wait(p, 800);
calls = await since(p, m);
check('power cut and restored: breaker clunks, the house winds down and up', has(calls, 'breaker_off') && has(calls, 'power_down') && has(calls, 'breaker_on') && has(calls, 'power_up'), calls.join(' '));

// blinds: the motor runs while they move; the den TV is on (a loop at the screen)
const gr = room('great_room');
await teleport(p, [gr.cx, 1.65, gr.cz], [gr.x0, 1.5, gr.cz]);
const blinds = await p.evaluate(() => window.__signals.names().find((n) => /^blinds_great/.test(n)));
await p.evaluate((n) => window.__signals.set(n, !window.__signals.get(n)), blinds);
await wait(p, 600);
s = await p.evaluate(() => [...window.__sfx.loops.keys()]);
check('blinds moving: the motor loop runs', s.some((k) => k.startsWith('motor:')), s.join(' '));
check('indoors: room tone and mains hum', s.includes('air') && s.includes('hum'), s.join(' '));
const den = room('den');
await teleport(p, [den.cx, 1.65, den.cz], [den.cx, 1.5, den.z0]);
await wait(p, 800);
s = await p.evaluate(() => [...window.__sfx.loops.keys()]);
check('the den TV (on at start) plays', s.some((k) => k.startsWith('tv:')), s.join(' '));
const fireOn = await p.evaluate(() => window.__signals.get('fire_great_room'));
await teleport(p, [gr.x1 - 2, 1.65, gr.cz], [gr.x1, 1.0, gr.cz]);
await wait(p, 800);
s = await p.evaluate(() => [...window.__sfx.loops.keys()]);
check('the fire burns audibly when on', !fireOn || s.some((k) => k.startsWith('fire:')), `fire=${fireOn} ${s.join(' ')}`);

// a vase: pick up, arm, throw at the wall: whoosh, shatter
eye = await faceItem(p, "(i) => i.def.type === 'pickup' && i.def.item === 'vase' && !i.host && i.root.position.y < 2");
if (eye) {
  m = await now(p);
  await pressE(p, 400);
  await p.keyboard.press('KeyI'); await wait(p, 300);
  const ids = await p.evaluate(() => window.__inventory.ids());
  for (let i = 0; i < ids.indexOf('vase'); i++) { await p.keyboard.press('ArrowDown'); await wait(p, 120); }
  await p.keyboard.press('Enter'); await wait(p, 300);
  await p.evaluate(() => { const c = window.__camera; c.lookAt(c.position.x + 1.2, c.position.y - 1.6, c.position.z); });   // at the floor
  await p.keyboard.press('Enter'); await wait(p, 1500);
  calls = await since(p, m);
  check('vase: picked up (glass), inventory open/close, armed, thrown, shatters', ['pickup_glass', 'ui_open', 'ui_arm', 'throw', 'shatter'].every((n) => has(calls, n)), calls.join(' '));
} else check('found a vase', false);
// a book landing whole, the flashlight, a battery, the tablet, being knocked down
m = await now(p);
await p.evaluate(() => window.__noise.emit({ position: window.__camera.position.clone().setY(0), loudness: 0.6, source: 'thud', item: 'book' }));
await p.evaluate(() => { window.__flashlight.toggle(); }); await wait(p, 200);
await p.evaluate(() => { window.__flashlight.battery = 0.3; }); await wait(p, 100);
await p.evaluate(() => { window.__flashlight.refill(); window.__flashlight.toggle(); }); await wait(p, 200);
await p.evaluate(() => window.__tablet.show()); await wait(p, 300);
await p.keyboard.press('ArrowDown'); await wait(p, 200);
await p.evaluate(() => window.__tablet.close()); await wait(p, 300);
await p.evaluate(() => window.__player.knockDown([window.__camera.position.x + 1, 0, window.__camera.position.z])); await wait(p, 900);
calls = await since(p, m);
check('book thud, flashlight clicks, battery, tablet open/move/close, knocked down (hit, fall)',
  ['thud_book', 'flashlight', 'battery', 'tablet_open', 'tablet_move', 'tablet_close', 'hit', 'fall'].every((n) => has(calls, n)), calls.join(' '));
await wait(p, 2500);
// outside (the terrace): the wind up, the room tone down
await teleport(p, [0, 1.57, 22.5], [0, 1.5, 40]);
await wait(p, 500);
s = await p.evaluate(() => [...window.__sfx.loops.entries()].map(([k, l]) => `${k}=${l.level.toFixed(2)}`));
check('outdoors: the wind up, the room tone down', s.includes('wind=1.00') && s.includes('air=0.20'), s.join(' '));
// levels of the synthesised loops (it can't listen: RMS / peak per buffer, and as played)
const loops = await p.evaluate(() => Object.fromEntries(Object.entries(window.__sfx.loopBuffers).map(([n, b]) => {
  let e = 0, pk = 0, len = 0;
  for (let c = 0; c < b.numberOfChannels; c++) { const d = b.getChannelData(c); for (const v of d) { e += v * v; pk = Math.max(pk, Math.abs(v)); } len += d.length; }
  // seam: the jump from the last sample to the first, against the typical step
  const d = b.getChannelData(0); let step = 0; for (let i = 1; i < d.length; i++) step += Math.abs(d[i] - d[i - 1]);
  return [n, { seconds: +b.duration.toFixed(1), rms: +(20 * Math.log10(Math.sqrt(e / len))).toFixed(1), peak: +(20 * Math.log10(pk)).toFixed(1), seam: +(Math.abs(d[0] - d[d.length - 1]) / (step / d.length)).toFixed(1) }];
})));
console.log('loops:', JSON.stringify(loops));
check('loops: sensible levels, no clipping, seamless', Object.values(loops).every((l) => l.peak <= -0.9 && l.rms > -26 && l.rms < -12 && l.seam < 8), JSON.stringify(loops));
await p.screenshot({ path: `${out}/house.png` });
await p.close();

// ================================================================ the Grimble
// (fast-forwarded: its walk in is cut to the last few metres, its stare at the glass to a second)
p = await open('&gdelay=0&hunt=now', [-19, 1.65, 0.5], [-26, 2.5, 0]);
await p.waitForFunction(() => window.__grimble?.state === 'walk', null, { timeout: 20000 });
await p.evaluate(() => { const g = window.__grimble; g.s = g.total - 5; });
m = await now(p);
await p.waitForFunction(() => window.__grimble.state === 'wave', null, { timeout: 30000 });
calls = await since(p, m);
check('outside: its footfalls, then three knocks on the glass', calls.filter((n) => n === 'g_step').length >= 1 && calls.filter((n) => n === 'g_knock').length === 3, calls.join(' '));
await p.evaluate(() => { const g = window.__grimble; g.t = g.o.waveTime; });
await p.waitForFunction(() => window.__grimble.state === 'watch', null, { timeout: 10000 });
await p.evaluate(() => { window.__grimble.stareFor = 0.5; });
const mSmash = await now(p);
m = mSmash;
await p.waitForFunction(() => window.__grimble.hunt?.broken, null, { timeout: 20000 });
await wait(p, 5000);
calls = await since(p, m);
const pk = await p.evaluate(() => window.__sfx.voices.filter((v) => v.busy).map((v) => v.name));
check('it smashes in: the smash, breathing, crawling', has(calls, 'g_smash') && calls.some((n) => n.startsWith('g_breath')) && (has(calls, 'g_hand') || has(calls, 'g_foot')), calls.join(' '));
await p.screenshot({ path: `${out}/grimble.png` });
// it hunts the player in the great room: growl on sight, the swipe's whoosh, the knockdown
await p.waitForFunction(() => window.__player.isDown, null, { timeout: 40000 }).catch(() => {});
await wait(p, 600);
calls = await since(p, mSmash);
check('the chase: growl, swipe whoosh, knocked down', has(calls, 'g_growl') && has(calls, 'g_swipe') && has(calls, 'hit'), calls.join(' '));
const counts = await p.evaluate(() => window.__sfx.counts);
console.log('grimble counts:', JSON.stringify(counts), 'busy voices:', pk.join(' '));
await p.close();

await b.close();
check('no console errors', errors.length === 0, errors.slice(0, 8).join(' | '));
console.log(fails ? `${fails} failed` : 'all passed');
process.exit(fails ? 1 : 0);
