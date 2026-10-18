// Screenshots of every major room in one page load (teleporting the player).
// Usage: node house_tour.mjs [out-dir] [room ...]
import { chromium } from 'playwright-core';
import { room, url } from './level.mjs';
const [out = 'build', ...only] = process.argv.slice(2);
const VIEWS = {   // stand near a corner, look across the room: [corner fx, fz] in 0..1 of the rect
  entry: [0.85, 0.85], great_room: [0.8, 0.9], den: [0.85, 0.15], dining: [0.85, 0.2], kitchen: [0.15, 0.8],
  scullery: [0.5, 0.85], wine_room: [0.15, 0.8], mudroom: [0.2, 0.8], garage: [0.5, 0.1], courtyard: [0.5, 0.92],
  powder: [0.5, 0.85], cloak: [0.5, 0.85], gallery_s: [0.05, 0.5], library: [0.9, 0.2], primary_bedroom: [0.85, 0.2],
  primary_bath: [0.15, 0.2], office: [0.15, 0.8], gym: [0.15, 0.8], guest_room: [0.15, 0.8], ugallery_n: [0.05, 0.5],
};
const names = only.length ? only : Object.keys(VIEWS);
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 1200, height: 720 } });
p.on('pageerror', (e) => console.log('pageerror:', e.message));
const first = room('entry');
await p.goto(url([first.cx, 1.65, first.cz], [first.cx, 1.5, first.z0]));
await p.waitForFunction(() => window.__loaded, null, { timeout: 90000 });
for (const n of names) {
  const r = room(n), [fx, fz] = VIEWS[n];
  const x = r.x0 + (r.x1 - r.x0) * fx, z = r.z0 + (r.z1 - r.z0) * fz;
  await p.evaluate(([x, y, z, lx, ly, lz]) => {
    const pl = window.__player;
    pl.pos.set(x, y, z); pl.vel.set(0, 0, 0); pl.syncCamera();
    window.__camera.lookAt(lx, ly, lz);
  }, [x, r.y + 0.02, z, r.cx, r.y + 1.3, r.cz]);
  await p.waitForTimeout(700);
  await p.screenshot({ path: `${out}/tour_${n}.png` });
  console.log(`tour_${n}.png`);
}
await b.close();
