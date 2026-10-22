// Being in the river (viewer/wild/player_hf.js + water_standin.js / water.js + swim.js), with
// the real player stepped at a fixed 60 Hz in the page (simulated time, like wild_routes.mjs):
//   probe   the current down the Laurel River's centreline (depth, speed, direction) and at the
//           creek's riffles
//   wade    across a Laurel Fork riffle and into the river's margin: speed by depth band,
//           splashes, noise
//   pool    swim across a pool (bank to bank), then climb out onto the far bank (Space + forward)
//   dive    dive in the pool: under, breath, back up, the tint
//   swept   swim into the shoals: swept, carried, recovered in the pool below (no wipeout)
//   narrows drift from the bridge pool with no input: swept into the ledge, wiped out, back on
//           the last dry foothold; and from the same spot, swimming for the bank makes it
//   hop     cross the shoals rock to rock (jumps between boulders, a mantle if one falls short)
//   shots   eye screenshots: wading, swimming, under, on a shoal rock, on the bank
//   live    the page's own loop: W held on the keyboard while swimming (main.js's hook runs)
//   mantle  Space + forward from the water onto a rock ~0.75 m over it; one 1.4+ m over it refuses
// Usage: node viewer/tools/wild_water.mjs [--world laurel_fork] [--only probe,wade,...] [--label L] [--water standin]
//   (--water standin: the stand-in field even when water.js is in, for A/B; the field in use is printed)
// Output: build/wilderness/<world>/water/<label>/report.json + *.png. Takes a browser slot.
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { ensureServer, BASE } from './server.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args.splice(i, 2)[1] : d; };
const world = opt('--world', 'laurel_fork');
const only = opt('--only', 'live,probe,wade,pool,dive,swept,narrows,hop,mantle,shots').split(',');
const label = opt('--label', 'latest');
const waterQS = opt('--water', '') === 'standin' ? '&water=standin' : '';   // force the stand-in field (A/B against water.js)
const out = path.join(root, 'build/wilderness', world, 'water', label);
fs.mkdirSync(out, { recursive: true });

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
const report = {};
let fails = 0;
const check = (name, ok, msg) => { console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${name}: ${msg}`); if (!ok) fails++; (report.checks ||= []).push({ name, ok, msg }); };
try {
  const shots = only.includes('shots');
  const page = await (await b.newContext({ viewport: shots ? { width: 1280, height: 720 } : { width: 640, height: 360 } })).newPage();
  page.on('pageerror', (e) => console.log('pageerror:', e.message));
  await page.goto(`${BASE}/viewer/wild.html?world=${world}&t=3&hud=0&q=${shots ? 3 : 0}${shots ? '' : '&grass=0'}${waterQS}`);
  await page.waitForFunction(() => window.__loaded, null, { timeout: 300000 });
  // the in-page harness: place, steer, step
  await page.evaluate(() => {
    const w = window.__wild, W = w.world, pl = window.__player, cam = window.__three.camera, fx = window.__swim.fx, water = pl.water;
    w.pause(true); w.fly = false;
    const H = (window.__H = {
      W, pl, water, fx, cam, dt: 1 / 60,
      // feet on the bed / the float line / a given height
      place(x, z, { y = null, swim = false } = {}) {
        const s = water.surfaceAt(x, z), g = pl.rampHeight({ x, z });
        pl.pos.set(x, y ?? (swim && Number.isFinite(s) ? Math.max(g, s - 1.35) : g), z); pl.vel.set(0, 0, 0);
        pl.swimming = false; pl.crouching = false; pl.height = 1.8;
        Object.assign(pl.waterState, { swept: false, wipeout: null, breath: 1, swimming: false, inWater: false });
        pl._wasIn = false; pl._dive = 0;
        pl.syncCamera();
      },
      look(dx, dz, dy = 0) { const L = Math.hypot(dx, dz) || 1; cam.position.set(pl.pos.x, pl.pos.y + pl.eye, pl.pos.z); cam.lookAt(cam.position.x + dx / L, cam.position.y + dy, cam.position.z + dz / L); },
      lookAt(x, z, dy = 0) { H.look(x - pl.pos.x, z - pl.pos.z, dy); },
      // n frames; fn(i) steers (H.look...) and returns the input, or false to stop
      run(n, fn = () => ({})) {
        for (let i = 0; i < n; i++) {
          const inp = fn(i);
          if (inp === false) return i;
          pl.update(H.dt, inp); fx.update(H.dt);
          const g = W.heightAt(pl.pos.x, pl.pos.z);
          if (pl.pos.y < g - 0.3) H.under = (H.under || 0) + 1;      // (fell through the ground)
        }
        return n;
      },
      hdist(a, b) { return Math.hypot(a.x - b.x, a.z - b.z); },
      snap() { const S = pl.waterState; return { pos: [pl.pos.x, pl.pos.y, pl.pos.z].map((v) => +v.toFixed(2)), band: S.band, imm: +S.imm.toFixed(2),
        depth: +S.depth.toFixed(2), swim: S.swimming, swept: S.swept, sub: S.submerged, breath: +S.breath.toFixed(2), flow: +S.flow.speed.toFixed(2), wipeouts: S.wipeouts }; },
      // the channel: the deepest wet vertex on row z (x in [x0, x1])
      deepest(z, x0 = -800, x1 = 800) {
        let best = null;
        for (let x = x0; x <= x1; x += W.spacing) { const d = water.depthAt(x, z); if (d > (best?.d ?? 0)) best = { x, d }; }
        return best;
      },
      // the banks either side of x on row z: the first dry points (depth < 0.05)
      banks(x, z) {
        let a = x, c = x;
        while (water.depthAt(a, z) > 0.05 && a > x - 120) a -= 0.5;
        while (water.depthAt(c, z) > 0.05 && c < x + 120) c += 0.5;
        return [a, c];
      },
      // a collider box across row z between x0 and x1 (a rock in the way)
      blocked(z, x0, x1) {
        const C = W.colliders;
        for (let k = 0; k < C.length; k += 6) if (C[k + 3] > x0 && C[k] < x1 && C[k + 5] > z - 0.4 && C[k + 2] < z + 0.4 && C[k + 4] > water.surfaceAt((C[k] + C[k + 3]) / 2, z) - 1.2) return true;
        return false;
      },
      // the river's places, from the level data (world.json "river": the bridge, the cascade, the
      // rapids; the player's Narrows circles) and the field itself, so a regenerated channel moves them
      sites() {
        if (H._sites) return H._sites;
        const R = W.meta.river, oy = W.meta.estate_offset[1], tz = (y) => -(y - oy);
        const bridgeZ = tz(R.bridge.a[1]), cascadeZ = tz(R.cascade[1]);
        const [sx, sy, sr] = R.rapids[0];
        const cells = (test) => { const out = []; for (let z = -120; z <= 760; z += 1.5) for (let x = -760; x <= -480; x += 1.5) { const d = water.depthAt(x, z); if (d > 0.1 && test(x, z)) out.push({ x, z, d, f: water.flowAt(x, z, { x: 0, z: 0, speed: 0 }) }); } return out; };
        const reach = {
          bridgePool: cells((x, z) => z > cascadeZ + 25 && z < bridgeZ + 15),
          shoals: cells((x, z) => Math.hypot(x - sx, z - tz(sy)) < sr),
          narrows: cells((x, z) => pl.hazards.some((h) => Math.hypot(x - h.x, z - h.z) < h.r) && z < cascadeZ + 15),
        };
        // the long pool: the row (z 300..700) with the widest run of deep (> 1.7 m), slow (< 0.7 m/s)
        // water and no rock across it
        let pool = null;
        for (let z = 300; z <= 700; z += 3) {
          let run = null, best = null;
          for (let x = -760; x <= -480; x += 0.75) {
            const ok = water.depthAt(x, z) > 1.7 && water.flowAt(x, z).speed < 0.7;
            if (ok) { run ??= { a: x }; run.c = x; if (!best || run.c - run.a > best.c - best.a) best = { ...run }; } else run = null;
          }
          if (!best || best.c - best.a < 10) continue;
          const [ba, bc] = H.banks((best.a + best.c) / 2, z);
          if (H.blocked(z, ba - 3, bc + 3)) continue;
          if (!pool || best.c - best.a > pool.c - pool.a) pool = { z, a: best.a, c: best.c, ba, bc, mid: (best.a + best.c) / 2 };
        }
        // the bridge pool's thalweg row: midway between its banks, 10 m above the bridge
        const bz = bridgeZ - 10, bd = H.deepest(bz, -760, -480), [b0, b1] = H.banks(bd.x, bz);
        return (H._sites = { reach, pool, bridgeZ, cascadeZ, shoal: { x: sx, z: tz(sy), r: sr }, bridgeRow: { z: bz, a: b0, c: b1, mid: (b0 + b1) / 2 } });
      },
    });
  });

  report.field = await page.evaluate(() => (window.__player.water?.standin ? 'stand-in (water_standin.js)' : 'water.js'));
  console.log(`water field: ${report.field}`);

  if (only.includes('live')) {
    console.log('live: the page loop (keyboard), swimming in the pool');
    const pe = [];
    page.on('pageerror', (e) => pe.push(e.message));
    await page.evaluate(() => { const H = window.__H, P = H.sites().pool; H.place(P.mid, P.z, { swim: true }); H.look(1, 0); window.__wild.pause(false); });
    const c0 = await page.evaluate(() => ({ ...window.__swim.counts }));
    await page.keyboard.down('KeyW');
    await page.waitForTimeout(2500);
    await page.keyboard.up('KeyW');
    report.live = await page.evaluate((c0) => { window.__wild.pause(true); const c = window.__swim.counts;
      return { strokes: (c.swim_stroke || 0) - (c0.swim_stroke || 0), state: window.__H.snap() }; }, c0);
    report.live.errors = pe;
    console.log('  ', JSON.stringify(report.live));
    check('live loop: swimming with the keyboard, no errors', report.live.strokes > 0 && report.live.state.swim && !pe.length, `${report.live.strokes} strokes`);
  }

  if (only.includes('probe')) {
    console.log("probe: the current in the Laurel River's reaches (from the level data) and down its rows");
    report.probe = await page.evaluate(async () => {
      const H = window.__H, S = H.sites();
      const { makeWaterStandin } = await import('../viewer/wild/water_standin.js');
      const ref = makeWaterStandin(H.W), rf = { x: 0, z: 0, speed: 0 };
      const downAt = (x, z) => { ref.flowAt(x, z, rf); return rf.speed > 0 ? [rf.x / rf.speed, rf.z / rf.speed] : [0, -1]; };
      const stats = (cells) => {
        const sp = cells.map((c) => c.f.speed).sort((a, b) => a - b), q = (k) => +(sp[Math.floor(k * (sp.length - 1))] ?? NaN).toFixed(2);
        const mx = cells.reduce((a, c) => a + c.f.x, 0), mz = cells.reduce((a, c) => a + c.f.z, 0), L = Math.hypot(mx, mz) || 1;
        const moving = cells.filter((c) => c.f.speed > 0.05);
        const down = moving.filter((c) => { const [dx, dz] = downAt(c.x, c.z); return c.f.x * dx + c.f.z * dz > 0; }).length / Math.max(1, moving.length);
        const dp = cells.map((c) => c.d).sort((a, b) => a - b);
        return { cells: cells.length, p50: q(0.5), p90: q(0.9), depthP50: +(dp[Math.floor(dp.length / 2)] ?? 0).toFixed(2), down: +down.toFixed(2), dir: [+(mx / L).toFixed(2), +(mz / L).toFixed(2)] };
      };
      const reaches = Object.fromEntries(Object.entries(S.reach).map(([k, v]) => [k, stats(v)]));
      // every 10 m row of the main stem from the inflow to the bridge pool: the row's mean current
      const rows = [];
      for (let z = 690; z >= S.bridgeZ - 20; z -= 10) {
        let mx = 0, mz = 0, n = 0, along = 0;
        for (let x = -760; x <= -480; x += 1.5) if (H.water.depthAt(x, z) > 0.1) { const f = H.water.flowAt(x, z), [dx, dz] = downAt(x, z); mx += f.x; mz += f.z; along += f.x * dx + f.z * dz; n++; }
        if (n) rows.push({ z, n, mz: +(mz / n).toFixed(3), mx: +(mx / n).toFixed(3), along: +(along / n).toFixed(3) });
      }
      return { reaches, rows, pool: S.pool, bridgeRow: S.bridgeRow };
    });
    const { reaches: R, rows, pool } = report.probe;
    for (const [k, v] of Object.entries(R)) console.log(`  ${k.padEnd(10)} ${JSON.stringify(v)}`);
    console.log(`  long pool row z ${pool?.z} (${pool?.a}..${pool?.c}, banks ${pool?.ba}..${pool?.bc})`);
    check('the bridge pool is slow', R.bridgePool.p90 <= 0.8, `p50 ${R.bridgePool.p50} p90 ${R.bridgePool.p90} m/s`);
    check('the Shoals have tongues that take your feet (p90 >= 2.1 m/s)', R.shoals.p90 >= 2.1, `p50 ${R.shoals.p50} p90 ${R.shoals.p90} m/s at ${R.shoals.depthP50} m`);
    check('the Narrows are deadly fast (p90 >= 3.2 m/s)', R.narrows.p90 >= 3.2, `p50 ${R.narrows.p50} p90 ${R.narrows.p90} m/s`);
    // (the Narrows' rock garden and chute carry the most lee eddies: 75% there)
    check('each reach flows downstream (eddies aside: >= 80% of its moving cells, the Narrows 75%)', R.bridgePool.down >= 0.8 && R.shoals.down >= 0.8 && R.narrows.down >= 0.75,
      Object.entries(R).map(([k, v]) => `${k} ${v.down}`).join(', '));
    const up = rows.filter((r) => r.along < -0.05), still = rows.filter((r) => r.along < 0.02);
    check('no 10 m row of the gorge runs upstream on average (along the channel)', up.length === 0,
      `${up.length} of ${rows.length} rows upstream${up.length ? ' ' + JSON.stringify(up.slice(0, 6)) : ''}; ${still.length} near-still (pools): ${still.map((r) => r.z).join(' ')}`);
    check('a long pool to swim in', !!pool && pool.c - pool.a > 10, pool ? `z ${pool.z}, ${(pool.c - pool.a).toFixed(1)} m of deep slow water` : 'none');
  }

  if (only.includes('wade')) {
    console.log('wade: from the bank into a pool (speed by depth), then across a creek riffle');
    report.wade = await page.evaluate(() => {
      const H = window.__H, pl = H.pl, S = pl.waterState, dt = H.dt;
      const out = {};
      // into the long pool from its gentler bank, toward the middle (then running: no sprint past the knee)
      const P = H.sites().pool, z = P.z;
      const shelf = (from, dir) => { let x = from; while (H.water.depthAt(x, z) < 1.35 && Math.abs(x - from) < 40) x += dir * 0.25; return Math.abs(x - from); };
      const west = shelf(P.ba, 1) >= shelf(P.bc, -1), sx = west ? P.ba - 2 : P.bc + 2, dir = west ? 1 : -1;
      out.side = west ? 'west' : 'east';
      for (const run of [false, true]) {
        const d = { x: P.mid };
        H.place(sx, z);
        const per = {}, prev = pl.pos.clone(), log0 = H.fx.log.length;
        let swamAt = null;
        H.run(60 * 20, (i) => {
          if (i > 0) { const v = H.hdist(pl.pos, prev) / dt; (per[S.band] ||= []).push(v); }
          prev.copy(pl.pos);
          if (S.swimming && swamAt === null) swamAt = +(i * dt).toFixed(1);
          if ((pl.pos.x - d.x) * dir > 0) return false;
          H.look(dir, 0); return { forward: true, run };
        });
        const steps = H.fx.log.slice(log0).filter((e) => e.kind === 'water_step');
        out[run ? 'run' : 'walk'] = { speeds: Object.fromEntries(Object.entries(per).map(([k, v]) => [k, +(v.slice(5).reduce((s, x) => s + x, 0) / Math.max(1, v.length - 5)).toFixed(2)])),
          swamAfterS: swamAt, steps: steps.length, stepNoise: [...new Set(steps.map((e) => `${e.band}:${e.loudness}`))] };
      }
      // a creek riffle: Laurel Fork (east of x -480), 0.25-0.6 m deep, the current over 1.2 m/s
      let rif = null;
      const W = H.W, half = W.size / 2;
      for (let k = 0; k < W.water.length && !rif; k += 7) {
        if (!Number.isFinite(W.water[k])) continue;
        const x = -half + (k % W.res) * W.spacing, z = -half + Math.floor(k / W.res) * W.spacing;
        if (x < -480) continue;
        const dd = H.water.depthAt(x, z), f = H.water.flowAt(x, z);
        if (dd > 0.25 && dd < 0.6 && f.speed > 1.2) rif = { x, z, f: { x: f.x / f.speed, z: f.z / f.speed }, speed: f.speed, depth: dd };
      }
      if (rif) {
        // across it: perpendicular to the flow, from 6 m one side to 6 m the other
        const px = -rif.f.z, pz = rif.f.x;
        H.place(rif.x - px * 6, rif.z - pz * 6);
        const start = pl.pos.clone(), log0 = H.fx.log.length;
        let wadeT = 0, maxImm = 0;
        H.run(60 * 10, () => {
          if ((pl.pos.x - start.x) * px + (pl.pos.z - start.z) * pz > 12) return false;
          if (S.inWater) { wadeT += dt; maxImm = Math.max(maxImm, S.imm); }
          H.look(px, pz); return { forward: true };
        });
        const along = (pl.pos.x - start.x) * rif.f.x + (pl.pos.z - start.z) * rif.f.z;
        const ev = H.fx.log.slice(log0);
        out.riffle = { at: [rif.x, rif.z].map((v) => +v.toFixed(1)), speed: +rif.speed.toFixed(2), depth: +rif.depth.toFixed(2), wadeS: +wadeT.toFixed(1), maxImm: +maxImm.toFixed(2),
          driftM: +along.toFixed(2), steps: ev.filter((e) => e.kind === 'water_step').length, noises: ev.filter((e) => e.noise).length, swept: S.swept };
      }
      return out;
    });
    const r = report.wade;
    console.log('  walk', JSON.stringify(r.walk)); console.log('  run ', JSON.stringify(r.run)); console.log('  riffle', JSON.stringify(r.riffle));
    const w = r.walk.speeds;
    check('wading slows with depth (walk)', w.ankle > w.knee && w.knee > w.waist && w.waist > w.chest, JSON.stringify(w));
    check('runs only to the knee', (r.run.speeds.waist ?? 0) <= (w.waist ?? 0) * 1.1 && r.run.speeds.knee > w.knee * 1.5, JSON.stringify(r.run.speeds));
    check('deep water = swimming', r.walk.swamAfterS !== null, `swimming after ${r.walk.swamAfterS} s`);
    check('wading splashes (sfx + noise)', r.walk.steps > 3, `${r.walk.steps} steps ${r.walk.stepNoise.join(' ')}`);
    if (r.riffle) check('a riffle is wadeable across (a little drift, no sweep)', !r.riffle.swept && r.riffle.driftM < 3, `drift ${r.riffle.driftM} m, ${r.riffle.steps} splashes`);
  }

  if (only.includes('pool')) {
    console.log('pool: swim across a pool, climb out on the far bank');
    report.pool = await page.evaluate(() => {
      const H = window.__H, pl = H.pl, S = pl.waterState, dt = H.dt;
      const P = H.sites().pool, z = P.z, a = P.ba, c = P.bc;
      H.place(a - 2, z);
      let t = 0, swimT = 0, maxSpeed = 0, climbed = 0, out = null;
      const prev = pl.pos.clone();
      H.run(60 * 90, (i) => {
        t = i * dt;
        if (S.swimming) { swimT += dt; if (i) maxSpeed = Math.max(maxSpeed, H.hdist(pl.pos, prev) / dt); }
        if (S.climbed) climbed++;
        prev.copy(pl.pos);
        if (!S.inWater && pl.pos.x > c - 4 && pl.grounded) { out = t; return false; }
        H.look(1, 0);
        // Space + forward near the far bank (the mantle)
        return { forward: true, jump: pl.pos.x > c - 3 };
      });
      return { width: +(c - a).toFixed(1), crossedS: out === null ? null : +out.toFixed(1), swimS: +swimT.toFixed(1), maxSwimSpeed: +maxSpeed.toFixed(2),
        driftM: +(pl.pos.z - z).toFixed(1), climbs: climbed, end: H.snap(), wipeouts: S.wipeouts };
    });
    const r = report.pool;
    console.log('  ', JSON.stringify(r));
    check('swims across the pool and climbs out', r.crossedS !== null && r.end.band === 'dry', `width ${r.width} m in ${r.crossedS} s (swimming ${r.swimS} s), drift ${r.driftM} m`);
    check('no sprint in the water', r.maxSwimSpeed < 2.2, `max ${r.maxSwimSpeed} m/s over the ground (swim 1.3 + current)`);
  }

  if (only.includes('dive')) {
    console.log('dive: under in the pool, out of air, back up');
    report.dive = await page.evaluate(() => {
      const H = window.__H, pl = H.pl, S = pl.waterState, dt = H.dt;
      const P = H.sites().pool, z = P.z, d = { x: P.mid };
      H.place(d.x, z, { swim: true });
      H.run(60, () => { H.look(0, 1); return {}; });
      const s0 = S.surface;
      let under = 0, minEye = 0;
      H.run(60 * 6, () => { if (S.submerged) under += dt; minEye = Math.min(minEye, pl.pos.y + pl.eye - S.surface); H.look(0, 1, -0.3); return { crouch: true }; });
      const afterDive = { under: +under.toFixed(1), minEyeBelow: +minEye.toFixed(2), breath: +S.breath.toFixed(2), tint: H.fx.el.tint?.style.opacity };
      let upT = null;
      H.run(60 * 6, (i) => { if (!S.submerged && upT === null) upT = +(i * dt).toFixed(1); H.look(0, 1); return {}; });
      // hold the breath to the end: forced up
      H.run(60 * 2, () => ({}));
      let forced = null, upAgain = null;
      H.run(60 * 40, (i) => { if (S.breath <= 0.001 && forced === null) forced = i * dt; if (forced !== null && !S.submerged && upAgain === null) upAgain = i * dt;
        if (forced !== null && i * dt > forced + 3) return false; return { crouch: true }; });
      return { surface: +s0.toFixed(2), afterDive, surfacedS: upT, outOfAirS: forced === null ? null : +forced.toFixed(1), upAfterS: upAgain === null ? null : +(upAgain - forced).toFixed(1), afterOutOfAir: H.snap(), tint: H.fx.el.tint?.style.opacity };
    });
    const r = report.dive;
    console.log('  ', JSON.stringify(r));
    check('C dives under (tint on)', r.afterDive.under > 2 && r.afterDive.tint === '1', `under ${r.afterDive.under} s, eye ${r.afterDive.minEyeBelow} m`);
    check('lets go: back up', r.surfacedS !== null && r.surfacedS < 3, `surfaced in ${r.surfacedS} s`);
    check('out of air: forced up (C still held)', r.outOfAirS !== null && r.upAfterS !== null && r.upAfterS < 2.5 && !r.afterOutOfAir.sub, `out of air at ${r.outOfAirS} s, up ${r.upAfterS} s later`);
  }

  if (only.includes('swept')) {
    console.log('swept: wade into a fast tongue of the Shoals');
    report.swept = await page.evaluate(() => {
      const H = window.__H, pl = H.pl, S = pl.waterState, dt = H.dt, sites = H.sites();
      // tongues: knee-to-waist deep cells where depth x speed is high; approached across the
      // current from 5 m away in slack, shallower water
      const cells = sites.reach.shoals.filter((c) => c.d > 0.45 && c.d < 1.1 && c.d * c.f.speed > 1.6).sort((a, b) => b.d * b.f.speed - a.d * a.f.speed);
      const tries = [];
      for (const t of cells.slice(0, 40)) {
        const ux = t.f.x / t.f.speed, uz = t.f.z / t.f.speed;
        let start = null;
        for (const side of [1, -1]) {
          const x = t.x - uz * 5 * side, z = t.z + ux * 5 * side, d = H.water.depthAt(x, z), f = H.water.flowAt(x, z);
          if (d > 0.15 && d < 0.7 && d * f.speed < 0.6) { start = { x, z }; break; }
        }
        if (!start) continue;
        H.place(start.x, start.z);
        let sweptAt = null, recoveredAt = null, sweptS = 0;
        H.run(60 * 50, (i) => {
          if (S.swept) { sweptS += dt; if (sweptAt === null) sweptAt = i * dt; }
          if (sweptAt !== null && !S.swept && recoveredAt === null) recoveredAt = i * dt;
          if (recoveredAt !== null && i * dt > recoveredAt + 1) return false;
          if (sweptAt === null && i * dt > 6) return false;
          H.lookAt(t.x, t.z); return { forward: true };
        });
        tries.push({ tongue: [t.x, t.z, +t.d.toFixed(2), +t.f.speed.toFixed(2)], sweptAtS: sweptAt === null ? null : +sweptAt.toFixed(1), sweptS: +sweptS.toFixed(1),
          recoveredAtS: recoveredAt === null ? null : +recoveredAt.toFixed(1), carriedM: +Math.hypot(pl.pos.x - start.x, pl.pos.z - start.z).toFixed(1), end: H.snap() });
        if (sweptAt !== null) break;
      }
      return { tongues: cells.length, tries: tries.length, ...(tries.at(-1) || {}), noise: H.fx.log.filter((e) => e.kind === 'water_swept').length };
    });
    const r = report.swept;
    console.log('  ', JSON.stringify(r));
    check('a Shoals tongue takes your feet', r.sweptAtS != null, `${r.tongues} tongues, swept after ${r.sweptAtS} s (try ${r.tries}) in ${JSON.stringify(r.tongue)}`);
    check('carried down and recovered, no wipeout', r.recoveredAtS != null && r.end?.wipeouts === 0, `recovered at ${r.recoveredAtS} s, carried ${r.carriedM} m`);
  }

  if (only.includes('narrows')) {
    console.log('narrows: drift from the bridge pool; then swim for the bank');
    report.narrows = await page.evaluate(() => {
      const H = window.__H, pl = H.pl, S = pl.waterState, dt = H.dt, out = {};
      // a dry foothold: the west bank upstream of the bridge, where you'd get in
      const B = H.sites().bridgeRow, z0 = H.sites().bridgeZ + 22, d0 = H.deepest(z0, -760, -480), [a0] = H.banks(d0.x, z0);
      const fx0 = a0 - 2.5;
      H.place(fx0, z0);
      H.run(60 * 3, () => { H.look(1, 0); return {}; });
      const w0 = S.wipeouts;
      const z = B.z, d = { x: B.mid };
      H.place(d.x, z, { swim: true });
      let doomT = null, back = null, fadeMax = 0, minZ = 1e9;
      H.run(60 * 300, (i) => {
        minZ = Math.min(minZ, pl.pos.z);
        fadeMax = Math.max(fadeMax, +(H.fx.el.fade?.style.opacity || 0));
        if (S.wipeout && doomT === null) doomT = i * dt;
        if (doomT !== null && !S.wipeout) { back = i * dt; return false; }
        H.look(0, -1); return {};
      });
      out.drift = { doomAfterS: doomT === null ? null : +doomT.toFixed(1), backAfterS: back === null ? null : +back.toFixed(1), wipeouts: S.wipeouts - w0,
        respawn: H.snap(), footholdDist: +Math.hypot(pl.pos.x - fx0, pl.pos.z - z0).toFixed(2), deepestZ: +minZ.toFixed(1), fadeMax };
      // the same start, swimming for the nearer bank (Space + forward at the bank)
      H.place(d.x, z, { swim: true });
      const [a, c] = H.banks(d.x, z), dir = d.x - a < c - d.x ? -1 : 1;
      const w1 = S.wipeouts;
      let outT = null;
      H.run(60 * 60, (i) => {
        if (i > 10 && !S.inWater && pl.grounded && S.wipeouts === w1 && H.water.depthAt(pl.pos.x, pl.pos.z) < 0.1) { outT = i * dt; return false; }
        H.look(dir, 0.35); return { forward: true, jump: true };
      });
      out.swimOut = { outAfterS: outT === null ? null : +outT.toFixed(1), wipeouts: S.wipeouts - w1, end: H.snap() };
      return out;
    });
    const r = report.narrows;
    console.log('  drift  ', JSON.stringify(r.drift)); console.log('  swimOut', JSON.stringify(r.swimOut));
    check('drifting into the Narrows wipes out', r.drift.wipeouts === 1 && r.drift.doomAfterS !== null, `after ${r.drift.doomAfterS} s`);
    check('back on the dry foothold', r.drift.respawn.band === 'dry' && r.drift.footholdDist < 4, `${r.drift.footholdDist} m from it, fade ${r.drift.fadeMax}`);
    check('fair: there is time to get out', r.drift.doomAfterS > 10, `${r.drift.doomAfterS} s from the bridge pool to the ledge`);
    check('swimming for the bank from the bridge pool makes it', r.swimOut.outAfterS !== null && r.swimOut.wipeouts === 0, `out after ${r.swimOut.outAfterS} s`);
  }

  if (only.includes('hop')) {
    console.log('hop: across the shoals rock to rock');
    report.hop = await page.evaluate(() => {
      const H = window.__H, pl = H.pl, S = pl.waterState, dt = H.dt, W = H.W, C = W.colliders;
      const { x: cx, z: cz } = H.sites().shoal;
      // the shoal's rocks that break the surface (collider tops over the water)
      const rocks = [];
      for (let k = 0; k < C.length; k += 6) {
        const mx = (C[k] + C[k + 3]) / 2, mz = (C[k + 2] + C[k + 5]) / 2;
        if (Math.hypot(mx - cx, mz - cz) > 42 || C[k + 3] - C[k] < 0.9 || C[k + 5] - C[k + 2] < 0.9) continue;
        const s = H.water.surfaceAt(mx, mz);
        if (!Number.isFinite(s) || C[k + 4] < s + 0.15) continue;
        rocks.push({ x0: C[k], z0: C[k + 2], x1: C[k + 3], z1: C[k + 5], top: C[k + 4], s });
      }
      const gap = (a, b) => Math.hypot(Math.max(0, a.x0 - b.x1, b.x0 - a.x1), Math.max(0, a.z0 - b.z1, b.z0 - a.z1));
      // banks: per rock, the dry ground west / east of it on its row
      // (the river's outer edges on the rock's row: a gravel island in the shoal isn't a bank)
      const edges = (z) => { let a = null, c = null; for (let x = cx - 90; x <= cx + 90; x += 0.5) if (H.water.depthAt(x, z) > 0.05) { a ??= x; c = x; } return [a - 0.5, c + 0.5]; };
      for (const r of rocks) { const z = (r.z0 + r.z1) / 2, [a, c] = edges(z); r.west = r.x0 - a; r.east = c - r.x1; r.wa = a; r.ea = c; }
      // west bank -> east bank, the easiest hops (cost 1 + gap^2): a hop <= 2.8 m (a running jump
      // makes ~4), at most 0.6 m up
      const ok = (a, b) => gap(a, b) <= 2.8 && b.top - a.top <= 0.6;
      const prev = new Map(), cost = new Map(), done = new Set();
      // (a first rock no more than 0.7 m over the bank beside it: a jump from dry ground)
      for (const r of rocks) { const z = (r.z0 + r.z1) / 2; r.bankW = H.W.heightAt(r.wa - 0.6, z); r.bankE = H.W.heightAt(r.ea + 0.6, z); }
      for (const r of rocks) if (r.west <= 1.8 && r.top - r.bankW <= 0.7) { prev.set(r, null); cost.set(r, 1); }
      let end = null;
      for (;;) {
        let r = null; for (const [k, v] of cost) if (!done.has(k) && (!r || v < cost.get(r))) r = k;
        if (!r) break;
        done.add(r);
        if (r.east <= 1.8 && r.bankE - r.top <= 0.6) { end = r; break; }
        for (const n of rocks) if (!done.has(n) && ok(r, n)) { const c = cost.get(r) + 1 + gap(r, n) ** 2; if (!(cost.get(n) <= c)) { cost.set(n, c); prev.set(n, r); } }
      }
      if (!end) {
        const reach = [...prev.keys()];
        return { rocks: rocks.length, path: null, fromWest: reach.length, maxX: Math.max(...reach.map((r) => r.x1)), westStarts: rocks.filter((r) => r.west <= 1.8).length,
          eastEnds: rocks.filter((r) => r.east <= 1.8).length, edges: [rocks[0]?.wa, rocks[0]?.ea], xs: rocks.map((r) => +((r.x0 + r.x1) / 2).toFixed(0)).sort((a, b) => a - b).join(' ') };
      }
      const path = []; for (let r = end; r; r = prev.get(r)) path.unshift(r);
      // drive it: from the west bank, look at the next rock, walk / run, jump at the edge
      const first = path[0], zc = (first.z0 + first.z1) / 2;
      H.place(first.wa - 1.2, zc);
      const inside = (r, x, z, m = 0) => x > r.x0 + m && x < r.x1 - m && z > r.z0 + m && z < r.z1 - m;
      const res = { rocks: rocks.length, hops: path.length + 1, landed: 0, mantles: 0, fellIn: 0, swept: false, log: [] };
      const targets = [...path, { bank: true, x0: path.at(-1).ea + 1, x1: path.at(-1).ea + 4, z0: zc - 50, z1: zc + 50 }];
      let cur = null;
      for (const tgt of targets) {
        const tx = tgt.bank ? tgt.x0 + 1.5 : (tgt.x0 + tgt.x1) / 2, tz = tgt.bank ? (path.at(-1).z0 + path.at(-1).z1) / 2 : (tgt.z0 + tgt.z1) / 2;
        let state = 'approach', done = false, stall = 0;
        const last = pl.pos.clone();
        H.run(60 * 12, (i) => {
          stall = H.hdist(pl.pos, last) < 0.01 ? stall + dt : 0; last.copy(pl.pos);
          const dx = tx - pl.pos.x, dz = tz - pl.pos.z, L = Math.hypot(dx, dz) || 1, ux = dx / L, uz = dz / L;
          const onTarget = tgt.bank ? (!S.inWater && pl.grounded && pl.pos.x > tgt.x0 - 0.5) : (pl.grounded && inside(tgt, pl.pos.x, pl.pos.z) && pl.pos.y >= tgt.top - 0.05);
          if (onTarget) { done = true; return false; }
          if (S.swept) res.swept = true;
          H.look(ux, uz);
          if (S.inWater) { if (state !== 'swim') { res.fellIn++; state = 'swim'; } return { forward: true, jump: true }; }   // fell short: mantle on
          const g = gap(cur || { x0: pl.pos.x, x1: pl.pos.x, z0: pl.pos.z, z1: pl.pos.z }, tgt);
          // jump when the next 0.35 m leaves the current rock (or the bank's dry ground)
          const nx = pl.pos.x + ux * 0.35, nz = pl.pos.z + uz * 0.35;
          const leaving = cur ? !inside(cur, nx, nz) : H.water.depthAt(nx, nz) > 0.05;
          return { forward: true, run: g > 1.1 || L > 3.2, jump: pl.grounded && (leaving || stall > 0.15) };
        });
        res.log.push({ to: tgt.bank ? 'bank' : [+tx.toFixed(1), +tz.toFixed(1), +tgt.top.toFixed(2)], ok: done, state, at: H.snap().pos });
        if (done) { if (state === 'swim') res.mantles++; else res.landed++; if (!tgt.bank && !window.__hopRock && res.landed >= 4) window.__hopRock = [pl.pos.x, pl.pos.z, pl.pos.y]; }
        else break;
        cur = tgt.bank ? null : tgt;
      }
      res.end = H.snap();
      res.crossed = res.log.at(-1).to === 'bank' && res.log.at(-1).ok;
      return res;
    });
    const r = report.hop;
    if (!r.path && !r.log) console.log('   no path:', JSON.stringify(r));
    console.log(`   rocks ${r.rocks}, hops ${r.hops}, landed ${r.landed}, mantles ${r.mantles}, fell in ${r.fellIn}, swept ${r.swept}`);
    for (const l of r.log || []) console.log('    ', JSON.stringify(l));
    check('crosses the shoals rock to rock', r.crossed && r.landed >= r.hops - 2, `${r.landed}/${r.hops} jumps landed, ${r.mantles} mantles`);
  }

  if (only.includes('mantle')) {
    console.log('mantle: from swimming onto a rock (Space + forward), and a rock too high to reach');
    report.mantle = await page.evaluate(() => {
      const H = window.__H, pl = H.pl, S = pl.waterState, dt = H.dt, C = H.W.colliders, out = {};
      // river rocks with deep, slowish water beside them
      const cand = [];
      for (let k = 0; k < C.length; k += 6) {
        const x0 = C[k], z0 = C[k + 2], x1 = C[k + 3], z1 = C[k + 5], top = C[k + 4], mx = (x0 + x1) / 2, mz = (z0 + z1) / 2;
        if (mx > -480 || x1 - x0 < 1.2) continue;
        const s = H.water.surfaceAt(mx, mz);
        if (!Number.isFinite(s)) continue;
        for (const [px, pz, lx, lz] of [[mx, z1 + 0.7, 0, -1], [mx, z0 - 0.7, 0, 1], [x0 - 0.7, mz, 1, 0], [x1 + 0.7, mz, -1, 0]]) {
          const d = H.water.depthAt(px, pz), f = H.water.flowAt(px, pz).speed;
          if (d > 1.6 && f < 1.2) { cand.push({ x0, z0, x1, z1, top, over: top - s, px, pz, lx, lz }); break; }
        }
      }
      const tryOne = (r) => {
        H.place(r.px, r.pz, { swim: true });
        H.run(20, () => { H.look(r.lx, r.lz); return {}; });
        let climbed = false;
        H.run(60 * 4, () => { if (pl.grounded && !S.inWater && pl.pos.y > r.top - 0.05) { climbed = true; return false; } H.look(r.lx, r.lz); return { forward: true, jump: true }; });
        return { over: +r.over.toFixed(2), climbed, end: H.snap() };
      };
      const low = cand.find((r) => r.over > 0.6 && r.over < 0.9), high = cand.find((r) => r.over > 1.4);
      out.candidates = cand.length;
      if (low) out.low = tryOne(low);
      if (high) out.high = tryOne(high);
      return out;
    });
    const r = report.mantle;
    console.log('  ', JSON.stringify(r));
    check('climbs out onto a rock up to ~0.95 m over the water', r.low?.climbed, JSON.stringify(r.low));
    check('a rock 1.4+ m over the water is out of reach', r.high && !r.high.climbed, JSON.stringify(r.high));
  }

  if (shots) {
    console.log('shots: from the eye');
    const setups = {
      // knee-deep at the shoals' west margin, looking out across the rocks
      wade: `(() => { const H = window.__H, c = H.sites().reach.shoals.find((c) => c.d > 0.5 && c.d < 0.65 && c.f.speed < 1.2 && !H.blocked(c.z, c.x - 1, c.x + 1));
        H.place(c.x, c.z); H.run(40, () => { H.look(0.3, -1, -0.05); return {}; }); })()`,
      // floating in the bridge pool, the swinging bridge upstream
      swim: `(() => { const H = window.__H, B = H.sites().bridgeRow, z = B.z - 6; H.place(B.mid, z, { swim: true });
        H.run(90, () => { H.look(0.15, 1, 0.12); return {}; }); })()`,
      // under: diving in the pool at z 440
      under: `(() => { const H = window.__H, P = H.sites().pool, z = P.z, d = { x: P.mid }; H.place(d.x, z, { swim: true });
        H.run(60 * 2.5, () => { H.look(0.3, 1, -0.1); return { crouch: true }; }); })()`,
      // on a rock mid-shoal, looking downstream over the white water
      rock: `(() => { const H = window.__H, r = window.__hopRock; if (r) H.place(r[0], r[1], { y: r[2] }); H.run(30, () => { H.look(0.1, -1, -0.12); return {}; }); })()`,
      // swept in the shoals
      swept: `(() => { const H = window.__H, t = H.sites().reach.shoals.filter((c) => c.d > 0.5 && c.d * c.f.speed > 1.8)[0];
        H.place(t.x, t.z); H.run(60 * 1.0, () => { H.look(t.f.x, t.f.z, -0.05); return {}; }); })()`,
      // on the bank above the bridge pool, looking at the river and the bridge
      bank: `(() => { const H = window.__H, z = H.sites().bridgeZ + 28, d = H.deepest(z, -760, -480), [a] = H.banks(d.x, z); H.place(a - 3, z);
        H.run(30, () => { H.look(1, -0.55, -0.08); return {}; }); })()`,
    };
    report.shots = {};
    for (const [name, js] of Object.entries(setups)) {
      await page.evaluate(js);
      await page.evaluate(async () => { const w = window.__wild; w.pause(false);
        await new Promise((ok) => { let n = 0; const f = () => (++n < 14 ? requestAnimationFrame(f) : ok()); requestAnimationFrame(f); }); w.pause(true); });
      const snap = await page.evaluate(() => window.__H.snap());
      await page.screenshot({ path: path.join(out, `${name}.png`) });
      report.shots[name] = snap;
      console.log(`  ${name.padEnd(6)} ${JSON.stringify(snap)}`);
    }
  }

  report.fellThrough = await page.evaluate(() => window.__H.under || 0);
  check('never under the ground', report.fellThrough === 0, `${report.fellThrough} frames`);
} catch (e) {
  console.log('FAILED', e.stack || e.message); fails++;
} finally {
  fs.writeFileSync(path.join(out, 'report.json'), JSON.stringify(report, null, 1));
  console.log(fails ? `${fails} FAILED` : 'all ok', '->', path.relative(root, out));
  await b.close(); stop(); release();
}
