// Distractions (viewer/devices.js): the devices that make noise on purpose, end to end. The
// Grimble breaks in at once while the player waits upstairs in the office (out of its sight);
// then each device is set off the way a player would (its own switch with E, the tablet's
// Devices page, the car key's panic button) and the test checks:
//   - the device sounds: noise events from its position, with its loudness, every few seconds
//     (alarms stop themselves; the switch follows), and its visible state changes
//   - the Grimble hears it and crawls to it: its head ends up near the nav-grid cell closest to
//     the device (side rooms are off its grid: the den TV pulls it to the great room's south
//     end, the car to the gallery corner by the garage, the bedroom clock to the dining room)
// A photo per device when it gets there (build/distractions/ by default).
// Usage: GT_BASE=http://localhost:8807 node viewer/tools/distractions.mjs [out-dir] [timeout-s=50] [fresh|sequence]
import { chromium } from 'playwright-core';
import fs from 'fs';
const [out = 'build/distractions', limit = '50', mode = 'fresh'] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
fs.mkdirSync('build/locks', { recursive: true });
let slot = null;
while (slot === null) {
  for (let i = 0; i < 3 && slot === null; i++) { try { fs.mkdirSync(`build/locks/browser_${i}`); slot = i; } catch {} }
  if (slot === null) await new Promise((ok) => setTimeout(ok, 3000));
}
const release = () => { try { fs.rmdirSync(`build/locks/browser_${slot}`); } catch {} };
process.on('exit', release);
process.on('SIGINT', () => { release(); process.exit(1); });

let fails = 0;
const check = (label, ok, detail = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}  ${detail}`); if (!ok) fails++; };

const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
// the player upstairs in the office: nowhere near a void, out of its sight
const OFFICE = [7, 4.6, -15];
// a fresh level with the Grimble just in (prowling by the broken glass)
async function openPage() {
  const p = await b.newPage({ viewport: { width: 960, height: 600 } });
  p.on('pageerror', (e) => console.log('pageerror:', e.message));
  await p.goto(`${process.env.GT_BASE || 'http://localhost:8765'}/viewer/index.html?level=mansion&gdelay=0&hunt=now` +
    `&pos=${OFFICE[0]},${OFFICE[1] + 1.65},${OFFICE[2]}&look=7,5.6,-11`);
  await p.waitForFunction(() => window.__loaded && window.__grimble && window.__hunt && window.__devices, null, { timeout: 180000 });
  await p.evaluate(() => {
    const g = window.__grimble, pl = window.__player, cam = window.__camera;
    document.querySelectorAll('#stats').forEach((e) => (e.style.display = 'none'));
    g.state = 'walk'; g.root.visible = true; g.s = g.total; g.place();     // straight to the glass
    const T = (window.__dt = { events: [], photo: null });
    window.__noise.on((e) => T.events.push({ t: window.__hunt.time, source: e.source, device: e.device,
      x: e.position.x, y: e.position.y, z: e.position.z, loudness: e.loudness }));
    const orig = pl.update.bind(pl);
    pl.update = (dt, input) => {
      if (T.photo) { cam.position.set(...T.photo.pos); cam.lookAt(...T.photo.at); return; }
      orig(dt, input);
    };
  });
  // in, past the smash and the crawl through the glass
  const t0 = Date.now();
  await p.waitForFunction(() => window.__grimble.state === 'inside' && !['smash', 'enter'].includes(window.__hunt.state),
    null, { timeout: 120000, polling: 250 });
  console.log(`(new level) inside after ${((Date.now() - t0) / 1000).toFixed(0)} s, state ${await p.evaluate(() => window.__hunt.state)}`);
  return p;
}
let p = null;

// how each device is set off: 'switch' = E on its own switch, 'tablet' = the Devices page, 'key' = the car key
const DEVICES = [
  { signal: 'car_alarm', how: 'key' },
  { signal: 'tv_den', how: 'switch', off: true },
  { signal: 'blender_kitchen', how: 'tablet' },
  { signal: 'doorbell', how: 'tablet' },
  { signal: 'music_great_room', how: 'switch', off: true },
  { signal: 'alarm', how: 'switch' },
];

for (const dev of DEVICES) {
  // fresh: each device in a new level, the Grimble just in by the great room glass. sequence: one
  // level, one device after another (it's pulled from end to end of the house); the current
  // Grimble finishes a search before it takes a new noise (and forgets one heard on the way), so
  // wait until it's prowling with nothing in mind
  if (!p || mode === 'fresh') { await p?.close(); p = await openPage(); }
  await p.waitForFunction(() => window.__hunt.state === 'prowl' && !window.__hunt.noise, null, { timeout: 30000, polling: 250 })
    .catch(() => console.log('   (still busy: ' + 'starting anyway)'));
  const info = await p.evaluate(({ signal, how }) => {
    const D = window.__devices, I = window.__interact, S = window.__signals, h = window.__hunt;
    const group = D.devices.filter((x) => x.signal === signal), d = group[0];
    if (!d) return { missing: true };
    // a pair of speakers is one source: the middle of the pair
    const pos = group.reduce((a, x) => a.add(D.position(x)), D.position(d).set(0, 0, 0)).divideScalar(group.length);
    const k = h.nav.nearest(pos.x, pos.z, 40), goal = k >= 0 ? h.nav.centre(k) : null;
    const T = window.__dt;
    T.events.length = 0;
    T.start = h.time;
    let msg = null;
    if (how === 'switch') {
      const it = I.items.find((x) => x.def.type === 'switch' && x.signal === signal);
      msg = it ? I.use(it, window.__player.boxAt(window.__player.pos).clone()) ?? 'used switch' : 'no switch';
    } else if (how === 'tablet') {
      const tb = window.__tablet;
      tb.show(); tb.setPage('devices');
      tb.row = tb.deviceRows().findIndex((r) => r.signal === signal) + 1;
      tb.key('Enter'); msg = tb.msg; tb.close();
    } else {
      const key = I.items.find((x) => x.def.item === 'car_key');
      msg = D.useRemote(key.def);
    }
    const hd = h.chain ? h.chain.hd : { x: h.root.position.x, y: h.root.position.z };
    return { pos: [pos.x, pos.y, pos.z], goal: goal && [goal.x, goal.y], loud: d.loudness, label: d.label, msg,
      on: S.get(signal), state: d.state, dist0: Math.hypot(hd.x - pos.x, hd.y - pos.z), delay: d.delay, for: d.for };
  }, dev);
  if (info.missing) { check(`${dev.signal}: device in the level`, false); continue; }
  console.log(`-- ${info.label} (${dev.signal}, ${dev.how}): "${info.msg}", device at ${info.pos.map((v) => v.toFixed(2)).join(', ')}, ` +
    `goal cell ${info.goal?.map((v) => v.toFixed(1)).join(', ')}, Grimble ${info.dist0.toFixed(1)} m away`);
  check(`${info.label}: on`, info.on === true && (info.state === 'sounding' || (info.delay > 0 && info.state === 'waiting')), `state ${info.state}`);
  // follow the Grimble's head until it's near the goal cell
  let best = 1e9, arrivedAt = null, heard = false, lastLog = 0;
  const tStart = Date.now();
  while ((Date.now() - tStart) / 1000 < +limit + (info.delay || 0)) {
    await p.waitForTimeout(250);
    const s = await p.evaluate((goal) => {
      const h = window.__hunt, hd = h.chain ? h.chain.hd : { x: h.root.position.x, y: h.root.position.z };
      return { d: Math.hypot(hd.x - goal[0], hd.y - goal[1]), st: h.state, n: h.noise && [h.noise.x, h.noise.y], t: h.time - window.__dt.start,
        hx: hd.x, hz: hd.y };
    }, info.goal);
    if (s.n && Math.hypot(s.n[0] - info.pos[0], s.n[1] - info.pos[2]) < 0.5) heard = true;
    best = Math.min(best, s.d);
    if (s.t - lastLog > 5) { lastLog = s.t; console.log(`   t ${s.t.toFixed(0)} s  ${s.st}  head ${s.hx.toFixed(1)}, ${s.hz.toFixed(1)}  ${s.d.toFixed(1)} m from the goal`); }
    if (s.d < 3.0) { arrivedAt = s.t; break; }
  }
  const ev = await p.evaluate(() => window.__dt.events);
  const mine = ev.filter((e) => Math.hypot(e.x - info.pos[0], e.z - info.pos[2]) < 0.6);
  check(`${info.label}: noise events from the device`, mine.length >= 2 && mine.every((e) => e.loudness === info.loud),
    `${mine.length} events, loudness ${info.loud}, source ${mine[0]?.source}`);
  if (info.delay > 0) check(`${info.label}: silent for its delay`, mine.length && mine[0].t - (await p.evaluate(() => window.__dt.start)) >= info.delay - 0.2,
    `first noise after ${(mine[0]?.t - (await p.evaluate(() => window.__dt.start))).toFixed(1)} s`);
  check(`${info.label}: the Grimble heard it`, heard);
  check(`${info.label}: the Grimble got there`, arrivedAt !== null, arrivedAt !== null ? `in ${arrivedAt.toFixed(1)} s` : `closest ${best.toFixed(1)} m`);
  // photo: from above, behind the device's goal cell, looking at the Grimble
  await p.evaluate((goal) => {
    const h = window.__hunt, hd = h.chain ? h.chain.hd : { x: h.root.position.x, y: h.root.position.z };
    const dx = hd.x - goal[0], dz = hd.y - goal[1], l = Math.hypot(dx, dz) || 1;
    window.__dt.photo = { pos: [hd.x + (dx / l) * 5 + 0.5, 3.6, hd.y + (dz / l) * 5 + 0.5], at: [hd.x, 0.8, hd.y] };
  }, info.goal);
  await p.waitForTimeout(400);
  await p.screenshot({ path: `${out}/${mode}_${dev.signal}.png` });
  await p.evaluate(() => { window.__dt.photo = null; });
  if (info.for) {
    // an alarm stops itself, and its switch follows
    await p.waitForFunction(({ signal }) => window.__signals.get(signal) === false, dev, { timeout: (info.for + (info.delay || 0) + 20) * 1000, polling: 250 });
    const sw = await p.evaluate(({ signal }) => {
      const it = window.__interact.items.find((x) => x.def.type === 'switch' && x.signal === signal);
      const d = window.__devices.devices.find((x) => x.signal === signal);
      return { sw: it ? it.target : null, state: d.state };
    }, dev);
    check(`${info.label}: stops by itself`, sw.state === 'off' && (sw.sw === null || sw.sw === 0), JSON.stringify(sw));
  }
  if (dev.off) await p.evaluate(({ signal }) => window.__signals.set(signal, false), dev);
  await p.waitForTimeout(1500);
}

// power off: electric devices fall silent; the car alarm (its own battery) doesn't
const pw = await p.evaluate(async () => {
  const S = window.__signals, D = window.__devices;
  S.set('tv_den', true); S.set('car_alarm', true);
  S.set('power', false);
  const st = Object.fromEntries(D.devices.map((d) => [d.id, d.state]));
  S.set('power', true);
  const back = D.devices.find((d) => d.signal === 'tv_den').state;
  S.set('tv_den', false); S.set('car_alarm', false);
  return { st, back };
});
check('power off silences the TV', pw.st['tv@den'] === 'off', JSON.stringify(pw.st));
check('the car alarm runs without house power', pw.st['car_alarm@garage'] === 'sounding');
check('power back: the TV plays again', pw.back === 'sounding');
// the tablet's Devices page: one row per signal, offline without power
const tab = await p.evaluate(() => {
  const tb = window.__tablet;
  tb.show(); tb.setPage('devices');
  const rows = tb.deviceRows().map((r) => r.signal);
  const html = tb.el.textContent;
  window.__signals.set('power', false);
  tb.row = 1; tb.key('Enter');
  const offline = tb.msg;
  window.__signals.set('power', true);
  tb.close();
  return { rows, html, offline };
});
check('tablet: Devices page lists the hub devices once each', new Set(tab.rows).size === tab.rows.length && tab.rows.length >= 5 && !tab.rows.includes('car_alarm'), tab.rows.join(', '));
check('tablet: offline without power', /offline/i.test(tab.offline), tab.offline);

// the car key the way a player uses it: take it (E), arm it (I, Enter), then Enter = the panic button
await p.mouse.click(480, 300);
await p.waitForTimeout(300);
await p.evaluate(() => {
  const I = window.__interact, inv = window.__inventory;
  const key = I.items.find((x) => x.def.item === 'car_key');
  I.use(key, window.__player.boxAt(window.__player.pos).clone());
  inv.sel = inv.ids().indexOf('car_key'); inv.armSelected();
});
await p.waitForTimeout(300);
const hintBefore = await p.textContent('#hint');
await p.keyboard.press('Enter');
await p.waitForTimeout(300);
const fob = await p.evaluate(() => ({ on: window.__signals.get('car_alarm'), toast: window.__toast(), hint: document.getElementById('hint').textContent }));
check('car key: armed hint', /Enter · Car alarm on/.test(hintBefore), hintBefore);
check('car key: Enter sets off the car alarm', fob.on === true && /Car alarm · on/.test(fob.toast), JSON.stringify(fob));
await p.keyboard.press('Enter');
await p.waitForTimeout(300);
check('car key: Enter again stops it', (await p.evaluate(() => window.__signals.get('car_alarm'))) === false);

await b.close();
console.log(fails ? `${fails} FAILED` : 'ALL PASS');
process.exit(fails ? 1 : 0);
