import * as THREE from 'three';
import { ATMOSPHERE_PARS } from './atmosphere.js';
import { rng } from './noise.js';
import { fetchPNG } from './png.js';

// The wilderness water (a generated level, load_world.js worlds): the Laurel River, Laurel Fork,
// the plunge pool, the falls, the mist, and the water-query API the player uses.
//   await prepareWater(world)          the level's water data (world.json "water_fx": current, foam,
//                                      standing waves, the skyline the surface reflects, bed kind;
//                                      blender/wilderness/levels/laurel_fork_water.py), if it has any
//   waterField(world)                  the CPU field (surfaceAt / depthAt / flowAt / wet), cached
//   buildWater(world, uniforms, tex)   the meshes: the water surface, the falls sheet, the mist (3 draws)
//   waterWetTexture(world)             the terrain's wet banks / cobble bars mask (main.js tex.wet)
// Contract: design/wilderness/blue_ridge/water.md. Coordinates: terrain-local three.js metres
// (x east, y up, z = -(estate y + 810)), as world.heightAt. No lights, no extra passes: the
// surface reflects the sky or the skyline baked per vertex (8 directions), its bed is the cobble
// scan seen through tea-green water absorbed by depth, the current is flow-mapped noise.

// ---------------------------------------------------------------- the level's water data
export async function prepareWater(world) {
  const fx = world.meta?.water_fx;
  if (!fx || world.waterFx) return world.waterFx || null;
  const dir = `../build/wilderness/${world.name}/world/`;
  let f, e, a;
  try { [f, e, a] = await Promise.all([fx.flow, fx.env, fx.aux].map((n) => fetchPNG(dir + n))); } catch (err) { console.warn('water fx:', err.message); return null; }
  const n = world.res * world.res, vm = fx.vmax / 127;
  const vx = new Float32Array(n), vz = new Float32Array(n), foam = new Float32Array(n), wave = new Float32Array(n);
  const phase = new Float32Array(n), bedrock = new Float32Array(n), env = new Uint8Array(n * 8);
  for (let k = 0; k < n; k++) {
    vx[k] = (f.data[k * 4] - 128) * vm; vz[k] = (f.data[k * 4 + 1] - 128) * vm;
    foam[k] = f.data[k * 4 + 2] / 255; wave[k] = f.data[k * 4 + 3] / 255;
    for (let c = 0; c < 4; c++) { const v = e.data[k * 4 + c]; env[k * 8 + c * 2] = v >> 8; env[k * 8 + c * 2 + 1] = v & 255; }
    phase[k] = a.data[k * 2] / fx.phase_scale; bedrock[k] = a.data[k * 2 + 1] / 65535;
  }
  world.waterFx = { vx, vz, foam, wave, phase, bedrock, env };
  return world.waterFx;
}

// ---------------------------------------------------------------- the query API
export function waterField(world) {
  if (world.waterField) return world.waterField;
  const { res, spacing, size, water } = world, half = size / 2, n = res * res;
  const fx = world.waterFx || null;
  // per-cell current (m/s): the level's baked field (water_flow.png) or, without it, down the
  // water surface's slope (over 2 cells each way), faster where it's steeper
  let vx = fx?.vx, vz = fx?.vz;
  if (!vx) {
    vx = new Float32Array(n); vz = new Float32Array(n);
    const lvl = (i, j) => water[Math.min(res - 1, Math.max(0, i)) + Math.min(res - 1, Math.max(0, j)) * res];
    for (let j = 0; j < res; j++) for (let i = 0; i < res; i++) {
      const k = i + j * res, h = water[k];
      if (!Number.isFinite(h)) continue;
      const at = (a, b) => { const v = lvl(a, b); return Number.isFinite(v) ? v : h; };
      const hx = at(i + 2, j) - at(i - 2, j), hz = at(i, j + 2) - at(i, j - 2), L = Math.hypot(hx, hz);
      if (L < 1e-6) continue;
      const sp = Math.min(6, 0.4 + 30 * L / (4 * spacing));
      vx[k] = -hx / L * sp; vz[k] = -hz / L * sp;
    }
  }
  const cellOf = (x, z) => {
    const fx_ = (x + half) / spacing, fz = (z + half) / spacing;
    if (fx_ < 0 || fz < 0 || fx_ >= res - 1 || fz >= res - 1) return null;
    const i = Math.floor(fx_), j = Math.floor(fz);
    return [i + j * res, fx_ - i, fz - j];
  };
  // the surface exactly as the mesh draws it: a quad for every cell with >= 2 wet corners (a dry
  // corner takes the wet ones' mean), split along its (i+1, j)-(i, j+1) diagonal
  const surfaceAt = (x, z) => {
    const c = cellOf(x, z);
    if (!c) return NaN;
    const [k, u, v] = c;
    let a = water[k], b = water[k + 1], d = water[k + res], e = water[k + res + 1];
    let m = 0, w = 0;
    for (const h of [a, b, d, e]) if (Number.isFinite(h)) { m += h; w++; }
    if (w < 2) return NaN;
    m /= w;
    if (!Number.isFinite(a)) a = m; if (!Number.isFinite(b)) b = m; if (!Number.isFinite(d)) d = m; if (!Number.isFinite(e)) e = m;
    return u + v <= 1 ? a + (b - a) * u + (d - a) * v : e + (d - e) * (1 - u) + (b - e) * (1 - v);
  };
  const depthAt = (x, z) => {
    const s = surfaceAt(x, z);
    return Number.isFinite(s) ? Math.max(0, s - world.heightAt(x, z)) : 0;
  };
  const flowAt = (x, z, out = { x: 0, z: 0, speed: 0 }) => {
    out.x = 0; out.z = 0; out.speed = 0;
    const c = cellOf(x, z);
    if (!c || !(depthAt(x, z) > 0.02)) return out;
    const [k, u, v] = c;
    let sx = 0, sz = 0, sw = 0;
    for (const [kk, w] of [[k, (1 - u) * (1 - v)], [k + 1, u * (1 - v)], [k + res, (1 - u) * v], [k + res + 1, u * v]]) {
      if (!Number.isFinite(water[kk])) continue;
      sx += vx[kk] * w; sz += vz[kk] * w; sw += w;
    }
    if (sw > 0) { out.x = sx / sw; out.z = sz / sw; out.speed = Math.hypot(out.x, out.z); }
    return out;
  };
  const wet = (x, z) => depthAt(x, z) > 0.02;
  world.waterField = { surfaceAt, depthAt, flowAt, wet, vx, vz, fx };
  return world.waterField;
}

// ---------------------------------------------------------------- shared noise
// One tileable 256² RGBA8 texture, made once (no download): rg = the slope of a 4-octave noise
// (the ripples' normals), b = foam (bubbly cells broken by noise), a = a soft low-frequency noise
let NOISE = null;
function noiseTexture() {
  if (NOISE) return NOISE;
  const N = 256, r = rng(91), data = new Uint8Array(N * N * 4);
  const grid = (c) => { const g = new Float32Array(c * c); for (let i = 0; i < g.length; i++) g[i] = r(); return g; };
  const octs = [4, 8, 16, 32].map((c) => ({ c, g: grid(c) }));
  const low = { c: 4, g: grid(4) };
  const vnoise = (o, x, y) => {             // periodic value noise, x, y in [0, 1)
    const fx = x * o.c, fy = y * o.c, i = Math.floor(fx), j = Math.floor(fy);
    let u = fx - i, v = fy - j; u = u * u * (3 - 2 * u); v = v * v * (3 - 2 * v);
    const at = (a, b) => o.g[((a % o.c) + o.c) % o.c + (((b % o.c) + o.c) % o.c) * o.c];
    return (at(i, j) * (1 - u) + at(i + 1, j) * u) * (1 - v) + (at(i, j + 1) * (1 - u) + at(i + 1, j + 1) * u) * v;
  };
  const h = new Float32Array(N * N);
  for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
    let s = 0, a = 1;
    for (const o of octs) { s += vnoise(o, x / N, y / N) * a; a *= 0.55; }
    h[x + y * N] = s;
  }
  // foam cells: 14 x 14 jittered points per tile, 1 - F1 (bubbles), times a breakup noise
  const C = 14, pts = [];
  for (let j = 0; j < C; j++) for (let i = 0; i < C; i++) pts.push([(i + r()) / C, (j + r()) / C, 0.6 + 0.4 * r()]);
  for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
    const k = x + y * N;
    const dx = (h[((x + 1) % N) + y * N] - h[((x + N - 1) % N) + y * N]) * N / 2, dy = (h[x + ((y + 1) % N) * N] - h[x + ((y + N - 1) % N) * N]) * N / 2;
    data[k * 4] = Math.max(0, Math.min(255, 128 + dx * 1.6));
    data[k * 4 + 1] = Math.max(0, Math.min(255, 128 + dy * 1.6));
    const px = x / N, py = y / N, ci = Math.floor(px * C), cj = Math.floor(py * C);
    let f1 = 9, wgt = 1;
    for (let b = -1; b <= 1; b++) for (let a = -1; a <= 1; a++) {
      const ii = (ci + a + C) % C, jj = (cj + b + C) % C, p = pts[ii + jj * C];
      let ex = p[0] + Math.floor((ci + a) / C) * 1 - px, ey = p[1] + Math.floor((cj + b) / C) * 1 - py;
      const d = Math.hypot(ex, ey) * C / p[2];
      if (d < f1) { f1 = d; wgt = p[2]; }
    }
    const bub = Math.max(0, 1 - f1) ** 0.7 * wgt;
    data[k * 4 + 2] = Math.round(Math.min(1, bub * 0.75 + (vnoise(octs[2], px, py) - 0.3) * 0.45) * 255);
    data[k * 4 + 3] = Math.round((vnoise(low, px, py) * 0.65 + vnoise(octs[0], px, py) * 0.35) * 255);
  }
  const t = new THREE.DataTexture(data, N, N, THREE.RGBAFormat);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.generateMipmaps = true; t.minFilter = THREE.LinearMipmapLinearFilter; t.magFilter = THREE.LinearFilter;
  t.needsUpdate = true; t.name = 'water_noise';
  NOISE = t;
  return t;
}

// distance (m) from every wet cell to the nearest dry one (chamfer, two passes)
function bankDistance(world) {
  const { res, spacing, water } = world, n = res * res, d = new Float32Array(n);
  for (let k = 0; k < n; k++) d[k] = Number.isFinite(water[k]) ? 1e9 : 0;
  const a = spacing, b = spacing * Math.SQRT2;
  const relax = (k, kk, s) => { const v = d[kk] + s; if (v < d[k]) d[k] = v; };
  for (let j = 1; j < res - 1; j++) for (let i = 1; i < res - 1; i++) {
    const k = i + j * res; if (!d[k]) continue;
    relax(k, k - 1, a); relax(k, k - res, a); relax(k, k - res - 1, b); relax(k, k - res + 1, b);
  }
  for (let j = res - 2; j > 0; j--) for (let i = res - 2; i > 0; i--) {
    const k = i + j * res; if (!d[k]) continue;
    relax(k, k + 1, a); relax(k, k + res, a); relax(k, k + res + 1, b); relax(k, k + res - 1, b);
  }
  return d;
}

// ---------------------------------------------------------------- the surface
// One mesh over every wet cell of the water raster (the Laurel River, Laurel Fork, the plunge pool)
// plus the river's ribbon beyond the square (world.river.out, down the valley to the town). Per
// vertex: the current (m/s), depth, foam potential, standing-wave strength and phase, the skyline in
// 8 directions, bedrock, the distance to the bank. What a pixel shows:
//   the bed through the water: the cobble scan (gold-brown, wet; grey gneiss on the bedrock shelves;
//     silted and green in the pools), refracted by the ripples, sun caustics in the sunlit shallows,
//     absorbed along the view path (tea-green: red goes first, then blue) toward the water's own
//     green-brown, so riffles read clear over cobbles and pools deep green
//   reflection (Fresnel): the sky above the skyline in the reflected direction, the gorge's forest
//     below it (lit on the side the sun reaches), so the banks' trees mirror along the edges and the
//     open sky down the middle of the reach
//   the current: two layers of ripple and foam noise advected along the flow and cross-faded
//     (flow map), each place on its own phase; rougher and quicker where the water runs fast
//   standing waves: stationary crests across the tongue below each drop (phase from the generator)
//   white water: the generator's foam potential (rapids, ledges, supercritical riffles, the rocks'
//     pillows, eddy lines and wakes, carried downstream as foam lines) thresholds bubbly foam cells,
//     broken into tongues by a slow breakup noise
//   sun glints: the low sun's specular on the ripples, where the light map has sun
export function buildWater(world, uniforms, tex) {
  const { res, spacing, size, water, heights } = world, half = size / 2;
  const fx = world.waterFx;
  const bank = bankDistance(world);
  const P = [], FL = [], FX = [], E0 = [], E1 = [], MI = [], idx = [];
  const vid = new Int32Array(res * res).fill(-1);
  const lvl = (i, j) => water[i + j * res];
  const vert = (i, j, h) => {
    const k = i + j * res;
    if (vid[k] >= 0) return vid[k];
    vid[k] = P.length / 3;
    P.push(-half + i * spacing, h, -half + j * spacing);
    const d = Math.max(0, h - heights[k]);
    if (fx) {
      FL.push(fx.vx[k], fx.vz[k]);
      FX.push(d, fx.foam[k], fx.wave[k], fx.phase[k]);
      E0.push(fx.env[k * 8], fx.env[k * 8 + 1], fx.env[k * 8 + 2], fx.env[k * 8 + 3]);
      E1.push(fx.env[k * 8 + 4], fx.env[k * 8 + 5], fx.env[k * 8 + 6], fx.env[k * 8 + 7]);
      MI.push(fx.bedrock[k], Math.min(bank[k], 60));
    } else {
      // (no generator data: down the surface's slope, white where it steepens)
      const at = (a, b) => { const v = lvl(Math.min(res - 1, Math.max(0, a)), Math.min(res - 1, Math.max(0, b))); return Number.isFinite(v) ? v : h; };
      const hx = at(i + 2, j) - at(i - 2, j), hz = at(i, j + 2) - at(i, j - 2), L = Math.hypot(hx, hz) + 1e-6, g = L / (4 * spacing);
      const sp = Math.min(6, 0.4 + 30 * g);
      FL.push(-hx / L * sp, -hz / L * sp);
      FX.push(d, Math.min(1, Math.max(0, (g - 0.03) / 0.09)), 0, 0);
      E0.push(30, 30, 30, 30); E1.push(30, 30, 30, 30);
      MI.push(0, Math.min(bank[k], 60));
    }
    return vid[k];
  };
  for (let j = 0; j < res - 1; j++) for (let i = 0; i < res - 1; i++) {
    const c = [lvl(i, j), lvl(i + 1, j), lvl(i, j + 1), lvl(i + 1, j + 1)];
    const wet = c.filter(Number.isFinite);
    if (wet.length < 2) continue;
    const mean = wet.reduce((a, b) => a + b, 0) / wet.length;
    const h = c.map((v) => (Number.isFinite(v) ? v : mean));
    const a = vert(i, j, h[0]), b = vert(i + 1, j, h[1]), d = vert(i, j + 1, h[2]), e = vert(i + 1, j + 1, h[3]);
    idx.push(a, d, b, b, d, e);
  }
  // the river beyond the square: a ribbon down the ring's valley floor (estate frame -> three)
  const oy = world.meta.estate_offset[1], out = world.meta.river?.out;
  if (out?.length > 1) {
    const base = P.length / 3;
    out.forEach((q, n) => {
      const a = out[Math.max(0, n - 1)], b = out[Math.min(out.length - 1, n + 1)];
      const dx = b[0] - a[0], dz = -(b[1] - a[1]), L = Math.hypot(dx, dz) || 1;
      const sx = -dz / L, sz = dx / L, w = q[3] / 2;
      const x = q[0], z = -(q[1] - oy), y = q[2];
      const g = Math.abs(b[2] - a[2]) / Math.max(1, Math.hypot(b[0] - a[0], b[1] - a[1]));
      const sp = 0.6 + 20 * g;
      for (const sd of [-1, 1]) {
        P.push(x + sx * w * sd, y, z + sz * w * sd); FL.push(dx / L * sp, dz / L * sp); FX.push(1.8, Math.min(1, g * 8), 0, 0);
        E0.push(22, 22, 22, 22); E1.push(22, 22, 22, 22); MI.push(0, 6);
      }
    });
    for (let n = 0; n < out.length - 1; n++) { const a = base + n * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
  g.setAttribute('aFlow', new THREE.Float32BufferAttribute(FL, 2));
  g.setAttribute('aFx', new THREE.Float32BufferAttribute(FX, 4));
  g.setAttribute('aEnv0', new THREE.BufferAttribute(new Uint8Array(E0), 4, true));
  g.setAttribute('aEnv1', new THREE.BufferAttribute(new Uint8Array(E1), 4, true));
  g.setAttribute('aMisc', new THREE.Float32BufferAttribute(MI, 2));
  g.setIndex(idx);
  g.computeVertexNormals();              // (the surface's own slope: the cascade and the ledges tilt)
  g.computeBoundingSphere();
  const falls = world.props.authored.find((p) => p.kind === 'falls');
  const fb = falls ? new THREE.Vector3(falls.x1, falls.z1, -(falls.y1 - oy)) : new THREE.Vector3(0, -1e4, 0);
  const mat = new THREE.ShaderMaterial({
    uniforms: { ...uniforms, uLight: { value: tex.light }, uMapXf: { value: new THREE.Vector4(-half, -half, 1 / size, 1) },
      uZenithW: { value: new THREE.Color(...(world.skyMeta?.zenith || [0.2, 0.33, 0.66])) },
      tBed: { value: tex.bed || tex.scree }, uBedTile: { value: tex.bedTile || 1.8 }, uFallsBase: { value: fb },
      tNoise: { value: noiseTexture() }, uDetail: { value: 1 } },
    vertexShader: /* glsl */`
      attribute vec2 aFlow, aMisc;
      attribute vec4 aFx, aEnv0, aEnv1;
      varying vec3 vWorld;
      varying vec2 vFlow, vMisc;
      varying vec4 vFx, vEnv0, vEnv1;
      varying vec3 vNg;
      void main() {
        vec4 w = modelMatrix * vec4(position, 1.0);
        vNg = normal;
        vWorld = w.xyz; vFlow = aFlow; vFx = aFx; vEnv0 = aEnv0; vEnv1 = aEnv1; vMisc = aMisc;
        gl_Position = projectionMatrix * viewMatrix * w;
      }`,
    fragmentShader: /* glsl */`
      uniform sampler2D uLight, tBed, tNoise;
      uniform vec4 uMapXf;
      uniform vec3 uSunColor, uSkyColor, uZenithW, uFallsBase;
      uniform float uBedTile, uDetail;
      varying vec3 vWorld;
      varying vec2 vFlow, vMisc;
      varying vec4 vFx, vEnv0, vEnv1;
      varying vec3 vNg;
      ${ATMOSPHERE_PARS}
      // the skyline's elevation (rad) toward a horizontal direction, between the 8 baked ones
      float skyline(vec2 d) {
        float kf = mod(atan(d.y, d.x) / 0.7853982 + 8.0, 8.0);
        vec4 d0 = abs(kf - vec4(0.0, 1.0, 2.0, 3.0)), d1 = abs(kf - vec4(4.0, 5.0, 6.0, 7.0));
        d0 = min(d0, 8.0 - d0); d1 = min(d1, 8.0 - d1);
        return (dot(max(1.0 - d0, 0.0), vEnv0) + dot(max(1.0 - d1, 0.0), vEnv1)) * 1.5707963;
      }
      void main() {
        vec3 ng = normalize(vNg);
        float steep = smoothstep(0.03, 0.22, 1.0 - ng.y);           // the water's own fall: drops, the cascade
        // (on a steep drop the raster's water is a skin over the rock: it reads as white water, not shallows)
        float depth = max(vFx.x, 0.5 * steep);
        // (Laurel Fork's falls is the falls sheet; under it the surface would be a white plank)
        if (vFx.y > 0.5 && depth < 1.5 && distance(vWorld.xz, uFallsBase.xz) < 22.0 && vWorld.y > uFallsBase.y + 1.5) discard;
        // (the shallow margin dithers out: no cell staircase where the water meets the bank)
        if (depth < 0.14 && fract(52.9829189 * fract(dot(gl_FragCoord.xy, vec2(0.06711056, 0.00583715)))) > depth / 0.14) discard;
        vec2 mu = (vWorld.xz - uMapXf.xy) * uMapXf.z;
        bool inMap = all(greaterThan(mu, vec2(0.0))) && all(lessThan(mu, vec2(1.0)));
        vec4 l = inMap ? textureLod(uLight, mu, 0.0) : vec4(1.0);
        float sunVis = l.a * l.g;
        vec3 toP = vWorld - cameraPosition;
        float dist = length(toP);
        vec3 v = toP / dist;
        vec2 xz = vWorld.xz - floor(vWorld.xz / 512.0) * 512.0;      // (small coordinates: no float jitter)
        vec2 fl = vFlow;
        float speed = length(fl);
        vec2 fdir = speed > 1e-3 ? fl / speed : vec2(0.0, -1.0);
        float t = uTime;
        // flow map: two layers half a cycle apart, each place on its own phase (no pulsing in step)
        const float T = 1.5;
        float jit = texture2D(tNoise, xz / 53.0).a * 2.0;
        float p0 = fract(t / T + jit), p1 = fract(p0 + 0.5);
        float wb = abs(1.0 - 2.0 * p0);
        vec2 o0 = fl * p0 * T, o1 = fl * p1 * T;
        vec2 g = mix(texture2D(tNoise, (xz - o0) / 7.0).rg, texture2D(tNoise, (xz - o1) / 7.0 + 0.37).rg, wb) - 0.5;
        if (uDetail > 0.5)
          g += (mix(texture2D(tNoise, (xz - o0) / 2.3 + 0.61).rg, texture2D(tNoise, (xz - o1) / 2.3 + 0.13).rg, wb) - 0.5) * 0.8;
        // calm pools barely ripple; riffles chop; foam roughens
        float rough = mix(0.06, 0.55, smoothstep(0.3, 3.0, speed)) + 0.35 * vFx.y;
        vec2 sl = g * rough;
        // standing waves: stationary crests across the current (their phase is baked)
        float ph = 6.2831853 * vFx.w, wv = vFx.z;
        float brkW = wv > 0.01 ? texture2D(tNoise, xz / 11.0 + vec2(0.0, t * 0.015)).a : 0.5;
        sl += fdir * wv * 0.5 * cos(ph) * (0.55 + 0.9 * brkW);
        vec3 n = normalize(ng + vec3(-sl.x, 0.0, -sl.y) * (1.0 + 1.5 * steep));
        vec3 rd = reflect(v, n);
        float cosv = max(dot(-v, n), 0.0);
        float fres = 0.02 + 0.98 * pow(1.0 - cosv, 5.0);
        // what it reflects: sky above the skyline, the gorge's forest below it
        vec2 hd = normalize(rd.xz + vec2(1e-5));
        float elev = asin(clamp(rd.y, -1.0, 1.0));
        float hz = skyline(hd);
        float skyw = smoothstep(hz - 0.05, hz + 0.05, elev);
        vec3 skyC = mix(hazeAlong(rd), uZenithW, sqrt(max(rd.y, 0.0)));
        float facing = max(0.0, -dot(hd, normalize(uSunDir.xz + vec2(1e-5))));
        vec3 forestC = vec3(0.02, 0.033, 0.015) * (uSkyColor * 1.7 + uSunColor * 0.6 * facing * facing);
        forestC = mix(forestC, hazeAlong(rd) * 0.45, (1.0 - smoothstep(0.02, 0.2, hz)) * 0.6);   // (a far, low skyline: a hazed ridge)
        vec3 refl = mix(forestC, skyC, skyw);
        // the bed through the water
        vec3 lit = uSunColor * sunVis * 0.85 + uSkyColor * l.b;
        float pathK = 1.0 + 1.0 / max(cosv, 0.2);
        vec3 Tw = exp(-vec3(0.5, 0.15, 0.27) * depth * pathK);
        vec2 buv = (vWorld.xz + n.xz * (0.2 + 0.35 * depth)) / uBedTile;
        vec3 bs = texture2D(tBed, buv).rgb;
        vec3 bed = bs * vec3(1.0, 0.84, 0.6) * 0.85;                                     // wet gold-brown cobbles
        bed = mix(bed, vec3(dot(bs, vec3(0.3, 0.5, 0.2))) * vec3(0.58, 0.59, 0.55), vMisc.x);  // bedrock: grey gneiss
        bed = mix(bed, bed * vec3(0.5, 0.72, 0.42), smoothstep(0.7, 2.6, depth) * 0.65); // algae and silt in the pools
        float caustic = 0.0;           // (sun caustics in the sunlit shallows; not at the low quality levels)
        if (uDetail > 0.5 && sunVis > 0.05 && depth < 1.4) {
          float cz = texture2D(tNoise, xz / 3.3 + vec2(t * 0.045, t * 0.03)).b * texture2D(tNoise, xz / 2.1 - vec2(t * 0.035, -t * 0.02) + 0.5).b;
          caustic = smoothstep(0.18, 0.5, cz) * sunVis * (1.0 - smoothstep(0.15, 1.4, depth));
        }
        vec3 under = bed * (lit + uSunColor * sunVis * caustic * 0.9);
        vec3 body = vec3(0.03, 0.064, 0.042) * lit;                                     // the water's own green-brown
        // (undercut and shaded banks: the edge of the water under a steep bank is darker)
        under = under * Tw + body * (1.0 - Tw);
        vec3 col = mix(under, refl, fres);
        // white water
        // (foam cells, advected; a second tap up the current streaks them along the flow, more when it's fast)
        float fpA = mix(texture2D(tNoise, (xz - o0) / 4.4 + 0.21).b, texture2D(tNoise, (xz - o1) / 4.4 + 0.77).b, wb);
        float fp = fpA;
        if (uDetail > 0.5) {
          vec2 sk = fdir * (0.4 + 0.35 * min(speed, 4.0));
          fp = 0.5 * (fpA + mix(texture2D(tNoise, (xz - o0 - sk) / 4.4 + 0.21).b, texture2D(tNoise, (xz - o1 - sk) / 4.4 + 0.77).b, wb));
        }
        float brk = uDetail > 0.5 ? mix(texture2D(tNoise, (xz - o0 * 0.7) / 26.0).a, texture2D(tNoise, (xz - o1 * 0.7) / 26.0 + 0.5).a, wb)
                                  : texture2D(tNoise, (xz - fl * 0.7 * T * 0.5) / 26.0).a;
        float pot = clamp(vFx.y * (0.45 + 1.0 * brk) + wv * 0.7 * pow(max(sin(ph), 0.0), 5.0) + 1.1 * steep, 0.0, 1.2);
        float foam = smoothstep(1.0 - pot, 1.5 - pot, fp + 0.12 * pot) * smoothstep(0.0, 0.1, depth + steep);
        // churn where the falls lands: rings of foam spreading over the pool
        float df = distance(vWorld.xz, uFallsBase.xz);
        float churn = (1.0 - smoothstep(2.0, 13.0, df)) * (0.55 + 0.45 * sin(df * 2.2 - t * 3.0));
        foam = max(foam, churn * smoothstep(0.35, 0.75, texture2D(tNoise, vWorld.xz / 3.0 + t * 0.07).b));
        foam = clamp(foam, 0.0, 1.0);
        // (aerated, not paint: brighter in the cells' crowns, blue-grey where only the sky lights it)
        vec3 white = vec3(0.8, 0.85, 0.86) * (uSunColor * 0.55 * sunVis + uSkyColor * (0.38 + 0.4 * l.b)) * (0.7 + 0.45 * fpA);
        col = mix(col, white, foam * 0.94);
        // the low sun's glints on the ripples
        float sd = max(dot(rd, uSunDir), 0.0);
        col += uSunColor * (pow(sd, 1400.0) * 12.0 + pow(sd, 110.0) * 0.25) * sunVis * (1.0 - foam);
        gl_FragColor = vec4(applyAtmosphere(col, vWorld), 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
  const mesh = new THREE.Mesh(g, mat);
  mesh.name = 'Wild_Water';
  mesh.position.y = 0.02;
  const grp = new THREE.Group();
  grp.name = 'Wild_WaterGroup';
  grp.add(mesh);
  if (falls) grp.add(buildFallsSheet(world, uniforms, tex, falls));
  grp.add(buildMist(world, uniforms, tex, falls));
  tex.waterLevel = waterLevelTexture(world);          // (the props' wet line: level.js kitPropMaterial)
  // the quality levels drop the ripples' fine layer at q0-1 (main.js quality.setLevel calls this)
  // (and draw half the mist cards: additive overdraw is the software renderer's cost)
  const mist = grp.children.find((o) => o.name === 'Wild_Mist'), mistN = mist.geometry.index.count;
  grp.userData.setLow = (low) => { mat.uniforms.uDetail.value = low ? 0 : 1; mist.geometry.setDrawRange(0, low ? Math.min(mistN, 6 * 24) : mistN); };
  return grp;
}

// The falls: a translucent, bowed sheet from the lip's water to the pool, streaks pouring down it
// (fast, broken, thinning to show the dark wet rock behind). Its spray is in the mist (buildMist).
function buildFallsSheet(world, uniforms, tex, f) {
  const oy = world.meta.estate_offset[1];
  const top = new THREE.Vector3(f.x0, f.z0, -(f.y0 - oy)), bot = new THREE.Vector3(f.x1, f.z1, -(f.y1 - oy));
  const fl = new THREE.Vector3(bot.x - top.x, 0, bot.z - top.z).normalize(), side = new THREE.Vector3(-fl.z, 0, fl.x);
  const nu = 10, nv = 24, P = [], UV = [], I = [];
  for (let v = 0; v <= nv; v++) for (let u = 0; u <= nu; u++) {
    const t = v / nv, w = (u / nu - 0.5) * f.width * (1 + 0.35 * t);
    // a ballistic lip (it shoots out, then drops), bowing out from the face
    const p = top.clone().lerp(bot, t).addScaledVector(fl, Math.sin(Math.min(1, t * 1.6) * Math.PI * 0.5) * 1.6 + 0.2).addScaledVector(side, w);
    P.push(p.x, p.y, p.z); UV.push(u / nu, t);
  }
  for (let v = 0; v < nv; v++) for (let u = 0; u < nu; u++) { const a = u + v * (nu + 1), b = a + 1, c = a + nu + 1, d = c + 1; I.push(a, c, b, b, c, d); }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(UV, 2));
  g.setIndex(I);
  const U = { ...uniforms, uLight: { value: tex.light }, uMapXf: { value: new THREE.Vector4(-world.size / 2, -world.size / 2, 1 / world.size, 1) },
    uHeightF: { value: f.z0 - f.z1 } };
  const sheet = new THREE.Mesh(g, new THREE.ShaderMaterial({
    uniforms: U, transparent: true, depthWrite: false, side: THREE.DoubleSide,
    vertexShader: /* glsl */`
      varying vec2 vUv; varying vec3 vWorld;
      void main() { vUv = uv; vec4 w = modelMatrix * vec4(position, 1.0); vWorld = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: /* glsl */`
      uniform sampler2D uLight; uniform vec4 uMapXf; uniform vec3 uSunColor, uSkyColor; uniform float uHeightF;
      varying vec2 vUv; varying vec3 vWorld;
      ${ATMOSPHERE_PARS}
      float hn(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
      float vn(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
        return mix(mix(hn(i), hn(i + vec2(1, 0)), f.x), mix(hn(i + vec2(0, 1)), hn(i + vec2(1, 1)), f.x), f.y); }
      void main() {
        vec4 l = textureLod(uLight, (vWorld.xz - uMapXf.xy) * uMapXf.z, 0.0);
        float t = uTime, y = vUv.y * uHeightF;
        // streaks: narrow ropes of water accelerating down the drop, breaking into spray lower down
        float s1 = vn(vec2(vUv.x * 26.0, y * 0.5 - t * 6.0)), s2 = vn(vec2(vUv.x * 61.0, y * 1.3 - t * 11.0));
        float s3 = vn(vec2(vUv.x * 9.0, y * 0.25 - t * 3.0));
        float rope = smoothstep(0.35, 0.75, s1 * 0.55 + s2 * 0.3 + s3 * 0.35);
        float edge = smoothstep(0.0, 0.12, vUv.x) * smoothstep(1.0, 0.88, vUv.x);
        float a = (0.18 + 0.75 * rope) * edge * mix(0.95, 0.6, vUv.y) * smoothstep(1.0, 0.86, vUv.y);
        if (a < 0.02) discard;
        vec3 foam = vec3(0.9, 0.92, 0.9) * (uSunColor * 0.6 * l.a * l.g + uSkyColor * (0.5 + 0.5 * l.b)) * (0.75 + 0.35 * rope);
        gl_FragColor = vec4(applyAtmosphere(foam, vWorld), a);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  }));
  sheet.name = 'Wild_Falls';
  sheet.renderOrder = 10;
  return sheet;
}

// ---------------------------------------------------------------- mist
// Spray and mist as one draw: camera-facing additive cards (no textures, no lights), drifting up
// and pulsing: a cluster at the foot of the falls, and over the river wherever the water falls
// steeply through heavy white water (the Narrows cascade, the ledges, the big rapids), sized and
// placed from the water's own foam and slope.
function buildMist(world, uniforms, tex, falls) {
  const oy = world.meta.estate_offset[1], { res, spacing, size, water } = world, half = size / 2, fx = world.waterFx;
  const rr = rng(23), cards = [];                        // [x, y, z, size, strength]
  if (falls) {
    const top = new THREE.Vector3(falls.x0, falls.z0, -(falls.y0 - oy)), bot = new THREE.Vector3(falls.x1, falls.z1, -(falls.y1 - oy));
    const fl = new THREE.Vector3(bot.x - top.x, 0, bot.z - top.z).normalize(), side = new THREE.Vector3(-fl.z, 0, fl.x);
    for (let k = 0; k < 10; k++) {
      const c = bot.clone().addScaledVector(side, (rr() - 0.5) * falls.width * 1.2).addScaledVector(fl, -0.5 + rr() * 5).add(new THREE.Vector3(0, rr() * 3, 0));
      cards.push([c.x, c.y, c.z, 3.5 + rr() * 4.5, 1]);
    }
  }
  if (fx) {
    // the best cell per 9 m block: foam x steepness (the surface's fall over 3 m)
    const B = 6, best = new Map();
    for (let j = 2; j < res - 2; j++) for (let i = 2; i < res - 2; i++) {
      const k = i + j * res, h = water[k];
      if (!Number.isFinite(h) || fx.foam[k] < 0.55) continue;
      const a = water[k - 2], b = water[k + 2], c = water[k - 2 * res], d = water[k + 2 * res];
      if (![a, b, c, d].every(Number.isFinite)) continue;
      const s = Math.hypot(b - a, d - c) / (4 * spacing);
      const score = fx.foam[k] * Math.min(1, s / 0.12);
      if (score < 0.35) continue;
      const key = `${Math.floor(i / B)},${Math.floor(j / B)}`, o = best.get(key);
      if (!o || score > o[1]) best.set(key, [k, score, s]);
    }
    const list = [...best.values()].sort((p, q) => q[1] - p[1]).slice(0, 60);
    for (const [k, score, s] of list) {
      const i = k % res, j = Math.floor(k / res);
      const x = -half + i * spacing + (rr() - 0.5) * spacing * B, z = -half + j * spacing + (rr() - 0.5) * spacing * B;
      cards.push([x, water[k] + 0.6 + rr() * 1.5, z, 2.5 + 5 * Math.min(1, s / 0.3) + rr() * 2, 0.45 + 0.55 * score]);
    }
  }
  const SP = [], SC = [], SS = [], SI = [];
  cards.forEach(([x, y, z, s, a], k) => {
    const seed = rr();
    for (const [qx, qy] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) { SP.push(x, y, z); SC.push(qx, qy, s, seed); SS.push(a); }
    const o = k * 4; SI.push(o, o + 1, o + 2, o, o + 2, o + 3);
  });
  const sg = new THREE.BufferGeometry();
  sg.setAttribute('position', new THREE.Float32BufferAttribute(SP, 3));
  sg.setAttribute('corner', new THREE.Float32BufferAttribute(SC, 4));
  sg.setAttribute('strength', new THREE.Float32BufferAttribute(SS, 1));
  sg.setIndex(SI);
  const U = { ...uniforms, uLight: { value: tex.light }, uMapXf: { value: new THREE.Vector4(-half, -half, 1 / size, 1) } };
  const mist = new THREE.Mesh(sg, new THREE.ShaderMaterial({
    uniforms: U, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    vertexShader: /* glsl */`
      uniform float uTime;
      attribute vec4 corner;
      attribute float strength;
      varying vec2 vQ; varying float vSeed, vStr; varying vec3 vWorld;
      void main() {
        float rate = 0.12 + 0.05 * corner.w;
        float ph = fract(uTime * rate + corner.w);
        vec3 c = position + vec3(0.0, ph * 4.0, 0.0);
        float s = corner.z * (0.6 + 0.8 * ph);
        vec3 right = vec3(viewMatrix[0][0], viewMatrix[1][0], viewMatrix[2][0]);
        vec3 up = vec3(viewMatrix[0][1], viewMatrix[1][1], viewMatrix[2][1]);
        vec3 w = c + (right * corner.x + up * corner.y) * s;
        vQ = corner.xy; vSeed = corner.w + floor(uTime * rate + corner.w) * 0.37; vWorld = w; vStr = strength;
        gl_Position = projectionMatrix * viewMatrix * vec4(w, 1.0);
      }`,
    fragmentShader: /* glsl */`
      uniform sampler2D uLight; uniform vec4 uMapXf; uniform vec3 uSunColor, uSkyColor;
      varying vec2 vQ; varying float vSeed, vStr; varying vec3 vWorld;
      ${ATMOSPHERE_PARS}
      float hn(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
      float vn(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
        return mix(mix(hn(i), hn(i + vec2(1, 0)), f.x), mix(hn(i + vec2(0, 1)), hn(i + vec2(1, 1)), f.x), f.y); }
      void main() {
        float r = length(vQ);
        if (r > 1.0) discard;
        float puff = (1.0 - smoothstep(0.2, 1.0, r)) * (0.45 + 0.55 * vn(vQ * 2.6 + vSeed * 17.0 + uTime * 0.3));
        float ph = fract(uTime * 0.15 + vSeed);
        float a = puff * 0.12 * sin(ph * 3.1416) * vStr;
        vec2 mu = (vWorld.xz - uMapXf.xy) * uMapXf.z;
        vec4 l = all(greaterThan(mu, vec2(0.0))) && all(lessThan(mu, vec2(1.0))) ? textureLod(uLight, mu, 0.0) : vec4(1.0);
        // (backlit by the low sun, mist glows: forward scatter toward the sun)
        vec3 vd = normalize(vWorld - cameraPosition);
        float fwd = pow(max(dot(vd, uSunDir), 0.0), 6.0);
        vec3 c = (uSunColor * (0.5 + 1.5 * fwd) * l.a * l.g + uSkyColor * 0.6) * a;
        gl_FragColor = vec4(c, 1.0);
      }`,
  }));
  mist.name = 'Wild_Mist';
  mist.frustumCulled = false;
  mist.renderOrder = 11;
  return mist;
}

// ---------------------------------------------------------------- the props' wet line
// RG half float over the square at 3 m: r = the nearest water's level (within ~9 m; -9999 beyond),
// g = its foam (the splash height). level.js kitPropMaterial darkens rock and wood below
// level + splash (a dark wet band at the waterline, higher where the river is white).
function waterLevelTexture(world) {
  const { res, water } = world, fx = world.waterFx, S = 2, m = Math.floor((res - 1) / S) + 1;
  const lv = new Float32Array(m * m).fill(-9999), fo = new Float32Array(m * m), dist = new Float32Array(m * m).fill(1e9);
  for (let j = 0; j < m; j++) for (let i = 0; i < m; i++) {
    const k = i * S + j * S * res, o = i + j * m;
    if (Number.isFinite(water[k])) { lv[o] = water[k]; fo[o] = fx ? fx.foam[k] : 0; dist[o] = 0; }
  }
  const relax = (o, oo, d) => { if (dist[oo] + d < dist[o]) { dist[o] = dist[oo] + d; lv[o] = lv[oo]; fo[o] = fo[oo]; } };
  for (let j = 1; j < m; j++) for (let i = 1; i < m - 1; i++) { const o = i + j * m; relax(o, o - 1, 1); relax(o, o - m, 1); relax(o, o - m - 1, 1.41); relax(o, o - m + 1, 1.41); }
  for (let j = m - 2; j >= 0; j--) for (let i = m - 2; i > 0; i--) { const o = i + j * m; relax(o, o + 1, 1); relax(o, o + m, 1); relax(o, o + m + 1, 1.41); relax(o, o + m - 1, 1.41); }
  const data = new Uint16Array(m * m * 2);
  for (let o = 0; o < m * m; o++) {
    data[o * 2] = THREE.DataUtils.toHalfFloat(dist[o] <= 3 ? lv[o] : -9999);
    data[o * 2 + 1] = THREE.DataUtils.toHalfFloat(fo[o]);
  }
  const t = new THREE.DataTexture(data, m, m, THREE.RGFormat, THREE.HalfFloatType);
  t.minFilter = t.magFilter = THREE.LinearFilter; t.needsUpdate = true; t.name = 'water_level';
  return t;
}

// ---------------------------------------------------------------- wet banks
// The terrain's wet / cobble mask (R8G8 over the heightfield's vertices; terrain.js tWet): r = wet
// (the banks within ~2-6 m of the water, wider where the river is white and splashes; the falls'
// spray zone and its face), g = cobble bar (low, flat ground beside the water: under 2 m above the
// nearest water within 34 m). A chamfer distance from the water raster carrying the nearest
// water's level and foam. (It replaces main.js's wetTexture, which had no foam to go on.)
export function waterWetTexture(world) {
  const { res, spacing, water, heights, size } = world, n = res * res, fx = world.waterFx;
  const dist = new Float32Array(n).fill(1e9), lvl = new Float32Array(n), fo = new Float32Array(n);
  for (let k = 0; k < n; k++) if (Number.isFinite(water[k])) { dist[k] = 0; lvl[k] = water[k]; fo[k] = fx ? fx.foam[k] : 0; }
  const a = spacing, b = spacing * Math.SQRT2;
  const relax = (k, kk, d) => { const v = dist[kk] + d; if (v < dist[k]) { dist[k] = v; lvl[k] = lvl[kk]; fo[k] = fo[kk]; } };
  for (let j = 0; j < res; j++) for (let i = 0; i < res; i++) {
    const k = i + j * res;
    if (i > 0) relax(k, k - 1, a);
    if (j > 0) { relax(k, k - res, a); if (i > 0) relax(k, k - res - 1, b); if (i < res - 1) relax(k, k - res + 1, b); }
  }
  for (let j = res - 1; j >= 0; j--) for (let i = res - 1; i >= 0; i--) {
    const k = i + j * res;
    if (i < res - 1) relax(k, k + 1, a);
    if (j < res - 1) { relax(k, k + res, a); if (i < res - 1) relax(k, k + res + 1, b); if (i > 0) relax(k, k + res - 1, b); }
  }
  const out = new Uint8Array(n * 2), half = size / 2;
  const f = world.props?.authored?.find((p) => p.kind === 'falls'), oy = world.meta.estate_offset[1];
  const fx0 = f ? f.x1 : 1e9, fz0 = f ? -(f.y1 - oy) : 1e9, tx = f ? f.x0 : 1e9, tz = f ? -(f.y0 - oy) : 1e9;
  for (let j = 0; j < res; j++) for (let i = 0; i < res; i++) {
    const k = i + j * res, x = -half + i * spacing, z = -half + j * spacing;
    const above = heights[k] - lvl[k];
    const reach = 2.2 + 4.5 * fo[k];
    let wet = Math.max(0, 1 - dist[k] / reach) ** 0.7 * (above < 0.6 + 2.5 * fo[k] ? 1 : 0.35);
    if (f) {
      const d = Math.hypot(x - fx0, z - fz0), dt = Math.hypot(x - tx, z - tz);
      wet = Math.max(wet, Math.max(0, 1 - d / 26), Math.max(0, 1 - dt / 16) * 0.9);
    }
    const bar = dist[k] < 34 && dist[k] > 0 ? Math.max(0, 1 - Math.max(0, above - 0.6) / 1.6) * (1 - Math.max(0, dist[k] - 26) / 8) : 0;
    out[k * 2] = Math.round(Math.min(1, wet) * 255); out[k * 2 + 1] = Math.round(Math.min(1, bar) * 255);
  }
  const t = new THREE.DataTexture(out, res, res, THREE.RGFormat, THREE.UnsignedByteType);
  t.minFilter = THREE.LinearFilter; t.magFilter = THREE.LinearFilter; t.needsUpdate = true;
  t.name = 'wet_cobble';
  return t;
}
