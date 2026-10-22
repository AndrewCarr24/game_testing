// Playtest of the Grimble hunt: it breaks in at once and a scripted player flees round the main
// spaces (great room, the gallery ring round the courtyard, kitchen, entry), staying a few metres
// ahead (running when it's close, waiting when it falls behind). Every frame it logs the
// Grimble's state; every `shot` seconds the game pauses and takes photos (the player looking
// back at it, and a high view from near the ceiling behind it). It measures:
//   - in walls: skinned vertices of its body (every 7th) inside a wall box or outside every
//     main space (= through a wall into a side room / outdoors), per probe (2 a second)
//   - futile: seconds it plays a crawl (it's trying to move) but its head gains < 0.5 m in 3 s,
//     and how much it turned meanwhile
//   - squeeze: seconds with the old code's wall push switched off (gone in the chain version)
// Usage: node viewer/tools/hunt_play.mjs [out-dir=build/hunt] [seconds=120] [route=ring]
//   routes: ring (round the galleries), kitchen (great room -> gallery_n -> kitchen -> back),
//           entry (great room -> gallery_s -> entry and back)
import { chromium } from 'playwright-core';
import fs from 'fs';
const [out = 'build/hunt', secs = '120', route = 'ring', shotEvery = '4'] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const ROUTES = {
  // world glTF (x, z); the galleries' centre lines are x = +-11.75, z = +-8.75
  ring: [[-18, 3.5], [-11.75, 3.5], [-11.75, 8.75], [11.75, 8.75], [11.75, -8.75], [-11.75, -8.75], [-11.75, -3.5], [-16, -3.5], [-16, 3.5]],
  // a lap, then into the mudroom (a side room: out of its reach; teleported past the door) to hide,
  // so it searches and prowls
  // up to the upper gallery over the great room once it's in (it rears up at the balustrade)
  upper: [[-18, 3.5, 'wait', 9], [-11.6, 1, 'tp', 4.6], [-11.6, 1, 'hold']],
  // a lap, then gone (upstairs in the office, nowhere near a void): it searches, then prowls
  lost: [[-18, 3.5], [-11.75, 3.5], [-11.75, 8.75], [0, 8.75], [7, -15, 'tp', 4.6], [7, -15, 'hold']],
  hide: [[-18, 3.5], [-11.75, 3.5], [-11.75, 8.75], [11.75, 8.75], [11.75, -3.5], [18, -5, 'tp'], [18, -5, 'hold']],
  kitchen: [[-18, -3.5], [-11.75, -3.5], [-11.75, -8.75], [0, -8.75], [0, -15], [5, -15], [0, -15], [0, -8.75], [-11.75, -8.75], [-11.75, -3.5], [-18, -3.5]],
  entry: [[-18, 3.5], [-11.75, 3.5], [-11.75, 8.75], [4.75, 8.75], [4.75, 15], [-4, 16], [4.75, 15], [4.75, 8.75], [-11.75, 8.75], [-11.75, 3.5], [-18, 3.5]],
  courtyard: [[-18, 3.5], [-11.75, 3.5], [-11.75, 8.75], [0, 8.75], [0, 3], [6, 0], [0, -3], [-6, 0], [0, 3], [0, 8.75], [-11.75, 8.75], [-11.75, 3.5], [-18, 3.5]],
};
fs.mkdirSync('build/locks', { recursive: true });
let slot = null;
while (slot === null) {
  for (let i = 0; i < 3 && slot === null; i++) { try { fs.mkdirSync(`build/locks/browser_${i}`); slot = i; } catch {} }
  if (slot === null) await new Promise((ok) => setTimeout(ok, 3000));
}
process.on('exit', () => { try { fs.rmdirSync(`build/locks/browser_${slot}`); } catch {} });

const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 960, height: 600 } });
p.on('pageerror', (e) => console.log('pageerror:', e.message));
p.on('console', (m) => { if (m.type() === 'error') console.log('console:', m.text()); });
await p.goto(`${process.env.GT_BASE || 'http://localhost:8765'}/viewer/index.html?level=mansion&grimble=house&gdelay=0&hunt=now&pos=-18,1.65,3.5&look=-26,1.5,0${process.env.QS || ''}`);
await p.waitForFunction(() => window.__loaded && window.__grimble && window.__hunt, null, { timeout: 120000 });

await p.evaluate((route) => {
  const g = window.__grimble, h = window.__hunt, pl = window.__player, cam = window.__camera;
  const THREE = { Vector3: g.root.position.constructor, Ray: h._ray.constructor };
  document.querySelectorAll('#hud,#stats').forEach((e) => (e.style.display = 'none'));
  const pt = window.__pt = { paused: false, log: [], route, wp: 0, photo: null, t: 0, events: [] };
  // straight to the glass: skip the walk-in (the knock-wave-stare round still plays, then Smash)
  g.state = 'walk'; g.root.visible = true; g.s = g.total; g.place();
  // its body: the skinned meshes (not the staff once it's dropped), every 7th vertex
  const meshes = [];
  g.root.traverse((o) => { if (o.isSkinnedMesh) meshes.push(o); });
  const v = new THREE.Vector3();
  const rooms = ['great_room', 'entry', 'gallery_s', 'gallery_n', 'gallery_w', 'gallery_e', 'courtyard', 'kitchen', 'dining']
    .map((r) => window.__level?.rooms?.[r]?.rect).filter(Boolean);
  const inMain = (x, z) => rooms.some((r) => x >= r[0] && x <= r[2] && z >= r[1] && z <= r[3]) || (x < -25.9 && Math.abs(z) < 3);
  const probe = () => {
    let n = 0, worst = 0, where = null, total = 0, out = 0;
    g.root.updateMatrixWorld(true);
    for (const m of meshes) {
      if (!m.visible) continue;
      const pos = m.geometry.attributes.position;
      for (let i = 0; i < pos.count; i += 7) {
        v.fromBufferAttribute(pos, i); m.applyBoneTransform(i, v); v.applyMatrix4(m.matrixWorld);
        total++;
        if (v.y < 0.05) continue;
        if (!inMain(v.x, v.z)) { out++; n++; if (!where) where = [+v.x.toFixed(2), +v.y.toFixed(2), +v.z.toFixed(2), m.name, 'outside']; continue; }
        for (const c of h.solid) {
          if (v.x <= c.min.x || v.x >= c.max.x || v.z <= c.min.z || v.z >= c.max.z || v.y <= c.min.y || v.y >= c.max.y) continue;
          // depth: how far past the wall's nearer face (thin boxes: the half thickness at most)
          const d = Math.min(v.x - c.min.x, c.max.x - v.x, v.z - c.min.z, c.max.z - v.z);
          // a point inside a wall box counts as "through" by its distance to the box's nearest face
          // plus the wall thickness it crossed: a lining 0.15 m thick fully crossed = poking out the far side
          n++;
          if (d > worst) { worst = d; where = [+v.x.toFixed(2), +v.y.toFixed(2), +v.z.toFixed(2), m.name]; }
          break;
        }
      }
    }
    return { n, total, worst, where, out };
  };
  // is a body point past a wall into the next room? sample: any vertex whose straight line from the
  // root crosses a wall box (it went through it)
  const through = () => {
    let n = 0, far = 0, at = null;
    const o = new THREE.Vector3(g.root.position.x, 1.0, g.root.position.z);
    const ray = new THREE.Ray(), hit = new THREE.Vector3();
    for (const m of meshes) {
      if (!m.visible) continue;
      const pos = m.geometry.attributes.position;
      for (let i = 0; i < pos.count; i += 23) {
        v.fromBufferAttribute(pos, i); m.applyBoneTransform(i, v); v.applyMatrix4(m.matrixWorld);
        if (v.y < 0.1 || v.y > 4.0) continue;
        const a = new THREE.Vector3(v.x, Math.min(v.y, 2.5), v.z);
        const d = a.distanceTo(o);
        ray.set(o, a.clone().sub(o).normalize());
        for (const c of h.solid) {
          if (c.containsPoint(o)) continue;
          if (ray.intersectBox(c, hit) && hit.distanceTo(o) < d - 0.02) {
            const past = d - hit.distanceTo(o);
            n++; if (past > far) { far = past; at = [+v.x.toFixed(2), +v.y.toFixed(2), +v.z.toFixed(2), m.name]; }
            break;
          }
        }
      }
    }
    return { n, far, at };
  };
  pt.probe = probe; pt.through = through;
  // where the staff is: its two ends (along the hindquarters' direction) and the hand
  pt.staff = () => {
    const m = meshes.find((o) => /Staff/.test(o.name)); if (!m || !h.chain) return null;
    const hr = h.rearYaw(), fx = Math.sin(hr), fz = Math.cos(hr), P = m.geometry.attributes.position;
    let lo = [1e9], hi = [-1e9];
    for (let i = 0; i < P.count; i += 3) { v.fromBufferAttribute(P, i); m.applyBoneTransform(i, v); v.applyMatrix4(m.matrixWorld);
      const d = v.x * fx + v.z * fz; if (d < lo[0]) lo = [d, +v.x.toFixed(2), +v.z.toFixed(2)]; if (d > hi[0]) hi = [d, +v.x.toFixed(2), +v.z.toFixed(2)]; }
    const gp = h.staffBone.getWorldPosition(v.clone());
    return { tail: lo.slice(1), front: hi.slice(1), grip: [+gp.x.toFixed(2), +gp.z.toFixed(2)], q: [+h.chain.q.x.toFixed(2), +h.chain.q.y.toFixed(2)], bend: +((h.frontYaw() - hr) * 57.3).toFixed(0), da: h.staffDa, hand: (() => { const p = h.hand.getWorldPosition(v.clone()); return [+p.x.toFixed(2), +p.z.toFixed(2)]; })(), tailI: h.staffTailI };
  };
  // the player: run the route, keep a few metres ahead
  const origP = pl.update.bind(pl);
  const fwd = new THREE.Vector3();
  pl.update = (dt, input) => {
    if (pt.paused) { if (pt.photo) { cam.position.set(...pt.photo.pos); cam.up.set(0, 1, 0); cam.lookAt(...pt.photo.at); } return; }
    const inside = g.state === 'inside' && !['smash'].includes(h.state);
    const R = pt.route;
    if (R[R.length - 1][2] === 'hold') pt.wp = Math.min(pt.wp, R.length - 1);
    const wp = R[pt.wp % R.length];
    if (wp[2] === 'tp') { pl.pos.set(wp[0], wp[3] ?? 0, wp[1]); pt.wp++; }
    // 'wait': stand there until it's within wp[3] m, then on
    if (wp[2] === 'wait' && Math.hypot(wp[0] - pl.pos.x, wp[1] - pl.pos.z) < 0.6 && Math.hypot(g.root.position.x - pl.pos.x, g.root.position.z - pl.pos.z) < wp[3]) pt.wp++;
    const hold = wp[2] === 'hold' || (wp[2] === 'wait' && Math.hypot(wp[0] - pl.pos.x, wp[1] - pl.pos.z) < 0.6);
    const dx = wp[0] - pl.pos.x, dz = wp[1] - pl.pos.z;
    if (!hold && Math.hypot(dx, dz) < 0.6) pt.wp++;
    const gd = Math.hypot(g.root.position.x - pl.pos.x, g.root.position.z - pl.pos.z);
    // before it's in: wait in the great room watching it; then flee, running when it's near
    const go = inside && gd < 14 && !hold;
    // the scripted player caught on furniture (1.5 s of trying without getting anywhere, not
    // counting time knocked down): on to the next waypoint
    if (pt.lastP && !pl.isDown && go) pt.stuckFor = (pt.stuckFor || 0) + (Math.hypot(pl.pos.x - pt.lastP[0], pl.pos.z - pt.lastP[1]) < 0.02 ? dt : -dt);
    pt.stuckFor = Math.max(0, pt.stuckFor || 0);
    if (pt.stuckFor > 1.5 && !hold) { pt.wp++; pt.stuckFor = 0; }
    pt.lastP = [pl.pos.x, pl.pos.z];
    const run = gd < 9;
    if (!go) cam.lookAt(g.root.position.x, 1.8, g.root.position.z);
    else cam.lookAt(pl.pos.x + dx, pl.pos.y + 1.6, pl.pos.z + dz);
    origP(dt, { forward: go, run, back: false, left: false, right: false, jump: false, crouch: false });
  };
  const origG = g.update.bind(g);
  let acc = 0;
  g.update = (dt, player) => {
    if (pt.paused) return;
    origG(dt, player);
    pt.t += dt; acc += dt;
    if (g.state !== 'inside') return;
    if (acc >= 0.1) {
      acc = 0;
      const pr = pt.t % 0.5 < 0.1 ? probe() : null;
      const hd = h.chain ? h.chain.hd : g.root.position;
      pt.log.push({ t: +pt.t.toFixed(2), x: +g.root.position.x.toFixed(2), z: +g.root.position.z.toFixed(2), hd: +g.heading.toFixed(3),
        hx: +(hd.x).toFixed(2), hz: +(h.chain ? hd.y : hd.z).toFixed(2),
        st: h.state, path: h.path ? h.path.length : 0, seenAgo: +(h.time - h.seenAt).toFixed(1), cam: [+cam.position.x.toFixed(2), +cam.position.y.toFixed(2), +cam.position.z.toFixed(2)], sq: h.time < (h.squeezeUntil ?? 0) ? 1 : 0,
        px: +pl.pos.x.toFixed(2), pz: +pl.pos.z.toFixed(2), py: +pl.pos.y.toFixed(2), down: pl.isDown ? 1 : 0,
        anim: g.current?.getClip().name, pen: pr });
    }
  };
}, ROUTES[route]);

const t0 = Date.now();
let lastShot = 0, k = 0;
while ((Date.now() - t0) / 1000 < +secs) {
  await p.waitForTimeout(250);
  const st = await p.evaluate(() => ({ t: window.__pt.t, inside: window.__grimble.state === 'inside', hs: window.__hunt.state }));
  if (st.inside && st.hs !== 'smash' && st.t - lastShot >= +shotEvery) {
    lastShot = st.t;
    const views = await p.evaluate(() => {
      const g = window.__grimble, pl = window.__player, pt = window.__pt;
      pt.paused = true;
      const gx = g.root.position.x, gz = g.root.position.z, hd = g.heading;
      const eye = [pl.pos.x, pl.pos.y + 1.65, pl.pos.z];
      // the high view: behind it near the ceiling, on the nav grid (the corridor's middle), looking at its middle
      const h = window.__hunt, by = h.bodyYaw ?? hd;
      let bx = gx - Math.sin(by) * 4.5, bz = gz - Math.cos(by) * 4.5;
      const k = h.nav.nearest(bx, bz, 6); if (k >= 0) { const c = h.nav.centre(k); bx = c.x; bz = c.y; }
      return [
        // the player looking at its head (wherever the animation has it: crawling or reared up)
        { name: 'player', pos: eye, at: (() => { const hb = g.root.getObjectByName('Head'); const v = hb.getWorldPosition(g.root.position.clone()); return [v.x, v.y - 0.6, v.z]; })() },
        { name: 'high', pos: [bx, 3.9, bz], at: [gx + Math.sin(hd) * 1.5, 0.6, gz + Math.cos(hd) * 1.5] },
      ];
    });
    const pen = await p.evaluate(() => ({ ...window.__pt.probe(), thr: window.__pt.through(), staff: window.__pt.staff() }));
    if (pen.n) console.log('   staff', JSON.stringify(pen.staff));
    for (const vw of views) {
      await p.evaluate((vw) => { window.__pt.photo = vw; }, vw);
      await p.waitForTimeout(350);
      await p.screenshot({ path: `${out}/${String(k).padStart(3, '0')}_${vw.name}.png` });
    }
    const info = await p.evaluate(() => { const h = window.__hunt, g = window.__grimble; return { t: window.__pt.t.toFixed(1), st: h.state, x: g.root.position.x.toFixed(2), z: g.root.position.z.toFixed(2) }; });
    console.log(`shot ${k} t=${info.t} ${info.st} at (${info.x}, ${info.z}) pen ${pen.n} pts worst ${pen.worst.toFixed(2)} m ${JSON.stringify(pen.where)} (${pen.out} past a wall)`);
    k++;
    // (the camera back at the player's eye before the Grimble's next look: it reads the camera)
    await p.evaluate(() => { const pl = window.__player; window.__camera.position.set(pl.pos.x, pl.pos.y + 1.65, pl.pos.z); window.__pt.photo = null; window.__pt.paused = false; });
  }
}
const log = await p.evaluate(() => window.__pt.log);
fs.writeFileSync(`${out}/log.json`, JSON.stringify(log));
// summary: futile windows (playing a crawl, < 0.5 m progress of the head over 3 s) and turning in them
let stuck = 0, turn = 0, sq = 0, penFrames = 0, probes = 0, outFrames = 0, maxN = 0;
const stuckAt = [];
const hx = (l) => l.hx ?? l.x, hz = (l) => l.hz ?? l.z;
for (let i = 30; i < log.length; i++) {
  const a = log[i - 30], c = log[i];
  const trying = /^Crawl(Fast)?$/.test(c.anim) && !['smash', 'swipe', 'reachUp'].includes(c.st);
  if (trying && Math.hypot(hx(c) - hx(a), hz(c) - hz(a)) < 0.5) {
    stuck += 0.1;
    let d = c.hd - log[i - 1].hd; d = Math.atan2(Math.sin(d), Math.cos(d)); turn += Math.abs(d);
    if (!stuckAt.length || c.t - stuckAt[stuckAt.length - 1].t1 > 1) stuckAt.push({ t0: c.t, t1: c.t, x: c.x, z: c.z, st: c.st });
    else stuckAt[stuckAt.length - 1].t1 = c.t;
  }
  if (c.sq) sq += 0.1;
}
for (const l of log) if (l.pen) { probes++; if (l.pen.n) penFrames++; if (l.pen.out) outFrames++; maxN = Math.max(maxN, l.pen.n); }
const dur = log.length ? log[log.length - 1].t - log[0].t : 0;
const states = {};
for (const l of log) states[l.st] = (states[l.st] || 0) + 0.1;
const downs = log.filter((l, i) => l.down && !(log[i - 1]?.down)).length;
const stats = await p.evaluate(() => window.__hunt.stats || {});
console.log(`inside ${dur.toFixed(1)} s; states ${JSON.stringify(Object.fromEntries(Object.entries(states).map(([k, v]) => [k, +v.toFixed(1)])))}`);
console.log(`futile ${stuck.toFixed(1)} s (turned ${(turn * 180 / Math.PI).toFixed(0)} deg meanwhile), squeezing ${sq.toFixed(1)} s, knockdowns ${downs}, ${JSON.stringify(stats)}`);
console.log(`in walls: ${penFrames}/${probes} probes with body points in a wall or past one (${outFrames} past one), worst probe ${maxN} points`);
for (const s of stuckAt) if (s.t1 - s.t0 >= 0.5) console.log(`  futile ${s.t0}-${s.t1} s at (${s.x}, ${s.z}) ${s.st}`);
await Promise.race([b.close(), new Promise((ok) => setTimeout(ok, 5000))]);
process.exit(0);
