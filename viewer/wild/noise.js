// Seeded noise for the synthetic wilderness (the real terrain comes from the terrain
// generator; this only has to look plausible and be deterministic, so benchmarks repeat).

export function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// 2D gradient (Perlin) noise, ~[-1, 1]
export function makeNoise(seed) {
  const r = rng(seed);
  const p = new Uint8Array(512);
  const perm = [...Array(256).keys()];
  for (let i = 255; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [perm[i], perm[j]] = [perm[j], perm[i]]; }
  for (let i = 0; i < 512; i++) p[i] = perm[i & 255];
  const gx = new Float32Array(16), gy = new Float32Array(16);
  for (let i = 0; i < 16; i++) { const a = (i / 16) * Math.PI * 2; gx[i] = Math.cos(a); gy[i] = Math.sin(a); }

  function perlin(x, y) {
    const xi = Math.floor(x), yi = Math.floor(y);
    const xf = x - xi, yf = y - yi;
    const X = xi & 255, Y = yi & 255;
    const u = xf * xf * xf * (xf * (xf * 6 - 15) + 10);
    const v = yf * yf * yf * (yf * (yf * 6 - 15) + 10);
    const aa = p[p[X] + Y] & 15, ab = p[p[X] + Y + 1] & 15;
    const ba = p[p[X + 1] + Y] & 15, bb = p[p[X + 1] + Y + 1] & 15;
    const n00 = gx[aa] * xf + gy[aa] * yf;
    const n10 = gx[ba] * (xf - 1) + gy[ba] * yf;
    const n01 = gx[ab] * xf + gy[ab] * (yf - 1);
    const n11 = gx[bb] * (xf - 1) + gy[bb] * (yf - 1);
    const x1 = n00 + u * (n10 - n00), x2 = n01 + u * (n11 - n01);
    return (x1 + v * (x2 - x1)) * 1.41;
  }
  function fbm(x, y, oct = 5, lac = 2.0, gain = 0.5) {
    let s = 0, a = 1, f = 1, n = 0;
    for (let i = 0; i < oct; i++) { s += a * perlin(x * f + i * 17.3, y * f - i * 9.1); n += a; a *= gain; f *= lac; }
    return s / n;
  }
  // ridged multifractal: sharp crests, ~[0, 1]
  function ridged(x, y, oct = 5, lac = 2.0, gain = 0.5) {
    let s = 0, a = 1, f = 1, n = 0, w = 1;
    for (let i = 0; i < oct; i++) {
      let v = 1 - Math.abs(perlin(x * f + i * 31.7, y * f + i * 11.9));
      v *= v * w;
      w = Math.min(1, Math.max(0, v * 2));
      s += a * v; n += a; a *= gain; f *= lac;
    }
    return s / n;
  }
  return { perlin, fbm, ridged };
}

export const smoothstep = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
export const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
