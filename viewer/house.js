import * as THREE from 'three';

// The house's systems as gameplay: power, light and darkness (prompts/interactivity.md).
// Sandbox only: no goal, no fail state, no story text; power starts on.
//
//  Power trips   The Grimble's break-in blows the main fuse: the lights flicker and go, the
//                isolator in the garage drops to off and its fuse carrier is empty (signals
//                `power` and `fuse_garage` false). A spare fuse is in the garage's steel locker
//                (a key chain: blender/levels/caches.py); with it in, the isolator switches back on. Later, while the
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
// URL: ?trips=0 no timed trips, ?trips=N one every N s (tests), ?breaktrip=1 the break-in
// trips the power and blows the fuse (off by default), ?dark=0 no fallback dimming. window.__house: {lightAt, roomAt, trip,
// level(room), state}. Sound hooks (optional): window.__sfx.play('power_flicker' | 'power_out'
// | 'power_on' | 'fuse_blow', position).

// share of a room's baked light that is daylight (the rest is its fittings), for the fallback
// dimmer and lightAt(): from each room's glazing (blender/levels/room_info.py); windowless = ~0
export const DAYLIGHT = {
  courtyard: 1.0,
  // (low: the bake's look is a golden-hour evening, and the fallback scales the electric light
  // in the lightmap by the same factor, so a high share leaves the coves and wall washes on)
  entry: 0.3, great_room: 0.3, dining: 0.25, kitchen: 0.25,
  gallery_s: 0.25, gallery_n: 0.25, gallery_w: 0.25, gallery_e: 0.25,
  ugallery_s: 0.22, ugallery_n: 0.22, ugallery_w: 0.22, ugallery_e: 0.22,
  library: 0.2, primary_bedroom: 0.18, office: 0.18, gym: 0.18, guest_room: 0.18, mudroom: 0.18,
  powder: 0.02, cloak: 0.02, den: 0.03, scullery: 0.03, wine_room: 0.02, garage: 0.02, primary_bath: 0.02,
};
const BLINDS = 0.3;           // daylight left with a room's blinds down
const DEFAULT_DAYLIGHT = 0.2;

// light level x time for a trip (the electric part of the light; ends dark). Power coming back
// just ramps the rooms up (update: ~0.3 s)
const TRIP_FLICKER = [[0, 0.2], [0.07, 1], [0.22, 0.1], [0.3, 0.85], [0.55, 0.25], [0.62, 1], [0.9, 0.08], [0.97, 0.55], [1.1, 0.03], [1.3, 0]];
const sample = (curve, t) => {
  let v = curve[0][1];
  for (const [at, k] of curve) if (t >= at) v = k;
  return v;
};

export class House {
  constructor({ signals, noise, level, baked, scene, camera, flashlight, interact, toast = () => {}, params = new URLSearchParams() }) {
    Object.assign(this, { signals, noise, baked, scene, camera, flashlight, interact, toast });
    this.rooms = Object.entries(level.rooms).sort((a, b) => b[1].floor - a[1].floor);   // upper floor first
    this.levels = new Map();      // room -> how far its fittings are on now, 0..1 (eases to target())
    this.flick = 1;               // the trip flicker on the electric part of the light
    this.tripping = null;         // { t, blowFuse, curve }
    this.time = 0;
    this.cueT = 0;
    this.wasBroken = false;
    const trips = params.get('trips');
    this.tripEvery = trips === null ? [150, 330] : +trips > 0 ? [+trips, +trips] : null;
    this.nextTrip = null;         // s of hunting left before the next timed trip
    this.breakTrip = params.get('breaktrip') === '1';   // (off by default: the user doesn't want the break-in to cut the power)
    // a room with a lights-off bake (bake.py --state off: baked.js fades it by its signal) needs
    // no fallback; the dimmer only drives the rooms without one
    this.baked = baked;
    this.dimmer = baked && params.get('dark') !== '0' ? this.collect() : null;
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

  // are a room's fittings on (1) or off (0)? Off, only its daylight comes in
  target(room) {
    return this.signals.get('power') !== false && this.signals.get(`lights_${room}`) !== false ? 1 : 0;
  }
  // the fittings' share right now (with the trip flicker)
  electric(room) { return (this.levels.get(room) ?? 1) * this.flick; }

  // how lit a spot is right now, 0..1 (outdoors 1: it's day). For the Grimble's eyes: the
  // player in a dark room is hard to see (unless the flashlight is on)
  lightAt(p) {
    const room = this.roomAt(p);
    if (!room) return 1;
    const d = this.daylight(room);
    return d + (1 - d) * this.electric(room);
  }
  // a room's light level (without the flicker): 1 lit .. its daylight share
  level(room) { const d = this.daylight(room); return d + (1 - d) * (this.levels.get(room) ?? 1); }

  // ------------------------------------------------------------ fallback dimmer
  // every material lit from a room's bake: its lightmap, probe and reflections are per room,
  // so the room is known from its env map (shell, props, rugs and the room batches share them)
  collect() {
    const byEnv = new Map();
    const hasOff = (room) => !!this.baked.bake?.rooms?.[room]?.off;
    for (const [room, r] of Object.entries(this.baked.rooms)) if (!hasOff(room)) byEnv.set(r.envMap, room);
    const mats = new Map();     // room -> [{m, lm, env, em}]
    const seen = new Map();     // material -> room
    // the shell's glowing parts (ceiling strips: Mansion_<room>_M_LightStrip) have no room env:
    // the room is in the mesh name (longest room name first: "ugallery_s" before "gallery_s")
    const names = Object.keys(this.baked.rooms).sort((a, b) => b.length - a.length);
    const byName = (n) => names.find((r) => n.startsWith(`Mansion_${r}_`) && !hasOff(r));
    const glows = (m) => m.emissive && m.emissive.getHex() !== 0 && m.emissiveIntensity > 0;
    const leds = new Set(this.interact.items.map((i) => i.indicator?.material).filter(Boolean));   // (locks' lights: theirs)
    this.scene.traverse((o) => {
      if (!o.isMesh || Array.isArray(o.material)) return;
      let m = o.material;
      // a reactor's material is the reactor's to drive (interactables.js); house.js flickers it
      if (!m || m.userData.emissiveBase !== undefined || leds.has(m)) return;
      const room = byEnv.get(m.envMap) ?? (glows(m) ? byName(o.name) : null);
      if (!room) return;
      if (seen.has(m) && seen.get(m) !== room) { m = o.material = m.clone(); }   // (a glow shared across rooms: one per room)
      if (seen.has(m)) return;
      seen.set(m, room);
      (mats.get(room) ?? mats.set(room, []).get(room)).push({
        m, lm: m.lightMapIntensity, env: m.envMapIntensity, em: glows(m) ? m.emissiveIntensity : null });
    });
    // the props' diffuse light: the room's SH probe (uniform arrays shared by reference)
    const sh = new Map();
    for (const [room, r] of Object.entries(this.baked.rooms)) if (r.sh && !hasOff(room)) sh.set(room, { arr: r.sh, base: r.sh.map((v) => v.clone()) });
    return { mats, sh, shown: new Map() };
  }

  // k: the room's light level; el: its fittings' share (their glow)
  apply(room, k, el) {
    const D = this.dimmer;
    const was = D?.shown.get(room);
    if (!D || (was && Math.abs(was.k - k) < 1e-3 && Math.abs(was.el - el) < 1e-3)) return;
    D.shown.set(room, { k, el });
    for (const e of D.mats.get(room) ?? []) {
      if (e.m.lightMap) e.m.lightMapIntensity = e.lm * k;
      e.m.envMapIntensity = e.env * (0.15 + 0.85 * k);   // reflections fade less: glass and metal still catch the windows
      if (e.em !== null) e.m.emissiveIntensity = e.em * el;   // strips, LED lines no switch drives
    }
    const s = D.sh.get(room);
    if (s) s.arr.forEach((v, i) => v.copy(s.base[i]).multiplyScalar(k));
  }

  applyAll(force = false) {
    for (const [room] of this.rooms) {
      const d = this.daylight(room), el = this.electric(room);
      if (force && this.dimmer) this.dimmer.shown.delete(room);
      this.apply(room, d + (1 - d) * el, el);
    }
  }

  // ------------------------------------------------------------ power events
  // the power trips: a flicker, then dark. blowFuse: the main fuse goes too (a spare is needed)
  trip({ blowFuse = false, delay = 0 } = {}) {
    if (this.signals.get('power') === false || this.tripping) return false;
    // (items off, blender/levels/caches.py) no spare fuse in the level: a blown fuse could never
    // be replaced, so the trip only drops the isolator (switch it back on in the garage)
    if (blowFuse && !this.interact?.items?.some((i) => i.def.item === 'fuse')) blowFuse = false;
    this.tripping = { t: -delay, blowFuse, sounded: false };
    return true;
  }

  onPower(on) {
    if (on) {
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
      if (this.nextTrip <= 0) { this.trip({ blowFuse: false }); this.nextTrip = this.tripEvery ? this.rand() : null; }
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
    }
  }

  rand() { const [a, b] = this.tripEvery ?? [Infinity, Infinity]; return a + Math.random() * (b - a); }

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
