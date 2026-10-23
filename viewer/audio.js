import * as THREE from 'three';
import { LOOPS, reverbIR } from './audio_synth.js';

// Sound effects (Web Audio). One-shots come from one MP3 sprite (assets/audio/sfx.mp3 + .json,
// built by tools/build_audio.py from Kenney's CC0 packs and numpy synthesis; credits in
// assets/audio/CREDITS.md); loops are synthesised here at start-up (viewer/audio_synth.js).
//
//   window.__sfx.play(name, position?, opts?)   a one-shot; position = Vector3 | [x, y, z] | null
//       (null, or a sound without a distance in the manifest = not positional: UI, the player's
//       own body). opts: {db, gain, rate, jitter, delay, ref, prio, occlude: false}. Unknown names
//       are ignored.
//       Returns the voice or null.
//   window.__sfx.log                            every play() call [{t, name, pos?, muted?}], for tests
//   window.__sfx.counts                         name -> number of calls
//   window.__sfx.unknown                        names asked for that the manifest doesn't have
//   window.__sfx.used(item, message)            index.html's E handler: the sounds for an E press
//                                               that changed nothing (a locked door, a dead switch)
//
// Positional sounds go through HRTF (the Grimble) or equal-power panners with inverse-distance
// fall-off from the sound's `ref` distance, muffled (low-pass + quieter) by each wall between the
// source and the ear, and into a shared reverb whose level follows the room the player is in. A
// pool of MAX_VOICES positional and MAX_FLAT flat voices; a busy pool steals the oldest voice of
// the lowest priority (footsteps first, the Grimble last). Loops (wind, room tone, mains hum,
// motors, TV, fire) are separate and never stolen.
//
// Nothing else has to call it: update() watches the game's public state each frame (the player's
// feet, doors and drawers, signals, inventory, flashlight, throwables, noise events, the Grimble's
// state and animation phase) and plays what that implies. The AudioContext starts on the first
// click or key (browsers allow no sound before it); until then calls are only logged. Off under
// window.__bench (benchmarks and screenshots) and with ?sfx=0 (index.html doesn't make it).

const MAX_VOICES = 14, MAX_FLAT = 6;
const dB = (d) => Math.pow(10, d / 20);
const PRIO = { step: 0, self: 1, ui: 1, world: 2, grimble: 3 };
const _p = new THREE.Vector3(), _f = new THREE.Vector3(), _u = new THREE.Vector3(), _q = new THREE.Quaternion();

// continuous sources: synth buffer, level (dB), distance (null = flat ambience), stereo bus
const LOOP_DEFS = {
  wind: { buf: 'wind', db: -22, ref: null },
  air: { buf: 'air', db: -36, ref: null },
  hum: { buf: 'hum', db: -44, ref: null },
  motor: { buf: 'motor', db: -22, ref: 2.0 },
  garage: { buf: 'motor', db: -16, ref: 4.0, rate: 0.55 },
  tv: { buf: 'tv', db: -12, ref: 3.0 },
  fire: { buf: 'fire', db: -20, ref: 2.0 },
};

// footfall contacts per animation clip (phase 0..1 of the cycle): a limb lands where its gait
// phase wraps (grimble_rig.py walk; grimble_crawl.py crawl/crawl_fast `phases`)
const GAIT = {
  Walk: [[0.0, 'g_step', 'foot'], [0.5, 'g_step', 'foot']],
  Crawl: [[0.0, 'g_foot', 'rear'], [0.25, 'g_hand', 'front'], [0.5, 'g_foot', 'rear'], [0.75, 'g_hand', 'front']],
  CrawlFast: [[0.0, 'g_foot', 'rear'], [0.44, 'g_hand', 'front'], [0.5, 'g_foot', 'rear'], [0.94, 'g_hand', 'front']],
};

const toVec = (p) => (p == null ? null : p.isVector3 ? p : Array.isArray(p) ? _p.set(p[0], p[1], p[2]) : p.x !== undefined ? _p.set(p.x, p.y ?? 0, p.z ?? 0) : null);
const r2 = (v) => Math.round(v * 100) / 100;

export class Sfx {
  // camera: the listener; level: mansion.json; shell: the shell's scene (floor materials, rugs)
  constructor({ camera, level, base = '../assets/', shell = null, volume = 1 }) {
    this.camera = camera;
    this.level = level;
    this.volume = Number.isFinite(volume) ? Math.max(0, volume) : 1;
    this.log = [];
    this.counts = {};
    this.unknown = new Set();
    this.ctx = null;
    this.buffer = null;
    this.manifest = null;
    this.offset = 0;              // the decoder's delay, measured from the sprite's marker
    this.voices = [];
    this.flat = [];
    this.loops = new Map();       // key -> {def, src, gain, filter, panner, level, touched, quietFor}
    this.loopBuffers = {};
    this.last = {};               // name -> last variant (no immediate repeats)
    this.t = 0;
    this.walls = null;            // the shell's boxes (occlusion), from attach()
    this.surfaces = new Surfaces(level, shell);
    this.wetByRoom = roomWetness(level);
    this.data = Promise.all([
      fetch(`${base}audio/sfx.json`).then((r) => r.json()),
      fetch(`${base}audio/sfx.mp3`).then((r) => r.arrayBuffer()),
    ]).then(([m, mp3]) => { this.manifest = m; this.mp3 = mp3; })
      .catch((e) => console.warn('sfx: no sound effects', e));
    this._unlock = () => this.unlock();
    addEventListener('pointerdown', this._unlock, true);
    addEventListener('keydown', this._unlock, true);
    addEventListener('keydown', (e) => this.key(e), true);
    this.state = { items: new WeakMap(), inv: null, sig: 0 };
  }

  // the game objects it watches (all optional)
  attach(o) {
    Object.assign(this, o);
    this.walls = o.interact?.walls ?? null;
    o.noise?.on((n) => this.heard(n));
    o.signals?.on('*', (v, name) => this.signalChanged(name, v));
    return this;
  }

  // ------------------------------------------------------------ engine
  unlock() {
    if (window.__bench) return;
    if (this.ctx) { if (this.ctx.state === 'suspended') this.ctx.resume(); return; }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    const ctx = this.ctx = new AC();
    this.master = ctx.createGain();
    this.master.gain.value = this.volume;
    const lim = ctx.createDynamicsCompressor();          // a safety limiter on the mix
    lim.threshold.value = -6; lim.knee.value = 4; lim.ratio.value = 12; lim.attack.value = 0.002; lim.release.value = 0.2;
    this.master.connect(lim).connect(ctx.destination);
    this.bus = ctx.createGain(); this.bus.connect(this.master);
    this.amb = ctx.createGain(); this.amb.connect(this.master);
    this.send = ctx.createGain();
    const conv = ctx.createConvolver();
    const ir = reverbIR(ctx.sampleRate);
    const irb = ctx.createBuffer(2, ir[0].length, ctx.sampleRate);
    ir.forEach((c, i) => irb.copyToChannel(c, i));
    conv.normalize = false;
    conv.buffer = irb;
    this.wet = ctx.createGain(); this.wet.gain.value = 0.15;
    this.send.connect(conv).connect(this.wet).connect(this.master);
    ctx.resume?.();
    removeEventListener('pointerdown', this._unlock, true);
    addEventListener('pointerdown', () => ctx.state === 'suspended' && ctx.resume(), true);
    this.data.then(() => this.mp3 && new Promise((ok, fail) => ctx.decodeAudioData(this.mp3.slice(0), ok, fail)))
      .then((buf) => {
        if (!buf) return;
        // the decoder may put silence in front: find the marker click to line the clips up
        const d = buf.getChannelData(0), lim2 = Math.min(d.length, buf.sampleRate);
        let i = 0;
        while (i < lim2 && Math.abs(d[i]) < 0.3) i++;
        this.offset = i < lim2 ? i / buf.sampleRate - this.manifest.mark : 0;
        this.buffer = buf;
      })
      .catch((e) => console.warn('sfx: could not decode the sound effects', e));
    // the loops: one per tick, so no single frame pays for all of them
    const names = ['air', 'hum', 'wind', 'tv', 'fire', 'motor'];   // the ambience first
    const next = () => {
      if (window.__bench) { setTimeout(next, 500); return; }   // (never inside a measured run)
      const n = names.shift();
      if (!n) return;
      const chs = LOOPS[n](ctx.sampleRate);
      const b = ctx.createBuffer(chs.length, chs[0].length, ctx.sampleRate);
      chs.forEach((c, i) => b.copyToChannel(c, i));
      this.loopBuffers[n] = b;
      setTimeout(next, 30);
    };
    setTimeout(next, 50);
  }

  get running() { return !!(this.ctx && this.buffer && this.ctx.state === 'running' && !window.__bench); }

  // how many walls are between the ear and p (0..3)
  occlusion(p) {
    if (!this.walls) return 0;
    const eye = this.camera.position, dir = _f.subVectors(p, eye), len = dir.length();
    if (len < 0.5) return 0;
    const ray = this._ray ?? (this._ray = new THREE.Ray()), hit = this._hit ?? (this._hit = new THREE.Vector3());
    ray.set(eye, dir.divideScalar(len));
    let n = 0;
    for (const w of this.walls) {
      if (w.containsPoint(p) || w.containsPoint(eye)) continue;
      if (ray.intersectBox(w, hit) && hit.distanceTo(eye) < len - 0.05 && ++n >= 3) break;
    }
    return n;
  }

  voice(pool, spatial, prio) {
    const now = this.ctx.currentTime, max = spatial ? MAX_VOICES : MAX_FLAT;
    let v = pool.find((x) => !x.busy || x.ends < now);
    if (!v && pool.length < max) {
      const c = this.ctx;
      v = { gain: c.createGain(), filter: c.createBiquadFilter(), sendGain: c.createGain(), panner: spatial ? c.createPanner() : null };
      v.filter.type = 'lowpass';
      v.gain.connect(v.filter);
      if (v.panner) {
        v.panner.distanceModel = 'inverse'; v.panner.maxDistance = 500;
        v.filter.connect(v.panner).connect(this.bus);
      } else v.filter.connect(this.bus);
      v.filter.connect(v.sendGain).connect(this.send);
      pool.push(v);
    }
    if (!v) {
      // steal: the lowest priority, then the oldest; never a more important sound
      v = pool.reduce((a, b) => (b.prio < a.prio || (b.prio === a.prio && b.started < a.started) ? b : a));
      if (v.prio > prio) return null;
    }
    if (v.src) { try { v.src.onended = null; v.src.stop(); } catch {} v.src.disconnect(); v.src = null; }
    return v;
  }

  play(name, position = null, opts = {}) {
    const pos = toVec(position);
    const entry = { t: Math.round(performance.now()), name };
    if (pos) entry.pos = [r2(pos.x), r2(pos.y), r2(pos.z)];
    this.log.push(entry);
    if (this.log.length > 500) this.log.shift();
    this.counts[name] = (this.counts[name] || 0) + 1;
    const s = this.manifest?.sounds[name];
    if (this.manifest && !s) this.unknown.add(name);
    if (!this.running || !s) { entry.muted = true; return null; }
    const spatial = !!pos && s.ref != null;
    const cat = opts.cat ?? s.cat;
    const prio = opts.prio ?? (name.startsWith('step_') ? PRIO.step : PRIO[cat] ?? 1);
    const v = this.voice(spatial ? this.voices : this.flat, spatial, prio);
    if (!v) { entry.muted = 'busy'; return null; }
    let i = Math.floor(Math.random() * s.v.length);
    if (s.v.length > 1 && i === this.last[name]) i = (i + 1) % s.v.length;
    this.last[name] = i;
    const [start, dur, makeup] = s.v[i];
    const c = this.ctx, when = c.currentTime + (opts.delay ?? 0);
    const src = c.createBufferSource();
    src.buffer = this.buffer;
    const jitter = opts.jitter ?? 0.04;
    src.playbackRate.value = (opts.rate ?? 1) * (1 + (Math.random() * 2 - 1) * jitter);
    let g = dB(s.gain + makeup + (opts.db ?? 0)) * (opts.gain ?? 1), cutoff = 20000, wet = cat === 'ui' ? 0 : cat === 'self' ? 0.5 : 1;
    if (spatial) {
      const walls = opts.occlude === false ? 0 : this.occlusion(pos);
      g *= [1, 0.5, 0.3, 0.2][walls];
      cutoff = [20000, 2200, 1000, 550][walls];
      const p = v.panner, ref = opts.ref ?? s.ref;
      p.panningModel = cat === 'grimble' ? 'HRTF' : 'equalpower';
      p.refDistance = ref;
      p.rolloffFactor = cat === 'grimble' ? 0.8 : 1;
      setPos(p, pos);
      // far sounds are mostly reverb, but not at full level (it's another room's)
      wet *= Math.min(1, Math.sqrt(ref / Math.max(ref, this.camera.position.distanceTo(pos))) * 1.2);
    }
    v.gain.gain.setValueAtTime(g, c.currentTime);
    v.filter.frequency.setValueAtTime(cutoff, c.currentTime);
    v.sendGain.gain.setValueAtTime(wet, c.currentTime);
    src.connect(v.gain);
    const offset = Math.max(0, start + this.offset - 0.004);
    src.start(when, offset, dur + 0.01);
    v.src = src; v.busy = true; v.prio = prio; v.started = when; v.name = name;
    v.ends = when + (dur + 0.01) / src.playbackRate.value;
    src.onended = () => { if (v.src === src) { v.busy = false; v.src = null; } };
    return v;
  }

  // move a playing positional voice (a breath that follows the head)
  move(v, position) { if (v?.panner && this.running) setPos(v.panner, toVec(position)); }

  // a loop at `level` (0..1) this frame; loops not asked for in a frame fade out and stop
  loop(key, name, level, position = null) {
    const def = LOOP_DEFS[name];
    let l = this.loops.get(key);
    if (!l) {
      if (level <= 0 || !this.running || !this.loopBuffers[def.buf]) return;
      const c = this.ctx;
      l = { def, gain: c.createGain(), filter: c.createBiquadFilter(), panner: null, level: 0, quietFor: 0 };
      l.gain.gain.value = 0;
      l.filter.type = 'lowpass'; l.filter.frequency.value = 20000;
      l.gain.connect(l.filter);
      if (def.ref != null) {
        l.panner = c.createPanner();
        Object.assign(l.panner, { panningModel: 'equalpower', distanceModel: 'inverse', refDistance: def.ref, rolloffFactor: 1, maxDistance: 500 });
        l.filter.connect(l.panner).connect(this.bus);
        l.send = c.createGain(); l.send.gain.value = 0.6;
        l.filter.connect(l.send).connect(this.send);
      } else l.filter.connect(this.amb);
      l.src = c.createBufferSource();
      l.src.buffer = this.loopBuffers[def.buf];
      l.src.loop = true;
      l.src.playbackRate.value = def.rate ?? 1;
      l.src.connect(l.gain);
      l.src.start(c.currentTime, Math.random() * l.src.buffer.duration);
      this.loops.set(key, l);
    }
    l.touched = true;
    l.level = level;
    if (l.panner && position) {
      const p = toVec(position);
      setPos(l.panner, p);
      // through walls: muffled (re-checked a few times a second)
      if ((l._occT = (l._occT ?? 0) - 1) <= 0) {
        l._occT = 15;
        const w = this.occlusion(p);
        l.occ = [1, 0.45, 0.28, 0.18][w];
        l.filter.frequency.setTargetAtTime([20000, 1800, 900, 500][w], this.ctx.currentTime, 0.1);
      }
    }
    const target = dB(def.db) * level * (l.occ ?? 1);
    if (Math.abs(target - (l.applied ?? -1)) > 1e-4) {
      l.applied = target;
      l.gain.gain.setTargetAtTime(target, this.ctx.currentTime, 0.25);
    }
  }

  endLoops(dt) {
    for (const [key, l] of this.loops) {
      if (!l.touched && l.level > 0) { l.level = 0; l.applied = 0; l.gain.gain.setTargetAtTime(0, this.ctx.currentTime, 0.2); }
      l.touched = false;
      l.quietFor = l.level <= 0.001 ? l.quietFor + dt : 0;
      if (l.quietFor > 1.5) { try { l.src.stop(); } catch {} l.src.disconnect(); this.loops.delete(key); }
    }
  }

  // ------------------------------------------------------------ per frame
  update(dt) {
    if (window.__bench || !(dt > 0)) return;
    this.t += dt;
    if (this.running) this.listen();
    this.feet(dt);
    this.watchItems();
    this.watchInventory();
    this.watchGrimble(dt);
    if (this.running) {
      this.reactorLoops();
      this.ambience();
      this.endLoops(dt);
    }
  }

  listen() {
    const L = this.ctx.listener, cam = this.camera;
    cam.getWorldPosition(_p);
    cam.getWorldQuaternion(_q);
    _f.set(0, 0, -1).applyQuaternion(_q);
    _u.set(0, 1, 0).applyQuaternion(_q);
    if (L.positionX) {
      L.positionX.value = _p.x; L.positionY.value = _p.y; L.positionZ.value = _p.z;
      L.forwardX.value = _f.x; L.forwardY.value = _f.y; L.forwardZ.value = _f.z;
      L.upX.value = _u.x; L.upY.value = _u.y; L.upZ.value = _u.z;
    } else {
      L.setPosition(_p.x, _p.y, _p.z);
      L.setOrientation(_f.x, _f.y, _f.z, _u.x, _u.y, _u.z);
    }
  }

  // footsteps by floor, jumps, landings, being knocked down
  feet(dt) {
    const pl = this.player;
    if (!pl?.pos) return;
    const st = this._feet ?? (this._feet = { prev: pl.pos.clone(), stride: 0.6, grounded: true, air: 0, minVy: 0, down: false });
    const p = pl.pos, horiz = Math.hypot(p.x - st.prev.x, p.z - st.prev.z);
    st.prev.copy(p);
    if (pl.isDown && !st.down) {
      this.play('hit');
      this.play('fall', null, { delay: 0.42 });
    }
    st.down = pl.isDown;
    const g = pl.grounded;
    if (!g && st.grounded && pl.vel.y > 3 && !pl.isDown) this.play('jump');
    if (!g) { st.air += dt; st.minVy = Math.min(st.minVy, pl.vel.y); }
    else if (!st.grounded && st.air > 0.25) {
      // landing: the body's weight, and a heavy step on whatever it is
      const hard = Math.min(1, -st.minVy / 9);
      if (!pl.isDown) this.play('land', null, { db: -8 + 8 * hard });
      this.play(`step_${this.surfaces.at(p, pl._onRamp)}`, null, { db: -2 + 3 * hard, rate: 0.92 });
      st.stride = 0;
    }
    if (g) { st.air = 0; st.minVy = 0; }
    st.grounded = g;
    if (!g || pl.isDown || horiz > 3) return;      // (a teleport isn't a step)
    const speed = horiz / dt;
    if (speed < 0.4) { st.stride = Math.max(st.stride, 0.55); return; }   // standing: the next one comes soon
    const run = speed > 5, crouch = pl.crouching;
    const stride = crouch ? 0.62 : run ? 1.75 : 1.2;
    st.stride += horiz;
    if (st.stride >= stride) {
      st.stride -= stride;
      this.play(`step_${this.surfaces.at(p, pl._onRamp)}`, null,
        { db: crouch ? -13 : run ? 0 : -5, rate: run ? 1.04 : 1, jitter: 0.06 });
    }
  }

  // doors, drawers and cabinet doors as they move; locks and use points as they change
  watchItems() {
    const ix = this.interact;
    if (!ix) return;
    for (const it of ix.items) {
      const d = it.def, type = d.type;
      let s = this.state.items.get(it);
      if (!s) {
        s = { target: it.target, locked: it.locked, done: type === 'use' && ix.done(it), closing: false, kind: kindOf(it) };
        this.state.items.set(it, s);
        continue;
      }
      if (type === 'rotate' || type === 'slide') {
        if (it.target !== s.target) {
          const at = ix.centre(it);
          if (it.target) this.play(`${s.kind}_open`, at);
          else if (s.kind === 'drawer') this.play('drawer_close', at);
          s.closing = !it.target;
        }
        if (s.closing && it.t <= 0.12) { s.closing = false; if (s.kind !== 'drawer') this.play(`${s.kind}_close`, ix.centre(it)); }
        s.target = it.target;
      }
      if (it.locked !== s.locked) {
        const key = it.lockKey ?? '';
        const card = /card/.test(key);
        this.play(card ? (it.locked ? 'keycard_lock' : 'keycard_unlock') : 'key_turn', ix.centre(it));
        s.locked = it.locked;
      }
      if (type === 'use') {
        const done = ix.done(it);
        if (done && !s.done) this.play(/fuse/.test(d.needs ?? '') ? 'fuse_insert' : 'use', ix.centre(it));
        s.done = done;
      }
    }
  }

  // E pressed on something (index.html): only what changes no state needs sound here
  used(it, msg) {
    if (!it || !this.interact) return;
    const at = this.interact.centre(it);
    if (it.locked) this.play('door_locked', at);
    else if (it.def.type === 'switch' && performance.now() - this.state.sig > 40) this.play('breaker_dead', at);   // (`requires` not met)
  }

  // a signal changed: switches on it click (every rocker on a signal follows it), power
  signalChanged(name, value) {
    this.state.sig = performance.now();
    const ix = this.interact;
    if (!ix) return;
    let best = null, bd = 30;
    for (const it of ix.items) {
      if (it.def.type !== 'switch' || it.signal !== name) continue;
      const d = ix.centre(it).distanceTo(this.camera.position);
      if (d < bd) { best = it; bd = d; }
    }
    const on = value === true || value === 1 || value === 'true';
    if (best) this.play(name === 'power' ? (on ? 'breaker_on' : 'breaker_off') : on ? 'switch_on' : 'switch_off', ix.centre(best));
    if (name === 'power') this.play(on ? 'power_up' : 'power_down', null, { delay: 0.08 });
  }

  // thrown things landing (signals.js Noise: {position, loudness, source, item})
  heard(n) {
    if (!n?.position) return;
    if (n.source === 'shatter') this.play('shatter', n.position, { db: 4 * Math.log2(Math.max(0.25, n.loudness ?? 1)) });
    else if (n.source === 'thud') this.play(/book/.test(n.item ?? '') ? 'thud_book' : 'thud', n.position);
  }

  // the inventory screen, picking up, arming, the flashlight, a battery, throwing, the tablet
  watchInventory() {
    const inv = this.inventory;
    if (inv) {
      const s = this.state.inv ?? (this.state.inv = { open: inv.open, sel: inv.sel, armed: inv.armed, counts: new Map([...inv.items].map(([id, e]) => [id, e.count])) });
      if (inv.open !== s.open) this.play(inv.open ? 'ui_open' : 'ui_close');
      else if (inv.open && inv.sel !== s.sel) this.play('ui_move');
      if (inv.armed !== s.armed) {
        if (inv.armed) this.play('ui_arm');
        else if (inv.has(s.armed)) this.play('ui_holster');
      }
      for (const [id, e] of inv.items) {
        if (e.count > (s.counts.get(id) ?? 0)) this.play(pickupSound(id, e.def), this.camera.position);
        s.counts.set(id, e.count);
      }
      for (const id of [...s.counts.keys()]) if (!inv.items.has(id)) s.counts.delete(id);
      s.open = inv.open; s.sel = inv.sel; s.armed = inv.armed;
    }
    const fl = this.flashlight;
    if (fl) {
      if (this._flOn !== undefined && fl.on !== this._flOn && (fl.on || fl.battery > 0)) this.play('flashlight');
      if (this._flBat !== undefined && fl.battery > this._flBat + 0.2) this.play('battery');
      this._flOn = fl.on; this._flBat = fl.battery;
    }
    const th = this.throwables;
    if (th) {
      if (th.flying.length > (this._flying ?? 0)) this.play('throw');
      this._flying = th.flying.length;
    }
    const tab = this.tablet;
    if (tab) {
      if (this._tab !== undefined && tab.open !== this._tab)
        this.play(tab.open ? (this.signals?.get('power') === false ? 'tablet_offline' : 'tablet_open') : 'tablet_close');
      this._tab = tab.open;
    }
  }

  // keys while the tablet is open (it takes the arrows and Enter): this runs before its handler
  key(e) {
    if (!this.tablet?.open || e.repeat) return;
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.code)) this.play('tablet_move');
    else if (e.code === 'Enter' || e.code === 'NumpadEnter') this.play('tablet_toggle');
  }

  // blinds and the garage door hum while they move; TVs and fires while they're on
  reactorLoops() {
    const ix = this.interact;
    if (!ix) return;
    const groups = this._groups ?? (this._groups = groupReactors(ix.reactors));
    for (const g of groups) {
      if (g.kind === 'motor' || g.kind === 'garage') {
        if (g.list.some((r) => r.t !== r.target)) this.loop(`${g.kind}:${g.signal}`, g.kind, 1, centreOf(g.list));
      } else if (g.list.some((r) => ix.live(r))) this.loop(`${g.kind}:${g.signal}`, g.kind, 1, g.list[0].node.getWorldPosition(new THREE.Vector3()));
    }
  }

  // wind outdoors (and through a smashed window), still air and the mains hum indoors, and the
  // reverb of the room the player is in
  ambience() {
    const here = this.culler?.here ?? null, name = here?.name;
    const out = !here || name === 'courtyard';
    const broken = !!this.grimble?.()?.hunt?.broken && (name === 'great_room' || name === 'gallery_w');
    const power = this.signals?.get('power') !== false;
    // (secret passage) below ground: no wind, the ventilation's air and its own mains (the bunker's
    // batteries: rooms[r].power "own") whatever the house's power
    const under = here?.level < 0, own = here && this.level?.rooms?.[name]?.power === 'own';
    this.loop('wind', 'wind', out ? 1 : broken ? 0.45 : under ? 0 : 0.08);
    this.loop('air', 'air', out ? 0.2 : under ? 1.6 : 1);
    this.loop('hum', 'hum', power || own ? (out ? 0.1 : under ? 1.5 : 1) : 0);
    const wet = out ? 0.04 : this.wetByRoom[name] ?? 0.12;
    if (Math.abs(wet - (this._wet ?? -1)) > 0.005) { this._wet = wet; this.wet.gain.setTargetAtTime(wet, this.ctx.currentTime, 0.3); }
  }

  // ------------------------------------------------------------ the Grimble
  watchGrimble(dt) {
    const g = this.grimble?.();
    const st = this._g ?? (this._g = { state: null, t: 0, clip: null, ph: 0, broken: false, hunt: null, breathAt: 0, inhale: true, sniffAt: 4, growlAt: -99, breath: null });
    if (!g?.root?.visible) return;
    const h = g.hunt, root = g.root.position;
    const head = g.head ? g.head.getWorldPosition(new THREE.Vector3()) : root.clone().add(new THREE.Vector3(0, 5, 0));
    // knocks: the knuckles meet the glass at the clip's tap times (grimble.js `taps`)
    if (g.state === 'knock') {
      const prev = st.state === 'knock' ? st.t : -1;
      for (const at of g.o.taps) if (g.t >= at && prev < at) this.play('g_knock', this.glassPoint(g), { occlude: false });
    }
    // footfalls from the animation's phase
    const a = g.current, clip = a?.getClip?.();
    if (clip && GAIT[clip.name] && a.getEffectiveWeight() > 0.5) {
      const ph = (((a.time % clip.duration) + clip.duration) % clip.duration) / clip.duration;
      if (st.clip === clip.name) {
        for (const [at, sound, where] of GAIT[clip.name]) {
          const crossed = st.ph <= ph ? st.ph < at && at <= ph : at > st.ph || at <= ph;
          if (crossed) this.play(sound, this.limbPoint(g, where), { db: clip.name === 'CrawlFast' ? 2 : 0 });
        }
      }
      st.clip = clip.name; st.ph = ph;
    } else st.clip = null;
    if (h) {
      if (h.broken && !st.broken) this.play('g_smash', this.glassPoint(g), { occlude: false });
      st.broken = !!h.broken;
      const hs = h.state;
      if (hs !== st.hunt) {
        if (hs === 'chase' && this.t - st.growlAt > 7) { this.play('g_growl', head); st.growlAt = this.t; }
        if (hs === 'swipe') this.play('g_snarl', head);
        if (hs === 'reachUp') this.play('g_rear', head);
        if (hs === 'search') st.sniffAt = this.t + 0.6;
      }
      // the swipe's whoosh, just before the claws arrive
      if (hs === 'swipe' || hs === 'reachUp') {
        const hit = (hs === 'swipe' ? h.o.swipeHit : h.o.reachHit) - 0.28, prev = hs === st.hunt ? st.ht : -1;
        if (h.t >= hit && prev < hit) this.play('g_swipe', this.limbPoint(g, 'front'), { db: hs === 'reachUp' ? -2 : 0 });
      }
      st.ht = h.t;
      st.hunt = hs;
      // sniffing while it searches or pauses
      if ((hs === 'search' || (hs === 'prowl' && clip?.name === 'CrawlIdle')) && this.t >= st.sniffAt) {
        this.play('g_sniff', head);
        st.sniffAt = this.t + 2.5 + Math.random() * 3;
      }
    }
    st.state = g.state; st.t = g.t;
    // breathing, faster on the chase; it follows the head
    if (st.breath?.ends > this.ctx?.currentTime) this.move(st.breath, head);
    if (this.t >= st.breathAt && g.state !== 'walk' && g.state !== 'wait') {
      const fast = h?.state === 'chase' || h?.state === 'swipe';
      st.breath = this.play(st.inhale ? 'g_breath_in' : 'g_breath_out', head, { rate: fast ? 1.3 : 1, jitter: 0.06 });
      const len = st.inhale ? (fast ? 0.75 : 1.3) : (fast ? 0.9 : 1.7 + Math.random() * 1.2);
      st.breathAt = this.t + len;
      st.inhale = !st.inhale;
    }
  }

  // where its knuckles meet the great room glass
  glassPoint(g) {
    const r = g.root.position, a = g.heading ?? 0, reach = g.o?.reach ?? 2;
    return new THREE.Vector3(r.x + Math.sin(a) * reach, r.y + 3.2, r.z + Math.cos(a) * reach);
  }

  // on all fours: hands at the head end of its body chain, feet at the hindquarters
  limbPoint(g, where) {
    const c = g.hunt?.chain, y = g.root.position.y;
    if (c && g.state === 'inside') {
      const q = where === 'front' ? c.hd : where === 'rear' ? c.b : c.q;
      return new THREE.Vector3(q.x, y + 0.2, q.y);
    }
    return g.root.position.clone();
  }
}

// ------------------------------------------------------------ helpers
function setPos(p, v) {
  if (!v) return;
  if (p.positionX) { p.positionX.value = v.x; p.positionY.value = v.y; p.positionZ.value = v.z; }
  else p.setPosition(v.x, v.y, v.z);
}

function centreOf(list) {
  const c = new THREE.Vector3(), b = new THREE.Box3(), v = new THREE.Vector3();
  for (const r of list) c.add(b.setFromObject(r.node).getCenter(v));
  return c.divideScalar(list.length || 1);
}

// a door, a drawer or a cabinet door (an oven, the fridge): doors are door.py's `<Door>_Hinge`
function kindOf(it) {
  if (it.def.type === 'slide') return 'drawer';
  if (it.def.type !== 'rotate') return null;
  const n = it.node?.name ?? '', pr = it.def.prompt ?? '';
  return /^Door/i.test(n) || (/door/i.test(pr) && !/oven|fridge|cabinet|cupboard/i.test(pr)) ? 'door' : 'cabinet';
}

function pickupSound(id, def = {}) {
  const s = `${id} ${def.item ?? ''} ${def.name ?? ''}`.toLowerCase();
  if (/vase|glass|bottle|decanter|tumbler|wine/.test(s)) return 'pickup_glass';
  if (/book/.test(s)) return 'pickup_book';
  if (/flashlight|fuse|battery|key|card|torch|tablet|phone|remote/.test(s)) return 'pickup_metal';
  return 'pickup';
}

// the reactors that make continuous sound, grouped by signal
function groupReactors(reactors) {
  const groups = new Map();
  for (const r of reactors) {
    const s = r.signal ?? '';
    let kind = null;
    if ((r.on.slide || r.on.rotate || r.on.scale) && /blind|shade|curtain|shutter/i.test(s)) kind = 'motor';
    else if ((r.on.slide || r.on.rotate || r.on.scale) && /garage|gate/i.test(s)) kind = 'garage';
    // (secret passage) the library's folding floor: the garage door's heavy motor; the safe wall's doors: a blind's
    else if ((r.on.slide || r.on.rotate) && /^secret_/i.test(s)) kind = 'garage';
    else if ((r.on.slide || r.on.rotate) && /^armory_/i.test(s)) kind = 'motor';
    else if (/^tv/i.test(s) && !r.moves) kind = 'tv';
    else if (/^fire/i.test(s) && r.on.visible !== undefined) kind = 'fire';
    if (!kind) continue;
    const key = `${kind}:${s}`;
    if (!groups.has(key)) groups.set(key, { kind, signal: s, list: [] });
    groups.get(key).list.push(r);
  }
  return [...groups.values()];
}

// how much reverb a room has: by its volume (a double-height stone hall rings, a powder room barely)
function roomWetness(level) {
  const out = {};
  for (const [name, r] of Object.entries(level?.rooms ?? {})) {
    const v = (r.rect[2] - r.rect[0]) * (r.rect[3] - r.rect[1]) * (r.height ?? 4);
    out[name] = Math.min(0.32, Math.max(0.05, 0.05 + 0.11 * Math.log10(Math.max(1, v / 60))));
  }
  if (out.courtyard !== undefined) out.courtyard = 0.04;
  // (secret passage) a room's own reverb level (mansion.json rooms[r].reverb: the concrete tunnels ring)
  for (const [name, r] of Object.entries(level?.rooms ?? {})) if (typeof r.reverb === 'number') out[name] = r.reverb;
  return out;
}

// What the player is walking on: each room's floor (the shell mesh that is its floor slab, by its
// material's name), the rugs (cells of 25 cm under the shell's _Rug meshes), the stair (walnut),
// outdoors the terrace, drive and lawn.
const CELL = 0.25;
export class Surfaces {
  constructor(level, shell) {
    this.rooms = [];
    this.rugs = new Set();
    this.zones = level?.zones ?? {};
    const byRoom = {};
    const names = Object.keys(level?.rooms ?? {}).sort((a, b) => b.length - a.length);
    shell?.updateMatrixWorld(true);
    shell?.traverse((o) => {
      if (!o.isMesh) return;
      if (/_Rug$/.test(o.name)) { this.addRug(o); return; }
      const room = names.find((n) => o.name.startsWith(`Mansion_${n}_`));
      if (room) (byRoom[room] ??= []).push(o);
    });
    for (const [name, r] of Object.entries(level?.rooms ?? {})) {
      // (secret passage) below ground it's concrete (their meshes have left the shell by now: secret_passage.js)
      this.rooms.push({ name, rect: r.rect, floor: r.floor, height: r.height, level: r.level,
                        surface: r.level < 0 ? 'concrete' : floorOf(byRoom[name] ?? [], r.floor) });
    }
    this.rooms.sort((a, b) => b.floor - a.floor);
    // (secret passage) rooms below ground first: the shaft stands inside the den
    this.rooms.sort((a, b) => (a.level < 0 ? 0 : 1) - (b.level < 0 ? 0 : 1));
  }

  addRug(mesh) {
    const g = mesh.geometry, pos = g.attributes.position, idx = g.index, m = mesh.matrixWorld;
    const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3(), n = new THREE.Vector3(), e1 = new THREE.Vector3(), e2 = new THREE.Vector3();
    const tri = new THREE.Triangle(), pt = new THREE.Vector3();
    const count = idx ? idx.count : pos.count;
    for (let i = 0; i + 2 < count; i += 3) {
      const i0 = idx ? idx.getX(i) : i, i1 = idx ? idx.getX(i + 1) : i + 1, i2 = idx ? idx.getX(i + 2) : i + 2;
      a.fromBufferAttribute(pos, i0).applyMatrix4(m); b.fromBufferAttribute(pos, i1).applyMatrix4(m); c.fromBufferAttribute(pos, i2).applyMatrix4(m);
      n.crossVectors(e1.subVectors(b, a), e2.subVectors(c, a));
      if (Math.abs(n.y) < 0.7 * n.length()) continue;          // only the top
      tri.set(a, b, c);
      const lvl = a.y > 2.3 ? 1 : 0;
      const x0 = Math.floor(Math.min(a.x, b.x, c.x) / CELL), x1 = Math.floor(Math.max(a.x, b.x, c.x) / CELL);
      const z0 = Math.floor(Math.min(a.z, b.z, c.z) / CELL), z1 = Math.floor(Math.max(a.z, b.z, c.z) / CELL);
      for (let x = x0; x <= x1; x++) for (let z = z0; z <= z1; z++) {
        pt.set((x + 0.5) * CELL, a.y, (z + 0.5) * CELL);
        tri.closestPointToPoint(pt, e1);
        if (Math.hypot(e1.x - pt.x, e1.z - pt.z) < CELL * 0.5) this.rugs.add(`${x},${z},${lvl}`);
      }
    }
  }

  at(p, onStair = false) {
    const room = this.rooms.find((r) => p.y >= r.floor - 0.5 && p.y <= r.floor + r.height &&
      p.x >= r.rect[0] && p.x <= r.rect[2] && p.z >= r.rect[1] && p.z <= r.rect[3]);
    if (onStair) return room?.level < 0 ? 'concrete' : 'wood';     // (secret passage: the shaft's steel stair)
    if (room) {
      if (p.y < room.floor + 0.12 && this.rugs.has(`${Math.floor(p.x / CELL)},${Math.floor(p.z / CELL)},${p.y > 2.3 ? 1 : 0}`)) return 'rug';
      return p.y > room.floor + 0.25 ? 'wood' : room.surface;     // up on the furniture
    }
    for (const [name, z] of Object.entries(this.zones)) {
      const r = z.rect;
      if (p.x < r[0] || p.x > r[2] || p.z < r[1] || p.z > r[3] || name === 'planting') continue;
      if (/motor_court|drive/.test(name)) return 'gravel';
      if (/terrace/.test(name)) return 'stone';
      if (/tennis/.test(name)) return 'concrete';
    }
    if (Math.abs(p.x) <= 31 && Math.abs(p.z) <= 25) return 'stone';   // the terrace round the house
    return 'grass';
  }
}

// the room's floor: the flat shell mesh at floor level (else the one named like a floor)
function floorOf(meshes, floor) {
  let best = null, bestArea = 0;
  const box = new THREE.Box3();
  for (const o of meshes) {
    if (/_(Art|Rug)$/.test(o.name) || /Plaster|Ceiling|Glass|Light|Mirror|Aluminium/i.test(o.material?.name ?? o.name)) continue;
    box.setFromObject(o);
    if (box.min.y < floor - 0.45 || box.min.y > floor + 0.05 || box.max.y > floor + 0.35) continue;
    const area = (box.max.x - box.min.x) * (box.max.z - box.min.z);
    if (area > bestArea) { best = o; bestArea = area; }
  }
  const name = best?.material?.name ?? meshes.map((o) => o.material?.name ?? '').find((n) => /Floor|Stone|Limestone|Marble|Tile|Paving|Concrete|Rubber/i.test(n)) ?? '';
  return surfaceOf(name);
}

function surfaceOf(material) {
  const m = material.toLowerCase();
  if (/rug|wool|carpet/.test(m)) return 'rug';
  if (/rubber/.test(m)) return 'rubber';
  if (/tile|marble|terrazzo/.test(m)) return 'tile';
  if (/concrete/.test(m)) return 'concrete';
  if (/paving|limestone|stone|slate|granite/.test(m)) return 'stone';
  return 'wood';
}
