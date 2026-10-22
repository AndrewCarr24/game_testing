// Smoke run of the invaders: load the house with N of them (or the fast waves), let it run in
// real time for `secs`, print the squad's summary and events, and take a few screenshots
// (the player's view and a high view over the entry) with the debug overlay.
// Usage: GT_BASE=http://localhost:8827 node viewer/tools/invaders_smoke.mjs [qs='&invaders=6,debug'] [secs=20] [out=build/invaders/smoke]
import fs from 'fs';
import { withPage } from './invaders_lib.mjs';

const [qs = '&invaders=6,debug', secs = '20', out = 'build/invaders/smoke'] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
await withPage(`&grimble=0&fx=0${qs}`, async (p) => {
  await p.waitForFunction(() => window.__invaders, null, { timeout: 60000 });
  const t0 = Date.now();
  let i = 0;
  while (Date.now() - t0 < +secs * 1000) {
    await p.waitForTimeout(5000);
    const s = await p.evaluate(() => window.__invaders.summary());
    console.log(JSON.stringify({ ...s, stats: undefined, nav: undefined, plans: s.stats.plans, planMs: +(s.stats.planMs).toFixed(1), maxMs: +s.stats.maxMs.toFixed(2), shots: s.stats.shots, hits: s.stats.hits, navFails: s.nav.fails }));
    await p.screenshot({ path: `${out}/eye_${i++}.png` });
  }
  const r = await p.evaluate(() => {
    const I = window.__invaders;
    return { events: I.events.slice(-80), agents: I.agents.map((a) => ({ id: a.id, role: a.role, st: a.state, why: a.why, pos: a.pos.toArray().map((v) => +v.toFixed(1)), layer: a.layer, aware: +a.aware.toFixed(2), stats: a.stats })) };
  });
  for (const e of r.events) console.log('ev', JSON.stringify(e));
  for (const a of r.agents) console.log('ag', JSON.stringify(a));
  // a high view over the front of the house
  await p.evaluate(() => { const c = window.__camera; window.__player.update = () => {}; c.position.set(0, 14, 34); c.lookAt(0, 0, 14); });
  await p.waitForTimeout(500);
  await p.screenshot({ path: `${out}/high.png` });
});
