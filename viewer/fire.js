import * as THREE from 'three';

// Live fire: meshes tagged fx="fire" in the asset (a flat card, UV 0..1 across and up; see
// blender/assets/living_fireplace.py) are drawn with an animated flame shader: a row of
// licking tongues, rising turbulence, a blue root, a red-orange-yellow body, additive so the
// layers glow through each other. One draw call per card, no textures, no real-time light
// (the fire's average glow on the hearth is in the bake).

const vertexShader = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }`;

const fragmentShader = /* glsl */ `
  #include <common>
  uniform float uTime, uSeed, uAspect, uStrength, uRed;
  varying vec2 vUv;
  float hash21(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }
  float vnoise(vec2 p) {
    vec2 i = floor(p), f = fract(p), u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash21(i), hash21(i + vec2(1, 0)), u.x), mix(hash21(i + vec2(0, 1)), hash21(i + vec2(1, 1)), u.x), u.y);
  }
  float fbm(vec2 p) {
    float v = 0.0, a = 0.5;
    for (int i = 0; i < 4; i++) { v += a * vnoise(p); p = p * 2.03 + 17.1; a *= 0.5; }
    return v;
  }
  void main() {
    float t = uTime, y = 1.0 - vUv.y;                 // glTF flips V: 0 is the card top
    float x = vUv.x * uAspect + uSeed * 7.3;          // card heights across: the noise stays round
    // the whole sheet sways a little, more towards the tips
    x += (fbm(vec2(x * 0.9, y * 1.2 - t * 0.5)) - 0.5) * 0.5 * y;
    // each tongue's height wanders on its own clock; the flames die down towards the burner's ends
    float u = vUv.x;
    float ends = sqrt(smoothstep(0.0, 0.12, u) * smoothstep(1.0, 0.88, u));
    float h = (0.3 + 0.75 * fbm(vec2(x * 2.2, t * 0.6 + uSeed))) * ends + 1e-3;
    // turbulence rising through the body
    float n = fbm(vec2(x * 5.0, y * 3.2 - t * 2.6));
    float heat = 1.0 - y / h + (n - 0.5) * 1.1 * y;
    // a continuous sheet at the burner splitting into separate licks higher up
    float licks = smoothstep(0.3, 0.72, fbm(vec2(x * 6.5, y * 1.6 - t * 2.0)));
    heat *= mix(1.0, 0.3 + 0.95 * licks, smoothstep(0.05, 0.45, y / h));
    heat *= 0.8 + 0.4 * fbm(vec2(x * 9.0, y * 6.0 - t * 4.0));
    heat = clamp(heat, 0.0, 1.0) * smoothstep(0.0, 0.03, u) * smoothstep(1.0, 0.97, u);
    // colour by heat: deep red edges, orange body, yellow-white core; blue at the burner
    vec3 col = mix(vec3(0.55, 0.04, 0.0), vec3(1.0, 0.32, 0.02), smoothstep(0.02, 0.35, heat));
    col = mix(col, vec3(1.0, 0.62, 0.14), smoothstep(0.4, 0.8, heat) * (1.0 - uRed));
    col = mix(col, vec3(1.0, 0.9, 0.65), smoothstep(0.88, 1.0, heat) * (1.0 - uRed));
    float root = 1.0 - smoothstep(0.0, 0.07, y);
    col = mix(col, vec3(0.12, 0.25, 1.0), root * 0.7);
    float glow = smoothstep(0.0, 0.25, heat) * (0.55 + 0.45 * heat) * (1.0 - root * 0.5);
    gl_FragColor = vec4(col * glow * uStrength, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }`;

export class Fire {
  constructor() {
    this.time = { value: 0 };
    this.cards = [];
  }

  // swap every fire card under `root` for the flame shader (call before batching: the
  // material is transparent, so the batcher leaves it alone)
  collect(root) {
    root.traverse((o) => {
      if (!o.isMesh || o.userData.fx !== 'fire') return;
      const seed = o.userData.seed ?? 0;
      o.material = new THREE.ShaderMaterial({
        vertexShader, fragmentShader,
        uniforms: {
          uTime: this.time, uSeed: { value: seed }, uAspect: { value: o.userData.aspect ?? 3 },
          // the back layer is taller and redder, the front one brighter
          uStrength: { value: seed === 1 ? 1.2 : 1.9 }, uRed: { value: seed === 1 ? 0.45 : 0 },
        },
        transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
      });
      o.castShadow = o.receiveShadow = false;
      this.cards.push(o);
    });
  }

  // a fixed time when a benchmark or screenshot drives the frame, so their images repeat
  update(dt, frozen = false) {
    this.time.value = frozen ? 1.5 : this.time.value + dt;
  }
}
