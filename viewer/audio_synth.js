// Procedural sound for viewer/audio.js: the continuous loops and the reverb's impulse response,
// made in the browser (nothing to download, and they loop seamlessly, which MP3 can't).
//
//   LOOPS[name](sampleRate) -> [Float32Array, ...] (one per channel), each a whole number of
//   seconds long and periodic: the tail is cross-faded into the head, every slow modulation
//   completes whole cycles. RMS-normalised to ~-16 dBFS; audio.js sets how loud each plays.
//   reverbIR(sampleRate, seconds) -> [left, right]: decaying, darkening noise.
//
// Deterministic (seeded): the same buffers every load.

function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const gauss = (r) => (r() * 2 - 1) * 1.73;   // white noise, unit variance (filtered, so uniform will do)

// RBJ biquad (direct form I); set() may be called while running (time-varying filters)
class Biquad {
  constructor(sr) { this.sr = sr; this.x1 = this.x2 = this.y1 = this.y2 = 0; }
  set(type, f, q = 0.707) {
    const w = 2 * Math.PI * Math.min(f, this.sr * 0.45) / this.sr, c = Math.cos(w), al = Math.sin(w) / (2 * q);
    let b0, b1, b2;
    if (type === 'lp') { b0 = (1 - c) / 2; b1 = 1 - c; b2 = b0; }
    else if (type === 'hp') { b0 = (1 + c) / 2; b1 = -(1 + c); b2 = b0; }
    else { b0 = al; b1 = 0; b2 = -al; }     // band-pass, 0 dB peak
    const a0 = 1 + al;
    this.b0 = b0 / a0; this.b1 = b1 / a0; this.b2 = b2 / a0; this.a1 = -2 * c / a0; this.a2 = (1 - al) / a0;
    return this;
  }
  tick(x) {
    const y = this.b0 * x + this.b1 * this.x1 + this.b2 * this.x2 - this.a1 * this.y1 - this.a2 * this.y2;
    this.x2 = this.x1; this.x1 = x; this.y2 = this.y1; this.y1 = y;
    return y;
  }
}

// make `buf` (length L + F) loop over L samples: its last F samples cross-fade into its first F
function periodic(buf, L) {
  const F = buf.length - L, out = new Float32Array(L);
  for (let i = 0; i < L; i++) out[i] = buf[i];
  for (let i = 0; i < F; i++) {
    const k = i / F;
    out[i] = buf[i] * Math.sin(0.5 * Math.PI * k) + buf[L + i] * Math.cos(0.5 * Math.PI * k);
  }
  return out;
}

// the other ear hears the same loop half a period later: wide, and half the work
function stereo(c) {
  const n = c.length, h = n >> 1, r = new Float32Array(n);
  r.set(c.subarray(h), 0); r.set(c.subarray(0, h), n - h);
  return [c, r];
}

function normalise(chs, rms = 0.16) {
  let s = 0, n = 0, pk = 0;
  for (const c of chs) for (const v of c) { s += v * v; n++; pk = Math.max(pk, Math.abs(v)); }
  const g = Math.min(rms / Math.sqrt(s / n || 1), 0.89 / (pk || 1));   // peaks <= -1 dBFS
  for (const c of chs) for (let i = 0; i < c.length; i++) c[i] *= g;
  return chs;
}

// a slow wobble with whole cycles over `T` s: sum of sines at k/T Hz
function wobble(r, T, ks) {
  const parts = ks.map((k) => ({ f: k / T, p: r() * 2 * Math.PI, a: 0.5 + r() * 0.5 }));
  const norm = parts.reduce((s, q) => s + q.a, 0);
  return (t) => parts.reduce((s, q) => s + q.a * Math.sin(2 * Math.PI * q.f * t + q.p), 0) / norm;
}

// outdoor wind: a low rumble and a band of air whose pitch and level rise with the gusts
function wind(sr, T = 16, seed = 1) {
  const L = T * sr, F = sr, chs = [];
  for (let ch = 0; ch < 1; ch++) {
    const r = rng(seed + ch * 101), gust = wobble(rng(seed), T, [1, 2, 3, 5, 7]);
    const lo1 = new Biquad(sr).set('lp', 220), lo2 = new Biquad(sr).set('lp', 220);
    const band = new Biquad(sr), band2 = new Biquad(sr), out = new Float32Array(L + F);
    let g = 0;
    for (let i = 0; i < L + F; i++) {
      if (i % 64 === 0) {
        g = 0.5 + 0.5 * gust((i % L) / sr);
        band.set('bp', 350 + 650 * g * g, 0.9); band2.set('bp', 1600 + 1400 * g, 2.5);
      }
      const w = gauss(r);
      const rumble = lo2.tick(lo1.tick(w)) * 2.2;
      const air = band.tick(w) * (0.25 + 0.9 * g * g) + band2.tick(w) * 0.12 * g * g * g;
      out[i] = rumble * (0.6 + 0.6 * g) + air;
    }
    chs.push(periodic(out, L));
  }
  return normalise(stereo(chs[0]));
}

// interior room tone without the electrics: still air, faint and low (stereo)
function air(sr, T = 8, seed = 2) {
  const L = T * sr, F = sr / 2, chs = [];
  for (let ch = 0; ch < 1; ch++) {
    const r = rng(seed + ch * 31), lo1 = new Biquad(sr).set('lp', 140), lo2 = new Biquad(sr).set('lp', 140);
    const hv = new Biquad(sr).set('bp', 520, 0.8), out = new Float32Array(L + F);
    for (let i = 0; i < L + F; i++) {
      const w = gauss(r);
      out[i] = lo2.tick(lo1.tick(w)) * 3 + hv.tick(w) * 0.05;
    }
    chs.push(periodic(out, L));
  }
  return normalise(stereo(chs[0]));
}

// the house's electrics: mains hum and its harmonics, a faint ventilation whine (mono). Every
// frequency is a whole number of cycles in T, so it loops without a seam
function hum(sr, T = 2, seed = 3) {
  const L = T * sr, out = new Float32Array(L), wob = wobble(rng(seed), T, [1, 3]);
  const parts = [[50, 0.35], [100, 1.0], [150, 0.4], [200, 0.25], [300, 0.12], [1250, 0.02]];
  let w = 1;
  for (let i = 0; i < L; i++) {
    const t = i / sr;
    if (i % 64 === 0) w = 0.85 + 0.15 * wob(t);
    let s = 0;
    for (const [f, a] of parts) s += a * Math.sin(2 * Math.PI * f * t);
    out[i] = s * w;
  }
  return normalise([out]);
}

// an electric motor (blinds; the garage door plays it slower): a buzzy fundamental with its
// harmonics, gear noise and a faint whine, a little uneven (mono, 2 s)
function motor(sr, T = 2, seed = 4) {
  const L = T * sr, F = sr / 4, r = rng(seed), out = new Float32Array(L + F);
  const gear = new Biquad(sr).set('bp', 2400, 1.2), lo = new Biquad(sr).set('lp', 1800);
  for (let i = 0; i < L + F; i++) {
    const t = (i % L) / sr;
    let s = 0;
    for (let k = 1; k <= 14; k++) s += Math.sin(2 * Math.PI * 110 * k * t) / k;
    const am = 1 + 0.12 * Math.sin(2 * Math.PI * 6 * t) + 0.05 * Math.sin(2 * Math.PI * 17 * t);
    out[i] = lo.tick(s * 0.5 * am) + gear.tick(gauss(r)) * 0.18 * am + Math.sin(2 * Math.PI * 880 * t) * 0.03;
  }
  return normalise([periodic(out, L)]);
}

// a TV in another room: unintelligible voices (formant-filtered pulse trains, syllable by
// syllable, two speakers) over a soft music bed, through a small speaker (mono, 12 s)
function tv(sr, T = 12, seed = 5) {
  const L = T * sr, F = sr / 2, r = rng(seed), out = new Float32Array(L + F);
  const V = [[730, 1090, 2440], [530, 1840, 2480], [270, 2290, 3010], [570, 840, 2410], [300, 870, 2240], [660, 1720, 2410]];
  const fm = [0, 1, 2].map(() => new Biquad(sr)), fric = new Biquad(sr).set('bp', 5000, 1.5);
  const spk1 = new Biquad(sr).set('hp', 200), spk2 = new Biquad(sr).set('lp', 4500);
  let i = 0, phase = 0, speaker = 0;
  while (i < L + F) {
    // a sentence: 4-12 syllables, then a pause; speakers take turns
    if (r() < 0.45) speaker = 1 - speaker;
    const f0base = speaker ? 205 : 118, syl = 4 + Math.floor(r() * 9);
    for (let s = 0; s < syl && i < L + F; s++) {
      const voicedSyl = r() < 0.8, d = Math.floor(sr * (0.09 + r() * 0.2)), v = V[Math.floor(r() * V.length)];
      fm.forEach((b, k) => b.set('bp', v[k] * (speaker ? 1.15 : 1), 6 + 4 * k));
      const rise = (r() - 0.5) * 0.3, att = sr * 0.02, rel = sr * 0.035;
      for (let j = 0; j < d && i < L + F; j++, i++) {
        const e = Math.min(1, j / att, (d - j) / rel);
        let x = 0;
        if (voicedSyl) {
          const f0 = f0base * (1 + rise * j / d) * (1 - 0.1 * s / syl);
          phase += f0 / sr;
          const pulse = phase >= 1 ? (phase -= 1, 1) : 0;
          x = fm[0].tick(pulse) * 1.0 + fm[1].tick(pulse) * 0.6 + fm[2].tick(pulse) * 0.3;
          x *= 6;
        } else x = fric.tick(gauss(r)) * 0.5;
        out[i] += x * e;
      }
      if (r() < 0.25) i += Math.floor(sr * (0.04 + r() * 0.12));   // a gap between words
    }
    i += Math.floor(sr * (0.25 + r() * 0.6));                       // between sentences
  }
  // the music bed: a slow pad (chords change every 3 s; whole cycles over T)
  const chords = [[220, 277.2, 329.6], [196, 246.9, 293.7], [174.6, 220, 261.6], [196, 246.9, 329.6]];
  for (let n = 0; n < L + F; n++) {
    const t = (n % L) / sr, c = chords[Math.floor(t / 3) % 4];
    const k = (t % 3) / 3, e = Math.min(1, k / 0.15, (1 - k) / 0.15);
    let s = 0;
    for (const f of c) s += Math.sin(2 * Math.PI * f * t);
    out[n] += s * 0.05 * e;
  }
  for (let n = 0; n < L + F; n++) out[n] = spk2.tick(spk1.tick(out[n]));
  return normalise([periodic(out, L)]);
}

// a gas fire: the soft roar of the burners and the odd tick of the heating stones (mono, 8 s)
function fire(sr, T = 8, seed = 6) {
  const L = T * sr, F = sr / 2, r = rng(seed), out = new Float32Array(L + F);
  const roar1 = new Biquad(sr).set('lp', 380), roar2 = new Biquad(sr).set('bp', 900, 0.6), wob = wobble(rng(seed), T, [3, 5, 11, 17]);
  const tick = new Biquad(sr).set('bp', 3200, 2);
  let next = 0, tickLeft = 0, tickAmp = 0;
  let g = 1;
  for (let i = 0; i < L + F; i++) {
    if (i % 64 === 0) g = 0.75 + 0.25 * wob((i % L) / sr);
    const w = gauss(r);
    let x = roar1.tick(w) * 1.6 * g + roar2.tick(w) * 0.25 * g;
    if (i >= next) { next = i + Math.floor(sr * (0.15 + r() * 0.9)); tickLeft = Math.floor(sr * (0.001 + r() * 0.004)); tickAmp = 0.5 + r() * 2.5; }
    if (tickLeft > 0) { x += tick.tick(gauss(r) * tickAmp); tickLeft--; } else x += tick.tick(0);
    out[i] += x;
  }
  return normalise([periodic(out, L)]);
}
export const LOOPS = { wind, air, hum, motor, tv, fire };

// a room's reverb: exponentially decaying noise that darkens as it decays (stereo)
export function reverbIR(sr, seconds = 1.8, seed = 9) {
  const n = Math.floor(sr * seconds), pre = Math.floor(sr * 0.012), chs = [];
  const tau = seconds / 6.9;                       // RT60 = seconds
  for (let ch = 0; ch < 2; ch++) {
    const r = rng(seed + ch), out = new Float32Array(n);
    let y = 0;
    for (let i = pre; i < n; i++) {
      const t = (i - pre) / sr, k = Math.exp(-t / tau);
      const cut = 9000 * Math.exp(-t / (seconds * 0.35)) + 900;     // the highs die first
      const a = Math.exp(-2 * Math.PI * cut / sr);
      y = (1 - a) * gauss(r) + a * y;
      out[i] = y * k;
    }
    chs.push(out);
  }
  // unit energy, so the wet level is the send's gain
  let e = 0;
  for (const c of chs) for (const v of c) e += v * v;
  const g = 1 / Math.sqrt(e / 2);
  for (const c of chs) for (let i = 0; i < n; i++) c[i] *= g;
  return chs;
}
