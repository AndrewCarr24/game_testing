// The bathhouse (the pool house, design/grounds/pool_house.md), walked with the real character
// controller (window.__player, 60 Hz, frame by frame toward each waypoint): from the secret
// passage's landing (z -4.2) up the stair past the pool's glass end, the wheel at its head (E: the
// plunge above drains, the slab in its wall sinks), up through the empty plunge into the cold room,
// into the bath hall, over the stepping stones, out of the glass door to the lap pool's deck; back
// in, out of the south door and on to the drive and the gate. Then the hidden way: cold room ->
// steam room -> fire bath -> its east door -> the garden court. A leg fails if the player stops
// making progress, falls below the floor it should be on, or the stair's ramp pops. Screenshots
// from the player's eye in build/bathhouse/<label>/. Usage: node bathhouse.mjs [label]
// (GT_BASE=http://localhost:<port>; QS='&bake=0' appends to the URL)
import { chromium } from 'playwright-core';
import fs from 'fs';
import { level, url } from './level.mjs';

const label = process.argv[2] || 'walk';
const out = `build/bathhouse/${label}`;
fs.mkdirSync(out, { recursive: true });
let slot = null;
for (let t = 0; slot === null && t < 600; t++) {
  for (let i = 0; i < 3 && slot === null; i++) { try { fs.mkdirSync(`build/locks/browser_${i}`); slot = i; } catch {} }
  if (slot === null) await new Promise((ok) => setTimeout(ok, 1000));
}
const release = () => { try { fs.rmdirSync(`build/locks/browser_${slot}`); } catch {} };
process.on('exit', release);
let fails = 0;
const check = (what, ok, detail = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${what}  ${detail}`); if (!ok) fails++; };

// Blender (x, y, z) -> glTF [x, z(up), -y]
const B = (x, y, z = 0) => [x, z, -y];
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
try {
  const p = await b.newPage({ viewport: { width: 1280, height: 760 } });
  p.on('pageerror', (e) => console.log('pageerror:', e.message));
  p.on('console', (m) => { if (m.type() === 'error') console.log('console:', m.text().slice(0, 200)); });
  const start = B(40.0, 33.0, -4.2 + 1.65), look = B(40.0, 40.0, -2.0);
  await p.goto(url(start, look) + '&grimble=0&invaders=0' + (process.env.QS || ''));
  await p.waitForFunction(() => window.__loaded, null, { timeout: 180000 });
  await p.mouse.click(640, 380); await p.waitForTimeout(800);
  const rooms = Object.keys(level.rooms).filter((r) => r.startsWith('ph_'));
  check('the bathhouse rooms are in the level', rooms.length >= 6, rooms.join(','));
  check('the secret stair has its ramp', (level.ramps || []).some((r) => r.along === 'z'), JSON.stringify(level.ramps?.at(-1)));

  // one leg: walk (run optional) to [x, z] glTF; returns where it ended and the largest
  // per-frame height change (the ramp must glide: treads are 0.18 m)
  const walk = async (name, [tx, , tz], opts = {}) => {
    const r = await p.evaluate(([tx, tz, o]) => {
      const pl = window.__player, cam = window.__camera, it = window.__interact;
      let best = Infinity, stall = 0, f = 0, why = null, maxDy = 0, lastY = pl.pos.y;
      for (; f < 60 * 30; f++) {
        const d = Math.hypot(tx - pl.pos.x, tz - pl.pos.z);
        if (d < (o.near ?? 0.3)) break;
        if (d < best - 0.03) { best = d; stall = 0; } else if (++stall > 150) { why = 'blocked'; break; }
        cam.position.set(pl.pos.x, pl.pos.y + 1.65, pl.pos.z);
        cam.lookAt(tx, pl.pos.y + 1.65, tz);
        pl.update(1 / 60, { forward: true, run: !!o.run, crouch: !!o.crouch });
        it.update(1 / 60, cam.position);
        maxDy = Math.max(maxDy, Math.abs(pl.pos.y - lastY)); lastY = pl.pos.y;
        if (o.minY !== undefined && pl.pos.y < o.minY) { why = `fell to y ${pl.pos.y.toFixed(2)}`; break; }
      }
      return { why: why ?? (f >= 1800 ? 'timeout' : null), pos: pl.pos.toArray().map((v) => +v.toFixed(2)), s: +(f / 60).toFixed(1), maxDy: +maxDy.toFixed(3), here: window.__culler?.here?.name ?? null };
    }, [tx, tz, opts]);
    check(`walk: ${name}`, !r.why, `${r.why ?? 'reached'} at ${JSON.stringify(r.pos)} in ${r.s}s (max dy/frame ${r.maxDy}, room ${r.here})`);
    return r;
  };
  const shot = async (name, eye, at) => {
    await p.evaluate(([e, a]) => {
      const pl = window.__player, cam = window.__camera;
      if (e) { pl.pos.set(e[0], e[1] - 1.65, e[2]); pl.vel.set(0, 0, 0); }
      cam.position.set(pl.pos.x, pl.pos.y + 1.65, pl.pos.z);
      cam.lookAt(...a);
    }, [eye, at]);
    await p.waitForTimeout(700);
    await p.screenshot({ path: `${out}/${name}.png` });
    console.log(`      shot ${name}.png`);
  };
  const face = async (at) => p.evaluate((a) => { const pl = window.__player, cam = window.__camera; cam.position.set(pl.pos.x, pl.pos.y + 1.65, pl.pos.z); cam.lookAt(...a); }, at);
  const hint = () => p.evaluate(() => document.getElementById('hint').textContent);
  const openDoor = async (name, [x, , z]) => {
    const r = await p.evaluate(([x, z]) => {
      const it = window.__interact, v = new (window.__camera.position.constructor)();
      const ds = it.items.filter((i) => i.def.type === 'rotate').map((i) => ({ i, d: i.node.getWorldPosition(v).distanceTo(v.set(x, i.node.getWorldPosition(v).y, z)) }));
      ds.sort((a, b) => a.d - b.d);
      if (!ds.length || ds[0].d > 1.6) return { ok: false, d: ds[0]?.d };
      ds[0].i.target = 1;
      for (let f = 0; f < 90; f++) it.update(1 / 60, window.__camera.position);
      return { ok: ds[0].i.t === 1, d: +ds[0].d.toFixed(2), name: ds[0].i.node.name };
    }, [x, z]);
    check(`open: ${name}`, r.ok, JSON.stringify(r));
  };

  // ---- 1. up the secret stair
  await shot('01_landing_up_the_stair', null, B(40.0, 40.0, -1.0));
  await walk('to the foot of the stair', B(40.0, 34.4));
  await shot('02_stair_foot', null, B(39.0, 38.5, -1.2));
  const up = await walk('up the stair to its head', B(40.0, 39.75), { minY: -4.3 });
  check('the stair glides (no pops)', up.maxDy < 0.08, `max ${up.maxDy} m in a frame`);
  check('at the head of the stair (z -1.2)', Math.abs(up.pos[1] + 1.2) < 0.06, `y ${up.pos[1]}`);
  await shot('03_stair_window', B(40.0, 38.0, -1.9 + 1.65), B(38.4, 37.0, -1.0));
  // ---- 2. the wheel
  await shot('04_head_slab', B(40.3, 39.7, -1.2 + 1.65), B(40.0, 40.5, -0.4));
  await p.evaluate(() => { const pl = window.__player; pl.pos.set(40.6, -1.2, -40.0); pl.vel.set(0, 0, 0); });
  await face(B(41.35, 40.0, -0.05));
  await p.waitForTimeout(400);
  const h1 = await hint();
  check('the wheel offers to open the valve', /valve/i.test(h1), `hint="${h1}"`);
  await p.keyboard.press('KeyE');
  await p.waitForTimeout(400);
  await shot('05_valve_turned', null, B(40.0, 40.6, -0.2));
  const drained = await p.evaluate(async () => {
    const it = window.__interact;
    const t0 = performance.now();
    while (performance.now() - t0 < 9000) {
      it.update(1 / 30, window.__camera.position);
      await new Promise((ok) => setTimeout(ok, 33));
    }
    const rs = it.reactors.filter((r) => r.signal === 'ph_plunge').map((r) => [r.node.name, +r.t.toFixed(2)]);
    return { sig: window.__signals.get('ph_plunge'), rs };
  });
  check('the plunge drains and the slab sinks', drained.sig === true && drained.rs.length >= 3 && drained.rs.every(([, t]) => t === 1), JSON.stringify(drained));
  await shot('06_slab_gone', B(40.0, 39.6, -1.2 + 1.65), B(40.0, 42.5, -0.2));
  // ---- 3. up through the empty plunge into the cold room
  await walk('through the slab\'s opening into the plunge', B(40.0, 41.0), { minY: -1.3 });
  await shot('07_in_the_plunge', null, B(40.0, 44.0, 0.8));
  const cold = await walk('up the plunge\'s steps into the cold room', B(40.0, 43.4), { minY: -1.3 });
  check('on the cold room floor', Math.abs(cold.pos[1]) < 0.05, `y ${cold.pos[1]}`);
  await shot('08_cold_room', B(43.8, 43.5, 1.65), B(39.5, 41.5, 0.0));
  // ---- 4. the hall, the stones, the glass door, the lap pool
  await walk('into the bath hall', B(37.4, 43.75));
  await shot('09_hall_from_the_cold_room', null, B(28.0, 33.0, 0.8));
  await walk('along the north walkway', B(28.0, 43.75));
  await walk('to the stepping stones', B(28.0, 41.2));
  await shot('10_stones', null, B(28.0, 33.0, 0.2));
  await walk('over the stepping stones', B(28.0, 34.4), { minY: -0.1 });
  await walk('onto the south walkway', B(28.2, 33.25));
  await shot('11_glass_door', null, B(20.0, 33.25, 1.2));
  await openDoor('the hall\'s glass door', B(27.0, 33.25));
  await walk('out onto the lawn', B(25.4, 33.25));
  await walk('to the lap pool\'s deck', B(21.9, 33.0));
  await shot('12_from_the_deck', null, B(32.0, 38.0, 2.0));
  await shot('13_lawn_golden', B(21.0, 27.5, 0.45 + 1.65), B(34.0, 40.0, 2.5));
  // ---- 5. back in, out of the south door, on to the gate
  await walk('back to the door', B(25.6, 33.25));
  await walk('back in', B(28.6, 33.25));
  await walk('to the south door', B(30.15, 31.9));
  await openDoor('the hall\'s south door', B(30.15, 31.0));
  await walk('out of the south door', B(30.15, 29.6));
  await walk('to the house\'s terrace', B(30.0, 23.0));
  await walk('the east terrace', B(28.5, -22.5), { run: true });
  await walk('down the drive', B(19.75, -45.0), { run: true });
  await walk('to the gate', B(19.75, -58.5), { run: true });
  // ---- 6. the hidden way: cold room -> steam -> fire bath -> east door -> court
  await p.evaluate(() => { const pl = window.__player; pl.pos.set(42.2, 0, -42.6); pl.vel.set(0, 0, 0); });
  await openDoor('the steam room\'s north door', B(43.2, 40.5));
  await walk('into the steam', B(43.2, 39.4));
  await shot('14_steam', null, B(43.2, 35.0, 1.2));
  await walk('through the steam', B(43.2, 35.4));
  await openDoor('the steam room\'s south door', B(43.2, 34.5));
  await walk('into the fire bath', B(43.2, 33.95));
  await shot('15_fire_bath', B(44.4, 34.0, 1.65), B(39.0, 32.5, 0.4));
  await walk('round the hot pool', B(44.35, 33.95));
  await walk('to its east door', B(44.35, 32.9));
  await openDoor('the fire bath\'s east door', B(45.0, 32.9));
  await walk('out to the garden court', B(46.8, 32.9));
  await shot('16_court', null, B(52.0, 34.0, 1.2));
  // ---- 7. views
  await shot('17_rest_room', B(36.0, 45.2, 1.65), B(36.0, 49.0, 1.2));
  await shot('18_hall_from_south', B(36.8, 32.0, 1.65), B(29.0, 41.0, 1.6));
  await shot('19_outside_sw', B(18.0, 24.0, 1.65), B(36.0, 40.0, 3.0));
  await shot('20_outside_north', B(36.0, 56.0, 1.65), B(36.0, 44.0, 1.5));
  const perf = await p.evaluate(() => ({ calls: window.__three?.renderer?.info?.render?.calls, tris: window.__three?.renderer?.info?.render?.triangles }));
  console.log('      last frame', JSON.stringify(perf));
} finally {
  await b.close();
  release();
}
console.log(fails ? `${fails} FAILED` : 'ALL PASS');
process.exit(fails ? 1 : 0);
