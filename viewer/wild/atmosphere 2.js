import * as THREE from 'three';

// Fog + aerial perspective shared by every wilderness shader. Distant surfaces fade toward the
// sky colour in the same direction, computed with viewer/sky.js's gradient (horizon -> zenith,
// sun glow), so far ridges melt into the dome without a seam. Exponential height fog: denser
// in valleys, thinner on ridges (analytic integral along the view ray, no loops).

export function atmosphereUniforms(sky) {
  const u = sky.dome.material.uniforms;
  const meta = sky.meta;
  return {
    uHorizon: u.horizon, uZenith: u.zenith, uSunDir: u.sunDir,
    uHaze: { value: new THREE.Color(...(meta.haze || [0.82, 0.7, 0.6])) },
    uFogDensity: { value: 0.0007 },     // per metre at the fog base height
    uFogFalloff: { value: 0.006 },      // per metre of height
    uFogBase: { value: 0.0 },
    uTime: { value: 0 },
    // physical haze (uHazeMode 1): uniform extinction (3.912 / visual range), air light from
    // hazeAlong(): blue away from the sun, peach toward it (the wild sky's horizon uses the same)
    uHazeMode: { value: 0 },
    uExt: { value: 3.912 / 32000 },
    uHazeAway: { value: new THREE.Color(0.27, 0.38, 0.55) },
    uHazeSun: { value: new THREE.Color(0.79, 0.55, 0.33) },
    uHazeScale: { value: 1.25 },
    // forest air (a level, under the canopy): the humid cove's own scatter, a dim green-grey that
    // separates the trunks in depth; strength from the forest under the camera (main.js), 0 = off
    uForestAir: { value: new THREE.Color(0.05, 0.065, 0.05) }, uForestAirK: { value: 0 },
  };
}

export const ATMOSPHERE_PARS = /* glsl */`
uniform vec3 uHorizon, uZenith, uSunDir, uHaze, uHazeAway, uHazeSun;
uniform float uFogDensity, uFogFalloff, uFogBase, uTime, uHazeMode, uExt, uHazeScale, uForestAirK;
uniform vec3 uForestAir;
vec3 hazeAlong(vec3 d) {
  float s = max(dot(normalize(vec3(d.x, 0.0, d.z) + 1e-5), normalize(vec3(uSunDir.x, 0.0, uSunDir.z))), 0.0);
  return mix(uHazeAway, uHazeSun, s * s * s) * uHazeScale;
}
vec3 skyAlong(vec3 d) {
  vec3 col = mix(uHorizon, uZenith, sqrt(max(d.y, 0.0)));
  float s = max(dot(d, uSunDir), 0.0);
  float s8 = s * s; s8 *= s8; s8 *= s8;
  return col + vec3(1.0, 0.92, 0.8) * 0.3 * s8;
}
vec3 applyAtmosphere(vec3 col, vec3 worldPos) {
  vec3 v = worldPos - cameraPosition;
  float dist = length(v);
  vec3 d = v / max(dist, 1e-3);
  if (uHazeMode > 0.5) {
    // aerial perspective, no fog: T = exp(-ext * d) (32 km visual range: 0.89 at 1 km, 0.38 at 8 km)
    col = mix(col, uForestAir, uForestAirK * (1.0 - exp(-dist / 160.0)) * (1.0 - smoothstep(150.0, 400.0, dist)));
    return mix(hazeAlong(d), col, exp(-uExt * dist));
  }
  float k = uFogFalloff * v.y;
  float rel = abs(k) > 1e-4 ? (1.0 - exp(-k)) / k : 1.0;
  float od = uFogDensity * exp(-uFogFalloff * (cameraPosition.y - uFogBase)) * dist * rel;
  float f = 1.0 - exp(-od);
  // haze near the ground, the sky's own colour toward the horizon line
  vec3 fogCol = mix(uHaze, skyAlong(vec3(d.x, max(d.y, 0.0), d.z)), 0.65);
  return mix(col, fogCol, f);
}`;

// shared lighting for everything lit by the low golden sun (no three.js lights: unlit
// materials with the sun and sky folded in, as the grounds' baked materials are)
export const LIGHT_PARS = /* glsl */`
uniform vec3 uSunColor, uSkyColor;
vec3 lightFoliage(vec3 n, float sunVis, float skyVis, float wrap) {
  float ndl = clamp((dot(n, uSunDir) + wrap) / (1.0 + wrap), 0.0, 1.0);
  return uSunColor * ndl * sunVis + uSkyColor * skyVis * (0.6 + 0.4 * n.y);
}`;

export function lightUniforms(meta) {
  // calibrated by eye against the mansion's lawn: sun = colour x strength / pi, sky = the
  // bake's sky light
  const sc = new THREE.Color(...(meta.sun_color || [1, 0.7, 0.45])).multiplyScalar((meta.sun_strength || 6) / Math.PI);
  // (shadowed ground also gets warm bounce light from the sunlit terrain around it: the sky
  // term is nudged toward the haze colour so shade reads grey-blue, not navy)
  const kc = new THREE.Color(...(meta.light || [0.42, 0.52, 0.72])).lerp(new THREE.Color(...(meta.haze || [0.82, 0.7, 0.6])), 0.35)
    .multiplyScalar((meta.light_strength || 0.85) * 0.9);
  return { uSunColor: { value: sc }, uSkyColor: { value: kc } };
}
