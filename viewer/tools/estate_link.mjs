// The estate <-> wilderness handoff (design/wilderness/estate_link.md), end to end in one tab:
// the house loads; the player comes down the drive (the gate opens, the wilderness loads into
// its iframe); out through the gate (the house suspends, the wild shows with the player handed
// over); out on the meadow, turn round, back in through the gate (the house resumes, the player
// inside the gate). Then the stand-alone fallback: wild.html on its own, in through the gate ->
// index.html?from=wild with the player inside. Screenshots into build/estate_link/ (or argv[2]).
//   node viewer/tools/estate_link.mjs [outdir]
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { ensureServer, BASE } from './server.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const out = process.argv[2] || path.join(root, 'build/estate_link');
fs.mkdirSync(out, { recursive: true });
const locks = path.join(root, 'build/locks');
let slot = null;
for (let t = 0; !slot; t++) {
  for (let i = 0; i < 3 && !slot; i++) { try { fs.mkdirSync(path.join(locks, `browser_${i}`)); slot = path.join(locks, `browser_${i}`); } catch {} }
  if (!slot) { if (t === 0) console.log('waiting for a browser slot...'); await new Promise((r) => setTimeout(r, 2000)); }
}
const release = () => { try { fs.rmdirSync(slot); } catch {} };
process.on('exit', release);
const stop = await ensureServer();
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
let fails = 0;
const check = (ok, msg) => { console.log(`${ok ? 'ok  ' : 'FAIL'} ${msg}`); if (!ok) fails++; };
try {
  const page = await b.newPage({ viewport: { width: 1280, height: 720 } });
  page.on('pageerror', (e) => console.log('pageerror:', e.message));
  page.on('console', (m) => { if (m.type() === 'error' && !/404/.test(m.text())) console.log('console:', m.text()); });
  const frames = (n) => page.evaluate((n) => new Promise((ok) => { const s = () => (n-- > 0 ? requestAnimationFrame(s) : ok()); s(); }), n);
  const shot = (name) => page.screenshot({ path: path.join(out, `${name}.png`) });
  const hide = () => page.addStyleTag({ content: 'body > *:not(canvas):not(iframe) { display: none !important; }' });
  // a player in the house: put them somewhere, looking somewhere (eye height above the feet)
  const placeHouse = (pos, look) => page.evaluate(([pos, look]) => {
    const p = window.__player, c = window.__three.camera;
    p.pos.set(pos[0], pos[1], pos[2]); p.vel.set(0, 0, 0); p.syncCamera(); c.lookAt(...look);
  }, [pos, look]);
  const wild = (fn, arg) => page.evaluate(([src, arg]) => {
    const w = document.querySelector('iframe').contentWindow;
    return new w.Function('arg', src).call(w, arg);
  }, [`return (${fn})(arg)`, arg]);

  const t0 = Date.now();
  await page.goto(`${BASE}/viewer/index.html?level=mansion&grimble=0`);
  await page.waitForFunction(() => window.__loaded, null, { timeout: 180000 });
  await hide();
  console.log(`house loaded in ${Date.now() - t0} ms`);
  // 1. down the drive: the gate opens by itself, the wilderness starts loading
  await placeHouse([19.75, 0, 54], [19.75, 1.6, 80]);
  await frames(20);
  await shot('1_house_drive_gate_opening');
  await page.waitForFunction(() => window.__estateGate?.t >= 1 && window.__estateGate?.ready, null, { timeout: 120000 });
  const loadMs = await page.evaluate(() => window.__estateGate.loadMs);
  check(true, `gate open, wilderness ready (iframe load ${loadMs} ms)`);
  await placeHouse([19.75, 0, 60.5], [19.75, 1.6, 90]);
  await frames(6);
  await shot('2_house_at_the_open_gate');
  // 2. out through the gate
  await placeHouse([19.75, 0, 62.85], [19.75, 1.6, 90]);
  await page.waitForFunction(() => window.__suspended === true, null, { timeout: 10000 }).catch(() => {});
  check(await page.evaluate(() => window.__suspended === true), 'crossing the gate line suspends the house');
  await page.waitForTimeout(500);
  const wp = await wild(() => window.__player.pos.toArray());
  check(Math.abs(wp[0] - 19.75) < 0.5 && Math.abs(wp[2] - (62.85 - 810)) < 0.6, `the player is in the wilderness at the gate (${wp.map((v) => v.toFixed(2))})`);
  await frames(10);
  await shot('3_wild_just_through_the_gate');
  // 3. out onto the meadow, look back at the gate and the house
  await wild(() => { const p = window.__player; p.pos.set(19.75, window.__wild.world.heightAt(19.75, -735), -735); p.vel.set(0, 0, 0); p.syncCamera(); window.__three.camera.lookAt(19.75, 3, -800); });
  await frames(10);
  await shot('4_wild_meadow_looking_back');
  // 4. back in through the gate
  await wild(() => { const p = window.__player; p.pos.set(19.75, 0, -747.5); p.vel.set(0, 0, 0); p.syncCamera(); });
  await page.waitForFunction(() => window.__suspended === false, null, { timeout: 10000 }).catch(() => {});
  check(await page.evaluate(() => window.__suspended === false), 'walking back in through the gate resumes the house');
  const hp = await page.evaluate(() => window.__player.pos.toArray());
  check(Math.abs(hp[2] - 62.5) < 0.5 && Math.abs(hp[0] - 19.75) < 0.5, `the player is inside the gate (${hp.map((v) => v.toFixed(2))})`);
  check(await wild(() => window.__wildGate.suspended), 'the wilderness is paused while the house plays');
  await frames(10);
  await shot('5_house_back_inside');
  // a second trip out: instant (the wilderness stays loaded)
  await placeHouse([19.75, 0, 58], [19.75, 1.6, 90]);
  await frames(4);
  const t1 = Date.now();
  await placeHouse([19.75, 0, 62.85], [19.75, 1.6, 90]);
  await page.waitForFunction(() => window.__suspended === true, null, { timeout: 5000 }).catch(() => {});
  check(await page.evaluate(() => window.__suspended === true), `second trip out (${Date.now() - t1} ms)`);

  // 5. stand-alone wilderness: in through the gate navigates to the house
  await page.goto(`${BASE}/viewer/wild.html?world=laurel_fork&hud=0`);
  await page.waitForFunction(() => window.__loaded, null, { timeout: 120000 });
  await page.evaluate(() => { const p = window.__player; p.pos.set(19.75, window.__wild.world.heightAt(19.75, -740), -740); p.syncCamera(); });
  await frames(4);
  await page.evaluate(() => { const p = window.__player; p.pos.set(19.75, 0, -747.5); p.syncCamera(); });
  await page.waitForURL(/from=wild/, { timeout: 20000 }).catch(() => {});
  await page.waitForFunction(() => window.__loaded, null, { timeout: 180000 }).catch(() => {});
  const hp2 = await page.evaluate(() => window.__player?.pos.toArray());
  check(!!hp2 && Math.abs(hp2[2] - 62.5) < 0.6, `stand-alone: the house loads with the player inside the gate (${hp2?.map((v) => v.toFixed(2))})`);
  await hide();
  await page.evaluate(() => window.__three.camera.lookAt(19.75, 1.6, 30));
  await frames(10);
  await shot('6_house_from_standalone_wild');
} finally { await b.close(); stop(); release(); }
console.log(fails ? `${fails} FAILED` : 'all ok', '->', out);
process.exit(fails ? 1 : 0);
