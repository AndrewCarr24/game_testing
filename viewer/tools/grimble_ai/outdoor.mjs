// Outdoor hunting test. With a level that has `grounds` (the engine loads their colliders) it
// runs as is; on a branch without them, pass a mansion.json with `grounds` and the grounds'
// collider file: the hunt is then rebuilt in the page with those colliders added (as index.html
// does) and the player gets the ground to stand on.
// Phase A (before the break-in): the Grimble at the glass, the player out on the west lawn in its
// sight -> it should drop to all fours and hunt them outside. Phase B: the player back inside
// (great room) -> it should go to the glass and break in. Phase C: after it's in, the player goes
// out onto the north terrace in its sight -> it should follow outside.
// Usage (project root): node viewer/tools/grimble_ai/outdoor.mjs <out-dir> [level.json grounds.json (served path)]
import { chromium } from 'playwright-core';
import fs from 'fs';
const [out = 'build/grimble_ai/outdoor', levelFile, groundsUrl] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
fs.mkdirSync('build/locks', { recursive: true });
let slot = null;
while (slot === null) {
  for (let i = 0; i < 3 && slot === null; i++) { try { fs.mkdirSync(`build/locks/browser_${i}`); slot = i; } catch {} }
  if (slot === null) await new Promise((ok) => setTimeout(ok, 3000));
}
const release = () => { try { fs.rmdirSync(`build/locks/browser_${slot}`); } catch {} };
process.on('exit', release);
process.on('uncaughtException', (e) => { console.error(e); release(); process.exit(1); });
process.on('unhandledRejection', (e) => { console.error(e); release(); process.exit(1); });
const grounds = levelFile ? JSON.parse(fs.readFileSync(levelFile, 'utf8')).grounds : null;
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 960, height: 600 } });
p.on('pageerror', (e) => console.log('pageerror:', e.message));
p.on('console', (m) => { if (m.type() === 'error' && !/404/.test(m.text())) console.log('console:', m.text()); });
await p.goto(`${process.env.GT_BASE || 'http://localhost:8765'}/viewer/index.html?level=mansion&gdelay=0&fx=0&pos=-18,1.65,3.5&look=-26,1.5,0`);
await p.waitForFunction(() => window.__loaded && window.__grimble && window.__hunt, null, { timeout: 180000 });
await p.evaluate(async ([grounds, groundsUrl]) => {
  const g = window.__grimble, pl = window.__player, cam = window.__camera, L = window.__level, C = window.__colliders;
  let h = window.__hunt, n = C.filter((c) => c.kind).length;
  document.querySelectorAll('#hud,#stats').forEach((e) => (e.style.display = 'none'));
  if (!L.grounds && grounds) {
    const { GrimbleHunt } = await import('/viewer/grimble_hunt.js');
    const old = h, V3 = g.root.position.constructor, Box3 = old.blockers[0].constructor;
    const data = await (await fetch(groundsUrl)).json();
    const see = new Set(grounds.seeThrough || []);
    for (const [kind, list] of Object.entries(data)) for (const q of list) {
      const box = new Box3(new V3(q[0], q[1], q[2]), new V3(q[3], q[4], q[5]));
      box.fixed = true; box.kind = kind; if (see.has(kind)) box.seeThrough = true;
      C.push(box); n++;
    }
    for (const k of old.blockers) k.min.set(0, -101, 0), k.max.set(0, -100, 0);
    h = new GrimbleHunt(g, { level: { ...L, grounds }, colliders: C, scene: old.scene, interact: window.__interact,
      sightBlockers: () => (window.__interact.sightBlockers ? window.__interact.sightBlockers() : []), opts: {} });
    h.onBreak = old.onBreak;
    g.hunt = h;
  }
  // straight to the glass (knock, wave, stare...)
  g.state = 'walk'; g.root.visible = true; g.s = g.total; g.place(); g.o.waveTime = 0.5; g.o.stare = [3, 3];
  const T = window.__T = { log: [], t: 0, script: null, wp: 0 };
  const origP = pl.update.bind(pl);
  pl.update = (dt, input) => {
    let inp = {};
    const R = T.route;
    if (R && T.wp < R.length && !pl.isDown) {
      const [x, z] = R[T.wp];
      if (Math.hypot(x - pl.pos.x, z - pl.pos.z) < 0.6) T.wp++;
      else { cam.lookAt(x, pl.pos.y + pl.eye, z); inp = { forward: true, run: T.run }; }
    } else { const c = h.chain ? h.chain.hd : g.root.position; cam.lookAt(c.x, 1.6, c.y ?? c.z); }
    origP(dt, inp);
  };
  const origG = g.update.bind(g);
  let acc = 0;
  g.update = (dt, eye) => {
    origG(dt, eye);
    T.t += dt; acc += dt;
    if (acc > 0.25) {
      acc = 0;
      const c = h.chain;
      T.log.push({ t: +T.t.toFixed(2), gs: g.state, hs: h.state, broken: !!h.broken, x: +g.root.position.x.toFixed(2), z: +g.root.position.z.toFixed(2), y: +g.root.position.y.toFixed(2),
        hd: c ? [+c.hd.x.toFixed(2), +c.hd.y.toFixed(2)] : null, P: [+pl.pos.x.toFixed(2), +pl.pos.z.toFixed(2), +pl.pos.y.toFixed(2)], seen: h.seenNow ? 1 : 0, down: pl.isDown ? 1 : 0,
        ls: h.lastSeen ? [+h.lastSeen.x.toFixed(1), +h.lastSeen.y.toFixed(1)] : null });
    }
  };
  T.tp = (x, z, y = 0) => { pl.pos.set(x, y, z); pl.vel.set(0, 0, 0); pl.syncCamera(); };
  T.n = n;
}, [grounds, groundsUrl]);
const ev = (f, a) => p.evaluate(f, a);
const waitT = async (s) => { const t0 = await ev(() => window.__T.t); await p.waitForFunction((t) => window.__T.t >= t, t0 + s, { timeout: s * 3000 + 30000, polling: 200 }); };
const shot = async (name) => {
  const v = await ev(() => { const g = window.__grimble, pl = window.__player; const hb = g.root.getObjectByName('Head'); const w = hb.getWorldPosition(g.root.position.clone()); return { pos: [pl.pos.x, pl.pos.y + pl.eye, pl.pos.z], at: [w.x, w.y - 0.6, w.z] }; });
  await ev((v) => { const cam = window.__camera; window.__freezeCam = v; cam.position.set(...v.pos); cam.lookAt(...v.at); }, v);
  await p.screenshot({ path: `${out}/${name}.png` });
};
const mark = (s) => ev((s) => window.__T.log.push({ mark: s, t: window.__T.t }), s);
console.log('ground boxes', await ev(() => window.__T.n));
// A: wait until it's at the glass (knocking), then the player out on the west lawn, in its sight
await p.waitForFunction(() => ['knock', 'wave', 'watch'].includes(window.__grimble.state), null, { timeout: 60000 });
await ev(() => window.__T.tp(-42, 6, -0.08)); await mark('A: player on the west lawn');
await waitT(1.5); await shot('A1_lawn_it_turns');
await waitT(6); await shot('A2_hunted_outside');
await ev(() => { window.__T.route = [[-45, 16], [-38, 18], [-34, 14]]; window.__T.wp = 0; window.__T.run = true; });
await waitT(10); await shot('A3_after_running');
// B: back inside (teleport into the great room, far from the glass)
await ev(() => { window.__T.route = null; window.__T.tp(-17, -6); }); await mark('B: player back inside');
await waitT(2); await shot('B1_inside');
await waitT(25); await shot('B2_after_25s');
// C: (if it broke in) the player out onto the north terrace through the dining doors' line
await ev(() => window.__T.tp(-18, -23, -0.02)); await mark('C: player on the north terrace');
await waitT(25); await shot('C1_terrace_after_25s');
const log = await ev(() => window.__T.log);
fs.writeFileSync(`${out}/log.json`, JSON.stringify(log));
let prev = '';
for (const l of log) {
  if (l.mark) { console.log('--', l.t.toFixed(1), l.mark); continue; }
  const k = `${l.gs}|${l.hs}|${l.broken}|${l.seen}|${l.down}`;
  if (k !== prev) console.log(l.t, l.gs, l.hs, 'broken', l.broken, 'root', l.x, l.z, l.y, 'hd', JSON.stringify(l.hd), 'P', JSON.stringify(l.P), 'seen', l.seen, 'down', l.down, 'ls', JSON.stringify(l.ls));
  prev = k;
}
await Promise.race([b.close(), new Promise((ok) => setTimeout(ok, 5000))]);
process.exit(0);
