// The waves on a fast clock (?waves=fast: 6 at 6 s, 20 at 30 s, 50 at 60 s), in real time, the
// player standing in the entry with ?god=1 (hit, never killed, so the squad keeps working):
// alive counts after each wave, where they came in, what they're doing, the invaders' CPU per frame
// (mean / max), the page's frame time, nav plans and failures. Screenshots: the player's view and
// a high view of the house at the end.
// Usage: GT_BASE=http://localhost:8827 node viewer/tools/invaders_waves.mjs [secs=75] [out=build/invaders/waves] [qs]
import fs from 'fs';
import { withPage } from './invaders_lib.mjs';

const [secs = '75', out = 'build/invaders/waves', qs = ''] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const rows = [];
await withPage(`&grimble=0&fx=0&waves=fast&god=1&invaders=debug${qs}`, async (p) => {
  await p.waitForFunction(() => window.__invaders, null, { timeout: 60000 });
  // frame times from the page's own loop
  await p.evaluate(() => {
    const F = window.__frames = { t: [], last: performance.now() };
    const tick = (now) => { F.t.push(now - F.last); F.last = now; if (F.t.length > 20000) F.t.shift(); requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  });
  const t0 = Date.now();
  let shot = 0;
  for (let k = 1; Date.now() - t0 < +secs * 1000; k++) {
    await p.waitForTimeout(5000);
    const s = await p.evaluate(() => {
      const I = window.__invaders, F = window.__frames.t.splice(0);
      F.sort((a, b) => a - b);
      const st = I.stats, f = Math.max(1, st.frames);
      const r = { t: +I.time.toFixed(1), alive: I.alive().length, inside: I.agents.filter((a) => a.alive && a.inside).length, watchers: I.agents.filter((a) => a.alive && a.role === 'watcher').length,
        states: I.summary().states, cpuMean: +(st.thinkMs / f).toFixed(3), cpuMax: +st.maxMs.toFixed(2), frameP50: +(F[Math.floor(F.length / 2)] ?? 0).toFixed(1), frameP95: +(F[Math.floor(F.length * 0.95)] ?? 0).toFixed(1),
        plans: st.plans, planMs: +st.planMs.toFixed(0), navFails: I.world.nav.stats.fails, shots: st.shots, playerHits: st.playerHits, queue: I.queue.length };
      st.thinkMs = 0; st.frames = 0; st.maxMs = 0;
      return r;
    });
    rows.push(s);
    console.log(JSON.stringify(s));
    if (s.alive >= 50 && shot++ < 1) await p.screenshot({ path: `${out}/eye_50.png` });
  }
  const ent = await p.evaluate(() => { const c = {}; for (const e of window.__invaders.events) if (e.kind === 'spawn') c[e.entry ?? e.role] = (c[e.entry ?? e.role] ?? 0) + 1; return c; });
  console.log('entries', JSON.stringify(ent));
  await p.evaluate(() => { const c = window.__camera; window.__player.update = () => {}; c.position.set(0, 38, 46); c.lookAt(0, 0, 4); });
  await p.waitForTimeout(600);
  await p.screenshot({ path: `${out}/high.png` });
});
fs.writeFileSync(`${out}/waves.json`, JSON.stringify(rows, null, 1));
