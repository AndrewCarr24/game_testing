import * as THREE from 'three';
import { ATMOSPHERE_PARS } from './atmosphere.js';

// The wilderness sky: viewer/sky.js's golden-hour gradient and sun (the colours of
// assets/levels/mansion_sky.json, so the house and the cove share one evening), with the
// horizon in the haze's own colour (hazeAlong: blue away from the sun, peach toward it) and,
// instead of the house's rendered horizon band, layered ridges: N ridgelines at 3-21 km, each a
// noise silhouette over azimuth, coloured by aerial perspective at its distance (T = exp(-ext d)),
// so ridge after ridge goes paler and bluer. They sit beyond the 4.6 km backdrop ring; the eye
// height and the earth's curvature set where each one meets the sky. One dome mesh named 'Sky',
// drawn last on the far plane.

export function makeWildSky(meta, uniforms, { layers = null } = {}) {
  const L = layers || [
    // distance m, base height m (over the estate lawn = 1,040 m asl), amplitude m, wavelength
    // (radians of azimuth). Blue Ridge crests at 3-50 km run 900-1,900 m asl: from the lookouts
    // (+174..+255) the near ones sit below the eye and each farther one peeks over the last,
    // converging on the horizon (the ring's own two ridges behind the house come first)
    [3300, -10, 120, 0.45], [4600, 25, 130, 0.55], [6400, 60, 140, 0.7], [9200, 100, 155, 0.85],
    [13500, 150, 170, 1.05], [21000, 230, 200, 1.35], [32000, 360, 240, 1.7], [48000, 560, 280, 2.2]];
  const material = new THREE.ShaderMaterial({
    uniforms: {
      ...uniforms,
      uZenithW: { value: new THREE.Color(...meta.zenith) },
      uLayers: { value: L.map((l) => new THREE.Vector4(...l)) },
      uRidgeCol: { value: new THREE.Color(0.045, 0.062, 0.05) },
    },
    side: THREE.BackSide, depthWrite: false,
    vertexShader: /* glsl */`
      varying vec3 vDir;
      void main() {
        vDir = position;
        vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        gl_Position = p.xyww;
      }`,
    fragmentShader: /* glsl */`
      uniform vec3 uZenithW, uRidgeCol;
      uniform vec4 uLayers[${L.length}];
      varying vec3 vDir;
      ${ATMOSPHERE_PARS}
      float h1(float n) { return fract(sin(n * 127.1) * 43758.5453); }
      float vnoise(float x) { float i = floor(x), f = fract(x); f = f * f * (3.0 - 2.0 * f); return mix(h1(i), h1(i + 1.0), f); }
      // old, rounded mountains: soft-crested fBm, not the alpine ridged kind
      float ridgeShape(float a, float k) {
        float s = 0.0, amp = 0.55, fr = 1.0;
        for (int o = 0; o < 4; o++) { s += amp * vnoise(a * fr + k * 17.3 + float(o) * 5.1); amp *= 0.5; fr *= 2.3; }
        return s;
      }
      void main() {
        vec3 d = normalize(vDir);
        vec3 col = mix(hazeAlong(d), uZenithW, sqrt(max(d.y, 0.0)));
        float s = max(dot(d, uSunDir), 0.0);
        float s8 = s * s; s8 *= s8; s8 *= s8;
        float s256 = s8 * s8; s256 *= s256; s256 *= s256; s256 *= s256; s256 *= s256;
        col += vec3(1.0, 0.92, 0.8) * (0.3 * s8 + 1.5 * s256) + 60.0 * step(0.99989, s);
        if (d.y < 0.09) {
          float az = atan(d.z, d.x);
          float el = asin(clamp(d.y, -1.0, 1.0));
          for (int k = 0; k < ${L.length}; k++) {
            vec4 l = uLayers[k];
            float crest = l.y + l.z * ridgeShape(az / l.w * 6.0, float(k));
            float h = crest - cameraPosition.y - l.x * l.x / 12742000.0;
            float top = atan(h, l.x);
            if (el < top) {
              float T = exp(-uExt * l.x);
              // the near layers' sunward slopes catch a little of the low sun; each crest reads as
              // a dark line and the haze pools in the valley below it (the layered Blue Ridge look)
              vec3 rc = uRidgeCol * (1.0 + 0.8 * s * s);
              float below = (top - el) * l.x / max(l.z, 1.0);          // metres under the crest / amplitude
              float pool = smoothstep(0.15, 1.6, below);
              vec3 hz = hazeAlong(d);
              col = mix(hz, rc, T * (1.0 - 0.55 * pool));
              col = mix(col, hz * 1.06, 0.18 * pool * (1.0 - T));
              break;
            }
          }
        }
        // (a hair of noise against 8-bit banding in the smooth gradient)
        col += (fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453) - 0.5) * 0.004;
        gl_FragColor = vec4(col, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
  const dome = new THREE.Mesh(new THREE.SphereGeometry(100, 64, 32), material);
  dome.name = 'Sky';
  dome.frustumCulled = false;
  dome.renderOrder = 1e6;                // after every opaque mesh (as sky.js)
  dome.onBeforeRender = (r, sc, cam) => { dome.position.copy(cam.position); dome.updateMatrixWorld(); };
  return { dome, material };
}
