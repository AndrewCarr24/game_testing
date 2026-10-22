import * as THREE from 'three';
import { ATMOSPHERE_PARS } from './atmosphere.js';

// CDLOD terrain (Strugar 2010): one 16x16-quad grid patch, instanced over the quadtree
// nodes selected for the camera each frame, displaced in the vertex shader from the height
// texture. Every level has a distance range twice the previous one's; near the far end of its
// range a node's odd vertices slide onto their even neighbours (geomorphing), so at a seam a
// fine node's vertices sit exactly on its coarse neighbour's: no cracks, no skirts, no
// popping. The whole terrain is ONE draw call, whatever the view.
//
// Lighting is baked (world.light): sun n.l x terrain shadow x tree shadow + sky visibility,
// times a splat blend of four tiling ground textures (height-blended so the transitions are
// crisp at 2 m mask resolution), then the shared fog / aerial perspective.

const PATCH_DEFAULT = 8;      // quads per patch side (a patch is a node quadrant)

export class Terrain {
  // Seams stay closed only while a node's far side is still short of the next level's morph start:
// range_i + node diagonal (3D) < range_i + morphStart * range_i. Leaf nodes of 16 m (8 quads per
// quadrant = 1 m) with range0 = 64 m leave room for ~2:1 height differences inside a node; 32 m
// leaves at the same range cracked on the synthetic mountains (viewer/tools/wild_cracks.mjs).
  // (a generated level: leaf 12 m, patch 4 for its 1536 m square at 1.5 m samples, so a leaf
  // node's quads are exactly the 1.5 m data cells; size / leaf must be a power of two and
  // leaf / spacing an integer)
  constructor(world, tex, uniforms, { leaf = 16, r0 = 64, morphStart = 0.6, patch = PATCH_DEFAULT, tints = null, tiles = null } = {}) {
    const PATCH = patch;
    this.patch = patch;
    this.world = world;
    const { size, res } = world;
    this.levels = Math.round(Math.log2(size / leaf)) + 1;
    this.leaf = leaf;
    this.ranges = [...Array(this.levels).keys()].map((i) => r0 * 2 ** i);
    this.ranges[this.levels - 1] = 1e9;   // the root covers everything
    const morph = this.ranges.map((r, i) => {
      // morphing completes 1% before the range ends (float32 distances in the shader graze it)
      const prev = i ? this.ranges[i - 1] : 0, end = i === this.levels - 1 ? this.ranges[i - 1] * 2 : r;
      return new THREE.Vector2(prev + (end - prev) * morphStart, end * 0.99);
    });

    // min/max height per node, finest first (leaf nodes cover leaf/spacing samples)
    this.minmax = [];
    const n0 = size / leaf, per = Math.round(leaf / world.spacing);
    let mm = new Float32Array(n0 * n0 * 2);
    for (let j = 0; j < n0; j++) for (let i = 0; i < n0; i++) {
      let lo = Infinity, hi = -Infinity;
      for (let b = 0; b <= per; b++) for (let a = 0; a <= per; a++) {
        const h = world.heights[(i * per + a) + (j * per + b) * res];
        if (h < lo) lo = h; if (h > hi) hi = h;
      }
      mm[(i + j * n0) * 2] = lo; mm[(i + j * n0) * 2 + 1] = hi;
    }
    this.minmax.push(mm);
    for (let n = n0 / 2; n >= 1; n /= 2) {
      const prev = mm, pn = n * 2; mm = new Float32Array(n * n * 2);
      for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) {
        let lo = Infinity, hi = -Infinity;
        for (const [a, b] of [[0, 0], [1, 0], [0, 1], [1, 1]]) {
          const q = ((2 * i + a) + (2 * j + b) * pn) * 2;
          lo = Math.min(lo, prev[q]); hi = Math.max(hi, prev[q + 1]);
        }
        mm[(i + j * n) * 2] = lo; mm[(i + j * n) * 2 + 1] = hi;
      }
      this.minmax.push(mm);
    }

    // patch geometry: (PATCH+1)^2 grid vertices, position.xz = integer grid coords
    const g = new THREE.InstancedBufferGeometry();
    const pos = new Float32Array((PATCH + 1) ** 2 * 3), idx = [];
    for (let j = 0; j <= PATCH; j++) for (let i = 0; i <= PATCH; i++) { const k = (i + j * (PATCH + 1)) * 3; pos[k] = i; pos[k + 2] = j; }
    for (let j = 0; j < PATCH; j++) for (let i = 0; i < PATCH; i++) {
      const a = i + j * (PATCH + 1), b = a + 1, c = a + PATCH + 1, d = c + 1;
      // alternate the diagonal so the grid has no directional bias
      if ((i + j) & 1) idx.push(a, c, b, b, c, d); else idx.push(a, c, d, a, d, b);
    }
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setIndex(idx);
    this.capacity = 4096;
    this.nodeData = new Float32Array(this.capacity * 4);
    this.nodeAttr = new THREE.InstancedBufferAttribute(this.nodeData, 4);
    this.nodeAttr.setUsage(THREE.DynamicDrawUsage);
    g.setAttribute('node', this.nodeAttr);
    g.instanceCount = 0;
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1e9);

    const material = new THREE.ShaderMaterial({
      uniforms: {
        ...uniforms,
        uHeight: { value: tex.height }, uSplat: { value: tex.splat }, uLight: { value: tex.light },
        tGrass: { value: tex.grass }, tFloor: { value: tex.floor }, tRock: { value: tex.rock }, tScree: { value: tex.scree },
        uTiles: { value: new THREE.Vector4(...(tiles || [3.0, 2.2, 7.0, 2.0])) },
        // a level: wet banks / spray (r) and cobble bars (g) from the water raster (main.js wetTexture)
        tWet: { value: tex.wet || null }, tBed: { value: tex.bed || tex.scree }, uBedTile: { value: tex.bedTile || 1.8 },
        uHasWet: { value: tex.wet ? 1 : 0 },
        // per-layer tints (grass, forest floor, rock, path): the prototype's by default
        uTint0: { value: new THREE.Vector3(...(tints?.[0] || [1.05, 1.0, 0.78])) },
        uTint1: { value: new THREE.Vector3(...(tints?.[1] || [0.95, 0.72, 0.5])) },
        uTint2: { value: new THREE.Vector3(...(tints?.[2] || [0.78, 0.74, 0.68])) },
        uTint3: { value: new THREE.Vector3(...(tints?.[3] || [0.62, 0.5, 0.38])) },
        uMorph: { value: morph },
        uCanopy: { value: new THREE.Vector2(2300, 2600) },
        // the canopy shell (a level): forested ground between the far impostors takes the
        // sunlit canopy's colour from ~150 m, so from a lookout the forest below closes into a
        // green sea instead of showing the dark floor between the crowns; (0, 0) = off
        uShell: { value: new THREE.Vector3(0, 0, 0) },
        uHF: { value: new THREE.Vector4(-size / 2, 1 / world.spacing, res, size) },
      },
      vertexShader: /* glsl */`
        uniform sampler2D uHeight;
        uniform vec4 uHF;              // origin, 1/spacing, res, size
        uniform vec2 uMorph[${this.levels}];
        attribute vec4 node;           // x0, z0, patch size (m), level
        varying vec3 vWorld;
        varying vec2 vMap;
        float hAt(vec2 xz) {
          vec2 t = clamp((xz - uHF.x) * uHF.y, vec2(0.0), vec2(uHF.z - 1.001));
          ivec2 i = ivec2(floor(t)); vec2 f = t - vec2(i);
          float a = texelFetch(uHeight, i, 0).r, b = texelFetch(uHeight, i + ivec2(1, 0), 0).r;
          float c = texelFetch(uHeight, i + ivec2(0, 1), 0).r, d = texelFetch(uHeight, i + ivec2(1, 1), 0).r;
          return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
        }
        void main() {
          float step = node.z / ${PATCH}.0;
          vec2 xz = node.xy + position.xz * step;
          float d = distance(cameraPosition, vec3(xz.x, hAt(xz), xz.y));
          vec2 m = uMorph[int(node.w + 0.5)];
          float k = clamp((d - m.x) / (m.y - m.x), 0.0, 1.0);
          xz -= fract(position.xz * 0.5) * 2.0 * step * k;
          vWorld = vec3(xz.x, hAt(xz), xz.y);
          vMap = (xz - uHF.x) / uHF.w;
          gl_Position = projectionMatrix * viewMatrix * vec4(vWorld, 1.0);
        }`,
      fragmentShader: /* glsl */`
        uniform sampler2D uSplat, uLight, tGrass, tFloor, tRock, tScree, tWet, tBed;
        uniform vec4 uTiles;
        uniform float uBedTile, uHasWet;
        uniform vec2 uCanopy;
        uniform vec3 uShell;
        uniform vec3 uTint0, uTint1, uTint2, uTint3;
        uniform vec3 uSunColor, uSkyColor;
        varying vec3 vWorld;
        varying vec2 vMap;
        ${ATMOSPHERE_PARS}
        void main() {
          vec4 s = texture2D(uSplat, vMap);
          vec2 p = vWorld.xz;
          vec3 g = texture2D(tGrass, p / uTiles.x).rgb;
          vec3 f = texture2D(tFloor, p / uTiles.y).rgb;
          vec3 c = texture2D(tScree, p / uTiles.w).rgb;
          vec3 r = vec3(0.0);
          #ifdef LOW
          r = texture2D(tRock, p / uTiles.z).rgb;
          #else
          if (s.b > 0.02) {
            // rock: biplanar on steep faces (top-down UVs smear on cliffs)
            vec3 n = normalize(cross(dFdx(vWorld), dFdy(vWorld)));
            vec3 w = pow(abs(n), vec3(4.0)); w /= w.x + w.y + w.z;
            r = texture2D(tRock, vWorld.zy / uTiles.z).rgb * w.x + texture2D(tRock, p / uTiles.z).rgb * w.y
              + texture2D(tRock, vWorld.xy / uTiles.z).rgb * w.z;
          }
          #endif
          // height blend: each layer's brightness is its height, so grass pokes through scree
          // and rock shows in cracks instead of a 2 m smear
          vec4 wt = vec4(s.r, s.g, s.b, max(0.0, 1.0 - s.r - s.g - s.b));
          #ifndef LOW
          vec4 h = wt + 0.35 * vec4(dot(g, vec3(1.0)), dot(f, vec3(1.0)), dot(r, vec3(0.8)), dot(c, vec3(0.6)));
          float top = max(max(h.x, h.y), max(h.z, h.w)) - 0.18;
          wt = max(h - top, 0.0); wt /= wt.x + wt.y + wt.z + wt.w;
          #endif
          vec4 l = texture2D(uLight, vMap), l0 = l;
          // (the scans desaturated first: their hue is the place they were shot; the tint is ours)
          #define DESAT(x, k) mix(vec3(dot(x, vec3(0.3, 0.5, 0.2))), x, k)
          vec3 gC = DESAT(g, 0.8) * uTint0, fC = DESAT(f, 0.65) * uTint1, rC = DESAT(r, 0.25) * uTint2, cC = DESAT(c, 0.6) * uTint3;
          vec2 wb = uHasWet > 0.5 ? texture2D(tWet, vMap).rg : vec2(0.0);
          if (uHasWet > 0.5) {
            // under the canopy the grass layer is moss (#4F7A2A): the litter's own grain, moss-green
            vec3 moss = vec3(0.05, 0.11, 0.018) * (0.55 + 0.9 * dot(f, vec3(0.6)));
            float shade = smoothstep(0.6, 0.28, l.b);
            gC = mix(gC, moss, shade);
            fC = mix(fC, moss, 0.22 * shade * smoothstep(0.45, 0.75, s.a));     // moss patches in the litter
            #ifndef LOW
            if (s.b > 0.02) {                                                     // moss on shaded rock tops
              vec3 nr = normalize(cross(dFdx(vWorld), dFdy(vWorld)));
              rC = mix(rC, moss * 1.1, smoothstep(0.55, 0.9, nr.y) * shade * 0.7);
            }
            #endif
            // cobble bars beside the river: the bed's gold-brown cobbles on the path layer
            if (wb.g > 0.02) cC = mix(cC, texture2D(tBed, p / uBedTile).rgb * vec3(0.95, 0.88, 0.75), wb.g);
          }
          vec3 albedo = gC * wt.x + fC * wt.y + rC * wt.z + cC * wt.w;
          albedo *= 0.82 + 0.36 * s.a;
          albedo *= 1.0 - 0.42 * wb.r;                     // wet: banks, the falls' spray zone and face
          // beyond the last tree impostors (quality levels cut them off early) forested ground
          // turns into canopy: the forest stays on the hills without drawing it
          float dc = distance(cameraPosition, vWorld);
          float cm = smoothstep(uCanopy.x, uCanopy.y, dc) * smoothstep(0.2, 0.7, s.g);
          // (the shell only shows under a closed canopy: where the light map's tree shadow is deep)
          float sh = uShell.z * smoothstep(uShell.x, uShell.y, dc) * smoothstep(0.2, 0.7, s.g) * smoothstep(0.85, 0.35, l0.g);
          cm = max(cm, sh);
          vec3 canopyCol = vec3(0.035, 0.058, 0.02) * (0.8 + 0.45 * s.a);
          albedo = mix(albedo, canopyCol, cm);
          vec3 col = albedo * (uSunColor * l.r * mix(l.g, 1.0, cm) + uSkyColor * l.b);
          gl_FragColor = vec4(applyAtmosphere(col, vWorld), 1.0);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }`,
    });
    this.mesh = new THREE.Mesh(g, material);
    this.mesh.frustumCulled = false;
    this.mesh.name = 'Wild_Terrain';
    this._box = new THREE.Box3();
    this.stats = { patches: 0, byLevel: [] };
  }

  // low quality: top-down rock, no height blend (fewer texture reads per pixel)
  setLow(low) {
    const m = this.mesh.material;
    if (!!m.defines.LOW === low) return;
    if (low) m.defines.LOW = 1; else delete m.defines.LOW;
    m.needsUpdate = true;
  }

  // select quadtree nodes for this camera; fills the instance buffer
  update(camera, frustum) {
    this.count = 0;
    this.stats.byLevel = new Array(this.levels).fill(0);
    this._cam = camera.position;
    this._frustum = frustum;
    this.select(0, 0, this.levels - 1);
    this.mesh.geometry.instanceCount = this.count;
    this.nodeAttr.clearUpdateRanges();
    this.nodeAttr.addUpdateRange(0, this.count * 4);
    this.nodeAttr.needsUpdate = true;
    this.stats.patches = this.count;
  }

  nodeBox(i, j, level) {
    const n = this.world.size / (this.leaf * 2 ** level), mm = this.minmax[level];
    const s = this.leaf * 2 ** level, o = -this.world.size / 2;
    this._box.min.set(o + i * s, mm[(i + j * n) * 2], o + j * s);
    this._box.max.set(o + (i + 1) * s, mm[(i + j * n) * 2 + 1], o + (j + 1) * s);
    return this._box;
  }

  inRange(i, j, level, range) {
    return this.nodeBox(i, j, level).distanceToPoint(this._cam) <= range;
  }

  // returns false when the node is outside its level's range (the parent then draws the area)
  select(i, j, level) {
    if (!this.inRange(i, j, level, this.ranges[level])) return false;
    if (!this._frustum.intersectsBox(this.nodeBox(i, j, level))) return true;
    if (level === 0 || !this.inRange(i, j, level, this.ranges[level - 1])) { this.add(i, j, level, 15); return true; }
    let mask = 0;
    for (let q = 0; q < 4; q++) if (!this.select(2 * i + (q & 1), 2 * j + (q >> 1), level - 1)) mask |= 1 << q;
    if (mask) this.add(i, j, level, mask);
    return true;
  }

  add(i, j, level, mask) {
    const s = this.leaf * 2 ** level, o = -this.world.size / 2, hs = s / 2;
    for (let q = 0; q < 4; q++) {
      if (!(mask & (1 << q)) || this.count >= this.capacity) continue;
      const x0 = o + i * s + (q & 1) * hs, z0 = o + j * s + (q >> 1) * hs;
      // quadrant-level frustum test (cheap, halves the far patches); the node's height range
      this.nodeBox(i, j, level);
      this._box.min.x = x0; this._box.min.z = z0; this._box.max.x = x0 + hs; this._box.max.z = z0 + hs;
      if (!this._frustum.intersectsBox(this._box)) continue;
      const k = this.count++ * 4;
      this.nodeData[k] = x0; this.nodeData[k + 1] = z0; this.nodeData[k + 2] = hs; this.nodeData[k + 3] = level;
      this.stats.byLevel[level]++;
    }
  }
}
