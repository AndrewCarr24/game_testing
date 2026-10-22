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
// Usage: node viewer/tools/wild_water.mjs [--world laurel_fork] [--only probe,wade,...] [--label L]
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
const only = opt('--only', 'probe,wade,pool,dive,swept,narrows,hop,shots').split(',');
const label = opt('--label', 'latest');
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
  await page.goto(`${BASE}/viewer/wild.html?world=${world}&t=3&hud=0&q=${shots ? 3 : 0}${shots ? '' : '&grass=0'}`);
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
        Object.assign(pl.waterState, { swept: false, wipeout: null, breath: 1 });
        pl._wasIn = false; pl._dive = 0;
        pl.syncCamera();
      },
      look(dx, dz, dy = 0) { const L = Math.hypot(dx, dz) || 1; cam.position.set(pl.pos.x, pl.pos.y + pl.eye, pl.pos.z); cam.lookAt(cam.position.x + dx / L, cam.position.y + dy, cam.position.z + dz / L); },
      lookAt(x, z, dy = 0) { H.look(x - pl.pos.x, z - pl.pos.z, dy); },
      step(input = {}, n = 1, each) {
        for (let i = 0; i < n; i++) { pl.update(H.dt, input); fx.update(H.dt); if (each && each(i) === false) return i; }
        return n;
      },
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
    });
  });

  if (only.includes('probe')) {
    console.log('probe: the current down the Laurel River');
    report.probe = await page.evaluate(() => {
      const H = window.__H, rows = [];
      for (let z = 740; z >= -70; z -= 20) {
        const d = H.deepest(z, -760, -480);
        if (!d) continue;
        const f = H.water.flowAt(d.x, z), [a, c] = H.banks(d.x, z);
        rows.push({ z, x: +d.x.toFixed(1), depth: +d.d.toFixed(2), width: +(c - a).toFixed(1), speed: +f.speed.toFixed(2), dir: [+(f.x / (f.speed || 1)).toFixed(2), +(f.z / (f.speed || 1)).toFixed(2)],
          margin: +H.water.flowAt(a + 1.5, z).speed.toFixed(2) });
      }
      return rows;
    });
    for (const r of report.probe) console.log(`  z ${String(r.z).padStart(4)} x ${r.x} depth ${r.depth} width ${r.width} speed ${r.speed} (margin ${r.margin}) dir ${r.dir}`);
    const at = (z0, z1) => report.probe.filter((r) => r.z >= z0 && r.z <= z1), down = at(1, 699);
    const sp = (rows) => rows.map((r) => r.speed).join(' ');
    check('the bridge pool is slow (z 20..40)', at(20, 40).every((r) => r.speed < 0.8), sp(at(20, 40)));
    check('the shoals run fast (z 200..260)', at(200, 260).every((r) => r.speed > 1.6), sp(at(200, 260)));
    check('the Narrows are deadly fast (z -60..-20)', at(-60, -20).every((r) => r.speed > 3.4), sp(at(-60, -20)));
    const med = report.probe.map((r) => r.speed).sort((a, b) => a - b)[Math.floor(report.probe.length / 2)];
    check('a typical run is swimmable across', med < 2.0, `median ${med} m/s`);
    check('flows downstream (-z) through the gorge', down.every((r) => r.dir[1] < 0), `${down.filter((r) => r.dir[1] >= 0).length} rows not`);
  }
} catch (e) {
  console.log('FAILED', e.stack || e.message); fails++;
} finally {
  fs.writeFileSync(path.join(out, 'report.json'), JSON.stringify(report, null, 1));
  console.log(fails ? `${fails} FAILED` : 'all ok', '->', path.relative(root, out));
  await b.close(); stop(); release();
}
