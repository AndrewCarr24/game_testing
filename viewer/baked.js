import * as THREE from 'three';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';

// Baked lighting from blender/levels/bake.py (assets/levels/<level>_bake.json),
// one set per room.
//
// Static shell meshes get their room's lightmap on the second UV set, holding all
// diffuse lighting (sun, sky, ceiling lights, lamps, bounce, soft contact shadows).
// On those materials real-time directional light is switched off so nothing is counted
// twice (point and spot lights, i.e. the flashlight, still light them); reflections come
// from the room's environment panorama.
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

// ------------------------------------------------------------------ lights off
// A room with a lights-off bake (bake.py --state off: bake JSON rooms[r].off) fades between its
// lit and dark states from its light signal (lights_<room>, or the group's) and `power`:
// - shell: the off lightmap is packed into the on lightmap's alpha as a luminance ratio
//   (sqrt-encoded), decoded in the shader as  off = on x ratio x mix(tint, 1, ratio)
//   (the light left over keeps the room's own tint: sky / sun bounce), so the GPU holds one
//   texture per room as before;
// - props: the room's SH probe is lerped in place (every material of the room shares it);
// - reflections: the room's panorama is re-filtered (PMREM) from a blend of the on and off
//   panoramas, a few times per fade (they're blurry), into the same render target;
// - the room's ceiling strips (shell emissive) fade with it; the fixtures' glows are reacts
//   (interactables.js) on the same signal.
const LUT_LIN = new Float32Array(256);
for (let i = 0; i < 256; i++) { const c = i / 255; LUT_LIN[i] = c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
const FADE = 0.45;           // seconds for a room to go dark or come back (dimmable LEDs)

async function fetchBlob(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: ${res.status}`);
  return res.blob();
}
const toBitmap = (blob) => createImageBitmap(blob, { colorSpaceConversion: 'none', premultiplyAlpha: 'none' });
// a panorama bitmap as an 8-bit sRGB texture (decoded to linear by the GPU)
function envTexture(bmp) {
  const t = new THREE.Texture(bmp);
  t.colorSpace = THREE.SRGBColorSpace;
  t.flipY = false;
  t.generateMipmaps = false;
  t.minFilter = t.magFilter = THREE.LinearFilter;
  t.needsUpdate = true;
  return t;
}

function bitmapPixels(bmp) {
  const g = new OffscreenCanvas(bmp.width, bmp.height).getContext('2d', { willReadFrequently: true });
  g.drawImage(bmp, 0, 0);
  return g.getImageData(0, 0, bmp.width, bmp.height).data;
}

// on (RGB) + the luminance ratio off / on (alpha, sqrt-encoded) in one sRGB RGBA texture,
// rows top-down like the image (flipY = false: the glTF UV convention)
function packLightmap(onBmp, offBmp) {
  if (onBmp.width !== offBmp.width || onBmp.height !== offBmp.height) return null;
  const a = bitmapPixels(onBmp), b = bitmapPixels(offBmp);
  const out = new Uint8Array(a.length);
  for (let i = 0; i < a.length; i += 4) {
    const lon = 0.2126 * LUT_LIN[a[i]] + 0.7152 * LUT_LIN[a[i + 1]] + 0.0722 * LUT_LIN[a[i + 2]];
    const loff = 0.2126 * LUT_LIN[b[i]] + 0.7152 * LUT_LIN[b[i + 1]] + 0.0722 * LUT_LIN[b[i + 2]];
    out[i] = a[i]; out[i + 1] = a[i + 1]; out[i + 2] = a[i + 2];
    out[i + 3] = lon > 1e-6 ? Math.round(Math.sqrt(Math.min(1, loff / lon)) * 255) : 255;
  }
  const tex = new THREE.DataTexture(out, onBmp.width, onBmp.height, THREE.RGBAFormat, THREE.UnsignedByteType);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.generateMipmaps = true;
  tex.minFilter = THREE.LinearMipmapLinearFilter;
  tex.magFilter = THREE.LinearFilter;
  tex.needsUpdate = true;
  return tex;
}

// the lightmap chunk with the lights-off ratio applied (roomOff 0 = lit, 1 = dark)
const LIGHTMAP_OFF = THREE.ShaderChunk.lights_fragment_maps.replace(
  'vec3 lightMapIrradiance = lightMapTexel.rgb * lightMapIntensity;',
  'vec3 lightMapIrradiance = lightMapTexel.rgb * lightMapIntensity;\n' +
  'float lmRatio = lightMapTexel.a * lightMapTexel.a;\n' +
  'lightMapIrradiance *= mix( vec3( 1.0 ), lmRatio * mix( roomTint, vec3( 1.0 ), lmRatio ), roomOff );');
if (!LIGHTMAP_OFF.includes('lmRatio')) console.warn('baked.js: lights_fragment_maps changed; rooms will not go dark');

// the panorama blend (on -> off) that a room's reflections are re-filtered from
const ENV_BLEND = new THREE.ShaderMaterial({
  uniforms: { onMap: { value: null }, offMap: { value: null }, t: { value: 0 }, scale: { value: 1 } },
  vertexShader: 'varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4( position.xy, 0.0, 1.0 ); }',
  // the bitmaps' rows run top-down (an ImageBitmap ignores flipY); equirect textures here are bottom-up
  fragmentShader: `uniform sampler2D onMap, offMap; uniform float t, scale; varying vec2 vUv;
    void main() { vec2 uv = vec2( vUv.x, 1.0 - vUv.y );
      gl_FragColor = vec4( mix( texture2D( onMap, uv ).rgb, texture2D( offMap, uv ).rgb, t ) * scale, 1.0 ); }`,
  depthTest: false, depthWrite: false,
});

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

// Point and spot lights (the flashlight, a hero lamp's react light) still light baked surfaces:
// only the sun and the stand-in fills are in the bake. Their direct light is summed before the
// directional loop in r160's chunk, so it's saved there and put back after the rest is zeroed.
// The clearcoat and sheen lobes keep their own direct-light sums (globals of the physical
// shader, added to the output after lights_fragment_end), so they're saved and restored too:
// otherwise the sun's coat glint shows on floors and props it can't reach.
const LOCAL_LIGHTS = THREE.ShaderChunk.lights_fragment_begin.replace(
  '#if ( NUM_DIR_LIGHTS > 0 ) && defined( RE_Direct )',
  'vec3 localDiffuse = reflectedLight.directDiffuse, localSpecular = reflectedLight.directSpecular;\n' +
  'vec3 localCoat = clearcoatSpecularDirect, localSheen = sheenSpecularDirect;\n#if ( NUM_DIR_LIGHTS > 0 ) && defined( RE_Direct )');
if (!LOCAL_LIGHTS.includes('localDiffuse')) console.warn('baked.js: lights_fragment_begin changed; point/spot lights will not light baked surfaces');
const keepLocal = (fs) => fs.replace('#include <lights_fragment_begin>', LOCAL_LIGHTS.includes('localDiffuse') ? LOCAL_LIGHTS
  : '#include <lights_fragment_begin>\nvec3 localDiffuse = vec3( 0.0 ), localSpecular = vec3( 0.0 ), localCoat = vec3( 0.0 ), localSheen = vec3( 0.0 );');
// after keepLocal: direct light back to the local lights only (the sun is in the bake, or can't get here)
const LOCAL_ONLY = [
  'reflectedLight.directDiffuse = localDiffuse;',
  'reflectedLight.directSpecular = localSpecular;',
  'clearcoatSpecularDirect = localCoat;',
  'sheenSpecularDirect = localSheen;',
];

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
// offStates = false ignores the lights-off bakes (?loff=0, for comparison): rooms stay lit
export async function loadBake(base, levelName, renderer, levelRooms = {}, box = true, specOcc = true, sheen = true, offStates = true) {
  const res = await fetch(`${base}levels/${levelName}_bake.json`);
  if (!res.ok) return null;
  const bake = await res.json();
  const pmrem = new THREE.PMREMGenerator(renderer);
  const rooms = {};
  // lights off: one PMREM generator per panorama width (each keeps its blur targets, so a room's
  // reflections can be re-filtered into the same render target) and one blend target per width
  const envGen = new Map();
  const envGenFor = (w, h) => {
    if (!envGen.has(w)) {
      const target = new THREE.WebGLRenderTarget(w, h, { type: THREE.HalfFloatType, depthBuffer: false, generateMipmaps: false,
                                                       magFilter: THREE.LinearFilter, minFilter: THREE.LinearFilter });
      target.texture.mapping = THREE.EquirectangularReflectionMapping;
      envGen.set(w, { gen: new THREE.PMREMGenerator(renderer), target });
    }
    return envGen.get(w);
  };
  const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), ENV_BLEND);
  quad.frustumCulled = false;
  const quadCam = new THREE.Camera();
  // re-filter room r's reflections from its panoramas blended at t (0 = lit, 1 = dark); needs
  // the panoramas decoded (envSources)
  function filterEnv(r, t) {
    const L = r.lit, { gen, target } = envGenFor(L.envW, L.envH);
    const u = ENV_BLEND.uniforms;
    u.onMap.value = L.src.on; u.offMap.value = L.src.off; u.t.value = t; u.scale.value = L.envScale;
    const prev = renderer.getRenderTarget();
    renderer.setRenderTarget(target);
    renderer.render(quad, quadCam);
    renderer.setRenderTarget(prev);
    L.envRT = gen.fromEquirectangular(target.texture, L.envRT);
    L.envT = t;
    return L.envRT.texture;
  }
  // a fading room's panoramas: kept as their (few kB) WebP blobs and decoded only while needed
  function envSources(L) {
    if (L.src || L.loading) return L.src;
    L.loading = Promise.all(L.envBlobs.map(toBitmap)).then(([a, b]) => { L.src = { on: envTexture(a), off: envTexture(b), bitmaps: [a, b] }; })
      .catch((err) => console.warn('baked.js: panorama decode failed', err)).finally(() => { L.loading = null; });
    return null;
  }
  function freeEnvSources(L) {
    if (!L.src) return;
    L.src.on.dispose(); L.src.off.dispose();
    for (const bmp of L.src.bitmaps) bmp.close();
    L.src = null;
  }
  await Promise.all(Object.entries(bake.rooms).map(async ([room, r]) => {
    let lightTex, envMap, lit = null;
    if (r.off && offStates) {
      try {
        const blobs = await Promise.all([r.lightmap.file, r.off.lightmap, r.environment.file, r.off.environment].map((f) => fetchBlob(base + f)));
        const [onBmp, offBmp, envOnBmp, envOffBmp] = await Promise.all(blobs.map(toBitmap));
        lightTex = packLightmap(onBmp, offBmp);
        onBmp.close(); offBmp.close();
        if (!lightTex || envOnBmp.width !== envOffBmp.width) throw new Error('its off maps do not match the on maps (re-bake with --state off)');
        lit = { signal: r.off.signal, t: 0, envT: -1, ratio: r.off.ratio ?? 0.3,
                envBlobs: blobs.slice(2), src: { on: envTexture(envOnBmp), off: envTexture(envOffBmp), bitmaps: [envOnBmp, envOffBmp] },
                loading: null, envW: envOnBmp.width, envH: envOnBmp.height, envScale: r.environment.scale, envRT: null,
                offU: { value: 0 }, tintU: { value: new THREE.Vector3(...(r.off.tint || [1, 1, 1])) },
                shOn: r.sh.map((c) => new THREE.Vector3(...c)), shOff: r.off.sh.map((c) => new THREE.Vector3(...c)) };
      } catch (err) {
        console.warn(`baked.js: ${room} lights-off state not loaded: ${err.message}`);
        lightTex = null; lit = null;
      }
    }
    if (!lightTex) {
      lightTex = await new THREE.TextureLoader().loadAsync(base + r.lightmap.file);
      lightTex.colorSpace = THREE.SRGBColorSpace;
    }
    lightTex.flipY = false;                  // glTF UV convention
    lightTex.channel = r.lightmap.uv;        // TEXCOORD_1 -> geometry.attributes.uv1
    if (!lit) {
      const envHdr = await loadEnvironment(base + r.environment.file, r.environment.scale);
      envHdr.mapping = THREE.EquirectangularReflectionMapping;
      envMap = pmrem.fromEquirectangular(envHdr).texture;
      envHdr.dispose();
    }
    const L = levelRooms[room], T = 0.15;   // T: wall lining, the rect is the room's outer edge
    rooms[room] = { lightTex, envMap, intensity: r.lightmap.intensity, objects: new Set(r.lightmap.objects),
                    sh: r.sh ? r.sh.map((c) => new THREE.Vector3(...c)) : null, lit,
                    offU: lit ? lit.offU : { value: 0 }, tintU: lit ? lit.tintU : { value: new THREE.Vector3(1, 1, 1) },
                    box: box && L?.probe && room !== 'courtyard' ? {   // (open to the sky: no box)
                      min: new THREE.Vector3(L.rect[0] + T, L.floor, L.rect[1] + T),
                      max: new THREE.Vector3(L.rect[2] - T, L.floor + L.height, L.rect[3] - T),
                      probe: new THREE.Vector3(...L.probe) } : null };
  }));
  pmrem.dispose();
  // the lit panoramas of the rooms with an off state (one at a time: the generators are shared)
  for (const r of Object.values(rooms)) if (r.lit) { r.envMap = filterEnv(r, 0); freeEnvSources(r.lit); }

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
      Object.assign(shader.uniforms, { roomOff: r.offU, roomTint: r.tintU });     // lights off (shared per room)
      shader.fragmentShader = keepLocal(shader.fragmentShader).replace(
        '#include <lights_pars_begin>', '#include <lights_pars_begin>\nuniform float roomOff;\nuniform vec3 roomTint;\n' + (r.sh ? 'uniform vec3 roomSH[ 9 ];' : '')).replace(
        '#include <lights_fragment_maps>',
        [
          // all direct light is in the bake; without shadows a real-time sun glint
          // would appear even where the sun can't reach (windowless rooms)
          ...LOCAL_ONLY,
          'irradiance = vec3( 0.0 );',
          LIGHTMAP_OFF.includes('lmRatio') ? LIGHTMAP_OFF : '#include <lights_fragment_maps>',
          'iblIrradiance = vec3( 0.0 );',
          // specular occlusion from the bake: where the lightmap is much darker than the
          // room's average light from that side (under a table, behind a sofa), the
          // panorama's reflection can't reach either
          ...(r.sh && specOcc ? [
            'float lmL = dot( lightMapIrradiance, vec3( 0.2126, 0.7152, 0.0722 ) );',
            'float shL = dot( shGetIrradianceAt( inverseTransformDirection( geometryNormal, viewMatrix ), roomSH ), vec3( 0.2126, 0.7152, 0.0722 ) );',
            // (not on metals: a mirror or steel panel is dark in the lightmap because it has
            // no diffuse, not because it's occluded; with it the gym's mirror wall went black)
            'radiance *= mix( smoothstep( 0.1, 0.8, lmL / max( shL, 1e-4 ) ), 1.0, step( 0.5, metalnessFactor ) );',
          ] : []),
        ].join('\n'));
    };
    m.customProgramCacheKey = () => 'baked-local' + (r.box ? '-box' : '') + (r.sh && specOcc ? '-so' : '') + (r.box && sheen ? '-sheen' : '');
    clones.set(key, m);
    return m;
  }

  // Props: diffuse light from the room's spherical-harmonics probe (computed from the
  // unclamped panorama, so the ceiling strips' full light reaches the furniture, matching
  // the baked walls); reflections from the room's (highlight-clamped) panorama.
  // sunless: the room never gets direct sun (mansion.json rooms[r].sun === false), so its
  // props skip the real-time sun (and its shadow lookups) entirely
  //
  // door: { room, axis } for a door between `room` and door.room. A door lit by its own room's
  // probe alone read black from the brighter side (the gym door from the office), so each face
  // takes the probe of the room it faces: axis (world, horizontal) points from `room` into
  // door.room; the leaf's edges and a door swung open blend the two; reflections stay `room`'s.
  // Every prop runs the same code (for the others roomSH2 = roomSH and the branch is skipped),
  // so doors share the props' shader programs: no extra compile when one comes into view.
  const noDoor = new THREE.Vector3();
  function roomMaterial(src, room, sunless = false, door = null) {
    const key = `${room}|${src.uuid}|env${sunless ? '|nosun' : ''}${door ? `|door:${door.room}` : ''}`;
    if (clones.has(key)) return clones.get(key);
    const m = src.clone();
    const r = rooms[room];
    m.envMap = r.envMap;
    if (r.sh) {
      const sh2 = door ? rooms[door.room].sh : r.sh;
      m.onBeforeCompile = (shader) => {
        addBoxProjection(shader, r.box);
        Object.assign(shader.uniforms, { roomSH: { value: r.sh }, roomSH2: { value: sh2 }, doorAxis: { value: door ? door.axis : noDoor } });
        shader.fragmentShader = (sunless ? keepLocal(shader.fragmentShader) : shader.fragmentShader)
          .replace('#include <lights_pars_begin>', '#include <lights_pars_begin>\nuniform vec3 roomSH[ 9 ], roomSH2[ 9 ];\nuniform vec3 doorAxis;')
          .replace('#include <lights_fragment_maps>', [
            '#include <lights_fragment_maps>',
            'iblIrradiance = vec3( 0.0 );',
            'vec3 shN = inverseTransformDirection( geometryNormal, viewMatrix );',
            'vec3 shIrr = shGetIrradianceAt( shN, roomSH );',
            'if ( dot( doorAxis, doorAxis ) > 0.0 ) shIrr = mix( shIrr, shGetIrradianceAt( shN, roomSH2 ), smoothstep( -0.35, 0.35, dot( shN, doorAxis ) ) );',
            'irradiance += shIrr;',
            ...(sunless ? LOCAL_ONLY : []),
          ].join('\n'));
      };
      m.customProgramCacheKey = () => (sunless ? 'room-sh-nosun-local' : 'room-sh') + (r.box ? '-box' : '');
    }
    clones.set(key, m);
    return m;
  }

  // a door prop between rooms a and b (a's lighting only if either has no probe)
  function applyDoor(root, a, b, axis, sunless = false) {
    if (!rooms[a]?.sh || !rooms[b]?.sh) return applyRoom(root, a, sunless);
    root.traverse((o) => {
      if (!o.isMesh) return;
      o.material = roomMaterial(o.material, a, sunless, { room: b, axis });
      if (sunless) o.castShadow = o.receiveShadow = false;
    });
  }

  // The house's window glass: no lightmap and no shadows (it's transparent), so the real-time
  // sun put its highlight on every pane, also inside rooms the sun can't reach (the gym's north
  // glass). Its direct specular is kept only while the eye is outdoors (glassSun = 1, see
  // setGlassSun: there the visible face is the sunlit outer one); indoors it shows only the
  // panorama's reflection. Balustrade glass is always indoors.
  const glassSun = { value: 0 };
  function glassMaterial(src, outdoor) {
    const key = `${src.uuid}|glass`;
    if (clones.has(key)) return clones.get(key);
    const m = src.clone();
    m.onBeforeCompile = (shader) => {
      shader.uniforms.glassSun = outdoor ? glassSun : { value: 0 };
      shader.fragmentShader = keepLocal(shader.fragmentShader)
        .replace('#include <lights_pars_begin>', '#include <lights_pars_begin>\nuniform float glassSun;')
        .replace('#include <lights_fragment_maps>', [
          '#include <lights_fragment_maps>',
          'reflectedLight.directSpecular = mix( localSpecular, reflectedLight.directSpecular, glassSun );',
          'clearcoatSpecularDirect = mix( localCoat, clearcoatSpecularDirect, glassSun );',
        ].join('\n'));
    };
    m.customProgramCacheKey = () => 'house-glass';
    clones.set(key, m);
    return m;
  }

  // shell: every baked mesh gets its room's lightmap; the glass its sun-aware material
  const byLength = Object.keys(rooms).sort((a, b) => b.length - a.length);
  const strips = {};                         // room -> {material, base}: its ceiling strips' glow
  function applyLightmaps(root) {
    let count = 0;
    root.traverse((o) => {
      if (!o.isMesh) return;
      // the glowing ceiling slots (one merged mesh per room): their glow follows the room's lights
      if (!Array.isArray(o.material) && /^M_LightStrip/.test(o.material.name)) {
        const room = byLength.find((n) => o.name.startsWith(`Mansion_${n}_`));
        if (room) {
          strips[room] ??= { material: o.material.clone(), base: o.material.emissiveIntensity };
          o.material = strips[room].material;
        }
        return;
      }
      const room = roomOf.get(o.name);
      if (!room && !Array.isArray(o.material) && /Glass/.test(o.material.name)) {
        o.material = glassMaterial(o.material, !/Rail/.test(o.material.name));
        return;
      }
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
  // is the eye outdoors (the lawn, the terraces, the courtyard)? Then the glass shows the sun
  const setGlassSun = (outdoors) => { glassSun.value = outdoors ? 1 : 0; };

  // ---- lights off: which signal each room's lights follow, and the per-frame fade
  // room -> signal: its off bake's, else mansion.json rooms[r].lights, else the lights signal
  // most of its fixtures were wired to (ix_common.wire), else lights_<room> (as bake.py)
  let signals = null;
  const roomSignal = {};
  const state = {};                          // room -> {t, target} for rooms without an off bake (strips only)
  function bindSignals(sigs, level) {
    signals = sigs;
    const counts = {};
    for (const p of level.props || []) {
      const s = typeof p.signal === 'object' && p.signal ? p.signal.lights : (typeof p.signal === 'string' && p.signal.startsWith('lights_') ? p.signal : null);
      if (s) { counts[p.room] ??= {}; counts[p.room][s] = (counts[p.room][s] || 0) + 1; }
    }
    for (const room of Object.keys(level.rooms)) {
      const c = counts[room];
      roomSignal[room] = rooms[room]?.lit?.signal ?? level.rooms[room].lights ??
        (c ? Object.keys(c).sort((a, b) => c[b] - c[a])[0] : `lights_${room}`);
      if (roomSignal[room]) sigs.define(roomSignal[room], true);      // a room's lights start on unless a switch says otherwise
    }
    // start in the right state, no fade
    for (const room of Object.keys(roomSignal)) apply(room, target(room));    // (its reflections follow in update)
  }
  const target = (room) => (!signals || !roomSignal[room] ? 0 :
    (signals.get('power') === false || signals.get(roomSignal[room]) === false) ? 1 : 0);
  const smooth = (t) => t * t * (3 - 2 * t);
  // t: 0 = lit, 1 = dark (linear; eased here)
  function apply(room, t) {
    const r = rooms[room], L = r?.lit, st = L ?? (state[room] ??= { t: 0 });
    st.t = t;
    const s = smooth(t);
    if (strips[room]) strips[room].material.emissiveIntensity = strips[room].base * (1 - s);
    if (!L) return;
    L.offU.value = s;
    for (let i = 0; i < 9; i++) r.sh[i].lerpVectors(L.shOn[i], L.shOff[i], s);
  }
  // per frame: fade every room toward its signal; re-filter a fading room's reflections every
  // ~0.12 of the fade (at most 2 rooms a frame: power off fades the whole house at once)
  function update(dt) {
    if (!signals) return;
    const pending = [];
    for (const room of Object.keys(roomSignal)) {
      const r = rooms[room], st = r?.lit ?? state[room];
      if (!st) continue;
      const goal = target(room);
      const L = r?.lit;
      if (st.t !== goal) {
        if (L) envSources(L);                    // start decoding its panoramas
        apply(room, goal > st.t ? Math.min(goal, st.t + dt / FADE) : Math.max(goal, st.t - dt / FADE));
      }
      if (L) {
        const s = smooth(L.t), gap = Math.abs(L.envT - s);
        if (gap > 0.12 || (gap > 1e-3 && L.t === goal)) pending.push([gap, room, goal]);
      }
    }
    pending.sort((a, b) => b[0] - a[0]);
    let n = 0;
    for (const [, room, goal] of pending) {
      const L = rooms[room].lit;
      if (n >= 2 || !envSources(L)) continue;   // (still decoding: next frame)
      filterEnv(rooms[room], smooth(L.t));
      n++;
      if (L.t === goal) freeEnvSources(L);       // settled: free the decoded panoramas
    }
  }
  // how much of a room's light is on right now: 1 = lit, down to its dark state's share of
  // the light (sun and sky through the windows, the neighbours' through the doors); for the
  // Grimble's eyes, the tablet, tests
  const lightLevel = (room) => {
    const L = rooms[room]?.lit;
    return L ? 1 - smooth(L.t) * (1 - L.ratio) : 1 - (state[room] ? smooth(state[room].t) : 0);
  };
  const isDark = (room) => (rooms[room]?.lit ?? state[room])?.t === 1;

  return { bake, rooms, applyLightmaps, applyRoom, applyDoor, setGlassSun, defaultEnv: fallback?.envMap,
           bindSignals, update, lightLevel, isDark, roomSignal };
}
