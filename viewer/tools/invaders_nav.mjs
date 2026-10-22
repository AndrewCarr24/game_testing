// The invaders' nav (viewer/invaders_nav.js) over the live level: build time, the stair's links,
// the door portals, and routes that must exist (outside -> in through each entry, both floors,
// side rooms through their doors, a locked door that must not be passed).
// Usage: GT_BASE=http://localhost:8827 node viewer/tools/invaders_nav.mjs
import { withPage } from './invaders_lib.mjs';

const r = await withPage('&grimble=0&fx=0&invaders=0', (p) => p.evaluate(async () => {
  const { buildWorld } = await import('/viewer/invaders.js');
  const t0 = performance.now();
  const world = buildWorld({ level: window.__level, colliders: window.__colliders, interact: window.__interact, signals: window.__signals });
  const tb = performance.now() - t0;
  const nav = world.nav;
  const P = (x, y, z) => nav.cellFor(x, y, z);
  const tests = {
    front_out_to_entry: [[0, 0, 30], [0, 0, 15], true],
    motor_to_guest_room: [[20, 0, 40], [20, 4.6, -5], true],
    motor_to_library: [[20, 0, 40], [-17, 4.6, 15], true],
    entry_to_den: [[0, 0, 15], [-20, 0, 15], true],
    entry_to_mudroom: [[0, 0, 15], [20, 0, -5], true],
    entry_to_powder: [[0, 0, 15], [-11, 0, 15], true],
    entry_to_wine: [[0, 0, 15], [20, 0, -15], true],
    terrace_to_kitchen: [[-1, 0, -23], [0, 0, -15], true],
    terrace_to_dining: [[-18, 0, -23], [-18, 0, -15], true],
    east_lawn_to_mudroom: [[29, 0, -9], [20, 0, -9], true],
    garage_out_in: [[19.75, 0, 24], [19.75, 0, 10], true],
    west_lawn_to_great: [[-35, 0, 0], [-20, 0, 0], true],
    upper_gallery_ring: [[-11.75, 4.6, 8.75], [11.75, 4.6, -8.75], true],
    bath: [[0, 0, 15], [-5, 4.6, -15], false],
    gym: [[0, 0, 15], [20, 4.6, -15], false],
    bedroom: [[0, 0, 15], [-18, 4.6, -15], false],
    bedroom_breach: [[0, 0, 15], [-18, 4.6, -15], true, true],
    gym_breach: [[0, 0, 15], [20, 4.6, -15], true, true],
    office_locked: [[0, 0, 15], [7, 4.6, -15], false],
  };
  const out = { build: +tb.toFixed(1), links: nav.linkCount, layers: nav.layers.map((L) => [L.name, L.w, L.h, L.open.reduce((a, b) => a + b, 0)]),
    doors: nav.doors.map((d) => [d.name, d.layer, d.cells, d.centre.toArray().map((v) => +v.toFixed(2)), d.locked()]) };
  const res = {};
  for (const [k, [a, b, want, breach]] of Object.entries(tests)) {
    const s = P(...a), g = P(...b);
    const t1 = performance.now();
    const path = nav.path(s, g, { breach: !!breach });
    if (k === 'garage_out_in') out.garagePath = path?.map((w) => [+w.x.toFixed(1), +w.z.toFixed(1), w.layer[0], w.door?.name ?? '']);
    res[k] = { ok: !!path === want, s, g, ms: +(performance.now() - t1).toFixed(2), len: +nav.lastLen.toFixed(1), n: path?.length,
      layers: path ? [...new Set(path.map((w) => w.layer))].join('>') : null, doors: path ? path.filter((w) => w.door).map((w) => w.door.name).join(',') : null };
  }
  out.routes = res;
  nav.flood(P(0, 0, 15));
  out.reach = nav.reachCount;
  out.stats = nav.stats;
  return out;
}));
console.log(JSON.stringify({ ...r, routes: undefined }, null, 0));
for (const [k, v] of Object.entries(r.routes)) console.log(v.ok ? 'PASS' : 'FAIL', k.padEnd(22), JSON.stringify(v));
const fails = Object.values(r.routes).filter((v) => !v.ok).length;
console.log(fails ? `${fails} FAIL` : 'all routes PASS');
process.exitCode = fails ? 1 : 0;
