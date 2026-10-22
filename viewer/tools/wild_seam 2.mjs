// The cove <-> town seam (design/town/brief.md "Getting there"): walks the real player west along
// the road out of laurel_fork until the exit reloads the page into laurel_town, then back east
// until it reloads into the cove again. Checks that each reload:
//  - lands in the other world at the same estate point (within 3.5 m: the spawn nudge);
//  - has the same ground height there as the point just left (within 0.6 m);
//  - stands the player on the ground;
//  - raises no page errors.
// Usage: node viewer/tools/wild_seam.mjs   (takes a browser slot; GT_BASE for a worktree's server)
// Output: build/wilderness/laurel_town/seam.json
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { ensureServer, BASE } from './server.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const locks = path.join(root, 'build/locks');
let slot = null;
while (!slot) {
  for (let i = 0; i < 3 && !slot; i++) { try { fs.mkdirSync(path.join(locks, `browser_${i}`)); slot = path.join(locks, `browser_${i}`); } catch {} }
  if (!slot) await new Promise((r) => setTimeout(r, 2000));
}
const release = () => { try { fs.rmdirSync(slot); } catch {} };
process.on('exit', release);
const stop = await ensureServer();
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const errors = [];
const out = { legs: [] };
const state = (page) => page.evaluate(() => {
  const w = window.__wild, p = window.__player.pos, [ox, oy] = w.world.meta.estate_offset;
  return { world: w.world.name, ex: p.x + ox, ey: -p.z + oy, ground: w.world.heightAt(p.x, p.z), feet: p.y };
});
const loaded = (page) => page.waitForFunction(() => window.__loaded, null, { timeout: 300000 });
// walk (W held) facing the estate heading (dx, dy) until the page reloads into another world
const walk = async (page, dx, dy, secs) => {
  const before = await state(page);
  let last = before;
  await page.evaluate(([dx, dy]) => {
    const cam = window.__three.camera, p = cam.position;
    cam.lookAt(p.x + dx * 10, p.y, p.z - dy * 10);
    dispatchEvent(new KeyboardEvent('keydown', { code: 'KeyW' }));
  }, [dx, dy]);
  const t = Date.now();
  while (Date.now() - t < secs * 1000) {
    try { last = await state(page); } catch { break; }           // (the page is navigating)
    if (!page.url().includes(`world=${before.world}`)) break;
    await page.waitForTimeout(50);
  }
  return { before, last };
};
try {
  const page = await (await b.newContext({ viewport: { width: 640, height: 360 } })).newPage();
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message));
  // the cove's road 12 m east of its exit, facing west
  await page.goto(`${BASE}/viewer/wild.html?world=laurel_fork&hud=0&q=0&grass=0&epos=-750,-703&elook=-800,-703`);
  await loaded(page);
  for (const [dx, dy] of [[-1, -0.03], [1, 0.03]]) {
    const leg = await walk(page, dx, dy, 60);
    await page.waitForURL((u) => !u.toString().includes(`world=${leg.before.world}`), { timeout: 30000 }).catch(() => {});
    await loaded(page);
    await page.waitForTimeout(800);
    out.legs.push({ from: leg.last, to: await state(page) });
  }
} finally {
  await b.close();
  stop?.();
}
let ok = errors.length === 0 && out.legs.length === 2;
for (const { from, to } of out.legs) {
  const d = Math.hypot(to.ex - from.ex, to.ey - from.ey), dz = Math.abs(to.ground - from.ground);
  const good = to.world !== from.world && d < 3.5 && dz < 0.6 && Math.abs(to.feet - to.ground) < 0.3;
  ok &&= good;
  console.log(`${from.world} (${from.ex.toFixed(1)}, ${from.ey.toFixed(1)}) ground ${from.ground.toFixed(2)} -> ${to.world} `
    + `(${to.ex.toFixed(1)}, ${to.ey.toFixed(1)}) ground ${to.ground.toFixed(2)} feet ${to.feet.toFixed(2)}: moved ${d.toFixed(2)} m, dz ${dz.toFixed(3)} ${good ? 'OK' : 'FAIL'}`);
}
console.log(errors.length ? errors.join('\n') : 'no page errors');
console.log(ok ? 'PASS' : 'FAIL');
fs.mkdirSync(path.join(root, 'build/wilderness/laurel_town'), { recursive: true });
fs.writeFileSync(path.join(root, 'build/wilderness/laurel_town/seam.json'), JSON.stringify({ ...out, errors, ok }, null, 1));
process.exit(ok ? 0 : 1);
