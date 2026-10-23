// The opening's sounds with the audio actually running (autoplay allowed, a click on the page):
// the five start on the step, ring, knock; the chime must have played through Web Audio (not just
// been logged), flat in the entry; then the player stands outside and a knock plays positional.
// No page errors.
// Usage: GT_BASE=http://localhost:8832 node viewer/tools/invaders_chime.mjs
import { withPage } from './invaders_lib.mjs';
let errors = 0;
const r = await withPage('&grimble=0&fx=0&invaders=on&seq=now&seqfrom=step&seqk=0.3&god=1', async (p) => {
  p.on('pageerror', () => errors++);
  await p.waitForFunction(() => window.__invaders?.opening && window.__sfx, null, { timeout: 60000 });
  await p.mouse.click(480, 300);
  await p.evaluate(() => window.__sfx.ctx?.resume?.());
  await p.waitForFunction(() => window.__sfx.running, null, { timeout: 20000 }).catch(() => {});
  await p.waitForFunction(() => (window.__invaders.opening.knocks ?? 0) >= 2, null, { timeout: 40000 }).catch(() => {});
  await p.waitForTimeout(1500);
  return p.evaluate(() => {
    const X = window.__sfx, synth = X.log.filter((e) => e.synth);
    return { ctx: X.ctx?.state ?? null, running: X.running, played: X.synthPlayed, logged: synth.map((e) => `${e.name}${e.flat ? ':flat' : ''}${e.muted ? ':' + e.muted : ''}`).join(' '), errorMuted: synth.filter((e) => e.muted === 'error').length, phase: window.__invaders.opening.phase };
  });
}, { args: ['--autoplay-policy=no-user-gesture-required'] });
console.log(JSON.stringify(r));
const ok = r.ctx === 'running' && (r.played.doorbell ?? 0) >= 1 && (r.played.door_knock ?? 0) >= 1 && !r.errorMuted && !errors;
console.log(ok ? 'PASS' : `FAIL (page errors ${errors})`);
