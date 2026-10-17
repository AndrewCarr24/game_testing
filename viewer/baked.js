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

export async function loadBake(base, levelName, renderer) {
  const res = await fetch(`${base}levels/${levelName}_bake.json`);
  if (!res.ok) return null;
  const bake = await res.json();
  const pmrem = new THREE.PMREMGenerator(renderer);
  const rooms = {};
  await Promise.all(Object.entries(bake.rooms).map(async ([room, r]) => {
    const [lightTex, envHdr] = await Promise.all([
      new THREE.TextureLoader().loadAsync(base + r.lightmap.file),
      new RGBELoader().loadAsync(base + r.environment.file),
    ]);
    lightTex.flipY = false;                  // glTF UV convention
    lightTex.colorSpace = THREE.SRGBColorSpace;
    lightTex.channel = r.lightmap.uv;        // TEXCOORD_1 -> geometry.attributes.uv1
    envHdr.mapping = THREE.EquirectangularReflectionMapping;
    const envMap = pmrem.fromEquirectangular(envHdr).texture;
    envHdr.dispose();
    rooms[room] = { lightTex, envMap, intensity: r.lightmap.intensity, objects: new Set(r.lightmap.objects) };
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

  function roomMaterial(src, room) {
    const key = `${room}|${src.uuid}|env`;
    if (clones.has(key)) return clones.get(key);
    const m = src.clone();
    m.envMap = rooms[room].envMap;
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
  function applyRoom(root, room) {
    if (!rooms[room]) return;
    root.traverse((o) => { if (o.isMesh) o.material = roomMaterial(o.material, room); });
  }

  return { bake, rooms, applyLightmaps, applyRoom, defaultEnv: Object.values(rooms)[0]?.envMap };
}
