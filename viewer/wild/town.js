import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { ATMOSPHERE_PARS } from './atmosphere.js';
import { litMaterial } from './level.js';

// Sourwood (world.json "town", blender/wilderness/levels/laurel_town*.py; design/town/brief.md):
// the town's blockout in the wilderness runtime. One merged lit mesh for every static piece
// (buildings' massing and roofs, streets with lane markings, sidewalks, the truss bridge, the
// footbridge, the tunnel portal, vehicles, the evidence, the townspeople's stand-ins, street
// lights' poles) and one merged emissive mesh (neon, lit windows, the gas canopy's band, street
// light globes, the video store's monitors): two draw calls. Buildings whose kit glTF exists
// (world.json town.kit, design/town/kit_status.md) are drawn from the kit instead of boxes.
// Colliders are in colliders.bin (the world step). Exits: Exits below.

const C = {
  brick: [0.33, 0.15, 0.1], brick2: [0.4, 0.2, 0.13], brick3: [0.27, 0.13, 0.1], brick_dark: [0.24, 0.11, 0.08],
  white: [0.8, 0.79, 0.75], cream: [0.72, 0.66, 0.52], sage: [0.42, 0.48, 0.38], grey: [0.45, 0.45, 0.43],
  block: [0.6, 0.58, 0.54], roof: [0.16, 0.16, 0.17], tin: [0.33, 0.35, 0.35], shingle: [0.2, 0.17, 0.15],
  glass: [0.03, 0.04, 0.05], steel: [0.5, 0.5, 0.5], tank: [0.62, 0.64, 0.63], canopy: [0.82, 0.82, 0.8],
  asphalt: [0.055, 0.056, 0.06], asphalt2: [0.07, 0.07, 0.072], concrete: [0.38, 0.37, 0.35], yellow: [0.55, 0.42, 0.05],
  line: [0.62, 0.62, 0.6], truss: [0.07, 0.17, 0.1], stone: [0.36, 0.34, 0.31], black: [0.01, 0.01, 0.01],
  bar: [0.1, 0.08, 0.07], board: [0.32, 0.12, 0.09], pump: [0.7, 0.1, 0.08], gravel: [0.25, 0.23, 0.2],
};
const PASTEL = [[0.62, 0.72, 0.66], [0.78, 0.7, 0.55], [0.6, 0.66, 0.74], [0.8, 0.62, 0.58], [0.74, 0.74, 0.6], [0.66, 0.6, 0.7]];
const HOUSE = [[0.78, 0.77, 0.72], [0.55, 0.58, 0.5], [0.42, 0.46, 0.52], [0.7, 0.64, 0.5], [0.6, 0.38, 0.3]];
const BRICKS = [C.brick, C.brick2, C.brick3, [0.42, 0.3, 0.22], [0.5, 0.45, 0.38]];
const AWN = [[0.08, 0.24, 0.14], [0.35, 0.06, 0.08], [0.06, 0.1, 0.25], [0.5, 0.45, 0.35]];
const CARS = [[0.6, 0.6, 0.62], [0.08, 0.1, 0.16], [0.5, 0.06, 0.05], [0.8, 0.8, 0.78], [0.2, 0.25, 0.2], [0.12, 0.12, 0.12]];
const hash = (s) => { let h = 2166136261; for (const c of s) h = Math.imul(h ^ c.charCodeAt(0), 16777619); return (h >>> 0) / 4294967296; };
const pick = (arr, s) => arr[Math.floor(hash(s) * arr.length) % arr.length];
const VEH = { van: [5.9, 2.1, 2.5], cruiser: [5.1, 2.0, 1.8], suv: [4.9, 1.9, 1.7], car: [4.8, 1.85, 1.45], pickup: [5.9, 2.0, 1.9], train: [57, 3.1, 4.5] };

function setColor(g, c) {
  const n = g.attributes.position.count, a = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) a.set(c, i * 3);
  g.setAttribute('color', new THREE.BufferAttribute(a, 3));
  return g;
}

export function emissiveMaterial(uniforms) {
  return new THREE.ShaderMaterial({
    uniforms: { ...uniforms },
    vertexColors: true,
    vertexShader: /* glsl */`
      varying vec3 vWorld, vCol;
      void main() { vec4 w = modelMatrix * vec4(position, 1.0); vWorld = w.xyz; vCol = color; gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: /* glsl */`
      varying vec3 vWorld, vCol;
      ${ATMOSPHERE_PARS}
      void main() {
        gl_FragColor = vec4(applyAtmosphere(vCol, vWorld), 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}

export class Town {
  constructor(world, uniforms, tex) {
    const T = world.meta.town, oy = world.meta.estate_offset[1];
    this.world = world; this.town = T;
    const lit = [], glow = [];
    const kitHas = new Set(params0().get('kit') === '0' ? [] : T.kit || []);
    if (params0().get('kit') === '0') { for (const b of T.buildings) b.kit = false; T.kit = []; }
    const W = (x, y, z) => new THREE.Vector3(x, z, -(y - oy));
    // an asset-frame box (u across, v back, z up) placed by a building / object frame
    const place = (x, y, z, yawDeg) => new THREE.Matrix4().compose(W(x, y, z), new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), yawDeg * Math.PI / 180), new THREE.Vector3(1, 1, 1));
    const abox = (M, x0, y0, z0, x1, y1, z1, col, out = lit) => {
      if (x1 - x0 < 1e-3 || y1 - y0 < 1e-3 || z1 - z0 < 1e-3) return;
      const g = new THREE.BoxGeometry(x1 - x0, z1 - z0, y1 - y0);
      g.translate((x0 + x1) / 2, (z0 + z1) / 2, -(y0 + y1) / 2);
      g.applyMatrix4(M);
      out.push(setColor(g.toNonIndexed(), col));
    };
    // ---- buildings
    for (const b of T.buildings) {
      if (b.kit) continue;                           // (drawn from the kit: loadKit)
      if (b.site) continue;                          // (a building agent's site: nothing until it's built)
      const M = place(b.x, b.y, b.z, b.yaw);
      const k = b.kind;
      const body = k.startsWith('town_shop') ? pick(BRICKS, b.id) : k.startsWith('town_cottage') ? pick(PASTEL, b.id)
        : k.startsWith('town_house') ? pick(HOUSE, b.id) : k === 'town_church' || k === 'town_church_hall' || k === 'town_inn' ? C.white
        : k === 'town_bar' ? C.bar : k === 'town_depot' ? C.board : k === 'town_mill' || k === 'town_school' ? C.brick
        : k === 'town_sheriff' ? [0.5, 0.42, 0.32] : k === 'town_fastfood' ? [0.42, 0.16, 0.1] : k === 'town_plaza' ? [0.66, 0.6, 0.5]
        : k.startsWith('town_motel') ? C.cream : k.startsWith('town_garage') || k === 'town_shed' ? pick(HOUSE, b.id + 'g') : C.grey;
      for (const p of b.parts) {
        const key = p[6];
        const col = C[key] && !key.startsWith('town_') ? C[key] : body;
        abox(M, p[0], p[1], p[2], p[3], p[4], p[5], col);
      }
      if (b.below_m > 0.05) {                         // piers under a hill lot's back half
        for (const u of [-b.w / 2 + 0.4, 0, b.w / 2 - 0.4]) for (const v of [0.5, b.d / 2 - 0.4])
          abox(M, u - 0.2, v - 0.2, -b.below_m - 0.4, u + 0.2, v + 0.2, 0, C.brick3);
      }
      const r = b.roof_shape;
      if (r) {
        const g = roofGeometry(b.w + 0.8, b.d + 0.8, r.eave, r.ridge, r.kind);
        g.applyMatrix4(M);
        lit.push(setColor(g, k.startsWith('town_cottage') || k.startsWith('town_house') ? pick([C.roof, C.tin, C.shingle, [0.3, 0.12, 0.1]], b.id + 'r') : k === 'town_bar' ? C.shingle : C.tin));
      }
      if (k === 'town_church') {                     // the steeple's spire on its tower
        const s = new THREE.ConeGeometry(2.0, 7.0, 4, 1); s.rotateY(Math.PI / 4); s.translate(0, 17.5, (b.d / 2 + 0.5) - 1.7);
        s.applyMatrix4(M); lit.push(setColor(s.toNonIndexed(), C.white));
      }
      if (k === 'town_mill_stack') { const s = new THREE.CylinderGeometry(1.3, 1.7, b.h, 10); s.translate(0, b.h / 2, 0); s.applyMatrix4(M); lit.pop(); lit.push(setColor(s.toNonIndexed(), C.brick_dark)); }
      if (k === 'town_water_tower') { const s = new THREE.ConeGeometry(4.6, 2.4, 14); s.translate(0, b.h - 1.0, 0); s.applyMatrix4(M); lit.push(setColor(s.toNonIndexed(), C.tank)); }
      // shopfront details: awnings, lit display windows
      if (k.startsWith('town_shop')) {
        abox(M, -b.w / 2 + 0.3, -b.d / 2 - 1.4, 2.9, b.w / 2 - 0.3, -b.d / 2, 3.2, pick(AWN, b.id + 'a'));
        abox(M, -b.w / 2 + 0.8, -b.d / 2 - 0.03, 0.6, b.w / 2 - 0.8, -b.d / 2 - 0.01, 2.6, [0.55, 0.42, 0.25], glow);
        for (const u of [-b.w / 4, b.w / 4]) abox(M, u - 0.6, -b.d / 2 - 0.03, 4.6, u + 0.6, -b.d / 2 - 0.01, 6.6, hash(b.id + u) > 0.6 ? [0.5, 0.36, 0.2] : C.glass, hash(b.id + u) > 0.6 ? glow : lit);
      }
      if (k === 'town_bar') {                         // neon: the window sign, a bottle, the porch strip
        abox(M, -9, -b.d / 2 - 0.06, 2.0, -4, -b.d / 2 - 0.04, 2.5, [2.4, 0.15, 0.12], glow);
        abox(M, 4.5, -b.d / 2 - 0.06, 1.2, 5.0, -b.d / 2 - 0.04, 2.8, [0.2, 1.6, 0.5], glow);
        abox(M, -b.w / 2, -b.d / 2 - 2.6, 3.0, b.w / 2, -b.d / 2 - 2.5, 3.08, [1.4, 0.5, 0.2], glow);
        abox(M, -b.w / 2, -b.d / 2 - 2.6, 3.08, b.w / 2, -b.d / 2, 3.3, C.shingle);          // the porch roof
        for (const u of [-b.w / 2 + 0.3, -5, 5, b.w / 2 - 0.3]) abox(M, u - 0.12, -b.d / 2 - 2.6, 0, u + 0.12, -b.d / 2 - 2.36, 3.0, [0.2, 0.15, 0.1]);
        // inside: the long bar, the back-bar's lit shelves, booths, the pool table's pool of light, the jukebox, the stage
        abox(M, -12, 3.0, 0, 2, 4.0, 1.1, [0.18, 0.08, 0.04]);
        abox(M, -12, 7.2, 1.2, 2, 7.6, 2.6, [1.1, 0.65, 0.3], glow);
        for (let u = -11; u < 10; u += 3.2) abox(M, u, -8.2, 0, u + 2.2, -6.6, 1.2, [0.35, 0.03, 0.03]);
        abox(M, 4, -2.5, 0, 6.6, -1.1, 0.85, [0.03, 0.18, 0.08]);
        abox(M, 4.6, -2.0, 2.6, 6.0, -1.6, 2.65, [1.6, 1.3, 0.8], glow);
        abox(M, 11, 5, 0, 12.2, 5.8, 1.6, [1.6, 0.6, 0.2], glow);
        abox(M, 9.5, -7, 0, 14.6, 7, 0.6, [0.12, 0.05, 0.04]);
        abox(M, 14.4, -6, 0.6, 14.6, 6, 3.4, [0.45, 0.02, 0.03]);
      }
      if (k === 'town_fastfood') abox(M, -b.w / 2, -b.d / 2 - 0.05, 4.6, b.w / 2, b.d / 2 + 0.05, 5.2, [1.2, 0.35, 0.08], glow);
      if (k === 'town_plaza') abox(M, 16, -b.d / 2 - 0.06, 0.6, 31, -b.d / 2 - 0.04, 2.6, [0.25, 0.45, 1.3], glow);   // the video store's window
      if (k === 'town_gas_station') abox(M, -b.w / 2, -b.d / 2 - 0.02, 5.25, b.w / 2, -b.d / 2 + 13.02, 5.45, [1.6, 1.6, 1.5], glow);
      if (k.startsWith('town_motel_wing')) for (let u = -11; u <= 11; u += 4.4) abox(M, u - 0.1, -b.d / 2 - 0.06, 2.3, u + 0.1, -b.d / 2 - 0.04, 2.5, [1.4, 1.1, 0.6], glow);
      if (k === 'town_sheriff') abox(M, -6, -b.d / 2 - 0.06, 1.0, 2, -b.d / 2 - 0.04, 2.4, [0.6, 0.55, 0.4], glow);
    }
    // ---- streets: asphalt, lane markings (double yellow centre, white edges), sidewalks downtown
    const H = (x, y) => world.heightAt(x, -(y - oy));
    const ribbon = (pts, off0, off1, lift, col, dash = 0, out = lit) => {
      const P = [], I = [];
      let s = 0;
      for (let i = 0; i < pts.length; i++) {
        const a = pts[Math.max(0, i - 1)], c = pts[Math.min(pts.length - 1, i + 1)];
        const dx = c[0] - a[0], dy = c[1] - a[1], L = Math.hypot(dx, dy) || 1, nx = -dy / L, ny = dx / L;
        if (i) s += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
        for (const o of [off0, off1]) {
          const x = pts[i][0] + nx * o, y = pts[i][1] + ny * o;
          P.push(x, Math.max(H(x, y), pts[i][2]) + lift, -(y - oy));
        }
        if (i && !(dash && Math.floor(s / dash) % 2)) { const q = (i - 1) * 2; I.push(q, q + 2, q + 1, q + 1, q + 2, q + 3); }
      }
      if (!I.length) return;
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
      g.setAttribute('normal', new THREE.Float32BufferAttribute(new Array(P.length).fill(0).map((_, k) => (k % 3 === 1 ? 1 : 0)), 3));
      g.setIndex(I);
      out.push(setColor(g.toNonIndexed(), col));
    };
    for (const s of T.streets) {
      const w = s.width / 2;
      // (the county road through town is road.js's concrete slab when the world has its road.json)
      if (s.kind === 'road' && T.county_road && params0().get('road') !== '0') { /* drawn by road.js */ } else if (s.kind === 'road') {
        ribbon(s.pts, -w, w, 0.07, C.asphalt);
        ribbon(s.pts, -0.2, -0.08, 0.085, C.yellow); ribbon(s.pts, 0.08, 0.2, 0.085, C.yellow);
        ribbon(s.pts, -w + 0.9, -w + 1.02, 0.085, C.line); ribbon(s.pts, w - 1.02, w - 0.9, 0.085, C.line);
      } else if (s.kind === 'street') {
        ribbon(s.pts, -w, w, 0.07, C.asphalt2);
        ribbon(s.pts, -0.06, 0.06, 0.085, C.line, 3);
      } else if (s.kind === 'walk') ribbon(s.pts, -w, w, 0.06, C.concrete);
      if (s.name === 'main_street') {               // downtown: sidewalks and curbs both sides, parking bays
        const dt = s.pts.filter((p) => p[0] < -95 && p[0] > -360);
        for (const sd of [-1, 1]) {
          ribbon(dt, sd > 0 ? w + 2.6 : -w - 6.6, sd > 0 ? w + 6.6 : -w - 2.6, 0.16, C.concrete);
          ribbon(dt, sd > 0 ? w : -w - 2.6, sd > 0 ? w + 2.6 : -w, 0.075, C.asphalt2);
        }
      }
    }
    // ---- the truss bridge and the footbridge
    for (const br of T.bridges) {
      const A = W(br.a[0], br.a[1], br.za), B = W(br.b[0], br.b[1], br.zb);
      const d = B.clone().sub(A), L = d.length(), dir = d.clone().normalize(), flat = d.clone().setY(0).normalize(), sd = new THREE.Vector3(-flat.z, 0, flat.x);
      const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(1, 0, 0), dir);
      const seg = (a, b, w, h, col, out = lit) => {
        const dd = b.clone().sub(a), len = dd.length(); if (len < 1e-3) return;
        const g = new THREE.BoxGeometry(len, h, w);
        g.applyMatrix4(new THREE.Matrix4().compose(a.clone().add(b).multiplyScalar(0.5), new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(1, 0, 0), dd.normalize()), new THREE.Vector3(1, 1, 1)));
        out.push(setColor(g.toNonIndexed(), col));
      };
      const at = (t, off = 0, up = 0) => A.clone().lerp(B, t).addScaledVector(sd, off).add(new THREE.Vector3(0, up, 0));
      const hw = br.width / 2;
      if (br.kind === 'truss' && kitHas.has('town_truss_span')) continue;     // (the kit's spans and pier: loadKit)
      if (br.kind === 'truss') {
        const g = new THREE.BoxGeometry(L, 0.5, br.width + 0.6); g.applyMatrix4(new THREE.Matrix4().compose(at(0.5, 0, -0.27), q, new THREE.Vector3(1, 1, 1)));
        lit.push(setColor(g.toNonIndexed(), C.asphalt2));
        for (const o of [-0.2, 0.08]) seg(at(0, o, 0.02), at(1, o, 0.02), 0.12, 0.02, C.yellow);
        const n = br.spans * 6;
        for (const s_ of [-1, 1]) {
          const o = s_ * (hw + 0.2);
          for (let sp = 0; sp < br.spans; sp++) {
            const t0 = sp / br.spans, t1 = (sp + 1) / br.spans;
            seg(at(t0, o, 0.3), at(t1, o, 0.3), 0.35, 0.5, C.truss);                          // bottom chord
            seg(at(t0 + 0.06 / br.spans, o, 7), at(t1 - 0.06 / br.spans, o, 7), 0.4, 0.45, C.truss);   // top chord
            seg(at(t0, o, 0.3), at(t0 + 0.06 / br.spans, o, 7), 0.4, 0.45, C.truss);            // end posts
            seg(at(t1, o, 0.3), at(t1 - 0.06 / br.spans, o, 7), 0.4, 0.45, C.truss);
            for (let k = 1; k < 6; k++) {
              const t = t0 + (t1 - t0) * k / 6;
              seg(at(t, o, 0.3), at(t, o, 7), 0.25, 0.25, C.truss);
              seg(at(t, o, 0.3), at(t + (k < 3 ? -1 : 1) * (t1 - t0) / 6, o, 7), 0.18, 0.18, C.truss);
            }
          }
          seg(at(0, o, 0), at(1, o, 0), 0.25, 1.1, C.concrete);                                // parapet curb
        }
        for (let k = 0; k <= n; k += 2) seg(at(k / n, -hw - 0.2, 7), at(k / n, hw + 0.2, 7), 0.25, 0.25, C.truss);   // portal / sway bracing
        for (let sp = 1; sp < br.spans; sp++) {                                                    // the stone pier
          const p = at(sp / br.spans, 0, 0), g2 = new THREE.BoxGeometry(4, p.y - (br.water - 4), br.width + 2);
          g2.applyMatrix4(new THREE.Matrix4().compose(p.clone().setY((p.y + br.water - 4) / 2 - 0.5), q.clone(), new THREE.Vector3(1, 1, 1)));
          lit.push(setColor(g2.toNonIndexed(), C.stone));
        }
        for (const [E, t] of [[A, 0], [B, 1]]) {                                                   // abutments and portal lamps
          const g3 = new THREE.BoxGeometry(3, 6, br.width + 3); g3.applyMatrix4(new THREE.Matrix4().compose(E.clone().add(new THREE.Vector3(0, -3.3, 0)), q, new THREE.Vector3(1, 1, 1)));
          lit.push(setColor(g3.toNonIndexed(), C.stone));
          for (const s_ of [-1, 1]) seg(at(t, s_ * (hw + 0.2), 6.2), at(t, s_ * (hw + 0.2), 6.6), 0.35, 0.35, [1.5, 1.4, 1.2], glow);
        }
      } else {
        seg(at(0, 0, -0.1), at(1, 0, -0.1), br.width, 0.2, C.steel);
        for (const s_ of [-1, 1]) seg(at(0, s_ * hw, 1.1), at(1, s_ * hw, 1.1), 0.06, 0.06, C.steel);
      }
    }
    // ---- the tunnel portal: a stone face with a dark bore into the hill
    if (T.tunnel && !kitHas.has('town_tunnel_portal')) {
      const t = T.tunnel, M = place(t.x, t.y, t.z, t.yaw);
      abox(M, -6, -0.8, -0.5, -3, 0.8, 10, C.stone); abox(M, 3, -0.8, -0.5, 6, 0.8, 10, C.stone); abox(M, -3, -0.8, 7.5, 3, 0.8, 10, C.stone);
      abox(M, -3, -0.5, -0.5, 3, 25, 7.5, C.black);
      abox(M, -9, 0.3, -0.5, -6, 1.3, 6, C.stone); abox(M, 6, 0.3, -0.5, 9, 1.3, 6, C.stone);
    }
    // ---- vehicles (the invaders' vans among them), the evidence, the townspeople's stand-ins
    for (const v of T.vehicles) {
      if (kitHas.has(`town_${v.kind}`)) continue;     // (drawn from the kit)
      const [L, Wd, Hh] = VEH[v.kind] || VEH.car, M = place(v.x, v.y, v.z, v.yaw - 90);
      const col = v.kind === 'van' ? [0.03, 0.035, 0.04] : v.kind === 'cruiser' ? [0.8, 0.8, 0.8] : v.kind === 'train' ? [0.35, 0.06, 0.05] : pick(CARS, `${v.x},${v.y}`);
      if (v.kind === 'train') {
        for (let k = 0; k < 3; k++) { const u0 = -L / 2 + k * 19.5; abox(M, -Wd / 2, u0, 0.4, Wd / 2, u0 + 18.5, Hh, k ? col : [0.1, 0.12, 0.1]); }
        continue;
      }
      // (the asset frame here: v = along the vehicle, u = across)
      abox(M, -Wd / 2, -L / 2, 0.3, Wd / 2, L / 2, Hh * (v.kind === 'van' ? 1 : 0.55), col);
      if (v.kind !== 'van') abox(M, -Wd / 2 + 0.1, -L / 2 + 1.1, Hh * 0.55, Wd / 2 - 0.1, L / 2 - (v.kind === 'pickup' ? 2.4 : 1.2), Hh, C.glass);
      else abox(M, -Wd / 2 - 0.01, L / 2 - 1.6, 1.3, Wd / 2 + 0.01, L / 2 - 0.4, 2.1, C.glass);
      if (v.kind === 'cruiser') { abox(M, -0.6, -0.3, Hh, 0.6, 0.3, Hh + 0.15, [0.1, 0.1, 0.8]); abox(M, -Wd / 2 - 0.01, -L / 2 + 1.5, 0.6, Wd / 2 + 0.01, L / 2 - 1.5, 0.9, [0.05, 0.05, 0.05]); }
    }
    for (const e of T.evidence) {
      if (e.kind === 'van' || kitHas.has(EVIDENCE_KIT[e.kind])) continue;
      const M = place(e.x, e.y, e.z, e.yaw - 90);
      if (e.kind === 'crates') abox(M, -0.6, -1.2, 0, 0.6, 1.2, 1.6, [0.4, 0.3, 0.18]);
      else if (e.kind === 'masks') { abox(M, -0.02, -1.8, 1.7, 0.02, 1.8, 1.73, [0.1, 0.1, 0.1]); for (let k = -3; k <= 3; k++) abox(M, -0.12, k * 0.5 - 0.12, 1.35, 0.12, k * 0.5 + 0.12, 1.68, [0.86, 0.85, 0.8]); }
      else if (e.kind === 'table') { abox(M, -0.4, -1.2, 0.72, 0.4, 1.2, 0.78, [0.5, 0.5, 0.48]); for (let k = 0; k < 24; k++) abox(M, -0.32 + (k % 4) * 0.2, -1.1 + Math.floor(k / 4) * 0.4, 0.78, -0.24 + (k % 4) * 0.2, -0.95 + Math.floor(k / 4) * 0.4, 0.79, [0.02, 0.02, 0.02]); }
      else if (e.kind === 'crt') for (let a = 0; a < 5; a++) for (let c = 0; c < 4; c++) abox(M, -0.3, -2 + a * 0.8, 0.2 + c * 0.55, 0.0, -1.3 + a * 0.8, 0.7 + c * 0.55, [0.35, 0.5, 0.65], glow);
      else if (e.kind === 'model') { abox(M, -1, -1.5, 0, 1, 1.5, 0.9, [0.3, 0.22, 0.15]); abox(M, -0.9, -1.4, 0.9, 0.9, 1.4, 0.95, [0.2, 0.35, 0.12]); abox(M, -0.2, -0.3, 0.95, 0.2, 0.3, 1.05, C.white); }
    }
    for (const p of T.people) {
      const M = place(p.x, p.y, p.z, -(p.face || 0));
      const col = p.role === 'sheriff' ? [0.38, 0.3, 0.18] : pick([[0.2, 0.25, 0.35], [0.4, 0.15, 0.12], [0.3, 0.3, 0.28], [0.15, 0.2, 0.15]], p.role);
      abox(M, -0.22, -0.13, 0, 0.22, 0.13, 0.85, [0.12, 0.12, 0.14]);
      abox(M, -0.25, -0.15, 0.85, 0.25, 0.15, 1.5, col);
      abox(M, -0.11, -0.12, 1.52, 0.11, 0.12, 1.78, [0.62, 0.48, 0.38]);
    }
    // ---- street lights downtown (acorn globes) and along the highway end
    const ms = T.streets.find((s) => s.name === 'main_street');
    if (ms) {
      let acc = 0;
      for (let i = 1; i < ms.pts.length; i++) {
        const a = ms.pts[i - 1], c = ms.pts[i], L = Math.hypot(c[0] - a[0], c[1] - a[1]);
        acc += L;
        if (acc < 24) continue;
        acc = 0;
        const nx = -(c[1] - a[1]) / L, ny = (c[0] - a[0]) / L, down = c[0] < -95 && c[0] > -360;
        for (const sd of [-1, 1]) {
          const off = down ? 6.2 : 6.5, x = c[0] + nx * off * sd, y = c[1] + ny * off * sd, z = H(x, y) + (down ? 0.16 : 0), h = down ? 4.2 : 9;
          const M = place(x, y, z, 0);
          abox(M, -0.08, -0.08, 0, 0.08, 0.08, h, [0.05, 0.06, 0.05]);
          abox(M, -0.22, -0.22, h, 0.22, 0.22, h + 0.5, down ? [1.6, 1.25, 0.75] : [1.4, 1.2, 0.9], glow);
        }
      }
    }
    // ---- merge: one lit draw, one emissive draw
    this.group = new THREE.Group();
    const merge = (parts) => mergeGeometries(parts.map((g) => { if (g.attributes.uv) g.deleteAttribute('uv'); if (!g.attributes.normal) g.computeVertexNormals(); return g.index ? g.toNonIndexed() : g; }));
    if (lit.length) { const m = new THREE.Mesh(merge(lit), litMaterial(uniforms, tex, world, { mossy: 0 })); m.name = 'Wild_Town'; m.frustumCulled = false; this.group.add(m); }
    if (glow.length) { const m = new THREE.Mesh(merge(glow), emissiveMaterial(uniforms)); m.name = 'Wild_Town_Glow'; m.frustumCulled = false; this.group.add(m); }
    this.stats = { buildings: T.buildings.length, litTris: lit.reduce((n, g) => n + g.attributes.position.count / 3, 0) };
    this.zones = [];
    this.ready = (T.kit || []).length ? this.loadKit(uniforms, tex).catch((e) => console.warn('town kit:', e)) : Promise.resolve();
    // the rebuilt buildings (prompts/town_building.md): each site's own model, lightmapped
    this.ready = this.ready.then(() => this.loadSites()).catch((e) => console.warn('town sites:', e));
  }

  // A rebuilt building (prompts/town_building.md): assets/models/town2_<id>.gltf placed on its
  // site (b.model, b.kit_offset from its sidecar). Its materials may carry a baked lightmap in
  // their extras (userData.lightmap: a path relative to assets/models/, userData.lightmapIntensity)
  // on the second UV set; emissive parts (neon) as authored. Kept as its own meshes (a building
  // close up; its own LOD nodes `<Root>_LOD1` hidden within lodDistance, else LOD0 hidden).
  async loadSites() {
    const T = this.town, oy = this.world.meta.estate_offset[1];
    const gl = new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath('https://unpkg.com/three@0.160.0/examples/jsm/libs/draco/gltf/'));
    const tl = new THREE.TextureLoader();
    this.sites = [];
    for (const b of T.buildings) {
      if (!b.site || !b.model) continue;
      try {
        const g = await gl.loadAsync(`../assets/models/${b.model}.gltf`);
        const root = g.scene;
        // [town2 sites: shared textures, reflections, LOD] (prompts/town_building.md; added by the
        // gas station workstream, generic for every site): a lightmap or panorama path is loaded
        // once (one GPU copy, however many materials name it); a material's extras `envMap` (an
        // equirect panorama, path relative to assets/models/) + `envMapIntensity` give it
        // reflections only (its diffuse light is the lightmap: the panorama's irradiance is
        // zeroed); nodes named `<Root>_LOD1` / `<Root>_LOD0` swap at the LOD1 node's extras
        // `lodDistance` (m, default 140; update() below).
        const texs = this._siteTex || (this._siteTex = new Map());
        const tex = (p, f) => { if (!texs.has(p)) { const t = tl.load(`../assets/models/${p}`); f(t); texs.set(p, t); } return texs.get(p); };
        const lod = { near: [], far: [], dist: 140 };
        root.traverse((o) => {
          if (/_LOD1$/.test(o.name)) { lod.far.push(o); if (o.userData?.lodDistance) lod.dist = o.userData.lodDistance; } else if (/_LOD0$/.test(o.name)) lod.near.push(o);
          if (!o.isMesh) return;
          for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
            const lm = m.userData?.lightmap;
            if (lm && !m.lightMap) {
              m.lightMap = tex(lm, (tx) => { tx.channel = 1; tx.flipY = false; tx.colorSpace = THREE.SRGBColorSpace; });
              m.lightMapIntensity = m.userData.lightmapIntensity ?? 1;
              m.needsUpdate = true;
            }
            const ep = m.userData?.envMap;
            if (ep && !m.envMap) {
              m.envMap = tex(ep, (tx) => { tx.mapping = THREE.EquirectangularReflectionMapping; tx.colorSpace = THREE.SRGBColorSpace; });
              m.envMapIntensity = m.userData.envMapIntensity ?? 1;
              m.onBeforeCompile = (sh) => {
                sh.fragmentShader = sh.fragmentShader.replace('#include <lights_fragment_maps>', '#include <lights_fragment_maps>\n\tiblIrradiance = vec3( 0.0 );');
              };
              m.customProgramCacheKey = () => 'town2-site-env';
              m.needsUpdate = true;
            }
          }
        });
        // [/town2 sites]
        const [ox, oyk] = b.kit_offset || [0, 0];
        root.position.set(b.x, b.z, -(b.y - oy));
        root.rotation.y = b.yaw * Math.PI / 180;
        root.updateMatrix();
        const inner = new THREE.Group(); inner.add(...root.children); inner.position.set(-ox, 0, oyk); root.add(inner);
        root.name = `Town_${b.id}`;
        this.group.add(root);
        this.sites.push({ id: b.id, root, lod });
      } catch (e) { console.warn('town site', b.id, e.message); }
    }
  }

  // The kit's glTFs (design/town/kit_status.md) in place of the boxes. Every placement's meshes
  // are baked into world space and merged per 250 m zone x LOD x material (M_Town_Atlas lit like
  // the wilderness, M_Town_Glow unlit): a zone draws its LOD0 within 260 m of the camera, its
  // LOD1 (palette swatches) beyond. Inside a walk-in (vertices within its footprint, below 3.6 m)
  // the atlas is drawn unlit x COLOR_0, the kit's baked lamplight (the film-set look it asks for).
  async loadKit(uniforms, tex) {
    const T = this.town, world = this.world, oy = world.meta.estate_offset[1];
    const gl = new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath('https://unpkg.com/three@0.160.0/examples/jsm/libs/draco/gltf/'));
    const models = {};
    let atlas = null, glowMap = null;
    THREE.Cache.enabled = true;          // (every kit glTF names the same atlas: fetch it once)
    await Promise.all(T.kit.map(async (k) => {
      try {
        const g = await gl.loadAsync(`../assets/models/${k}.gltf`);
        g.scene.updateMatrixWorld(true);
        const parts = { 0: [], 1: [] };
        g.scene.traverse((o) => {
          if (!o.isMesh) return;
          let lod = 0;
          for (let p = o; p; p = p.parent) if (/_LOD1$/.test(p.name)) lod = 1;
          const mats = Array.isArray(o.material) ? o.material : [o.material];
          const glow = /Glow/i.test(mats[0].name || '');
          if (!glow && mats[0].map && !atlas) atlas = mats[0].map;
          if (glow && !glowMap) glowMap = mats[0].emissiveMap || mats[0].map;
          parts[lod].push({ geo: o.geometry, matrix: o.matrixWorld.clone(), glow });
        });
        models[k] = parts;
      } catch (e) { console.warn('kit', k, e.message); }
    }));
    // placements: (kind, matrix, footprint for the inside test)
    const P = [];
    const place = (x, y, z, yawDeg) => new THREE.Matrix4().compose(new THREE.Vector3(x, z, -(y - oy)), new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), yawDeg * Math.PI / 180), new THREE.Vector3(1, 1, 1));
    for (const b of T.buildings) {
      if (!b.kit || !models[b.kind]) continue;
      const [ox, oyk] = b.kit_offset || [0, 0];
      // (the asset origin sits kit_offset from the footprint centre: three local x = u, z = -v)
      const M = place(b.x, b.y, b.z, b.yaw).multiply(new THREE.Matrix4().makeTranslation(-ox, 0, oyk));
      P.push({ kind: b.kind, M, inside: b.walkin ? { x0: b.kit_offset ? -b.w / 2 + ox + 0.6 : 0, x1: b.w / 2 + ox - 0.6, y0: -b.d / 2 + oyk + 0.6, y1: b.d / 2 + oyk - 0.6 } : null });
    }
    for (const v of T.vehicles) if (models[`town_${v.kind}`]) P.push({ kind: `town_${v.kind}`, M: place(v.x, v.y, v.z, v.yaw - 90) });
    for (const e of T.evidence) { const k = EVIDENCE_KIT[e.kind]; if (models[k]) P.push({ kind: k, M: place(e.x, e.y, e.z, e.yaw - 90) }); }
    if (T.tunnel && models.town_tunnel_portal) P.push({ kind: 'town_tunnel_portal', M: place(T.tunnel.x, T.tunnel.y, T.tunnel.z, T.tunnel.yaw) });
    for (const br of T.bridges) {
      if (br.kind !== 'truss' || !models.town_truss_span) continue;
      const yaw = Math.atan2(-(br.b[0] - br.a[0]), br.b[1] - br.a[1]) * 180 / Math.PI;     // (the span's +y along a -> b)
      for (let s = 0; s < br.spans; s++) {
        const t = (s + 0.5) / br.spans, x = br.a[0] + (br.b[0] - br.a[0]) * t, y = br.a[1] + (br.b[1] - br.a[1]) * t;
        P.push({ kind: 'town_truss_span', M: place(x, y, br.za + (br.zb - br.za) * t, yaw) });
      }
      if (models.town_bridge_pier) for (let s = 1; s < br.spans; s++) {
        const t = s / br.spans, x = br.a[0] + (br.b[0] - br.a[0]) * t, y = br.a[1] + (br.b[1] - br.a[1]) * t, zt = br.za + (br.zb - br.za) * t - 0.95;
        const M = place(x, y, zt, yaw).multiply(new THREE.Matrix4().makeScale(1, Math.max(0.3, (zt - (br.water - 3.5)) / 10), 1));
        P.push({ kind: 'town_bridge_pier', M });
      }
    }
    // bake + bucket
    const ZONE = 250, buckets = new Map(), v = new THREE.Vector3();
    for (const pl of P) {
      const c = new THREE.Vector3().setFromMatrixPosition(pl.M);
      const key = `${Math.floor(c.x / ZONE)},${Math.floor(c.z / ZONE)}`;
      for (const lod of [0, 1]) for (const part of models[pl.kind][lod]) {
        const g = part.geo.clone();
        for (const name of Object.keys(g.attributes)) if (!['position', 'normal', 'uv', 'color'].includes(name)) g.deleteAttribute(name);
        const n = g.attributes.position.count;
        if (!g.attributes.uv) g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(n * 2), 2));
        const col = new Float32Array(n * 3).fill(1);
        if (g.attributes.color) for (let i = 0; i < n; i++) { col[i * 3] = g.attributes.color.getX(i); col[i * 3 + 1] = g.attributes.color.getY(i); col[i * 3 + 2] = g.attributes.color.getZ(i); }
        g.setAttribute('color', new THREE.BufferAttribute(col, 3));
        g.applyMatrix4(part.matrix);
        const ins = new Float32Array(n);
        if (pl.inside && !part.glow) {
          const f = pl.inside, p = g.attributes.position;
          for (let i = 0; i < n; i++) { const x = p.getX(i), y = p.getY(i), vz = -p.getZ(i); ins[i] = x > f.x0 && x < f.x1 && vz > f.y0 && vz < f.y1 && y < 3.6 ? 1 : 0; }
        }
        g.setAttribute('inside', new THREE.BufferAttribute(ins, 1));
        g.applyMatrix4(pl.M);
        if (!g.attributes.normal) g.computeVertexNormals();
        const bk = `${key}|${lod}|${part.glow ? 1 : 0}`;
        if (!buckets.has(bk)) buckets.set(bk, { key, lod, glow: part.glow, geos: [], c: new THREE.Vector3(), n: 0 });
        const bu = buckets.get(bk); bu.geos.push(g.index ? g : g); bu.c.add(c); bu.n++;
      }
    }
    if (atlas) { atlas.colorSpace = THREE.SRGBColorSpace; }
    if (glowMap) { glowMap.colorSpace = THREE.SRGBColorSpace; }
    // (the kit's glow is the same atlas as emission: one texture on the GPU)
    const matA = kitAtlasMaterial(uniforms, tex, world, atlas), matG = kitGlowMaterial(uniforms, atlas || glowMap);
    const zones = new Map();
    let tris = 0;
    for (const bu of buckets.values()) {
      const geos = bu.geos.map((g) => (g.index ? g.toNonIndexed() : g));
      const m = new THREE.Mesh(mergeGeometries(geos), bu.glow ? matG : matA);
      m.name = `Wild_TownKit_${bu.lod}${bu.glow ? '_Glow' : ''}`;
      m.frustumCulled = false;
      if (bu.lod === 0) tris += m.geometry.attributes.position.count / 3;
      this.group.add(m);
      if (!zones.has(bu.key)) zones.set(bu.key, { c: bu.c.clone().multiplyScalar(1 / bu.n), lods: [[], []] });
      zones.get(bu.key).lods[bu.lod].push(m);
    }
    this.zones = [...zones.values()];
    this.stats.kitPlacements = P.length; this.stats.kitTrisLod0 = tris; this.stats.kitZones = this.zones.length;
    this._last = null;
  }

  update(camera) {
    const c = camera.position;
    // [town2 sites: LOD] (see loadSites)
    for (const st of this.sites || []) {
      if (!st.lod?.far.length) continue;
      const near = Math.hypot(c.x - st.root.position.x, c.z - st.root.position.z) < st.lod.dist;
      for (const o of st.lod.near) o.visible = near;
      for (const o of st.lod.far) o.visible = !near;
    }
    // [/town2 sites]
    for (const z of this.zones) {
      const near = Math.hypot(c.x - z.c.x, c.z - z.c.z) < 260;
      for (const m of z.lods[0]) m.visible = near;
      for (const m of z.lods[1]) m.visible = !near;
    }
  }
}

const EVIDENCE_KIT = { crates: 'town_crate_stack', crt: 'town_crt_wall', table: 'town_table_phones', model: 'town_estate_model' };
const params0 = () => new URLSearchParams(location.search);

function kitAtlasMaterial(uniforms, tex, world, map) {
  return new THREE.ShaderMaterial({
    uniforms: { ...uniforms, uLight: { value: tex.light }, tAtlas: { value: map },
      uMapXf: { value: new THREE.Vector4(-world.size / 2, -world.size / 2, 1 / world.size, 1) } },
    vertexColors: true,
    vertexShader: /* glsl */`
      attribute float inside;
      varying vec3 vWorld, vN, vCol; varying vec2 vUv; varying float vIn;
      void main() { vec4 w = modelMatrix * vec4(position, 1.0); vWorld = w.xyz; vN = normalize(mat3(modelMatrix) * normal); vCol = color; vUv = uv; vIn = inside;
        gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: /* glsl */`
      uniform sampler2D tAtlas, uLight;
      uniform vec4 uMapXf;
      uniform vec3 uSunColor, uSkyColor;
      varying vec3 vWorld, vN, vCol; varying vec2 vUv; varying float vIn;
      ${ATMOSPHERE_PARS}
      void main() {
        vec3 alb = texture2D(tAtlas, vUv).rgb * vCol;
        vec3 n = normalize(vN);
        vec3 col;
        if (vIn > 0.5) col = alb * 1.3;                                   // a walk-in's room: its baked lamplight
        else {
          vec4 l = textureLod(uLight, (vWorld.xz - uMapXf.xy) * uMapXf.z, 0.0);
          float ndl = clamp((dot(n, uSunDir) + 0.2) / 1.2, 0.0, 1.0);
          col = alb * (uSunColor * ndl * l.a * l.g + uSkyColor * l.b * (0.6 + 0.4 * n.y) + 0.04);
        }
        gl_FragColor = vec4(applyAtmosphere(col, vWorld), 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}

function kitGlowMaterial(uniforms, map) {
  return new THREE.ShaderMaterial({
    uniforms: { ...uniforms, tAtlas: { value: map } },
    vertexShader: /* glsl */`
      varying vec3 vWorld; varying vec2 vUv;
      void main() { vec4 w = modelMatrix * vec4(position, 1.0); vWorld = w.xyz; vUv = uv; gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: /* glsl */`
      uniform sampler2D tAtlas;
      varying vec3 vWorld; varying vec2 vUv;
      ${ATMOSPHERE_PARS}
      void main() {
        gl_FragColor = vec4(applyAtmosphere(texture2D(tAtlas, vUv).rgb * 3.0, vWorld), 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}

// ---------------------------------------------------------------- exits between worlds
// world.json "exits" (estate-frame rects): walking into one reloads the page into the other world
// at the same estate point, looking the same way (the cove <-> town seam: the heights there are
// identical in both worlds). A world without exits (laurel_fork today) gets the seam's other side
// from FALLBACK, so the cove's world needs no rebuild for it.
const FALLBACK = {
  laurel_fork: [{ name: 'town', to: 'laurel_town', rect: [-800, -1578, -762, -42], spawn_dx: -3 }],
};

export class Exits {
  constructor(world, name) {
    this.name = name;
    this.list = world.meta.town?.exits || world.meta.exits || FALLBACK[name] || [];   // (the cove's world.json "town" is its glimpse: no exits)
    const [ox, oy] = world.meta.estate_offset;
    this.ox = ox; this.oy = oy;
    this.armed = false;
    this.leaving = false;
  }

  // estate frame of a three.js point
  estate(p) { return [p.x + this.ox, -p.z + this.oy]; }

  check(camera, fly) {
    if (this.leaving || fly || !this.list.length) return null;
    const [x, y] = this.estate(camera.position);
    const inside = (e) => x >= e.rect[0] && x <= e.rect[2] && y >= e.rect[1] && y <= e.rect[3];
    // (armed only once the player has stood outside every exit: a spawn inside one does nothing)
    if (!this.armed) { this.armed = !this.list.some(inside); return null; }
    const e = this.list.find(inside);
    if (!e) return null;
    if (!e.to) { if (!e._logged) { console.log(`exit "${e.name}": a later level (${e.note || ''})`); e._logged = true; } return null; }
    const f = new THREE.Vector3(); camera.getWorldDirection(f);
    const sx = x + (e.spawn_dx || 0), u = new URL(location.href);
    for (const k of ['view', 'pos', 'look']) u.searchParams.delete(k);
    u.searchParams.set('world', e.to);
    u.searchParams.set('epos', `${sx.toFixed(2)},${y.toFixed(2)}`);
    u.searchParams.set('elook', `${(sx + f.x * 20).toFixed(2)},${(y - f.z * 20).toFixed(2)}`);
    this.leaving = true;
    document.body.style.transition = 'opacity 0.35s'; document.body.style.opacity = '0';
    setTimeout(() => location.replace(u.toString()), 350);
    return e;
  }
}

// a gable (ridge along the longer side) or hip roof over a w x d footprint, eave -> ridge
// (asset frame: u across = three x, v back = three -z)
function roofGeometry(w, d, eave, ridge, kind) {
  const alongU = w >= d, hu = w / 2, hv = d / 2;
  let P;
  if (kind === 'hip') {
    const r = Math.abs(w - d) / 2;
    const a = alongU ? [[-r, 0], [r, 0]] : [[0, -r], [0, r]];
    const c = [[-hu, -hv], [hu, -hv], [hu, hv], [-hu, hv]];
    const R0 = a[0], R1 = a[1];
    // four faces: front, right, back, left (ridge ends R0 / R1)
    const tri = (p, q, s) => [p, q, s];
    const F = alongU ? [tri(c[0], c[1], R1), tri(c[0], R1, R0), tri(c[1], c[2], R1), tri(c[2], c[3], R0), tri(c[2], R0, R1), tri(c[3], c[0], R0)]
      : [tri(c[0], c[1], R0), tri(c[1], c[2], R1), tri(c[1], R1, R0), tri(c[2], c[3], R1), tri(c[3], c[0], R0), tri(c[3], R0, R1)];
    P = [];
    for (const t of F) for (const p of t) P.push(p[0], (p === R0 || p === R1) ? ridge : eave, -p[1]);
  } else {
    const c = alongU ? [[-hu, -hv], [hu, -hv], [hu, hv], [-hu, hv], [-hu, 0], [hu, 0]] : [[-hu, -hv], [hu, -hv], [hu, hv], [-hu, hv], [0, -hv], [0, hv]];
    const v = (k) => [c[k][0], k >= 4 ? ridge : eave, -c[k][1]];
    const F = alongU ? [[0, 1, 5], [0, 5, 4], [2, 3, 4], [2, 4, 5], [0, 4, 3], [1, 2, 5]] : [[0, 4, 1], [1, 4, 5], [1, 5, 2], [3, 5, 4], [3, 4, 0], [2, 5, 3]];
    P = [];
    for (const f of F) for (const k of f) P.push(...v(k));
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
  g.computeVertexNormals();
  // (both windings: draw it double-sided by duplicating reversed)
  const idx = [...Array(P.length / 3).keys()];
  const back = new THREE.BufferGeometry();
  const Q = []; for (let i = 0; i < idx.length; i += 3) for (const k of [i, i + 2, i + 1]) Q.push(P[k * 3], P[k * 3 + 1], P[k * 3 + 2]);
  back.setAttribute('position', new THREE.Float32BufferAttribute(Q, 3));
  back.computeVertexNormals();
  return mergeGeometries([g, back]);
}
