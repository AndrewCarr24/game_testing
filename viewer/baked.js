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

export async function loadBake(base, levelName, renderer) {
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
    rooms[room] = { lightTex, envMap, intensity: r.lightmap.intensity, objects: new Set(r.lightmap.objects),
                    sh: r.sh ? r.sh.map((c) => new THREE.Vector3(...c)) : null };
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
      shader.fragmentShader = shader.fragmentShader.replace(
        '#include <lights_fragment_maps>',
        [
          // all direct light is in the bake; without shadows a real-time sun glint
          // would appear even where the sun can't reach (windowless rooms)
          'reflectedLight.directDiffuse = vec3( 0.0 );',
          'reflectedLight.directSpecular = vec3( 0.0 );',
          'irradiance = vec3( 0.0 );',
          '#include <lights_fragment_maps>',
          'iblIrradiance = vec3( 0.0 );',
        ].join('\n'));
    };
    m.customProgramCacheKey = () => 'baked-diffuse';
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
      m.customProgramCacheKey = () => (sunless ? 'room-sh-nosun' : 'room-sh');
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
