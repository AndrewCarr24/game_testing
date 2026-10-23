// Going outside: from the entry, open the front door, walk out onto the motor court, all the
// way round the house on the terrace (past the great room's glass, the dining and kitchen doors,
// the mudroom door, the garage), out over the lawn to the pool and the gate, and back in through
// the front door. The walking is the real character controller (window.__player) driven frame
// by frame toward each waypoint; a leg fails if the player stops making progress (blocked),
// ends up under the ground, or leaves the hedge. Screenshots from the player's eye on the way.
// Usage: node outside.mjs [out-dir]   (GT_BASE=http://localhost:<port> for a worktree)
import { chromium } from 'playwright-core';
import fs from 'fs';
import { level, url } from './level.mjs';
const out = process.argv[2] || 'build/outside';
fs.mkdirSync(out, { recursive: true });
const G = level.grounds;
if (!G) { console.log('FAIL  the level has no "grounds" (rebuild it)'); process.exit(1); }
const front = G.doors.filter((d) => d.room === 'entry');
// (no front door in the level yet: start outside, for testing the grounds alone)
const noDoor = !front.length;
// glTF: x east, z south (Blender y north = -z). Front doors at z = 20 (Blender y -20).
const fx = noDoor ? 0 : front.reduce((a, d) => a + d.position[0], 0) / front.length, fz = noDoor ? 20 : front[0].position[2];
const T = G.terrace;
// waypoints [x, z] (glTF): out the door, round the house on the terrace ring (x +-28.5, z +-22.5),
// a detour over the lawn (the pool steps, the gate's drive), back to the door and in
const route = [
  ['out the front door', [fx, fz + 2.2]],
  ['motor court', [fx, fz + 3.5]],
  ['south-west corner', [-28.5, 22.5]],
  ['west terrace (great room glass)', [-28.5, 0]],
  ['north-west corner', [-28.5, -22.5]],
  ['dining doors', [-18, -22.5]],
  ['kitchen door', [-1, -22.5]],
  ['up the pool steps', [8, -30.0]],
  ['back down to the terrace', [8, -22.5]],
  ['north-east corner', [28.5, -22.5]],
  ['mudroom door', [28.5, -8.9]],
  ['south-east corner', [28.5, 22.5]],
  ['down the drive', [19.75, 45]],
  ['at the gate', [19.75, 59.5]],
  ['back up the drive', [19.75, 30]],
  ['front of the house', [fx, fz + 3.5]],
  ['outside the open door', [fx, fz + 2.2]],
  ['back in through the door', [fx, fz - 3.0]],
];
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 1280, height: 760 } });
p.on('pageerror', (e) => console.log('pageerror:', e.message));
let fails = 0;
const check = (label, ok, detail = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}  ${detail}`); if (!ok) fails++; };
const eye = noDoor ? [fx, 1.6, fz + 3.5] : [fx + 0.4, 1.65, fz - 1.3];
// OUT_QS='&bake=0' (etc.) is appended to the page URL
await p.goto(url(eye, [fx + 0.6, 1.2, fz + 5]) + '&grimble=0' + (process.env.OUT_QS || ''));
await p.waitForFunction(() => window.__loaded, null, { timeout: 90000 });
await p.mouse.click(640, 380); await p.waitForTimeout(600);
const info = await p.evaluate(() => ({ boxes: window.__colliders.filter((c) => c.fixed).length, hint: document.getElementById('hint').textContent }));
check('the grounds colliders loaded', info.boxes > 100, `${info.boxes} fixed boxes`);
await p.screenshot({ path: `${out}/01_front_door_inside.png` });
if (noDoor) { check('an exterior door in the entry', false, 'none in level.grounds.doors'); route.splice(0, 1); route.pop(); }
else {
  // open the leaf in view with E (the real key path: prompt, interact.use)
  check('the front door offers to open', /Open door/.test(info.hint), `hint="${info.hint}"`);
  await p.keyboard.press('KeyE'); await p.waitForTimeout(1400);
  const opened = await p.evaluate(() => window.__interact.items.filter((i) => i.def.type === 'rotate' && i.t === 1)
    .map((i) => i.root.position.toArray()));
  const leaf = opened.find((q) => Math.abs(q[2] - fz) < 0.3 && Math.abs(q[0] - fx) < 2);
  check('E opens a front door', !!leaf, JSON.stringify(opened));
  // through the open leaf (the other one of the pair stays shut)
  if (leaf) for (const w of route) if (/front door|open door|through the door/.test(w[0])) w[1][0] = leaf[0];
  await p.screenshot({ path: `${out}/02_front_door_open.png` });
}
// walk the route with the real controller, 60 Hz, frame by frame
const shotsAt = { 'motor court': '03_motor_court', 'west terrace (great room glass)': '04_west_terrace',
  'dining doors': '05_north_terrace', 'up the pool steps': '06_pool_deck', 'mudroom door': '07_east_terrace',
  'at the gate': '08_gate', 'front of the house': '09_front' };
for (const [label, [tx, tz]] of route) {
  const r = await p.evaluate(([tx, tz, bounds, lawn]) => {
    const pl = window.__player, cam = window.__camera, it = window.__interact;
    let best = Infinity, stall = 0, f = 0, why = null;
    for (; f < 60 * 40; f++) {
      const d = Math.hypot(tx - pl.pos.x, tz - pl.pos.z);
      if (d < 0.35) break;
      if (d < best - 0.05) { best = d; stall = 0; } else if (++stall > 180) { why = 'blocked'; break; }
      cam.position.set(pl.pos.x, pl.pos.y + 1.65, pl.pos.z);
      cam.lookAt(tx, pl.pos.y + 1.65, tz);
      pl.update(1 / 60, { forward: true, run: d > 3, jump: stall > 60 && stall % 40 === 0 });
      it.update(1 / 60, cam.position);
      if (pl.pos.y < lawn - 0.1) { why = 'under the ground'; break; }
      if (pl.pos.x < bounds[0] || pl.pos.x > bounds[2] || pl.pos.z < bounds[1] || pl.pos.z > bounds[3]) { why = 'left the hedge'; break; }
    }
    return { why: why ?? (f >= 2400 ? 'timeout' : null), pos: pl.pos.toArray().map((v) => +v.toFixed(2)), s: +(f / 60).toFixed(1) };
  }, [tx, tz, G.bounds, G.lawn]);
  check(`walk: ${label}`, !r.why, `${r.why ?? 'reached'} at ${JSON.stringify(r.pos)} after ${r.s}s`);
  if (r.why) await p.screenshot({ path: `${out}/stuck_${label.replace(/\W+/g, '_')}.png` });
  if (shotsAt[label]) {
    await p.waitForTimeout(400);
    const calls = await p.evaluate(() => window.__three.renderer.info.render.calls);
    await p.screenshot({ path: `${out}/${shotsAt[label]}.png` });
    console.log(`      shot ${shotsAt[label]}.png (${calls} draw calls)`);
  }
}
const end = await p.evaluate(() => window.__player.pos.toArray());
if (!noDoor) check('back inside the entry', end[2] < fz - 1 && Math.abs(end[1]) < 0.05, JSON.stringify(end.map((v) => +v.toFixed(2))));
// every other exterior door: from outside, E opens it, walk in, walk back out
const seen = new Set(['entry']);
for (const d of G.doors) {
  if (seen.has(d.room) || d.asset === 'ix_garage_door') continue;   // (the garage door opens from its switch inside)
  seen.add(d.room);
  const r = level.rooms[d.room], [x, , z] = d.position;
  const n = Math.abs(z - r.rect[1]) < 0.3 ? [0, -1] : Math.abs(z - r.rect[3]) < 0.3 ? [0, 1] : Math.abs(x - r.rect[0]) < 0.3 ? [-1, 0] : [1, 0];
  const res = await p.evaluate(async ([x, z, n, rect]) => {
    const pl = window.__player, cam = window.__camera, it = window.__interact;
    pl.pos.set(x + n[0] * 1.3, 0, z + n[1] * 1.3); pl.vel.set(0, 0, 0);
    for (let i = 0; i < 30; i++) pl.update(1 / 60, {});
    cam.position.set(pl.pos.x, pl.pos.y + 1.65, pl.pos.z); cam.lookAt(x, 1.2, z);
    await new Promise((ok) => setTimeout(ok, 300));
    const hint = document.getElementById('hint').textContent;
    return { hint };
  }, [x, z, n, r.rect]);
  const ok1 = /Open door/.test(res.hint);
  await p.keyboard.press('KeyE'); await p.waitForTimeout(1400);
  const walk = await p.evaluate(([x, z, n, rect]) => {
    const pl = window.__player, cam = window.__camera, it = window.__interact;
    const go = (tx, tz) => {
      for (let f = 0; f < 600; f++) {
        if (Math.hypot(tx - pl.pos.x, tz - pl.pos.z) < 0.3) return true;
        cam.position.set(pl.pos.x, pl.pos.y + 1.65, pl.pos.z); cam.lookAt(tx, pl.pos.y + 1.65, tz);
        pl.update(1 / 60, { forward: true }); it.update(1 / 60, cam.position);
      }
      return false;
    };
    const inn = go(x - n[0] * 2.0, z - n[1] * 2.0);
    const inside = pl.pos.x > rect[0] && pl.pos.x < rect[2] && pl.pos.z > rect[1] && pl.pos.z < rect[3];
    const out = go(x + n[0] * 2.5, z + n[1] * 2.5);
    return { inn, inside, out, pos: pl.pos.toArray().map((v) => +v.toFixed(2)) };
  }, [x, z, n, r.rect]);
  check(`${d.room} door: E opens it from outside, walk in and back out`, ok1 && walk.inside && walk.out,   // (inside counts, not the 2 m point: the bathhouse's fire bath has its hot pool 1.2 m in)
    `hint="${res.hint}" in=${walk.inn} inside=${walk.inside} out=${walk.out} at ${JSON.stringify(walk.pos)}`);
  await p.screenshot({ path: `${out}/door_${d.room}.png` });
}
// a few views from the player's eye on the grounds (teleported; the lawn is under them)
const views = [
  ['10_west_garden', [-38, -4.4], [-60, 0]], ['11_pool', [0, -30], [20, -40]], ['12_fire_garden', [-18, -30], [-18, -40]],
  ['13_house_from_lawn', [-10, 52], [-4, 18]], ['14_tennis', [36, -2], [52, -2]],
];
for (const [name, [x, z], [lx, lz]] of views) {
  await p.evaluate(([x, z, lx, lz]) => {
    const pl = window.__player; pl.pos.set(x, 2, z); pl.vel.set(0, 0, 0);
    for (let i = 0; i < 90; i++) pl.update(1 / 60, {});
    window.__camera.position.set(pl.pos.x, pl.pos.y + 1.65, pl.pos.z); window.__camera.lookAt(lx, pl.pos.y + 1.5, lz);
  }, [x, z, lx, lz]);
  await p.waitForTimeout(500);
  const s = await p.evaluate(() => ({ y: window.__player.pos.y, calls: window.__three.renderer.info.render.calls }));
  check(`stand on the grounds at ${name}`, s.y > G.lawn - 0.05 && s.y < G.lawn + 1.0, `feet y=${s.y.toFixed(2)}, ${s.calls} draw calls`);
  await p.screenshot({ path: `${out}/${name}.png` });
}
await b.close();
console.log(fails ? `${fails} failed` : 'all passed');
process.exit(fails ? 1 : 0);
