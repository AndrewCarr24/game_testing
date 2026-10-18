import * as THREE from 'three';

// What the windows look out on, beyond the real lawn / terrace / hedge geometry:
// a procedural sky (horizon-to-zenith gradient, sun glow) with the horizon band from
// blender/levels/horizon.py (tree belts, fields, hills, haze; alpha 0 where sky shows)
// laid over it. One dome mesh, drawn after all opaque geometry so only the pixels
// actually seen through glass are shaded. Also provides a small prefiltered sky
// environment for outdoor materials (lawn, hedge, stone).

const vert = /* glsl */`
varying vec3 vDir;
void main() {
  vDir = position;                       // dome centred on the camera: position = view direction
  vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  gl_Position = p.xyww;                  // on the far plane
}`;

const frag = /* glsl */`
uniform vec3 horizon, zenith, sunDir;
uniform sampler2D band;
uniform float bandScale, latMin, latMax, sinMin, sinMax, hasBand;
varying vec3 vDir;
#define RECIPROCAL_PI2 0.15915494309189535
void main() {
  // cheap on purpose (no trig outside the band, powers by squaring): this runs for every
  // pixel seen through a window, and weak GPUs pay per pixel
  vec3 d = normalize(vDir);
  vec3 col = d.y < 0.0 ? horizon * 0.85 : mix(horizon, zenith, sqrt(d.y));
  float s = max(dot(d, sunDir), 0.0);
  float s8 = s * s; s8 *= s8; s8 *= s8;
  float s256 = s8 * s8; s256 *= s256; s256 *= s256; s256 *= s256; s256 *= s256;
  col += vec3(1.0, 0.92, 0.8) * (0.3 * s8 + 1.5 * s256) + 60.0 * step(0.99989, s);
  if (hasBand > 0.5 && d.y > sinMin && d.y < sinMax) {
    float v = (asin(d.y) - latMin) / (latMax - latMin);
    vec4 b = texture2D(band, vec2(atan(d.z, d.x) * RECIPROCAL_PI2 + 0.5, v));
    col = mix(col, b.rgb * bandScale, b.a);
  }
  gl_FragColor = vec4(col, 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`;

export async function loadSky(url, renderer) {
  const res = await fetch(url);
  if (!res.ok) return null;
  const meta = await res.json();
  const base = url.slice(0, url.lastIndexOf('/levels/') + 1);
  const band = await new THREE.TextureLoader().loadAsync(base + meta.file);
  band.colorSpace = THREE.SRGBColorSpace;
  // no mipmaps: the band is magnified on screen, and without mip selection the u wrap-around
  // (where atan jumps) leaves no seam
  band.generateMipmaps = false;
  band.minFilter = band.magFilter = THREE.LinearFilter;
  band.wrapS = THREE.RepeatWrapping;
  const rad = (deg) => (deg * Math.PI) / 180;
  const material = new THREE.ShaderMaterial({
    vertexShader: vert, fragmentShader: frag, side: THREE.BackSide, depthWrite: false,
    uniforms: {
      horizon: { value: new THREE.Color(...meta.horizon) }, zenith: { value: new THREE.Color(...meta.zenith) },
      sunDir: { value: new THREE.Vector3(...meta.sun).normalize() },
      band: { value: band }, bandScale: { value: meta.scale }, hasBand: { value: 1 },
      latMin: { value: rad(meta.latitude[0]) }, latMax: { value: rad(meta.latitude[1]) },
      sinMin: { value: Math.sin(rad(meta.latitude[0])) }, sinMax: { value: Math.sin(rad(meta.latitude[1])) },
    },
  });
  const dome = new THREE.Mesh(new THREE.SphereGeometry(100, 48, 24), material);
  dome.name = 'Sky';
  dome.frustumCulled = false;
  dome.renderOrder = 1e6;                // after every opaque mesh: shades only what shows through
  dome.onBeforeRender = (r, s, camera) => { dome.position.copy(camera.position); dome.updateMatrixWorld(); };

  // the sky prefiltered as an environment map, for unbaked outdoor materials only (made
  // on first use: with baked grounds nothing needs it)
  let env = null;
  const getEnv = () => {
    if (env) return env;
    const envScene = new THREE.Scene();
    const envDome = new THREE.Mesh(dome.geometry, material.clone());
    envDome.material.uniforms.hasBand.value = 0;   // the band's trees are too far to matter for ambient
    envDome.frustumCulled = false;
    envScene.add(envDome);
    const pmrem = new THREE.PMREMGenerator(renderer);
    env = pmrem.fromScene(envScene, 0, 0.1, 1000).texture;
    pmrem.dispose();
    return env;
  };
  return { dome, getEnv, meta };
}

// Water (pools, fountains, the reflecting pool): the sky's gradient and sun reflected off
// a flat surface with Fresnel, over a deep water colour. No textures, no render targets.
export function waterMaterial(sky) {
  const u = sky.dome.material.uniforms;
  return new THREE.ShaderMaterial({
    uniforms: { horizon: u.horizon, zenith: u.zenith, sunDir: u.sunDir,
                deep: { value: new THREE.Color(0.012, 0.06, 0.07) } },
    vertexShader: /* glsl */`
      varying vec3 vWorld;
      void main() {
        vec4 w = modelMatrix * vec4(position, 1.0);
        vWorld = w.xyz;
        gl_Position = projectionMatrix * viewMatrix * w;
      }`,
    fragmentShader: /* glsl */`
      uniform vec3 horizon, zenith, sunDir, deep;
      varying vec3 vWorld;
      void main() {
        vec3 v = normalize(vWorld - cameraPosition);
        // a gentle, fixed ripple so reflections aren't mirror-perfect
        vec3 n = normalize(vec3(0.02 * sin(vWorld.x * 2.1 + vWorld.z * 0.7), 1.0, 0.02 * sin(vWorld.z * 2.7 - vWorld.x * 0.4)));
        vec3 r = reflect(v, n);
        vec3 sky = mix(horizon, zenith, sqrt(max(r.y, 0.0)));
        float c = 1.0 - max(dot(-v, n), 0.0);
        float c2 = c * c;
        float fres = 0.02 + 0.98 * c2 * c2 * c;
        float s = max(dot(r, sunDir), 0.0);
        float s8 = s * s; s8 *= s8; s8 *= s8;
        float s256 = s8 * s8; s256 *= s256; s256 *= s256; s256 *= s256; s256 *= s256;
        gl_FragColor = vec4(mix(deep, sky, fres) + vec3(4.0) * s256, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}

// Lawn: mowing stripes and slow large-scale variation in world space, so the 3 m texture
// tile doesn't read as a repeat across a 180 m lawn. A few ALU ops on lawn pixels only.
export function addLawnStripes(m) {
  m.onBeforeCompile = (shader) => {
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec2 vLawn;')
      .replace('#include <project_vertex>', '#include <project_vertex>\nvLawn = (modelMatrix * vec4(transformed, 1.0)).xz;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec2 vLawn;')
      .replace('#include <map_fragment>', [
        '#include <map_fragment>',
        'float stripe = step(0.5, fract(vLawn.x / 3.6));',
        'float broad = sin(vLawn.x * 0.043 + 2.0 * sin(vLawn.y * 0.031)) * sin(vLawn.y * 0.057 + 1.3);',
        'diffuseColor.rgb *= mix(0.84, 1.06, stripe) * (1.0 + 0.12 * broad);',
      ].join('\n'));
  };
  m.customProgramCacheKey = () => 'lawn';
  return m;
}

// The grounds (assets/models/<level>_outdoor.gltf, blender/levels/grounds.py). Baked
// (bake.outdoor = vertex-colour scales): lighting is in the vertex colours, so everything is
// drawn unlit - flat: vertex colour x scale; textured: texture x vertex colour x scale -
// with no lights, shadows or environment lookups. Unbaked: the exported PBR materials, lit
// by the real-time sun and the sky.
export function applyOutdoor(root, sky, baked) {
  const cache = new Map();
  root.traverse((o) => {
    if (!o.isMesh) return;
    o.castShadow = false;
    o.receiveShadow = !baked;
    const src = o.material;
    if (cache.has(src)) { o.material = cache.get(src); return; }
    let m;
    if (src.name.startsWith('M_Water')) m = waterMaterial(sky);
    else if (src.name === 'M_Out_Glass') {
      m = new THREE.MeshBasicMaterial({ color: 0x0b0e0e, transparent: true, opacity: 0.22, depthWrite: false });
    } else if (baked) {
      const flat = !src.map;
      m = new THREE.MeshBasicMaterial({ map: src.map, vertexColors: true, name: src.name });
      m.color.copy(flat ? new THREE.Color(1, 1, 1) : src.color).multiplyScalar(flat ? baked.flat : baked.textured);
    } else {
      m = src;
      m.vertexColors = false;
      m.envMap = sky.getEnv();
    }
    if (src.name === 'M_Grounds_Lawn') addLawnStripes(m);
    cache.set(src, m);
    o.material = m;
  });
}
