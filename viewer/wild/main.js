import * as THREE from 'three';
import { PointerLockControls } from 'three/addons/controls/PointerLockControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { loadSky } from '../sky.js';
import { KEYS } from '../player.js';
import { generateWorld } from './world.js';
import { loadWorld } from './load_world.js';
import { atmosphereUniforms, lightUniforms } from './atmosphere.js';
import { Terrain } from './terrain.js';
import { Forest, TIERS, TIERS_VEG, meanColor } from './trees.js';
import { Grass } from './grass.js';
import { loadVegKit } from './veg.js';
import { HeightfieldPlayer } from './player_hf.js';
import { makeWildSky } from './sky_wild.js';
import { buildBackdrop, buildWater, Props, buildEstate, estateColliders } from './level.js';
import { Town, Exits } from './town.js';   // [town] Sourwood (world=laurel_town) + the exits between worlds

// Wilderness runtime spike (viewer/wild_proto.html). URL options:
//   view=open|forest|ridge|spawn   start view (default spawn); pos=x,y,z&look=x,y,z overrides
//   trees=N (40000) bushes=N (120000) blades=N per 8 m grass tile (4500) seed=N
//   res=2049 (height samples per side, 1 m) map=1024 (splat/light texels per side)
//   grass=0 trees=0 under=0 terrain=0   switch systems off (A/B costs)
//   near=42 mid=150 (tree LOD distances, m)  fogd=0.0007 (fog density)  t=N (freeze time at N s)
//   veg=1 production-weight trees from the vegetation spike (build/wilderness/veg: ash for
//   broadleaf, fir for conifer and pine; LOD0-2 + baked impostor, bark + leaf draw calls)
//   q=3|2|1|0 fix the quality level (default: 3, or 0 on a software renderer; the governor
//   steps it down while < 50 fps over 2 s windows); aa=0|1 force MSAA off/on
//   fly=1 start in fly mode; hud=0 hide the overlay; aa=0 no MSAA; pr=N pixel-ratio cap (1.5)
//   world=<name> a generated level from build/wilderness/<name>/world/ (load_world.js), e.g.
//   world=laurel_fork: its terrain, forest (the vegetation agent's species where veg.json has
//   them, stand-ins otherwise; veg=0 stand-ins only), water, props, colliders, the estate seen from
//   outside, haze and sky; starts at its spawn (the gate). view=<name> any of its world.json views
//   (gate, meadow_edge, poplar_cove, falls, footlog, laurel_hell, raven, knob, painted, gap, and the
//   bench's open / forest / ridge / spawn; the river: bridge cascade river_gorge river_road); epos=x,y[,z]&elook=x,y,z
//   in the estate frame. A level's kit options: variants=N (q3 default 2: poplar, hemlock, red oak), vegtex=1024,
//   kitprops=0 (stand-in logs and rocks), split=1 (opaque + leaf draws for every tree LOD), shell=0 (no canopy
//   shell on far forested ground), ground=0 (the house's ground textures, not the Poly Haven scans),
//   shrubs=0 / canopy=0 (A/B costs)
// Keys: click to look; WASD, Shift run, Space jump, C crouch; F fly (Space/C up/down, Shift fast);
// 1-4 jump to the open / forest / ridge / spawn views; H overlay.

const params = new URLSearchParams(location.search);
const num = (k, d) => (params.has(k) ? +params.get(k) : d);
const on = (k) => params.get(k) !== '0';
const hud = document.getElementById('hud');
const status = (s) => { hud.textContent = s; };

// sky look: viewer/sky.js's dome + mansion.json's "golden" look (sun, sky light, haze)
const LOOK = { haze: [0.82, 0.7, 0.6], light: [0.42, 0.52, 0.72], light_strength: 0.85, sun_strength: 6.0, sun_color: [1.0, 0.7, 0.45] };

// software rendering (SwiftShader, llvmpipe): MSAA alone costs it ~1/3 of the frame and can only
// be chosen when the context is made, so look at the GPU first (a throwaway context)
const softwareGPU = (() => {
  const gl = document.createElement('canvas').getContext('webgl2');
  const dbg = gl?.getExtension('WEBGL_debug_renderer_info');
  const name = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : '';
  gl?.getExtension('WEBGL_lose_context')?.loseContext();
  return /swiftshader|llvmpipe|software/i.test(name);
})();
const renderer = new THREE.WebGLRenderer({ antialias: params.has('aa') ? params.get('aa') !== '0' : !softwareGPU, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, num('pr', 1.5)));     // as the game: cap at 1.5x
renderer.setSize(innerWidth, innerHeight);
// the game's tone mapping (index.html: Khronos PBR Neutral in the custom slot), exposure as baked
THREE.ShaderChunk.tonemapping_pars_fragment = THREE.ShaderChunk.tonemapping_pars_fragment.replace(
  'vec3 CustomToneMapping( vec3 color ) { return color; }', `vec3 CustomToneMapping( vec3 color ) {
    const float StartCompression = 0.8 - 0.04;
    const float Desaturation = 0.15;
    color *= toneMappingExposure;
    float x = min( color.r, min( color.g, color.b ) );
    float offset = x < 0.08 ? x - 6.25 * x * x : 0.04;
    color -= offset;
    float peak = max( color.r, max( color.g, color.b ) );
    if ( peak < StartCompression ) return color;
    float d = 1.0 - StartCompression;
    float newPeak = 1.0 - d * d / ( peak + d - StartCompression );
    color *= newPeak / peak;
    float g = 1.0 - 1.0 / ( Desaturation * ( peak - newPeak ) + 1.0 );
    return mix( color, vec3( newPeak ), g );
  }`);
renderer.toneMapping = THREE.CustomToneMapping;
renderer.toneMappingExposure = 0.95;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(70, innerWidth / innerHeight, 0.2, 3200);
window.__three = { renderer, scene, camera };

async function main() {
  const T = {};
  let t0 = performance.now();
  const worldName = params.get('world') || window.WILD_WORLD || null;
  status(worldName ? `loading ${worldName}...` : 'generating terrain...');
  await new Promise((r) => setTimeout(r, 0));
  const world = worldName ? await loadWorld(worldName)
    : generateWorld({ res: num('res', 2049), mapRes: num('map', 1024), seed: num('seed', 7),
      trees: on('trees') ? num('trees', 40000) : 0, bushes: on('under') ? num('bushes', 120000) : 0 });
  const level = !!world.speciesInfo;
  if (level) {                       // switches: trees=0 (no trees / shrubs), under=0 (no ground cover)
    for (const [id, info] of Object.entries(world.speciesInfo)) {
      if ((!on('trees') && info.tier !== 'under') || (!on('under') && info.tier === 'under') || (!on('shrubs') && info.tier === 'shrub')
        || (!on('canopy') && info.tier === 'tree')) world.species[id] = new Float32Array(0);
    }
  }
  T.world = Math.round(performance.now() - t0); t0 = performance.now();

  const loader = new THREE.TextureLoader();
  const aniso = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  const img = async (f, repeat = true) => {
    const t = await loader.loadAsync(f.includes('/') ? f : `../assets/textures/${f}`);
    t.colorSpace = THREE.SRGBColorSpace;
    if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = aniso; }
    t.name = f.split('/').pop();
    return t;
  };
  // the vegetation kit (viewer/wild/veg.js): only what the level places; variants only where the
  // quality may use them (q3); anything missing falls back to its stand-in
  const q0 = params.has('q') ? num('q', 3) : softwareGPU ? 0 : 3;
  let vegModels = null, kitProps = null;
  if (level && params.get('veg') !== '0') {
    const kit = await loadVegKit({ world, maxTex: num('vegtex', 1024), maxVariants: num('variants', q0 >= 3 ? 2 : 1), aniso: Math.min(4, aniso) });
    vegModels = kit.models;
    kitProps = params.get('kitprops') === '0' ? null : kit.props;
  }
  const needStand = !level || Object.entries(world.speciesInfo).some(([id, info]) => world.species[id]?.length && !vegModels?.[id]);
  const none = Promise.resolve(null);
  // a level's ground: Poly Haven scans (blender/wilderness/ground_textures.py, ground.json), else the
  // prototype's house textures
  let ground = null;
  if (level && params.get('ground') !== '0') {
    try { ground = await (await fetch('../build/wilderness/ground/ground.json')).json(); } catch { ground = null; }
  }
  const gtex = (k, f) => (ground?.[k] ? img(`../build/wilderness/ground/${ground[k].file}`) : img(f));
  const [grass, floor, rock, scree, leaves, bark, foliage, sky, bed] = await Promise.all([
    gtex('grass', 'T_Grounds_Grass_BaseColor.png'), gtex('litter', 'T_Grounds_Hedge_BaseColor.png'), gtex('rock', 'T_Garage_Concrete_BaseColor.png'),
    gtex('path', 'T_Out_Gravel_BaseColor.png'), needStand ? img('T_EntryTree_Leaves_BaseColor.png', false) : none,
    needStand ? img('T_EntryTree_Bark_BaseColor.png', false) : none,
    needStand ? img('T_Courtyard_Foliage_BaseColor.png', false) : none, loadSky('../assets/levels/mansion_sky.json', renderer),
    ground?.bed ? img(`../build/wilderness/ground/${ground.bed.file}`) : none]);
  T.textures = Math.round(performance.now() - t0); t0 = performance.now();

  const height = new THREE.DataTexture(world.heights, world.res, world.res, THREE.RedFormat, THREE.FloatType);
  height.minFilter = height.magFilter = THREE.NearestFilter; height.needsUpdate = true;
  const map = (data) => {
    const t = new THREE.DataTexture(data, world.mapRes, world.mapRes, THREE.RGBAFormat);
    t.generateMipmaps = true; t.minFilter = THREE.LinearMipmapLinearFilter; t.magFilter = THREE.LinearFilter;
    t.anisotropy = aniso; t.needsUpdate = true;
    return t;
  };
  let lightTex;
  if (world.lightImage) {               // (a level's WebP light map: straight to the GPU, as the PNG would be)
    lightTex = new THREE.Texture(world.lightImage);
    lightTex.flipY = false; lightTex.premultiplyAlpha = false; lightTex.colorSpace = THREE.NoColorSpace;
    lightTex.generateMipmaps = true; lightTex.minFilter = THREE.LinearMipmapLinearFilter; lightTex.magFilter = THREE.LinearFilter;
    lightTex.anisotropy = aniso; lightTex.needsUpdate = true;
  } else lightTex = map(world.light);
  const tex = { height, splat: map(world.splat), light: lightTex, grass, floor, rock, scree, leaves, bark, foliage, bed: bed || scree,
    bedTile: ground?.bed?.tile_m || 1.8, wet: level ? wetTexture(world) : null };

  sky.meta.haze = LOOK.haze;
  const uniforms = { ...atmosphereUniforms(sky), ...lightUniforms(LOOK), uBounce: { value: new THREE.Color(0.13, 0.14, 0.105) } };
  uniforms.uFogDensity.value = num('fogd', 0.0007);
  if (level) {
    // the brief's haze: aerial perspective at a 32 km visual range, no fog; the wild sky (the
    // house's golden-hour colours, layered ridges instead of the house's horizon band)
    // (THREE.Color parses '#rrggbb' as sRGB into the linear working space already)
    const hex = (h) => new THREE.Color(h);
    uniforms.uHazeMode.value = 1;
    uniforms.uExt.value = world.haze?.extinction ?? 3.912 / 32000;
    if (world.haze?.away) uniforms.uHazeAway.value.copy(hex(world.haze.away));
    if (world.haze?.sun) uniforms.uHazeSun.value.copy(hex(world.haze.sun));
    uniforms.uBloom = { value: [new THREE.Color(1, 1, 1), ...[1, 2, 3, 4].map((k) => new THREE.Color(...(world.meta.bloom?.[k] || [1, 1, 1])).convertSRGBToLinear())] };
    world.skyMeta = sky.meta;
    const wild = makeWildSky(sky.meta, uniforms);
    scene.add(wild.dome);
  } else scene.add(sky.dome);

  // (a level: 12 m leaves of 4 x 4 quads = its 1.5 m cells; Appalachian ground tints: leaf litter
  // #4A3A28, moss on the grass layer, grey gneiss, trail dirt)
  // (a level: the brief's palette (Appendix A, linear) over each scan's own mean colour, so the
  // scans bring their detail and the level keeps its colours)
  const PALETTE = { grass: [0.07, 0.095, 0.032], litter: [0.11, 0.072, 0.038], rock: [0.19, 0.19, 0.175], path: [0.105, 0.075, 0.045] };
  // (relative to the scan's mean after the terrain shader's desaturation: DESAT in terrain.js)
  const SAT = { grass: 0.8, litter: 0.65, rock: 0.25, path: 0.6 };
  const tintOf = (t, k) => {
    const m0 = meanColor(t), lum = m0[0] * 0.3 + m0[1] * 0.5 + m0[2] * 0.2, m = m0.map((v) => lum + (v - lum) * SAT[k]);
    return PALETTE[k].map((v, i) => Math.min(3, Math.max(0.3, v / Math.max(m[i], 1e-3))));
  };
  const terrain = level
    ? new Terrain(world, tex, uniforms, { leaf: 12, r0: 64, patch: 4,
      tints: ground ? [tintOf(grass, 'grass'), tintOf(floor, 'litter'), tintOf(rock, 'rock'), tintOf(scree, 'path')]
        : [[1.0, 1.0, 0.6], [0.82, 0.66, 0.5], [0.9, 0.88, 0.84], [0.5, 0.39, 0.28]],
      tiles: ground ? [ground.grass.tile_m, ground.litter.tile_m, ground.rock.tile_m, ground.path.tile_m] : null })
    : new Terrain(world, tex, uniforms);
  if (on('terrain')) scene.add(terrain.mesh);
  if (level && params.get('shell') !== '0') terrain.mesh.material.uniforms.uShell.value.set(140, 420, 0.85);
  let veg = null;
  if (!level && params.get('veg') === '1') {
    const gl = new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath('https://unpkg.com/three@0.160.0/examples/jsm/libs/draco/gltf/'));
    const load = async (name) => {
      const g = await gl.loadAsync(`../build/wilderness/veg/${name}.gltf`);
      const lods = [0, 1, 2].map((i) => {
        const node = g.scene.getObjectByName(`Veg_${name[0].toUpperCase() + name.slice(1)}_LOD${i}`);
        const parts = [];
        node.traverse((o) => {
          if (!o.isMesh) return;
          const geo = o.geometry, c = geo.attributes.color, ao = new Float32Array(geo.attributes.position.count).fill(1);
          if (c) for (let k = 0; k < ao.length; k++) ao[k] = c.getX(k);
          geo.setAttribute('ao', new THREE.BufferAttribute(ao, 1));
          const map = o.material.map;
          parts.push({ geo, map });
        });
        return parts;
      });
      return { name, lods };
    };
    const [ash, fir] = await Promise.all([load('ash'), load('fir')]);
    veg = { broadleaf: ash, conifer: fir, pine: fir };
  }
  const tiers = { ...TIERS, ...(veg ? TIERS_VEG : {}) };
  if (params.has('near')) { const n = num('near', 42); tiers.near = [0, 0, n, n + 14]; tiers.mid = [n, n + 14, tiers.mid[2], tiers.mid[3]]; }
  if (params.has('mid')) { const m = num('mid', 150); tiers.mid = [tiers.mid[0], tiers.mid[1], m, m + 25]; tiers.far = [m, m + 25, 2600, 2700]; }
  const forest = new Forest(world, renderer, uniforms, tex, { tiers, veg, vegModels, split: params.has('split') ? params.get('split') === '1' : false });
  scene.add(forest.group);
  const grassSys = new Grass(world, tex, uniforms, { blades: num('blades', 4500), ...(level ? { floor: 0.05, height: 1.15, tint: [1.2, 1.05, 0.5], hay: true, blades: num('blades', 6500) } : {}),
    ...(world.meta?.grass || {}) });   // [town] a level's own grass (the town's mown lawns)
  if (on('grass')) scene.add(grassSys.group);
  // a level's own meshes
  let props = null, town = null;
  if (level) {
    scene.add(buildBackdrop(world, uniforms));
    scene.add(buildWater(world, uniforms, tex));
    props = new Props(world, uniforms, tex, kitProps);
    scene.add(props.group);
    if (world.estate) scene.add(buildEstate(world, uniforms, tex));   // [town] (the town has no estate stand-in)
    // [town] the town's buildings, streets, bridges (viewer/wild/town.js)
    if (world.meta.town?.buildings && params.get('town') !== '0') { town = new Town(world, uniforms, tex); scene.add(town.group); }
  }
  T.build = Math.round(performance.now() - t0); t0 = performance.now();

  // ---- quality levels (3 = as built). Lower levels shorten the near tiers (more impostors),
  // shrink then drop the grass, pull in the undergrowth, cap the pixel ratio at 1 and use the
  // cheap terrain shader. Runtime switches only: no reload, one shader recompile (terrain).
  const L = (near, mid, under, end) => ({
    near: [0, 0, near, near * 1.3], mid: [near, near * 1.3, mid, mid * 1.17], far: [mid, mid * 1.17, end * 0.85, end],
    lod0: [0, 0, near * 0.47, near * 0.62], lod1: [near * 0.47, near * 0.62, near * 1.07, near * 1.3],
    lod2: [near * 1.07, near * 1.3, mid * 0.7, mid * 0.82], under: [0, 0, under, under * 1.28],
    vfar: [mid * 0.7, mid * 0.82, end * 0.85, end],
    // shrubs (stand-ins / models) and ground-cover models scale with the trees' near range
    snear: [0, 0, near * 0.38, near * 0.52], smid: [near * 0.38, near * 0.52, mid * 0.4, mid * 0.5], sfar: [mid * 0.4, mid * 0.5, end * 0.2, end * 0.22],
    slod0: [0, 0, near * 0.29, near * 0.36], slod1: [near * 0.29, near * 0.36, near * 0.76, near * 0.9], slod2: [near * 0.76, near * 0.9, mid * 0.47, mid * 0.57],
    simp: [near * 0.76, near * 0.9, end * 0.2, end * 0.22], tlod2: [near * 0.76, near * 0.9, mid * 1.0, mid * 1.1],
    ulod0: [0, 0, under * 0.19, under * 0.23], ulod1: [under * 0.19, under * 0.23, under * 0.83, under],
    timp: [near * 1.07, near * 1.3, end * 0.55, end * 0.6], snag: [0, 0, mid * 1.0, mid * 1.1], ucover: [0, 0, under * 0.83, under],
    ulod2: [under * 0.42, under * 0.5, under * 0.83, under]});
  const built = { ...tiers };
  const LEVELS = [
    { tiers: L(18, 70, 20, 500), grass: null, pr: 1, low: true },
    { tiers: L(26, 100, 30, 900), grass: [[5, 8], [15, 20]], pr: 1, low: true },
    { tiers: L(34, 130, 40, 1500), grass: [[7, 12], [24, 30]], pr: 1.5, low: false },
    { tiers: { ...built, end: 2700 }, grass: [[9, 15], [30, 38]], pr: 1.5, low: false },
  ];
  const quality = {
    level: 3,
    setLevel(q) {
      q = Math.max(0, Math.min(3, q));
      this.level = q;
      const Q = LEVELS[q];
      const t = Q.tiers;
      forest.setTiers(q === 3 ? { ...forest.tiers, ...built } : level ? t
        : veg ? { lod0: t.lod0, lod1: t.lod1, lod2: t.lod2, far: [t.lod2[2], t.lod2[3], t.far[2], t.far[3]], under: t.under }
        : { near: t.near, mid: t.mid, far: t.far, under: t.under }, q >= 3 ? num('variants', 2) : 1);
      if (Q.grass) grassSys.setRange(Q.grass[0], Q.grass[1], on('grass')); else grassSys.setRange([0, 0], [0, 0], false);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, Math.min(Q.pr, num('pr', 1.5))));
      terrain.setLow(Q.low);
      forest.setLow(Q.low);
      const end = q === 3 ? 2700 : t.far[3];
      terrain.mesh.material.uniforms.uCanopy.value.set(end * 0.8, end * 0.97);
    },
  };
  quality.setLevel(q0);
  // the house's governor (viewer/fx.js), inlined so the page doesn't load the post-processing
  // passes: one level down per 2 s window under 50 fps, from 4 s after the load, never back up;
  // off under benchmarks and while paused
  const govern = params.has('q') ? () => {} : (() => {
    let start = 0, frames = 0;
    const begin = performance.now() + 4000;
    return (now) => {
      if (quality.level <= 0 || window.__bench || now < begin) return;
      if (!start || now - start > 4000) { start = now; frames = 0; return; }    // (a pause: start over)
      frames++;
      if (now - start < 2000) return;
      const ms = (now - start) / frames;
      start = now; frames = 0;
      if (ms > 20) { quality.setLevel(quality.level - 1); console.log(`quality: ${ms.toFixed(1)} ms/frame -> q${quality.level}`); }
    };
  })();

  // ---- player: viewer/player.js on the heightfield, trunks as fixed box colliders
  let colliders;
  if (level) {
    // trunks, logs, boulders and props from the world (colliders.bin), the estate's hedge and house
    colliders = [];
    const C = world.colliders;
    for (let k = 0; k < C.length; k += 6) {
      const b = new THREE.Box3(new THREE.Vector3(C[k], C[k + 1], C[k + 2]), new THREE.Vector3(C[k + 3], C[k + 4], C[k + 5]));
      b.fixed = true;
      colliders.push(b);
    }
    if (world.estate) colliders.push(...estateColliders(world));   // [town]
  } else colliders = forest.colliders();
  const estateView = () => {
    if (!params.has('epos')) return null;
    const p = params.get('epos').split(',').map(Number), l = (params.get('elook') || '').split(',').map(Number);
    // [town] the estate frame through the world's own offset (the town's square is centred at estate x -1500)
    const [ox, oy] = world.meta?.estate_offset || [0, -810];
    const px = p[0] - ox, pz = -(p[1] - oy);
    const pos = [px, p.length > 2 ? p[2] : world.heightAt(px, pz) + 1.65, pz];
    return { pos, look: l.length >= 2 ? [l[0] - ox, l.length > 2 ? l[2] : pos[1], -(l[1] - oy)] : [pos[0], pos[1], pos[2] + 10] };
  };
  const startView = () => {
    if (params.has('pos')) {
      const p = params.get('pos').split(',').map(Number), l = (params.get('look') || '').split(',').map(Number);
      return { pos: p, look: l.length === 3 ? l : [p[0], p[1], p[2] - 10] };
    }
    return estateView() || world.views[params.get('view') || 'spawn'] || world.views.spawn;
  };
  const v0 = startView();
  const player = new HeightfieldPlayer(camera, colliders, [v0.pos[0], world.heightAt(v0.pos[0], v0.pos[2]), v0.pos[2]], world,
    level ? { maxSlopeDeg: 40 } : {});
  camera.position.set(...v0.pos);
  camera.lookAt(...v0.look);
  let fly = params.get('fly') === '1' || (params.has('pos') && Math.abs(v0.pos[1] - world.heightAt(v0.pos[0], v0.pos[2]) - 1.65) > 0.5);
  window.__player = player;
  const exits = level && params.get('exits') !== '0' ? new Exits(world, worldName) : null;   // [town]

  const setView = (name) => {
    const v = typeof name === 'string' ? world.views[name] : name;
    if (!v) return false;
    player.pos.set(v.pos[0], world.heightAt(v.pos[0], v.pos[2]), v.pos[2]); player.vel.set(0, 0, 0);
    camera.position.set(...v.pos); camera.lookAt(...v.look);
    return true;
  };

  const controls = new PointerLockControls(camera, document.body);
  renderer.domElement.addEventListener('click', () => controls.lock());
  const held = new Set();
  addEventListener('keydown', (e) => {
    held.add(e.code);
    if (e.code === 'KeyF') { fly = !fly; if (!fly) { player.pos.set(camera.position.x, Math.max(camera.position.y - 1.65, world.heightAt(camera.position.x, camera.position.z)), camera.position.z); player.vel.set(0, 0, 0); } }
    if (e.code === 'KeyH') overlay.style.display = overlay.style.display === 'none' ? '' : 'none';
    const views = world.meta?.keys || (level ? { Digit1: 'gate', Digit2: 'meadow_edge', Digit3: 'poplar_cove', Digit4: 'falls', Digit5: 'footlog',
      Digit6: 'laurel_hell', Digit7: 'raven', Digit8: 'knob', Digit9: 'painted', Digit0: 'gap' }
      : { Digit1: 'open', Digit2: 'forest', Digit3: 'ridge', Digit4: 'spawn' });   // [town] world.json keys
    if (views[e.code]) setView(views[e.code]);
  });
  addEventListener('keyup', (e) => held.delete(e.code));
  const input = () => Object.fromEntries(Object.entries(KEYS).map(([k, codes]) => [k, codes.some((c) => held.has(c))]));

  // ---- debug overlay
  const overlay = document.getElementById('overlay');
  if (params.get('hud') === '0') { overlay.style.display = 'none'; hud.style.display = 'none'; }
  const frustum = new THREE.Frustum(), pv = new THREE.Matrix4();
  const clock = new THREE.Clock();
  let acc = 0, frames = 0, lastHud = 0, fps = 0, frameMs = 0;
  const frozen = params.has('t') ? num('t', 0) : null;

  const update = (dt) => {
    if (fly) {
      const i = input(), sp = (i.run ? 80 : 20) * dt;
      const f = new THREE.Vector3(); camera.getWorldDirection(f);
      const r = new THREE.Vector3().crossVectors(f, camera.up).normalize();
      camera.position.addScaledVector(f, ((i.forward ? 1 : 0) - (i.back ? 1 : 0)) * sp).addScaledVector(r, ((i.right ? 1 : 0) - (i.left ? 1 : 0)) * sp);
      camera.position.y += ((i.jump ? 1 : 0) - (i.crouch ? 1 : 0)) * sp;
      camera.position.y = Math.max(camera.position.y, world.heightAt(camera.position.x, camera.position.z) + 0.3);
    } else if (controls.isLocked || held.size) {
      player.update(Math.min(dt, 0.05), input());
    }
    exits?.check(camera, fly);   // [town] walking across the seam reloads into the other world
  };
  const cull = () => {
    camera.updateMatrixWorld();
    pv.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    frustum.setFromProjectionMatrix(pv);
    const c0 = performance.now();
    if (on('terrain')) terrain.update(camera, frustum);
    forest.update(camera, frustum);
    if (on('grass')) grassSys.update(camera, frustum);
    props?.update(camera);
    return performance.now() - c0;
  };
  let cullMs = 0;
  const stats = () => ({
    calls: renderer.info.render.calls, triangles: renderer.info.render.triangles,
    terrainPatches: terrain.stats.patches, terrainByLevel: terrain.stats.byLevel,
    trees: forest.stats.tiers, treeInstances: forest.stats.instances, treeCells: forest.stats.cells,
    grass: grassSys.stats, cullMs: +cullMs.toFixed(2), forestMs: forest.stats.cpuMs,
    pos: camera.position.toArray().map((v) => +v.toFixed(1)),
    trisBy: trisBy(), callsBy: callsBy(),
  });
  // the meshes that drew last frame (one draw call each)
  const callsBy = () => {
    const out = [];
    scene.traverse((o) => {
      if (!o.isMesh || !o.visible) return;
      let p = o.parent; while (p) { if (!p.visible) return; p = p.parent; }
      const g = o.geometry;
      if (o.isInstancedMesh ? o.count === 0 : g.isInstancedBufferGeometry && g.instanceCount === 0) return;
      out.push(o.name || o.type);
    });
    return out;
  };
  // GPU textures by name (as textureMB counts them) and the download by directory
  const textureList = () => {
    const seen = new Map();
    const visit = (t) => {
      if (!t || !t.isTexture || seen.has(t)) return;
      const w = t.image?.width || 0, h = t.image?.height || 0;
      const bpp = t.type === THREE.FloatType ? (t.format === THREE.RedFormat ? 4 : 16) : 4;
      const mips = t.generateMipmaps !== false && t.minFilter !== THREE.NearestFilter && t.minFilter !== THREE.LinearFilter ? 1.33 : 1;
      seen.set(t, { name: t.name || t.userData?.uri || t.image?.src?.split('/').pop() || t.uuid.slice(0, 8), w, h, mb: +((w * h * bpp * mips) / 1e6).toFixed(2) });
    };
    scene.traverse((o) => { const m = o.material; if (!m) return;
      for (const v of Object.values(m.uniforms || {})) visit(v.value);
      for (const v of Object.values(m)) visit(v); });
    return [...seen.values()].sort((a, b) => b.mb - a.mb);
  };
  const downloadBy = () => {
    const by = {};
    for (const e of performance.getEntriesByType('resource')) {
      if (!e.name.startsWith(location.origin)) continue;
      const p = new URL(e.name).pathname.split('/').slice(0, -1).join('/');
      by[p] = +(((by[p] || 0) + (e.encodedBodySize || 0) / 1e6)).toFixed(3);
    }
    return by;
  };
  // triangles per system (instances x triangles per instance, as drawn)
  const trisBy = () => {
    const out = {};
    scene.traverse((o) => {
      if (!o.isMesh || !o.visible || !o.geometry.isInstancedBufferGeometry) return;
      const g = o.geometry, n = (g.drawRange.count === Infinity ? g.index.count : Math.min(g.drawRange.count, g.index.count)) / 3;
      const k = o.name.replace('Wild_', '');
      out[k] = Math.round(n * g.instanceCount);
    });
    return out;
  };
  const textureMB = () => {
    const seen = new Set(); let bytes = 0;
    const visit = (t) => {
      if (!t || !t.isTexture || seen.has(t)) return;
      seen.add(t);
      const w = t.image?.width || 0, h = t.image?.height || 0;
      const bpp = t.type === THREE.FloatType ? (t.format === THREE.RedFormat ? 4 : 16) : 4;
      const mips = t.generateMipmaps !== false && t.minFilter !== THREE.NearestFilter && t.minFilter !== THREE.LinearFilter ? 1.33 : 1;
      bytes += w * h * bpp * mips;
    };
    scene.traverse((o) => { const m = o.material; if (!m) return;
      for (const v of Object.values(m.uniforms || {})) visit(v.value);
      for (const v of Object.values(m)) visit(v); });
    return +(bytes / 1e6).toFixed(1);
  };
  // what the generated data would weigh as shipped files (16-bit heights + gzip; WebP maps;
  // quantised instances + gzip), measured in the page with the browser's own encoders
  const shippingEstimate = async () => {
    const gz = async (u8) => new Uint8Array(await new Response(new Blob([u8]).stream().pipeThrough(new CompressionStream('gzip'))).arrayBuffer()).length;
    const { res, heights } = world;
    let lo = Infinity, hi = -Infinity; for (const h of heights) { if (h < lo) lo = h; if (h > hi) hi = h; }
    const q = new Uint16Array(res * res), sc = 65535 / (hi - lo);
    for (let j = 0; j < res; j++) for (let i = 0; i < res; i++) {        // PNG "sub" filter: deltas along rows
      const k = i + j * res, v = Math.round((heights[k] - lo) * sc), p = i ? Math.round((heights[k - 1] - lo) * sc) : 0;
      q[k] = (v - p) & 0xffff;
    }
    const webp = async (data) => {
      const c = document.createElement('canvas'); c.width = c.height = world.mapRes;
      const ctx = c.getContext('2d'), id = ctx.createImageData(world.mapRes, world.mapRes);
      for (let i = 0; i < data.length; i += 4) { id.data[i] = data[i]; id.data[i + 1] = data[i + 1]; id.data[i + 2] = data[i + 2]; id.data[i + 3] = 255; }
      ctx.putImageData(id, 0, 0);
      const b = await new Promise((r) => c.toBlob(r, 'image/webp', 0.9));
      return b.size;
    };
    let inst = 0, count = 0;
    for (const a of Object.values(world.species)) {
      const n = a.length / 6, u = new Uint16Array(n * 4); count += n;
      for (let k = 0; k < n; k++) {
        u[k * 4] = ((a[k * 6] / world.size + 0.5) * 65535) | 0; u[k * 4 + 1] = ((a[k * 6 + 2] / world.size + 0.5) * 65535) | 0;
        u[k * 4 + 2] = (a[k * 6 + 3] * 20000) | 0; u[k * 4 + 3] = ((a[k * 6 + 4] / 6.2832) * 65535) | 0;
      }
      inst += await gz(new Uint8Array(u.buffer));
    }
    return { heightsMB: +((await gz(new Uint8Array(q.buffer))) / 1e6).toFixed(2), heightRange: [+lo.toFixed(1), +hi.toFixed(1)],
      splatWebpMB: +((await webp(world.splat)) / 1e6).toFixed(2), lightWebpRgbMB: world.light ? +((await webp(world.light)) / 1e6).toFixed(2) : null,
      instancesMB: +(inst / 1e6).toFixed(2), instances: count };
  };

  // pause the loop and draw one frame (screenshots on slow renderers: the compositor waits for a
  // frame that takes a second to draw)
  let loop = null;
  const pause = (p) => { renderer.setAnimationLoop(p ? null : loop); if (p) { cull(); renderer.render(scene, camera); } };
  window.__wild = { world, level, props, town, exits, pause, quality, softwareGPU, terrain, forest, grass: grassSys, uniforms, setView, stats, textureMB, textureList, downloadBy, shippingEstimate, timings: { ...world.timings, ...T },
    cull, colliders: colliders.length, get fly() { return fly; }, set fly(v) { fly = v; } };

  addEventListener('resize', () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); });

  renderer.setAnimationLoop(loop = () => {
    const b = window.__bench;
    b?.frameStart();
    const dt = Math.min(clock.getDelta(), 0.1);
    uniforms.uTime.value = frozen ?? uniforms.uTime.value + dt;
    update(dt);
    b?.drive();
    if (level) {                       // forest air: the forest-floor weight of the splat under the camera
      const half = world.size / 2, M = world.mapRes;
      const i = Math.floor(((camera.position.x + half) / world.size) * M), j = Math.floor(((camera.position.z + half) / world.size) * M);
      const fw = i >= 0 && j >= 0 && i < M && j < M ? world.splat[(i + j * M) * 4 + 1] / 255 : 0;
      const k = uniforms.uForestAirK;
      k.value += (0.55 * Math.max(0, Math.min(1, (fw - 0.3) / 0.5)) * Math.max(0, Math.min(1, 1 - (camera.position.y - world.heightAt(camera.position.x, camera.position.z) - 3) / 25)) - k.value) * Math.min(1, dt * 3);
    }
    cullMs = cull();
    b?.renderStart();
    govern(performance.now());
    renderer.render(scene, camera);
    b?.frameEnd();
    frames++; acc += dt;
    const now = performance.now();
    if (now - lastHud > 400 && overlay.style.display !== 'none') {
      fps = frames / acc; frameMs = (acc / frames) * 1000; frames = 0; acc = 0; lastHud = now;
      const s = stats();
      const tr = Object.entries(s.trees).map(([k, v]) => `${k.padEnd(9)} ${v.map((n) => String(n).padStart(6)).join(' ')}`).join('\n');
      overlay.textContent =
        `${fps.toFixed(0)} fps  ${frameMs.toFixed(2)} ms   ${fly ? 'FLY' : 'WALK'}   q${quality.level}${softwareGPU ? ' (software GPU)' : ''}\n` +
        `draw calls ${s.calls}   triangles ${(s.triangles / 1000).toFixed(0)}k\n` +
        `terrain patches ${s.terrainPatches}  [${s.terrainByLevel.join(' ')}]\n` +
        `trees: near / mid / impostor (fern, tuft: near)\n${tr}\n` +
        `tree instances ${s.treeInstances}  cells ${s.treeCells}\n` +
        `grass tiles ${s.grass.denseTiles}+${s.grass.outerTiles}  blades ${(s.grass.blades / 1000).toFixed(0)}k\n` +
        `cull cpu ${s.cullMs} ms (forest ${s.forestMs})\n` +
        `pos ${s.pos.join(', ')}`;
    }
  });
  status(`world ${T.world} ms, textures ${T.textures} ms, build ${T.build} ms · click to walk · F fly · 1-4 views · H overlay`);
  // first frame drawn (shaders compiled) before reporting loaded
  cull(); renderer.render(scene, camera);
  window.__loaded = true;
}

// The wet / cobble mask of a level (R8G8 over the heightfield's vertices): r = wet (the banks
// within ~3 m of water, darker soil and rock; the falls' spray zone and its face), g = cobble bar
// (low, flat ground beside the water: under 2 m above the nearest water within 34 m). A chamfer
// distance transform from the water raster, carrying the nearest water level.
function wetTexture(world) {
  const { res, spacing, water, heights, size } = world, n = res * res;
  const dist = new Float32Array(n).fill(1e9), lvl = new Float32Array(n);
  for (let k = 0; k < n; k++) if (Number.isFinite(water[k])) { dist[k] = 0; lvl[k] = water[k]; }
  const a = spacing, b = spacing * Math.SQRT2;
  const relax = (k, kk, d) => { const v = dist[kk] + d; if (v < dist[k]) { dist[k] = v; lvl[k] = lvl[kk]; } };
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
  const fx = f ? f.x1 : 1e9, fz = f ? -(f.y1 - oy) : 1e9, tx = f ? f.x0 : 1e9, tz = f ? -(f.y0 - oy) : 1e9;
  for (let j = 0; j < res; j++) for (let i = 0; i < res; i++) {
    const k = i + j * res, x = -half + i * spacing, z = -half + j * spacing;
    const above = heights[k] - lvl[k];
    let wet = Math.max(0, 1 - dist[k] / 3.5) * (above < 3 ? 1 : 0.4);
    if (f) {                                              // spray: the foot and the face of the falls
      const d = Math.hypot(x - fx, z - fz), dt = Math.hypot(x - tx, z - tz);
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

main().catch((e) => { status('error: ' + e.message); console.error(e); });
