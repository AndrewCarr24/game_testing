// The friendly Grimble of Poplar Cove (viewer/wild/grimble_wild.js), scripted in the wild runtime
// (viewer/wild.html?world=laurel_fork) with the real player (player_hf.js: colliders, slopes,
// water) stepped at a fixed 60 Hz in the page (simulated time, the render loop paused; frames are
// drawn only for the photos):
//   1. from the creek trail (route A at its nearest to the home, view=grimble) the player walks
//      toward its home across the Poplar branch: the first sight of it (its head sees the
//      player's eye past the trunks), the notice (it turns, the head tilts), the wave
//   2. the player walks away along the trail toward the gate: it follows at a distance, then
//      waves goodbye (time / leash / lost) and walks home
//   3. back at home: the player comes over quietly (crouched) and watches it (a tree, the pat with
//      the leaves coming down, its rest)
//   4. the player walks straight at it: it steps aside / backs off; the player never gets inside it
// Checked every frame: its footprint (footR) never inside a trunk, log or boulder collider (the
// world's boxes, filtered here on their own), the player never inside its soft collider, no
// knock-downs or hits. Photos from the player's eye: first sight, notice, wave, following, the
// goodbye, at home, stepping aside.
// Usage: node viewer/tools/wild_grimble.mjs [label] [--profile gpu|soft] [--seed N]
// Output: build/wilderness/laurel_fork/grimble/<label>/ (report.json, *.png, contact.png). Takes a browser slot.
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import { execFileSync } from 'child_process';
import { fileURLToPath } from 'url';
import { ensureServer, BASE } from './server.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args.splice(i, 2)[1] : d; };
const profile = opt('--profile', 'gpu');
const seed = +opt('--seed', 3);
const label = args[0] || 'latest';
const out = path.join(root, 'build/wilderness/laurel_fork/grimble', label);
fs.mkdirSync(out, { recursive: true });
const P = { gpu: { angle: 'metal', w: 1600, h: 900, q: 3 }, soft: { angle: 'swiftshader', w: 1280, h: 720, q: 0 } }[profile];

const locks = path.join(root, 'build/locks');
fs.mkdirSync(locks, { recursive: true });
let slot = null;
while (!slot) {
  for (let i = 0; i < 3 && !slot; i++) { try { fs.mkdirSync(path.join(locks, `browser_${i}`)); slot = path.join(locks, `browser_${i}`); } catch {} }
  if (!slot) await new Promise((r) => setTimeout(r, 2000));
}
const release = () => { try { fs.rmdirSync(slot); } catch {} };
process.on('exit', release);
const stop = await ensureServer();
const b = await chromium.launch({ channel: 'chrome', args: [`--use-angle=${P.angle}`] });
const report = { label, profile, seed, phases: {}, shots: [], errors: [] };
try {
  const page = await (await b.newContext({ viewport: { width: P.w, height: P.h } })).newPage();
  page.on('pageerror', (e) => { report.errors.push(e.message); console.log('pageerror:', e.message); });
  // a seeded Math.random, so a run repeats
  await page.addInitScript((s) => { let x = s >>> 0 || 1; Math.random = () => { x ^= x << 13; x >>>= 0; x ^= x >> 17; x ^= x << 5; x >>>= 0; return x / 4294967296; }; }, seed);
  await page.goto(`${BASE}/viewer/wild.html?world=laurel_fork&hud=0&t=3&q=${P.q}&view=grimble`);
  await page.waitForFunction(() => window.__loaded && window.__grimble, null, { timeout: 300000 });

  // ---- the harness (in the page)
  await page.evaluate(async () => {
    window.__THREE = await import('three');
    const w = window.__wild, W = w.world, g = window.__grimble, pl = window.__player, cam = window.__three.camera;
    w.pause(true);
    const H = g.home;
    // the trunks, logs and boulders round its home, from the player's own collider list (not the Grimble's)
    const solids = pl.boxes.filter((c) => c.fixed && Math.abs((c.min.x + c.max.x) / 2 - H.x) < 170 && Math.abs((c.min.z + c.max.z) / 2 - H.y) < 170)
      .filter((c) => { const gy = W.heightAt((c.min.x + c.max.x) / 2, (c.min.z + c.max.z) / 2); return c.max.y - gy > 0.6 && c.min.y - gy < 3.5; });
    const kd = { n: 0 }, orig = pl.knockDown?.bind(pl);
    pl.knockDown = (...a) => { kd.n++; return orig?.(...a); };
    const R = { frames: 0, maxPen: 0, penFrames: 0, minD: 1e9, insideBox: 0, followD: [], states: {}, updMs: 0, visFrames: 0 };
    let t = 0;
    const footR = g.o.footR, dt = 1 / 60;
    const eye = () => new THREE_V(pl.pos.x, pl.pos.y + pl.eye, pl.pos.z);
    function THREE_V(x, y, z) { return cam.position.clone().set(x, y, z); }
    const chest = () => cam.position.clone().set(g.pos.x, g.groundY + 4.2, g.pos.y);
    let look = null;      // a point to look at (camera), else along the walk
    function frame(input, toward) {
      // the view: toward the walk target (movement follows the camera), or at `look`
      cam.position.set(pl.pos.x, pl.pos.y + pl.eye, pl.pos.z);
      if (toward) cam.lookAt(toward.x, pl.pos.y + pl.eye, toward.y);
      pl.update(dt, input);
      cam.position.set(pl.pos.x, pl.pos.y + pl.eye, pl.pos.z);
      if (look) cam.lookAt(look === 'g' ? chest() : look);
      cam.updateMatrixWorld();
      const t0 = performance.now();
      g.update(dt, cam);
      R.updMs += performance.now() - t0;
      t += dt; R.frames++;
      R.states[g.state] = (R.states[g.state] || 0) + 1;
      if (g.root.visible) R.visFrames++;
      // its footprint vs the trunks (independent of its own push-out)
      for (const c of solids) {
        if (g.pos.x < c.min.x - footR || g.pos.x > c.max.x + footR || g.pos.y < c.min.z - footR || g.pos.y > c.max.z + footR) continue;
        const qx = Math.max(c.min.x, Math.min(g.pos.x, c.max.x)), qz = Math.max(c.min.z, Math.min(g.pos.y, c.max.z));
        const pen = footR - Math.hypot(g.pos.x - qx, g.pos.y - qz);
        if (pen > 0.03) { R.penFrames++; if (pen > R.maxPen) { R.maxPen = pen; R.penAt = [+g.pos.x.toFixed(2), +g.pos.y.toFixed(2)]; } }
      }
      const d = Math.hypot(pl.pos.x - g.pos.x, pl.pos.z - g.pos.y);
      R.minD = Math.min(R.minD, d);
      if (pl.boxAt(pl.pos).intersectsBox(g.box)) R.insideBox++;
      if (g.state === 'follow' && R.phase === 'away') R.followD.push(d);
    }
    // walk the player along a path (the Grimble's grid, else straight), until(fn) or maxT
    function walkTo(goal, { run = false, crouch = false, until = null, maxT = 120, stopAt = 1.5 } = {}) {
      const G = { x: goal[0], y: goal[1] };
      let route = g.nav.path(new g.pos.constructor(pl.pos.x, pl.pos.z), new g.pos.constructor(G.x, G.y));
      route = route && route.length ? route.slice(1).map((p) => ({ x: p.x, y: p.y })) : [G];
      route.push(G);
      let i = 0, t0 = t, stuckT = t, best = 1e9, side = 0, checkT = t;
      while (t - t0 < maxT) {
        if (until && until()) return 'until';
        while (i < route.length - 1 && Math.hypot(route[i].x - pl.pos.x, route[i].y - pl.pos.z) < 1.5) i++;
        const tgt = route[i], dd = Math.hypot(G.x - pl.pos.x, G.y - pl.pos.z);
        if (dd < stopAt) return 'there';
        if (dd < best - 0.3) { best = dd; stuckT = t; }
        // (stuck on a trunk, a log or a step: crouch (the propped ghost log on the trail), then sidestep and hop)
        if (t - stuckT > 1.5) { side = (side + 1) % 3; stuckT = t; }
        frame({ forward: true, run, crouch: crouch || side === 1, right: side === 2 && Math.floor(t * 2) % 2 === 0, jump: side === 2 && Math.floor(t * 3) % 3 === 0 }, tgt);
      }
      return 'timeout';
    }
    function wait(secs, { until = null, crouch = false } = {}) {
      const t0 = t;
      while (t - t0 < secs) { if (until && until()) return 'until'; frame({ crouch }, null); }
      return 'time';
    }
    // a route's points from index a toward b (route A: the creek trail)
    function trail(name, a, b, opts) {
      const rt = W.routes[name], step = a < b ? 1 : -1;
      for (let k = a; k !== b; k += step * 3) {
        const r = walkTo(rt[k], { ...opts, stopAt: 2.5, maxT: 30 });
        if (r === 'until') return 'until';
        if (opts.maxT && opts.t0 != null && t - opts.t0 > opts.maxT) return 'timeout';
      }
      return 'end';
    }
    // the nearest route A point to its home
    const A = W.routes.A;
    let ai = 0, ad = 1e9;
    A.forEach((p, k) => { const d = Math.hypot(p[0] - H.x, p[1] - H.y); if (d < ad) { ad = d; ai = k; } });
    // a photo: the eye looks at it, one frame drawn
    function photo() {
      cam.position.set(pl.pos.x, pl.pos.y + pl.eye, pl.pos.z);
      cam.lookAt(chest()); cam.updateMatrixWorld();
      g.update(1e-4, cam);
      w.pause(true);
      return { t: +t.toFixed(1), d: +Math.hypot(pl.pos.x - g.pos.x, pl.pos.z - g.pos.y).toFixed(1), state: g.state, visible: g.root.visible,
        player: [+pl.pos.x.toFixed(1), +pl.pos.z.toFixed(1)], grimble: [+g.pos.x.toFixed(1), +g.pos.y.toFixed(1)] };
    }
    const ev = (name, since = 0) => g.log.find((e) => e.ev === name && e.t >= since);
    // how much of it shows from the eye: pixels that change when it's hidden (a 320 x 180 render,
    // the forest, shrubs and ground in front of it included)
    const renderer = window.__three.renderer, scene = window.__three.scene;
    let target = null, bufA = null, bufB = null;
    function visPx(from = null) {
      const THREE = window.__THREE;
      if (!target) { target = new THREE.WebGLRenderTarget(320, 180); bufA = new Uint8Array(320 * 180 * 4); bufB = new Uint8Array(320 * 180 * 4); }
      const p0 = cam.position.clone(), q0 = cam.quaternion.clone();
      if (from) cam.position.copy(from);
      cam.lookAt(chest()); cam.updateMatrixWorld();
      g.update(1e-4, cam);
      const vis = g.root.visible;
      w.cull();
      renderer.setRenderTarget(target);
      g.root.visible = true; renderer.render(scene, cam); renderer.readRenderTargetPixels(target, 0, 0, 320, 180, bufA);
      g.root.visible = false; renderer.render(scene, cam); renderer.readRenderTargetPixels(target, 0, 0, 320, 180, bufB);
      renderer.setRenderTarget(null);
      g.root.visible = vis;
      let n = 0;
      for (let i = 0; i < bufA.length; i += 4) if (Math.abs(bufA[i] - bufB[i]) + Math.abs(bufA[i + 1] - bufB[i + 1]) + Math.abs(bufA[i + 2] - bufB[i + 2]) > 12) n++;
      if (from) cam.position.copy(p0);
      cam.quaternion.copy(q0); cam.updateMatrixWorld();
      return n;
    }
    // the best place to stand within r m for a photo of it (where the shrubs and trunks don't hide it)
    function bestEye(r = 3) {
      let best = { n: visPx(), x: pl.pos.x, z: pl.pos.z };
      for (let a = 0; a < 8; a++) for (const rr of [r * 0.5, r]) {
        const x = pl.pos.x + Math.cos(a * Math.PI / 4) * rr, z = pl.pos.z + Math.sin(a * Math.PI / 4) * rr;
        const y = W.heightAt(x, z);
        if (pl.overlapping && pl.overlapping(new pl.pos.constructor(x, y, z)).length) continue;
        const n = visPx(cam.position.clone().set(x, y + pl.eye, z));
        if (n > best.n * 1.15) best = { n, x, z };
      }
      pl.pos.set(best.x, W.heightAt(best.x, best.z), best.z); pl.vel.set(0, 0, 0);
      return best.n;
    }
    window.__T = { R, kd, g, pl, W, H, ai, frame, walkTo, wait, trail, photo, ev, visPx, bestEye, get t() { return t; }, set look(v) { look = v; }, set phase(v) { R.phase = v; }, solids: solids.length };
  });

  const shot = async (name, meta) => {
    const file = path.join(out, `${name}.png`);
    await page.screenshot({ path: file });
    report.shots.push({ name, file, ...meta });
    console.log(`photo ${name}: ${JSON.stringify(meta)}`);
  };
  const ev = (fn, arg) => page.evaluate(fn, arg);

  // ---- 1. from the trail toward its home: first sight, notice, wave
  const p1 = await ev(() => {
    const T = window.__T, g = T.g, pl = T.pl, W = T.W;
    const a = W.routes.A[T.ai];
    pl.pos.set(a[0], W.heightAt(a[0], a[1]), a[1]); pl.vel.set(0, 0, 0);
    g.aware = 0;
    T.wait(1);
    // walk east toward the home (16 m short of it), until its head first sees the player's eye
    // (its eye on you, and enough of it on screen to see: checked every 0.25 s)
    let next = 0, px = 0;
    const r = T.walkTo([T.H.x - 16, T.H.y], { maxT: 120, until: () => { if (T.t < next) return false; next = T.t + 0.25; px = T.visPx(); return px >= 25 || !!T.ev('notice'); } });
    return { start: a, r, t: T.t, d: +g.playerDist.toFixed(1), visPx: px, grimbleSees: g.seen };
  });
  report.phases.approach = p1;
  await shot('1_first_sight', await ev(() => window.__T.photo()));
  const p1b = await ev(() => {
    const T = window.__T, g = T.g;
    const t0 = T.t;
    // on toward it (walking, looking where it goes) until it notices
    let r = T.ev('notice') ? 'already' : T.walkTo([T.H.x - 16, T.H.y], { until: () => !!T.ev('notice'), maxT: 90 });
    if (!T.ev('notice')) r = T.wait(20, { until: () => !!T.ev('notice') });
    // (closer while it turns: a curious player walks up, to ~20 m)
    T.look = 'g';
    T.walkTo([g.pos.x, g.pos.y], { stopAt: 20, maxT: 10, until: () => g.state === 'notice' && g.t > 1.2 });
    return { r, noticeAt: T.ev('notice'), d: +g.playerDist.toFixed(1), state: g.state };
  });
  report.phases.notice = p1b;
  await shot('2_notice', await ev(() => ({ ...window.__T.photo(), visPx: window.__T.bestEye(3) })));
  const p1c = await ev(() => {
    const T = window.__T, g = T.g;
    let r = T.walkTo([g.pos.x, g.pos.y], { stopAt: 18, maxT: 10, until: () => g.state === 'wave' && g.t > 1.1 });
    if (r !== 'until') r = T.wait(12, { until: () => g.state === 'wave' && g.t > 1.1 });
    return { r, wave: T.ev('wave'), tilt: +g.tilt.toFixed(2) };
  });
  report.phases.wave = p1c;
  await shot('3_wave', await ev(() => { const T = window.__T, n = T.bestEye(2); return { ...T.photo(), visPx: n }; }));
  await ev(() => window.__T.wait(8, { until: () => window.__T.g.state === 'follow' }));

  // ---- 2. away along the trail toward the gate: it follows, then says goodbye and goes home
  const p2 = await ev(() => {
    const T = window.__T, g = T.g;
    T.look = null;
    T.phase = 'away';
    const t0 = T.t;
    const followStart = T.ev('follow');
    // back to the trail (it follows), looking back at it now and then
    for (let k = 0; k < 4; k++) {
      T.look = null; T.walkTo(T.W.routes.A[T.ai], { stopAt: 3, maxT: 7 });
      T.look = 'g'; T.wait(2.5);
    }
    return { followStart, t: T.t, d: g.playerDist, state: g.state };
  });
  report.phases.follow = p2;
  await shot('4_following', await ev(() => { const T = window.__T; return { ...T.photo(), visPx: T.visPx() }; }));
  const p2b = await ev(() => {
    const T = window.__T, g = T.g;
    const t0 = T.t;
    // on along the trail toward the gate, walking 8 s and stopping 3 s to look back, until it says goodbye
    let r = 'timeout', k = Math.max(0, T.ai - 3);
    const done = () => ['farewell', 'return'].includes(g.state);
    while (T.t - t0 < 200 && !done() && k > 0) {
      T.look = null;
      const t1 = T.t;
      while (T.t - t1 < 8 && !done() && k > 0) { T.walkTo(T.W.routes.A[k], { stopAt: 2.5, maxT: 8 - (T.t - t1), until: done }); if (Math.hypot(T.W.routes.A[k][0] - T.pl.pos.x, T.W.routes.A[k][1] - T.pl.pos.z) < 3) k = Math.max(0, k - 3); }
      if (done()) { r = 'until'; break; }
      T.look = 'g'; if (T.wait(3, { until: done }) === 'until') { r = 'until'; break; }
    }
    T.phase = null;
    return { r, farewell: T.ev('farewell'), t: T.t, d: +g.playerDist.toFixed(1), player: [+T.pl.pos.x.toFixed(1), +T.pl.pos.z.toFixed(1)], fromHome: +Math.hypot(g.pos.x - T.H.x, g.pos.y - T.H.y).toFixed(1) };
  });
  report.phases.farewell = p2b;
  if (p2b.farewell) {
    await ev(() => { const T = window.__T; T.look = 'g'; T.wait(1.2); });
    await shot('5_goodbye', await ev(() => { const T = window.__T; return { ...T.photo(), visPx: T.visPx() }; }));
  }
  const p2c = await ev(() => {
    const T = window.__T, g = T.g;
    T.look = null;
    const t0 = T.t;
    const r = T.wait(240, { until: () => T.ev('home', t0 - 30) && g.state !== 'return' });
    const dHome = Math.hypot(g.pos.x - T.H.x, g.pos.y - T.H.y);
    return { r, home: T.ev('home', t0 - 300), dHome: +dHome.toFixed(1), t: T.t };
  });
  report.phases.return = p2c;

  // ---- 3. at home: the player comes back over quietly and watches (crouched, ~24 m off)
  const p3 = await ev(() => {
    const T = window.__T, g = T.g, pl = T.pl, W = T.W;
    // let it settle into its own things first (it ignores the far player)
    T.wait(25, { until: () => ['pat', 'rest'].includes(g.state) || (g.state === 'look' && g.t > 2) });
    // a spot ~24 m from it, on its grid, that it can be seen from
    let spot = null, best = -1;
    for (let a = 0; a < 16; a++) for (const rr of [18, 24]) {
      const ang = g.heading + (a % 2 ? 1 : -1) * Math.ceil(a / 2) * 0.3;
      const x = g.pos.x + Math.sin(ang) * rr, z = g.pos.y + Math.cos(ang) * rr;
      if (!g.nav.walkable(g.nav.idx(x, z))) continue;
      const n = T.visPx(T.pl.pos.clone().set(x, W.heightAt(x, z) + 1.1, z));
      if (n > best) { best = n; spot = [x, z]; }
    }
    pl.pos.set(spot[0], W.heightAt(spot[0], spot[1]), spot[1]); pl.vel.set(0, 0, 0); pl.crouching = true; pl.height = 1.1;
    T.look = 'g';
    g.aware = 0;
    T.wait(0.2, { crouch: true });
    return { spot, visPx: best, state: g.state, t: T.t };
  });
  report.phases.home = p3;
  await shot('6_at_home', await ev(() => window.__T.photo()));
  // then it goes back to its own things (it won't follow again for a while): the wonder (it pats
  // a big poplar and leaves come down) and its rest, each photographed if it happens within a while
  for (const [name, want] of [['7_pat_leaves', 'pat'], ['8_rest', 'rest']]) {
    const r = await ev((want) => {
      const T = window.__T, g = T.g;
      const t0 = T.t;
      const ok = want === 'pat' ? () => g.state === 'pat' && g.patting && g.t > 2.2 && g.leaves.alive > 0
        : () => g.state === 'rest' && g.current === g.actions.CrawlIdle && g.t > 3;
      const r = T.wait(300, { crouch: true, until: ok });
      return { r, waited: +(T.t - t0).toFixed(1), leaves: g.leaves.alive, state: g.state };
    }, want);
    report.phases[want] = r;
    if (r.r === 'until') await shot(name, await ev(() => { const T = window.__T, n = T.bestEye(4); return { ...T.photo(), visPx: n, leaves: T.g.leaves.alive }; }));
  }

  // ---- 4. straight at it: it makes room; the player never ends up inside it
  const p4 = await ev(() => {
    const T = window.__T, g = T.g, pl = T.pl;
    T.look = null;
    pl.crouching = false; pl.height = 1.8;
    const t0 = T.t, minD0 = T.R.minD;
    T.R.minD = 1e9;
    let r = 'x';
    for (let k = 0; k < 6 && !T.ev('aside', t0); k++) r = T.walkTo([g.pos.x, g.pos.y], { stopAt: 0.2, maxT: 6, until: () => g.state === 'aside' });
    T.look = 'g';
    T.wait(1.5);
    return { r, aside: T.ev('aside', t0), minD: +T.R.minD.toFixed(2), state: g.state, t: T.t, minDBefore: +minD0.toFixed(2) };
  });
  report.phases.aside = p4;
  await ev(() => { const T = window.__T; T.look = 'g'; T.wait(8, { until: () => T.g.state !== 'aside' }); T.wait(0.8); });
  await shot('9_step_aside', await ev(() => { const T = window.__T; return { ...T.photo(), visPx: T.visPx() }; }));
  const p4b = await ev(() => {
    const T = window.__T, g = T.g;
    // keep pressing into it for 8 s (walking at its position)
    const t0 = T.t;
    T.look = null;
    let n = 0;
    while (T.t - t0 < 8) { T.walkTo([g.pos.x, g.pos.y], { stopAt: 0.1, maxT: 1 }); n++; }
    return { minD: +T.R.minD.toFixed(2), asides: T.g.log.filter((e) => e.ev === 'aside' && e.t >= t0).length };
  });
  report.phases.press = p4b;

  // ---- the summary
  const S = await ev(() => {
    const T = window.__T, R = T.R, g = T.g;
    const fd = R.followD;
    return {
      simS: +T.t.toFixed(1), frames: R.frames, solids: T.solids,
      footprint: { maxPen: +R.maxPen.toFixed(3), penFrames: R.penFrames, at: R.penAt || null, grimbleOwn: g.stats },
      playerInsideItFrames: R.insideBox, minPlayerDist: +R.minD.toFixed(2),
      follow: fd.length ? { s: +(fd.length / 60).toFixed(1), min: +Math.min(...fd).toFixed(1), mean: +(fd.reduce((a, b) => a + b, 0) / fd.length).toFixed(1), max: +Math.max(...fd).toFixed(1) } : null,
      knockDowns: T.kd.n, combat: !!window.__combat, states: Object.fromEntries(Object.entries(R.states).map(([k, v]) => [k, +(v / 60).toFixed(1)])),
      updMsPerFrame: +(R.updMs / R.frames).toFixed(3),
      log: g.log.map((e) => `${e.t} ${e.ev}${e.to ? ' ' + JSON.stringify(e.to) : ''}${e.why ? ' ' + e.why : ''}${e.d ? ' d=' + e.d : ''}${e.what ? ' ' + e.what : ''} @${e.at.join(',')}`),
    };
  });
  report.summary = S;
  // draw calls with it in view (the following photo's frame)
  report.drawCalls = await ev(() => { const r = window.__three.renderer; window.__wild.pause(true); return r.info.render.calls; });
} finally {
  await b.close();
  stop();
  release();
}

const S = report.summary || {};
const ph = report.phases;
const checks = {
  first_sight: !!ph.approach && ph.approach.r === 'until',
  notice: !!ph.notice?.noticeAt,
  wave: !!ph.wave?.wave,
  follow: !!S.follow && S.follow.s > 10 && S.follow.min >= 8,
  goodbye_and_home: !!ph.farewell?.farewell && !!ph.return?.home && ph.return.dHome < 6,
  steps_aside: !!ph.aside?.aside,
  never_inside_player: S.playerInsideItFrames === 0 && S.minPlayerDist >= 1.2,
  no_trunk_clipping: S.footprint?.maxPen <= 0.05,
  no_damage: S.knockDowns === 0,
  no_page_errors: report.errors.length === 0,
};
report.checks = checks;
report.pass = Object.values(checks).every(Boolean);
fs.writeFileSync(path.join(out, 'report.json'), JSON.stringify(report, null, 1));
const shots = report.shots.map((s) => s.file);
if (shots.length) {
  try { execFileSync('node', [path.join(root, 'viewer/tools/grid.mjs'), path.join(out, 'contact.png'), '2', ...shots], { stdio: 'ignore' }); } catch (e) { console.log('contact sheet:', e.message); }
}
console.log(JSON.stringify({ phases: ph, summary: { ...S, log: undefined } }, null, 1));
console.log((S.log || []).join('\n'));
for (const [k, v] of Object.entries(checks)) console.log(`${v ? 'PASS' : 'FAIL'} ${k}`);
console.log(`${report.pass ? 'PASS' : 'FAIL'}: ${out}`);
process.exit(report.pass ? 0 : 1);
