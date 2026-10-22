// Walks the real player through the front doors of the town's walk-ins (laurel_town; world.json
// town.buildings with the kit's colliders) and reports who got inside: each starts 6 m out in front
// of its door, faces it and walks for 5 s. PASS = it ends more than 2 m inside the front wall.
// Usage: node viewer/tools/wild_walkin.mjs [ids,...]   (default: bar, gas, fastfood, sheriff, depot, church)
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { ensureServer, BASE } from './server.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const ids = (process.argv[2] || 'bar,gas,fastfood,sheriff,depot,church').split(',');
// the kit's front doors in the asset frame (u, v) (design/town/kit_status.md "entrances")
const DOORS = { town_bar: [5.2, -9.1, 5.0, -15.1],   // (the bar: left of the porch post at u 5.8 in front of its door)
  town_gas_station: [0, -6.1, 3.5, -9.5], town_fastfood: [-4.5, -7.1], town_sheriff: [-5.0, -9.5],
  town_depot: [-9.0, -6.1], town_church: [0, -16.8],
  site_gas_station: [-6.6, 3.2, -6.6, -4.0] };   // [gas] the rebuilt station (town2_gas): its sliding doors, from the drive aisle
const locks = path.join(root, 'build/locks');
let slot = null;
while (!slot) {
  for (let i = 0; i < 3 && !slot; i++) { try { fs.mkdirSync(path.join(locks, `browser_${i}`)); slot = path.join(locks, `browser_${i}`); } catch {} }
  if (!slot) await new Promise((r) => setTimeout(r, 2000));
}
process.on('exit', () => { try { fs.rmdirSync(slot); } catch {} });
const stop = await ensureServer();
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
let ok = true;
try {
  const page = await (await b.newContext({ viewport: { width: 640, height: 360 } })).newPage();
  page.on('pageerror', (e) => { console.log('pageerror', e.message); ok = false; });
  await page.goto(`${BASE}/viewer/wild.html?world=laurel_town&hud=0&q=0&grass=0&exits=0`);
  await page.waitForFunction(() => window.__loaded, null, { timeout: 300000 });
  for (const id of ids) {
    const r = await page.evaluate(([id, DOORS]) => {
      const W = window.__wild.world, T = W.meta.town, oy = W.meta.estate_offset[1];
      const bd = T.buildings.find((q) => q.id === id), door = DOORS[bd.kind];
      if (!door) return { id, skipped: true };
      const [ox, oyk] = bd.kit_offset || [0, 0], a = bd.yaw * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
      const at = (u, v) => [bd.x + (u - ox) * c - (v - oyk) * s, bd.y + (u - ox) * s + (v - oyk) * c];   // asset -> town frame
      const [sx, sy] = door.length > 2 ? at(door[2], door[3]) : at(door[0], door[1] - 6), [tx, ty] = at(door[0], door[1] + 4);
      const pl = window.__player, cam = window.__three.camera;
      pl.pos.set(sx, W.heightAt(sx, -(sy - oy)), -(sy - oy)); pl.vel.set(0, 0, 0);
      cam.position.set(sx, pl.pos.y + 1.65, -(sy - oy)); cam.lookAt(tx, pl.pos.y + 1.65, -(ty - oy));
      window.__wild.pause(true);
      const inp = { forward: true };
      for (let k = 0; k < 300; k++) { cam.lookAt(tx, cam.position.y, -(ty - oy)); pl.update(1 / 60, inp); }
      const ex = pl.pos.x, ey = -pl.pos.z + oy;
      // depth past the front wall (v from the door, in the asset frame)
      const du = ex - bd.x, dv = ey - bd.y, v = -du * s + dv * c + oyk;
      window.__wild.pause(false);
      return { id, inside_m: +(v - door[1]).toFixed(2), feet: +(pl.pos.y - W.heightAt(pl.pos.x, pl.pos.z)).toFixed(2) };
    }, [id, DOORS]);
    const pass = r.skipped || r.inside_m > 2;
    ok &&= pass;
    console.log(id, JSON.stringify(r), pass ? 'OK' : 'FAIL');
  }
} finally { await b.close(); stop?.(); }
console.log(ok ? 'PASS' : 'FAIL');
process.exit(ok ? 0 : 1);
