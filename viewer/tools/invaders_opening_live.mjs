// The opening (viewer/invaders_opening.js) in real time: the five walk up from `from` (gate |
// court | step), ring, wait, knock, look in, split up and break in. Prints the phase timeline,
// the rings / chimes / knocks / handles and every handoff, and takes photos from inside the house
// at the moments (through the glass, at the door, at the great room's glass) plus high views.
// `who`: ghost (the camera roams, nobody is seen: the no-answer run) | entry (the player stands in
// the entry, looking out: they see them).
// Usage: GT_BASE=http://localhost:8832 node viewer/tools/invaders_opening_live.mjs [from=gate] [who=ghost] [secs=200] [out=build/invaders/opening_live] [qs]
import fs from 'fs';
import { withPage } from './invaders_lib.mjs';

const [from = 'gate', who = 'ghost', secs = '200', out = 'build/invaders/opening_live', qs = ''] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
// [phase, seconds into it, eye, look at]
const SHOTS = [
  ['approach', 12, [3, 1.65, 18.2], [12, 1.0, 40]],
  ['approach', 24, [1.5, 1.65, 17.6], [5, 1.2, 28]],
  ['gather', 1.5, [-1.6, 1.65, 16.6], [1.0, 1.3, 22.5]],
  ['ring', 0.45, [3.4, 1.6, 18.7], [1.95, 1.3, 20.8]],
  ['wait1', 4, [3.6, 1.65, 14.5], [0.5, 1.3, 22.5]],
  ['knock', 0.6, [0.2, 1.65, 18.6], [1.8, 1.3, 20.8]],
  ['peer', 5, [3.75, 1.6, 18.7], [3.75, 1.55, 20.6]],
  ['peer', 6, [-3.0, 1.6, 18.3], [-3.75, 1.5, 20.6]],
  ['split', 0.7, [0.5, 1.65, 15.0], [-0.5, 1.3, 23]],
  ['probe', 35, [-21.5, 1.65, 1.2], [-27.2, 1.3, -0.2]],
  ['breakin', 3.5, [1.8, 1.65, 15.8], [-0.75, 1.1, 21]],
];
const ENTRY_SHOTS = [['approach', 20], ['ring', 0.45], ['wait1', 2.5], ['handle', 1.5], ['stare', 1.8], ['breakin', 3.0], ['done', 2.5]];
const HIGH = { approach: [[34, 26, 58], [12, 0, 36]], gather: [[8, 14, 34], [0.5, 0, 22]], probe: [[0, 60, 30], [0, 0, 0]] };
await withPage(`&grimble=0&fx=0&god=1&invaders=on&seq=now&seqfrom=${from}&pos=0,1.65,15&look=0,1.5,25${qs}`, async (p) => {
  await p.waitForFunction(() => window.__invaders?.opening, null, { timeout: 60000 });
  await p.evaluate((who) => {
    document.querySelectorAll('#hud,#stats,#hint').forEach((e) => (e.style.display = 'none'));
    const pl = window.__player;
    pl.update = () => {};
    // ghost: the camera isn't someone they can see
    if (who === 'ghost') { Object.defineProperty(pl, 'hidden', { get: () => true, set: () => {}, configurable: true }); pl.pos.set(9, 4.6, -15); }
    else { pl.pos.set(0.5, 0, 16.5); window.__camera.position.set(0.5, 1.65, 16.5); window.__camera.lookAt(1, 1.4, 24); }
  }, who);
  const t0 = Date.now(), done = new Set();
  let last = null, phaseAt = 0;
  const view = async (name, pos, at) => {
    await p.evaluate(([pos, at]) => { const c = window.__camera; c.position.set(...pos); c.lookAt(...at); }, [pos, at]);
    await p.waitForTimeout(350);
    await p.screenshot({ path: `${out}/${name}.png` });
  };
  while (Date.now() - t0 < +secs * 1000) {
    await p.waitForTimeout(250);
    const s = await p.evaluate(() => window.__invaders.opening.summary());
    if (s.phase !== last) { console.log(`${s.t.toFixed(1).padStart(6)} ${s.phase}${s.reason ? ' (' + s.reason + ')' : ''}  rings ${s.rings} knocks ${s.knocks} handles ${s.handles}`); last = s.phase; phaseAt = s.t; }
    if (who !== 'ghost') {
      // the player's own eye (it stays put: what they see is what they're seen from), turned to the leader
      for (const [i, [ph, dt]] of ENTRY_SHOTS.entries()) {
        if (ph !== s.phase || done.has(i) || s.t - phaseAt < dt) continue;
        done.add(i);
        const L = s.cast.leader?.pos;
        await p.evaluate((L) => { const c = window.__camera; c.lookAt(L[0], 1.45, L[1]); }, L);
        await p.waitForTimeout(300);
        await p.screenshot({ path: `${out}/${String(i).padStart(2, '0')}_${ph}.png` });
      }
      if (s.phase === 'done' && s.t - phaseAt > 4) break;
      continue;
    }
    for (const [i, [ph, dt, pos, at]] of SHOTS.entries()) {
      if (ph !== s.phase || done.has(i) || s.t - phaseAt < dt) continue;
      done.add(i);
      await view(`${String(i).padStart(2, '0')}_${ph}`, pos, at);
      if (HIGH[ph] && !done.has(`h${ph}`)) { done.add(`h${ph}`); await view(`high_${ph}`, ...HIGH[ph]); }
    }
    if (s.phase === 'done' && s.t - phaseAt > 6) break;
  }
  const r = await p.evaluate(() => {
    const I = window.__invaders, X = window.__sfx;
    return { summary: I.opening.summary(), events: I.events.filter((e) => /^seq|breach|glass|inside/.test(e.kind)), states: I.summary().states,
      sfx: X ? { doorbell: X.counts.doorbell ?? 0, unknownDoorbell: X.unknown?.has('doorbell') ?? null, knock: X.counts.door_knock ?? 0, kick: X.counts.door_kick ?? 0, handle: X.counts.door_locked ?? 0 } : null,
      investigate: I.events.filter((e) => e.kind === 'investigate').map((e) => e.source) };
  });
  for (const e of r.events) console.log(JSON.stringify(e));
  console.log('sfx', JSON.stringify(r.sfx), 'investigate', JSON.stringify(r.investigate), 'states', JSON.stringify(r.states));
  fs.writeFileSync(`${out}/run.json`, JSON.stringify(r, null, 1));
  await view('high_end', [2, 34, 50], [2, 0, 12]);
});
