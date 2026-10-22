// Invader AI suite: one page load (no waves, the debug overlay on), then the scenarios in
// invaders_scenarios.js run fast-forward (invaders_page.js: K substeps of 1/60 s per frame,
// seeded Math.random), each with the squad cleared and the player reset. Per scenario: PASS/FAIL
// and its metrics, a log (build/invaders/<label>/<name>.json) and photos (the player's eye and a
// high view) at the end. Summary in summary.txt.
// Usage: GT_BASE=http://localhost:8827 node viewer/tools/invaders_suite.mjs <label> [names|all] [seed=1]
import fs from 'fs';
import path from 'path';
import { withPage } from './invaders_lib.mjs';

const HERE = path.dirname(new URL(import.meta.url).pathname);
const [label = 'x', names = 'all', seed = '1'] = process.argv.slice(2);
const out = `build/invaders/${label}`;
fs.mkdirSync(out, { recursive: true });
const scSrc = fs.readFileSync(`${HERE}/invaders_scenarios.js`, 'utf8');
const pageSrc = fs.readFileSync(`${HERE}/invaders_page.js`, 'utf8');
const lines = [];
const say = (s) => { console.log(s); lines.push(s); };

await withPage(`&grimble=0&fx=0&waves=0&invaders=debug${process.env.QS || ''}`, async (p) => {
  await p.waitForFunction(() => window.__invaders && window.__combat, null, { timeout: 60000 });
  await p.evaluate(`(${pageSrc})()`);
  await p.evaluate(`window.__SC = ${scSrc}`);
  const all = await p.evaluate(() => Object.keys(window.__SC));
  const list = names === 'all' ? all : names.split(',');
  let fails = 0;
  for (const name of list) {
    const t0 = Date.now();
    await p.evaluate((n) => window.__S.run(window.__SC[n]), name);
    for (;;) {
      await p.waitForTimeout(250);
      if (await p.evaluate(() => window.__S.done)) break;
      if (Date.now() - t0 > 300000) { say(`${name}: timeout`); break; }
    }
    const r = await p.evaluate(() => { const r = window.__S.result(); return { ...r, log: window.__S.log }; });
    fs.writeFileSync(`${out}/${name}.json`, JSON.stringify(r, null, 1));
    const { pass, marks, events, summary, log, ...metrics } = r;
    if (!pass) fails++;
    say(`${pass ? 'PASS' : 'FAIL'} ${name.padEnd(12)} ${JSON.stringify(metrics)}  (${((Date.now() - t0) / 1000).toFixed(0)} s, ${summary.msPerFrame} ms/frame)`);
    // photos: the player's eye, and from above the nearest invader
    await p.evaluate(() => { const S = window.__S; S.done = false; S.paused = true; S.photo = null; });
    await p.screenshot({ path: `${out}/${name}_eye.png` });
    const high = await p.evaluate(() => {
      const I = window.__invaders, pl = window.__player;
      const a = I.agents.filter((x) => x.alive).sort((x, y) => x.pos.distanceTo(pl.pos) - y.pos.distanceTo(pl.pos))[0] ?? I.agents[0];
      const c = a ? a.pos : pl.pos;
      return { pos: [c.x + 4, c.y + 6.5, c.z + 6], at: [c.x, c.y + 0.8, c.z] };
    });
    await p.evaluate((v) => { window.__S.photo = v; }, high);
    await p.waitForTimeout(300);
    await p.screenshot({ path: `${out}/${name}_high.png` });
    await p.evaluate(() => { const S = window.__S; S.paused = false; S.done = true; S.photo = null; });
  }
  say(fails ? `${fails} FAIL` : 'all PASS');
}, { seed: +seed });
fs.writeFileSync(`${out}/summary.txt`, lines.join('\n') + '\n');
