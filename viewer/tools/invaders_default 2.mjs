// The game's default path: no ?invaders in the URL and navigator.webdriver spoofed false (as a
// player's browser): the squad must be there with the real wave schedule, no overlay, and no
// Grimble (it lives in the forest now; ?grimble=house brings the old visit back). Then the
// sounds asked for that the sound sprite lacks, and the bodies' cost per frame.
// Usage: GT_BASE=http://localhost:8827 node viewer/tools/invaders_default.mjs
import { withPage } from './invaders_lib.mjs';
const r = await withPage('&fx=0&waves=fast&god=1', async (p) => {
  await p.waitForFunction(() => window.__invaders, null, { timeout: 60000 });
  await p.waitForTimeout(40000);
  return p.evaluate(() => {
    const I = window.__invaders, f = Math.max(1, I.stats.frames);
    return { invaders: !!I, waves: I.waves.map((w) => w.at), debug: I.debug, grimble: !!window.__grimble, hunt: !!window.__hunt, alive: I.alive().length, rig: !!I.bodies.rig,
      aiMs: +(I.stats.thinkMs / f).toFixed(3), bodyMs: +(I.stats.bodyMs / f).toFixed(3), unknownSfx: [...(window.__sfx?.unknown ?? [])] };
  });
}, { init: () => Object.defineProperty(navigator, 'webdriver', { get: () => false }) });
console.log(JSON.stringify(r));
