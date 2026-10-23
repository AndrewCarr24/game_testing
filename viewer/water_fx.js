import * as THREE from 'three';

// The bathhouse's water (blender/assets/ph_*.py; design/grounds/pool_house.md), like fire.js:
// meshes tagged `fx` in the asset are given a shader at load, before batching (all of them are
// transparent, so the batcher leaves them alone). No textures but one 128² ripple normal map made
// here, no real-time lights; the time freezes under window.__bench so shots repeat.
//   fx = "water"      a pool's surface: its own (room-lit, box-projected) material, made
//                     see-through looking down and a mirror at a grazing angle (Fresnel alpha),
//                     with two ripple layers drifting across each other
//   fx = "caustics"   light off / through moving water: an additive card on a wall or a pool
//                     floor (userData: aspect = width / height, scale = cells per metre,
//                     color, strength, stretch = vertical stretch)
//   fx = "underwater" the secret stair's window into the pool: the card looks INTO a box of
//                     water (userData.box = [x0, y0, z0, x1, y1, z1], glTF, the pool's inside up to
//                     its surface): the view ray is followed to the wall, floor or surface it meets
//                     (caustics on the stone, the surface's silver mirror outside Snell's window,
//                     the light above inside it), fogged teal by the distance it went
//   fx = "steam"      drifting vapour: additive soft noise (the hot pool, the steam room)

const NOISE = /* glsl */ `
  float wHash(vec2 p) { p = fract(p * vec2(127.1, 311.7)); p += dot(p, p + 19.19); return fract(p.x * p.y); }
  float wNoise(vec2 p) {
    vec2 i = floor(p), f = fract(p), u = f * f * (3.0 - 2.0 * f);
    return mix(mix(wHash(i), wHash(i + vec2(1, 0)), u.x), mix(wHash(i + vec2(0, 1)), wHash(i + vec2(1, 1)), u.x), u.y);
  }
  float wFbm(vec2 p) { float v = 0.0, a = 0.5; for (int i = 0; i < 4; i++) { v += a * wNoise(p); p = p * 2.07 + 13.7; a *= 0.5; } return v; }
  // caustic network: two ridged noise layers over a slowly warped domain; where their ridges
  // cross the light gathers into bright knots joined by thin filaments
  float caustic(vec2 p, float t) {
    vec2 q = p + 0.55 * vec2(wFbm(p * 0.7 + t * 0.11), wFbm(p * 0.7 - t * 0.09 + 7.3));
    float r1 = 1.0 - abs(wNoise(q * 1.9 + vec2(t * 0.21, -t * 0.13)) * 2.0 - 1.0);
    float r2 = 1.0 - abs(wNoise(q * 2.7 + vec2(-t * 0.17, t * 0.19) + 3.1) * 2.0 - 1.0);
    return pow(r1, 5.0) * 0.6 + pow(r1 * r2, 7.0) * 1.6;
  }
`;

const cardVertex = /* glsl */ `
  varying vec2 vUv;
  varying vec3 vWorld;
  void main() {
    vUv = uv;
    vec4 w = modelMatrix * vec4(position, 1.0);
    vWorld = w.xyz;
    gl_Position = projectionMatrix * viewMatrix * w;
  }`;

const causticsFragment = /* glsl */ `
  #include <common>
  uniform float uTime, uAspect, uScale, uStrength, uStretch, uSeed;
  uniform vec3 uColor;
  varying vec2 vUv;
  ${NOISE}
  void main() {
    vec2 p = vec2(vUv.x * uAspect, (1.0 - vUv.y) / uStretch) * uScale + uSeed * 11.0;
    float c = caustic(p, uTime);
    // soft edges, so the card has no outline on the wall
    float e = smoothstep(0.0, 0.12, vUv.x) * smoothstep(1.0, 0.88, vUv.x) * smoothstep(0.0, 0.18, vUv.y) * smoothstep(1.0, 0.8, vUv.y);
    // and the pattern breathes: the surface's gusts
    float g = 0.75 + 0.25 * sin(uTime * 0.37 + vUv.x * 3.0) * sin(uTime * 0.23 - vUv.y * 2.0);
    gl_FragColor = vec4(uColor * c * e * g * uStrength, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }`;

const underwaterFragment = /* glsl */ `
  #include <common>
  uniform float uTime;
  uniform vec3 uBoxMin, uBoxMax, uStone, uDeep, uAbove, uSun;
  varying vec2 vUv;
  varying vec3 vWorld;
  ${NOISE}
  void main() {
    vec3 rd = normalize(vWorld - cameraPosition);
    vec3 ro = vWorld + rd * 0.002;
    vec3 tA = (uBoxMin - ro) / rd, tB = (uBoxMax - ro) / rd;
    vec3 tFar = max(tA, tB);
    float t = min(min(tFar.x, tFar.y), tFar.z);
    vec3 hit = ro + rd * t;
    float surface = uBoxMax.y;
    vec3 col;
    float rip = wFbm(hit.xz * 1.3 + uTime * 0.25);
    if (tFar.y <= t + 1e-4 && rd.y > 0.0) {
      // the surface from below: Snell's window straight up (the hall's light), a mirror outside it
      float inside = smoothstep(0.62, 0.7, rd.y + (rip - 0.5) * 0.08);
      vec3 mirror = mix(uDeep * 1.6, uStone * 0.5, 0.3) * (0.7 + 0.6 * rip);
      col = mix(mirror, uAbove * (0.8 + 0.4 * rip), inside);
    } else {
      // stone: lit from above through the moving surface (caustics, strongest near the top and
      // on the floor), darker with depth
      vec2 q = abs(rd.y) > 0.5 || tFar.y <= t + 1e-4 ? hit.xz : vec2(hit.x + hit.z, hit.y * 1.6);
      float depth = clamp((surface - hit.y) / max(surface - uBoxMin.y, 0.1), 0.0, 1.0);
      float c = caustic(q * 2.2, uTime * 0.8);
      // tile joints (the pool's 0.3 m stone courses)
      vec2 g = abs(fract((abs(rd.y) > 0.5 ? hit.xz : vec2(hit.x + hit.z, hit.y)) / 0.3) - 0.5);
      float joint = smoothstep(0.47, 0.5, max(g.x, g.y));
      col = uStone * (1.0 - 0.35 * joint) * (0.55 + 0.45 * (1.0 - depth)) + uSun * c * (0.35 + 0.65 * (1.0 - depth * 0.7));
    }
    // a few faint shafts of light hanging in the water
    float shafts = 0.0;
    for (int i = 1; i <= 5; i++) {
      vec3 s = ro + rd * (t * float(i) / 6.0);
      shafts += caustic(vec2(s.x * 0.9 + s.y * 0.35, s.z * 0.9) * 1.2, uTime * 0.5) * smoothstep(uBoxMin.y, surface, s.y);
    }
    col += uSun * shafts * 0.035;
    // the water itself: absorbed red first, so far things go teal
    float fog = 1.0 - exp(-t * 0.16);
    col = mix(col * vec3(0.55, 0.85, 0.95), uDeep, fog);
    gl_FragColor = vec4(col, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }`;

const steamFragment = /* glsl */ `
  #include <common>
  uniform float uTime, uAspect, uStrength, uSeed;
  uniform vec3 uColor;
  varying vec2 vUv;
  ${NOISE}
  void main() {
    float y = 1.0 - vUv.y;
    vec2 p = vec2(vUv.x * uAspect, y) * 2.2 + vec2(uSeed * 5.0, -uTime * 0.12);
    float n = wFbm(p + vec2(wFbm(p * 0.6 + uTime * 0.05), 0.0));
    float d = smoothstep(0.35, 0.85, n);
    float e = smoothstep(0.0, 0.2, vUv.x) * smoothstep(1.0, 0.8, vUv.x) * smoothstep(0.0, 0.25, y) * smoothstep(1.0, 0.55, y);
    gl_FragColor = vec4(uColor * d * e * uStrength, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }`;

// a tileable ripple normal map: a few crossing wave trains of small amplitude
function rippleMap(n = 128) {
  const data = new Uint8Array(n * n * 4);
  const waves = [[3, 1, 0.9], [-2, 3, 0.7], [5, -2, 0.45], [1, 6, 0.35], [-7, -3, 0.25], [9, 4, 0.18]];
  for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) {
    let dx = 0, dy = 0;
    for (const [kx, ky, a] of waves) {
      const ph = 2 * Math.PI * (kx * i + ky * j) / n;
      dx += a * kx * Math.cos(ph); dy += a * ky * Math.cos(ph);
    }
    const s = 0.06, nx = -dx * s, ny = -dy * s, l = Math.hypot(nx, ny, 1);
    const k = (j * n + i) * 4;
    data[k] = (nx / l * 0.5 + 0.5) * 255; data[k + 1] = (ny / l * 0.5 + 0.5) * 255; data[k + 2] = (1 / l * 0.5 + 0.5) * 255; data[k + 3] = 255;
  }
  const t = new THREE.DataTexture(data, n, n);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.magFilter = THREE.LinearFilter; t.minFilter = THREE.LinearMipmapLinearFilter; t.generateMipmaps = true;
  t.needsUpdate = true;
  return t;
}

const v3 = (a, d) => new THREE.Color(...(a ?? d));

export class WaterFx {
  constructor() {
    this.time = { value: 0 };
    this.count = 0;
    this.ripples = null;
  }

  collect(root) {
    root.traverse((o) => {
      if (!o.isMesh || !o.userData.fx) return;
      const fx = o.userData.fx;
      if (fx === 'water') this.water(o);
      else if (fx === 'caustics') this.card(o, causticsFragment, {
        uAspect: { value: o.userData.aspect ?? 1 }, uScale: { value: o.userData.scale ?? 2.5 },
        uStrength: { value: o.userData.strength ?? 0.5 }, uStretch: { value: o.userData.stretch ?? 1.0 },
        uSeed: { value: o.userData.seed ?? 0 }, uColor: { value: v3(o.userData.color, [1.0, 0.78, 0.5]) },
      });
      else if (fx === 'steam') this.card(o, steamFragment, {
        uAspect: { value: o.userData.aspect ?? 1 }, uStrength: { value: o.userData.strength ?? 0.12 },
        uSeed: { value: o.userData.seed ?? 0 }, uColor: { value: v3(o.userData.color, [1.0, 0.95, 0.9]) },
      });
      else if (fx === 'underwater') {
        const b = o.userData.box ?? [0, -1, 0, 1, 0, 1];
        this.card(o, underwaterFragment, {
          uBoxMin: { value: new THREE.Vector3(b[0], b[1], b[2]) }, uBoxMax: { value: new THREE.Vector3(b[3], b[4], b[5]) },
          uStone: { value: v3(o.userData.stone, [0.09, 0.12, 0.11]) }, uDeep: { value: v3(o.userData.deep, [0.006, 0.05, 0.06]) },
          uAbove: { value: v3(o.userData.above, [0.9, 0.75, 0.55]) }, uSun: { value: v3(o.userData.sun, [0.75, 0.85, 0.75]) },
        }, false);
      }
    });
  }

  card(o, fragmentShader, uniforms, additive = true) {
    o.material = new THREE.ShaderMaterial({
      vertexShader: cardVertex, fragmentShader, uniforms: { uTime: this.time, ...uniforms },
      transparent: additive, depthWrite: !additive, blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
      side: THREE.FrontSide,
    });
    o.castShadow = o.receiveShadow = false;
    if (additive) o.renderOrder = 2;
    this.count++;
  }

  // the pools' surfaces keep their room-lit material (baked.js: SH + the box-projected panorama)
  water(o) {
    this.ripples ??= rippleMap();
    const m = o.material.clone();
    m.normalMap = this.ripples;
    m.normalScale = new THREE.Vector2(0.35, 0.35);
    m.transparent = true;
    m.depthWrite = false;
    const prev = m.onBeforeCompile, prevKey = m.customProgramCacheKey?.bind(m);
    const time = this.time, tile = o.userData.tile ?? 1.6;
    m.onBeforeCompile = (shader, renderer) => {
      prev?.call(m, shader, renderer);
      shader.uniforms.uWaterTime = time;
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', '#include <common>\nuniform float uWaterTime;')
        .replace('vec3 mapN = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;', [
          `vec2 wUv = vNormalMapUv / ${tile.toFixed(3)};`,
          'vec3 mapN = texture2D( normalMap, wUv + uWaterTime * vec2( 0.011, 0.006 ) ).xyz * 2.0 - 1.0;',
          'mapN.xy += ( texture2D( normalMap, wUv * 1.73 + vec2( 0.37, 0.61 ) - uWaterTime * vec2( 0.007, -0.009 ) ).xy * 2.0 - 1.0 ) * 0.8;',
        ].join('\n'))
        .replace('#include <opaque_fragment>', [
          // looking straight down you see into the water (its floor, its caustics); at a grazing
          // angle it's a mirror of the room
          'float wFres = pow( 1.0 - clamp( abs( dot( normal, normalize( vViewPosition ) ) ), 0.0, 1.0 ), 4.0 );',
          'diffuseColor.a = mix( diffuseColor.a, 1.0, wFres );',
          '#include <opaque_fragment>',
        ].join('\n'));
    };
    m.customProgramCacheKey = () => (prevKey ? prevKey() : '') + '|bath-water';
    m.needsUpdate = true;
    o.material = m;
    o.renderOrder = 1;
    o.castShadow = false;
    this.count++;
  }

  update(dt, frozen = false) {
    if (!frozen) this.time.value += dt;
  }
}
