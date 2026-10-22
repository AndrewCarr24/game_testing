// The estate's car, driven (viewer/vehicle.js): scripted drives with checks and screenshots from
// the driver's seat at each stage.
//   node viewer/tools/car_drive.mjs [trip|road|keys] [--out dir] [--speed m/s] [--ts timeScale]
//   trip (default)  the whole trip in one tab, the way the game runs it: the house (E at the
//                   driver's door, the seat, the garage door from its switch, the keys), out of
//                   the garage, down the drive, out through the gate (the house hands the car to the
//                   wilderness's iframe), down the county road (the four hairpins, the river leg),
//                   across the seam into the town (the iframe reloads into laurel_town), Main
//                   Street; then turned round and back: the seam, the cove, up the hairpins, in
//                   through the gate (the wilderness hands the car back to the house), up the drive
//                   into the garage, parked, E out
//   road            wild.html on its own: the cove's road out and back (car=drive / car=back:<m>)
//   keys            the house only: E, W/S, A/D, Space, V, E out (real key presses)
// Checks per leg: never through the ground (the body over the heightfield / floor), never stuck
// (progress along the line), the number of hits, the handoffs. The car is driven by its autopilot
// (pure pursuit on the right-hand lane, braking for curvature) through the same controls as the
// keys, at --ts x real time (default 2.5). Shots: build/car_drive/ (or --out).
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { ensureServer, BASE } from './server.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const argv = process.argv.slice(2);
const opt = (k, d) => { const i = argv.indexOf(k); if (i < 0) return d; const v = argv[i + 1]; argv.splice(i, 2); return v; };
const out = opt('--out', path.join(root, 'build/car_drive'));
const SPEED = +opt('--speed', 22);
const TS = +opt('--ts', 2.5);
const stages = argv.length ? argv : ['trip'];
fs.mkdirSync(out, { recursive: true });
const locks = path.join(root, 'build/locks');
let slot = null;
for (let t = 0; !slot; t++) {
  for (let i = 0; i < 3 && !slot; i++) { try { fs.mkdirSync(path.join(locks, `browser_${i}`)); slot = path.join(locks, `browser_${i}`); } catch {} }
  if (!slot) { if (t === 0) console.log('waiting for a browser slot...'); await new Promise((r) => setTimeout(r, 2000)); }
}
const release = () => { try { fs.rmdirSync(slot); } catch {} };
process.on('exit', release);
process.on('SIGINT', () => { release(); process.exit(1); });
const stop = await ensureServer();
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal', '--autoplay-policy=no-user-gesture-required'] });
let fails = 0;
const check = (ok, msg) => { console.log(`${ok ? 'ok  ' : 'FAIL'} ${msg}`); if (!ok) fails++; return ok; };
const legs = [];

// ---- in-page path makers (evaluated where the car is)
// the county road's right-hand lane (window.__road's centreline), from the point nearest the car,
// optionally reversed, up to `limit` metres / past x = `untilX`, then `extra` points
const LANE = (a) => {
  const C = window.__road.userData.centreline.map((p) => [p.x, p.z]);
  if (a.back) C.reverse();
  const L = [];
  for (let i = 0; i < C.length; i++) {
    const p = C[Math.max(0, i - 2)], q = C[Math.min(C.length - 1, i + 2)];
    const tx = q[0] - p[0], tz = q[1] - p[1], tl = Math.hypot(tx, tz) || 1;
    L.push([C[i][0] - (tz / tl) * 1.7, C[i][1] + (tx / tl) * 1.7]);
  }
  const c = window.__vehicle.pos;
  let bi = 0, bd = Infinity;
  L.forEach((p, i) => { const d = (p[0] - c.x) ** 2 + (p[1] - c.z) ** 2; if (d < bd) { bd = d; bi = i; } });
  // (start a few metres ahead of the car)
  let s = 0, k = bi;
  while (k < L.length - 1 && s < 4) { s += Math.hypot(L[k + 1][0] - L[k][0], L[k + 1][1] - L[k][1]); k++; }
  let path = [[c.x, c.z], ...L.slice(k)];
  if (a.limit) { let acc = 0, j = 1; for (; j < path.length && acc < a.limit; j++) acc += Math.hypot(path[j][0] - path[j - 1][0], path[j][1] - path[j - 1][1]); path = path.slice(0, j); }
  if (a.untilX != null) { const j = path.findIndex((p, i) => i > 0 && (a.west ? p[0] < a.untilX : p[0] > a.untilX)); if (j > 0) path = path.slice(0, j + 1); }
  return [...path, ...(a.extra || [])];
};
const FIXED = (a) => [[window.__vehicle.pos.x, window.__vehicle.pos.z], ...a.pts];

try {
  const page = await b.newPage({ viewport: { width: 1280, height: 720 } });
  page.on('pageerror', (e) => console.log('pageerror:', e.message));
  page.on('requestfailed', (r) => { if (!/favicon/.test(r.url())) console.log('request failed:', r.url(), r.failure()?.errorText); });
  page.on('console', (m) => { if (m.type() === 'error' && !/404|favicon/.test(m.text())) console.log('console:', m.text()); });
  const frames = (n) => page.evaluate((n) => new Promise((ok) => { const s = () => (n-- > 0 ? requestAnimationFrame(s) : ok()); s(); }), n).catch(() => {});
  const shot = async (name) => { await page.screenshot({ path: path.join(out, `${name}.png`) }); console.log(`     shot ${name}.png`); };
  // run a function where the car is: the wilderness iframe while the player is out there, else the page
  const W = (fn, arg) => page.evaluate(([src, arg]) => {
    const f = document.querySelector('iframe');
    const w = f && window.__estateGate?.inWild ? f.contentWindow : window;
    return new w.Function('arg', src).call(w, arg);
  }, [`return (${fn})(arg)`, arg]);
  const waitW = async (fn, arg, timeout = 90000) => {
    const t0 = Date.now();
    for (;;) {
      let v = null;
      try { v = await W(fn, arg); } catch { v = null; }
      if (v) return v;
      if (Date.now() - t0 > timeout) return null;
      await page.waitForTimeout(250);
    }
  };
  const carReady = (world) => waitW((w) => window.__loaded && window.__vehicle && window.__car?.driving && (!w || window.__wild?.world?.name === w) && !window.__car.pending, world);

  // drive along an in-page path on the autopilot; samples the car each frame
  const drive = async (label, pathFn, arg = {}, opts = {}) => {
    const { speed = SPEED, until = null, timeout = 400000, shots = [], ts = TS } = opts;
    await W((a) => {
      const c = window.__vehicle;
      const pts = new Function('return ' + a.fn)()(a.arg);
      c.timeScale = a.ts;
      c.autopilot(pts, { speed: a.speed, stop: a.stop });
      const d = window.__drive = { min: Infinity, max: -Infinity, maxV: 0, stuck: 0, t0: performance.now(), hits0: c.stats.hits, last: 0, lastT: performance.now(), samples: 0, offMax: 0, air: 0 };
      c.stats.maxHit = 0;
      const g = window.__wild?.world?.heightAt;
      const tick = () => {
        if (window.__drive !== d || c.auto?.done) return;
        const gh = g ? g(c.pos.x, c.pos.z) : Math.max(...c.ground.filter(Number.isFinite));
        const dy = c.pos.y - gh;
        if (Number.isFinite(dy)) { d.min = Math.min(d.min, dy); d.max = Math.max(d.max, dy); }
        d.maxV = Math.max(d.maxV, c.speed);
        d.offMax = Math.max(d.offMax, c.auto?.offset || 0);
        if (!c.contact) d.air++;
        const prog = c.auto?.s[c.auto.i] || 0;
        if (prog > d.last + 1) { d.last = prog; d.lastT = performance.now(); }
        d.stuck = Math.max(d.stuck, (performance.now() - d.lastT) / 1000);
        d.samples++;
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
      return true;
    }, { fn: pathFn.toString(), arg, speed, stop: opts.stop !== false, ts });
    const t0 = Date.now();
    let res = null, last = null;
    const startWorld = await W(() => window.__wild?.world?.name || 'house');
    const pending = [...shots];
    for (;;) {
      await page.waitForTimeout(400);
      try {
        res = await W(() => {
          const c = window.__vehicle, d = window.__drive;
          if (!d || !c?.auto) return null;
          return { done: !!c.auto.done, stuck: d.stuck, s: c.auto.s[c.auto.i], end: c.auto.s.at(-1), min: d.min, max: d.max, maxV: d.maxV, hits: c.stats.hits - d.hits0,
            maxHit: c.stats.maxHit, off: d.offMax, air: d.air, pos: c.pos.toArray().map((v) => +v.toFixed(1)), t: (performance.now() - d.t0) / 1000, samples: d.samples,
            world: window.__wild?.world?.name || 'house' };
        });
      } catch { res = null; }       // (mid-reload: the other world loading)
      // (a leg that ends in the other level: the stats are the last ones from the level it was driven in)
      if (res && (startWorld === 'house') === (res.world === 'house')) last = res; else if (res && !until) last = res;
      while (res && pending.length && res.s >= pending[0][0]) { const [, name] = pending.shift(); await shot(name); }
      if (until && (await until().catch(() => false))) break;
      if (!res && !until) { if (Date.now() - t0 > 20000) break; continue; }
      if (res?.done || (res && res.stuck > 12) || Date.now() - t0 > timeout) break;
    }
    res = last;
    if (res) {
      console.log(`     ${label}: ${res.s?.toFixed(0)} / ${res.end?.toFixed(0)} m in ${res.t.toFixed(1)} s (x${ts}), top ${(res.maxV * 3.6).toFixed(0)} km/h, body over ground ${res.min.toFixed(2)}..${res.max.toFixed(2)} m, ` +
        `hits ${res.hits} (hardest ${res.maxHit.toFixed(1)} m/s), airborne ${res.air} frames, off the line <= ${res.off.toFixed(1)} m, stuck <= ${res.stuck.toFixed(1)} s, at ${res.pos} (${res.world})`);
      legs.push({ label, ...res });
    }
    return res;
  };
  const legOk = (r, label, { hits = 0, reach = true } = {}) => check(r && (!reach || r.done) && r.min > -0.35 && r.stuck < 12 && r.hits <= hits,
    `${label}: ${r ? `${r.s?.toFixed(0)} m, body ${r.min.toFixed(2)}..${r.max.toFixed(2)} m over the ground, ${r.hits} hits, stuck <= ${r.stuck.toFixed(1)} s` : 'no data'}`);

  const house = async (qs = '') => {
    const t0 = Date.now();
    await page.goto(`${BASE}/viewer/index.html?level=mansion&grimble=0&invaders=0${qs}`);
    await page.waitForFunction(() => window.__loaded, null, { timeout: 240000 });
    console.log(`house loaded in ${Date.now() - t0} ms`);
    await page.mouse.click(640, 360);
    await page.waitForTimeout(400);
  };
  const placeHouse = (pos, look) => page.evaluate(([pos, look]) => {
    const p = window.__player, c = window.__three.camera;
    p.pos.set(pos[0], pos[1], pos[2]); p.vel.set(0, 0, 0); p.syncCamera(); c.lookAt(...look);
  }, [pos, look]);

  // ------------------------------------------------------------------ keys: the house, real key presses
  const keys = async () => {
    await placeHouse([18.6, 0, 15.4], [16.75, 1.0, 15.4]);
    await frames(10);
    check(await page.evaluate(() => window.__car?.prompt), 'at the driver\'s door: the "E Drive" prompt');
    await shot('01_garage_at_the_door');
    await page.keyboard.press('KeyE');
    await page.waitForTimeout(900);
    const seated = await page.evaluate(() => { const c = window.__vehicle; return { driving: c.driving, d: c.seatWorld().distanceTo(window.__three.camera.position) }; });
    check(seated.driving && seated.d < 0.05, `E: in the driver's seat (the camera ${seated.d.toFixed(3)} m from the seat)`);
    await shot('02_garage_drivers_seat');
    await page.evaluate(() => window.__signals.set('garage_door', true));   // (its switch's signal)
    await page.waitForTimeout(5200);
    const p0 = await page.evaluate(() => ({ p: window.__vehicle.pos.toArray(), yaw: window.__vehicle.yaw }));
    await page.keyboard.down('KeyW'); await page.keyboard.down('KeyA'); await page.waitForTimeout(800);
    const snd = await page.evaluate(() => { const N = window.__car.audio.nodes; return N && { state: N.ctx.state, sfx: N.ctx === window.__sfx?.ctx, whine: N.w1.frequency.value, road: N.rg.gain.value, v: window.__vehicle.speed }; });
    check(snd && snd.state === 'running' && snd.whine > 150, `sound: the EV synth on ${snd?.sfx ? "window.__sfx's" : 'its own'} context (${snd?.state}), whine ${snd?.whine?.toFixed(0)} Hz at ${snd?.v?.toFixed(1)} m/s`);
    await page.keyboard.up('KeyA'); await page.keyboard.up('KeyW');
    await page.keyboard.down('KeyS'); await page.waitForTimeout(900); await page.keyboard.up('KeyS');
    await page.waitForFunction(() => window.__vehicle.speed < 0.3, null, { timeout: 5000 }).catch(() => {});
    const p1 = await page.evaluate(() => ({ p: window.__vehicle.pos.toArray(), yaw: window.__vehicle.yaw, v: window.__vehicle.speed }));
    check(p1.p[2] - p0.p[2] > 0.5 && p1.yaw - p0.yaw > 0.02 && p1.v < 0.3,
      `W+A then S: ${(p1.p[2] - p0.p[2]).toFixed(2)} m forward, turned ${((p1.yaw - p0.yaw) * 57.3).toFixed(1)} deg left, stopped (${p1.v.toFixed(2)} m/s)`);
    await page.keyboard.down('KeyS'); await page.waitForTimeout(1400); await page.keyboard.up('KeyS');
    await page.waitForTimeout(900);
    const p2 = await page.evaluate(() => ({ p: window.__vehicle.pos.toArray(), v: window.__vehicle.speed, g: window.__vehicle.gear }));
    check(p2.p[2] < p1.p[2] - 0.3, `S from a standstill: reversed ${(p1.p[2] - p2.p[2]).toFixed(2)} m`);
    await page.keyboard.down('KeyA'); await page.waitForTimeout(500);
    await shot('02b_garage_seat_steering_left');
    await page.keyboard.press('KeyV'); await frames(20);
    check(await page.evaluate(() => window.__vehicle.camMode === 'chase'), 'V: the chase camera');
    await shot('03_garage_chase_cam');
    await page.keyboard.up('KeyA');
    await page.keyboard.press('KeyV'); await frames(5);
    await page.keyboard.press('KeyE'); await page.waitForTimeout(400);
    const outd = await page.evaluate(() => { const c = window.__vehicle, p = window.__player; return { driving: c.driving, d: Math.hypot(p.pos.x - c.pos.x, p.pos.z - c.pos.z), y: p.pos.y }; });
    check(!outd.driving && outd.d > 1.2 && outd.d < 3.5 && Math.abs(outd.y) < 0.1, `E: out, standing ${outd.d.toFixed(2)} m from the car's centre`);
    await page.waitForTimeout(800);
    // (the car is solid again where it's parked)
    const solid = await page.evaluate(() => { const c = window.__vehicle, P = window.__player; return P.overlapping(new P.pos.constructor(c.pos.x, 0.02, c.pos.z), 1.8).length > 0; });
    check(solid, 'parked: its colliders are back round it');
    const dbg = await page.evaluate(() => { const c = window.__vehicle, cam = window.__three.camera; const d = c.doorWorld();
      return { prompt: window.__car.prompt, speed: c.speed, door: d.toArray(), eye: cam.position.toArray(), reach: c.inReach(cam.position, cam.getWorldDirection(d.clone())) }; });
    console.log('     (at the door again:', JSON.stringify(dbg), ')');
    await page.keyboard.press('KeyE'); await page.waitForTimeout(700);
    check(await page.evaluate(() => window.__vehicle.driving), 'E again: back in');
  };

  if (stages.includes('keys')) { await house('&pos=18.6,1.65,15.4&look=16.75,1.0,15.4'); await keys(); }

  if (stages.includes('trip')) {
    // ---------------------------------------------------------------- the house -> the gate
    await house('&pos=18.6,1.65,15.4&look=16.75,1.0,15.4');
    await keys();
    const g0 = await drive('garage -> drive', FIXED, { pts: [[16.75, 22], [17.5, 26], [19.75, 31], [19.75, 50]] }, { speed: 9 });
    legOk(g0, 'out of the garage, across the motor court, down the drive');
    await shot('04_drive_gate_opening');
    // out through the gate: the handoff carries the car into the wilderness iframe
    const tg = Date.now();
    await drive('drive -> gate', FIXED, { pts: [[19.75, 75]] }, { speed: 8, stop: false, ts: 1,
      until: () => page.evaluate(() => window.__suspended === true && window.__estateGate?.inWild) });
    const inWild = await carReady('laurel_fork');
    check(!!inWild && await page.evaluate(() => window.__suspended === true), `through the gate: the house suspended, the car in the wilderness, driving (${Date.now() - tg} ms)`);
    await frames(10);
    await shot('05_wild_through_the_gate');
    // ---------------------------------------------------------------- down the county road to the seam
    const r1 = await drive('cove road (out)', LANE, { extra: [] }, {
      until: () => page.evaluate(() => /laurel_town/.test(document.querySelector('iframe')?.contentWindow.location.search || '')),
      shots: [[200, '06_road_meadow'], [880, '07_road_hairpin_1'], [1370, '08_road_hairpin_2'], [2360, '09_road_hairpin_4'], [2600, '10_road_river_leg'], [2860, '11_road_seam_cove_side']] });
    legOk(r1, 'the cove road, gate to the seam', { reach: false });
    check(r1 && r1.s > 2860, `reached the seam (${r1?.s?.toFixed(0)} m)`);
    // ---------------------------------------------------------------- the town
    const tt = Date.now();
    const inTown = await carReady('laurel_town');
    check(!!inTown, `across the seam: the iframe reloaded into the town, the car with it, driving (${Date.now() - tt} ms)`);
    await frames(20);
    await shot('12_town_arrival');
    const r2 = await drive('town road -> Main Street', LANE, { untilX: -40, west: true }, { shots: [[300, '13_town_gorge_road'], [700, '14_town_main_street_east']] });
    legOk(r2, 'into the town and down Main Street');
    await shot('15_town_main_street');
    // turned round on the spot (the test's shortcut: a U-turn on a 10 m street isn't the autopilot's)
    await W(() => { const c = window.__vehicle; c.yaw += Math.PI; c.vel.set(0, 0, 0); c.yawRate = 0; const r = [-Math.cos(c.yaw), Math.sin(c.yaw)]; c.pos.x += r[0] * 3.4; c.pos.z += r[1] * 3.4; c.settle(); c.applyTransform(); c._prevQ.copy(c._q); window.__three.camera.quaternion.copy(c._q); return true; });
    await frames(5);
    const r3 = await drive('Main Street -> the seam', LANE, { back: true, extra: [] }, {
      until: () => page.evaluate(() => /laurel_fork/.test(document.querySelector('iframe')?.contentWindow.location.search || '')),
      shots: [[400, '16_town_leaving']] });
    legOk(r3, 'back up the town road to the seam', { reach: false });
    const tc = Date.now();
    check(!!(await carReady('laurel_fork')), `across the seam again: back in the cove, driving (${Date.now() - tc} ms)`);
    await frames(10);
    await shot('17_cove_back_at_the_seam');
    // ---------------------------------------------------------------- up the hairpins, in through the gate
    const r4 = await drive('cove road (back)', LANE, { back: true, extra: [[19.75, -752], [19.75, -760]] }, {
      until: () => page.evaluate(() => window.__suspended === false && window.__car?.driving),
      shots: [[500, '18_road_back_hairpin_4'], [1500, '19_road_back_hairpin_2'], [2700, '20_road_back_meadow']] });
    legOk(r4, 'up the cove road to the gate', { reach: false });
    const back = await page.evaluate(() => ({ s: window.__suspended, d: window.__car?.driving, p: window.__vehicle?.pos.toArray() }));
    check(back.s === false && back.d, `in through the gate: the house again, the car with it, driving (at ${back.p?.map((v) => v.toFixed(1))})`);
    await frames(10);
    await shot('21_house_back_inside_the_gate');
    const r5 = await drive('drive -> garage', FIXED, { pts: [[19.75, 50], [19.75, 31], [17.5, 26], [16.75, 21], [16.75, 15.5]] }, { speed: 8 });
    legOk(r5, 'up the drive into the garage');
    await shot('22_garage_parked');
    await page.keyboard.press('KeyE'); await page.waitForTimeout(500);
    check(await page.evaluate(() => !window.__vehicle.driving), 'E: out in the garage');
  }

  if (stages.includes('gate')) {
    // the handoff alone: in the car on the drive, out through the gate and back in
    await house('&pos=18.6,1.65,15.4&look=16.75,1.0,15.4');
    await page.evaluate(() => { const c = window.__car; c.enter(); const v = window.__vehicle; v.trans = null; v.pos.set(19.75, -0.08, 45); v.yaw = 0; v.settle(); v.applyTransform(); v._prevQ.copy(v._q); window.__three.camera.quaternion.copy(v._q); });
    await page.waitForTimeout(500);
    await drive('drive -> gate', FIXED, { pts: [[19.75, 80]] }, { speed: 8, stop: false, ts: 1,
      until: () => page.evaluate(() => window.__suspended === true && window.__estateGate?.inWild) });
    check(!!(await carReady('laurel_fork')), 'through the gate: the car in the wilderness');
    const st = await W(() => { const c = window.__vehicle, cam = window.__three.camera, d = cam.getWorldDirection(cam.position.clone());
      return { yaw: c.yaw, vel: c.vel.toArray(), pos: c.pos.toArray(), cam: d.toArray(), auto: !!c.auto }; });
    console.log('     wild car:', JSON.stringify(st));
    await frames(10);
    await shot('gate_wild_side');
    // and straight back in (fast: the gate's line must catch a car at speed); turned round on the spot first
    await W(() => { const c = window.__vehicle; c.pos.z += 12; c.yaw = Math.PI; c.vel.set(0, 0, 0); c.yawRate = 0; c.settle(); c.applyTransform(); c._prevQ.copy(c._q); window.__three.camera.quaternion.copy(c._q); return true; });
    await drive('wild -> gate', FIXED, { pts: [[19.75, -735], [19.75, -760], [19.75, -790]] }, { speed: 16, stop: false,
      until: () => page.evaluate(() => window.__suspended === false && window.__car?.driving) });
    const hb = await page.evaluate(() => ({ s: window.__suspended, d: window.__car?.driving, p: window.__vehicle.pos.toArray().map((v) => +v.toFixed(2)), yaw: +window.__vehicle.yaw.toFixed(2), v: window.__vehicle.vel.toArray().map((v) => +v.toFixed(2)), hold: window.__vehicle.hold, auto: !!window.__vehicle.auto, asleep: window.__car.asleep }));
    check(hb.s === false && hb.d && hb.p[2] > 55, `back in through the gate, driving, the car at the gate (${JSON.stringify(hb)})`);
    await page.evaluate(() => window.__signals.set('garage_door', true));
    const r5 = await drive('gate -> garage', FIXED, { pts: [[19.75, 50], [19.75, 31], [17.5, 26], [16.75, 21], [16.75, 15.5]] }, { speed: 8 });
    legOk(r5, 'up the drive into the garage');
  }

  if (stages.includes('cost')) {
    // what the car costs where it's drawn: the same views with the car shown and hidden (draw calls,
    // triangles, frame time over 120 uncapped-ish frames) and the vehicle's own CPU per frame
    const measure = (label) => W(async (label) => {
      const r = window.__three.renderer, c = window.__vehicle;
      const run = async (show) => {
        c.root.visible = show;
        await new Promise((ok) => { let n = 20; const f = () => (n-- > 0 ? requestAnimationFrame(f) : ok()); f(); });
        let calls = 0, tris = 0, n = 0; const t = []; let last = performance.now();
        await new Promise((ok) => { const f = () => { const now = performance.now(); t.push(now - last); last = now; calls += r.info.render.calls; tris += r.info.render.triangles; if (++n < 120) requestAnimationFrame(f); else ok(); }; requestAnimationFrame(f); });
        t.sort((a, b) => a - b);
        return { calls: Math.round(calls / n), tris: Math.round(tris / n), p50: +t[60].toFixed(2), p95: +t[114].toFixed(2) };
      };
      const on = await run(true), off = await run(false);
      c.root.visible = true;
      // the vehicle's CPU: 200 updates at 60 Hz with the keys held
      const t0 = performance.now();
      for (let i = 0; i < 200; i++) c.update(1 / 60, { forward: true });
      const cpu = (performance.now() - t0) / 200;
      return { label, on, off, cpuMs: +cpu.toFixed(3) };
    }, label);
    const say = (m) => console.log(`     ${m.label}: car shown ${m.on.calls} calls / ${(m.on.tris / 1000).toFixed(0)}k tris / p50 ${m.on.p50} ms, hidden ${m.off.calls} / ${(m.off.tris / 1000).toFixed(0)}k / ${m.off.p50} ms -> +${m.on.calls - m.off.calls} calls, +${((m.on.tris - m.off.tris) / 1000).toFixed(1)}k tris; vehicle update ${m.cpuMs} ms/frame`);
    await page.goto(`${BASE}/viewer/wild.html?world=laurel_fork&car=s:1300&hud=0`);
    await carReady('laurel_fork');
    await page.waitForTimeout(3000);
    const m1 = await measure('wild (the road, seat view)'); say(m1);
    await W(() => { window.__vehicle.toggleCamera(); return true; });
    const m2 = await measure('wild (the road, chase view)'); say(m2);
    legs.push({ cost: [m1, m2] });
  }

  if (stages.includes('road')) {
    // the cove road on its own (stand-alone wild.html): out to the seam, and back from the far end
    const t0 = Date.now();
    await page.goto(`${BASE}/viewer/wild.html?world=laurel_fork&car=drive&hud=0`);
    check(!!(await carReady('laurel_fork')), `wild.html?car=drive: in the car at the gate (${Date.now() - t0} ms)`);
    const r1 = await drive('cove road (out)', LANE, { untilX: -752, west: true }, { shots: [[880, 'road_hairpin_1'], [2600, 'road_river']] });
    legOk(r1, 'the cove road, gate to the seam');
    await page.goto(`${BASE}/viewer/wild.html?world=laurel_fork&car=back:2870&hud=0`);
    check(!!(await carReady('laurel_fork')), 'wild.html?car=back:2870: at the seam, facing the gate');
    const r2 = await drive('cove road (back)', LANE, { back: true, extra: [[19.75, -752], [19.75, -760]] }, { shots: [[1500, 'road_back_hairpin']],
      until: () => page.evaluate(() => /index\.html/.test(location.pathname)) });
    legOk(r2, 'the cove road, seam to the gate', { reach: false });
    // stand-alone, the gate leads to the house by navigating (sessionStorage): the car comes too
    await page.waitForFunction(() => window.__loaded && window.__car, null, { timeout: 240000 }).catch(() => {});
    await page.waitForTimeout(1000);
    const h = await page.evaluate(() => ({ url: location.search, d: window.__car?.driving, p: window.__vehicle?.pos.toArray().map((v) => +v.toFixed(1)) }));
    check(/from=wild/.test(h.url) && h.d, `stand-alone: in through the gate to index.html?from=wild, driving the car (at ${h.p})`);
    await frames(10);
    await shot('road_back_in_the_house');
  }
  fs.writeFileSync(path.join(out, 'legs.json'), JSON.stringify(legs, null, 1));
} finally {
  await b.close();
  stop();
  release();
}
console.log(fails ? `${fails} FAILED` : 'all passed');
process.exit(fails ? 1 : 0);
