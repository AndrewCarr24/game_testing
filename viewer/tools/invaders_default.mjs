// The game's default path: no ?invaders in the URL and navigator.webdriver spoofed false (as a
// player's browser): the squad must be there with the opening (the first five at the front door,
// viewer/invaders_opening.js; here ?seq=now so they come at once) and no waves (?waves=old brings
// those back), no overlay, and no Grimble (it lives in the forest now; ?grimble=house brings the
// old visit back). Then the sounds asked for that the sound sprite lacks, and the bodies' cost.
// Usage: GT_BASE=http://localhost:8832 node viewer/tools/invaders_default.mjs
import { withPage } from './invaders_lib.mjs';
const r = await withPage('&fx=0&god=1&seq=now', async (p) => {
  await p.waitForFunction(() => window.__invaders, null, { timeout: 60000 });
  await p.waitForTimeout(40000);
  return p.evaluate(() => {
    const I = window.__invaders, f = Math.max(1, I.stats.frames), O = I.opening;
    return { invaders: !!I, waves: I.waves.map((w) => w.at), opening: O ? { phase: O.phase, delay: O.delay, rings: O.rings } : null, debug: I.debug, grimble: !!window.__grimble, hunt: !!window.__hunt, alive: I.alive().length, rig: !!I.bodies.rig,
      aiMs: +(I.stats.thinkMs / f).toFixed(3), bodyMs: +(I.stats.bodyMs / f).toFixed(3), unknownSfx: [...(window.__sfx?.unknown ?? [])] };
  });
}, { init: () => Object.defineProperty(navigator, 'webdriver', { get: () => false }) });
console.log(JSON.stringify(r));
const ok = r.invaders && !r.waves.length && r.opening && r.alive === 5 && !r.debug && !r.grimble;
console.log(ok ? 'PASS' : 'FAIL');
