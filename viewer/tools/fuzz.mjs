// Random play in every room, simulated in the page (faster than real time): run, strafe, jump,
// crouch and turn from 6 random starts per room (doors open on half of them), then try to walk
// out in 8 directions. Flags a player left inside a box (> 1 cm), under the floor, outside every
// room (out of the house) or stuck. Must report 0 problems; it found the corners where
// depenetration pushed the player out through the facade (dining, garage, wine room).
// Usage: SEEDS=7,12 node fuzz.mjs   (seed 12 is the wine-room corner)
import { chromium } from 'playwright-core';
const seeds = (process.env.SEEDS || '7,12').split(',').map(Number);
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 800, height: 500 } });
p.on('pageerror', (e) => console.log('pageerror:', e.message));
await p.goto((process.env.GT_BASE || 'http://localhost:8765') + '/viewer/index.html?level=mansion&grimble=0');
await p.waitForFunction(() => window.__loaded, null, { timeout: 90000 });
let problems = 0;
for (const seed of seeds) {
  const res = await p.evaluate(async (SEED) => {
    const THREE = await import('three');
    const pl = window.__player, cam = window.__camera, L = window.__level, it = window.__interact;
    let s = SEED; const rnd = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
    const fits = (x, z, y) => pl.overlapping(new THREE.Vector3(x, y + 0.02, z)).length === 0;
    const roomAt = (x, y, z) => Object.entries(L.rooms).find(([, r]) => y >= r.floor - 0.3 && y <= r.floor + r.height &&
      x >= r.rect[0] - 0.3 && x <= r.rect[2] + 0.3 && z >= r.rect[1] - 0.3 && z <= r.rect[3] + 0.3)?.[0];
    const step = (input, secs, yaw) => {
      for (let t = 0; t < secs; t += 1 / 60) {
        cam.position.set(pl.pos.x, pl.pos.y + pl.eye, pl.pos.z);
        cam.rotation.set(0, yaw, 0, 'YXZ');
        pl.update(1 / 60, input);
      }
    };
    // out through an open exterior door (going outside) is fine: on the grounds, inside the hedge
    // (getting pushed out through a wall is walls.mjs's to catch: it runs into every wall)
    const B = L.grounds?.bounds;
    const outByDoor = (p) => !!B && p.y > -0.2 && p.x > B[0] && p.x < B[2] && p.z > B[1] && p.z < B[3];
    const depth = (c) => { const b = pl.boxAt(pl.pos); return Math.min(b.max.x - c.min.x, c.max.x - b.min.x, b.max.z - c.min.z, c.max.z - b.min.z); };
    const bad = [];
    let runs = 0;
    for (const [room, r] of Object.entries(L.rooms)) {
      for (let k = 0; k < 6; k++) {
        let x, z, tries = 0;
        do { x = r.rect[0] + 0.5 + rnd() * (r.rect[2] - r.rect[0] - 1); z = r.rect[1] + 0.5 + rnd() * (r.rect[3] - r.rect[1] - 1); } while (!fits(x, z, r.floor) && ++tries < 50);
        if (tries >= 50) continue;
        for (const i of it.items) if (i.def.type === 'rotate' && !i.locked) { i.t = i.target = k % 2 === 0 ? 1 : 0; it.pose(i); }
        pl.pos.set(x, r.floor + 0.02, z); pl.vel.set(0, 0, 0); pl.crouching = false; pl.down = null;
        runs++;
        let yaw = rnd() * 6.283;
        for (let seg = 0; seg < 40; seg++) {
          yaw += (rnd() - 0.5) * 2.5;
          step({ forward: rnd() < 0.8, left: rnd() < 0.2, right: rnd() < 0.2, run: rnd() < 0.5, jump: rnd() < 0.3, crouch: rnd() < 0.15 }, 0.2 + rnd() * 0.6, yaw);
          if (seg % 3 === 0) step({}, 0.05, yaw);
          const inside = pl.overlapping(pl.pos).filter((c) => c.max.y - pl.pos.y > 0.32 && depth(c) > 0.01);
          if (inside.length || pl.pos.y < -0.3 || (!roomAt(pl.pos.x, pl.pos.y, pl.pos.z) && !outByDoor(pl.pos))) {
            bad.push({ room, why: inside.length ? 'inside a box' : pl.pos.y < -0.3 ? 'under the floor' : 'out of the house', pos: pl.pos.toArray().map((v) => +v.toFixed(2)) });
            break;
          }
        }
        step({}, 0.6, yaw);
        const start = pl.pos.clone();
        let best = 0;
        for (let d = 0; d < 8 && best < 0.3; d++) {
          pl.pos.copy(start); pl.vel.set(0, 0, 0);
          step({ forward: true, jump: d % 2 === 1 }, 0.7, (d / 8) * 6.283);
          best = Math.max(best, pl.pos.distanceTo(start));
        }
        if (best < 0.3) bad.push({ room, why: 'stuck', pos: start.toArray().map((v) => +v.toFixed(2)) });
      }
    }
    for (const i of it.items) if (i.def.type === 'rotate') { i.t = i.target = 0; it.pose(i); }
    return { runs, bad };
  }, seed);
  console.log(`seed ${seed}: ${res.runs} runs, ${res.bad.length} problems`);
  for (const x of res.bad) console.log('  ', JSON.stringify(x));
  problems += res.bad.length;
}
await b.close();
console.log(problems ? `${problems} problems` : 'all passed');
process.exit(problems ? 1 : 0);
