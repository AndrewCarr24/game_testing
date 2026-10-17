// Stress the character controller against every wall: walk/sprint/jump into walls,
// corners, doors and picture frames from many angles; flag any impossible position
// (on top of a wall or ceiling, below the floor). Usage: node walls.mjs
import { chromium } from 'playwright-core';
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 800, height: 500 } });
p.on('pageerror', (e) => console.log('pageerror:', e.message));
await p.goto('http://localhost:8765/viewer/index.html?level=mansion');
await p.waitForFunction(() => window.__loaded, null, { timeout: 60000 });
const result = await p.evaluate(async () => {
  const THREE = await import('three');
  const pl = window.__player, cam = window.__camera, it = window.__interact;
  // open every door so the doorways get tested too
  for (const i of it.items) if (i.def.type === 'rotate') { i.locked = false; i.t = i.target = 1; it.pose(i); }
  // start points (glTF x, z) inside each room, with the room's floor height 0
  const starts = { office: [[0, 0], [2.4, 2.2], [-2.5, -2.0], [2.4, -1.5]],
                   hall: [[2.4, 5.0], [2.4, 8.5], [2.4, 12.0]],
                   bedroom: [[1.0, 14.5], [-1.0, 16.0], [3.0, 16.5]] };
  const bad = [];
  let runs = 0;
  for (const [room, pts] of Object.entries(starts)) for (const [sx, sz] of pts) {
    for (let a = 0; a < 16; a++) for (const mode of ['walk', 'run', 'jump', 'strafe']) {
      runs++;
      pl.pos.set(sx, 0, sz); pl.vel.set(0, 0, 0); pl.crouching = false;
      const ang = (a / 16) * Math.PI * 2 + 0.13;
      cam.position.set(sx, 1.65, sz);
      cam.lookAt(sx + Math.cos(ang), 1.65, sz + Math.sin(ang));
      let worst = null, ground = 0;
      for (let f = 0; f < 240; f++) {           // 4 s at 60 fps, pressing into whatever is ahead
        pl.update(1 / 60, { forward: mode !== 'strafe', right: mode === 'strafe', run: mode !== 'walk',
                            jump: mode === 'jump' && f % 50 === 0, left: false, back: false, crouch: false });
        const y = pl.pos.y;
        if (pl.grounded) ground = y;
        // impossible: higher than one jump above what we last stood on, on top of the
        // building (nothing walkable is above 1.2 m), under the floor, or inside a box
        const why = y > ground + 1.15 ? 'above jump' : y > 2.0 ? 'on the roof' : y < -0.05 ? 'under the floor'
                  : pl.overlapping(pl.pos).length ? 'inside a box' : null;
        if (why) { worst = { why, f, y: +y.toFixed(2), ground: +ground.toFixed(2), x: +pl.pos.x.toFixed(2), z: +pl.pos.z.toFixed(2) }; break; }
      }
      if (worst) bad.push({ room, start: [sx, sz], angle: a, mode, ...worst });
    }
  }
  return { runs, bad };
});
console.log(`${result.runs} runs, ${result.bad.length} ended somewhere impossible`);
for (const r of result.bad.slice(0, 15)) console.log(JSON.stringify(r));
await b.close();
process.exit(result.bad.length ? 1 : 0);
