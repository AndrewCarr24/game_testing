// Walks a generated level's routes (world.json "routes": A down the creek, B along the ridge,
// C through the laurel hell; gate -> the Gap) with the real player (viewer/wild/player_hf.js
// on viewer/player.js: colliders, thickets, slope limit), stepped at a fixed 60 Hz in the page
// (simulated time, so a 7-minute route takes seconds). The walker runs (Shift) toward a point
// 4 m ahead on the route; when it makes no progress it crouches (tunnels, the propped log),
// then jumps, then sidesteps; only if all fail is the spot counted as STUCK and skipped.
// Also checks the feet never go under the ground (falling through) and records time, length,
// wading, the slope limit's blocks and where the walker had to crouch.
// Usage: node viewer/tools/wild_routes.mjs [--world laurel_fork] [--routes A,B,C] [--walk]   (--walk: walk, don't run)
// Output: build/wilderness/<world>/routes.json. Takes a browser slot.
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { ensureServer, BASE } from './server.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args.splice(i, 2)[1] : d; };
const world = opt('--world', 'laurel_fork');
const only = opt('--routes', '');
const walk = args.includes('--walk');

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
try {
  const page = await (await b.newContext({ viewport: { width: 640, height: 360 } })).newPage();
  page.on('pageerror', (e) => console.log('pageerror:', e.message));
  await page.goto(`${BASE}/viewer/wild.html?world=${world}&t=3&hud=0&q=0&grass=0`);
  await page.waitForFunction(() => window.__loaded, null, { timeout: 300000 });
  const names = only ? only.split(',') : await page.evaluate(() => Object.keys(window.__wild.world.routes));
  const results = {};
  for (const name of names) {
    const r = await page.evaluate(({ name, walk }) => {
      const w = window.__wild, W = w.world, pl = window.__player, cam = window.__three.camera;
      w.pause(true); w.fly = false;
      const R = W.routes[name].map(([x, z]) => ({ x, z }));
      // dense polyline + arc length
      const P = [R[0]], S = [0];
      for (let i = 1; i < R.length; i++) {
        const a = R[i - 1], c = R[i], L = Math.hypot(c.x - a.x, c.z - a.z), n = Math.max(1, Math.ceil(L / 1));
        for (let k = 1; k <= n; k++) { P.push({ x: a.x + (c.x - a.x) * k / n, z: a.z + (c.z - a.z) * k / n }); S.push(S.at(-1) + L / n); }
      }
      const total = S.at(-1);
      pl.pos.set(P[0].x, W.heightAt(P[0].x, P[0].z), P[0].z); pl.vel.set(0, 0, 0);
      const dt = 1 / 60;
      let t = 0, k = 0, best = 0, lastGain = 0, mode = 0, modeT = 0, side = 1;
      const out = { stuck: [], fall: [], crouchM: 0, wadeS: 0, slopeBlocks: 0, minFeet: 1e9, maxFeet: -1e9, skipsM: 0 };
      const thicketAt = (x, z) => { const c = W.cellAt(x, z); return c < 0 ? 0 : W.thicket[c]; };
      let prev = pl.pos.clone();
      while (k < P.length - 3 && t < 1800) {
        // progress: nearest route point ahead of the last one (search a window)
        let bk = k, bd = 1e9;
        for (let q = k; q < Math.min(P.length, k + 40); q++) { const d = Math.hypot(P[q].x - pl.pos.x, P[q].z - pl.pos.z); if (d < bd) { bd = d; bk = q; } }
        k = bk;
        if (S[k] > best + 0.5) { best = S[k]; lastGain = t; if (mode) { mode = 0; } }
        const tgt = P[Math.min(P.length - 1, k + 3)];
        // stuck handling: crouch, jump, sidestep, then skip ahead
        const since = t - lastGain;
        if (since > 1.0 && mode === 0) { mode = 1; modeT = t; }
        if (mode === 1 && t - modeT > 2.0) { mode = 2; modeT = t; }
        if (mode === 2 && t - modeT > 1.0) { mode = 3; modeT = t; side = -side; }
        if (mode === 3 && t - modeT > 2.0) {
          out.stuck.push({ at: [+pl.pos.x.toFixed(1), +pl.pos.y.toFixed(1), +pl.pos.z.toFixed(1)], s: +S[k].toFixed(0) });
          const q = Math.min(P.length - 1, k + 8);
          out.skipsM += S[q] - S[k];
          pl.pos.set(P[q].x, W.heightAt(P[q].x, P[q].z) + 0.05, P[q].z); pl.vel.set(0, 0, 0);
          k = q; best = S[q]; lastGain = t; mode = 0;
        }
        // look at the target (steer); sidestep while in mode 3
        const dx = tgt.x - pl.pos.x, dz = tgt.z - pl.pos.z, L = Math.hypot(dx, dz) || 1;
        cam.position.set(pl.pos.x, pl.pos.y + pl.eye, pl.pos.z);
        cam.lookAt(pl.pos.x + dx / L, pl.pos.y + pl.eye, pl.pos.z + dz / L);
        const ahead = P[Math.min(P.length - 1, k + 2)];
        const tun = thicketAt(pl.pos.x, pl.pos.z) === 128 || thicketAt(ahead.x, ahead.z) === 128;
        const input = { forward: true, run: !walk && !tun && mode === 0, crouch: tun || mode === 1,
          jump: mode === 2 && Math.floor((t - modeT) * 4) % 2 === 0, right: mode === 3 && side > 0, left: mode === 3 && side < 0 };
        pl.update(dt, input);
        t += dt;
        const g = W.heightAt(pl.pos.x, pl.pos.z), f = pl.pos.y - g;
        if (pl.grounded) { out.minFeet = Math.min(out.minFeet, f); out.maxFeet = Math.max(out.maxFeet, f); }
        if (f < -0.3) { out.fall.push([+pl.pos.x.toFixed(1), +pl.pos.z.toFixed(1), +f.toFixed(2)]); pl.pos.y = g; pl.vel.y = 0; }
        if (input.crouch) out.crouchM += pl.pos.distanceTo(prev);
        if (pl.wading) out.wadeS += dt;
        prev.copy(pl.pos);
      }
      w.pause(false);
      return { ...out, routeM: Math.round(total), simS: +t.toFixed(1), done: k >= P.length - 3,
        crouchM: Math.round(out.crouchM), wadeS: +out.wadeS.toFixed(1), skipsM: Math.round(out.skipsM),
        minFeet: +out.minFeet.toFixed(3), maxFeet: +out.maxFeet.toFixed(3), end: [+pl.pos.x.toFixed(1), +pl.pos.z.toFixed(1)] };
    }, { name, walk });
    results[name] = r;
    console.log(`route ${name}: ${r.done ? 'reached the end' : 'DID NOT FINISH'} ${r.routeM} m in ${r.simS} s (${(r.simS / 60).toFixed(1)} min), ` +
      `stuck ${r.stuck.length}${r.stuck.length ? ' ' + JSON.stringify(r.stuck.slice(0, 8)) : ''}, fell through ${r.fall.length}, ` +
      `crouched ${r.crouchM} m, wading ${r.wadeS} s, feet-ground ${r.minFeet}..${r.maxFeet} m`);
  }
  // thickets: standing, the hell blocks; crouched, a tunnel lets you through; inside one you can't stand up
  results.thicket = await page.evaluate(() => {
    const W = window.__wild.world, pl = window.__player, cam = window.__three.camera, dt = 1 / 60;
    const res = W.res, sp = W.spacing, half = W.size / 2, T = W.thicket;
    let tun = null, wall = null;
    for (let k = 0; k < T.length && (!tun || !wall); k++) {
      const i = k % res, j = Math.floor(k / res);
      if (!tun && T[k] === 128 && T[k + 1] === 128 && T[k + 2] === 128 && T[k + res] === 128) tun = [i, j];
      if (!wall && T[k] === 0 && T[k + 1] === 255 && T[k + 2] === 255 && T[k + 3] === 255 && T[k + 4] === 255 && W.heightAt(-half + i * sp, -half + j * sp) > -200) wall = [i, j];
    }
    const run = (x, z, dx, dz, input, secs) => {
      pl.pos.set(x, W.heightAt(x, z), z); pl.vel.set(0, 0, 0);
      if (input.crouch || input.startCrouched) { pl.crouching = true; pl.height = 1.1; } else { pl.crouching = false; pl.height = 1.8; }
      for (let t = 0; t < secs; t += dt) { cam.position.set(pl.pos.x, pl.pos.y + 1, pl.pos.z); cam.lookAt(pl.pos.x + dx, pl.pos.y + 1, pl.pos.z + dz); pl.update(dt, input); }
      return Math.hypot(pl.pos.x - x, pl.pos.z - z);
    };
    const out = {};
    if (wall) { const x = -half + wall[0] * sp, z = -half + wall[1] * sp; out.walkIntoHellM = +run(x, z, 1, 0, { forward: true }, 2).toFixed(2); }
    if (tun) {
      const x = -half + tun[0] * sp, z = -half + tun[1] * sp;
      run(x, z, 1, 0, { crouch: true }, 0.3);
      run(x, z, 0, 0, { startCrouched: true }, 0.5);                // crouched in a tunnel, let go of C: stay down
      out.standsUpInTunnel = !pl.crouching;
    }
    return out;
  });
  console.log('thicket:', JSON.stringify(results.thicket), '(walking into the hell should move < 1 m; standing up in a tunnel: false)');
  fs.writeFileSync(path.join(root, 'build/wilderness', world, 'routes.json'), JSON.stringify(results, null, 1));
} finally { await b.close(); stop(); release(); }
