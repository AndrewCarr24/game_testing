import * as THREE from 'three';
import { mergeGeometries, mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';
import { ATMOSPHERE_PARS } from './atmosphere.js';
import { rng } from './noise.js';

// Meshes a generated level adds to the wilderness runtime (load_world.js worlds): the backdrop
// ring, water (creek, plunge pool, the falls), props (logs, root wads, boulders, the footlog,
// walls, lookout slabs) and the estate stand-in seen from outside. All lit like the rest of the
// wilderness: the low sun x the baked light map (terrain + canopy shadow at the spot) + sky,
// then aerial perspective. No real-time lights, no shadow maps.

const LIT_PARS = /* glsl */`
uniform vec3 uSunColor, uSkyColor;
uniform sampler2D uLight;
uniform vec4 uMapXf;             // origin x, origin z, 1/size, use the map (1) or full sun (0)
vec3 litColor(vec3 alb, vec3 n, vec3 wpos, float wrap) {
  vec4 l = uMapXf.w > 0.5 ? textureLod(uLight, (wpos.xz - uMapXf.xy) * uMapXf.z, 0.0) : vec4(1.0);
  float ndl = clamp((dot(n, uSunDir) + wrap) / (1.0 + wrap), 0.0, 1.0);
  return alb * (uSunColor * ndl * l.a * l.g + uSkyColor * l.b * (0.6 + 0.4 * n.y));
}`;

export function litMaterial(uniforms, tex, world, { instanced = false, useMap = true, mossy = 0 } = {}) {
  return new THREE.ShaderMaterial({
    uniforms: { ...uniforms, uLight: { value: tex.light },
      uMapXf: { value: new THREE.Vector4(-world.size / 2, -world.size / 2, 1 / world.size, useMap ? 1 : 0) },
      uMoss: { value: mossy } },
    vertexColors: true,
    vertexShader: /* glsl */`
      varying vec3 vWorld, vN, vCol;
      void main() {
        mat4 m = modelMatrix;
        #ifdef USE_INSTANCING
          m = m * instanceMatrix;
        #endif
        vec4 w = m * vec4(position, 1.0);
        vWorld = w.xyz;
        vN = normalize(mat3(m) * normal);
        vCol = color;
        #ifdef USE_INSTANCING_COLOR
          vCol *= instanceColor;
        #endif
        gl_Position = projectionMatrix * viewMatrix * w;
      }`,
    fragmentShader: /* glsl */`
      uniform float uMoss;
      varying vec3 vWorld, vN, vCol;
      ${ATMOSPHERE_PARS}
      ${LIT_PARS}
      float hn(vec3 p) { return fract(sin(dot(floor(p), vec3(12.9898, 78.233, 37.719))) * 43758.5453); }
      void main() {
        vec3 n = normalize(vN);
        vec3 alb = vCol;
        if (uMoss > 0.0) {             // moss on every up-facing wet surface (brief: #4F7A2A)
          float m = smoothstep(0.35, 0.8, n.y + 0.25 * hn(vWorld * 2.3)) * uMoss;
          alb = mix(alb, vec3(0.078, 0.19, 0.024), m);
        }
        gl_FragColor = vec4(applyAtmosphere(litColor(alb, n, vWorld, 0.2), vWorld), 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}

// the kit's dead wood and rock as instanced props: bark / rock (part 0), the moss tile on their
// sky-facing faces (part 1), a root plate's soil (part 3); AO from the kit; lit like the rest
export function kitPropMaterial(uniforms, tex, world, maps) {
  const w = maps.wood || maps.shell, sh = maps.shell || w, so = maps.soil || w;
  return new THREE.ShaderMaterial({
    uniforms: { ...uniforms, uLight: { value: tex.light }, uMapXf: { value: new THREE.Vector4(-world.size / 2, -world.size / 2, 1 / world.size, 1) },
      tWood: { value: w }, tMoss: { value: sh }, tSoil: { value: so }, uBounce: uniforms.uBounce || { value: new THREE.Color(0.16, 0.2, 0.1) } },
    vertexShader: /* glsl */`
      attribute float ao, part;
      varying vec3 vWorld, vN; varying vec2 vUv; varying float vAO, vPart;
      void main() {
        mat4 m = modelMatrix * instanceMatrix;
        vec4 wp = m * vec4(position, 1.0);
        vWorld = wp.xyz; vN = normalize(mat3(m) * normal); vUv = uv; vAO = ao; vPart = part;
        gl_Position = projectionMatrix * viewMatrix * wp;
      }`,
    fragmentShader: /* glsl */`
      uniform sampler2D tWood, tMoss, tSoil;
      uniform vec3 uBounce;
      varying vec3 vWorld, vN; varying vec2 vUv; varying float vAO, vPart;
      ${ATMOSPHERE_PARS}
      ${LIT_PARS}
      void main() {
        vec3 n = normalize(vN);
        vec3 alb = vPart > 2.5 ? texture2D(tSoil, vUv).rgb : vPart > 0.5 ? texture2D(tMoss, vUv).rgb : texture2D(tWood, vUv).rgb;
        vec3 col = litColor(alb * mix(vAO, 1.0, 0.25), n, vWorld, 0.15) + alb * uBounce * 0.5 * vAO;
        gl_FragColor = vec4(applyAtmosphere(col, vWorld), 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}

const srgb = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);

// ---------------------------------------------------------------- backdrop ring
// The 4.6 km ring around the square (12 m samples, shown every 24 m), its baked colour as vertex
// colours, a hole over the fine terrain; its innermost ring drops under the fine terrain's edge
// (a skirt) so no sky shows through the seam.
export function buildBackdrop(world, uniforms, { step = 2 } = {}) {
  const B = world.backdrop, n = B.res, cell = B.cell, x0 = -B.extent / 2;
  const half = world.size / 2;
  const m = Math.floor((n - 1) / step) + 1, c = cell * step;
  const pos = new Float32Array(m * m * 3), col = new Float32Array(m * m * 3);
  for (let j = 0; j < m; j++) for (let i = 0; i < m; i++) {
    const si = Math.min(n - 1, i * step), sj = Math.min(n - 1, j * step);
    const k = (i + j * m) * 3, s = si + sj * n;          // image rows north first = three z ascending
    const x = x0 + si * cell, z = x0 + sj * cell;
    let h = B.heights[s];
    const inside = Math.abs(x) < half - 1 && Math.abs(z) < half - 1;
    if (inside) h -= 6;                                  // the skirt (only its edge quads are kept)
    pos[k] = x; pos[k + 1] = h; pos[k + 2] = z;
    col[k] = srgb(B.color[s * 3] / 255); col[k + 1] = srgb(B.color[s * 3 + 1] / 255); col[k + 2] = srgb(B.color[s * 3 + 2] / 255);
  }
  const idx = [];
  for (let j = 0; j < m - 1; j++) for (let i = 0; i < m - 1; i++) {
    const xa = x0 + i * c, xb = xa + c, za = x0 + j * c, zb = za + c;
    // drop quads wholly inside the square (by more than one cell: the edge quads are the skirt)
    if (xa >= -half + c - 1 && xb <= half - c + 1 && za >= -half + c - 1 && zb <= half - c + 1) continue;
    const a = i + j * m, b = a + 1, d = a + m, e = d + 1;
    idx.push(a, d, b, b, d, e);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  const mat = new THREE.ShaderMaterial({
    uniforms: { ...uniforms, uScale: { value: (world.meta.light_scale || 0.385) * 1.15 } },
    vertexColors: true,
    vertexShader: /* glsl */`
      varying vec3 vWorld, vCol;
      void main() { vec4 w = modelMatrix * vec4(position, 1.0); vWorld = w.xyz; vCol = color; gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: /* glsl */`
      uniform float uScale;
      varying vec3 vWorld, vCol;
      ${ATMOSPHERE_PARS}
      float hn(vec2 p) { return fract(sin(dot(floor(p), vec2(12.9898, 78.233))) * 43758.5453); }
      void main() {
        // crowns: a mottle at ~14 m, so the far forest isn't velvet
        vec2 p = vWorld.xz / 14.0;
        vec2 f = fract(p); f = f * f * (3.0 - 2.0 * f);
        float a = hn(p), b = hn(p + vec2(1, 0)), cc = hn(p + vec2(0, 1)), d = hn(p + vec2(1, 1));
        float m = mix(mix(a, b, f.x), mix(cc, d, f.x), f.y);
        vec3 col = vCol * uScale * (0.75 + 0.5 * m);
        gl_FragColor = vec4(applyAtmosphere(col, vWorld), 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
  const mesh = new THREE.Mesh(g, mat);
  mesh.name = 'Wild_Backdrop';
  mesh.frustumCulled = false;
  return mesh;
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

// ---------------------------------------------------------------- props
function logGeometry(sides = 10, rings = 8, root = false) {
  // unit log along +x (0..1), radius 1, tapering to 0.7; broken, splintered far end
  const g = new THREE.CylinderGeometry(0.72, 1, 1, sides, rings, false);
  g.rotateZ(-Math.PI / 2); g.translate(0.5, 0, 0);
  const p = g.attributes.position, r = rng(5);
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), y = p.getY(i), z = p.getZ(i), a = Math.atan2(z, y);
    const k = 1 + 0.07 * Math.sin(a * 7 + x * 9) + 0.04 * (r() - 0.5);
    p.setY(i, y * k); p.setZ(i, z * k);
    if (x > 0.99) p.setX(i, x + 0.04 * Math.sin(a * 5));
  }
  g.computeVertexNormals();
  return g;
}

function boulderGeometry(detail = 2, seed = 3) {
  // (IcosahedronGeometry is non-indexed: merge its vertices, or the normals come out faceted)
  const g = mergeVertices(new THREE.IcosahedronGeometry(1, detail).deleteAttribute('normal').deleteAttribute('uv'));
  const p = g.attributes.position, r = rng(seed);
  const bumps = [...Array(7)].map(() => [r() * 2 - 1, r() * 2 - 1, r() * 2 - 1, 0.15 + 0.2 * r()]);
  for (let i = 0; i < p.count; i++) {
    const v = new THREE.Vector3(p.getX(i), p.getY(i), p.getZ(i)).normalize();
    let k = 1;
    for (const [x, y, z, a] of bumps) k += a * Math.max(0, v.x * x + v.y * y + v.z * z) ** 3;
    if (v.y < -0.2) k *= 0.85;                       // flatter underside (sits in the ground)
    p.setXYZ(i, v.x * k, v.y * k, v.z * k);
  }
  g.computeVertexNormals();
  return g;
}

const setColor = (g, c) => {
  const n = g.attributes.position.count, a = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) a.set(c, i * 3);
  g.setAttribute('color', new THREE.BufferAttribute(a, 3));
  return g;
};

// Instanced props with a distance cull (refreshed when the camera moves): logs, root wads,
// boulders, slabs; plus the authored ones (footlog, walls) as one merged mesh.
export class Props {
  constructor(world, uniforms, tex, kit = null) {
    this.world = world;
    const toW = (x, y, z) => new THREE.Vector3(x, z, -(y - world.meta.estate_offset[1]));
    const P = world.props;
    this.kinds = [];
    const add = (name, geo, list, mossy, range) => {
      const mat = litMaterial(uniforms, tex, world, { instanced: true, mossy });
      const mesh = new THREE.InstancedMesh(geo, mat, Math.max(1, list.length));
      mesh.name = `Wild_${name}`;
      mesh.frustumCulled = false;
      mesh.count = 0;
      this.kinds.push({ name, mesh, list, range });
    };
    const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), e = new THREE.Euler();
    const logs = [], wads = [], rocks = [];
    const logOf = (l, ghost) => {
      const a = toW(l.x0, l.y0, l.z0), b = toW(l.x1, l.y1, l.z1);
      const d = b.clone().sub(a), L = d.length();
      q.setFromUnitVectors(new THREE.Vector3(1, 0, 0), d.clone().normalize());
      m.compose(a, q, s.set(L, l.r, l.r));
      return { pos: a.clone().add(b).multiplyScalar(0.5), matrix: m.clone(), color: ghost ? [0.5, 0.5, 0.47] : [0.2, 0.14, 0.09] };
    };
    for (const l of P.logs) {
      logs.push(logOf(l, l.kind === 'ghost'));
      if (l.wad) {                                       // root wad: a disc of roots and soil at the base
        const a = toW(l.x0, l.y0, l.z0), b = toW(l.x1, l.y1, l.z1), d = b.clone().sub(a).normalize();
        q.setFromUnitVectors(new THREE.Vector3(1, 0, 0), d);
        const R = 1.6 + 2.6 * l.r;
        m.compose(a.clone().addScaledVector(d, -0.2).add(new THREE.Vector3(0, R * 0.45, 0)), q, s.set(0.35, R, R));
        wads.push({ pos: a, matrix: m.clone(), color: [0.16, 0.11, 0.07] });
      }
    }
    for (const p of P.authored) if (p.kind === 'hero_ghost') logs.push(logOf(p, true));
    const rockOf = (b, color) => {
      const c = toW(b.x, b.y, b.z);
      e.set(0, b.yaw || 0, 0); q.setFromEuler(e);
      m.compose(c, q, s.set(b.r, b.r * (b.sq || 0.7), b.r * (0.8 + 0.3 * (b.seed || 0.5))));
      return { pos: c, matrix: m.clone(), color };
    };
    for (const b of P.boulders) rocks.push(rockOf(b, [0.28 + 0.05 * b.seed, 0.28 + 0.05 * b.seed, 0.26]));
    for (const p of P.authored) {
      if (p.kind === 'boulder') rocks.push(rockOf(p, [0.3, 0.3, 0.28]));
      if (p.kind === 'slab') {
        const c = toW(p.x, p.y, p.z + p.h * 0.5);
        e.set(0, p.yaw || 0, 0); q.setFromEuler(e);
        m.compose(c, q, s.set(p.w * 0.5, p.h * 0.62, p.dd * 0.5));
        rocks.push({ pos: c, matrix: m.clone(), color: [0.42, 0.41, 0.38] });
      }
    }
    const K = kit || {};
    if (K.chestnut_log_2 && K.blowdown_log && K.creek_boulder) {
      // the kit's models: each log's matrix maps the model's own length / thickness onto the placed
      // log; blowdowns carry their own root plates (no separate wad); boulders by their radius
      const fit = (geo) => { geo.computeBoundingBox(); const b = geo.boundingBox;
        return { x0: b.min.x, len: b.max.x - b.min.x, r: Math.max(b.max.y - b.min.y, b.max.z - b.min.z) / 2, y0: b.min.y, h: b.max.y - b.min.y }; };
      const fg = fit(K.chestnut_log_2.all), fb = fit(K.blowdown_log.all), fr = fit(K.creek_boulder.all);
      const kitLog = (l, F, isBlow) => {
        const a = toW(l.x0, l.y0, l.z0), b = toW(l.x1, l.y1, l.z1), d = b.clone().sub(a), L = d.length();
        q.setFromUnitVectors(new THREE.Vector3(1, 0, 0), d.clone().normalize());
        const sr = (l.r * (isBlow ? 1.0 : 1.0)) / (isBlow ? 0.6 : 0.4);
        const sx = L / (F.len * 0.98);
        const mm = new THREE.Matrix4().compose(a, q, s.set(sx, sr, sr)).multiply(new THREE.Matrix4().makeTranslation(-F.x0, -(isBlow ? 0.55 : 0.33), 0));
        return { pos: a.clone().add(b).multiplyScalar(0.5), matrix: mm, color: [1, 1, 1] };
      };
      const ghosts = [], blows = [], krocks = [];
      for (const l of P.logs) (l.wad ? blows : ghosts).push(kitLog(l, l.wad ? fb : fg, l.wad));
      for (const p of P.authored) if (p.kind === 'hero_ghost') ghosts.push(kitLog(p, fg, false));
      const kitRock = (b) => {
        const c = toW(b.x, b.y, b.z);
        e.set(0, b.yaw || 0, 0); q.setFromEuler(e);
        const k = b.r / (fr.len / 2);
        m.compose(c.clone().add(new THREE.Vector3(0, -b.r * 0.25, 0)), q, s.set(k, k * (b.sq || 0.7) * 1.25, k * (0.85 + 0.3 * (b.seed || 0.5))));
        return { pos: c, matrix: m.clone(), color: [1, 1, 1] };
      };
      for (const b of P.boulders) krocks.push(kitRock(b));
      for (const p of P.authored) if (p.kind === 'boulder') krocks.push(kitRock(p));
      for (const p of P.authored) if (p.kind === 'slab') rocks.push(rockOf(p, [0.42, 0.41, 0.38]));    // (slabs stay boxes)
      const addKit = (name, M, list, range) => {
        const mesh = new THREE.InstancedMesh(M.all, kitPropMaterial(uniforms, tex, world, M.maps), Math.max(1, list.length));
        mesh.name = `Wild_${name}`; mesh.frustumCulled = false; mesh.count = 0;
        this.kinds.push({ name, mesh, list, range });
      };
      addKit('Logs', K.chestnut_log_2, ghosts, 320);
      addKit('Blowdowns', K.blowdown_log, blows, 320);
      addKit('Boulders', K.creek_boulder, krocks, 380);
      const slabs = rocks.filter((it) => it.color[0] > 0.4);
      if (slabs.length) add('Slabs', setColor(boulderGeometry(1, 3), [1, 1, 1]), slabs, 0.3, 400);
    } else {
      add('Logs', setColor(logGeometry(), [1, 1, 1]), logs, 0.7, 320);
      add('RootWads', setColor(boulderGeometry(1, 9), [1, 1, 1]), wads, 0.0, 260);
      add('Boulders', setColor(boulderGeometry(2, 3), [1, 1, 1]), rocks, 0.85, 380);
    }
    // authored, merged: the footlog (a sawn log + handrail), the overlook wall
    const parts = [];
    for (const p of P.authored) {
      if (p.kind === 'footlog') {
        const a = toW(p.x0, p.y0, p.z - p.r), b = toW(p.x1, p.y1, p.z - p.r), d = b.clone().sub(a), L = d.length();
        const dir = d.clone().normalize(), side = new THREE.Vector3(-dir.z, 0, dir.x).multiplyScalar(p.rail_side);
        const log = logGeometry(12, 4);
        log.applyMatrix4(new THREE.Matrix4().compose(a, new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(1, 0, 0), dir), new THREE.Vector3(L, p.r, p.r * 1.02)));
        parts.push(setColor(log.toNonIndexed(), [0.32, 0.24, 0.16]));
        const deck = new THREE.BoxGeometry(L, 0.06, 0.62);
        deck.applyMatrix4(new THREE.Matrix4().compose(a.clone().add(b).multiplyScalar(0.5).add(new THREE.Vector3(0, p.r - 0.03, 0)),
          new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(1, 0, 0), dir), new THREE.Vector3(1, 1, 1)));
        parts.push(setColor(deck.toNonIndexed(), [0.55, 0.45, 0.32]));
        for (let t = 0; t <= L + 0.01; t += 2) {
          const base = a.clone().addScaledVector(dir, t).addScaledVector(side, 0.55).add(new THREE.Vector3(0, p.r, 0));
          const post = new THREE.BoxGeometry(0.1, 1.05, 0.1); post.translate(base.x, base.y + 0.52, base.z);
          parts.push(setColor(post.toNonIndexed(), [0.3, 0.22, 0.14]));
        }
        const rail = new THREE.BoxGeometry(L, 0.08, 0.08);
        rail.applyMatrix4(new THREE.Matrix4().compose(a.clone().add(b).multiplyScalar(0.5).addScaledVector(side, 0.55).add(new THREE.Vector3(0, p.r + 1.02, 0)),
          new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(1, 0, 0), dir), new THREE.Vector3(1, 1, 1)));
        parts.push(setColor(rail.toNonIndexed(), [0.3, 0.22, 0.14]));
      }
      if (p.kind === 'swing_bridge') {
        // a swinging footbridge: plank deck on two sagging cables, wooden towers at each end, cable
        // handrails on hangers (the deck colliders are in colliders.bin)
        const A = toW(p.x0, p.y0, p.z0), B = toW(p.x1, p.y1, p.z1);
        const dir = B.clone().sub(A).setY(0).normalize(), sd = new THREE.Vector3(-dir.z, 0, dir.x), L = A.distanceTo(B);
        const at = (t) => A.clone().lerp(B, t).add(new THREE.Vector3(0, -p.sag * 4 * t * (1 - t), 0));
        const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(1, 0, 0), dir);
        const seg = (a, b, w, h, c) => {           // a box from a to b (w across, h tall)
          const d = b.clone().sub(a), len = d.length();
          const bx = new THREE.BoxGeometry(len, h, w);
          bx.applyMatrix4(new THREE.Matrix4().compose(a.clone().add(b).multiplyScalar(0.5),
            new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(1, 0, 0), d.normalize()), new THREE.Vector3(1, 1, 1)));
          parts.push(setColor(bx.toNonIndexed(), c));
        };
        const WOOD = [0.34, 0.27, 0.19], CABLE = [0.1, 0.1, 0.1], POST = [0.26, 0.2, 0.14];
        const np_ = Math.max(8, Math.round(L / 0.32));
        for (let k = 0; k < np_; k++) {                 // planks across
          const c = at((k + 0.5) / np_);
          const pl = new THREE.BoxGeometry(0.22, 0.05, p.width);
          pl.applyMatrix4(new THREE.Matrix4().compose(c.clone().add(new THREE.Vector3(0, -0.03, 0)), q, new THREE.Vector3(1, 1, 1)));
          parts.push(setColor(pl.toNonIndexed(), k % 7 === 3 ? [0.28, 0.22, 0.16] : WOOD));
        }
        const hw = p.width / 2, ns = 24;
        for (const s_ of [-1, 1]) {
          const off = sd.clone().multiplyScalar(s_ * (hw + 0.05));
          for (let k = 0; k < ns; k++) {               // the deck stringers and the handrail cable
            const t0 = k / ns, t1 = (k + 1) / ns;
            seg(at(t0).add(off), at(t1).add(off), 0.09, 0.12, [0.22, 0.17, 0.12]);
            const cab = (t) => at(t).add(off).add(new THREE.Vector3(0, 1.1 + (p.tower - 1.1) * Math.pow(Math.abs(2 * t - 1), 2.2) * 0.9, 0));
            seg(cab(t0), cab(t1), 0.04, 0.04, CABLE);
            if (k % 2 === 0) seg(at(t0).add(off), cab(t0), 0.02, 0.02, CABLE);          // hangers
          }
          for (const [E, t] of [[A, 0], [B, 1]]) {      // towers: a pair of posts at each end, a cap
            const base = E.clone().add(off.clone().multiplyScalar(1.25)).addScaledVector(dir, t ? 0.4 : -0.4);
            seg(base.clone().add(new THREE.Vector3(0, -0.6, 0)), base.clone().add(new THREE.Vector3(0, p.tower + 0.2, 0)), 0.28, 0.28, POST);
          }
        }
        for (const [E, t] of [[A, 0], [B, 1]]) {
          const c0 = E.clone().addScaledVector(dir, t ? 0.4 : -0.4).add(new THREE.Vector3(0, p.tower + 0.1, 0));
          seg(c0.clone().addScaledVector(sd, -hw - 0.5), c0.clone().addScaledVector(sd, hw + 0.5), 0.3, 0.3, POST);
          // the timber crib under the deck end and the steps up to it from the bank
          const zg = t ? p.ground1 : p.ground0, zt = E.y;
          if (zt - zg > 0.3) {
            const crib = new THREE.BoxGeometry(2.4, zt - zg + 0.6, p.width + 1.4);
            crib.applyMatrix4(new THREE.Matrix4().compose(E.clone().addScaledVector(dir, t ? 0.9 : -0.9).setY((zt + zg) / 2 - 0.3), q, new THREE.Vector3(1, 1, 1)));
            parts.push(setColor(crib.toNonIndexed(), [0.24, 0.19, 0.14]));
            const steps = (t ? p.steps1 : p.steps0) || [];
            for (const [sx, sy, top] of steps) {
              const st = new THREE.BoxGeometry(p.tread + 0.02, 0.08, 0.95);
              st.applyMatrix4(new THREE.Matrix4().compose(toW(sx, sy, top - 0.04), q, new THREE.Vector3(1, 1, 1)));
              parts.push(setColor(st.toNonIndexed(), WOOD));
            }
            if (steps.length) {
              const [lx, ly, ltop, lg] = steps[steps.length - 1];
              for (const s2 of [-1, 1]) seg(toW(lx, ly, lg).addScaledVector(sd, s2 * 0.5), E.clone().addScaledVector(sd, s2 * 0.5).setY(zt), 0.12, 0.2, POST);
            }
          }
        }
      }
      if (p.kind === 'rail') {
        // the old rail line along the river road: ties every 0.65 m, two rails (1.435 m gauge)
        const pts = p.pts.map(([x, y, z]) => toW(x, y, z));
        let acc = 0;
        for (let k = 1; k < pts.length; k++) {
          const a = pts[k - 1], b = pts[k], d = b.clone().sub(a), len = d.length();
          const dir = d.clone().setY(0).normalize(), sd = new THREE.Vector3(-dir.z, 0, dir.x);
          const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(1, 0, 0), d.clone().normalize());
          const gnd = p.pts[k][3];
          if (gnd !== undefined && a.y - gnd > 0.2) {          // the embankment under the line beyond the square
            const hgt = a.y - gnd + 0.3, wb = 3.6 + hgt * 1.4;
            const em = new THREE.CylinderGeometry(1.9, wb, hgt, 4, 1, false, Math.PI / 4);
            em.rotateY(Math.PI / 4); em.scale(len / (1.9 * Math.SQRT2), 1, 1);
            em.applyMatrix4(new THREE.Matrix4().compose(a.clone().add(b).multiplyScalar(0.5).add(new THREE.Vector3(0, -hgt / 2 - 0.02, 0)),
              new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(1, 0, 0), dir), new THREE.Vector3(1, 1, 1)));
            parts.push(setColor(em.toNonIndexed(), [0.2, 0.18, 0.15]));
          }
          for (const s_ of [-0.72, 0.72]) {
            const r_ = new THREE.BoxGeometry(len + 0.02, 0.15, 0.08);
            r_.applyMatrix4(new THREE.Matrix4().compose(a.clone().add(b).multiplyScalar(0.5).addScaledVector(sd, s_).add(new THREE.Vector3(0, 0.2, 0)), q, new THREE.Vector3(1, 1, 1)));
            parts.push(setColor(r_.toNonIndexed(), [0.2, 0.13, 0.09]));       // rusty steel
          }
          for (; acc < len; acc += 0.65) {
            const c = a.clone().addScaledVector(d, acc / len);
            const tie = new THREE.BoxGeometry(0.22, 0.14, 2.5);
            tie.applyMatrix4(new THREE.Matrix4().compose(c.add(new THREE.Vector3(0, 0.07, 0)), q, new THREE.Vector3(1, 1, 1)));
            parts.push(setColor(tie.toNonIndexed(), [0.16, 0.13, 0.1]));
          }
          acc -= len;
        }
      }
      if (p.kind === 'wall') {
        const a = toW(p.x0, p.y0, p.z), b = toW(p.x1, p.y1, p.z), L = a.distanceTo(b);
        const w = new THREE.BoxGeometry(L, p.h + 0.6, p.t);
        w.translate((a.x + b.x) / 2, p.z + (p.h - 0.6) / 2, (a.z + b.z) / 2);
        parts.push(setColor(w.toNonIndexed(), [0.42, 0.4, 0.36]));
      }
    }
    this.authored = null;
    if (parts.length) {
      const g = mergeGeometries(parts.map((p) => { p.deleteAttribute('uv'); return p; }));
      this.authored = new THREE.Mesh(g, litMaterial(uniforms, tex, world, { mossy: 0.15 }));
      this.authored.name = 'Wild_Authored';
    }
    this.group = new THREE.Group();
    for (const k of this.kinds) this.group.add(k.mesh);
    if (this.authored) this.group.add(this.authored);
    this._last = new THREE.Vector3(1e9, 0, 0);
    this.stats = {};
  }

  update(camera) {
    const c = camera.position;
    if (c.distanceToSquared(this._last) < 16) return;
    this._last.copy(c);
    const col = new THREE.Color();
    for (const k of this.kinds) {
      let n = 0;
      for (const it of k.list) {
        if (it.pos.distanceToSquared(c) > k.range * k.range) continue;
        k.mesh.setMatrixAt(n, it.matrix);
        k.mesh.setColorAt(n, col.setRGB(...it.color));
        n++;
      }
      k.mesh.count = n;
      k.mesh.instanceMatrix.needsUpdate = true;
      if (k.mesh.instanceColor) k.mesh.instanceColor.needsUpdate = true;
      this.stats[k.name] = n;
    }
  }
}

// ---------------------------------------------------------------- the estate, seen from outside
// A stand-in (one merged mesh, ~5k triangles): lawn, terrace, the white house (two floors, the
// courtyard open, glass bands), the hedge with the gate, the pool, Italian cypresses.
export function buildEstate(world, uniforms, tex) {
  const E = world.estate, oy = world.meta.estate_offset[1];
  const parts = [];
  const box = (x0, y0, x1, y1, z0, z1, c) => {
    const g = new THREE.BoxGeometry(x1 - x0, z1 - z0, y1 - y0);
    g.translate((x0 + x1) / 2, (z0 + z1) / 2, -((y0 + y1) / 2 - oy));
    parts.push(setColor(g.toNonIndexed(), c));
  };
  const WHITE = [0.78, 0.76, 0.72], GLASS = [0.05, 0.065, 0.08], LAWN = [0.07, 0.16, 0.03], STONE = [0.5, 0.47, 0.4];
  const HEDGE = [0.025, 0.06, 0.018], CYP = [0.012, 0.03, 0.012], POOL = [0.05, 0.22, 0.3];
  const [lx0, ly0, lx1, ly1] = E.lawn.rect;
  box(lx0, ly0, lx1, ly1, E.lawn.z - 0.5, E.lawn.z, LAWN);
  const [tx0, ty0, tx1, ty1] = E.terrace.rect;
  box(tx0, ty0, tx1, ty1, E.lawn.z, 0.05, STONE);
  for (const h of E.house) {
    const [x0, y0, x1, y1] = h.rect;
    if (h.hole) {
      const [hx0, hy0, hx1, hy1] = h.hole;
      box(x0, y0, x1, hy0, h.z0, h.z1, WHITE); box(x0, hy1, x1, y1, h.z0, h.z1, WHITE);
      box(x0, hy0, hx0, hy1, h.z0, h.z1, WHITE); box(hx1, hy0, x1, hy1, h.z0, h.z1, WHITE);
      box(hx0, hy0, hx1, hy1, 0, 0.1, [0.3, 0.35, 0.2]);        // the courtyard's planting
    } else box(x0, y0, x1, y1, h.z0, h.z1 + 0.05, WHITE);
  }
  for (const gb of E.glass_bands) {
    const [z0, z1] = gb.z;
    if (gb.face === 's') box(gb.x[0], -20.08, gb.x[1], -20.0, z0, z1, GLASS);
    if (gb.face === 'n') box(gb.x[0], 20.0, gb.x[1], 20.08, z0, z1, GLASS);
    if (gb.face === 'w') box(-26.08, gb.y[0], -26.0, gb.y[1], z0, z1, GLASS);
  }
  const H = E.hedge, [hx0, hy0, hx1, hy1] = H.rect, t = H.thick / 2;
  box(hx0 - t, hy1 - t, hx1 + t, hy1 + t, 0, H.height, HEDGE);
  box(hx0 - t, hy0 - t, hx0 + t, hy1 + t, 0, H.height, HEDGE);
  box(hx1 - t, hy0 - t, hx1 + t, hy1 + t, 0, H.height, HEDGE);
  box(hx0 - t, hy0 - t, H.gap[0], hy0 + t, 0, H.height, HEDGE);
  box(H.gap[1], hy0 - t, hx1 + t, hy0 + t, 0, H.height, HEDGE);
  // gate piers and the two leaves, standing open inward
  const G = E.gate;
  box(G.x[0] - G.pier, G.y - 0.6, G.x[0], G.y + 0.6, 0, G.height, STONE);
  box(G.x[1], G.y - 0.6, G.x[1] + G.pier, G.y + 0.6, 0, G.height, STONE);
  box(G.x[0] + 0.05, G.y + 0.2, G.x[0] + 0.15, G.y + 5.6, 0.1, 2.6, [0.1, 0.1, 0.1]);
  box(G.x[1] - 0.15, G.y + 0.2, G.x[1] - 0.05, G.y + 5.6, 0.1, 2.6, [0.1, 0.1, 0.1]);
  const [px0, py0, px1, py1] = E.pool.rect;
  box(px0 - 1, py0 - 1, px1 + 1, py1 + 1, 0, 0.45, STONE);
  box(px0, py0, px1, py1, 0.45, 0.47, POOL);
  const [qx0, qy0, qx1, qy1] = E.pool_house.rect;
  box(qx0, qy0, qx1, qy1, 0, E.pool_house.z1, WHITE);
  for (const [x, y] of E.cypress) {
    const g = new THREE.ConeGeometry(E.cypress_r, E.cypress_height, 7, 1);
    g.translate(x, E.cypress_height / 2 + 0.3, -(y - oy));
    parts.push(setColor(g.toNonIndexed(), CYP));
    const tr = new THREE.CylinderGeometry(0.15, 0.2, 0.8, 5); tr.translate(x, 0.4, -(y - oy));
    parts.push(setColor(tr.toNonIndexed(), [0.1, 0.07, 0.05]));
  }
  // the town downstream (world.json town: not built yet, a later level), as the ring shows it from the
  // river corridor: a water tower, a white steeple, the truss bridge, a mill and its stack, houses
  const T = world.meta.town;
  for (const gl of T?.glimpses || []) {
    const W = (x, y, z) => new THREE.Vector3(x, z, -(y - oy));
    if (gl.kind === 'water_tower') {
      for (const [dx, dy] of [[-2.5, -2.5], [2.5, -2.5], [2.5, 2.5], [-2.5, 2.5]]) {
        const leg = new THREE.CylinderGeometry(0.25, 0.3, gl.h - 6, 5); leg.translate(gl.x + dx, gl.z + (gl.h - 6) / 2, -(gl.y + dy - oy));
        parts.push(setColor(leg.toNonIndexed(), [0.45, 0.46, 0.45]));
      }
      const tank = new THREE.CylinderGeometry(4.2, 4.2, 5.5, 14); tank.translate(gl.x, gl.z + gl.h - 3.2, -(gl.y - oy));
      parts.push(setColor(tank.toNonIndexed(), [0.66, 0.67, 0.65]));
      const cap = new THREE.ConeGeometry(4.4, 2.2, 14); cap.translate(gl.x, gl.z + gl.h + 0.6, -(gl.y - oy));
      parts.push(setColor(cap.toNonIndexed(), [0.55, 0.56, 0.55]));
    } else if (gl.kind === 'steeple') {
      box(gl.x - 5, gl.y - 9, gl.x + 5, gl.y + 9, gl.z, gl.z + 7, [0.8, 0.79, 0.75]);
      box(gl.x - 2, gl.y - 11.5, gl.x + 2, gl.y - 7.5, gl.z, gl.z + gl.h - 7, [0.82, 0.81, 0.77]);
      const sp = new THREE.ConeGeometry(2.0, 7.5, 6); sp.translate(gl.x, gl.z + gl.h - 3.2, -(gl.y - 9.5 - oy));
      parts.push(setColor(sp.toNonIndexed(), [0.78, 0.78, 0.76]));
      const roof = new THREE.CylinderGeometry(0.01, 6.2, 3.0, 4, 1); roof.rotateY(Math.PI / 4); roof.scale(1, 1, 1.75); roof.translate(gl.x, gl.z + 8.5, -(gl.y - oy));
      parts.push(setColor(roof.toNonIndexed(), [0.18, 0.19, 0.2]));
    } else if (gl.kind === 'truss_bridge') {
      const a = W(gl.x0, gl.y0, gl.z + gl.h), b = W(gl.x1, gl.y1, gl.z + gl.h), L = a.distanceTo(b);
      const dir = b.clone().sub(a).normalize(), sd = new THREE.Vector3(-dir.z, 0, dir.x);
      const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(1, 0, 0), dir);
      const bx = (c, len, h, w, col) => { const g_ = new THREE.BoxGeometry(len, h, w); g_.applyMatrix4(new THREE.Matrix4().compose(c, q, new THREE.Vector3(1, 1, 1))); parts.push(setColor(g_.toNonIndexed(), col)); };
      const mid = a.clone().add(b).multiplyScalar(0.5), STEEL = [0.14, 0.17, 0.15];
      bx(mid, L, 0.6, 7.5, [0.2, 0.2, 0.2]);                           // deck
      for (const s_ of [-3.6, 3.6]) {
        bx(mid.clone().addScaledVector(sd, s_).add(new THREE.Vector3(0, 5.5, 0)), L * 0.86, 0.5, 0.4, STEEL);   // top chord
        for (let k = 0; k <= 8; k++) {                                   // verticals / diagonals
          const c = a.clone().lerp(b, 0.07 + 0.86 * k / 8).addScaledVector(sd, s_).add(new THREE.Vector3(0, 2.8, 0));
          const v_ = new THREE.BoxGeometry(0.35, 5.6, 0.35); v_.translate(c.x, c.y, c.z); parts.push(setColor(v_.toNonIndexed(), STEEL));
        }
      }
      for (const E of [a, b]) { const pier = new THREE.BoxGeometry(3, gl.h + 2, 9); pier.translate(E.x, E.y - (gl.h + 2) / 2, E.z); parts.push(setColor(pier.toNonIndexed(), [0.45, 0.43, 0.4])); }
    } else if (gl.kind === 'tipple') {                                   // the old tannery / mill and its stack
      box(gl.x - 16, gl.y - 7, gl.x + 16, gl.y + 7, gl.z, gl.z + 9, [0.36, 0.18, 0.12]);
      box(gl.x + 10, gl.y + 2, gl.x + 12.5, gl.y + 4.5, gl.z, gl.z + gl.h + 14, [0.33, 0.16, 0.11]);
    } else if (gl.kind === 'house') {
      const ROOFS = [[0.2, 0.2, 0.22], [0.38, 0.12, 0.08], [0.16, 0.26, 0.18]];
      const body = new THREE.BoxGeometry(gl.w, gl.h, gl.d); body.rotateY(gl.yaw); body.translate(gl.x, gl.z + gl.h / 2, -(gl.y - oy));
      parts.push(setColor(body.toNonIndexed(), [0.78, 0.76, 0.7]));
      const roof = new THREE.CylinderGeometry(0.01, gl.d * 0.75, 2.6, 4, 1); roof.rotateY(Math.PI / 4); roof.scale(gl.w / gl.d, 1, 1);
      roof.rotateY(gl.yaw); roof.translate(gl.x, gl.z + gl.h + 1.3, -(gl.y - oy));
      parts.push(setColor(roof.toNonIndexed(), ROOFS[gl.roof % 3]));
    }
  }
  const g = mergeGeometries(parts.map((p) => { p.deleteAttribute('uv'); if (p.attributes.normal === undefined) p.computeVertexNormals(); return p; }));
  const mesh = new THREE.Mesh(g, litMaterial(uniforms, tex, world, { useMap: false }));
  mesh.name = 'Wild_Estate';
  return mesh;
}

// estate colliders (three.js boxes): the hedge, piers and the house (the gate stays open)
export function estateColliders(world) {
  const E = world.estate, oy = world.meta.estate_offset[1], out = [];
  const b = (x0, y0, x1, y1, z0, z1) => { const bx = new THREE.Box3(new THREE.Vector3(x0, z0, -(y1 - oy)), new THREE.Vector3(x1, z1, -(y0 - oy))); bx.fixed = true; out.push(bx); };
  const H = E.hedge, [hx0, hy0, hx1, hy1] = H.rect, t = H.thick / 2;
  b(hx0 - t, hy1 - t, hx1 + t, hy1 + t, -1, H.height);
  b(hx0 - t, hy0 - t, hx0 + t, hy1 + t, -1, H.height);
  b(hx1 - t, hy0 - t, hx1 + t, hy1 + t, -1, H.height);
  b(hx0 - t, hy0 - t, E.gate.x[0], hy0 + t, -1, H.height);
  b(E.gate.x[1], hy0 - t, hx1 + t, hy0 + t, -1, H.height);
  for (const h of E.house) { const [x0, y0, x1, y1] = h.rect; b(x0, y0, x1, y1, -1, h.z1); }
  return out;
}
