// In-page part of the invader suite (viewer/tools/invaders_suite.mjs). Fast-forward: K substeps
// of 1/60 s per real frame; the scripted player, the doors (interact), hiding and the invaders are
// all stepped in the same loop. One page load, many scenarios: window.__S.run(spec) clears the
// squad, resets the player, runs spec.setup + the steps for spec.secs of game time, logging every
// 0.25 s; spec.check(I, S) scores it.
() => {
  const I = window.__invaders, pl = window.__player, cam = window.__camera, it = window.__interact, hid = window.__hiding;
  const V3 = pl.pos.constructor;
  document.querySelectorAll('#hud,#stats').forEach((e) => (e.style.display = 'none'));
  const S = window.__S = { K: 4, sub: 1 / 60, spec: null, t: 0, log: [], marks: [], done: true, paused: false, want: null, V3 };
  const NO = { forward: false, back: false, left: false, right: false, jump: false, run: false, crouch: false };
  // ---- helpers for scenarios
  const doorItem = (x, z, y = 0) => {
    let best = null, bd = 1e9;
    for (const i of it.items) {
      if (!i.collider || i.def.type !== 'rotate') continue;
      const c = i.root.getWorldPosition(new V3()); const d = Math.hypot(c.x - x, c.z - z) + Math.abs(c.y - y);
      if (d < bd) { bd = d; best = i; }
    }
    return best;
  };
  S.door = (x, z, open, y = 0) => { const d = doorItem(x, z, y); d.target = d.t = open ? 1 : 0; it.pose(d); };
  S.lock = (x, z, locked, y = 0) => { const d = doorItem(x, z, y); d.locked = locked; };
  S.placeP = (x, z, y = 0) => { pl.pos.set(x, y, z); pl.vel.set(0, 0, 0); pl.syncCamera(); };
  S.v = (x, y, z) => new V3(x, y, z);
  S.mark = (label) => S.marks.push({ t: +S.t.toFixed(2), label });
  // an invader that is already inside (state, facing yaw = atan2(dx, dz))
  S.add = (role, x, z, { y = 0, yaw = 0, state = null, post = null, weapon = null } = {}) => {
    const a = I.spawn(role, { at: new V3(x, y, z), inside: role !== 'watcher', yaw, post, weapon, layer: y > 3 ? 'upper' : 'ground' });
    if (state === 'idle') { a.set('idle'); }
    if (state === 'hold') { a.set('hold'); a.sub = { at: a.pos.clone(), yaw, until: 1e9 }; }
    return a;
  };
  S.saw = (a, p = pl.pos) => { a.aware = 1; a.visAt = a.time; a.sawAt(p.clone(), 'sight'); a.set(a.gun ? 'pursue' : 'pursue', 'test'); };
  S.tell = (a, p) => a.told({ pos: p.clone(), t: a.time, src: 'test' });
  S.spot = (x, z, y = 0) => {
    let best = null, bd = 1e9;
    for (const i of it.items) {
      if (i.def.type !== 'hide' || i.disabled || !i.pose) continue;
      const d = Math.hypot(i.pose.exit.x - x, i.pose.exit.z - z) + Math.abs(i.pose.exit.y - y);
      if (d < bd) { bd = d; best = i; }
    }
    return best;
  };
  S.hide = (x, z, y = 0) => { const sp = S.spot(x, z, y); hid.enter(sp); return sp; };
  S.events = (kind) => I.events.filter((e) => e.t >= S.t0 && (!kind || e.kind === kind));
  // ---- the script
  let si = 0, stepT = 0, crouch = false, look = null, wp = 0;
  const lookAtNearest = () => {
    let best = null, bd = 1e9;
    for (const a of I.agents) { if (!a.alive) continue; const d = a.pos.distanceTo(pl.pos); if (d < bd) { bd = d; best = a; } }
    if (best) cam.lookAt(best.pos.x, best.pos.y + 1.5, best.pos.z);
  };
  const step = (dt) => {
    const steps = S.spec.steps ?? [];
    let input = { ...NO, crouch };
    for (let guard = 0; guard < 20 && si < steps.length; guard++) {
      const s = steps[si];
      const next = () => { si++; stepT = 0; wp = 0; if (s.label) S.mark(s.label); };
      if (s.go) {
        const R = Array.isArray(s.go[0]) ? s.go : [s.go];
        if (pl.isDown || hid.spot) { input = { ...NO }; break; }
        while (wp < R.length && Math.hypot(R[wp][0] - pl.pos.x, R[wp][1] - pl.pos.z) < 0.45) wp++;
        if (wp >= R.length) { next(); continue; }
        const [x, z] = R[wp];
        cam.lookAt(x, pl.pos.y + pl.eye, z);
        input = { ...NO, forward: true, run: s.mode === 'run', crouch: s.mode === 'crouch' || crouch };
        stepT += dt;
        if (s.timeout && stepT > s.timeout) { S.mark('go timeout ' + si); next(); continue; }
        break;
      }
      if (s.wait !== undefined) { stepT += dt; if (stepT >= s.wait) { next(); continue; } break; }
      if (s.until) {
        stepT += dt;
        const to = s.timeout ?? 60;
        if (s.until(I, S, pl) || stepT >= to) { if (stepT >= to) S.mark('until timeout ' + si); next(); continue; }
        break;
      }
      if (s.tp) { S.placeP(...s.tp); next(); continue; }
      if (s.door) { S.door(...s.door); next(); continue; }
      if (s.noise) { window.__noise.emit({ position: new V3(s.noise[0], s.noise[3] ?? 0.5, s.noise[1]), loudness: s.noise[2] ?? 1, source: s.source ?? 'test' }); S.mark(`noise ${s.noise}`); next(); continue; }
      if (s.crouch !== undefined) { crouch = s.crouch; next(); continue; }
      if (s.look !== undefined) { look = s.look; next(); continue; }
      if (s.hide) { S.hide(...s.hide); next(); continue; }
      if (s.fn) { s.fn(I, S, pl); next(); continue; }
      if (s.photo) { S.want = s.photo; S.paused = true; next(); return null; }
      next();
    }
    if (!input.forward && !hid.spot) {
      if (look === 'nearest') lookAtNearest();
      else if (Array.isArray(look)) cam.lookAt(...look);
    }
    return input;
  };
  // ---- the loop: the game's own update calls these once per frame; we step them K times
  const origP = pl.update.bind(pl), origI = I.update.bind(I), origIt = it.update.bind(it), origH = hid.update.bind(hid);
  const fs = window.__footsteps, origF = fs ? fs.update.bind(fs) : null;
  pl.update = () => {}; it.update = () => []; hid.update = () => !!hid.spot;
  if (fs) fs.update = () => {};
  let acc = 0;
  I.update = () => {
    if (!S.spec) return;
    if (S.paused || S.done) { if (S.paused && S.photo) { cam.position.set(...S.photo.pos); cam.up.set(0, 1, 0); cam.lookAt(...S.photo.at); } return; }
    for (let k = 0; k < S.K; k++) {
      const input = step(S.sub);
      if (S.paused) return;
      origIt(S.sub, cam.position);
      if (!origH(S.sub)) origP(S.sub, input);
      origF?.(S.sub, pl);
      origI(S.sub);
      window.__combat?.update?.(0);
      S.t += S.sub; acc += S.sub;
      if (S.t >= S.spec.secs || (S.spec.stop && S.spec.stop(I, S, pl))) { S.done = true; return; }
      if (acc >= 0.25 - 1e-6) {
        acc = 0;
        const C = window.__vitals?.target;
        S.log.push({ t: +S.t.toFixed(2), p: [+pl.pos.x.toFixed(2), +pl.pos.y.toFixed(2), +pl.pos.z.toFixed(2)], hid: pl.hidden ? 1 : 0, hp: C ? Math.round(C.health) : null,
          a: I.agents.map((a) => [a.id, a.state, +a.pos.x.toFixed(1), +a.pos.y.toFixed(1), +a.pos.z.toFixed(1), +a.aware.toFixed(2), a.seenNow ? 1 : 0, a.alive ? 1 : 0]) });
      }
    }
  };
  S.run = (spec) => {
    I.clear();
    I.time = 0;
    I.events.length = 0;
    I.stats.shots = I.stats.hits = I.stats.playerHits = I.stats.damage = I.stats.swings = 0;
    // the player back on their feet (viewer/combat.js PlayerVitals)
    const V = window.__vitals;
    if (V) { V.dead = false; V.flash = 0; V.target.health = V.target.maxHealth; V.target.alive = true; V.deathEl?.classList.remove('on'); }
    document.body.classList.remove('cb-dead');
    pl.dead = false;
    if (hid.spot) hid.leave({ instant: true });
    pl.hidden = false; pl.crouching = false;
    if (pl.down) { pl.down = null; pl.eye = 1.65; }
    S.spec = spec; S.t = 0; S.t0 = 0; S.log = []; S.marks = []; si = 0; stepT = 0; crouch = false; look = spec.look ?? 'nearest'; wp = 0;
    for (const d of spec.doors ?? []) S.door(...d);
    S.placeP(...spec.P);
    if (spec.face) cam.lookAt(...spec.face);
    spec.setup?.(I, S, pl);
    S.done = false; S.paused = false;
  };
  S.result = () => {
    const r = S.spec.check ? S.spec.check(I, S, pl) : {};
    return { ...r, marks: S.marks, events: I.events.slice(0, 400), summary: I.summary() };
  };
  S.resume = () => { S.photo = null; S.paused = false; pl.syncCamera(); };
  return true;
}
