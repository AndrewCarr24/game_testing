import * as THREE from 'three';
import { ATMOSPHERE_PARS } from './atmosphere.js';
import { rng } from './noise.js';

// The wilderness water (a generated level, load_world.js worlds): the Laurel River, Laurel Fork,
// the plunge pool, the falls and their spray, and the water-query API the player uses.
//   waterField(world)   the CPU field (surfaceAt / depthAt / flowAt / wet), cached on the world
//   buildWater(world, uniforms, tex)   the meshes
// Contract: design/wilderness/blue_ridge/water.md. Coordinates: terrain-local three.js metres
// (x east, y up, z = -(estate y + 810)), as world.heightAt.

// ---------------------------------------------------------------- the query API
export function waterField(world) {
  if (world.waterField) return world.waterField;
  const { res, spacing, size, water, heights } = world, half = size / 2, n = res * res;
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

// ---------------------------------------------------------------- water
// One mesh over every wet cell of the water raster (the Laurel River, Laurel Fork, the plunge
// pool) plus the river's ribbon beyond the square (world.river.out, down the valley to the town).
// Tea-clear water over the cobble bed (tex.bed), absorbed by depth (tannin water: blue goes first,
// so deep water turns amber-black); reflections of the sky only where the sky is open (the light
// map's sky visibility), the gorge's dark walls and canopy elsewhere; whitewater where the surface
// steepens (riffles, the shoals, the Narrows ledge and cascade) and around rocks in rapids; the
// churn where the falls lands. The falls itself is buildFalls (a translucent sheet + spray).
export function buildWater(world, uniforms, tex) {
  const { res, spacing, size, water, heights } = world, half = size / 2;
  const P = [], F = [], S = [], Dp = [], idx = [];
  const vid = new Int32Array(res * res).fill(-1);
  const lvl = (i, j) => water[i + j * res];
  const vert = (i, j, h) => {
    const k = i + j * res;
    if (vid[k] >= 0) return vid[k];
    vid[k] = P.length / 3;
    P.push(-half + i * spacing, h, -half + j * spacing);
    // flow: down the water surface's gradient (over 2 cells each way: smoother rapids)
    const at = (a, b) => { const v = lvl(Math.min(res - 1, Math.max(0, a)), Math.min(res - 1, Math.max(0, b))); return Number.isFinite(v) ? v : h; };
    const hx = at(i + 2, j) - at(i - 2, j), hz = at(i, j + 2) - at(i, j - 2);
    const g = Math.hypot(hx, hz) / (4 * spacing);
    F.push(-hx / (Math.hypot(hx, hz) + 1e-6), -hz / (Math.hypot(hx, hz) + 1e-6));
    S.push(Math.min(1, g));
    Dp.push(Math.max(0, h - heights[k]));
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
      for (const sd of [-1, 1]) { P.push(x + sx * w * sd, y, z + sz * w * sd); F.push(dx / L, dz / L); S.push(Math.min(1, g)); Dp.push(1.8); }
    });
    for (let n = 0; n < out.length - 1; n++) { const a = base + n * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
  g.setAttribute('flow', new THREE.Float32BufferAttribute(F, 2));
  g.setAttribute('steep', new THREE.Float32BufferAttribute(S, 1));
  g.setAttribute('depth', new THREE.Float32BufferAttribute(Dp, 1));
  g.setIndex(idx);
  g.computeVertexNormals();
  const falls = world.props.authored.find((p) => p.kind === 'falls');
  const fb = falls ? new THREE.Vector3(falls.x1, falls.z1, -(falls.y1 - oy)) : new THREE.Vector3(0, -1e4, 0);
  const mat = new THREE.ShaderMaterial({
    uniforms: { ...uniforms, uLight: { value: tex.light }, uMapXf: { value: new THREE.Vector4(-half, -half, 1 / size, 1) },
      uZenithW: { value: new THREE.Color(...(world.skyMeta?.zenith || [0.2, 0.33, 0.66])) },
      tBed: { value: tex.bed || tex.scree }, uBedTile: { value: tex.bedTile || 1.8 }, uFallsBase: { value: fb } },
    vertexShader: /* glsl */`
      attribute vec2 flow;
      attribute float steep, depth;
      varying vec3 vWorld, vN;
      varying vec2 vFlow;
      varying float vSteep, vDepth;
      void main() { vec4 w = modelMatrix * vec4(position, 1.0); vWorld = w.xyz; vN = normal; vFlow = flow; vSteep = steep; vDepth = depth;
        gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: /* glsl */`
      uniform sampler2D uLight, tBed;
      uniform vec4 uMapXf;
      uniform vec3 uSunColor, uSkyColor, uZenithW, uFallsBase;
      uniform float uBedTile;
      varying vec3 vWorld, vN;
      varying vec2 vFlow;
      varying float vSteep, vDepth;
      ${ATMOSPHERE_PARS}
      float hn(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
      float vn(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
        return mix(mix(hn(i), hn(i + vec2(1, 0)), f.x), mix(hn(i + vec2(0, 1)), hn(i + vec2(1, 1)), f.x), f.y); }
      // flow-map noise: two layers advected along the local flow, each restarting every 4 s,
      // cross-faded (no swirl where the flow turns, no stretch over time)
      float flowN(vec2 xz, vec2 fl, float speed, vec2 k, float t) {
        float p0 = fract(t * 0.25), p1 = fract(t * 0.25 + 0.5);
        vec2 o0 = fl * p0 * speed * 4.0, o1 = fl * p1 * speed * 4.0;
        vec2 ax = normalize(fl + 1e-4), ay = vec2(-ax.y, ax.x);
        vec2 a = xz - o0, b = xz - o1 + 17.0;
        float n0 = vn(vec2(dot(a, ax) * k.x, dot(a, ay) * k.y)), n1 = vn(vec2(dot(b, ax) * k.x, dot(b, ay) * k.y));
        return mix(n0, n1, abs(p0 * 2.0 - 1.0));
      }
      void main() {
        // (Laurel Fork's falls is buildFalls' sheet; under it the surface would be a white plank)
        if (vSteep > 0.55 && distance(vWorld.xz, uFallsBase.xz) < 26.0) discard;
        // (the shallow margin dithers out: no cell staircase where the water meets the bank)
        if (vDepth < 0.14 && fract(52.9829189 * fract(dot(gl_FragCoord.xy, vec2(0.06711056, 0.00583715)))) > vDepth / 0.14) discard;
        vec2 mu = (vWorld.xz - uMapXf.xy) * uMapXf.z;
        bool inMap = all(greaterThan(mu, vec2(0.0))) && all(lessThan(mu, vec2(1.0)));
        vec4 l = inMap ? textureLod(uLight, mu, 0.0) : vec4(1.0, 1.0, 1.0, 1.0);
        vec3 v = normalize(vWorld - cameraPosition);
        vec2 fl = normalize(vFlow + 1e-4);
        vec2 q = vec2(dot(vWorld.xz, fl), dot(vWorld.xz, vec2(-fl.y, fl.x)));
        float t = uTime;
        float speed = 0.8 + 14.0 * vSteep;
        // ripples along the flow; rougher where it runs fast
        // (a local frame: the rotated coordinates stay small, so turning flow can't swirl them)
        vec2 lxz = vWorld.xz - floor(vWorld.xz / 256.0) * 256.0;
        float r1 = flowN(lxz, fl, speed * 0.7, vec2(1.3, 2.1), t), r2 = flowN(lxz * 1.7, fl, speed * 1.3, vec2(2.2, 2.5), t + 1.3);
        float rough = 0.18 + 0.9 * smoothstep(0.02, 0.15, vSteep);
        vec3 n = normalize(vec3(((r1 - 0.5) * 0.25 + (r2 - 0.5) * 0.12) * rough * 2.0, 1.0, (r2 - r1) * 0.2 * rough * 2.0));
        vec3 rd = reflect(v, n);
        float fres = 0.02 + 0.98 * pow(1.0 - max(dot(-v, n), 0.0), 5.0);
        // what the surface reflects: open sky where the sky is open, the gorge's dark walls and
        // the canopy where it isn't (sky visibility from the light map)
        vec3 sky = mix(hazeAlong(rd), uZenithW, sqrt(max(rd.y, 0.0)));
        vec3 walls = vec3(0.016, 0.03, 0.013) * (uSkyColor * 2.2 + uSunColor * 0.35 * l.a);    // the gorge's forest
        vec3 refl = mix(walls, sky, smoothstep(0.25, 0.85, l.b));
        // the bed through the water: gold-brown cobbles, refracted by the ripples, absorbed by depth
        float dpt = max(vDepth, 0.0);
        vec2 buv = (vWorld.xz + n.xz * (0.35 + 0.25 * dpt)) / uBedTile;
        vec3 bed = texture2D(tBed, buv).rgb * vec3(1.05, 0.92, 0.72);
        vec3 lit = uSunColor * l.a * l.g * 0.85 + uSkyColor * l.b;
        vec3 Tw = exp(-dpt * vec3(0.26, 0.36, 0.72));
        vec3 body = vec3(0.012, 0.017, 0.008) * lit;                    // deep water: green-tea dark
        vec3 under = mix(body, bed * lit, Tw);
        float glint = pow(max(dot(rd, uSunDir), 0.0), 260.0) * 14.0 * l.a * l.g;
        // (a river's surface is never a mirror: the current's chop scatters it)
        vec3 col = mix(under, refl, fres * 0.6) + vec3(1.0, 0.82, 0.58) * glint;
        // whitewater: riffles (patchy, where the current quickens) to rapids to the cascade, streaking
        // down the flow and breaking up
        float riff = smoothstep(0.012, 0.05, vSteep) * smoothstep(0.55, 0.85, vn(lxz * vec2(0.12, 0.3)));
        float ww = max(smoothstep(0.05, 0.25, vSteep), 0.55 * riff);
        // churn where the falls lands: rings of foam spreading over the pool
        float df = distance(vWorld.xz, uFallsBase.xz);
        float churn = (1.0 - smoothstep(2.0, 13.0, df)) * (0.55 + 0.45 * sin(df * 2.2 - t * 3.0));
        float st = flowN(lxz, fl, speed * 0.35, vec2(0.5, 2.5), t) * 0.6 + flowN(lxz, fl, speed * 0.7, vec2(1.6, 7.0), t + 2.1) * 0.4;
        // (broken up by a world-space break-up noise: tongues of dark water between the white)
        float brk = vn(lxz * 0.45) * 0.6 + vn(lxz * 1.3) * 0.4;
        float foam = max(ww * smoothstep(0.5, 0.9, 0.15 + 0.6 * st + 0.4 * brk) * mix(0.55, 1.0, smoothstep(0.15, 0.4, vSteep)),
                         churn * smoothstep(0.3, 0.8, vn(vWorld.xz * 1.7 + t * 0.6)));
        foam = clamp(foam, 0.0, 1.0);
        vec3 white = vec3(0.86, 0.88, 0.86) * (uSunColor * 0.5 * l.a * l.g + uSkyColor * (0.45 + 0.55 * l.b));
        col = mix(col, white, foam);
        gl_FragColor = vec4(applyAtmosphere(col, vWorld), 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
  const mesh = new THREE.Mesh(g, mat);
  mesh.name = 'Wild_Water';
  mesh.position.y = 0.02;
  if (falls) mesh.add(buildFalls(world, uniforms, tex, falls));
  return mesh;
}

// The falls: a translucent, bowed sheet from the lip's water to the pool, streaks pouring down it
// (fast, broken, thinning to show the dark wet rock behind), and its spray: a few camera-facing
// cards of drifting mist at the foot (additive, like fire.js's flames: no textures, no lights).
// Two draw calls.
function buildFalls(world, uniforms, tex, f) {
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
  // spray: 10 cards around the foot of the falls, billboarded, drifting and pulsing
  const N = 10, SP = [], SC = [], SI = [];
  const rr = rng(23);
  for (let k = 0; k < N; k++) {
    const c = bot.clone().addScaledVector(side, (rr() - 0.5) * f.width * 1.2).addScaledVector(fl, -0.5 + rr() * 5).add(new THREE.Vector3(0, rr() * 3, 0));
    const s = 3.5 + rr() * 4.5;
    for (const [qx, qy] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) { SP.push(c.x, c.y, c.z); SC.push(qx, qy, s, rr()); }
    const o = k * 4; SI.push(o, o + 1, o + 2, o, o + 2, o + 3);
  }
  const sg = new THREE.BufferGeometry();
  sg.setAttribute('position', new THREE.Float32BufferAttribute(SP, 3));
  sg.setAttribute('corner', new THREE.Float32BufferAttribute(SC, 4));
  sg.setIndex(SI);
  const spray = new THREE.Mesh(sg, new THREE.ShaderMaterial({
    uniforms: U, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    vertexShader: /* glsl */`
      uniform float uTime;
      attribute vec4 corner;
      varying vec2 vQ; varying float vSeed; varying vec3 vWorld;
      void main() {
        float ph = fract(uTime * (0.12 + 0.05 * corner.w) + corner.w);
        vec3 c = position + vec3(0.0, ph * 4.0, 0.0);
        float s = corner.z * (0.6 + 0.8 * ph);
        vec3 right = vec3(viewMatrix[0][0], viewMatrix[1][0], viewMatrix[2][0]);
        vec3 up = vec3(viewMatrix[0][1], viewMatrix[1][1], viewMatrix[2][1]);
        vec3 w = c + (right * corner.x + up * corner.y) * s;
        vQ = corner.xy; vSeed = corner.w + floor(uTime * (0.12 + 0.05 * corner.w) + corner.w) * 0.37; vWorld = w;
        gl_Position = projectionMatrix * viewMatrix * vec4(w, 1.0);
      }`,
    fragmentShader: /* glsl */`
      uniform sampler2D uLight; uniform vec4 uMapXf; uniform vec3 uSunColor, uSkyColor;
      varying vec2 vQ; varying float vSeed; varying vec3 vWorld;
      ${ATMOSPHERE_PARS}
      float hn(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
      float vn(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
        return mix(mix(hn(i), hn(i + vec2(1, 0)), f.x), mix(hn(i + vec2(0, 1)), hn(i + vec2(1, 1)), f.x), f.y); }
      void main() {
        float r = length(vQ);
        float puff = (1.0 - smoothstep(0.2, 1.0, r)) * (0.45 + 0.55 * vn(vQ * 2.6 + vSeed * 17.0 + uTime * 0.3));
        float ph = fract(uTime * 0.15 + vSeed);
        float a = puff * 0.12 * sin(ph * 3.1416);
        vec4 l = textureLod(uLight, (vWorld.xz - uMapXf.xy) * uMapXf.z, 0.0);
        vec3 c = (uSunColor * 0.5 * l.a * l.g + uSkyColor * 0.6) * a;
        gl_FragColor = vec4(c, 1.0);
      }`,
  }));
  spray.name = 'Wild_Spray';
  spray.frustumCulled = false;
  spray.renderOrder = 11;
  const grp = new THREE.Group();
  grp.add(sheet, spray);
  grp.position.y = -0.02;
  return grp;
}

