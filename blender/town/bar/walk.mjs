// Walks the real player (wild runtime, laurel_town) through THE BAR (town2_bar) along four
// routes and reports every leg that doesn't arrive: in from the lot up the porch steps; across
// the room to the deck, down the stair to the landing at the water; round the bar's return into
// the bartender's aisle; down the corridor into the back room. Waypoints in the asset frame.
//   GT_BASE=http://localhost:<port> node blender/town/bar/walk.mjs
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const BASE = process.env.GT_BASE || 'http://localhost:8765';
const ROUTES = {
  front_door: [[-8.45, -16.0], [-8.45, -11.3], [-8.45, -5.2]],
  room_to_river: [[-8.45, -5.2], [-6.5, -3.6], [4.5, -3.0], [9.4, -1.0], [9.6, 4.0], [9.6, 6.4], [9.6, 8.6], [14.2, 10.9], [14.2, 17.4], [14.0, 19.0]],
  behind_the_bar: [[2.0, 2.5], [4.75, 3.3], [4.75, 5.7], [3.0, 5.65], [-9.2, 5.5]],
  back_room: [[-9.6, -0.8], [-10.9, -0.8], [-13.4, -0.8], [-13.4, 1.2], [-14.55, 1.5], [-14.55, 3.9], [-12.5, 4.4]],
};
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
  for (const [name, pts] of Object.entries(ROUTES)) {
    const r = await page.evaluate(([pts]) => {
      const W = window.__wild.world, T = W.meta.town, oy = W.meta.estate_offset[1];
      const bd = T.buildings.find((q) => q.id === 'bar');
      const [ox, oyk] = bd.kit_offset || [0, 0], a = bd.yaw * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
      const at = (u, v) => { const x = bd.x + (u - ox) * c - (v - oyk) * s, y = bd.y + (u - ox) * s + (v - oyk) * c; return [x, -(y - oy)]; };
      const pl = window.__player, cam = window.__three.camera;
      const [sx, sz] = at(...pts[0]);
      pl.pos.set(sx, W.heightAt(sx, sz) + 0.6, sz); pl.vel.set(0, 0, 0);
      window.__wild.pause(true);
      const legs = [];
      for (let i = 1; i < pts.length; i++) {
        const [tx, tz] = at(...pts[i]);
        let k = 0, d = 1e9;
        for (; k < 60 * 14; k++) {
          cam.position.set(pl.pos.x, pl.pos.y + 1.6, pl.pos.z);
          cam.lookAt(tx, pl.pos.y + 1.6, tz);
          pl.update(1 / 60, { forward: true });
          d = Math.hypot(pl.pos.x - tx, pl.pos.z - tz);
          if (d < 0.45) break;
        }
        legs.push({ to: pts[i], ok: d < 0.45, s: +(k / 60).toFixed(1), miss_m: +d.toFixed(2), y: +(pl.pos.y - bd.z).toFixed(2) });
        if (d >= 0.45) break;
      }
      window.__wild.pause(false);
      return legs;
    }, [pts]);
    const pass = r.length === pts.length - 1 && r.every((l) => l.ok);
    ok &&= pass;
    console.log(name.padEnd(16), pass ? 'OK  ' : 'FAIL', r.map((l) => `${l.to.join(',')}:${l.ok ? `${l.s}s@${l.y}` : `stuck ${l.miss_m}m`}`).join('  '));
  }
} finally { await b.close(); }
console.log(ok ? 'PASS' : 'FAIL');
process.exit(ok ? 0 : 1);
