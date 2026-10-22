// Scenarios for viewer/tools/invaders_opening.mjs: the first five (viewer/invaders_opening.js),
// fast-forward in viewer/tools/invaders_page.js (evaluated in the page; same spec format as
// invaders_scenarios.js). setup starts the opening: S.open(from, k) (from: gate | court | step;
// k scales its waits). World glTF (x, z), +z south: the front door at z = 20, the gate at z 62.
(() => {
  const first = (S, kind, f = () => true) => S.events(kind).find(f)?.t ?? null;
  const r2 = (v) => (v == null ? null : +v.toFixed(2));
  const O = () => window.__invaders.opening;
  const phaseAt = (S, ph) => O().timeline.find((x) => x.phase === ph)?.t ?? null;
  const cast = (k) => O().cast[k];
  // out of sight of the front: the upstairs office (its door shut), the kitchen
  const OFFICE = [7, -15, 4.6], KITCHEN = [-2, -15];
  const start = (from, k = 1) => (I, S) => { const o = O(); o.k = k; o.start({ from }); S.t0 = 0; };
  const FRONT = [[-0.75, 20, false], [0.75, 20, false]];
  return {
    // up the drive from the gate in a loose group, the leader in front; on the step by the ring
    arrival: { P: OFFICE, secs: 70, doors: [...FRONT, [6.75, -10.5, false, 4.6]], look: [6.75, 6.2, -10.5],
      setup: (I, S) => { start('gate')(I, S); S.gaps = []; S.leadFront = 0; S.samples = 0; },
      stop: () => O().phase === 'wait1',
      steps: [{ until: (I, S) => {
        const c = O().cast, L = c.leader, rest = Object.values(c).filter((a) => a !== L);
        if (O().phase === 'approach' && L) {
          S.samples++;
          const dz = (a) => Math.hypot(a.pos.x, a.pos.z - 20);
          if (rest.every((a) => dz(a) > dz(L) - 0.3)) S.leadFront++;
          const all = Object.values(c);
          let g = 1e9;
          for (let i = 0; i < all.length; i++) for (let j = i + 1; j < all.length; j++) g = Math.min(g, Math.hypot(all[i].pos.x - all[j].pos.x, all[i].pos.z - all[j].pos.z));
          S.gaps.push(g);
        }
        return O().phase === 'ring';
      }, timeout: 70 }, { wait: 1 }],
      check: (I, S) => {
        const o = O(), ring = phaseAt(S, 'ring'), gather = phaseAt(S, 'gather');
        const slots = { leader: [1.95, 20.8], gunA: [-2.5, 22.05], gunB: [3.4, 22.45], bat: [-0.85, 23.25], knife: [1.9, 23.85] };
        const off = Object.fromEntries(Object.entries(slots).map(([k, [x, z]]) => [k, r2(Math.hypot(cast(k).pos.x - x, cast(k).pos.z - z))]));
        const minGap = Math.min(...S.gaps), spawned = S.events('spawn').length;
        const front = S.leadFront / Math.max(1, S.samples);
        return { pass: spawned === 5 && ring != null && ring < 45 && Object.values(off).every((d) => d < 1.0) && minGap > 0.55 && front > 0.9 && !S.events('inside').length && !S.events('seq_seen').length,
          spawned, gatherAt: r2(gather), ringAt: r2(ring), leaderInFront: r2(front), minGap: r2(minGap), offSlot: off };
      } },
    // the ring is the house's chime: heard (flat, the house's speakers) from the far side of the
    // house; the squad doesn't go to investigate its own ring
    ring_heard: { P: KITCHEN, secs: 14, doors: FRONT, look: [-2, 1.6, -19],
      setup: (I, S) => { start('step')(I, S); S.log0 = window.__sfx?.log.length ?? 0; S.sig = []; S.off = window.__signals.on('doorbell', (v) => S.sig.push([+S.t.toFixed(2), v])); },
      steps: [{ wait: 14 }],
      check: (I, S) => {
        const X = window.__sfx, chimes = X ? X.log.slice(S.log0).filter((e) => e.name === 'doorbell') : [];
        const ring = first(S, 'seq_ring'), inv = S.events('investigate');
        return { pass: ring != null && S.sig.some((s) => s[1] === true) && !!X && chimes.length > 0 && chimes.every((e) => e.synth && e.flat) && !X.unknown.has('doorbell') && inv.length === 0,
          ringAt: r2(ring), signal: S.sig.map((s) => s.join(':')).join(' '), chimes: chimes.length, flat: chimes.every((e) => e.flat), investigate: inv.length, phase: O().phase };
      } },
    // the player answers the door after the first ring: a beat, then they're in
    answer: { P: [-7.2, 12.5], secs: 22, doors: FRONT, look: [0, 1.6, 21],
      setup: start('step'),
      steps: [{ until: () => O().phase === 'wait1', timeout: 10 }, { wait: 2 }, { go: [[-1, 18.6]], mode: 'walk' }, { fn: (I, S) => { S.door(0.75, 20, true); S.mark('opened'); } }, { look: 'nearest' }, { wait: 16 }],
      check: (I, S) => {
        const opened = S.marks.find((m) => m.label === 'opened')?.t ?? null, ans = phaseAt(S, 'answered'), inside = S.log.find((l) => l.t > (opened ?? 1e9) && l.a.some((a) => a[4] < 19.6))?.t ?? null, atk = S.log.find((l) => l.t > (opened ?? 1e9) && l.a.some((a) => ['engage', 'chase', 'strike'].includes(a[1])))?.t ?? null;
        return { pass: opened != null && ans != null && ans - opened < 1 && inside != null && atk != null && atk - opened < 6, opened: r2(opened), answered: r2(ans), firstInside: r2(inside), attackAt: r2(atk), hit: r2(first(S, 'playerHit')), reason: O().reason };
      } },
    // seen through the glass while they wait: they watch, stare in (the gunmen aim), then the
    // door is kicked in; no shot through the glass before it opens
    glass: { P: [2.2, 16.8], secs: 40, doors: FRONT, look: [1.5, 1.6, 22],
      setup: start('step'),
      steps: [{ wait: 40 }],
      check: (I, S) => {
        const seen = first(S, 'seq_seen'), stare = phaseAt(S, 'stare'), kick = first(S, 'breach'), shots = S.events('shot').filter((e) => kick == null || e.t < kick).length;
        return { pass: seen != null && stare != null && kick != null && kick - seen < 30 && shots === 0, seenAt: r2(seen), stareAt: r2(stare), kickedIn: r2(kick), shotsBeforeKick: shots, hit: r2(first(S, 'playerHit')), reason: O().reason };
      } },
    // hidden in the coat closet before they come: the whole sequence (waits x0.4): rings, knock,
    // handle, the look in, round the house, then they break in (front, glass, side door) and sweep
    hide: { P: [9.5, 16.5], secs: 170, doors: [...FRONT, [8, 17.5, true]], look: [10, 1.6, 12],
      steps: [{ go: [[10.2, 13.6], [11.03, 12.4]], mode: 'walk' }, { hide: [11.03, 11.82] }, { until: (I, S, pl) => pl.hidden, timeout: 3, label: 'hidden' },
        { fn: (I, S) => start('step', 0.4)(I, S) }, { wait: 170 }],
      check: (I, S) => {
        const o = O(), br = phaseAt(S, 'breakin'), found = first(S, 'found'), seen = first(S, 'seq_seen'), glass = first(S, 'glass'), breaches = S.events('breach').map((e) => e.door);
        const sweeping = S.log[S.log.length - 1].a.filter((a) => ['sweep', 'search', 'check', 'respond', 'investigate'].includes(a[1])).length;
        return { pass: o.reason === 'nobody answered' && o.rings === 2 && o.knocks >= 2 && o.handles >= 3 && br != null && seen == null && (found == null || found > br) && breaches.length >= 1 && sweeping >= 2,
          rings: o.rings, knocks: o.knocks, handles: o.handles, breakinAt: r2(br), reason: o.reason, breaches: breaches.join(','), glass: r2(glass), foundAt: r2(found), sweeping, timeline: o.timeline.map((x) => `${x.phase}@${x.t}`).join(' ') };
      } },
    // noises inside while they wait (the player knocks something over twice): they look, then come in
    heard: { P: OFFICE, secs: 30, doors: [...FRONT, [6.75, -10.5, false, 4.6]], look: [6.75, 6.2, -10.5],
      setup: start('step'),
      steps: [{ until: () => O().phase === 'wait1', timeout: 10 }, { wait: 1.5 }, { noise: [3, 14, 1.0, 0.5], source: 'thud' }, { wait: 4 }, { noise: [-3, 13, 1.0, 0.5], source: 'thud' }, { wait: 20 }],
      check: (I, S) => {
        const h = S.events('seq_heard'), br = phaseAt(S, 'breakin');
        return { pass: h.length >= 2 && br != null && O().reason === 'heard someone', heard: h.length, breakinAt: r2(br), reason: O().reason, kick: r2(first(S, 'breach')) };
      } },
    // the power is off: the bell is dead (it needs power); they knock instead, longer and harder
    power_off: { P: OFFICE, secs: 22, doors: [...FRONT, [6.75, -10.5, false, 4.6]], look: [6.75, 6.2, -10.5],
      setup: (I, S) => { window.__signals.set('power', false); S.log0 = window.__sfx?.log.length ?? 0; start('step', 0.5)(I, S); },
      steps: [{ wait: 22 }],
      check: (I, S) => {
        const o = O(), chimes = (window.__sfx?.log ?? []).slice(S.log0).filter((e) => e.name === 'doorbell').length, dead = S.events('seq_ring').filter((e) => e.dead).length;
        window.__signals.set('power', true);
        return { pass: !!o.bellDead && dead >= 1 && chimes === 0 && o.knocks === 3, deadRings: dead, chimes, knocks: o.knocks, phase: o.phase };
      } },
    // the entry's blinds are down: standing right behind them, they can't see in (the sequence
    // runs on as if nobody's home)
    blinds: { P: [2.2, 16.8], secs: 39, doors: FRONT, look: [1.5, 1.6, 22],
      setup: (I, S) => { window.__signals.set('blinds_entry', true); },
      steps: [{ wait: 9 }, { fn: (I, S) => start('step')(I, S) }, { wait: 30 }],     // (the blinds take ~7 s to come down)
      check: (I, S) => {
        const o = O(), seen = first(S, 'seq_seen'), blockers = window.__interact.sightBlockers().length;
        window.__signals.set('blinds_entry', false);
        return { pass: seen == null && blockers > 0 && o.rings === 2, seen: r2(seen), blockers, rings: o.rings, phase: o.phase };
      } },
    // the player is out on the court when they come up the drive: straight to the hunt (shots)
    outside: { P: [6, 31], secs: 20, doors: FRONT, look: [19, 1.6, 40],
      setup: start('court'),
      steps: [{ wait: 20 }],
      check: (I, S) => {
        const seen = first(S, 'seq_seen', (e) => e.outside), shot = first(S, 'shot');
        return { pass: seen != null && shot != null && shot - seen < 4, seenAt: r2(seen), firstShot: r2(shot), reason: O().reason, hit: r2(first(S, 'playerHit')) };
      } },
  };
})()
