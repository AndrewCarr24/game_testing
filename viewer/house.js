import * as THREE from 'three';

// The house's systems as gameplay: power, light and darkness (prompts/interactivity.md).
// Sandbox only: no goal, no fail state, no story text; power starts on.
//
//  Power trips   The Grimble's break-in blows the main fuse: the lights flicker and go, the
//                isolator in the garage drops to off and its fuse carrier is empty (signals
//                `power` and `fuse_garage` false). A spare fuse is upstairs (the guest room's
//                nightstand drawer); with it in, the isolator switches back on. Later, while the
//                Grimble moves through the house, the isolator trips now and then (fuse intact:
//                a walk to the garage in the dark). The player may switch it off on purpose.
//  Power drives  every electric reactor (lamps, screens, LED strips, the chargers' light bars),
//                the motors (blinds, the garage door: interactables.js `motor`), the tablet's
//                hub and cameras (tablet.js), and the room light below.
//  Darkness      lightAt(position) = how lit that spot is, 0..1, from the signals: a room is
//                lit while `power` and its `lights_<room>` are on, else only daylight through
//                its glass (DAYLIGHT, less with its blinds down; windowless rooms go black).
//                Until the lighting workstream's lights-off bake lands, a fallback dims each
//                room's baked lighting to that level (lightmap, probe SH and reflections: only
//                uniform changes, no recompiles); it stands down by itself when the bake
//                provides its own signal-driven off states (see `theirs` below), or with ?dark=0.
//  Flashlight    signal `flashlight` mirrors whether it's lit (window.__flashlight.beam() has
//                where it points). In the dark the beam gives you away: while it's on in a
//                dark spot and the Grimble is inside, in the beam (or close by) with no wall
//                between, a `light` cue goes out through the noise hook every second:
//                window.__noise.emit({position: eye, loudness: 1, source: 'light'}).
//
// URL: ?trips=0 no timed trips, ?trips=N one every N s (tests), ?breaktrip=0 the break-in
// leaves the power on, ?dark=0 no fallback dimming. window.__house: {lightAt, roomAt, trip,
// level(room), state}. Sound hooks (optional): window.__sfx.play('power_flicker' | 'power_out'
// | 'power_on' | 'fuse_blow', position).

// share of a room's baked light that is daylight (the rest is its fittings), for the fallback
// dimmer and lightAt(): from each room's glazing (blender/levels/room_info.py); windowless = ~0
export const DAYLIGHT = {
  courtyard: 1.0,
  entry: 0.45, great_room: 0.5, dining: 0.4, kitchen: 0.4,
  gallery_s: 0.45, gallery_n: 0.45, gallery_w: 0.45, gallery_e: 0.45,
  ugallery_s: 0.4, ugallery_n: 0.4, ugallery_w: 0.4, ugallery_e: 0.4,
  library: 0.35, primary_bedroom: 0.3, office: 0.3, gym: 0.3, guest_room: 0.3, mudroom: 0.3,
  powder: 0.02, cloak: 0.02, den: 0.03, scullery: 0.03, wine_room: 0.02, garage: 0.02, primary_bath: 0.02,
};
const BLINDS = 0.3;           // daylight left with a room's blinds down
const DEFAULT_DAYLIGHT = 0.25;

// light level x time for a trip (the electric part of the light; ends dark) and a restore
const TRIP_FLICKER = [[0, 0.2], [0.07, 1], [0.22, 0.1], [0.3, 0.85], [0.55, 0.25], [0.62, 1], [0.9, 0.08], [0.97, 0.55], [1.1, 0.03], [1.3, 0]];
const RESTORE_FLICKER = [[0, 0.5], [0.06, 0], [0.16, 0.8], [0.22, 0.2], [0.3, 1]];
const sample = (curve, t) => {
  let v = curve[0][1];
  for (const [at, k] of curve) if (t >= at) v = k;
  return v;
};

export class House {
  constructor({ signals, noise, level, baked, scene, camera, flashlight, interact, toast = () => {}, params = new URLSearchParams() }) {
    Object.assign(this, { signals, noise, baked, scene, camera, flashlight, interact, toast });
    this.rooms = Object.entries(level.rooms).sort((a, b) => b[1].floor - a[1].floor);   // upper floor first
    this.levels = new Map();      // room -> current light level (what the fallback shows)
    this.flick = 1;               // trip / restore flicker on the electric part of the light
    this.tripping = null;         // { t, blowFuse, curve }
    this.restoring = null;
    this.time = 0;
    this.cueT = 0;
    this.wasBroken = false;
    const trips = params.get('trips');
    this.tripEvery = trips === null ? [150, 330] : +trips > 0 ? [+trips, +trips] : null;
    this.nextTrip = null;         // s of hunting left before the next timed trip
    this.breakTrip = params.get('breaktrip') !== '0';
    // the lighting workstream's signal-driven off-state bake supersedes the fallback dimmer
    const theirs = baked && (baked.signalDriven || typeof baked.setLights === 'function' ||
      Object.values(baked.bake?.rooms ?? {}).some((r) => r.off || r.lightmapOff || r.dark));
    this.dimmer = baked && !theirs && params.get('dark') !== '0' ? this.collect() : null;
    for (const [name] of this.rooms) this.levels.set(name, this.target(name));
    this.applyAll(true);
    signals.on('power', (on) => this.onPower(on));
    this.state = () => ({
      power: signals.get('power'), fuse: signals.get('fuse_garage'), tripping: !!this.tripping,
      nextTrip: this.nextTrip, flashlight: signals.get('flashlight'), dimmer: !!this.dimmer,
    });
  }

  // ------------------------------------------------------------ light levels
  roomAt(p) {
    for (const [name, r] of this.rooms) {
      if (p.y < r.floor - 0.1 || p.y > r.floor + r.height + 0.1) continue;
      if (p.x >= r.rect[0] && p.x <= r.rect[2] && p.z >= r.rect[1] && p.z <= r.rect[3]) return name;
    }
    return null;
  }

  daylight(room) {
    const d = DAYLIGHT[room] ?? DEFAULT_DAYLIGHT;
    return this.signals.get(`blinds_${room}`) === true ? d * BLINDS : d;
  }

  // the level a room settles at: its fittings on (1) or only what daylight comes in
  target(room) {
    const lit = this.signals.get('power') !== false && this.signals.get(`lights_${room}`) !== false;
    return lit ? 1 : this.daylight(room);
  }

  // how lit a spot is right now, 0..1 (outdoors 1: it's day). For the Grimble's eyes: the
  // player in a dark room is hard to see (unless the flashlight is on)
  lightAt(p) {
    const room = this.roomAt(p);
    if (!room) return 1;
    const d = this.daylight(room), lvl = this.levels.get(room) ?? 1;
    return Math.max(d, d + (lvl - d) * this.flick);
  }
  level(room) { return this.levels.get(room); }

  // ------------------------------------------------------------ fallback dimmer
  // every material lit from a room's bake: its lightmap, probe and reflections are per room,
  // so the room is known from its env map (shell, props, rugs and the room batches share them)
  collect() {
    const byEnv = new Map();
    for (const [room, r] of Object.entries(this.baked.rooms)) byEnv.set(r.envMap, room);
    const mats = new Map();     // room -> [{m, lm, env}]
    const seen = new Set();
    this.scene.traverse((o) => {
      if (!o.isMesh) return;
      for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
        const room = m && byEnv.get(m.envMap);
        if (!room || seen.has(m)) continue;
        seen.add(m);
        (mats.get(room) ?? mats.set(room, []).get(room)).push({ m, lm: m.lightMapIntensity, env: m.envMapIntensity });
      }
    });
    // the props' diffuse light: the room's SH probe (uniform arrays shared by reference)
    const sh = new Map();
    for (const [room, r] of Object.entries(this.baked.rooms)) if (r.sh) sh.set(room, { arr: r.sh, base: r.sh.map((v) => v.clone()) });
    return { mats, sh, shown: new Map() };
  }

  apply(room, k) {
    const D = this.dimmer;
    if (!D || Math.abs((D.shown.get(room) ?? 1) - k) < 1e-3) return;
    D.shown.set(room, k);
    for (const e of D.mats.get(room) ?? []) {
      if (e.m.lightMap) e.m.lightMapIntensity = e.lm * k;
      e.m.envMapIntensity = e.env * (0.15 + 0.85 * k);   // reflections fade less: glass and metal still catch the windows
    }
    const s = D.sh.get(room);
    if (s) s.arr.forEach((v, i) => v.copy(s.base[i]).multiplyScalar(k));
  }

  applyAll(force = false) {
    for (const [room] of this.rooms) {
      const d = this.daylight(room), lvl = this.levels.get(room);
      const k = d + (lvl - d) * this.flick;
      if (force && this.dimmer) this.dimmer.shown.set(room, -1);
      this.apply(room, k);
    }
  }

  // ------------------------------------------------------------ power events
  // the power trips: a flicker, then dark. blowFuse: the main fuse goes too (a spare is needed)
  trip({ blowFuse = false, delay = 0 } = {}) {
    if (this.signals.get('power') === false || this.tripping) return false;
    this.tripping = { t: -delay, blowFuse, sounded: false };
    return true;
  }

  onPower(on) {
    if (on) {
      this.restoring = { t: 0 };
      this.toast('Power on');
      window.__sfx?.play?.('power_on', this.camera.position.clone());
      // a quiet spell after the lights come back
      if (this.tripEvery && this.nextTrip !== null) this.nextTrip = Math.max(this.nextTrip, 120);
    }
  }

  // the Grimble inside (window.__hunt, viewer/grimble_hunt.js): did it just break in, is it about?
  hunt() { return window.__hunt?.broken ? window.__hunt : null; }

  events(dt) {
    const h = this.hunt();
    if (h && !this.wasBroken) {
      this.wasBroken = true;
      if (this.breakTrip) this.trip({ blowFuse: true, delay: 0.5 });
      if (this.tripEvery) this.nextTrip = this.rand();
    }
    // timed trips while it moves through the house with the power on
    if (h && this.nextTrip !== null && this.signals.get('power') !== false && !this.tripping &&
        ['chase', 'search', 'prowl'].includes(h.state)) {
      this.nextTrip -= dt;
      if (this.nextTrip <= 0) { this.trip({ blowFuse: false }); this.nextTrip = this.rand(); }
    }
    if (this.tripping) {
      const tr = this.tripping;
      tr.t += dt;
      if (tr.t >= 0 && !tr.sounded) {
        tr.sounded = true;
        window.__sfx?.play?.('power_flicker', this.camera.position.clone());
      }
      this.flick = tr.t < 0 ? 1 : sample(TRIP_FLICKER, tr.t);
      if (tr.t >= TRIP_FLICKER.at(-1)[0]) {
        this.tripping = null;
        this.flick = 1;
        if (tr.blowFuse) { this.signals.set('fuse_garage', false); window.__sfx?.play?.('fuse_blow', this.camera.position.clone()); }
        this.signals.set('power', false);
        // the fittings are already dark from the flicker: no fade back from full glow
        for (const r of this.interact.reactors) if (r.electric && r.t !== r.target) { r.t = r.target; this.interact.poseReactor(r); }
        window.__sfx?.play?.('power_out', this.camera.position.clone());
        this.toast('Power out');
        // snap the rooms dark (the flicker already took them there)
        for (const [room] of this.rooms) this.levels.set(room, this.target(room));
      }
    } else if (this.restoring) {
      this.restoring.t += dt;
      this.flick = sample(RESTORE_FLICKER, this.restoring.t);
      if (this.restoring.t >= RESTORE_FLICKER.at(-1)[0]) { this.restoring = null; this.flick = 1; }
    }
  }

  rand() { const [a, b] = this.tripEvery; return a + Math.random() * (b - a); }

  // the electric fittings flicker with the room light (their materials and the point-light pool)
  flickerFittings() {
    const f = this.flick;
    if (f === 1 && this._lastFlick === 1) return;
    this._lastFlick = f;
    for (const r of this.interact.reactors) {
      if (!r.electric || !r.mats.length || r.on.emissive === undefined) continue;
      const e = r.off.emissive + (r.on.emissive - r.off.emissive) * r.t;
      for (const { m, base } of r.mats) m.emissiveIntensity = base * e * f;
    }
    if (this.interact.lights) for (const l of this.interact.lights) l.intensity *= f;
  }

  // ------------------------------------------------------------ the flashlight's light cue
  wallBetween(a, b) {
    const walls = this.interact.walls;
    if (!walls) return false;
    const dir = new THREE.Vector3().subVectors(b, a), len = dir.length();
    const ray = new THREE.Ray(a, dir.divideScalar(len)), hit = new THREE.Vector3();
    return walls.some((w) => ray.intersectBox(w, hit) && hit.distanceTo(a) < len - 0.3);
  }

  lightCue(dt) {
    this.cueT -= dt;
    if (this.cueT > 0) return;
    this.cueT = 1;
    const h = this.hunt(), beam = this.flashlight?.beam();
    if (!h || !beam?.on) return;
    if (this.lightAt(beam.position) > 0.6) return;            // a torch in a lit room is nothing to see
    const g = h.root.position.clone();
    g.y += 1.2;
    const to = g.clone().sub(beam.position), d = to.length();
    if (d > beam.range + 6) return;
    const inBeam = to.divideScalar(d).dot(beam.direction) > Math.cos(THREE.MathUtils.degToRad(beam.cone + 10));
    if (!inBeam && d > 10) return;         // its glow round you shows close by; the beam itself from its full reach
    if (this.wallBetween(beam.position, g)) return;
    this.noise.emit({ position: beam.position.clone(), loudness: 1, source: 'light' });
  }

  // the Grimble is lit by the sky (not a room probe): in a dark room it should be dark too
  shadeGrimble() {
    const g = window.__grimble?.root;
    if (!g || !g.visible || g.userData.lightAware) return;   // (its own code may take this over)
    if (!this._gmats) {
      this._gmats = [];
      g.traverse((o) => { if (o.isMesh) for (const m of [o.material].flat()) this._gmats.push({ m, env: m.envMapIntensity }); });
    }
    const k = this.hunt() ? Math.max(0.06, this.lightAt(g.position.clone().setY(g.position.y + 1))) : 1;
    if (Math.abs(k - (this._gk ?? 1)) < 1e-3) return;
    this._gk = k;
    for (const e of this._gmats) e.m.envMapIntensity = e.env * k;
  }

  // ------------------------------------------------------------ per frame (after interact.update)
  update(dt) {
    this.time += dt;
    this.events(dt);
    // rooms ease to their level: dark fast, light back a little slower
    for (const [room] of this.rooms) {
      const cur = this.levels.get(room), to = this.target(room);
      if (cur === to) continue;
      const rate = to < cur ? 6 : 3;
      this.levels.set(room, cur + Math.sign(to - cur) * Math.min(Math.abs(to - cur), rate * dt));
    }
    this.applyAll();
    this.flickerFittings();
    if (this.flashlight) this.signals.set('flashlight', !!this.flashlight.beam().on);
    this.lightCue(dt);
    this.shadeGrimble();
  }
}
