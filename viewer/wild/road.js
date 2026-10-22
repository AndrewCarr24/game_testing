import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { ATMOSPHERE_PARS } from './atmosphere.js';

// The county road (blender/wilderness/levels/laurel_fork_road.py -> world/road.json): the estate's
// drive leaves the gate as a two-lane concrete road, four hairpins down the cove's north wall to
// the Laurel River, then west along its north bank out of the square and down the valley to the
// town's edge. Two draw calls:
//   Wild_Road         the slab: 7.0 m of concrete (two 3.35 m lanes) between 1.2 m gravel
//                     shoulders, all procedural in the shader from (across, along) metres: the
//                     concrete's mottle and aggregate, saw-cut joints every 4.5 m and the centre
//                     joint, darker wheel paths, a double yellow centre line, white edge lines
//   Wild_RoadFurniture guardrails (galvanised W-beam on posts every 1.9 m) where the fill side
//                     drops, and culverts (a concrete headwall and a dark pipe mouth at each end)
// Lit like the rest of the wilderness: the low sun x the level's light map (terrain and canopy
// shadow) + sky, then aerial perspective. It sits on the corridor's flat core; distant vertices are
// pulled a little toward the camera so the terrain's coarser far LODs don't swallow it.

const LIT = /* glsl */`
uniform vec3 uSunColor, uSkyColor;
uniform sampler2D uLight;
uniform vec4 uMapXf;
vec3 litColor(vec3 alb, vec3 n, vec3 wpos) {
  vec4 l = textureLod(uLight, (wpos.xz - uMapXf.xy) * uMapXf.z, 0.0);
  if (uMapXf.w < 0.5) l = vec4(1.0);
  float ndl = clamp(dot(n, uSunDir), 0.0, 1.0);
  return alb * (uSunColor * ndl * l.a * l.g + uSkyColor * l.b * (0.6 + 0.4 * n.y));
}`;

const PULL = /* glsl */`
  // (pull distant vertices toward the eye: the terrain's far LODs are coarser than the road)
  vec3 toCam = cameraPosition - w.xyz;
  float dc = length(toCam);
  w.xyz += toCam / max(dc, 1e-3) * min(dc * 0.004, 6.0) * step(30.0, dc);
`;

// the slab's surface (albedo) from (across, along) metres: shared with the house's stretch of it
// (viewer/estate_gate.js, inside the house level's lawn edge)
export const ROAD_SURFACE = /* glsl */`
      float h2(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
      float vn(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
        return mix(mix(h2(i), h2(i + vec2(1, 0)), f.x), mix(h2(i + vec2(0, 1)), h2(i + vec2(1, 1)), f.x), f.y); }
      float band(float x, float a, float b, float aa) { return smoothstep(a - aa, a + aa, x) * (1.0 - smoothstep(b - aa, b + aa, x)); }
      vec3 roadSurface(vec2 uv, float uHalf, float uJoint) {
        float u = uv.x, v = uv.y, au = abs(u);
        float aa = max(fwidth(u), 0.01) * 0.75;
        vec2 wp = vec2(u, v);
        vec3 col;
        if (au < uHalf) {
          // concrete: a pale warm grey, mottled per slab and at a few scales, aggregate speckle,
          // darker wheel paths (oil and rubber) and the faint lane centre stain
          float slabId = floor(v / uJoint) + (u > 0.0 ? 0.5 : 0.0);
          float m = 0.55 * vn(wp * 0.45) + 0.3 * vn(wp * 1.7) + 0.15 * vn(wp * 9.0);
          col = vec3(0.30, 0.295, 0.28) * (0.86 + 0.22 * m) * (0.95 + 0.1 * h2(vec2(slabId, 3.1)));
          col *= 0.93 + 0.14 * h2(floor(wp * 90.0));
          float lane = au - 1.675;                          // the lane's own centre (3.35 m lanes)
          float wheel = band(abs(lane), 0.55, 1.05, 0.25);
          col *= 1.0 - 0.13 * wheel - 0.08 * band(abs(lane), 0.0, 0.25, 0.2);
          // saw-cut joints: transverse every uJoint m, longitudinal at the centre (under the paint)
          float jt = abs(fract(v / uJoint + 0.5) - 0.5) * uJoint;
          col *= 1.0 - 0.55 * (1.0 - smoothstep(0.004, 0.012 + fwidth(v), jt));
          // paint: double yellow centre line (two 0.12 m lines 0.10 m apart), white edge lines
          float yel = band(au, 0.05, 0.17, aa);
          float wht = band(au, uHalf - 0.17, uHalf - 0.05, aa);
          float wear = 0.82 + 0.18 * vn(wp * vec2(6.0, 0.7));
          col = mix(col, vec3(0.62, 0.42, 0.04) * wear, yel * 0.95);
          col = mix(col, vec3(0.70, 0.70, 0.67) * wear, wht * 0.95);
        } else {
          // gravel shoulders, dusty at the slab's edge
          float m = vn(wp * 2.3) * 0.6 + 0.4 * h2(floor(wp * 40.0));
          col = vec3(0.16, 0.135, 0.10) * (0.75 + 0.5 * m);
          col = mix(col, vec3(0.22, 0.2, 0.17), 0.5 * (1.0 - smoothstep(0.0, 0.5, au - uHalf)));
        }
        return col;
      }`;

export async function buildRoad(world, uniforms, tex, base = '../build/wilderness') {
  let R;
  try {
    const res = await fetch(`${base}/${world.name}/world/road.json`);
    if (!res.ok) return null;
    R = await res.json();
  } catch { return null; }
  const pts = [...R.points, ...(R.ring || [])].map((p) => new THREE.Vector3(...p));
  const inSquare = R.points.length;
  const n = pts.length;
  // arc length, tangents, right-hand normals (three: x east, z south; right of travel)
  const s = new Float32Array(n), right = [];
  for (let i = 1; i < n; i++) s[i] = s[i - 1] + Math.hypot(pts[i].x - pts[i - 1].x, pts[i].z - pts[i - 1].z);
  for (let i = 0; i < n; i++) {
    const a = pts[Math.max(0, i - 2)], b = pts[Math.min(n - 1, i + 2)];
    const t = new THREE.Vector3(b.x - a.x, 0, b.z - a.z).normalize();
    right.push(new THREE.Vector3(-t.z, 0, t.x));
  }
  const half = R.paved / 2, W = half + R.shoulder;
  const sAt = (si) => {                 // centreline point + right at arc length si
    let lo = 0, hi = n - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (s[m] <= si) lo = m; else hi = m; }
    const t = (si - s[lo]) / Math.max(1e-6, s[hi] - s[lo]);
    return { p: pts[lo].clone().lerp(pts[hi], t), r: right[lo].clone().lerp(right[hi], t).normalize(), i: lo };
  };

  // ---- the slab: 6 vertices across (shoulder edge, edge line, centre, ...), the shoulders'
  // outer edge tucked 6 cm down into the ground
  const across = [-W - 0.25, -half, -0.0, half, W + 0.25];
  const drop = [-0.12, 0, 0, 0, -0.12];
  const P = new Float32Array(n * across.length * 3), UV = new Float32Array(n * across.length * 2);
  for (let i = 0; i < n; i++) for (let k = 0; k < across.length; k++) {
    const v = (i * across.length + k), o = across[k];
    P[v * 3] = pts[i].x + right[i].x * o; P[v * 3 + 1] = pts[i].y + 0.05 + drop[k]; P[v * 3 + 2] = pts[i].z + right[i].z * o;
    UV[v * 2] = o; UV[v * 2 + 1] = s[i];
  }
  const idx = [];
  for (let i = 0; i < n - 1; i++) for (let k = 0; k < across.length - 1; k++) {
    const a = i * across.length + k, b = a + 1, c = a + across.length, d = c + 1;
    idx.push(a, b, c, b, d, c);              // (counter-clockwise seen from above)
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(P, 3));
  g.setAttribute('uv', new THREE.BufferAttribute(UV, 2));
  g.setIndex(idx);
  g.computeVertexNormals();
  g.computeBoundingSphere();
  const mapXf = new THREE.Vector4(-world.size / 2, -world.size / 2, 1 / world.size, 1);
  const slab = new THREE.ShaderMaterial({
    uniforms: { ...uniforms, uLight: { value: tex.light }, uMapXf: { value: mapXf }, uHalf: { value: half }, uJoint: { value: R.joint || 4.5 } },
    vertexShader: /* glsl */`
      varying vec3 vWorld, vN; varying vec2 vUv;
      void main() {
        vec4 w = modelMatrix * vec4(position, 1.0);
        vN = normalize(mat3(modelMatrix) * normal); vUv = uv;
        ${PULL}
        vWorld = (modelMatrix * vec4(position, 1.0)).xyz;
        gl_Position = projectionMatrix * viewMatrix * w;
      }`,
    fragmentShader: /* glsl */`
      uniform float uHalf, uJoint;
      varying vec3 vWorld, vN; varying vec2 vUv;
      ${ATMOSPHERE_PARS}
      ${LIT}
      ${ROAD_SURFACE}
      void main() {
        vec3 col = roadSurface(vUv, uHalf, uJoint);
        vec3 n = normalize(vN);
        gl_FragColor = vec4(applyAtmosphere(litColor(col, n, vWorld), vWorld), 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
    polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2,
  });
  slab.extensions = { derivatives: true };
  const road = new THREE.Mesh(g, slab);
  road.name = 'Wild_Road';
  road.frustumCulled = false;

  // ---- furniture: guardrails and culverts, one merged vertex-coloured mesh
  const parts = [];
  const col = (geo, c) => {
    const a = new Float32Array(geo.attributes.position.count * 3);
    for (let i = 0; i < a.length; i += 3) { a[i] = c[0]; a[i + 1] = c[1]; a[i + 2] = c[2]; }
    geo.setAttribute('color', new THREE.BufferAttribute(a, 3));
    if (geo.attributes.uv) geo.deleteAttribute('uv');
    if (geo.attributes.normal) geo.deleteAttribute('normal');
    return geo;
  };
  const STEEL = [0.42, 0.44, 0.45], POST = [0.34, 0.35, 0.36], CONC = [0.36, 0.35, 0.33], DARK = [0.02, 0.02, 0.02];
  const up = new THREE.Vector3(0, 1, 0);
  const place = (geo, p, r, c) => {               // geo authored with x = across (right), z = along
    const fwd = new THREE.Vector3().crossVectors(r, up).negate();
    const m = new THREE.Matrix4().makeBasis(r, up, fwd).setPosition(p);
    parts.push(col(geo.applyMatrix4(m), c));
  };
  let railM = 0, posts = 0;
  for (const rail of R.rails || []) {
    const [s0, s1] = rail.s, off = rail.side * (half + 1.0);
    // the W-beam: a ribbon 0.31 m deep (0.55-0.86 m up), double-sided by two faces
    const N = Math.max(2, Math.ceil((s1 - s0) / 2)), bp = [], bi = [];
    for (let k = 0; k <= N; k++) {
      const { p, r } = sAt(s0 + ((s1 - s0) * k) / N);
      const c = p.clone().addScaledVector(r, off);
      for (const [dy, dx] of [[0.55, 0], [0.70, 0.07 * rail.side], [0.86, 0]]) bp.push(c.x + r.x * dx, c.y + dy, c.z + r.z * dx);
    }
    for (let k = 0; k < N; k++) for (let j = 0; j < 2; j++) {
      const a = k * 3 + j, b = a + 1, cc = a + 3, d = cc + 1;
      bi.push(a, cc, b, b, cc, d, a, b, cc, b, d, cc);
    }
    const bg = new THREE.BufferGeometry();
    bg.setAttribute('position', new THREE.Float32BufferAttribute(bp, 3));
    bg.setIndex(bi);
    parts.push(col(bg.toNonIndexed(), STEEL));
    railM += s1 - s0;
    for (let si = s0; si <= s1; si += 1.905) {
      const { p, r } = sAt(si);
      const pg = new THREE.BoxGeometry(0.15, 1.3, 0.15).translate(0, 0.25, 0);
      place(pg, p.clone().addScaledVector(r, off + 0.12 * rail.side), r, POST);
      posts++;
    }
  }
  for (const c of R.culverts || []) {
    const { p, r } = sAt(c.s);
    for (const side of [1, -1]) {
      const L = side > 0 ? c.right : c.left;
      if (!(L > 0)) continue;
      // the pipe's end sits at the fill's toe (outlet) or the hollow's floor (inlet)
      const end = p.clone().addScaledVector(r, side * L);
      const gy = world.heightAt(end.x, end.z);
      end.y = gy;
      const head = new THREE.BoxGeometry(3.2, 1.7, 0.35).translate(0, 0.55, 0);
      place(head, end, r.clone().cross(up).negate().normalize().multiplyScalar(1), CONC);   // (faces along the pipe)
      const mouth = new THREE.CircleGeometry(0.55, 14).rotateY(side > 0 ? Math.PI / 2 : -Math.PI / 2).translate(side * 0.19, 0.6, 0);
      place(mouth, end, r, DARK);
    }
  }
  let furniture = null;
  if (parts.length) {
    const fg = mergeGeometries(parts.map((p) => (p.index ? p.toNonIndexed() : p)));
    fg.computeVertexNormals();
    const fm = new THREE.ShaderMaterial({
      uniforms: { ...uniforms, uLight: { value: tex.light }, uMapXf: { value: mapXf } },
      vertexColors: true, side: THREE.DoubleSide,
      vertexShader: /* glsl */`
        varying vec3 vWorld, vN, vCol;
        void main() {
          vec4 w = modelMatrix * vec4(position, 1.0);
          vWorld = w.xyz; vN = normalize(mat3(modelMatrix) * normal); vCol = color;
          gl_Position = projectionMatrix * viewMatrix * w;
        }`,
      fragmentShader: /* glsl */`
        varying vec3 vWorld, vN, vCol;
        ${ATMOSPHERE_PARS}
        ${LIT}
        void main() {
          vec3 n = normalize(vN);
          if (!gl_FrontFacing) n = -n;
          // galvanised steel: a little sky sheen on top of the diffuse
          vec3 c = litColor(vCol, n, vWorld) + vCol * uSkyColor * 0.25 * max(n.y, 0.0);
          gl_FragColor = vec4(applyAtmosphere(c, vWorld), 1.0);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }`,
    });
    furniture = new THREE.Mesh(fg, fm);
    furniture.name = 'Wild_RoadFurniture';
  }
  const group = new THREE.Group();
  group.name = 'Wild_County_Road';
  group.add(road);
  if (furniture) group.add(furniture);
  group.userData = { length: s[inSquare - 1], ringLength: s[n - 1] - s[inSquare - 1], rails: railM, posts, culverts: (R.culverts || []).length,
    // the centreline (three.js frame) for whoever drives it later (car_ev)
    centreline: pts, inSquare, sAt };
  return group;
}
