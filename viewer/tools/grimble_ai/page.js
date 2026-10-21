// In-page part of the Grimble AI suite (build/gt/suite.mjs). Fast-forward: K substeps of 1/60 s
// per real frame, the scripted player stepped in the same loop. One page load, many scenarios:
// window.__S.run(spec) resets both, runs the steps for spec.secs of game time and logs every 0.1 s.
() => {
  const g = window.__grimble, h = window.__hunt, pl = window.__player, cam = window.__camera, it = window.__interact;
  const V3 = g.root.position.constructor, V2 = h.pos2().constructor;
  document.querySelectorAll('#hud,#stats').forEach((e) => (e.style.display = 'none'));
  g.state = 'walk'; g.root.visible = true; g.s = g.total; g.place(); g.o.waveTime = 0.5; g.o.stare = [0.5, 0.5];
  const S = window.__S = { K: 6, sub: 1 / 60, spec: null, t: 0, log: [], events: [], done: true, paused: false, want: null, photoN: 0 };
  const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
  const doorItem = (x, z) => {
    let best = null, bd = 1e9;
    for (const i of it.items) {
      if (!i.collider || i.def.type !== 'rotate') continue;
      const c = i.root.getWorldPosition(new V3()); const d = Math.hypot(c.x - x, c.z - z);
      if (d < bd) { bd = d; best = i; }
    }
    return best;
  };
  S.door = (x, z, open) => { const d = doorItem(x, z); d.target = d.t = open ? 1 : 0; it.pose(d); };
  S.placeG = (x, z, yaw) => {
    g.root.position.set(x, 0, z); g.heading = yaw; g.root.rotation.y = yaw;
    h.startChain();
    if (h.reset) h.reset();
    h.set('prowl'); h.path = null; h.goal = null; h.idleFor = 0;
    h.lastSeen = null; h.seenAt = -1e9; h.noise = null; h.unstickUntil = 0;
    h.turnAt = null; h.stage = null; h.cantTurn = false; h._prog = null; h._turnTry = 0;
    h.hitAt = h.time;
    h.solveChain(); h.placeRoot();
  };
  S.placeP = (x, z, y = 0) => { pl.pos.set(x, y, z); pl.vel.set(0, 0, 0); pl.syncCamera(); };
  // hold it (idle) for s seconds where it is, memory wiped (a prowl pause)
  S.idleG = (s) => { if (h.hold) h.hold(s); else { h.set('prowl'); h.path = null; h.idleFor = s; } };
  // it has just seen the player at (x, z): chase
  S.sawP = () => {
    if (h.sawPlayer) h.sawPlayer(new V2(pl.pos.x, pl.pos.z), pl.pos.y);
    else { h.lastSeen = new V2(pl.pos.x, pl.pos.z); h.seenAt = h.time; h.state = 'chase'; }
  };
  S.mark = (label) => S.events.push({ t: +S.t.toFixed(2), label });
  const NO = { forward: false, back: false, left: false, right: false, jump: false, run: false, crouch: false };
  let si = 0, stepT = 0, crouch = false, look = 'grimble', wp = 0;
  const lookAtG = () => { const c = h.chain ? h.chain.hd : h.pos2(); cam.lookAt(c.x, pl.pos.y + 1.4, c.y); };
  const step = (dt) => {
    const steps = S.spec.steps;
    let input = { ...NO, crouch };
    for (let guard = 0; guard < 20 && si < steps.length; guard++) {
      const s = steps[si];
      const next = () => { si++; stepT = 0; wp = 0; if (s.label) S.mark(s.label); };
      if (s.go) {
        const R = Array.isArray(s.go[0]) ? s.go : [s.go];
        if (pl.isDown) { input = { ...NO }; break; }
        while (wp < R.length && Math.hypot(R[wp][0] - pl.pos.x, R[wp][1] - pl.pos.z) < 0.5) wp++;
        if (wp >= R.length) { next(); continue; }
        const [x, z] = R[wp];
        cam.lookAt(x, pl.pos.y + pl.eye, z);
        input = { ...NO, forward: true, run: s.mode === 'run', crouch: s.mode === 'crouch' || crouch };
        stepT += dt;
        if (s.timeout && stepT > s.timeout) { S.mark('go timeout ' + si); next(); continue; }
        break;
      }
      if (s.wait !== undefined) {
        stepT += dt;
        if (stepT >= s.wait) { next(); continue; }
        break;
      }
      if (s.until) {
        stepT += dt;
        if (s.until(h, pl, S) || stepT >= (s.timeout ?? 60)) { if (stepT >= (s.timeout ?? 60)) S.mark('until timeout ' + si); next(); continue; }
        break;
      }
      if (s.tp) { S.placeP(...s.tp); next(); continue; }
      if (s.door) { S.door(...s.door); next(); continue; }
      if (s.noise) { window.__noise.emit({ position: new V3(s.noise[0], 0.5, s.noise[1]), loudness: s.noise[2] ?? 1, source: 'test' }); S.mark(`noise ${s.noise}`); next(); continue; }
      if (s.crouch !== undefined) { crouch = s.crouch; next(); continue; }
      if (s.hidden !== undefined) { pl.hidden = s.hidden; next(); continue; }
      if (s.look !== undefined) { look = s.look; next(); continue; }
      if (s.fn) { s.fn(h, pl, S); next(); continue; }
      if (s.photo) { S.want = s.photo; S.paused = true; next(); return null; }
      next();
    }
    if (!input.forward) {
      if (look === 'grimble') lookAtG();
      else if (Array.isArray(look)) cam.lookAt(...look);
    }
    return input;
  };
  const origP = pl.update.bind(pl);
  pl.update = () => {};
  const fs = window.__footsteps, fsUpdate = fs ? fs.update.bind(fs) : null;
  if (fs) fs.update = () => {};
  const origG = g.update.bind(g);
  let acc = 0, lastYaw = null, lastHf = null;
  g.update = (dt, eye) => {
    if (!S.spec) return origG(dt, eye);
    if (S.paused || S.done) { if (S.paused && S.photo) { cam.position.set(...S.photo.pos); cam.up.set(0, 1, 0); cam.lookAt(...S.photo.at); } return; }
    for (let i = 0; i < S.K; i++) {
      const input = step(S.sub);
      if (S.paused) return;
      origP(S.sub, input);
      fsUpdate?.(S.sub, pl);
      origG(S.sub, cam.position);
      S.t += S.sub; acc += S.sub;
      if (S.spec.photoUnstick && h.stats.unsticks > (S.lastUn ?? 0)) { S.lastUn = h.stats.unsticks; if (S.lastUn <= S.spec.photoUnstick) { S.want = { name: `unstick${S.lastUn}_t${Math.round(S.t)}`, view: 'high' }; S.paused = true; return; } }
      if (S.t >= S.spec.secs) { S.done = true; return; }
      if (acc >= 0.1 - 1e-6 && h.chain) {
        acc = 0;
        const c = h.chain, P = pl.pos;
        const yaw = h.bodyYaw ?? 0, hf = h.frontYaw();
        const dYaw = lastYaw == null ? 0 : wrap(yaw - lastYaw), dHf = lastHf == null ? 0 : wrap(hf - lastHf);
        lastYaw = yaw; lastHf = hf;
        const brg = wrap(Math.atan2(P.x - c.hd.x, P.z - c.hd.y) - hf);
        let rem = 0;
        if (h.path && h.path.length) { rem = c.hd.distanceTo(h.path[Math.min(h.pathI ?? 0, h.path.length - 1) + (h.path.length > 1 ? 1 : 0)] ?? h.path[h.path.length - 1]); }
        S.log.push({
          t: +S.t.toFixed(2), st: h.state, sub: h.sub ?? null, anim: g.current?.getClip().name,
          x: +c.hd.x.toFixed(2), z: +c.hd.y.toFixed(2), qx: +c.q.x.toFixed(2), qz: +c.q.y.toFixed(2), bx: +c.b.x.toFixed(2), bz: +c.b.y.toFixed(2),
          hf: +hf.toFixed(3), dYaw: +dYaw.toFixed(3), dHf: +dHf.toFixed(3),
          px: +P.x.toFixed(2), pz: +P.z.toFixed(2), py: +P.y.toFixed(2), down: pl.isDown ? 1 : 0,
          seen: h.seenAt === h.time ? 1 : 0, seenAgo: +(h.time - h.seenAt).toFixed(1),
          ls: h.lastSeen ? [+h.lastSeen.x.toFixed(2), +h.lastSeen.y.toFixed(2)] : null,
          goal: h.goal ? [+h.goal.x.toFixed(2), +h.goal.y.toFixed(2)] : null,
          path: h.path ? h.path.length : 0, brg: +brg.toFixed(2),
          unst: h.stats.unsticks, fails: h.stats.fails ?? 0, replans: h.stats.replans,
          aware: h.aware !== undefined ? +h.aware.toFixed(2) : null,
          gk: h.goalK >= 0 && h.nav.centre ? h.nav.centre(h.goalK).toArray().map((v) => +v.toFixed(2)) : null, goff: h.goalOff != null ? +(+h.goalOff).toFixed(2) : null,
          peek: h.peek ? 1 : 0, wk: h.waiting?.kind ?? null, pend: h.path && h.path.length ? h.path[h.path.length - 1].toArray().map((v) => +v.toFixed(2)) : null,
        });
      }
    }
  };
  S.run = (spec) => { S.lastUn = 0;
    S.spec = spec; S.t = 0; S.log = []; S.events = []; si = 0; stepT = 0; crouch = false; look = 'grimble'; wp = 0; lastYaw = lastHf = null;
    pl.hidden = false; pl.crouching = false;
    if (pl.down) { pl.down = null; pl.eye = 1.65; }
    for (const d of spec.doors ?? [[-19.75, 10.5, false], [13.5, -3.5, false], [8, 17.5, false], [-8, 17.5, false]]) S.door(...d);
    S.placeP(...spec.P);
    S.placeG(...spec.G);
    if (spec.idle) S.idleG(spec.idle);
    if (spec.saw) S.sawP();
    h.stats.unsticks = 0; h.stats.replans = 0; if (h.stats.fails !== undefined) h.stats.fails = 0;
    S.done = false; S.paused = false;
  };
  S.resume = () => { S.photo = null; S.paused = false; pl.syncCamera(); };
  return true;
}
