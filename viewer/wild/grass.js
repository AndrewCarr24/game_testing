import * as THREE from 'three';
import { ATMOSPHERE_PARS } from './atmosphere.js';
import { rng } from './noise.js';

// Near-only grass: one 8 x 8 m tile of blades (3 triangles each, at random places, ordered by
// their random number, so any prefix is an even subset and a density d keeps exactly the
// first d of them), instanced over the tiles around the camera that pass the frustum
// test. Two tiers, one draw call each: the dense ring (every blade) and the outer ring (the
// first third of the blades, wider; also the near tiles whose grass density never exceeds a
// third: they would discard the rest anyway). Inside the dense ring the other two thirds shrink away
// before its edge and the kept blades widen, so the switch is invisible; the outer ring's
// blades shrink to nothing at its edge, where the terrain's own grass texture takes over.
// Each blade sits on the heightfield (4 texel fetches at its root), takes its density from the
// splat's grass weight, its colour from the terrain's grass texture (a low mip = the colour
// the ground shows at that spot) and its light from the baked light map, and bends in the
// wind (travelling gusts). Nothing per blade lives on the CPU.

const TILE = 8;

export class Grass {
  constructor(world, tex, uniforms, { blades = 4500, dense = [9, 15], far = [30, 38], seed = 21, floor = 0.25, height = 1.0, tint = [1.05, 1.0, 0.78], hay = false } = {}) {
    this.floor = floor;
    this.world = world;
    this.dense = dense; this.far = far;
    const r = rng(seed), B = blades;
    const bl = new Float32Array(B * 5 * 4), sh = new Float32Array(B * 5 * 3), idx = new Uint32Array(B * 9);
    const SH = [[-1, 0], [1, 0], [-0.7, 0.5], [0.7, 0.5], [0, 1]];
    for (let b = 0; b < B; b++) {
      const x = r() * TILE, z = r() * TILE, a = r() * Math.PI, s = (b + r()) / B;   // blades sorted by their random
      for (let v = 0; v < 5; v++) {
        const k = b * 5 + v;
        bl.set([x, z, a, s], k * 4);
        sh.set([SH[v][0], SH[v][1], b / B], k * 3);
      }
      const o = b * 5;
      idx.set([o, o + 1, o + 2, o + 2, o + 1, o + 3, o + 2, o + 3, o + 4], b * 9);
    }
    const base = new THREE.BufferGeometry();
    base.setAttribute('position', new THREE.BufferAttribute(sh, 3));   // (side, t, rank)
    base.setAttribute('blade', new THREE.BufferAttribute(bl, 4));
    base.setIndex(new THREE.BufferAttribute(idx, 1));

    const n = Math.ceil((2 * far[1]) / TILE + 2) ** 2;
    this.tiers = [];
    for (const [name, frac] of [['dense', 1], ['outer', 1 / 3]]) {
      const g = new THREE.InstancedBufferGeometry();
      g.index = base.index;
      g.setAttribute('position', base.attributes.position);
      g.setAttribute('blade', base.attributes.blade);
      const data = new Float32Array(n * 2), attr = new THREE.InstancedBufferAttribute(data, 2);
      attr.setUsage(THREE.DynamicDrawUsage);
      g.setAttribute('tile', attr);
      g.setDrawRange(0, Math.floor(B * frac) * 9);
      g.instanceCount = 0;
      const material = new THREE.ShaderMaterial({
        uniforms: {
          ...uniforms,
          uHeight: { value: tex.height }, uSplat: { value: tex.splat }, uLight: { value: tex.light }, tGrass: { value: tex.grass },
          uHF: { value: new THREE.Vector4(-world.size / 2, 1 / world.spacing, world.res, world.size) },
          uDist: { value: new THREE.Vector4(dense[0], dense[1], far[0], far[1]) },
          uFloorGrass: { value: floor }, uBladeH: { value: height }, uGrassTint: { value: new THREE.Vector3(...tint) },
        },
        defines: hay ? { HAY: 1 } : {},
        side: THREE.DoubleSide,
        vertexShader: /* glsl */`
          uniform sampler2D uHeight, uSplat, uLight, tGrass;
          uniform vec4 uHF, uDist;
          uniform float uTime, uFloorGrass, uBladeH;
          uniform vec3 uGrassTint;
          uniform vec3 uSunColor, uSkyColor, uSunDir;
          attribute vec4 blade;      // x, z in the tile, angle, random
          attribute vec2 tile;
          varying vec3 vCol, vWorld;
          float hAt(vec2 xz) {
            vec2 t = clamp((xz - uHF.x) * uHF.y, vec2(0.0), vec2(uHF.z - 1.001));
            ivec2 i = ivec2(floor(t)); vec2 f = t - vec2(i);
            float a = texelFetch(uHeight, i, 0).r, b = texelFetch(uHeight, i + ivec2(1, 0), 0).r;
            float c = texelFetch(uHeight, i + ivec2(0, 1), 0).r, d = texelFetch(uHeight, i + ivec2(1, 1), 0).r;
            return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
          }
          void main() {
            vec2 rootXZ = tile + blade.xy;
            vec3 root = vec3(rootXZ.x, hAt(rootXZ), rootXZ.y);
            vec2 mapUv = (rootXZ - uHF.x) / uHF.w;
            vec4 s = textureLod(uSplat, mapUv, 0.0);
            float d = distance(cameraPosition, root);
            float rnd = blade.w, rank = position.z;
            // density from the splat (grass, a little on the forest floor), thinned with distance
            float dens = clamp(s.r * 1.15 + s.g * uFloorGrass - 0.08, 0.0, 1.0);
            float keep = clamp((dens - rnd) * 5.0, 0.0, 1.0);    // blades at the density edge come in short
            float thin = rank < 0.3333 ? 1.0 : 1.0 - smoothstep(uDist.x, uDist.y, d);
            float fade = 1.0 - smoothstep(uDist.z, uDist.w, d);
            float h = (0.22 + 0.42 * fract(rnd * 13.7)) * (0.55 + 0.6 * s.r) * keep * thin * fade * uBladeH;
            float w = 0.04 * (1.0 + 0.9 * smoothstep(uDist.x - 4.0, uDist.y, d)) * (1.0 - position.y);
            #ifdef HAY
              // the hay meadow before the first cutting (0.6-0.9 m, patchy), softer and fuller: wider
              // blades that bow over; a quarter carry a seed head (orchard grass / timothy panicle) and a
              // few an ox-eye daisy, widened at the tip
              float patchH = 0.75 + 0.5 * fract(sin(dot(floor(rootXZ / 5.0), vec2(12.9898, 78.233))) * 43758.5453);
              float kind = fract(rnd * 31.7);
              float head = step(0.74, kind), daisy = step(0.993, kind);
              h = (0.28 + 0.62 * pow(fract(rnd * 13.7), 0.7)) * patchH * (0.45 + 0.6 * s.r) * keep * thin * fade * uBladeH;
              w = 0.055 * (1.0 + 0.9 * smoothstep(uDist.x - 4.0, uDist.y, d)) * mix(1.0 - 0.75 * position.y, 1.0, 0.0);
              if (position.y > 0.4) w *= mix(1.0, 1.9, head) * mix(1.0, 2.2, daisy);
            #endif
            // blades turn halfway toward the camera, so few are seen edge-on
            vec2 toCam = normalize(cameraPosition.xz - rootXZ + 1e-4);
            vec2 dir = normalize(mix(vec2(cos(blade.z), sin(blade.z)), vec2(-toCam.y, toCam.x), 0.5));
            float t = position.y;
            // wind: a travelling gust front plus per-blade flutter
            float gust = sin(dot(rootXZ, vec2(0.13, 0.05)) - uTime * 1.6) * 0.5 + 0.5;
            float sway = (0.25 + 0.75 * gust) * 0.35 + 0.08 * sin(uTime * 5.0 + rnd * 40.0);
            vec3 wp = root + vec3(dir.x, 0.0, dir.y) * w * position.x;
            wp.y += t * h * (1.0 - 0.25 * sway * t);
            wp.xz += vec2(0.93, 0.36) * sway * t * t * h;
            #ifdef HAY
              // (tall blades bow over under their own weight)
              wp.xz += vec2(cos(blade.z), sin(blade.z)) * t * t * h * 0.35 * fract(rnd * 3.3);
              wp.y -= t * t * h * 0.12;
            #endif
            vWorld = wp;
            // colour: the ground's grass colour at this spot (a high mip of the terrain's
            // texture, same tint as the terrain), darker at the root, drier at some tips
            vec3 g = textureLod(tGrass, rootXZ / 3.0, 7.0).rgb * uGrassTint * (0.82 + 0.36 * s.a);
            g *= mix(0.55, 1.18, t);
            g = mix(g, g * vec3(1.35, 1.15, 0.6), t * step(0.8, fract(rnd * 7.1)));
            #ifdef HAY
              // mid-June greens, from blue-green orchard grass to yellow-green timothy, per blade and patch
              vec3 g0 = vec3(0.045, 0.085, 0.028), g1 = vec3(0.085, 0.11, 0.032);
              g = mix(g0, g1, fract(rnd * 5.3)) * (0.85 + 0.3 * s.a) * mix(0.5, 1.12, t);
              // heads: straw and purple-brown panicles; daisies white
              vec3 hc = mix(vec3(0.2, 0.16, 0.08), vec3(0.14, 0.08, 0.09), step(0.5, fract(rnd * 71.0)));
              g = mix(g, hc, head * smoothstep(0.45, 0.7, t));
              g = mix(g, vec3(0.42, 0.42, 0.38), daisy * smoothstep(0.6, 0.85, t));
            #endif
            vec4 l = textureLod(uLight, mapUv, 0.0);
            vec3 v = normalize(wp - cameraPosition);
            float back = pow(max(dot(v, uSunDir), 0.0), 3.0) * t;      // sun through the blades
            vCol = g * (uSunColor * (l.r * l.g * (0.85 + 0.3 * t) + 0.35 * back * l.a * l.g) + uSkyColor * l.b);
            gl_Position = projectionMatrix * viewMatrix * vec4(wp, 1.0);
          }`,
        fragmentShader: /* glsl */`
          varying vec3 vCol, vWorld;
          ${ATMOSPHERE_PARS}
          void main() {
            gl_FragColor = vec4(applyAtmosphere(vCol, vWorld), 1.0);
            #include <tonemapping_fragment>
            #include <colorspace_fragment>
          }`,
      });
      const mesh = new THREE.Mesh(g, material);
      mesh.frustumCulled = false;
      mesh.name = `Wild_Grass_${name}`;
      this.tiers.push({ name, mesh, data, attr, count: 0, blades: Math.floor(B * frac) });
    }
    this.group = new THREE.Group();
    for (const t of this.tiers) this.group.add(t.mesh);
    // tiles with no grass at all (forest floor, rock, path) are never drawn: max density per
    // tile from the splat, as the shader computes it
    const M = world.mapRes, nt = Math.ceil(world.size / TILE), per = world.size / M;
    this.tileDensity = new Float32Array(nt * nt);
    for (let j = 0; j < M; j++) for (let i = 0; i < M; i++) {
      const k = (i + j * M) * 4, d = (world.splat[k] / 255) * 1.15 + (world.splat[k + 1] / 255) * floor - 0.08;
      const ti = Math.floor((i * per) / TILE), tj = Math.floor((j * per) / TILE), q = ti + tj * nt;
      if (d > this.tileDensity[q]) this.tileDensity[q] = d;
    }
    this.nt = nt;
    this._box = new THREE.Box3();
    this.stats = {};
  }

  // quality levels: the dense and outer ring radii (m); off = no grass
  setRange(dense, far, on = true) {
    this.dense = dense; this.far = far; this.on = on;
    for (const t of this.tiers) { t.mesh.material.uniforms.uDist.value.set(dense[0], dense[1], far[0], far[1]); t.mesh.visible = on; }
  }

  update(camera, frustum) {
    if (this.on === false) { for (const t of this.tiers) t.mesh.visible = false; this.stats = { denseTiles: 0, outerTiles: 0, blades: 0 }; return; }
    const c = camera.position, R = this.far[1], dense = this.dense[1];
    const i0 = Math.floor((c.x - R) / TILE), i1 = Math.floor((c.x + R) / TILE);
    const j0 = Math.floor((c.z - R) / TILE), j1 = Math.floor((c.z + R) / TILE);
    const [D, O] = this.tiers;
    D.count = 0; O.count = 0;
    const y = this.world.heightAt(c.x, c.z);
    for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
      const x0 = i * TILE, z0 = j * TILE;
      const dx = Math.max(x0 - c.x, 0, c.x - x0 - TILE), dz = Math.max(z0 - c.z, 0, c.z - z0 - TILE);
      const dmin = Math.hypot(dx, dz);
      if (dmin > R) continue;
      const ti = i + this.nt / 2, tj = j + this.nt / 2;
      if (ti < 0 || tj < 0 || ti >= this.nt || tj >= this.nt || this.tileDensity[ti + tj * this.nt] <= 0.02) continue;
      const hc = this.world.heightAt(x0 + TILE / 2, z0 + TILE / 2);
      this._box.min.set(x0, Math.min(hc, y) - 6, z0); this._box.max.set(x0 + TILE, Math.max(hc, y) + 6, z0 + TILE);
      if (!frustum.intersectsBox(this._box)) continue;
      const t = dmin < dense && this.tileDensity[ti + tj * this.nt] > 0.34 ? D : O;
      t.data[t.count * 2] = x0; t.data[t.count * 2 + 1] = z0; t.count++;
    }
    for (const t of this.tiers) {
      t.mesh.geometry.instanceCount = t.count;
      t.mesh.visible = t.count > 0;
      t.attr.clearUpdateRanges(); t.attr.addUpdateRange(0, t.count * 2); t.attr.needsUpdate = true;
    }
    this.stats = { denseTiles: D.count, outerTiles: O.count, blades: D.count * D.blades + O.count * O.blades };
  }
}
