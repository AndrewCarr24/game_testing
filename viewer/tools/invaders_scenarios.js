// Scenarios for viewer/tools/invaders_suite.mjs (evaluated in the page). World glTF (x, z), +z
// south (the front door is at z = 20). yaw = atan2(dx, dz): W -PI/2, E PI/2, N PI, S 0.
// P: player feet [x, z, y]. setup(I, S): place invaders (S.add(role, x, z, {yaw, state, y})).
// steps: {go: [[x, z], ...], mode: run|walk|crouch}, {wait}, {until(I, S, pl), timeout}, {tp}, {door: [x, z, open, y]},
//        {noise: [x, z, loud, y]}, {crouch}, {look: 'nearest'|[x, y, z]}, {hide: [x, z, y]}, {fn(I, S, pl)}, {photo: {name, view}}
// check(I, S, pl) -> {pass, ...metrics}
(() => {
  const W = -Math.PI / 2, E = Math.PI / 2, N = Math.PI, S0 = 0;
  const first = (S, kind, f = () => true) => S.events(kind).find(f)?.t ?? null;
  const r2 = (v) => (v == null ? null : +v.toFixed(2));
  return {
    // a gunman holding the south gallery; the player walks out into it 20 m away
    spotted: { P: [-12.5, 8.75], secs: 14, doors: [], face: [0, 1.6, 8.75],
      setup: (I, S) => { S.gun = S.add('gun', 9, 8.75, { yaw: W, state: 'hold' }); },
      steps: [{ go: [[-4, 8.75]], mode: 'walk', label: 'in view' }, { look: 'nearest' }, { wait: 14 }],
      check: (I, S) => {
        const seen = S.log.find((l) => l.a.some((a) => a[6]))?.t ?? null, shot = first(S, 'shot'), hit = first(S, 'playerHit');
        const shots = S.events('shot').length, hits = S.events('shot').filter((e) => e.hit).length;
        return { pass: seen != null && seen < 4 && shot != null && shot - seen < 2.5 && hit != null, noticed: r2(seen), firstShot: r2(shot), aimDelay: r2(shot - seen), firstHit: r2(hit), shots, hits, hpEnd: S.log[S.log.length - 1].hp };
      } },
    // the same, but the player stays behind the galleries' corner (out of sight): no shots
    // (the courtyard's glass doesn't stop a look; the den's walls and its shut door do)
    no_cheat: { P: [-20, 15], secs: 12, doors: [[-19.75, 10.5, false]],
      setup: (I, S) => { S.add('gun', -19.75, 5, { yaw: S0, state: 'hold' }); S.add('bat', -12, 8.75, { yaw: W, state: 'idle' }); },
      steps: [{ look: [-19.75, 1.6, 10.5] }, { go: [[-22, 13], [-17, 13], [-20, 17]], mode: 'walk' }, { wait: 12 }],
      check: (I, S) => ({ pass: !S.log.some((l) => l.a.some((a) => a[6])) && S.events('shot').length === 0, shots: S.events('shot').length }) },
    // it sees the player duck into the entry's coat closet: it opens it and drags them out
    hide_seen: { P: [9.5, 16.5], secs: 30, doors: [[8, 17.5, true]], look: 'nearest',
      setup: (I, S) => { S.bat = S.add('bat', 4.5, 16.5, { yaw: E, state: 'idle' }); S.saw(S.bat); },
      steps: [{ go: [[10.2, 13.6], [11.03, 12.4]], mode: 'run' }, { hide: [11.03, 11.82] }, { until: (I, S, pl) => pl.hidden, timeout: 3, label: 'hidden' }, { wait: 30 }],
      check: (I, S) => {
        const found = first(S, 'found'), hidAt = S.marks.find((m) => m.label === 'hidden')?.t ?? null, hit = first(S, 'playerHit');
        return { pass: found != null && hidAt != null, hidAt, found: r2(found), foundAfter: r2(found - hidAt), hitAfterFound: r2(hit != null && found != null ? hit - found : null), spots: S.events('found').length };
      } },
    // hidden in the kitchen pantry before they come; three sweep the ground floor with a report
    // of the kitchen a while ago: do they search methodically (rooms, spots) without beelining?
    hide_unseen: { P: [-9.35, -11.86], secs: 120, doors: [],
      setup: (I, S, pl) => {
        S.hide(-9.35, -11.86);
        const a = S.add('bat', -18, 0, { yaw: E }), b = S.add('knife', 0, 8.75, { yaw: N }), c = S.add('leader', 4.75, 15, { yaw: N });
        // (last seen in the great room, 20 s ago: they don't know about the pantry)
        I.time = 20; I.report(c, S.v(-20, 0, 0), 'test', true); I.intel[I.intel.length - 1].t = 0;
        for (const x of [a, b]) { S.tell(x, S.v(-20, 0, 0)); x.know.t = 0; x.set('respond'); }
      },
      steps: [{ wait: 120 }],
      check: (I, S) => {
        const found = first(S, 'found'), checks = I.agents.reduce((s, a) => s + a.stats.spots, 0), rooms = new Set([...I.cleared.keys()]);
        return { pass: checks >= 2 && rooms.size >= 3, found: r2(found), spotsChecked: checks, roomsCleared: [...rooms].join(','), firstSpot: S.events('found')[0]?.spot ?? null };
      } },
    // out of the front door with a watcher on it: shot at outside
    front_door: { P: [0, 16], secs: 16, doors: [[-0.75, 20, true], [0.75, 20, true]], look: [0, 1.6, 30],
      setup: (I, S) => { const E = I.entries.find((e) => e.name === 'entry'); S.w = S.add('watcher', E.post.at.x, E.post.at.z, { yaw: E.post.yaw, post: E.post }); },
      steps: [{ go: [[0, 19], [0, 23], [6, 30]], mode: 'run', label: 'out' }, { look: 'nearest' }, { wait: 16 }],
      check: (I, S) => {
        const out = S.log.find((l) => l.p[2] > 20.3)?.t ?? null, seen = S.log.find((l) => l.a.some((a) => a[6]))?.t ?? null, shot = first(S, 'shot'), hit = first(S, 'playerHit');
        return { pass: shot != null && hit != null && shot - out < 4, outAt: r2(out), seenAt: r2(seen), firstShot: r2(shot), firstHit: r2(hit), shots: S.events('shot').length, hits: S.events('shot').filter((e) => e.hit).length, hpEnd: S.log[S.log.length - 1].hp };
      } },
    // a noise lures a bat out of the south gallery (a vase smashed in the great room); the player,
    // in the entry, slips through behind it
    lure: { P: [6, 14], secs: 40, doors: [], look: [4.75, 1.6, 8.75],
      setup: (I, S) => { S.bat = S.add('bat', -6, 8.75, { yaw: S0, state: 'idle' }); },
      steps: [{ wait: 1 }, { noise: [-18, -5, 1.0], source: 'shatter' }, { until: (I, S) => S.bat.pos.x < -12, timeout: 20, label: 'gone' },
        { go: [[4.75, 8.75], [11.75, 8.75], [11.75, -3.5]], mode: 'walk' }, { door: [13.5, -3.5, true] }, { go: [[16, -3.5], [18, -7]], mode: 'walk' },
        { door: [13.5, -3.5, false] }, { look: [13.5, 1.6, -3.5], label: 'past' }, { wait: 30 }],
      check: (I, S) => {
        const inv = first(S, 'investigate');
        const closest = Math.min(...S.log.map((l) => { const a = l.a[0]; return Math.hypot(a[2] + 18, a[4] + 5); }));
        const noticed = S.log.some((l) => l.a.some((a) => a[6]));
        return { pass: inv != null && closest < 4 && !noticed, investigateAt: r2(inv), closest: r2(closest), noticedPlayer: noticed };
      } },
    // told the player is upstairs in the library: out of the den (door), up the stair, through the
    // library's door
    stairs: { P: [-17, 15, 4.6], secs: 45, doors: [[-19.75, 10.5, false], [-10.75, 10.5, false, 4.6]], look: [-10.75, 6.2, 10.5],
      setup: (I, S) => { S.k = S.add('knife', -20, 16, { yaw: S0, state: 'idle' }); S.tell(S.k, S.v(-17, 4.6, 15)); S.k.set('respond'); },
      stop: (I, S, pl) => S.k.pos.y > 4.4 && S.k.pos.distanceTo(pl.pos) < 3,
      check: (I, S) => {
        const doors = S.events('door').map((e) => e.door), up = S.log.find((l) => l.a[0][3] > 4.4)?.t ?? null;
        return { pass: doors.length >= 2 && up != null && S.k.pos.distanceTo(S.v(-17, 4.6, 15)) < 4, doors: doors.join(','), upstairsAt: up, endT: +S.t.toFixed(1), end: S.k.pos.toArray().map(r2) };
      } },
    // seen going into the office (locked): it kicks the door in
    breach: { P: [7, -15, 4.6], secs: 30, doors: [[6.75, -10.5, false, 4.6]], look: [6.75, 6.2, -10.5],
      setup: (I, S) => { S.b = S.add('bat', 0, -8.75, { y: 4.6, yaw: E, state: 'idle' }); S.saw(S.b, S.v(7, 4.6, -15)); },
      steps: [{ wait: 30 }],
      check: (I, S) => {
        const br = first(S, 'breach'), hit = first(S, 'playerHit');
        return { pass: br != null && hit != null, breach: r2(br), hit: r2(hit), kicks: S.b.stats.breaches ?? 0 };
      } },
    // shot twice by the player: staggers, calls out, then runs
    hit_react: { P: [0, 15], secs: 12, doors: [], look: 'nearest',
      setup: (I, S, pl) => { S.g = S.add('gun', 0, 8.75, { yaw: N }); S.h0 = I.stats.reports; },
      steps: [{ wait: 0.5 }, { fn: (I, S, pl) => { S.g.onHit(30, { from: { position: () => pl.pos }, weapon: 'test' }); S.st1 = S.g.state; S.sg = S.g.staggerUntil > S.g.time; } }, { wait: 2 },
        { fn: (I, S, pl) => S.g.onHit(45, { from: { position: () => pl.pos }, weapon: 'test' }) }, { wait: 0.2 }, { fn: (I, S) => { S.st2 = S.g.state; } }, { wait: 9 }],
      check: (I, S, pl) => ({ pass: S.sg && S.st2 === 'flee' && I.stats.reports > S.h0, staggered: S.sg, afterFirst: S.st1, afterSecond: S.st2, health: S.g.health, endDist: r2(S.g.pos.distanceTo(pl.pos)) }) },
    // the squad's radio: one sees the player; the far ones hear of it after the delay (and longer
    // once the leader is dead)
    radio: { P: [4.75, 15], secs: 10, doors: [[-19.75, 10.5, false], [13.5, -3.5, false]], look: [0, 1.6, 8.75],
      setup: (I, S) => {
        S.lead = S.add('leader', 4.75, 9, { yaw: S0, state: 'idle' });
        S.far1 = S.add('bat', -20, -15, { state: 'idle' }); S.far2 = S.add('knife', 20, -15, { state: 'idle' });
      },
      steps: [{ until: (I, S) => S.lead.seenNow, timeout: 4, label: 'seen' }, { wait: 6 }],
      check: (I, S) => {
        const seen = S.marks.find((m) => m.label === 'seen')?.t;
        const t1 = first(S, 'told', (e) => e.id === S.far1.id), t2 = first(S, 'told', (e) => e.id === S.far2.id);
        const d1 = t1 != null ? t1 - seen : null, d2 = t2 != null ? t2 - seen : null;
        return { pass: d1 != null && d2 != null && d1 > 0.8 && d1 < 3 && d2 > 0.8 && d2 < 3, seen, delay1: r2(d1), delay2: r2(d2), state1: S.far1.state, state2: S.far2.state };
      } },
  };
})()
