import * as THREE from 'three';
import { ATMOSPHERE_PARS, LIGHT_PARS } from './atmosphere.js';
import { rng } from './noise.js';

// Instanced forest. Per species: a near mesh, a mid mesh (~1/4 of the triangles) and a
// lit impostor (8 views baked at load into an albedo + normal atlas), each ONE instanced draw
// call. Instances are bucketed into 64 m cells; every frame the visible cells (frustum test),
// nearest first, are copied into each tier's instance buffer by distance band. Tiers overlap
// by a fade band where both draw with complementary screen-space dither, so LOD changes
// cross-fade instead of popping. Undergrowth (ferns, tufts) is a near-only mesh tier.
//
// The stand-in meshes are built here (leaf cards from the project's foliage textures, bark
// from the entry tree); real trees (The Grove / SpeedTree / Blender exports) replace build*()
// and keep the rest. Atlas colours are stored sqrt-encoded (gamma 2) in 8-bit targets.

// with the production-weight trees (?veg=1): their LOD distances (design/wilderness/_tech/vegetation.md)
export const TIERS_VEG = {
  lod0: [0, 0, 20, 26],
  lod1: [20, 26, 45, 55],
  lod2: [45, 55, 105, 125],
  far: [105, 125, 2600, 2700],
};

export const TIERS = {
  // distance bands (m): [fade-in start, fade-in end, fade-out start, fade-out end]
  near: [0, 0, 42, 56],
  mid: [42, 56, 150, 175],
  far: [150, 175, 2600, 2700],
  under: [0, 0, 48, 62],
  // shrubs and thickets (stand-ins: near / mid / impostor; production models: LOD0 within 12 m,
  // the runtime's rule for thickets)
  snear: [0, 0, 16, 22], smid: [16, 22, 60, 75], sfar: [60, 75, 520, 600],
  slod0: [0, 0, 12, 15], slod1: [12, 15, 32, 38], slod2: [32, 38, 70, 85],
  // kit shrubs: LOD0 (hull + cards), LOD1, then the shared impostor; thicket tiles: their hull
  // LOD2 is their far LOD (to 160 m, no impostor)
  simp: [32, 38, 520, 600], tlod2: [32, 38, 150, 165],
  // small trees' impostors from their LOD1's end; the snags' single tier; ground cover's single tier
  timp: [45, 55, 1500, 1700], snag: [0, 0, 150, 170], ucover: [0, 0, 40, 50],
  // ground cover models (ferns, doghobble): LOD0 near, LOD1 to the cull
  ulod0: [0, 0, 9, 11], ulod1: [9, 11, 40, 50], ulod2: [20, 24, 40, 50],
};

const CELL = 64;
const AT_W = 1024, AT_H = 1280, BARK_V = 256 / AT_H;   // atlas: bark strip below, foliage above
const fol = (u, v) => [u, BARK_V + (1 - BARK_V) * v];

// ---------------------------------------------------------------- geometry helpers
class Geo {
  constructor() { this.p = []; this.n = []; this.uv = []; this.ao = []; this.bl = []; this.idx = []; this._bloom = 0; }
  v(p, n, uv, ao) { this.p.push(...p); this.n.push(...n); this.uv.push(...uv); this.ao.push(ao); this.bl.push(this._bloom); return this.ao.length - 1; }
  // a leaf card: centre c, half-extent vectors r (right) and u (up), atlas cell [u0, v0, su, sv]
  // in atlas UVs; normals bent toward `radial` (the crown's outward direction): the foliage
  // shades as a volume instead of as flat cards
  card(c, r, u, cell, radial, ao, bend = 0.7) {
    const cn = norm(cross(r, u)), n = norm(lerp3(cn, radial, bend));
    const [u0, v0, su, sv] = cell;
    const a = this.v(add(c, sc(r, -1), sc(u, -1)), n, [u0, v0], ao * 0.8);
    const b = this.v(add(c, r, sc(u, -1)), n, [u0 + su, v0], ao * 0.8);
    const d = this.v(add(c, r, u), n, [u0 + su, v0 + sv], ao);
    const e = this.v(add(c, sc(r, -1), u), n, [u0, v0 + sv], ao);
    this.idx.push(a, b, d, a, d, e);
  }
  // a bent card: centre line pts (base first), half width w along `side`; cell [u0, v0, su, sv]
  strip(pts, side, w, cell, radialFn, aoFn) {
    const [u0, v0, su, sv] = cell, base = this.ao.length;
    pts.forEach((p, i) => {
      const t = i / (pts.length - 1);
      const along = norm(sub(pts[Math.min(i + 1, pts.length - 1)], pts[Math.max(i - 1, 0)]));
      const cn = norm(cross(side, along)), n = norm(lerp3(cn, radialFn(p), 0.55));
      const ww = w * (1 - 0.5 * t * t);
      this.v(add(p, sc(side, -ww)), n, [u0, v0 + sv * t], aoFn(t));
      this.v(add(p, sc(side, ww)), n, [u0 + su, v0 + sv * t], aoFn(t));
    });
    for (let i = 0; i < pts.length - 1; i++) { const a = base + 2 * i; this.idx.push(a, a + 1, a + 3, a, a + 3, a + 2); }
  }
  // a tapered tube along pts with radii rs, bark UVs (u around, v along) in the bark strip
  tube(pts, rs, sides, ao0 = 0.55, ao1 = 0.9) {
    const base = this.ao.length;
    let len = 0, total = 0;
    for (let i = 1; i < pts.length; i++) total += dist(pts[i], pts[i - 1]);
    pts.forEach((p, i) => {
      if (i) len += dist(p, pts[i - 1]);
      const along = norm(sub(pts[Math.min(i + 1, pts.length - 1)], pts[Math.max(i - 1, 0)]));
      const ref = Math.abs(along[1]) > 0.9 ? [1, 0, 0] : [0, 1, 0];
      const x = norm(cross(ref, along)), z = cross(along, x);
      for (let s = 0; s <= sides; s++) {
        const a = (s / sides) * Math.PI * 2, n = add(sc(x, Math.cos(a)), sc(z, Math.sin(a)));
        this.v(add(p, sc(n, rs[i])), n, [s / sides, 0.002 + 0.97 * BARK_V * (len / total)], ao0 + (ao1 - ao0) * (i / (pts.length - 1)));
      }
    });
    for (let i = 0; i < pts.length - 1; i++) for (let s = 0; s < sides; s++) {
      const a = base + i * (sides + 1) + s, b = a + sides + 1;
      this.idx.push(a, b, a + 1, a + 1, b, b + 1);
    }
  }
  build() {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(this.p, 3));
    g.setAttribute('normal', new THREE.Float32BufferAttribute(this.n, 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute(this.uv, 2));
    g.setAttribute('ao', new THREE.Float32BufferAttribute(this.ao, 1));
    g.setAttribute('bloom', new THREE.Float32BufferAttribute(this.bl, 1));
    g.setIndex(this.idx);
    g.computeBoundingBox();
    return g;
  }
}
const add = (...v) => v.reduce((a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]]);
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const sc = (a, s) => [a[0] * s, a[1] * s, a[2] * s];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const norm = (a) => { const l = Math.hypot(...a) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };
const lerp3 = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
const randDir = (r) => { const z = 2 * r() - 1, a = r() * Math.PI * 2, s = Math.sqrt(1 - z * z); return [s * Math.cos(a), z, s * Math.sin(a)]; };
const cellUV = (cu, cv, s) => { const [u0, v0] = fol(cu, cv); return [u0, v0, s, s * (1 - BARK_V)]; };
const LEAF_CELLS = [cellUV(0, 0.5, 0.5), cellUV(0.5, 0.5, 0.5), cellUV(0, 0, 0.5), cellUV(0.5, 0, 0.5)];

function buildBroadleaf(lod, seed = 3) {
  const r = rng(seed), g = new Geo(), mid = lod > 0;
  const top = [0.2, 4.6, 0.08];
  g.tube([[0, -0.3, 0], [0.04, 1.6, 0.02], [0.12, 3.2, 0.05], top], [0.27, 0.22, 0.18, 0.14], mid ? 5 : 8);
  const crown = [0.2, 7.6, 0.1], R = [4.5, 3.7, 4.5];
  const nb = mid ? 3 : 7, tips = [];
  for (let i = 0; i < nb; i++) {
    const a = (i / nb) * Math.PI * 2 + r(), y = 2.9 + 1.6 * r();
    const s = [0.08 + 0.03 * y, y, 0.03 * y], d = norm([Math.cos(a) * 0.8, 0.7 + 0.3 * r(), Math.sin(a) * 0.8]);
    const tip = add(s, sc(d, 3.6), [0, 0.4, 0]);
    g.tube([s, add(s, sc(d, 1.7)), tip], [0.1, 0.065, 0.03], mid ? 4 : 5, 0.45, 0.75);
    tips.push(tip);
  }
  // leaf cards: clustered around the branch tips and over the crown's shell
  const cards = mid ? 52 : 230, size = mid ? 3.0 : 1.75;
  for (let i = 0; i < cards; i++) {
    let c, d;
    if (i % 3 === 0) { const t = tips[i % tips.length]; d = norm(sub(t, crown)); c = add(t, sc(randDir(r), 1.3 * r())); }
    else {
      d = randDir(r); d = norm([d[0], d[1] * 0.75 + 0.25, d[2]]);
      const rad = 0.55 + 0.45 * Math.cbrt(r());
      c = [crown[0] + d[0] * R[0] * rad, crown[1] + d[1] * R[1] * rad, crown[2] + d[2] * R[2] * rad];
    }
    const up = norm(add(d, [0, 1.3, 0], sc(randDir(r), 0.5)));
    const right = norm(cross(up, randDir(r)));
    const s = size * (0.8 + 0.4 * r());
    const rel = sub(c, crown), rad = Math.min(1, Math.hypot(rel[0] / R[0], rel[1] / R[1], rel[2] / R[2]));
    const ao = 0.3 + 0.7 * (0.55 * rad + 0.45 * (norm(rel)[1] * 0.5 + 0.5));
    g.card(c, sc(right, s / 2), sc(up, s / 2), LEAF_CELLS[Math.floor(r() * 4)], norm(rel), ao);
  }
  return g.build();
}

function buildConifer(lod, seed = 5) {
  const r = rng(seed), g = new Geo(), mid = lod > 0;
  const H = 17;
  g.tube([[0, -0.3, 0], [0, 5, 0], [0, 11, 0], [0, H, 0]], [0.3, 0.22, 0.13, 0.03], mid ? 4 : 7);
  const whorls = mid ? 8 : 20;
  for (let wI = 0; wI < whorls; wI++) {
    const t = (wI + 0.5) / whorls, y = 1.6 + t * (H - 2.2);
    const L = 0.35 + 2.85 * Math.pow(1 - t, 1.05), per = mid ? 6 : t > 0.8 ? 6 : 9;
    for (let k = 0; k < per; k++) {
      const a = (k / per) * Math.PI * 2 + wI * 2.3 + 0.3 * r();
      const dir = norm([Math.cos(a), -0.28 - 0.25 * (1 - t) + 0.15 * r(), Math.sin(a)]);
      const side0 = norm(cross([0, 1, 0], dir)), tilt = (r() - 0.5) * 0.9;
      const side = norm(add(sc(side0, Math.cos(tilt)), sc([0, 1, 0], Math.sin(tilt))));
      const len = L * (mid ? 1.15 : 1) * (0.85 + 0.3 * r());
      const p0 = [dir[0] * 0.1, y, dir[2] * 0.1];
      const pts = [p0, add(p0, sc(dir, len * 0.5), [0, 0.06 * len, 0]), add(p0, sc(dir, len), [0, -0.05 * len, 0])];
      const radial = (p) => norm([p[0], 0.45 * Math.hypot(p[0], p[2]) + 0.15, p[2]]);
      g.strip(pts, side, (mid ? 0.6 : 0.45) * len + 0.3, LEAF_CELLS[k & 1], radial, (s) => 0.35 + 0.65 * (0.3 + 0.7 * t) * (0.6 + 0.4 * s));
    }
  }
  // the spire: two crossed cards on the leader
  for (const a of [0, Math.PI / 2]) {
    const right = [Math.cos(a) * 0.55, 0, Math.sin(a) * 0.55];
    g.card([0, H - 0.9, 0], right, [0, 1.4, 0], LEAF_CELLS[0], [Math.cos(a + 1.57), 0.4, Math.sin(a + 1.57)], 0.95, 0.3);
  }
  return g.build();
}

function buildPine(lod, seed = 9) {
  const r = rng(seed), g = new Geo(), mid = lod > 0;
  const top = [0.5, 18.8, 0.2];
  g.tube([[0, -0.3, 0], [0.1, 6, 0.05], [0.3, 12, 0.1], top], [0.34, 0.27, 0.2, 0.08], mid ? 5 : 7, 0.6, 0.95);
  const clumps = mid ? 4 : 7, crown = [0.4, 15.8, 0.15];
  for (let i = 0; i < clumps; i++) {
    const a = (i / clumps) * Math.PI * 2 + 0.7 * r(), y = 12.8 + 5.5 * (i / clumps) + r();
    const out = (1 - (y - 12.8) / 7) * 2.3 + 0.6;
    const c = [Math.cos(a) * out + 0.3, y + 0.8, Math.sin(a) * out + 0.12];
    if (!mid) g.tube([[0.25, y - 0.6, 0.08], c], [0.1, 0.05], 4, 0.55, 0.8);
    const n = mid ? 8 : 16;
    for (let k = 0; k < n; k++) {
      const d = randDir(r), p = add(c, sc([d[0], d[1] * 0.55, d[2]], 0.95));
      const radial = norm([p[0] - crown[0], (p[1] - crown[1]) * 0.8 + 0.6, p[2] - crown[2]]);
      const up = norm(add(d, [0, 1.6, 0])), right = norm(cross(up, randDir(r)));
      const s = (mid ? 2.2 : 1.55) * (0.8 + 0.4 * r());
      g.card(p, sc(right, s / 2), sc(up, s / 2), LEAF_CELLS[2 + (k & 1)], radial, 0.45 + 0.55 * (0.5 + 0.5 * d[1]), 0.65);
    }
  }
  return g.build();
}

// shrub / thicket stand-in (rhododendron, mountain laurel, azalea): a few stems under a dense,
// layered dome of leaf cards; ~28% of the outer, upper cards flower (the `bloom` attribute; the
// instance's bloom index picks the colour, 0 = not in bloom)
function buildShrub(lod, seed = 17) {
  const r = rng(seed), g = new Geo(), mid = lod > 0;
  const ns = mid ? 3 : 6;
  for (let i = 0; i < ns; i++) {
    const a = (i / ns) * Math.PI * 2 + r(), top = [Math.cos(a) * 0.7, 1.1 + 0.4 * r(), Math.sin(a) * 0.7];
    g.tube([[0, -0.1, 0], [top[0] * 0.45, top[1] * 0.55, top[2] * 0.45], top], [0.07, 0.05, 0.03], mid ? 3 : 4, 0.35, 0.6);
  }
  const crown = [0, 1.3, 0], R = [1.55, 1.05, 1.55];
  const cards = mid ? 42 : 150, size = mid ? 1.55 : 0.95;
  for (let i = 0; i < cards; i++) {
    let d = randDir(r); d = norm([d[0], d[1] * 0.7 + 0.2, d[2]]);
    const rad = 0.55 + 0.45 * Math.cbrt(r());
    const c = [crown[0] + d[0] * R[0] * rad, crown[1] + d[1] * R[1] * rad, crown[2] + d[2] * R[2] * rad];
    const up = norm(add(d, [0, 1.1, 0], sc(randDir(r), 0.6))), right = norm(cross(up, randDir(r)));
    const sz = size * (0.8 + 0.4 * r());
    const ao = 0.3 + 0.7 * (0.5 * rad + 0.5 * (d[1] * 0.5 + 0.5));
    g._bloom = rad > 0.82 && d[1] > -0.05 && r() < 0.28 ? 1 : 0;
    g.card(c, sc(right, sz / 2), sc(up, sz / 2), LEAF_CELLS[Math.floor(r() * 4)], d, ao, 0.75);
    g._bloom = 0;
  }
  return g.build();
}

// undergrowth on the courtyard foliage atlas (cells as courtyard_common.CELLS)
function buildFern(seed = 11) {
  const r = rng(seed), g = new Geo();
  for (let i = 0; i < 7; i++) {
    const a = (i / 7) * Math.PI * 2 + 0.4 * r(), d = [Math.cos(a), 0, Math.sin(a)], L = 0.8 + 0.4 * r();
    const pts = [[0, 0, 0], add(sc(d, L * 0.35), [0, L * 0.55, 0]), add(sc(d, L * 0.75), [0, L * 0.65, 0]), add(sc(d, L), [0, L * 0.4, 0])];
    g.strip(pts, norm(cross([0, 1, 0], d)), 0.2, [0.75, 0.25, 0.25, 0.25], (p) => norm([p[0], 1.2, p[2]]), (t) => 0.45 + 0.55 * t);
  }
  return g.build();
}
function buildTuft(seed = 13) {
  const r = rng(seed), g = new Geo();
  for (let i = 0; i < 4; i++) {
    const a = (i / 4) * Math.PI + 0.3 * r(), right = [Math.cos(a) * 0.45, 0, Math.sin(a) * 0.45];
    const cell = i & 1 ? [0, 0, 0.5, 0.5] : [0.5, 0.25, 0.25, 0.25];
    g.card([0, 0.33, 0], right, [0, 0.36, 0], cell, [Math.cos(a + 1.57), 0.8, Math.sin(a + 1.57)], 0.8, 0.5);
  }
  return g.build();
}

// ---------------------------------------------------------------- textures
// procedural needle cards (no needle texture in the project yet): conifer fronds in cells 0-1,
// pine tufts in cells 2-3. Drawn on opaque canvases (colour + coverage mask) so the colour
// under transparent texels stays needle-coloured: no dark fringes when mip-mapped.
function needleTexture() {
  const S = 1024, col = document.createElement('canvas'), msk = document.createElement('canvas');
  col.width = col.height = msk.width = msk.height = S;
  const c = col.getContext('2d'), m = msk.getContext('2d'), r = rng(77);
  c.fillStyle = 'rgb(34,52,30)'; c.fillRect(0, 0, S, S);
  c.fillStyle = 'rgb(70,78,40)'; c.fillRect(0, S / 2, S, S / 2);
  m.fillStyle = '#000'; m.fillRect(0, 0, S, S);
  const line = (x0, y0, x1, y1, w, rgb) => {
    for (const [ctx, st] of [[c, rgb], [m, '#fff']]) { ctx.strokeStyle = st; ctx.lineWidth = w; ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke(); }
  };
  c.lineCap = m.lineCap = 'round';
  // fronds (top half of the canvas = cells 0, 1 in UV space, which is flipped)
  for (let cell = 0; cell < 2; cell++) {
    const ox = cell * 512, oy = 0;
    const bend = (r() - 0.5) * 60;
    for (let t = 0; t <= 1; t += 0.012) {
      const x = ox + 256 + bend * t * t, y = oy + 500 - t * 470;
      const L = 150 * (1 - 0.75 * t) * (0.8 + 0.4 * r());
      for (const s of [-1, 1]) {
        const a = s * (0.9 + 0.3 * r()), dx = Math.sin(a) * L, dy = -Math.cos(a) * L * 0.6;
        const g = 40 + 35 * r();
        line(x, y, x + dx, y + dy, 5, `rgb(${18 + 18 * r()},${g},${26 + 14 * r()})`);
        for (let q = 0.3; q < 1; q += 0.22) {      // needles on the side shoots
          const px = x + dx * q, py = y + dy * q;
          line(px, py, px + dx * 0.25 + s * 10, py - 26 * (1 - q), 3, `rgb(${22 + 20 * r()},${g + 8},${28 + 12 * r()})`);
        }
      }
    }
    line(ox + 256, oy + 505, ox + 256 + bend, oy + 30, 7, 'rgb(60,45,30)');
  }
  // pine tufts (bottom half = cells 2, 3)
  for (let cell = 0; cell < 2; cell++) {
    const ox = cell * 512, oy = 512, bx = ox + 256, by = oy + 470;
    for (let i = 0; i < 380; i++) {
      const a = (r() - 0.5) * 2.6, L = 160 + 260 * r() * (1 - 0.35 * Math.abs(a)), curve = (r() - 0.5) * 40;
      const x1 = bx + Math.sin(a) * L, y1 = by - Math.cos(a) * L * 0.95;
      const g = 75 + 40 * r();
      for (const [ctx, st] of [[c, `rgb(${48 + 30 * r()},${g},${34 + 16 * r()})`], [m, '#fff']]) {
        ctx.strokeStyle = st; ctx.lineWidth = 3.2; ctx.beginPath(); ctx.moveTo(bx, by);
        ctx.quadraticCurveTo((bx + x1) / 2 + curve, (by + y1) / 2, x1, y1); ctx.stroke();
      }
    }
  }
  const cd = c.getImageData(0, 0, S, S).data, md = m.getImageData(0, 0, S, S).data;
  for (let i = 0; i < S * S; i++) cd[i * 4 + 3] = md[i * 4];
  const t = new THREE.DataTexture(new Uint8Array(cd.buffer), S, S, THREE.RGBAFormat);
  t.flipY = true;           // canvas rows top-down -> UV v up, as image textures
  t.colorSpace = THREE.SRGBColorSpace;
  t.needsUpdate = true;
  return t;
}

const copyMaterial = new THREE.ShaderMaterial({
  uniforms: { map: { value: null }, src: { value: new THREE.Vector4(0, 0, 1, 1) }, tint: { value: new THREE.Color(1, 1, 1) } },
  vertexShader: 'varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
  fragmentShader: `uniform sampler2D map; uniform vec4 src; uniform vec3 tint; varying vec2 vUv;
    void main() { vec4 t = texture2D(map, src.xy + vUv * src.zw); gl_FragColor = vec4(sqrt(t.rgb * tint), t.a); }`,
  depthTest: false, depthWrite: false,
});
const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), copyMaterial);
quad.frustumCulled = false;
const quadScene = new THREE.Scene(); quadScene.add(quad);
const orthoCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

function blit(renderer, target, map, srcRect, dst, tint = [1, 1, 1]) {
  copyMaterial.uniforms.map.value = map;
  copyMaterial.uniforms.src.value.set(...srcRect);
  copyMaterial.uniforms.tint.value.setRGB(...tint);
  target.viewport.set(...dst); target.scissor.set(...dst); target.scissorTest = true;
  renderer.setRenderTarget(target);
  renderer.render(quadScene, orthoCam);
}

function makeTarget(w, h, depth = false) {
  const t = new THREE.WebGLRenderTarget(w, h, { depthBuffer: depth, generateMipmaps: true,
    minFilter: THREE.LinearMipmapLinearFilter, magFilter: THREE.LinearFilter });
  return t;
}

// species atlas: foliage cells above, bark strip below
function buildAtlas(renderer, foliage, bark, barkTint) {
  const t = makeTarget(AT_W, AT_H);
  renderer.setRenderTarget(t); renderer.setClearColor(0x000000, 0); renderer.clear();
  blit(renderer, t, foliage, [0, 0, 1, 1], [0, AT_H - 1024, AT_W, 1024]);
  blit(renderer, t, bark, [0, 0, 1, 0.25], [0, 0, AT_W, AT_H - 1024], barkTint);
  renderer.setRenderTarget(null);
  return t.texture;
}

// ---------------------------------------------------------------- materials
const DITHER = /* glsl */`
float ign(vec2 p) { return fract(52.9829189 * fract(dot(p, vec2(0.06711056, 0.00583715)))); }
// complementary cross-fade: a tier fading in keeps the pixels a tier fading out drops
bool faded(float fin, float fout) { float d = ign(gl_FragCoord.xy); return d < 1.0 - fin || d >= fout; }
// alpha-tested foliage that keeps its coverage when mip-mapped, sharpened for alpha-to-coverage
float coverage(float a, vec2 uv, vec2 size) {
  vec2 dx = dFdx(uv * size), dy = dFdy(uv * size);
  float lod = max(0.0, 0.5 * log2(max(dot(dx, dx), dot(dy, dy))));
  a *= 1.0 + lod * 0.28;
  return clamp((a - 0.5) / max(fwidth(a), 1e-4) + 0.5, 0.0, 1.0);
}`;

const INSTANCE_VS = /* glsl */`
attribute vec4 inst0;          // x, y, z, horizontal scale
attribute vec4 inst1;          // rotY, seed (+ bloom index in its integer part), vertical / horizontal
                               // stretch (0 = 1), species tint (RGB x 100 packed in 24 bits; 0 = none)
uniform vec4 uFade;
uniform vec4 uMapXf;           // origin x, origin z, 1/size
uniform sampler2D uLight;
varying float vFadeIn, vFadeOut, vSun, vSky;
varying vec3 vWorld, vTint;
float seedOf() { return fract(inst1.y); }
float stretchOf() { return inst1.z > 0.0 ? inst1.z : 1.0; }
vec3 speciesTint() {
  float t = inst1.w;
  if (t <= 0.0) return vec3(1.0);
  return vec3(floor(t / 65536.0), mod(floor(t / 256.0), 256.0), mod(t, 256.0)) / 100.0;
}
void instanceCommonF(vec3 root, float hf, vec4 fade) {
  float d = distance(cameraPosition, root);
  vFadeIn = fade.y > 0.0 ? smoothstep(fade.x, fade.y, d) : 1.0;
  vFadeOut = 1.0 - smoothstep(fade.z, fade.w, d);
  vec4 l = textureLod(uLight, (root.xz - uMapXf.xy) * uMapXf.z, 0.0);
  // terrain shadow for the whole tree; neighbours' shadows only on the lower crown
  vSun = l.a * mix(l.g, 1.0, smoothstep(0.35, 0.95, hf));
  vSky = mix(l.b, 1.0, 0.5 * hf);
  vTint = mix(vec3(0.86, 1.0, 0.8), vec3(1.12, 1.02, 0.78), fract(seedOf() * 7.31)) * speciesTint();
}
void instanceCommon(vec3 root, float hf) { instanceCommonF(root, hf, uFade); }`;

function treeMaterial(uniforms, atlas, height, fade, { undergrowth = false, linear = false } = {}) {
  return new THREE.ShaderMaterial({
    uniforms: { ...uniforms, uAtlas: { value: atlas }, uHeightM: { value: height }, uFade: { value: new THREE.Vector4(...fade) },
      uAtlasSize: { value: new THREE.Vector2(atlas.image?.width || AT_W, atlas.image?.height || AT_H) },
      uBloom: { value: uniforms.uBloom?.value || [0, 1, 2, 3, 4].map(() => new THREE.Color(1, 1, 1)) } },
    defines: { ...(undergrowth ? { UNDERGROWTH: 1 } : {}), ...(undergrowth || linear ? { LINEAR_MAP: 1 } : {}) },
    side: THREE.DoubleSide,
    alphaToCoverage: true,
    vertexShader: /* glsl */`
      uniform float uHeightM, uTime;
      attribute float ao;
      attribute float bloom;
      varying vec2 vUv;
      varying vec3 vN;
      varying float vAO, vBloom;
      ${INSTANCE_VS}
      void main() {
        float c = cos(inst1.x), s = sin(inst1.x);
        // per-instance shape variation from the seed: one mesh reads as many trees
        float sd = seedOf();
        vec3 p = position * inst0.w * vec3(0.8 + 0.4 * fract(sd * 3.7), (0.88 + 0.24 * fract(sd * 5.3)) * stretchOf(), 0.8 + 0.4 * fract(sd * 3.7));
        float hf = clamp(position.y / uHeightM, 0.0, 1.0);
        vBloom = bloom * floor(inst1.y);
        float w = uTime * 1.1 + sd * 6.283 + inst0.x * 0.013;
        #ifdef UNDERGROWTH
          vec2 sway = vec2(sin(w * 2.3), cos(w * 1.7)) * 0.06 * hf;
        #else
          vec2 sway = vec2(sin(w), cos(w * 0.73)) * (0.12 + 0.05 * sin(w * 3.1 + position.x)) * hf * hf * inst0.w;
        #endif
        vec3 wp = vec3(c * p.x + s * p.z, p.y, -s * p.x + c * p.z) + inst0.xyz;
        wp.xz += sway;
        vN = vec3(c * normal.x + s * normal.z, normal.y, -s * normal.x + c * normal.z);
        vUv = uv; vAO = ao;
        instanceCommon(inst0.xyz, hf);
        vWorld = wp;
        gl_Position = projectionMatrix * viewMatrix * vec4(wp, 1.0);
      }`,
    fragmentShader: /* glsl */`
      uniform sampler2D uAtlas;
      uniform vec2 uAtlasSize;
      uniform vec3 uBloom[5];
      varying vec2 vUv;
      varying vec3 vN;
      varying float vAO, vBloom;
      varying float vFadeIn, vFadeOut, vSun, vSky;
      varying vec3 vWorld, vTint;
      ${ATMOSPHERE_PARS}
      ${LIGHT_PARS}
      ${DITHER}
      void main() {
        if (faded(vFadeIn, vFadeOut)) discard;
        vec4 t = texture2D(uAtlas, vUv);
        float a = coverage(t.a, vUv, uAtlasSize);
        if (a < 0.3) discard;
        #ifdef LINEAR_MAP
          vec3 alb = t.rgb;              // an ordinary sRGB texture (decoded on sampling)
        #else
          vec3 alb = t.rgb * t.rgb;      // sqrt-encoded atlas
        #endif
        vec3 tint = vTint;
        if (vBloom > 0.5) {               // flowering cards (stand-in shrubs): the species' bloom colour
          int bk = int(vBloom + 0.5);
          alb = uBloom[bk] * (0.75 + 0.5 * dot(alb, vec3(0.6))); tint = vec3(1.0);
        }
        vec3 n = normalize(vN);
        vec3 col = alb * tint * vAO * lightFoliage(n, vSun, vSky * vAO, 0.3);
        gl_FragColor = vec4(applyAtmosphere(col, vWorld), a);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}

function impostorMaterial(uniforms, alb, nrm, frames, size, fade) {
  return new THREE.ShaderMaterial({
    uniforms: { ...uniforms, uAlb: { value: alb }, uNrm: { value: nrm }, uFrames: { value: frames },
      uSize: { value: new THREE.Vector2(...size) }, uFade: { value: new THREE.Vector4(...fade) },
      uAtlasSize: { value: new THREE.Vector2(alb.image.width, alb.image.height) } },
    alphaToCoverage: true,
    vertexShader: /* glsl */`
      uniform float uFrames, uTime;
      uniform vec2 uSize;
      varying vec2 vUvL;
      varying float vF0, vF1, vBlend, vC, vS;
      varying vec3 vNv;
      ${INSTANCE_VS}
      void main() {
        vec3 base = inst0.xyz;
        vec3 toCam = cameraPosition - base; toCam.y = 0.0;
        toCam = normalize(toCam + vec3(1e-4, 0.0, 0.0));
        vec3 right = vec3(toCam.z, 0.0, -toCam.x);
        float c = cos(inst1.x), s = sin(inst1.x);
        // the view direction in the tree's own frame picks (and blends) the baked views
        float lx = toCam.x * c - toCam.z * s, lz = toCam.x * s + toCam.z * c;
        float f = (atan(lx, lz) / 6.2831853 + 1.0) * uFrames;
        float f0 = floor(f);
        vBlend = f - f0; vF0 = mod(f0, uFrames); vF1 = mod(f0 + 1.0, uFrames);
        vC = c; vS = s;
        float sd = seedOf();
        float w = uTime * 1.1 + sd * 6.283 + inst0.x * 0.013;
        vec3 wp = base + right * position.x * uSize.x * inst0.w * (0.8 + 0.4 * fract(sd * 3.7))
          + vec3(0.0, position.y * uSize.y * inst0.w * (0.88 + 0.24 * fract(sd * 5.3)) * stretchOf(), 0.0);
        wp.xz += vec2(sin(w), cos(w * 0.73)) * 0.12 * position.y * position.y * inst0.w;
        vUvL = vec2(position.x + 0.5, position.y);
        vNv = right * position.x * 1.6 + vec3(0.0, 0.5, 0.0) + toCam * 0.6;   // LOW: a rounded crown, no normal map
        instanceCommon(base, position.y);
        vWorld = wp;
        gl_Position = projectionMatrix * viewMatrix * vec4(wp, 1.0);
      }`,
    fragmentShader: /* glsl */`
      uniform sampler2D uAlb, uNrm;
      uniform float uFrames;
      uniform vec2 uAtlasSize;
      varying vec2 vUvL;
      varying float vF0, vF1, vBlend, vC, vS;
      varying vec3 vNv;
      varying float vFadeIn, vFadeOut, vSun, vSky;
      varying vec3 vWorld, vTint;
      ${ATMOSPHERE_PARS}
      ${LIGHT_PARS}
      ${DITHER}
      void main() {
        if (faded(vFadeIn, vFadeOut)) discard;
        #ifdef LOW
          // one frame, no normal map: 1 texture read instead of 4
          vec2 uv0 = vec2((floor(vF0 + vBlend + 0.5) - (vF0 + vBlend + 0.5 >= uFrames ? uFrames : 0.0) + vUvL.x) / uFrames, vUvL.y);
          vec4 t = texture2D(uAlb, uv0);
          if (t.a < 0.5) discard;
          float a = 1.0;
          vec3 n = normalize(vNv);
        #else
          vec2 uv0 = vec2((vF0 + vUvL.x) / uFrames, vUvL.y), uv1 = vec2((vF1 + vUvL.x) / uFrames, vUvL.y);
          vec4 a0 = texture2D(uAlb, uv0), a1 = texture2D(uAlb, uv1);
          vec4 t = mix(a0, a1, vBlend);
          float a = coverage(t.a, uv0, uAtlasSize);
          if (a < 0.3) discard;
          vec3 nl = normalize(mix(texture2D(uNrm, uv0).xyz, texture2D(uNrm, uv1).xyz, vBlend) * 2.0 - 1.0);
          vec3 n = vec3(vC * nl.x + vS * nl.z, nl.y, -vS * nl.x + vC * nl.z);
        #endif
        vec3 alb = t.rgb * t.rgb;        // sqrt-encoded albedo x AO (the bake)
        vec3 col = alb * vTint * lightFoliage(n, vSun, vSky * 0.8, 0.3);
        gl_FragColor = vec4(applyAtmosphere(col, vWorld), a);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}

// The kit's models (viewer/wild/veg.js): one material per LOD and role.
//   mode 'opaque': the hull + wood (part 0 wood map, 1 hull tile), no alpha test, drawn first
//                  (renderOrder -1) so early depth rejects the cards behind it
//   mode 'leaf':   the twig cards (alpha-tested, alpha-to-coverage, double-sided)
//   mode 'all':    hull + wood + cards in one draw (far LODs: one call per tier)
// Lighting: cards and hulls as foliage (wrap, bent normals, sun through the leaves); wood as a
// surface with a bounce term (the lit litter and the canopy's transmitted green under a closed
// roof: without it a cove trunk at a fifth of open light reads black).
function vegMaterial(uniforms, maps, height, fade, mode, { doubleSided = true, kind = 'broadleaf' } = {}) {
  const leafMap = maps.leaf || maps.shell || maps.wood, woodMap = maps.wood || maps.shell || maps.leaf, shellMap = maps.shell || maps.wood || maps.leaf;
  const soilMap = maps.soil || woodMap;
  const m = new THREE.ShaderMaterial({
    uniforms: { ...uniforms, tLeaf: { value: leafMap }, tWood: { value: woodMap }, tShell: { value: shellMap }, tSoil: { value: soilMap },
      uHeightM: { value: height }, uFade: { value: new THREE.Vector4(...fade) },
      uLeafSize: { value: new THREE.Vector2(leafMap?.image?.width || 1024, leafMap?.image?.height || 1024) },
      uBounce: uniforms.uBounce || { value: new THREE.Color(0.16, 0.2, 0.1) } },
    defines: { ...(mode !== 'opaque' ? { HAS_LEAF: 1 } : {}), ...(mode === 'leaf' ? { LEAF_ONLY: 1 } : {}), ...(mode === 'opaque' ? { NO_LEAF: 1 } : {}),
      ...(kind === 'clump' || kind === 'mat' ? { UNDERGROWTH: 1 } : {}) },
    side: doubleSided || mode !== 'opaque' ? THREE.DoubleSide : THREE.FrontSide,
    alphaToCoverage: mode !== 'opaque',
    vertexShader: /* glsl */`
      uniform float uHeightM, uTime;
      attribute float ao;
      attribute float part;
      varying vec2 vUv;
      varying vec3 vN;
      varying float vAO, vPart, vHf;
      ${INSTANCE_VS}
      void main() {
        float c = cos(inst1.x), s = sin(inst1.x);
        float sd = seedOf();
        vec3 p = position * inst0.w * vec3(0.9 + 0.2 * fract(sd * 3.7), (0.92 + 0.16 * fract(sd * 5.3)) * stretchOf(), 0.9 + 0.2 * fract(sd * 3.7));
        float hf = clamp(position.y / uHeightM, 0.0, 1.0);
        float w = uTime * 1.1 + sd * 6.283 + inst0.x * 0.013;
        #ifdef UNDERGROWTH
          vec2 sway = vec2(sin(w * 2.3), cos(w * 1.7)) * 0.05 * hf;
        #else
          vec2 sway = vec2(sin(w), cos(w * 0.73)) * (0.1 + 0.04 * sin(w * 3.1 + position.x)) * hf * hf * inst0.w;
          sway += (part > 1.5 ? 1.0 : 0.0) * vec2(sin(w * 4.1 + position.x * 0.7), cos(w * 3.3 + position.z * 0.7)) * 0.03 * hf;
        #endif
        vec3 wp = vec3(c * p.x + s * p.z, p.y, -s * p.x + c * p.z) + inst0.xyz;
        wp.xz += sway;
        vN = vec3(c * normal.x + s * normal.z, normal.y, -s * normal.x + c * normal.z);
        vUv = uv; vAO = ao; vPart = part; vHf = hf;
        instanceCommon(inst0.xyz, hf);
        vWorld = wp;
        gl_Position = projectionMatrix * viewMatrix * vec4(wp, 1.0);
      }`,
    fragmentShader: /* glsl */`
      uniform sampler2D tLeaf, tWood, tShell, tSoil;
      uniform vec2 uLeafSize;
      uniform vec3 uBounce;
      uniform float uHeightM;
      varying vec2 vUv;
      varying vec3 vN;
      varying float vAO, vPart, vHf;
      varying float vFadeIn, vFadeOut, vSun, vSky;
      varying vec3 vWorld, vTint;
      ${ATMOSPHERE_PARS}
      ${LIGHT_PARS}
      ${DITHER}
      void main() {
        if (faded(vFadeIn, vFadeOut)) discard;
        vec3 n = normalize(vN);
        vec3 col;
        float a = 1.0;
        #ifdef HAS_LEAF
        #ifndef LEAF_ONLY
        if (vPart > 1.5) {
        #endif
          vec4 t = texture2D(tLeaf, vUv);
          a = coverage(t.a, vUv, uLeafSize);
          if (a < 0.3) discard;
          vec3 v = normalize(vWorld - cameraPosition);
          float back = pow(max(dot(v, uSunDir), 0.0), 4.0) * 0.6;     // sun through the leaves
          col = t.rgb * vTint * vAO * (lightFoliage(n, vSun, vSky * vAO, 0.3) + uSunColor * back * vSun * 0.5);
        #ifndef LEAF_ONLY
        } else
        #endif
        #endif
        #ifndef LEAF_ONLY
        {
          if (!gl_FrontFacing) n = -n;
          if (vPart > 0.5 && vPart < 1.5) {
            // the hull: the same leaves as an opaque tile, lit as foliage
            vec3 alb = texture2D(tShell, vUv).rgb;
            col = alb * vTint * vAO * lightFoliage(n, vSun, vSky * vAO, 0.3);
          } else {
            vec3 alb = vPart > 2.5 ? texture2D(tSoil, vUv).rgb : texture2D(tWood, vUv).rgb;
            alb = mix(vec3(dot(alb, vec3(0.3, 0.5, 0.2))), alb, 0.6);     // (scanned barks run olive in this light)
            float ndl = clamp((dot(n, uSunDir) + 0.1) / 1.1, 0.0, 1.0);
            // bounce: lit ground below (stronger low on the trunk, facing down / out), the canopy's
            // green transmitted light from above; contact darkening in the last metre and a half
            float low = 1.0 - smoothstep(0.0, 0.25, vHf);
            vec3 amb = uSkyColor * vSky * (0.55 + 0.35 * n.y) + uBounce * (0.6 + 0.4 * low) * (0.7 - 0.3 * n.y);
            float contact = mix(0.6, 1.0, smoothstep(0.0, 1.5, vHf * uHeightM));
            // (bark keeps its own colour: no leaf tint; poplar, beech-grey buckeye and maple read silver)
            col = alb * mix(vAO, 1.0, 0.45) * contact * (uSunColor * ndl * vSun + amb);
          }
        }
        #endif
        gl_FragColor = vec4(applyAtmosphere(col, vWorld), a);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
  if (mode === 'opaque') m.alphaToCoverage = false;
  return m;
}

// One impostor atlas for every kit species (one far draw call for the whole forest): each
// species' LOD0 is rendered from 8 azimuths into its own rectangle of a shared albedo x AO and
// object-space normal atlas (shelf-packed rows). The instance's species slot (integer part of
// inst1.y) picks its rectangle and billboard size from uniform arrays.
export const IMP_SLOTS = 32;
function bakeSharedImpostors(renderer, entries, { width = 2048, frames = 8 } = {}) {
  // sizes
  const items = entries.map((e) => {
    const bb = new THREE.Box3();
    for (const p of e.parts) { p.geo.computeBoundingBox(); bb.union(p.geo.boundingBox); }
    const radius = Math.max(-bb.min.x, bb.max.x, -bb.min.z, bb.max.z) * 1.04;
    const H = bb.max.y * 1.02, W = Math.max(2 * radius, 0.25 * H);
    const cellH = e.cellH, cellW = Math.max(16, Math.ceil((cellH * W) / H / 4) * 4);
    return { ...e, radius, H, W, cellW, cellH, w: cellW * frames, h: cellH };
  });
  // shelf packing, tallest first, 4 px gutters
  const order = [...items].sort((a, b) => b.h - a.h);
  let x = 0, y = 0, rowH = 0;
  for (const it of order) {
    if (x + it.w > width) { x = 0; y += rowH + 4; rowH = 0; }
    it.x = x; it.y = y; x += it.w + 4; rowH = Math.max(rowH, it.h);
  }
  const height = Math.ceil((y + rowH) / 4) * 4;
  const mk = (mode, map, role) => new THREE.ShaderMaterial({
    uniforms: { uMap: { value: map } }, side: THREE.DoubleSide,
    vertexShader: `attribute float ao; varying vec2 vUv; varying vec3 vN; varying float vAO;
      void main() { vUv = uv; vN = normal; vAO = ao; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `uniform sampler2D uMap; varying vec2 vUv; varying vec3 vN; varying float vAO;
      void main() { vec4 t = texture2D(uMap, vUv); ${role === 'leaf' ? 'if (t.a < 0.5) discard;' : ''}
        ${mode === 1 ? 'gl_FragColor = vec4(normalize(vN) * 0.5 + 0.5, 1.0);' : 'gl_FragColor = vec4(sqrt(t.rgb * vAO), 1.0);'} }`,
  });
  // (the normal atlas at half resolution: lighting varies slower than the silhouette)
  const targets = [makeTarget(width, height, true), makeTarget(width / 2, height / 2, true)];
  for (const mode of [0, 1]) {
    const t = targets[mode], k = mode ? 0.5 : 1;
    renderer.setRenderTarget(t);
    t.scissorTest = false;
    renderer.setClearColor(mode === 0 ? new THREE.Color(0.17, 0.22, 0.12) : new THREE.Color(0.5, 0.75, 0.5), 0);
    renderer.clear();
    for (const it of items) {
      const scene = new THREE.Scene();
      for (const p of it.parts) { const m = new THREE.Mesh(p.geo, mk(mode, p.map, p.role)); scene.add(m); }
      const cam = new THREE.OrthographicCamera(-it.W / 2, it.W / 2, it.H, 0, 0.1, 4 * it.radius + 10);
      for (let f = 0; f < frames; f++) {
        const th = (f / frames) * Math.PI * 2;
        cam.position.set(Math.sin(th) * (2 * it.radius + 2), 0, Math.cos(th) * (2 * it.radius + 2));
        cam.lookAt(0, 0, 0); cam.updateMatrixWorld();
        const vp = [(it.x + f * it.cellW) * k, it.y * k, it.cellW * k, it.cellH * k];
        t.viewport.set(...vp); t.scissor.set(...vp); t.scissorTest = true;
        renderer.setRenderTarget(t);
        renderer.render(scene, cam);
      }
      for (const o of scene.children) o.material.dispose();
    }
    t.scissorTest = false;
    renderer.setRenderTarget(null);
  }
  for (const t of targets) { t.texture.name = `impostors_${t === targets[0] ? 'albedo' : 'normal'}`; }
  const rects = items.map((it) => new THREE.Vector4(it.x / width, it.y / height, it.cellW / width, it.cellH / height));
  const sizes = items.map((it) => new THREE.Vector2(it.W, it.H));
  return { alb: targets[0].texture, nrm: targets[1].texture, rects, sizes, frames, width, height, slots: items.map((it) => it.key) };
}

function sharedImpostorMaterial(uniforms, atlas, fade) {
  const pad = (a, v) => { const o = a.slice(); while (o.length < IMP_SLOTS) o.push(v.clone()); return o; };
  return new THREE.ShaderMaterial({
    uniforms: { ...uniforms, uAlb: { value: atlas.alb }, uNrm: { value: atlas.nrm }, uFrames: { value: atlas.frames },
      uRects: { value: pad(atlas.rects, new THREE.Vector4()) }, uSizes: { value: pad(atlas.sizes, new THREE.Vector2(1, 1)) },
      uFade: { value: new THREE.Vector4(...fade) }, uAtlasSize: { value: new THREE.Vector2(atlas.width, atlas.height) },
      uSlotFade: { value: pad(atlas.rects.map(() => new THREE.Vector4(...fade)), new THREE.Vector4(...fade)) } },
    alphaToCoverage: true,
    vertexShader: /* glsl */`
      uniform float uFrames, uTime;
      uniform vec4 uRects[${IMP_SLOTS}];
      uniform vec2 uSizes[${IMP_SLOTS}];
      uniform vec4 uSlotFade[${IMP_SLOTS}];
      varying vec2 vUvL;
      varying vec4 vRect;
      varying float vF0, vF1, vBlend, vC, vS;
      varying vec3 vNv;
      ${INSTANCE_VS}
      void main() {
        int slot = int(floor(inst1.y));
        vRect = uRects[slot];
        vec2 size = uSizes[slot];
        vec3 base = inst0.xyz;
        vec3 toCam = cameraPosition - base; toCam.y = 0.0;
        toCam = normalize(toCam + vec3(1e-4, 0.0, 0.0));
        vec3 right = vec3(toCam.z, 0.0, -toCam.x);
        float c = cos(inst1.x), s = sin(inst1.x);
        float lx = toCam.x * c - toCam.z * s, lz = toCam.x * s + toCam.z * c;
        float f = (atan(lx, lz) / 6.2831853 + 1.0) * uFrames;
        float f0 = floor(f);
        vBlend = f - f0; vF0 = mod(f0, uFrames); vF1 = mod(f0 + 1.0, uFrames);
        vC = c; vS = s;
        float sd = seedOf();
        float w = uTime * 1.1 + sd * 6.283 + inst0.x * 0.013;
        vec3 wp = base + right * position.x * size.x * inst0.w * (0.9 + 0.2 * fract(sd * 3.7))
          + vec3(0.0, position.y * size.y * inst0.w * (0.92 + 0.16 * fract(sd * 5.3)) * stretchOf(), 0.0);
        wp.xz += vec2(sin(w), cos(w * 0.73)) * 0.1 * position.y * position.y * inst0.w;
        vUvL = vec2(position.x + 0.5, position.y);
        vNv = right * position.x * 1.6 + vec3(0.0, 0.5, 0.0) + toCam * 0.6;
        instanceCommonF(base, position.y, uSlotFade[slot]);
        vWorld = wp;
        gl_Position = projectionMatrix * viewMatrix * vec4(wp, 1.0);
      }`,
    fragmentShader: /* glsl */`
      uniform sampler2D uAlb, uNrm;
      uniform float uFrames;
      uniform vec2 uAtlasSize;
      varying vec2 vUvL;
      varying vec4 vRect;
      varying float vF0, vF1, vBlend, vC, vS;
      varying vec3 vNv;
      varying float vFadeIn, vFadeOut, vSun, vSky;
      varying vec3 vWorld, vTint;
      ${ATMOSPHERE_PARS}
      ${LIGHT_PARS}
      ${DITHER}
      vec2 cellUv(float fr) { return vRect.xy + vec2((fr + clamp(vUvL.x, 0.01, 0.99)) * vRect.z, clamp(vUvL.y, 0.004, 0.996) * vRect.w); }
      void main() {
        if (faded(vFadeIn, vFadeOut)) discard;
        #ifdef LOW
          float fr = floor(vF0 + vBlend + 0.5); fr -= fr >= uFrames ? uFrames : 0.0;
          vec2 uv0 = cellUv(fr);
          vec4 t = texture2D(uAlb, uv0);
          if (t.a < 0.5) discard;
          float a = 1.0;
          vec3 n = normalize(vNv);
        #else
          vec2 uv0 = cellUv(vF0), uv1 = cellUv(vF1);
          vec4 t = mix(texture2D(uAlb, uv0), texture2D(uAlb, uv1), vBlend);
          float a = coverage(t.a, uv0, uAtlasSize);
          if (a < 0.3) discard;
          vec3 nl = normalize(mix(texture2D(uNrm, uv0).xyz, texture2D(uNrm, uv1).xyz, vBlend) * 2.0 - 1.0);
          vec3 n = vec3(vC * nl.x + vS * nl.z, nl.y, -vS * nl.x + vC * nl.z);
        #endif
        vec3 alb = t.rgb * t.rgb;
        vec3 col = alb * vTint * lightFoliage(n, vSun, vSky * 0.8, 0.3);
        gl_FragColor = vec4(applyAtmosphere(col, vWorld), a);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}

// render a species' near mesh (one or more parts: geometry + texture) from `frames` azimuths
// into albedo + normal atlases
function bakeImpostor(renderer, parts, frames = 8, cellH = 256) {
  const bb = new THREE.Box3();
  for (const p of parts) { p.geo.computeBoundingBox(); bb.union(p.geo.boundingBox); }
  const radius = Math.max(-bb.min.x, bb.max.x, -bb.min.z, bb.max.z) * 1.04;
  const H = bb.max.y * 1.02, W = Math.max(2 * radius, 0.25 * H);
  const cellW = Math.ceil((cellH * W) / H / 8) * 8;
  const mk = (mode, map, linear) => new THREE.ShaderMaterial({
    uniforms: { uAtlas: { value: map } }, side: THREE.DoubleSide,
    vertexShader: `attribute float ao; varying vec2 vUv; varying vec3 vN; varying float vAO;
      void main() { vUv = uv; vN = normal; vAO = ao; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `uniform sampler2D uAtlas; varying vec2 vUv; varying vec3 vN; varying float vAO;
      void main() { vec4 t = texture2D(uAtlas, vUv); if (t.a < 0.5) discard;
        ${mode === 1 ? 'gl_FragColor = vec4(normalize(vN) * 0.5 + 0.5, 1.0);'
          : linear ? 'gl_FragColor = vec4(sqrt(t.rgb * vAO), 1.0);' : 'gl_FragColor = vec4(t.rgb * sqrt(vAO), 1.0);'} }`,
  });
  const scene = new THREE.Scene();
  const meshes = parts.map((p) => { const m = new THREE.Mesh(p.geo); scene.add(m); return m; });
  const cam = new THREE.OrthographicCamera(-W / 2, W / 2, H, 0, 0.1, 4 * radius + 10);
  const out = [];
  for (const mode of [0, 1]) {
    meshes.forEach((m, i) => (m.material = mk(mode, parts[i].map, parts[i].linear)));
    const t = makeTarget(cellW * frames, cellH, true);
    renderer.setRenderTarget(t);
    renderer.setClearColor(mode === 0 ? new THREE.Color(0.18, 0.24, 0.14) : new THREE.Color(0.5, 0.75, 0.5), 0);
    renderer.clear();
    for (let k = 0; k < frames; k++) {
      const th = (k / frames) * Math.PI * 2;
      cam.position.set(Math.sin(th) * (2 * radius + 2), 0, Math.cos(th) * (2 * radius + 2));
      cam.lookAt(0, 0, 0);
      cam.updateMatrixWorld();
      t.viewport.set(k * cellW, 0, cellW, cellH); t.scissor.set(k * cellW, 0, cellW, cellH); t.scissorTest = true;
      renderer.setRenderTarget(t);
      renderer.render(scene, cam);
    }
    renderer.setRenderTarget(null);
    out.push(t.texture);
  }
  // (the clear colour, a foliage average, fills the transparent texels: no dark mip fringes)
  return { alb: out[0], nrm: out[1], size: [W, H], frames };
}

// ---------------------------------------------------------------- forest
// mean colour (linear) of a texture's opaque texels: the reference a species tint is relative to
export function meanColor(t) {
  const img = t.image;
  let data, w, h;
  if (img?.data) { data = img.data; w = img.width; h = img.height; }
  else if (img) {
    const c = document.createElement('canvas'); c.width = c.height = 64;
    const ctx = c.getContext('2d'); ctx.drawImage(img, 0, 0, 64, 64);
    data = ctx.getImageData(0, 0, 64, 64).data; w = h = 64;
  } else return [0.2, 0.3, 0.1];
  const lin = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
  let r = 0, g = 0, b = 0, n = 0;
  const step = Math.max(1, Math.floor((w * h) / 20000));
  for (let i = 0; i < w * h; i += step) {
    if (data[i * 4 + 3] < 128) continue;
    r += lin(data[i * 4]); g += lin(data[i * 4 + 1]); b += lin(data[i * 4 + 2]); n++;
  }
  return n ? [r / n, g / n, b / n] : [0.2, 0.3, 0.1];
}
const packTint = (m) => m.reduce((a, v) => a * 256 + Math.max(1, Math.min(255, Math.round(v * 100))), 0);

// tier names by a species' tier class, for stand-ins / production models
const TIER_SETS = {
  tree: { stand: ['near', 'mid', 'far'], veg: ['lod0', 'lod1', 'lod2', 'vfar'] },
  shrub: { stand: ['snear', 'smid', 'sfar'], veg: ['slod0', 'slod1', 'slod2', 'sfar'] },
  under: { stand: ['under'], veg: ['ulod0', 'ulod1', 'ulod2'] },
};

export class Forest {
  constructor(world, renderer, uniforms, tex, opts = {}) {
    this.world = world;
    // (production trees' impostors start where their LOD2 ends: 'vfar', not the stand-ins' 'far')
    this.tiers = { ...TIERS, lod0: TIERS_VEG.lod0, lod1: TIERS_VEG.lod1, lod2: TIERS_VEG.lod2, vfar: TIERS_VEG.far, ...(opts.tiers || {}) };
    if (world.speciesInfo) { this.buildGrouped(world, renderer, uniforms, tex, opts); return; }
    const needles = needleTexture();
    const atlases = {
      broadleaf: buildAtlas(renderer, tex.leaves, tex.bark, [1, 1, 1]),
      conifer: buildAtlas(renderer, needles, tex.bark, [0.85, 0.8, 0.78]),
      pine: buildAtlas(renderer, needles, tex.bark, [1.25, 0.85, 0.62]),
    };
    const builders = { broadleaf: buildBroadleaf, conifer: buildConifer, pine: buildPine };
    this.species = [];
    const mapXf = { uMapXf: { value: new THREE.Vector4(-world.size / 2, -world.size / 2, 1 / world.size, 0) }, uLight: { value: tex.light } };
    const U = { ...uniforms, ...mapXf };
    const quadGeo = new THREE.PlaneGeometry(1, 1, 1, 1).translate(0, 0.5, 0);
    for (const name of ['broadleaf', 'conifer', 'pine']) {
      const veg = opts.veg?.[name];
      if (veg) {
        // production-weight trees (blender/wilderness/trees.py): LOD0-2, bark + leaf each
        const T = this.tiers;
        const bands = [T.lod0, T.lod1, T.lod2];
        const imp = bakeImpostor(renderer, veg.lods[0].map((p) => ({ ...p, linear: true })));
        const H = imp.size[1] / 1.02;
        this.species.push(this.makeSpecies(name, [
          ...veg.lods.map((parts, i) => ({ tier: `lod${i}`, parts: parts.map((p) => ({ geo: p.geo, mat: treeMaterial(U, p.map, H, bands[i], { linear: true }) })) })),
          { tier: 'far', parts: [{ geo: quadGeo, mat: impostorMaterial(U, imp.alb, imp.nrm, imp.frames, imp.size, this.tiers.far) }] },
        ], { height: H, tris: [...veg.lods.map((parts) => parts.reduce((a, p) => a + p.geo.index.count / 3, 0)), 2], veg: veg.name }));
        continue;
      }
      const near = builders[name](0), mid = builders[name](1);
      const imp = bakeImpostor(renderer, [{ geo: near, map: atlases[name] }]);
      const H = near.boundingBox.max.y;
      this.species.push(this.makeSpecies(name, [
        { tier: 'near', parts: [{ geo: near, mat: treeMaterial(U, atlases[name], H, this.tiers.near) }] },
        { tier: 'mid', parts: [{ geo: mid, mat: treeMaterial(U, atlases[name], H, this.tiers.mid) }] },
        { tier: 'far', parts: [{ geo: quadGeo, mat: impostorMaterial(U, imp.alb, imp.nrm, imp.frames, imp.size, this.tiers.far) }] },
      ], { height: H, tris: [near.index.count / 3, mid.index.count / 3, 2] }));
    }
    for (const [name, build] of [['fern', buildFern], ['tuft', buildTuft]]) {
      const geo = build();
      this.species.push(this.makeSpecies(name, [
        { tier: 'under', parts: [{ geo, mat: treeMaterial(U, tex.foliage, geo.boundingBox.max.y, this.tiers.under, { undergrowth: true }) }] },
      ], { height: geo.boundingBox.max.y, tris: [geo.index.count / 3] }));
    }
    this.group = new THREE.Group();
    for (const s of this.species) for (const t of s.tiers) for (const m of t.meshes) this.group.add(m);
    this.buildCells();
    this.stats = {};
  }

  // A level's species table (world.speciesInfo): every species id with instances is drawn
  // with its production model when opts.vegModels has it (the vegetation agent's glTF: LOD0-2,
  // bark / leaf / ... primitives, an impostor baked here from LOD0), otherwise with the stand-in
  // of its kind. Stand-in species share one render group per kind (draw calls stay per kind):
  // each instance carries its species' size (height / width over the mesh's), tint (the species'
  // leaf colour over the stand-in texture's) and bloom.
  buildGrouped(world, renderer, uniforms, tex, opts) {
    const mapXf = { uMapXf: { value: new THREE.Vector4(-world.size / 2, -world.size / 2, 1 / world.size, 0) }, uLight: { value: tex.light } };
    const U = { ...uniforms, ...mapXf };
    const quadGeo = new THREE.PlaneGeometry(1, 1, 1, 1).translate(0, 0.5, 0);
    const lin = (c) => c.map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
    // groups: veg:<id> (own model) or the stand-in kind
    const groups = new Map();
    for (const [id, info] of Object.entries(world.speciesInfo)) {
      const arr = world.species[id];
      if (!arr || !arr.length) continue;
      const veg = opts.vegModels?.[id];
      // (by model: the ring's forest shares the cove species' draw calls)
      const key = veg ? `veg:${veg.name}` : info.kind;
      if (!groups.has(key)) groups.set(key, { key, kind: info.kind, tier: info.tier, veg, tile: !!info.tile, ids: [] });
      groups.get(key).ids.push(id);
    }
    // the stand-ins' atlases and reference colours, only when some species still needs them
    let atlases = null, ref = null;
    if ([...groups.values()].some((G) => !G.veg)) {
      const needles = needleTexture();
      atlases = {
        broadleaf: buildAtlas(renderer, tex.leaves, tex.bark, [1, 1, 1]),
        conifer: buildAtlas(renderer, needles, tex.bark, [0.85, 0.8, 0.78]),
        pine: buildAtlas(renderer, needles, tex.bark, [1.25, 0.85, 0.62]),
      };
      atlases.shrub = atlases.broadleaf;
      const nm = meanColor(needles);
      ref = { broadleaf: meanColor(tex.leaves), conifer: nm.map((v, i) => v * [0.72, 0.64, 0.61][i]), pine: nm.map((v, i) => v * [1.56, 0.72, 0.38][i]),
        fern: meanColor(tex.foliage), tuft: meanColor(tex.foliage) };
      ref.shrub = ref.broadleaf;
    }
    const builders = { broadleaf: buildBroadleaf, conifer: buildConifer, pine: buildPine, shrub: buildShrub, fern: () => buildFern(), tuft: () => buildTuft() };

    // the kit species' impostors: one shared atlas, one far draw for all of them
    const vegGroups = [...groups.values()].filter((G) => G.veg);
    const impEntries = vegGroups.filter((G) => (G.tier === 'tree' && !/snag/.test(G.veg.name)) || (G.tier === 'shrub' && !G.tile))
      .map((G) => ({ key: G.key, parts: G.veg.variants[0].lods[0].parts,
        cellH: G.tier === 'tree' ? ((G.veg.sp.height_m || 30) > 30 ? 256 : (G.veg.sp.height_m || 30) > 15 ? 192 : 128) : 112 }));
    let shared = null;
    if (impEntries.length) {
      const atlas = bakeSharedImpostors(renderer, impEntries);
      this.impostorAtlas = atlas;
      const mat = sharedImpostorMaterial(U, atlas, this.tiers.vfar);
      const tier = this.makeTier(quadGeo, mat, 'impostors', Math.max(1, vegGroups.reduce((a, G) => a + G.ids.reduce((b, id) => b + world.species[id].length / 6, 0), 0)));
      shared = { ...tier, slots: atlas.slots, tierName: 'vfar' };
      this.shared = shared;
    }

    this.species = [];
    this.groups = {};
    for (const G of groups.values()) {
      let parts, H, W, tris;
      if (G.veg) {
        const vars = G.veg.variants, base = vars[0].lods;
        const bb = new THREE.Box3();
        for (const p of base[0].parts) { p.geo.computeBoundingBox(); bb.union(p.geo.boundingBox); }
        H = bb.max.y; W = Math.max(bb.max.x - bb.min.x, bb.max.z - bb.min.z);
        const kind = G.veg.kind, dbl = G.tile || kind === 'mat';
        const mat = (lod, mode, band) => vegMaterial(U, lod.maps, H, this.tiers[band], mode, { doubleSided: dbl, kind });
        // per tier: [band name, lod index, split (opaque + leaf draws) or merged]
        // per tier, a draw call per LOD (two for a heath's LOD0: hull + cards). Small trees (the
        // understory, < 15 m) go from LOD1 to the impostor; the few snags are one LOD1 tier;
        // ground cover is its LOD0 to its cull distance (40-144 triangles: a second LOD only cost calls)
        const small = G.tier === 'tree' && (G.veg.sp.height_m || 30) < 15, snag = G.veg.kind === 'conifer' && /snag/.test(G.veg.name);
        // (opts.split: opaque + leaf draws for every tree LOD instead of one merged draw: a software
        // rasteriser runs both sides of the merged shader's branch, sampling bark and hull for every leaf)
        const sp_ = !!opts.split;
        const plan = snag ? [['snag', 1, false]]
          : small ? [['lod0', 0, sp_], ['lod1', 1, sp_]]
          : G.tier === 'tree' ? [['lod0', 0, sp_], ['lod1', 1, sp_], ['lod2', 2, sp_]]
          : G.tier === 'shrub' && G.tile ? [['slod0', 0, true], ['slod1', 1, false], ['tlod2', 2, false]]
          : G.tier === 'shrub' ? [['slod0', 0, true], ['slod1', 1, false]]
          : [['ucover', 0, false]];
        parts = [];
        for (const [band, li, split] of plan) {
          if (li >= base.length) continue;
          const subFor = (lods) => {
            const L = lods[Math.min(li, lods.length - 1)];
            if (split && L.opaque && L.leaf) {
              const o = { geo: L.opaque, mat: mat(L, 'opaque', band), order: -1 };
              return [o, { geo: L.leaf, mat: mat(L, 'leaf', band) }];
            }
            return [{ geo: L.all, mat: mat(L, 'all', band), order: L.opaque && !L.leaf ? -1 : 0 }];
          };
          // variants (seeded re-growths) only on the near tiers: they look alike from LOD2 on
          // (LOD0 only, and not for ground cover: variants cost a draw call per tier in range)
          const subs = (li === 0 && G.tier !== 'under' ? vars : vars.slice(0, 1)).map((v) => subFor(v.lods));
          parts.push({ tier: band, subs });
        }
        const slot = shared ? shared.slots.indexOf(G.key) : -1;
        if (slot >= 0 && !snag) parts.push({ tier: small ? 'timp' : G.tier === 'tree' ? 'vfar' : 'simp', shared, slot });
        tris = [...base.map((L) => L.tris), 2];
      } else {
        const b = builders[G.kind];
        const tiers = TIER_SETS[G.tier] || TIER_SETS.tree;
        const near = b(0);
        near.computeBoundingBox();
        H = near.boundingBox.max.y;
        W = Math.max(near.boundingBox.max.x - near.boundingBox.min.x, near.boundingBox.max.z - near.boundingBox.min.z);
        const atlas = atlases[G.kind] || tex.foliage, under = G.tier === 'under';
        if (tiers.stand.length === 1) {
          parts = [{ tier: tiers.stand[0], parts: [{ geo: near, mat: treeMaterial(U, atlas, H, this.tiers[tiers.stand[0]], { undergrowth: under }) }] }];
          tris = [near.index.count / 3];
        } else {
          const mid = b(1);
          const imp = bakeImpostor(renderer, [{ geo: near, map: atlas }], 8, G.tier === 'shrub' ? 128 : 256);
          parts = [
            { tier: tiers.stand[0], parts: [{ geo: near, mat: treeMaterial(U, atlas, H, this.tiers[tiers.stand[0]]) }] },
            { tier: tiers.stand[1], parts: [{ geo: mid, mat: treeMaterial(U, atlas, H, this.tiers[tiers.stand[1]]) }] },
            { tier: tiers.stand[2], parts: [{ geo: quadGeo, mat: impostorMaterial(U, imp.alb, imp.nrm, imp.frames, imp.size, this.tiers[tiers.stand[2]]) }] },
          ];
          tris = [near.index.count / 3, mid.index.count / 3, 2];
        }
      }
      // instances: 8 floats (x, y, z, horizontal scale, rotY, seed+bloom, stretch, tint)
      let n = 0;
      for (const id of G.ids) n += world.species[id].length / 6;
      const src8 = new Float32Array(n * 8);
      let o = 0;
      for (const id of G.ids) {
        const info = world.speciesInfo[id], a = world.species[id];
        const sh = info.width / W, sv = info.height / H;
        let tint = 0;
        if (!G.veg) {
          const t = lin(info.tint_rgb), rr = ref[G.kind] || [0.2, 0.3, 0.1];
          tint = packTint(t.map((v, i) => Math.min(2.5, Math.max(0.25, v / Math.max(rr[i], 1e-3)))));
        }
        // kit models are drawn at their own proportions (the placement's size scales them evenly)
        const hs = G.veg ? sv : sh, st = G.veg ? 1 : sv / sh;
        for (let q = 0; q < a.length; q += 6) {
          src8.set([a[q], a[q + 1], a[q + 2], a[q + 3] * hs, a[q + 4], a[q + 5], st, tint], o);
          o += 8;
        }
      }
      const name = G.veg ? G.ids[0] : G.kind;
      const sp = this.makeSpecies(name, parts, { height: H, tris, veg: G.veg?.name, ids: G.ids, variants: G.veg?.variants.length || 1 }, src8);
      this.species.push(sp);
      this.groups[name] = { ids: G.ids, model: G.veg ? 'veg' : 'stand-in', instances: n, height: +H.toFixed(1), variants: G.veg?.variants.map((v) => v.name) };
    }
    this.group = new THREE.Group();
    for (const s of this.species) for (const t of s.tiers) for (const sub of t.subs || []) for (const m of sub.meshes) this.group.add(m);
    if (shared) for (const m of shared.meshes) this.group.add(m);
    this.buildCells();
    this.stats = {};
  }

  // an instance buffer (8 floats per instance) and the meshes drawing from it
  makeTier(geoOrParts, mat, label, cap) {
    const list = Array.isArray(geoOrParts) ? geoOrParts : [{ geo: geoOrParts, mat }];
    const data = new Float32Array(Math.max(1, cap) * 8);
    const buf = new THREE.InstancedInterleavedBuffer(data, 8);
    buf.setUsage(THREE.DynamicDrawUsage);
    const meshes = list.map((p, i) => {
      const g = new THREE.InstancedBufferGeometry();
      g.index = p.geo.index;
      for (const [k, a] of Object.entries(p.geo.attributes)) g.setAttribute(k, a);
      g.setAttribute('inst0', new THREE.InterleavedBufferAttribute(buf, 4, 0));
      g.setAttribute('inst1', new THREE.InterleavedBufferAttribute(buf, 4, 4));
      g.instanceCount = 0;
      const mesh = new THREE.Mesh(g, p.mat);
      mesh.frustumCulled = false;
      if (p.order) mesh.renderOrder = p.order;
      mesh.name = `Wild_${label}${list.length > 1 ? '_' + (p.mat.defines?.NO_LEAF ? 'hull' : p.mat.defines?.LEAF_ONLY ? 'leaf' : i) : ''}`;
      return mesh;
    });
    return { meshes, data, buf, count: 0 };
  }

  // one instance buffer per tier (per variant), shared by the tier's parts (e.g. hull + cards = 2
  // draw calls); a `shared` tier appends into the forest-wide impostor buffer with its slot
  makeSpecies(name, tiers, info, src8 = null) {
    if (!src8) {                     // synthetic world: 6 floats per instance -> 8
      const a = this.world.species[name], m = a.length / 6;
      src8 = new Float32Array(m * 8);
      for (let q = 0; q < m; q++) for (let k = 0; k < 6; k++) src8[q * 8 + k] = a[q * 6 + k];
    }
    const n = src8.length / 8;
    const out = { name, n, ...info, src8, tiers: [] };
    for (const t of tiers) {
      const band = this.tiers[t.tier];
      const lohi = { lo: band[0] - 1, hi: band[3] + 1 };
      if (t.shared) { out.tiers.push({ tier: t.tier, shared: t.shared, slot: t.slot, count: 0, ...lohi }); continue; }
      const subsSpec = t.subs || [t.parts];
      const subs = subsSpec.map((parts, v) => this.makeTier(parts, null, `${name}${v ? '_v' + (v + 1) : ''}_${t.tier}`, n));
      out.tiers.push({ tier: t.tier, subs, vActive: subs.length, count: 0, ...lohi,
        // (back compat: the first variant's buffer and meshes)
        meshes: subs.flatMap((s) => s.meshes), data: subs[0].data, buf: subs[0].buf });
    }
    return out;
  }

  // sort every species' instances by 64 m cell; per cell: [start, count] per species + bounds
  buildCells() {
    const { size } = this.world, nc = Math.ceil(size / CELL), half = size / 2;
    this.nc = nc;
    this.cells = [];
    for (let j = 0; j < nc; j++) for (let i = 0; i < nc; i++)
      this.cells.push({ box: new THREE.Box3(new THREE.Vector3(-half + i * CELL, Infinity, -half + j * CELL),
        new THREE.Vector3(-half + (i + 1) * CELL, -Infinity, -half + (j + 1) * CELL)), ranges: [], centre: new THREE.Vector3() });
    for (const [si, sp] of this.species.entries()) {
      const src = sp.src8, n = sp.n;
      const key = new Int32Array(n), counts = new Int32Array(nc * nc);
      for (let q = 0; q < n; q++) {
        const i = Math.max(0, Math.min(nc - 1, Math.floor((src[q * 8] + half) / CELL))), j = Math.max(0, Math.min(nc - 1, Math.floor((src[q * 8 + 2] + half) / CELL)));
        key[q] = i + j * nc; counts[key[q]]++;
      }
      const start = new Int32Array(nc * nc); let acc = 0;
      for (let c = 0; c < nc * nc; c++) { start[c] = acc; acc += counts[c]; }
      const fill = start.slice(), sorted = new Float32Array(n * 8);
      for (let q = 0; q < n; q++) {
        const o = fill[key[q]]++ * 8;
        for (let k = 0; k < 8; k++) sorted[o + k] = src[q * 8 + k];
        const box = this.cells[key[q]].box, y = src[q * 8 + 1];
        // (instances outside the square, the ring's forest, are kept in the edge cells: grow the box)
        const ix = src[q * 8], iz = src[q * 8 + 2];
        if (ix < box.min.x) box.min.x = ix - 10; if (ix > box.max.x) box.max.x = ix + 10;
        if (iz < box.min.z) box.min.z = iz - 10; if (iz > box.max.z) box.max.z = iz + 10;
        box.min.y = Math.min(box.min.y, y);
        box.max.y = Math.max(box.max.y, y + sp.height * src[q * 8 + 3] * (src[q * 8 + 6] || 1) * 1.15);   // (+ the shader's height stretch)
      }
      sp.src8 = null;
      sp.sorted = sorted;
      // the shared impostor tier reads a copy whose seed carries the species' slot
      const st = sp.tiers.find((t) => t.shared);
      if (st) {
        const imp = sorted.slice();
        for (let q = 0; q < n; q++) imp[q * 8 + 5] = st.slot + (imp[q * 8 + 5] % 1);
        sp.sortedImp = imp;
      }
      for (let c = 0; c < nc * nc; c++) this.cells[c].ranges[si] = [start[c], counts[c]];
    }
    for (const c of this.cells) {
      if (c.box.min.y === Infinity) { c.box.min.y = 0; c.box.max.y = 0; c.empty = true; }
      c.box.getCenter(c.centre);
      c.radius = c.box.min.distanceTo(c.box.max) / 2;
    }
  }

  update(camera, frustum) {
    const t0 = performance.now();
    const cam = camera.position;
    const vis = [];
    for (const c of this.cells) {
      if (c.empty || !frustum.intersectsBox(c.box)) continue;
      const dmin = c.box.distanceToPoint(cam), dmax = cam.distanceTo(c.centre) + c.radius;
      vis.push({ c, dmin, dmax });
    }
    vis.sort((a, b) => a.dmin - b.dmin);       // front to back: early depth rejection in forests
    let instances = 0;
    if (this.shared) this.shared.count = 0;
    for (const [si, sp] of this.species.entries()) {
      for (const t of sp.tiers) {
        const S = t.shared ? sp.sortedImp : sp.sorted;
        // destination buffers: the shared impostor buffer, or this tier's per-variant buffers
        const dst = t.shared ? [t.shared] : t.subs.slice(0, t.vActive);
        const V = dst.length;
        const cnt = dst.map((d) => (t.shared ? d.count : 0));
        const n0 = cnt[0];
        for (const { c, dmin, dmax } of vis) {
          const [st, nn] = c.ranges[si];
          if (!nn || dmax < t.lo || dmin > t.hi) continue;
          if (V === 1 && dmin >= t.lo && dmax <= t.hi) { dst[0].data.set(S.subarray(st * 8, (st + nn) * 8), cnt[0] * 8); cnt[0] += nn; continue; }
          for (let q = st; q < st + nn; q++) {
            const o = q * 8, dx = S[o] - cam.x, dy = S[o + 1] - cam.y, dz = S[o + 2] - cam.z;
            const d = Math.sqrt(dx * dx + dy * dy + dz * dz);
            if (d < t.lo || d > t.hi) continue;
            const v = V === 1 ? 0 : Math.min(V - 1, Math.floor(((S[o + 5] * 7.919) % 1) * V));
            const D = dst[v].data, w = cnt[v] * 8;
            for (let k = 0; k < 8; k++) D[w + k] = S[o + k];
            cnt[v]++;
          }
        }
        if (t.shared) { t.count = cnt[0] - n0; t.shared.count = cnt[0]; instances += t.count; continue; }
        t.count = 0;
        t.subs.forEach((sub, v) => {
          const n = v < V ? cnt[v] : 0;
          sub.count = n; t.count += n;
          for (const m of sub.meshes) { m.geometry.instanceCount = n; m.visible = n > 0; }
          sub.buf.clearUpdateRanges();
          sub.buf.addUpdateRange(0, n * 8);
          sub.buf.needsUpdate = true;
        });
        instances += t.count;
      }
    }
    if (this.shared) {
      const s = this.shared;
      for (const m of s.meshes) { m.geometry.instanceCount = s.count; m.visible = s.count > 0; }
      s.buf.clearUpdateRanges(); s.buf.addUpdateRange(0, s.count * 8); s.buf.needsUpdate = true;
    }
    this.stats = { cells: vis.length, instances, cpuMs: +(performance.now() - t0).toFixed(2),
      tiers: Object.fromEntries(this.species.map((s) => [s.name, s.tiers.map((t) => t.count)])) };
  }

  // quality levels: new distance bands per tier name (missing names keep theirs); `variants`:
  // how many of a species' variants the near tiers may use
  setTiers(bands, variants = null) {
    for (const sp of this.species) for (const t of sp.tiers) {
      const b = bands[t.tier];
      if (variants !== null && t.subs) t.vActive = Math.max(1, Math.min(t.subs.length, variants));
      if (!b) continue;
      t.lo = b[0] - 1; t.hi = b[3] + 1;
      if (t.subs) for (const sub of t.subs) for (const m of sub.meshes) m.material.uniforms.uFade.value.set(...b);
    }
    // (the shared impostor draw fades each species by its own band: trees vfar, shrubs sfar)
    if (this.shared) for (const sp of this.species) for (const t of sp.tiers) {
      if (!t.shared) continue;
      const b = this.tiers[t.tier] = bands[t.tier] || this.tiers[t.tier];
      for (const m of this.shared.meshes) m.material.uniforms.uSlotFade.value[t.slot].set(...b);
    }
  }

  // low quality: impostors read one frame and no normal map
  setLow(low) {
    const mats = [];
    for (const sp of this.species) for (const t of sp.tiers) {
      if (!['far', 'vfar', 'sfar', 'simp'].includes(t.tier) || !t.subs) continue;
      for (const sub of t.subs) for (const m of sub.meshes) mats.push(m.material);
    }
    if (this.shared) for (const m of this.shared.meshes) mats.push(m.material);
    for (const m of mats) {
      if (!!m.defines.LOW === low) continue;
      if (low) m.defines.LOW = 1; else delete m.defines.LOW;
      m.needsUpdate = true;
    }
  }

  // trunk colliders for the player (fixed boxes: viewer/player.js puts them in its grid)
  colliders() {
    const out = [];
    for (const sp of this.species) {
      const r0 = { broadleaf: 0.3, conifer: 0.25, pine: 0.24 }[sp.name];
      if (!r0) continue;
      const S = sp.sorted;
      for (let q = 0; q < sp.n; q++) {
        const o = q * 8, r = r0 * S[o + 3];
        const b = new THREE.Box3(new THREE.Vector3(S[o] - r, S[o + 1] - 1, S[o + 2] - r), new THREE.Vector3(S[o] + r, S[o + 1] + 6, S[o + 2] + r));
        b.fixed = true;
        out.push(b);
      }
    }
    return out;
  }
}
