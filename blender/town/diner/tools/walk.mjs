// Walks the real wild player (60 Hz, walking) through the diner along routes of waypoints in the
// asset frame (x east, y north from the lot's centre; the car's floor is up three steps) and
// reports, per leg, whether it got within 0.6 m of the waypoint, where it stopped, and its feet
// over the floor it stands on. Routes: the front door -> the aisle -> behind the counter -> the
// kitchen -> the back door -> the yard; the restroom hall -> both restrooms; round the lot.
// Usage: GT_BASE=http://localhost:8836 node blender/town/diner/tools/walk.mjs [route,...]
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
const BASE = process.env.GT_BASE || 'http://localhost:8765';
const ROUTES = {
  front: [[0, -9], [0, -2.6], [0, -0.3], [0, 1.4], [0, 2.45], [6.4, 2.45], [7.2, 4.3], [7.8, 5.0], [7.6, 6.4], [6.2, 7.6], [4.5, 8.35], [2.6, 9.4], [1.7, 10.8], [1.7, 12.2], [1.7, 13.6]],
  restrooms: [[0, -9], [0, -0.3], [0, 2.45], [-6.6, 2.45], [-7.85, 4.5], [-7.85, 5.9], [-7.25, 6.6], [-7.25, 7.6], [-7.6, 9.0], [-7.25, 7.5], [-6.2, 6.5], [-4.7, 6.6], [-4.7, 7.6], [-4.4, 9.0]],
  staff: [[0, -9], [0, -0.3], [0, 2.45], [-6.0, 2.45], [-7.85, 4.5], [-7.85, 6.1], [-4.0, 6.1], [-3.4, 6.05], [-2.4, 6.1], [0.0, 6.6], [3.0, 6.6], [6.0, 6.7], [7.8, 5.0], [7.6, 4.3], [6.4, 2.6]],
  lot: [[-13, -12], [13, -12], [13, 12], [3, 13.8], [0.3, 11.95], [-9.8, 11.95], [-12, 5], [-13, -12]],
};
const pick = (process.argv[2] || Object.keys(ROUTES).join(',')).split(',');

const locks = path.join(root, 'build/locks');
let slot = null;
while (!slot) {
  for (let i = 0; i < 3 && !slot; i++) { try { fs.mkdirSync(path.join(locks, `browser_${i}`)); slot = path.join(locks, `browser_${i}`); } catch {} }
  if (!slot) await new Promise((r) => setTimeout(r, 2000));
}
process.on('exit', () => { try { fs.rmdirSync(slot); } catch {} });
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
let ok = true;
try {
  const page = await (await b.newContext({ viewport: { width: 640, height: 360 } })).newPage();
  page.on('pageerror', (e) => { console.log('pageerror', e.message); ok = false; });
  await page.goto(`${BASE}/viewer/wild.html?world=laurel_town&hud=0&q=0&grass=0&exits=0`);
  await page.waitForFunction(() => window.__loaded, null, { timeout: 300000 });
  for (const name of pick) {
    const res = await page.evaluate(([pts]) => {
      const W = window.__wild.world, T = W.meta.town, oy = W.meta.estate_offset[1];
      const bd = T.buildings.find((q) => q.id === 'diner');
      const [ox, oyk] = bd.kit_offset || [0, 0];
      const three = (u, v) => [bd.x + (u - ox), -((bd.y + (v - oyk)) - oy)];
      const back = (x, z) => [x - bd.x + ox, (-z + oy) - bd.y + oyk];
      const pl = window.__player, cam = window.__three.camera;
      const [sx, sz] = three(...pts[0]);
      pl.pos.set(sx, W.heightAt(sx, sz) + 0.3, sz); pl.vel.set(0, 0, 0);
      window.__wild.pause(true);
      const legs = [];
      for (let i = 1; i < pts.length; i++) {
        const [tx, tz] = three(...pts[i]);
        let k = 0, best = 1e9;
        for (; k < 60 * 12; k++) {
          cam.position.set(pl.pos.x, pl.pos.y + 1.65, pl.pos.z);
          cam.lookAt(tx, pl.pos.y + 1.65, tz);
          pl.update(1 / 60, { forward: true });
          const d = Math.hypot(pl.pos.x - tx, pl.pos.z - tz);
          best = Math.min(best, d);
          if (d < 0.35) break;
        }
        const [u, v] = back(pl.pos.x, pl.pos.z);
        legs.push({ to: pts[i], reached: best < 0.6, best: +best.toFixed(2), at: [+u.toFixed(2), +v.toFixed(2)], z: +(pl.pos.y - bd.z).toFixed(2), s: +(k / 60).toFixed(1) });
      }
      window.__wild.pause(false);
      return legs;
    }, [ROUTES[name]]);
    const fails = res.filter((l) => !l.reached);
    ok &&= !fails.length;
    console.log(`${name}: ${res.length - fails.length}/${res.length} legs`);
    for (const l of res) console.log(`   -> ${JSON.stringify(l.to)} ${l.reached ? 'ok' : 'STUCK'} at ${JSON.stringify(l.at)} feet ${l.z} m (${l.s} s)`);
  }
} finally { await b.close(); }
console.log(ok ? 'PASS' : 'FAIL');
process.exit(ok ? 0 : 1);
