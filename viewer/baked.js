import * as THREE from 'three';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';

// Baked lighting from blender/levels/bake.py (assets/levels/<level>_bake.json).
//
// Static shell meshes get a lightmap on their second UV set holding all diffuse
// lighting (sun, sky, ceiling coves, bounce, soft contact shadows). On those
// materials real-time diffuse light is switched off so nothing is counted twice;
// real-time specular (sun glints, environment reflections) stays.
// Everything else (props, anything that moves) is lit by the real-time sun plus
// the baked room panorama as its environment map.

export async function loadBake(base, levelName, renderer) {
  const res = await fetch(`${base}levels/${levelName}_bake.json`);
  if (!res.ok) return null;
  const bake = await res.json();

  const [lightTex, envHdr] = await Promise.all([
    new THREE.TextureLoader().loadAsync(base + bake.lightmap.file),
    new RGBELoader().loadAsync(base + bake.environment.file),
  ]);
  lightTex.flipY = false;                  // glTF UV convention
  lightTex.colorSpace = THREE.SRGBColorSpace;
  lightTex.channel = bake.lightmap.uv;     // TEXCOORD_1 -> geometry.attributes.uv1
  envHdr.mapping = THREE.EquirectangularReflectionMapping;
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envMap = pmrem.fromEquirectangular(envHdr).texture;
  envHdr.dispose();
  pmrem.dispose();

  const baked = new Set(bake.lightmap.objects);
  const patched = new Set();

  function applyLightmap(root) {
    let count = 0;
    root.traverse((o) => {
      if (!o.isMesh || !baked.has(o.name) || !o.geometry.attributes.uv1) return;
      o.receiveShadow = false;             // its shadows are already in the bake
      count++;
      const m = o.material;
      if (patched.has(m)) return;
      patched.add(m);
      m.lightMap = lightTex;
      m.lightMapIntensity = bake.lightmap.intensity;
      m.onBeforeCompile = (shader) => {
        shader.fragmentShader = shader.fragmentShader.replace(
          '#include <lights_fragment_maps>',
          [
            'reflectedLight.directDiffuse = vec3( 0.0 );  // baked',
            'irradiance = vec3( 0.0 );',
            '#include <lights_fragment_maps>',
            'iblIrradiance = vec3( 0.0 );',
          ].join('\n'));
      };
      m.customProgramCacheKey = () => 'baked-diffuse';
      m.needsUpdate = true;
    });
    return count;
  }

  return { bake, envMap, applyLightmap };
}
