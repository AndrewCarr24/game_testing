// Stress the character controller against every wall: walk/sprint/jump into walls,
// corners, doors and picture frames from many angles; flag any impossible position
// (on top of a wall or ceiling, below the floor), indoors and on the grounds. Usage: node walls.mjs
import { chromium } from 'playwright-core';
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 800, height: 500 } });
p.on('pageerror', (e) => console.log('pageerror:', e.message));
await p.goto((process.env.GT_BASE || 'http://localhost:8765') + '/viewer/index.html?level=mansion');
await p.waitForFunction(() => window.__loaded, null, { timeout: 180000 });
// ROOMS=a,b,c: only these rooms (and no grounds), e.g. ROOMS=secret_stair,armory,tunnel_e,pump_room,tunnel_n
const only = process.env.ROOMS ? process.env.ROOMS.split(',') : null;
const result = await p.evaluate(async (only) => {
  const THREE = await import('three');
  const pl = window.__player, cam = window.__camera, it = window.__interact;
  // open every door so the doorways get tested too
  for (const i of it.items) if (i.def.type === 'rotate') { i.locked = false; i.t = i.target = 1; it.pose(i); }
  // start at the centre and two inner corners of every room in the level
  // furnished rooms: walk a spiral out from each target until the player fits there
  const fits = (x, z, y) => { pl.pos.set(x, y + 0.02, z); return pl.overlapping(pl.pos).length === 0; };
  const clearNear = (x, z, y) => {
    for (let rad = 0; rad < 4; rad += 0.25)
      for (let a = 0; a < 16; a++) {
        const px = x + rad * Math.cos(a * Math.PI / 8), pz = z + rad * Math.sin(a * Math.PI / 8);
        if (fits(px, pz, y)) return [px, pz, y];
      }
    return null;
  };
  const starts = {};
  // (below ground) a shaft stands inside another room's rect (the secret stair in the den): a start
  // for that room must not be in the shaft
  const shafts = Object.entries(window.__level.rooms).filter(([, q]) => q.kind === 'shaft');
  const inShaft = (name, p) => p && shafts.some(([n, q]) => n !== name && p[0] > q.rect[0] - 0.4 && p[0] < q.rect[2] + 0.4 && p[1] > q.rect[1] - 0.4 && p[1] < q.rect[3] + 0.4);
  for (const [name, r] of Object.entries(window.__level.rooms)) {
    if (only && !only.includes(name)) continue;
    const [x0, z0, x1, z1] = r.rect, cx = (x0 + x1) / 2, cz = (z0 + z1) / 2;
    starts[name] = [[cx, cz], [x0 + 1.2, z0 + 1.2], [x1 - 1.2, z1 - 1.2], [x1 - 1.2, z0 + 1.2]]
      .map(([x, z]) => clearNear(x, z, r.floor)).filter((p) => p && !inShaft(name, p)).slice(0, 3);
  }
  // going outside: the grounds too (each zone's centre and two corners, the terrace's four sides,
  // on the lawn); outside the house the floor is the lawn, not 0
  const G = window.__level.grounds;
  if (G && !only) {
    for (const [name, [x0, z0, x1, z1]] of Object.entries(G.zones)) {
      if (name === 'planting') continue;
      const [bx0, bz0, bx1, bz1] = G.bounds;          // (a zone may reach past the hedge: the drive)
      starts['zone ' + name] = [[(x0 + x1) / 2, (z0 + z1) / 2], [x0 + 2, z0 + 2], [x1 - 2, z1 - 2]]
        .map(([x, z]) => [Math.min(bx1 - 1, Math.max(bx0 + 1, x)), Math.min(bz1 - 1, Math.max(bz0 + 1, z))])
        .map(([x, z]) => clearNear(x, z, G.lawn)).filter(Boolean);
    }
    starts.terrace = [[0, 22.5], [0, -22.5], [-28.5, 0], [28.5, 0]].map(([x, z]) => clearNear(x, z, G.terrace)).filter(Boolean);
  }
  const [hx0, hz0, hx1, hz1] = G ? G.house : [-1e9, -1e9, 1e9, 1e9];
  // (below ground: a run that starts under the house keeps its own floor, -4.2)
  const floorAt = (x, z, sy = 0) => (sy < -1 ? sy : x > hx0 && x < hx1 && z > hz0 && z < hz1 ? 0 : G.lawn);
  const bad = [];
  let runs = 0;
  for (const [room, pts] of Object.entries(starts)) for (const [sx, sz, sy] of pts) {
    for (let a = 0; a < 8; a++) for (const mode of ['walk', 'run', 'jump', 'strafe']) {
      runs++;
      pl.pos.set(sx, sy + 0.05, sz); pl.vel.set(0, 0, 0); pl.crouching = false; pl.grounded = false;
      const ang = (a / 8) * Math.PI * 2 + 0.13;
      cam.position.set(sx, sy + 1.65, sz);
      cam.lookAt(sx + Math.cos(ang), sy + 1.65, sz + Math.sin(ang));
      let worst = null, takeoff = sy, prevY = sy + 0.05;
      for (let f = 0; f < 240; f++) {           // 4 s at 60 fps, pressing into whatever is ahead
        pl.update(1 / 60, { forward: mode !== 'strafe', right: mode === 'strafe', run: mode !== 'walk',
                            jump: mode === 'jump' && f % 50 === 0, left: false, back: false, crouch: false });
        const y = pl.pos.y;
        if (pl.grounded || pl.vel.y === 0) takeoff = y;
        // impossible: a sudden upward jump (teleport; two 0.3 m step-ups in one frame is the most climbing can do), rising more
        // than a jump above where we took off, on the roof, under the ground floor, or
        // left inside a box
        const why = y - prevY > 0.65 ? 'teleported up' : y > takeoff + 1.2 ? 'above jump' : y > 8.4 ? 'on the roof'
                  : y < floorAt(pl.pos.x, pl.pos.z, sy) - 0.05 ? 'under the floor' : pl.overlapping(pl.pos).length ? 'inside a box' : null;
        prevY = y;
        if (why) { worst = { why, f, y: +y.toFixed(2), takeoff: +takeoff.toFixed(2), x: +pl.pos.x.toFixed(2), z: +pl.pos.z.toFixed(2) }; break; }
      }
      if (worst) bad.push({ room, start: [+sx.toFixed(1), +sz.toFixed(1)], angle: a, mode, ...worst });
    }
  }
  return { runs, bad };
}, only);
console.log(`${result.runs} runs, ${result.bad.length} ended somewhere impossible`);
for (const r of result.bad.slice(0, 15)) console.log(JSON.stringify(r));
await b.close();
process.exit(result.bad.length ? 1 : 0);
