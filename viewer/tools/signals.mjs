// Interactivity v2 (prompts/interactivity.md): switches, signals, react nodes, power gating,
// `use` with an item, the flashlight and its battery, noise events, the tablet, knockdown.
// The level may not have switch props yet, so the test builds a small fixture in the page
// (THREE objects carrying userData.interact / userData.react) in the upper north gallery and
// registers it through the public API (window.__interact.register). Usage: node signals.mjs [out-dir]
import { chromium } from 'playwright-core';
import { room, url } from './level.mjs';
const out = process.argv[2] || '.';
const g = room('ugallery_n');
const Z = g.z1 - 1.0;                 // player line, 1 m in from the courtyard side
const FIX_Z = g.z1 - 2.0;             // fixtures 1 m north of it
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 1100, height: 700 } });
p.on('pageerror', (e) => console.log('pageerror:', e.message));
let fails = 0;
const check = (label, ok, detail = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}  ${detail}`); if (!ok) fails++; };
const at = (x) => [x, g.y + 1.65, Z];
const lookN = (x) => [x, g.y + 1.2, FIX_Z];

await p.goto(url(at(4), lookN(4)) + '&grimble=0');
await p.waitForFunction(() => window.__loaded, null, { timeout: 90000 });
await p.mouse.click(550, 350); await p.waitForTimeout(400);
const press = async (k, wait = 350) => { await p.keyboard.press(k); await p.waitForTimeout(wait); };
const hint = () => p.textContent('#hint');
const toast = () => p.evaluate(() => window.__toast());
const teleport = (pos, look) => p.evaluate(([pos, look]) => {
  window.__player.pos.set(pos[0], pos[1] - 1.65, pos[2]); window.__player.vel.set(0, 0, 0);
  window.__player.syncCamera(); window.__camera.lookAt(...look);
}, [pos, look]);

// ---------------------------------------------------------------- the fixture
await p.evaluate(async ([y, fz]) => {
  const THREE = await import('three');
  const { scene } = window.__three, it = window.__interact;
  const box = (w, h, d, mat) => new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat ?? new THREE.MeshStandardMaterial({ color: 0xdddddd }));
  const place = (obj, x, h) => { obj.position.set(x, y + h, fz); scene.add(obj); obj.updateMatrixWorld(true); return obj; };
  const F = (window.__fx_test = {});
  // switch plate: a rocker that tips 12 degrees, with a status LED
  const plate = new THREE.Group(); plate.name = 'Test_Switch';
  const rocker = box(0.03, 0.06, 0.02); rocker.name = 'Test_Switch_Rocker';
  rocker.userData.interact = { type: 'switch', prompt: 'Turn on', promptActive: 'Turn off', signal: 'lights_test', state: false,
    range: 1.2, travel: { axis: 'x', angle: 12 }, indicator: 'Test_Switch_LED' };
  const led = box(0.006, 0.006, 0.004, new THREE.MeshStandardMaterial({ color: 0x111111, emissive: 0x20ff40 })); led.name = 'Test_Switch_LED';
  led.position.set(0, -0.045, 0);
  plate.add(rocker, led);
  F.switchItems = it.register(place(plate, 4, 1.2));
  // a second switch on the same signal far down the gallery (two-way switching)
  const plate2 = plate.clone(true); plate2.name = 'Test_Switch2';
  plate2.children[0].userData = JSON.parse(JSON.stringify(rocker.userData));
  F.switch2 = it.register(place(plate2, 12, 1.2))[0];
  // a lamp: glow material (emissive), a shell shown when on, a point light
  const lamp = new THREE.Group(); lamp.name = 'Test_Lamp';
  const glow = box(0.2, 0.2, 0.2, new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xffeecc, emissiveIntensity: 2 }));
  glow.name = 'Test_Lamp_Glow'; glow.userData.react = { signal: 'lights_test', on: { emissive: 1 } };
  const shell = box(0.25, 0.25, 0.25, new THREE.MeshStandardMaterial({ color: 0xffffff, transparent: true, opacity: 0.3 }));
  shell.name = 'Test_Lamp_Shell'; shell.userData.react = { signal: 'lights_test', on: 'show' };
  const bulb = new THREE.Object3D(); bulb.name = 'Test_Lamp_Bulb'; bulb.position.y = 0.3;
  bulb.userData.react = [{ signal: 'lights_test', on: { light: { color: [1, 0.9, 0.8], intensity: 5, distance: 6 } } }];
  lamp.add(glow, shell, bulb);
  it.register(place(lamp, 6, 0.4));
  // the same lamp placed with a signal override
  const lamp2 = lamp.clone(true); lamp2.name = 'Test_Lamp2';
  lamp2.traverse((o) => { if (o.userData.react) o.userData = JSON.parse(JSON.stringify(o.userData)); });
  F.lamp2 = it.register(place(lamp2, 7, 0.4), { signal: 'lights_other' });
  // motorised blind: rolls down 2.4 m when blinds_test is on; blocks the Grimble's sight
  const blind = box(1.6, 2.4, 0.04); blind.name = 'Test_Blind';
  blind.userData.react = { signal: 'blinds_test', on: { slide: { axis: 'y', distance: -2.4 } }, duration: 0.5, block_sight: true };
  it.register(place(blind, -4, 2.4 + 1.25));
  // breaker: a `use` point that needs a fuse and restores power; placed with state false
  const breaker = new THREE.Group(); breaker.name = 'Test_Breaker';
  const door = box(0.4, 0.5, 0.1); door.name = 'Test_Breaker_Slot';
  door.userData.interact = { type: 'use', needs: 'fuse', consume: true, prompt: 'Insert fuse', promptDone: 'Power restored',
    signal: 'power', value: true, range: 1.2 };
  breaker.add(door);
  it.register(place(breaker, 9, 1.3), { state: false });
  // a fuse on a stand beside it
  const fuse = box(0.03, 0.08, 0.03, new THREE.MeshStandardMaterial({ color: 0xc0a050 })); fuse.name = 'Test_Fuse';
  fuse.userData.interact = { type: 'pickup', item: 'fuse', name: 'Fuse', prompt: 'Take fuse', range: 1.2 };
  it.register(place(fuse, 9.6, 0.9));
  // load order: a lamp on lights_order registered before its switch (authored state: on)
  const lamp3 = lamp.clone(true); lamp3.name = 'Test_Lamp3';
  lamp3.traverse((o) => { if (o.userData.react) o.userData = JSON.parse(JSON.stringify(o.userData)); });
  it.register(place(lamp3, 8, 0.4), { signal: 'lights_order' });
  const plate3 = plate.clone(true); plate3.name = 'Test_Switch3';
  plate3.children[0].userData = JSON.parse(JSON.stringify({ ...rocker.userData, interact: { ...rocker.userData.interact, signal: 'lights_order', state: true } }));
  it.register(place(plate3, 14, 1.2));
  F.order = () => ({ value: window.__signals.get('lights_order'), glow: +lamp3.children[0].material.emissiveIntensity.toFixed(2),
    shared: lamp3.children[0].material === lamp2.children[0].material });
  F.state = () => {
    const r = (n) => it.reactors.find((x) => x.node.name === n);
    return {
      lights: window.__signals.get('lights_test'), power: window.__signals.get('power'), blinds: window.__signals.get('blinds_test'),
      rocker: +it.items.find((i) => i.node.name === 'Test_Switch_Rocker').node.rotation.x.toFixed(3),
      switch2: F.switch2.t,
      led: +led.material.emissiveIntensity.toFixed(2),
      glow: +glow.material.emissiveIntensity.toFixed(2), shell: shell.material.visible,
      light: Math.max(...it.lights.map((l) => l.intensity)),
      lamp2: +lamp2.children[0].material.emissiveIntensity.toFixed(2),
      blindY: +(blind.position.y - y).toFixed(2), blockers: it.sightBlockers().length,
      blocks: it.blocksSight(new THREE.Vector3(-4, y + 1.5, fz - 3), new THREE.Vector3(-4, y + 1.5, fz + 3)),
      lamp2Signal: r('Test_Lamp2_Glow')?.signal ?? F.lamp2.find((x) => x.isReactor)?.signal,
      fuse: window.__inventory.count('fuse'), armed: window.__inventory.armed,
    };
  };
}, [g.y, FIX_Z]);
const S = () => p.evaluate(() => window.__fx_test.state());

// ---------------------------------------------------------------- power starts off (breaker state)
let s = await S();
check('placement state: the breaker placed with state false starts the power off', s.power === false, `power=${s.power}`);
await p.evaluate(() => window.__signals.set('power', true));
await p.waitForTimeout(300);
const order = await p.evaluate(() => window.__fx_test.order());
check('a switch\'s authored state wins over a reactor loaded before it', order.value === true && order.glow === 2, JSON.stringify(order));
await p.evaluate(() => window.__signals.set('lights_order', false));

// ---------------------------------------------------------------- switch + reacts
await teleport(at(4), lookN(4)); await p.waitForTimeout(200);
s = await S();
check('switch offers "Turn on" and everything starts off', (await hint()).includes('E · Turn on') && !s.lights && s.glow === 0 && !s.shell && s.light === 0,
  `hint="${await hint()}" ${JSON.stringify(s)}`);
await press('KeyE', 500); s = await S();
check('E turns lights_test on, the rocker tips, its LED lights', s.lights === true && Math.abs(s.rocker - 0.209) < 0.01 && s.led > 0,
  `lights=${s.lights} rocker=${s.rocker} led=${s.led}`);
check('the other switch on that signal follows it', s.switch2 === 1, `t=${s.switch2}`);
check('react: emissive back to as authored, shell shown, point light on', s.glow === 2 && s.shell && s.light === 5,
  `glow=${s.glow} shell=${s.shell} light=${s.light}`);
check('hint now offers "Turn off"', (await hint()).includes('E · Turn off'), `hint="${await hint()}"`);
check('placement signal override: lamp 2 follows lights_other, not lights_test', s.lamp2 === 0 && s.lamp2Signal === 'lights_other', `lamp2=${s.lamp2} signal=${s.lamp2Signal}`);

// ---------------------------------------------------------------- blinds / sight
await p.evaluate(() => window.__signals.set('blinds_test', true)); await p.waitForTimeout(800); s = await S();
check('blinds roll down 2.4 m and block sight', Math.abs(s.blindY - 1.25) < 0.01 && s.blockers === 1 && s.blocks, `y=${s.blindY} blockers=${s.blockers} blocks=${s.blocks}`);
await p.evaluate(() => window.__signals.set('blinds_test', false)); await p.waitForTimeout(800); s = await S();
check('blinds up: no sight blockers', Math.abs(s.blindY - 3.65) < 0.01 && s.blockers === 0 && !s.blocks, `y=${s.blindY} blockers=${s.blockers}`);

// ---------------------------------------------------------------- power gating
await p.evaluate(() => window.__signals.set('power', false)); await p.waitForTimeout(300); s = await S();
check('power off: the lamp goes dark although its switch is on', s.lights === true && s.glow === 0 && !s.shell && s.light === 0 && s.led === 0,
  `glow=${s.glow} shell=${s.shell} light=${s.light} led=${s.led}`);

// ---------------------------------------------------------------- use with an item (fuse)
await teleport(at(9), lookN(9)); await p.waitForTimeout(200);
check('the fuse on the stand is offered first', (await hint()).includes('Take fuse'), `hint="${await hint()}"`);
await p.evaluate(() => { const f = window.__interact.items.find((i) => i.node.name === 'Test_Fuse'); f.node.position.x += 3; f.node.updateMatrixWorld(true); });
await p.waitForTimeout(200);
check('without the fuse, the breaker says what is missing', (await hint()).includes('needs a fuse'), `hint="${await hint()}"`);
await press('KeyE'); check('E on it: "Needs a fuse"', (await toast()).includes('Needs a fuse'), `toast="${await toast()}"`);
await p.evaluate(() => { const f = window.__interact.items.find((i) => i.node.name === 'Test_Fuse'); f.node.position.x -= 3; f.node.updateMatrixWorld(true); });
await p.waitForTimeout(200);
await press('KeyE'); s = await S();
check('E takes the fuse', s.fuse === 1, `fuse=${s.fuse}`);
await press('KeyI', 200);
const ids = await p.evaluate(() => window.__inventory.ids());
for (let i = 0; i < ids.indexOf('fuse'); i++) await press('ArrowDown', 80);
await press('Enter', 300);
check('armed fuse: hint "Enter · Insert fuse"', (await hint()).includes('Enter · Insert fuse'), `hint="${await hint()}"`);
await press('Enter', 400); s = await S();
check('Enter inserts it: power back, fuse used up, lamp on again', s.power === true && s.fuse === 0 && s.armed === null && s.glow === 2 && s.light === 5,
  `power=${s.power} fuse=${s.fuse} glow=${s.glow} toast="${await toast()}"`);

// ---------------------------------------------------------------- flashlight
const F = () => p.evaluate(() => ({ on: window.__flashlight.on, battery: window.__flashlight.battery, intensity: window.__flashlight.spot?.intensity ?? -1,
  meter: document.getElementById('battery').classList.contains('show'), batteries: window.__inventory.count('battery') }));
await p.evaluate(async () => {
  const THREE = await import('three');
  const torch = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.025, 0.18), new THREE.MeshStandardMaterial({ color: 0x222222 }));
  window.__inventory.add('flashlight', 'Flashlight', torch, { item: 'flashlight' });
  window.__inventory.armed = 'flashlight'; window.__inventory.changed();
});
await p.waitForTimeout(300);
check('armed flashlight: hint "Enter · Flashlight on", battery meter shown', (await hint()).includes('Flashlight on') && (await F()).meter, `hint="${await hint()}"`);
await press('Enter', 100);
let f0 = await F();
await p.waitForTimeout(2000);
let f1 = await F();
const drained = f0.battery - f1.battery;
check('Enter: the spot is on and the battery drains (~4 min per battery)', f1.on && f1.intensity > 0 && drained > 2 / 240 * 0.7 && drained < 2 / 240 * 1.6,
  `intensity=${f1.intensity} drained=${drained.toFixed(4)} in 2 s (expect ${(2 / 240).toFixed(4)})`);
await p.screenshot({ path: `${out}/signals_flashlight.png` });
await press('Enter', 100); f1 = await F();
check('Enter again: off', !f1.on && f1.intensity === 0);
await p.evaluate(() => { window.__flashlight.battery = 0.0004; });
await press('Enter', 400); f1 = await F();
check('the battery runs flat: the light goes out', !f1.on && f1.battery === 0 && f1.intensity === 0, JSON.stringify(f1));
await press('Enter', 200);
check('a flat flashlight says so', (await toast()).includes('flat'), `toast="${await toast()}"`);
await p.evaluate(() => window.__inventory.add('battery', 'Battery', null, { item: 'battery' }));
await press('Enter', 200); f1 = await F();
check('with a spare battery, Enter swaps it in and turns on', f1.on && f1.battery > 0.99 && f1.batteries === 0, JSON.stringify(f1));
await press('Enter', 100);
await p.evaluate(() => { window.__flashlight.battery = 0.3; window.__inventory.add('battery', 'Battery', null, { item: 'battery' }); window.__inventory.armed = 'battery'; window.__inventory.changed(); });
await press('Enter', 200); f1 = await F();
check('an armed battery refills the flashlight', f1.battery > 0.99 && f1.batteries === 0, JSON.stringify(f1));

// ---------------------------------------------------------------- noise from a throw
await teleport(at(10), [10, g.y + 1.4, g.z0]);
await p.evaluate(async () => {
  const THREE = await import('three');
  window.__heard = [];
  window.__noise.on((e) => window.__heard.push({ x: e.position.x, y: e.position.y, z: e.position.z, loudness: e.loudness }));
  const jar = new THREE.Mesh(new THREE.SphereGeometry(0.06), new THREE.MeshStandardMaterial({ color: 0x88aacc, transparent: true, opacity: 0.6 }));
  window.__inventory.add('jar', 'Jar', jar, { item: 'jar', throwable: true, noise: 0.6 });
  window.__inventory.armed = 'jar'; window.__inventory.changed();
});
await p.waitForTimeout(150);
await press('Enter', 1500);
const heard = await p.evaluate(() => window.__heard);
check('a thrown jar hitting the wall is a noise event with its loudness', heard.length === 1 && heard[0].loudness === 0.6 && Math.abs(heard[0].z - g.z0) < 0.6,
  JSON.stringify(heard));

// ---------------------------------------------------------------- a whole throwable (book): thuds, rests, can be taken again
await p.evaluate(async () => {
  const THREE = await import('three');
  window.__heard = [];
  const book = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.03, 0.23), new THREE.MeshStandardMaterial({ color: 0x7a3b2a }));
  book.name = 'Test_Book';
  const def = { type: 'pickup', item: 'book', name: 'Book', prompt: 'Take book', range: 1.4, throwable: true, noise: 0.6, shatter: false };
  book.userData.interact = def;
  window.__inventory.add('book', 'Book', book, def);
  window.__inventory.armed = 'book'; window.__inventory.changed();
});
await p.waitForTimeout(150);
await press('Enter', 2500);
const book = await p.evaluate(() => {
  const it = window.__interact.items.filter((i) => i.node.name === 'Test_Book' && !i.taken);
  const n = it[0]?.node;
  return { heard: window.__heard.length, loudness: window.__heard[0]?.loudness, flying: window.__throwables.flying.length,
    shards: window.__throwables.shards.length, pickups: it.length, y: n ? n.position.y : null };
});
const shardsBefore = 1;   // the jar's
check('a book thuds (one noise), lands whole on the floor and can be taken again',
  book.heard === 1 && book.loudness === 0.6 && book.flying === 0 && book.shards === shardsBefore && book.pickups === 1 && Math.abs(book.y - g.y) < 0.2,
  JSON.stringify(book));

// ---------------------------------------------------------------- tablet
await teleport(at(4), lookN(4));
await p.evaluate(async () => {
  const THREE = await import('three');
  window.__inventory.add('tablet', 'Tablet', new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.01, 0.17), new THREE.MeshStandardMaterial()), { item: 'tablet' });
  window.__inventory.armed = 'tablet'; window.__inventory.changed();
});
await p.waitForTimeout(200);
check('armed tablet: hint "Enter · Open tablet"', (await hint()).includes('Open tablet'), `hint="${await hint()}"`);
const T = () => p.evaluate(() => {
  const t = window.__tablet, el = document.getElementById('tablet');
  return { open: t.open, shown: el.classList.contains('open'), page: t.page, row: t.row, col: t.col, cam: t.cam, frames: t.frames,
    rooms: t.rooms().map((r) => r.room), text: el.textContent, ms: +t.lastFeedMs.toFixed(2), calls: t.feedCalls,
    lights: window.__signals.get('lights_test'), blinds: window.__signals.get('blinds_test'),
    look: window.__camera.quaternion.toArray().map((v) => +v.toFixed(4)).join(','), pos: window.__player.pos.toArray().map((v) => +v.toFixed(3)).join(',') };
});
await press('Enter', 300); let t = await T();
check('Enter opens the tablet with the rooms that have light / blinds signals', t.open && t.shown && t.rooms.includes('test') && t.rooms.includes('other') && t.text.includes('Lights'),
  `rooms=${t.rooms}`);
await p.screenshot({ path: `${out}/signals_tablet_rooms.png` });
const row = t.rooms.indexOf('test') + 1;
while ((await T()).row !== row) await press((await T()).row < row ? 'ArrowDown' : 'ArrowUp', 60);
const lightsBefore = (await T()).lights;
await press('Enter', 200); t = await T();
check('Enter on a room toggles its lights', t.lights === !lightsBefore, `lights ${lightsBefore} -> ${t.lights}`);
await press('ArrowRight', 100); await press('Enter', 200); t = await T();
check('→ then Enter toggles its blinds', t.col === 1 && t.blinds === true, `col=${t.col} blinds=${t.blinds}`);
await p.keyboard.down('KeyW'); await p.waitForTimeout(300); await p.keyboard.up('KeyW');
const t2 = await T();
check('the player does not move or turn while the tablet is open', t2.pos === t.pos && t2.look === t.look);
while ((await T()).row !== 0) await press('ArrowUp', 60);
await press('ArrowRight', 1200); t = await T();
const pix = await p.evaluate(() => {
  const d = window.__tablet.ctx.getImageData(0, 0, 320, 180).data; let sum = 0, n = 0;
  for (let i = 0; i < d.length; i += 16) { sum += d[i] + d[i + 1] + d[i + 2]; n++; }
  return sum / n / 3;
});
check('Cameras page: a live feed renders at ~5 fps into the panel', t.page === 'cameras' && t.frames >= 4 && t.frames <= 9 && pix > 10,
  `frames=${t.frames} in ~1.2 s, mean pixel=${pix.toFixed(1)}, feed ${t.ms} ms CPU, ${t.calls} draw calls`);
await p.screenshot({ path: `${out}/signals_tablet_feed.png` });
const cam0 = (await T()).cam;
await press('ArrowDown', 500); t = await T();
check('↓ picks the next camera', t.cam === cam0 + 1 && t.row === t.cam + 1, `cam ${cam0} -> ${t.cam}`);
await p.evaluate(() => window.__signals.set('power', false)); await p.waitForTimeout(200); t = await T();
check('power off: the tablet is offline', t.text.includes('OFFLINE') && t.text.includes('NO SIGNAL'));
await p.evaluate(() => window.__signals.set('power', true));
await press('KeyI', 200); t = await T();
check('I closes it', !t.open && !t.shown);
await press('Delete', 100);

// ---------------------------------------------------------------- knockdown
const K = () => p.evaluate(() => {
  const pl = window.__player, cam = window.__camera;
  const up = window.__camera.up.clone().applyQuaternion(cam.quaternion);
  return { down: pl.isDown, eye: +pl.eye.toFixed(2), x: pl.pos.x, y: pl.pos.y, z: pl.pos.z, tilt: Math.acos(Math.min(1, up.y)) * 180 / Math.PI,
           overlap: pl.overlapping(pl.pos).length };
});
await teleport([10, g.y + 1.65, g.z0 + 1.2], [14, g.y + 1.65, g.z0 + 1.2]);
await p.waitForTimeout(300);
let k0 = await K();
await p.evaluate(async () => { const THREE = await import('three'); const pl = window.__player; window.__player.knockDown(new THREE.Vector3(pl.pos.x, pl.pos.y, pl.pos.z - 2)); });
await p.keyboard.down('KeyW');
await p.waitForTimeout(1100);
let k1 = await K();
check('knockDown: down, eye near the floor, view rolled over', k1.down && k1.eye < 0.5 && k1.tilt > 50, `eye=${k1.eye} tilt=${k1.tilt.toFixed(0)}°`);
check('shoved away from the blow (+z), clear of every collider', k1.z - k0.z > 1.0 && k1.overlap === 0 && k1.z < g.z1, `moved ${(k1.z - k0.z).toFixed(2)} m, overlap=${k1.overlap}`);
await p.waitForTimeout(600);
const k2 = await K();
check('input is ignored while down (W held)', Math.hypot(k2.x - k1.x, k2.z - k1.z) < 0.1, `moved ${Math.hypot(k2.x - k1.x, k2.z - k1.z).toFixed(3)} m`);
await p.keyboard.up('KeyW');
await p.waitForTimeout(1200);
const k3 = await K();
check('gets up after ~2.5 s: eye back up, view level', !k3.down && k3.eye > 1.5 && k3.tilt < 3, `eye=${k3.eye} tilt=${k3.tilt.toFixed(1)}°`);
// into the north wall: shoved toward it, stops at it
await teleport([10.5, g.y + 1.65, g.z0 + 0.9], [10.5, g.y + 1.65, g.z1]);
await p.waitForTimeout(200);
await p.evaluate(() => window.__player.knockDown({ dir: { x: 0, y: 0, z: 1 } }));   // the blow comes from the south
await p.waitForTimeout(1000);
const k4 = await K();
check('shoved into a wall: stops at it, never inside', k4.overlap === 0 && k4.z > g.z0 && k4.z < g.z0 + 0.9, `z=${k4.z.toFixed(2)} (wall at ${g.z0})`);
await p.waitForTimeout(2000);
check('and gets up there', !(await K()).down);

await b.close();
console.log(fails ? `${fails} failed` : 'all passed');
process.exit(fails ? 1 : 0);
