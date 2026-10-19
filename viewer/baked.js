import * as THREE from 'three';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';

// Baked lighting from blender/levels/bake.py (assets/levels/<level>_bake.json),
// one set per room.
//
// Static shell meshes get their room's lightmap on the second UV set, holding all
// diffuse lighting (sun, sky, ceiling lights, lamps, bounce, soft contact shadows).
// On those materials real-time direct light is switched off so nothing is counted
// twice; reflections come from the room's environment panorama.
// Props (anything that moves) are lit by the real-time sun plus their room's baked
// panorama as environment map. Materials are cloned per room where rooms share them.

// A room panorama: .hdr (older bakes) or 8-bit sRGB WebP holding radiance / scale, which
// is decoded back to linear float radiance here so prefiltering sees the same light.
export async function loadEnvironment(url, scale = 1) {
  if (url.endsWith('.hdr')) return new RGBELoader().loadAsync(url);
  const blob = await (await fetch(url)).blob();
  const bmp = await createImageBitmap(blob, { colorSpaceConversion: 'none', premultiplyAlpha: 'none' });
  const g = new OffscreenCanvas(bmp.width, bmp.height).getContext('2d');
  g.drawImage(bmp, 0, 0);
  const src = g.getImageData(0, 0, bmp.width, bmp.height).data;
  const lut = new Float32Array(256);
  for (let i = 0; i < 256; i++) { const c = i / 255; lut[i] = scale * (c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)); }
  const half = new Uint16Array(256);           // half floats, as RGBELoader gives (half the upload)
  for (let i = 0; i < 256; i++) half[i] = THREE.DataUtils.toHalfFloat(lut[i]);
  const one = THREE.DataUtils.toHalfFloat(1);
  const data = new Uint16Array(bmp.width * bmp.height * 4);
  // canvas rows run top-down; equirect textures here are bottom-up (flipY = false below)
  for (let y = 0; y < bmp.height; y++) {
    const row = (bmp.height - 1 - y) * bmp.width * 4, out = y * bmp.width * 4;
    for (let x = 0; x < bmp.width * 4; x += 4) {
      data[out + x] = half[src[row + x]]; data[out + x + 1] = half[src[row + x + 1]]; data[out + x + 2] = half[src[row + x + 2]]; data[out + x + 3] = one;
    }
  }
  const tex = new THREE.DataTexture(data, bmp.width, bmp.height, THREE.RGBAFormat, THREE.HalfFloatType);
  tex.colorSpace = THREE.LinearSRGBColorSpace;
  tex.magFilter = tex.minFilter = THREE.LinearFilter;
  tex.needsUpdate = true;
  return tex;
}

// Box-projected (parallax-corrected) reflections: a room is a box, so a reflection ray is
// traced to the room's walls and the panorama is looked up in the direction from the probe
// (where it was rendered) to that hit point. Floors and counters then reflect the real
// windows and walls in the right place instead of a panorama at infinity. A few ALU ops.
const BOX_PARS = /* glsl */ `
uniform vec3 envBoxMin, envBoxMax, envProbe;
varying vec3 vWorldPos;
vec3 boxProject( vec3 dir ) {
  vec3 p = clamp( vWorldPos, envBoxMin + 0.01, envBoxMax - 0.01 );
  vec3 t = max( ( envBoxMax - p ) / dir, ( envBoxMin - p ) / dir );
  float d = min( min( t.x, t.y ), t.z );
  return normalize( p + dir * d - envProbe );
}`;
const boxRadiance = THREE.ShaderChunk.envmap_physical_pars_fragment.replace(
  'reflectVec = inverseTransformDirection( reflectVec, viewMatrix );',
  'reflectVec = boxProject( inverseTransformDirection( reflectVec, viewMatrix ) );');

// Uneven sheen on the shell (floors, walls, counters): real polished surfaces are smudged
// and worn, so their reflections break up. Roughness varies with low-frequency world-space
// noise (footpaths, wipes) and with the texture's own grain (dark grain and joints a little
// rougher). Glossy materials only; a few ALU ops, no textures.
const SHEEN_PARS = /* glsl */ `
float sheenHash( vec2 p ) { p = fract( p * vec2( 123.34, 456.21 ) ); p += dot( p, p + 45.32 ); return fract( p.x * p.y ); }
float sheenNoise( vec2 p ) {
  vec2 i = floor( p ), f = fract( p ), u = f * f * ( 3.0 - 2.0 * f );
  return mix( mix( sheenHash( i ), sheenHash( i + vec2( 1, 0 ) ), u.x ), mix( sheenHash( i + vec2( 0, 1 ) ), sheenHash( i + vec2( 1, 1 ) ), u.x ), u.y );
}`;
const SHEEN = /* glsl */ `
if ( roughnessFactor < 0.75 ) {
  vec2 sp = vWorldPos.xz + vWorldPos.y * 0.37;
  float smudge = sheenNoise( sp * 0.9 ) * 0.65 + sheenNoise( sp * 3.7 ) * 0.35;
  float grain = clamp( 1.0 - dot( diffuseColor.rgb, vec3( 0.333 ) ) * 1.6, 0.0, 1.0 );
  roughnessFactor = clamp( roughnessFactor * ( 0.72 + 0.5 * smudge + 0.25 * grain ), 0.04, 1.0 );
}`;

function addSheen(shader) {
  shader.fragmentShader = shader.fragmentShader
    .replace('#include <roughnessmap_pars_fragment>', '#include <roughnessmap_pars_fragment>\n' + SHEEN_PARS)
    .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\n' + SHEEN);
}

function addBoxProjection(shader, box) {
  if (!box) return;
  Object.assign(shader.uniforms, { envBoxMin: { value: box.min }, envBoxMax: { value: box.max }, envProbe: { value: box.probe } });
  shader.vertexShader = shader.vertexShader
    .replace('#include <common>', '#include <common>\nvarying vec3 vWorldPos;')
    .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\nvWorldPos = worldPosition.xyz;');
  shader.fragmentShader = shader.fragmentShader
    .replace('#include <envmap_physical_pars_fragment>', BOX_PARS + '\n' + boxRadiance);
}

// levelRooms: mansion.json rooms (rect, floor, height, probe) for the reflection boxes;
// box = false turns box projection off (?box=0, for comparison)
// specOcc = false turns the lightmap specular occlusion off (?so=0)
// sheen = false turns the roughness variation off (?sheen=0)
export async function loadBake(base, levelName, renderer, levelRooms = {}, box = true, specOcc = true, sheen = true) {
  const res = await fetch(`${base}levels/${levelName}_bake.json`);
  if (!res.ok) return null;
  const bake = await res.json();
  const pmrem = new THREE.PMREMGenerator(renderer);
  const rooms = {};
  await Promise.all(Object.entries(bake.rooms).map(async ([room, r]) => {
    const [lightTex, envHdr] = await Promise.all([
      new THREE.TextureLoader().loadAsync(base + r.lightmap.file),
      loadEnvironment(base + r.environment.file, r.environment.scale),
    ]);
    lightTex.flipY = false;                  // glTF UV convention
    lightTex.colorSpace = THREE.SRGBColorSpace;
    lightTex.channel = r.lightmap.uv;        // TEXCOORD_1 -> geometry.attributes.uv1
    envHdr.mapping = THREE.EquirectangularReflectionMapping;
    const envMap = pmrem.fromEquirectangular(envHdr).texture;
    envHdr.dispose();
    const L = levelRooms[room], T = 0.15;   // T: wall lining, the rect is the room's outer edge
    rooms[room] = { lightTex, envMap, intensity: r.lightmap.intensity, objects: new Set(r.lightmap.objects),
                    sh: r.sh ? r.sh.map((c) => new THREE.Vector3(...c)) : null,
                    box: box && L?.probe && room !== 'courtyard' ? {   // (open to the sky: no box)
                      min: new THREE.Vector3(L.rect[0] + T, L.floor, L.rect[1] + T),
                      max: new THREE.Vector3(L.rect[2] - T, L.floor + L.height, L.rect[3] - T),
                      probe: new THREE.Vector3(...L.probe) } : null };
  }));
  pmrem.dispose();

  const roomOf = new Map();                  // shell mesh name -> room
  for (const [room, r] of Object.entries(rooms)) for (const n of r.objects) roomOf.set(n, room);
  const clones = new Map();                  // `${room}|${material.uuid}|${kind}` -> material

  function bakedMaterial(src, room) {
    const key = `${room}|${src.uuid}|baked`;
    if (clones.has(key)) return clones.get(key);
    const r = rooms[room];
    const m = src.clone();
    m.lightMap = r.lightTex;
    m.lightMapIntensity = r.intensity;
    m.envMap = r.envMap;
    m.onBeforeCompile = (shader) => {
      addBoxProjection(shader, r.box);
      if (r.box && sheen) addSheen(shader);           // (needs vWorldPos from the box projection)
      if (r.sh) shader.uniforms.roomSH = { value: r.sh };
      shader.fragmentShader = shader.fragmentShader.replace(
        '#include <lights_pars_begin>', '#include <lights_pars_begin>\n' + (r.sh ? 'uniform vec3 roomSH[ 9 ];' : '')).replace(
        '#include <lights_fragment_maps>',
        [
          // all direct light is in the bake; without shadows a real-time sun glint
          // would appear even where the sun can't reach (windowless rooms)
          'reflectedLight.directDiffuse = vec3( 0.0 );',
          'reflectedLight.directSpecular = vec3( 0.0 );',
          'irradiance = vec3( 0.0 );',
          '#include <lights_fragment_maps>',
          'iblIrradiance = vec3( 0.0 );',
          // specular occlusion from the bake: where the lightmap is much darker than the
          // room's average light from that side (under a table, behind a sofa), the
          // panorama's reflection can't reach either
          ...(r.sh && specOcc ? [
            'float lmL = dot( lightMapIrradiance, vec3( 0.2126, 0.7152, 0.0722 ) );',
            'float shL = dot( shGetIrradianceAt( inverseTransformDirection( geometryNormal, viewMatrix ), roomSH ), vec3( 0.2126, 0.7152, 0.0722 ) );',
            'radiance *= smoothstep( 0.1, 0.8, lmL / max( shL, 1e-4 ) );',
          ] : []),
        ].join('\n'));
    };
    m.customProgramCacheKey = () => 'baked-diffuse' + (r.box ? '-box' : '') + (r.sh && specOcc ? '-so' : '') + (r.box && sheen ? '-sheen' : '');
    clones.set(key, m);
    return m;
  }

  // Props: diffuse light from the room's spherical-harmonics probe (computed from the
  // unclamped panorama, so the ceiling strips' full light reaches the furniture, matching
  // the baked walls); reflections from the room's (highlight-clamped) panorama.
  // sunless: the room never gets direct sun (mansion.json rooms[r].sun === false), so its
  // props skip the real-time sun (and its shadow lookups) entirely
  function roomMaterial(src, room, sunless = false) {
    const key = `${room}|${src.uuid}|env${sunless ? '|nosun' : ''}`;
    if (clones.has(key)) return clones.get(key);
    const m = src.clone();
    const r = rooms[room];
    m.envMap = r.envMap;
    if (r.sh) {
      m.onBeforeCompile = (shader) => {
        addBoxProjection(shader, r.box);
        shader.uniforms.roomSH = { value: r.sh };
        shader.fragmentShader = shader.fragmentShader
          .replace('#include <lights_pars_begin>', '#include <lights_pars_begin>\nuniform vec3 roomSH[ 9 ];')
          .replace('#include <lights_fragment_maps>', [
            '#include <lights_fragment_maps>',
            'iblIrradiance = vec3( 0.0 );',
            'irradiance += shGetIrradianceAt( inverseTransformDirection( geometryNormal, viewMatrix ), roomSH );',
            ...(sunless ? ['reflectedLight.directDiffuse = vec3( 0.0 );', 'reflectedLight.directSpecular = vec3( 0.0 );'] : []),
          ].join('\n'));
      };
      m.customProgramCacheKey = () => (sunless ? 'room-sh-nosun' : 'room-sh') + (r.box ? '-box' : '');
    }
    clones.set(key, m);
    return m;
  }

  // shell: every baked mesh gets its room's lightmap
  function applyLightmaps(root) {
    let count = 0;
    root.traverse((o) => {
      const room = o.isMesh && roomOf.get(o.name);
      if (!room || !o.geometry.attributes.uv1) return;
      o.material = bakedMaterial(o.material, room);
      o.receiveShadow = false;             // its shadows are already in the bake
      count++;
    });
    return count;
  }

  // props: light everything under `root` with its room's environment
  function applyRoom(root, room, sunless = false) {
    if (!rooms[room]) return;
    root.traverse((o) => {
      if (!o.isMesh) return;
      o.material = roomMaterial(o.material, room, sunless);
      if (sunless) o.castShadow = o.receiveShadow = false;   // nothing for the sun to shade here
    });
  }

  // materials without a room of their own (the house's window glass) reflect the entry's
  // panorama; picked by name, not by which room happened to finish loading first
  const fallback = rooms.entry ?? rooms[Object.keys(bake.rooms)[0]];
  return { bake, rooms, applyLightmaps, applyRoom, defaultEnv: fallback?.envMap };
}
