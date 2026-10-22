import * as THREE from 'three';

// The invaders' few sounds that the sprite (assets/audio/sfx.mp3, tools/build_audio.py) doesn't
// have yet, made in the browser like audio_synth.js's loops and played through viewer/audio.js's
// buses (its voices, reverb send, wall occlusion). install(sfx) wraps sfx.play: these names play
// here, every other name goes on to the sprite as before. (When the sprite gets real recordings
// of these, delete the entry here: the sprite's wins, see `has`.)
//
//   doorbell     the house's chime (ix_control_panel's noisemaker, signal `doorbell`): a two-tone
//                ding-dong over the house's speakers, so it's heard the same in every room (flat,
//                into the reverb); outside, from the panel, through the glass. The device pulses
//                every 1.3 s while it rings (4 s): one chime takes 2.6 s, so a ring is two chimes.
//   door_knock   knuckles on the front door's glass: three raps (positional)
//   door_kick    a boot against a locked door: a heavy thud and the frame's rattle (positional, loud)
//
// Deterministic (seeded noise), ~0.5 ms to make each buffer, made once on first use.

function rng(seed) {
  let a = seed >>> 0;
  return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

// a struck bar / tubular chime: inharmonic partials with their own decays
function bell(out, sr, at, f0, amp, decay) {
  const parts = [[1, 1, 1], [2.76, 0.42, 0.55], [5.40, 0.22, 0.35], [8.93, 0.08, 0.22], [0.5, 0.12, 1.6]];
  const i0 = Math.floor(at * sr);
  for (const [k, a, dk] of parts) {
    const f = f0 * k, w = 2 * Math.PI * f / sr, tau = decay * dk * sr;
    for (let i = 0; i < out.length - i0; i++) {
      const env = Math.exp(-i / tau) * Math.min(1, i / (0.002 * sr));
      if (env < 1e-4) break;
      out[i0 + i] += amp * a * env * Math.sin(w * i);
    }
  }
}

const MAKE = {
  // ding (E5) - dong (C5), the second a little louder and longer
  doorbell(sr) {
    const out = new Float32Array(Math.floor(sr * 2.6));
    bell(out, sr, 0.0, 659.25, 0.5, 0.9);
    bell(out, sr, 0.62, 523.25, 0.6, 1.25);
    return out;
  },
  // three raps on glass in a door frame: a click, a short glassy ring, a low knock in the frame
  door_knock(sr) {
    const r = rng(7), out = new Float32Array(Math.floor(sr * 1.1));
    for (const [at, a] of [[0, 0.9], [0.21, 0.75], [0.40, 1.0]]) {
      const i0 = Math.floor(at * sr);
      let lp = 0;
      for (let i = 0; i < 0.12 * sr && i0 + i < out.length; i++) {
        const t = i / sr;
        lp += 0.35 * ((r() * 2 - 1) - lp);
        const body = Math.sin(2 * Math.PI * 180 * t) * Math.exp(-t / 0.018) * 0.9;
        const glass = (Math.sin(2 * Math.PI * 2310 * t) * 0.25 + Math.sin(2 * Math.PI * 3720 * t) * 0.12) * Math.exp(-t / 0.03);
        const click = lp * Math.exp(-t / 0.004) * 1.4;
        out[i0 + i] += a * (body + glass + click);
      }
    }
    return out;
  },
  // a kick: a low thump, the frame and lock rattling after it
  door_kick(sr) {
    const r = rng(11), out = new Float32Array(Math.floor(sr * 0.9));
    let lp = 0, lp2 = 0;
    for (let i = 0; i < out.length; i++) {
      const t = i / sr;
      const n = r() * 2 - 1;
      lp += 0.08 * (n - lp); lp2 += 0.5 * (n - lp2);
      const thump = Math.sin(2 * Math.PI * (70 + 40 * Math.exp(-t / 0.03)) * t) * Math.exp(-t / 0.09) * 1.2;
      const crack = lp2 * Math.exp(-t / 0.012) * 0.9;
      const rattle = lp * 6 * Math.exp(-t / 0.18) * (0.6 + 0.4 * Math.sin(2 * Math.PI * 23 * t));
      out[i] = thump + crack + rattle * 0.5;
    }
    return out;
  },
};

// level (dB), distance (ref m; null = flat), whether it's the house's speakers, min gap between plays
const DEFS = {
  doorbell: { db: -6, ref: 6, house: true, gap: 2.55 },
  door_knock: { db: -6, ref: 5, gap: 0.6 },
  door_kick: { db: -2, ref: 9, gap: 0.3 },
};

const _p = new THREE.Vector3();

export function install(sfx, { inHouse = null } = {}) {
  if (!sfx || sfx.__invSynth) return;
  sfx.__invSynth = true;
  const orig = sfx.play.bind(sfx), bufs = {}, last = {};
  const has = (name) => DEFS[name] && !sfx.manifest?.sounds?.[name];
  sfx.synthPlayed = {};          // name -> plays that made sound (tests)
  sfx.play = (name, position = null, opts = {}) => {
    if (!has(name)) return orig(name, position, opts);
    const D = DEFS[name];
    const pos = position == null ? null : position.isVector3 ? position : Array.isArray(position) ? _p.set(...position) : _p.set(position.x, position.y ?? 0, position.z);
    const entry = { t: Math.round(performance.now()), name, synth: true };
    if (pos) entry.pos = [+pos.x.toFixed(2), +pos.y.toFixed(2), +pos.z.toFixed(2)];
    sfx.log.push(entry);
    if (sfx.log.length > 500) sfx.log.shift();
    sfx.counts[name] = (sfx.counts[name] || 0) + 1;
    // the house's chime: the same in every room (a speaker in each); from outside, from the panel
    const eye = sfx.camera.position;
    const inside = D.house && (inHouse ? inHouse(eye) : true);
    const spatial = !!pos && !inside;
    entry.flat = !spatial;
    const now = performance.now() / 1000;
    if (now - (last[name] ?? -1e9) < D.gap) { entry.muted = 'repeat'; return null; }
    last[name] = now;
    const c = sfx.ctx;
    if (!c || c.state !== 'running' || window.__bench) { entry.muted = true; return null; }
    if (!bufs[name]) {
      const data = MAKE[name](c.sampleRate);
      let peak = 0;
      for (const v of data) peak = Math.max(peak, Math.abs(v));
      for (let i = 0; i < data.length; i++) data[i] /= peak || 1;
      const b = c.createBuffer(1, data.length, c.sampleRate);
      b.copyToChannel(data, 0);
      bufs[name] = b;
    }
    const v = sfx.voice(spatial ? sfx.voices : sfx.flat, spatial, 2);
    if (!v) { entry.muted = 'busy'; return null; }
    const src = c.createBufferSource();
    src.buffer = bufs[name];
    src.playbackRate.value = (opts.rate ?? 1) * (1 + (Math.random() * 2 - 1) * (D.house ? 0 : 0.04));
    let g = Math.pow(10, (D.db + (opts.db ?? 0)) / 20) * (opts.gain ?? 1), cutoff = 20000, wet = D.house ? 0.55 : 1;
    if (spatial) {
      const walls = sfx.occlusion(pos);
      g *= [1, 0.5, 0.3, 0.2][walls];
      cutoff = [20000, 2200, 1000, 550][walls];
      v.panner.panningModel = 'equalpower';
      v.panner.refDistance = D.ref; v.panner.rolloffFactor = 1;
      if (v.panner.positionX) { v.panner.positionX.value = pos.x; v.panner.positionY.value = pos.y; v.panner.positionZ.value = pos.z; }
      else v.panner.setPosition(pos.x, pos.y, pos.z);
      wet *= Math.min(1, Math.sqrt(D.ref / Math.max(D.ref, eye.distanceTo(pos))) * 1.2);
    }
    const t = c.currentTime + (opts.delay ?? 0);
    v.gain.gain.setValueAtTime(g, c.currentTime);
    v.filter.frequency.setValueAtTime(cutoff, c.currentTime);
    v.sendGain.gain.setValueAtTime(wet, c.currentTime);
    src.connect(v.gain);
    src.start(t);
    v.src = src; v.busy = true; v.prio = 2; v.started = t; v.name = name;
    v.ends = t + src.buffer.duration / src.playbackRate.value;
    src.onended = () => { if (v.src === src) { v.busy = false; v.src = null; } };
    sfx.synthPlayed[name] = (sfx.synthPlayed[name] || 0) + 1;
    return v;
  };
  // (the sprite doesn't list these: not unknown)
  for (const n of Object.keys(DEFS)) sfx.unknown?.delete(n);
}

export const SYNTH_SOUNDS = Object.keys(DEFS);
