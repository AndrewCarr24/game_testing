// Review screenshots of one room in the real engine (baked lighting, screen effects on, no Grimble).
// Usage: node viewer/tools/review_room.mjs <room> [out-dir] ["px,py,pz,lx,ly,lz" ...]
// Without views: 4 corner views (eye height, looking across the room; an eye inside a collider
// is pulled toward the centre until clear), 4 wall views from the
// centre, a view down at the floor and one up at the ceiling. Views are room-local? No: world
// glTF coords (see room_info: rect = [x0, z0, x1, z1] in mansion.json). At most 3 browsers run
// at once machine-wide (a lock in build/locks/), so many reviewers can share the machine.
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import { room } from './level.mjs';

const [name, outDir = `build/review/${process.argv[2]}`, ...custom] = process.argv.slice(2);
const base = process.env.REVIEW_BASE || process.env.GT_BASE || 'http://localhost:8765';   // (another server: compare builds)
const r = room(name);
fs.mkdirSync(outDir, { recursive: true });

// machine-wide browser slots
const lockDir = 'build/locks';
fs.mkdirSync(lockDir, { recursive: true });
let slot = null;
for (;;) {
  for (let i = 0; i < 3 && slot === null; i++) {
    try { fs.mkdirSync(`${lockDir}/browser_${i}`); slot = i; } catch {}
  }
  if (slot !== null) break;
  await new Promise((ok) => setTimeout(ok, 3000));
}
const release = () => { try { fs.rmdirSync(`${lockDir}/browser_${slot}`); } catch {} };
process.on('exit', release);
process.on('SIGINT', () => { release(); process.exit(1); });

const y = r.floor + 1.65, m = 0.6;
const [x0, z0, x1, z1] = [r.x0 + m, r.z0 + m, r.x1 - m, r.z1 - m];
const cx = r.cx, cz = r.cz, cy = r.floor + 1.2;
const views = custom.length ? custom.map((v, i) => [`custom_${i + 1}`, v.split(',').map(Number)]) : [
  ['corner_nw', [x0, y, z0, cx, cy, cz]], ['corner_ne', [x1, y, z0, cx, cy, cz]],
  ['corner_se', [x1, y, z1, cx, cy, cz]], ['corner_sw', [x0, y, z1, cx, cy, cz]],
  ['wall_n', [cx, y, cz, cx, cy, r.z0]], ['wall_s', [cx, y, cz, cx, cy, r.z1]],
  ['wall_e', [cx, y, cz, r.x1, cy, cz]], ['wall_w', [cx, y, cz, r.x0, cy, cz]],
  ['floor', [cx, y, cz + 0.01, cx + 0.01, r.floor, cz + 2.5]], ['ceiling', [cx, y, cz + 0.01, cx + 0.01, r.floor + r.height, cz + 2]],
];
try {
  const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
  const p = await b.newPage({ viewport: { width: 1280, height: 800 } });
  p.on('pageerror', (e) => console.log('pageerror:', e.message));
  await p.goto(`${base}/viewer/index.html?level=mansion&grimble=0&pos=${cx},${y},${cz}&look=${cx},${cy},${r.z0}`);
  await p.waitForFunction(() => window.__loaded, null, { timeout: 120000 });
  await p.evaluate(() => { document.querySelectorAll('#hud, #stats, #hint, .hud, #toast').forEach((e) => (e.style.display = 'none')); });
  for (const v of views) {
    const [label, [px, py, pz, lx, ly, lz]] = v;
    if (label.startsWith('corner_')) {
      // a corner eye inside a cabinet, plant or wall shows its inside: step it toward the room
      // centre until a box round the head (±0.3 m, -0.4..+0.2 m) is clear of every collider
      // (the level's shell and every prop's part boxes, as the player collides with them)
      const moved = await p.evaluate(([px, py, pz, cx, cz]) => {
        const cols = window.__colliders, Box = cols[0].constructor, V = window.__camera.position.constructor;
        const head = new Box(), from = new V(px, py, pz), to = new V(cx, py, cz), at = new V();
        const len = from.distanceTo(to);
        for (let s = 0; s < len; s += 0.25) {
          at.lerpVectors(from, to, s / len);
          head.set(new V(at.x - 0.3, at.y - 0.4, at.z - 0.3), new V(at.x + 0.3, at.y + 0.2, at.z + 0.3));
          if (!cols.some((c) => c.intersectsBox(head))) return [at.x, at.y, at.z, s];
        }
        return [px, py, pz, 0];
      }, [px, py, pz, cx, cz]);
      if (moved[3] > 0) console.log(`${label}: pulled ${moved[3].toFixed(2)} m toward the centre (clear of colliders)`);
      [v[1][0], v[1][1], v[1][2]] = moved;
    }
    const [, [qx, qy, qz]] = v;
    await p.evaluate(([px, py, pz, lx, ly, lz]) => {
      const c = window.__camera;
      window.__bench = { frameStart() {}, drive() { c.position.set(px, py, pz); c.lookAt(lx, ly, lz); }, renderStart() {}, frameEnd() {} };
    }, [qx, qy, qz, lx, ly, lz]);
    await p.waitForTimeout(700);
    const f = path.join(outDir, `${label}.png`);
    await p.screenshot({ path: f });
    console.log(f);
  }
  await b.close();
} finally { release(); }
