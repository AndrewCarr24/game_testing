// The opening (viewer/invaders_opening.js) in real time, the player standing still in the entry:
// the five walk up from `from` (gate | court | step), ring, wait, knock, look in, split up and
// break in. Prints the phase timeline, the rings / chimes / knocks / handles, every handoff,
// and takes photos from inside at the moments (through the glass, at the door) plus a high view.
// Usage: GT_BASE=http://localhost:8832 node viewer/tools/invaders_opening_live.mjs [from=court] [secs=150] [out=build/invaders/opening_live] [qs]
import fs from 'fs';
import { withPage } from './invaders_lib.mjs';

const [from = 'court', secs = '150', out = 'build/invaders/opening_live', qs = ''] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
// where the photos are taken from (the player's eye), per phase
const VIEWS = {
  approach: { pos: [1.5, 1.65, 17.5], at: [8, 1.3, 34] },
  gather: { pos: [-1.2, 1.65, 16.8], at: [1.0, 1.4, 22] },
  ring: { pos: [-1.2, 1.65, 16.8], at: [1.4, 1.4, 21] },
  wait1: { pos: [3.2, 1.65, 13.5], at: [0.5, 1.4, 22] },
  knock: { pos: [-0.4, 1.65, 18.4], at: [1.0, 1.3, 21] },
  peer: { pos: [2.6, 1.65, 18.6], at: [3.7, 1.6, 20.5] },
  split: { pos: [0.5, 1.65, 15.5], at: [0, 1.4, 23] },
  probe: { pos: [-20, 1.65, 3], at: [-27.5, 1.3, 0] },
  breakin: { pos: [0.3, 1.65, 14.5], at: [0.3, 1.2, 21] },
};
await withPage(`&grimble=0&fx=0&god=1&invaders=debug&seq=now&seqfrom=${from}&pos=0,1.65,15&look=0,1.5,25${qs}`, async (p) => {
  await p.waitForFunction(() => window.__invaders?.opening, null, { timeout: 60000 });
  await p.evaluate(() => {
    document.querySelectorAll('#hud,#stats,#hint').forEach((e) => (e.style.display = 'none'));
    window.__player.update = () => {};
  });
  const t0 = Date.now(), shot = new Set();
  let last = null;
  while (Date.now() - t0 < +secs * 1000) {
    await p.waitForTimeout(500);
    const s = await p.evaluate(() => window.__invaders.opening.summary());
    if (s.phase !== last) { console.log(`${s.t.toFixed(1).padStart(6)} ${s.phase}${s.reason ? ' (' + s.reason + ')' : ''}  rings ${s.rings} knocks ${s.knocks} handles ${s.handles}`); last = s.phase; }
    const v = VIEWS[s.phase];
    if (v && !shot.has(s.phase)) {
      // (a moment into the phase: the poses have started)
      shot.add(s.phase);
      await p.waitForTimeout(s.phase === 'approach' ? 6000 : s.phase === 'peer' ? 4000 : s.phase === 'probe' ? 15000 : 1200);
      await p.evaluate((v) => { const c = window.__camera; c.position.set(...v.pos); c.lookAt(...v.at); window.__player.pos.set(v.pos[0], 0, v.pos[2]); }, v);
      await p.waitForTimeout(400);
      await p.screenshot({ path: `${out}/${s.phase}.png` });
    }
    if (s.phase === 'done') break;
  }
  const r = await p.evaluate(() => {
    const I = window.__invaders, X = window.__sfx;
    return { summary: I.opening.summary(), events: I.events.filter((e) => /^seq|breach|glass|inside|door/.test(e.kind)), states: I.summary().states,
      sfx: X ? { doorbell: X.counts.doorbell ?? 0, unknownDoorbell: X.unknown?.has('doorbell') ?? null, knock: X.counts.door_knock ?? 0, kick: X.counts.door_kick ?? 0, handle: X.counts.door_locked ?? 0 } : null,
      investigate: I.events.filter((e) => e.kind === 'investigate').map((e) => e.source) };
  });
  for (const e of r.events) console.log(JSON.stringify(e));
  console.log('sfx', JSON.stringify(r.sfx), 'investigate', JSON.stringify(r.investigate), 'states', JSON.stringify(r.states));
  fs.writeFileSync(`${out}/run.json`, JSON.stringify(r, null, 1));
  await p.evaluate(() => { const c = window.__camera; c.position.set(2, 34, 50); c.lookAt(2, 0, 12); });
  await p.waitForTimeout(600);
  await p.screenshot({ path: `${out}/high.png` });
});
