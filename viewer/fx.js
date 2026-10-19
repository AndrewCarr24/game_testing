import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { SMAAPass } from 'three/addons/postprocessing/SMAAPass.js';

// Screen-space effects for the "archviz" look (?fx=1), each cheap enough for a web game:
// - contact shadows: GTAO at half resolution, normals reconstructed from the main pass's
//   depth (no second geometry pass, so no extra draw calls), so furniture sits on the
//   floor and darkens into the corners it touches;
// - glow: a low, half-resolution bloom on what's brighter than white (bulbs, fire,
//   sunlit glass), the cue the eye reads as real light;
// - tone mapping + sRGB at the end (the scene renders linear HDR into a half-float target).
// Anti-aliasing: SMAA at the end by default (msaa = 0). A multisampled half-float target
// looks the same but its resolve cost more than all the effects together (M4: ~1 ms).

const OutputShader = {
  uniforms: { tDiffuse: { value: null } },
  vertexShader: /* glsl */ `
    varying vec2 vUv;
    void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
  fragmentShader: /* glsl */ `
    // three prepends the tone curves only when this pass draws to the screen (SMAA may
    // come after it); colorspace_pars (sRGBTransferOETF) is always there
    #ifndef TONE_MAPPING
    #include <tonemapping_pars_fragment>
    #endif
    uniform sampler2D tDiffuse;
    varying vec2 vUv;
    void main() {
      gl_FragColor = texture2D(tDiffuse, vUv);
      #if defined(TM_AGX)
        gl_FragColor.rgb = AgXToneMapping(gl_FragColor.rgb);
      #elif defined(TM_ACES)
        gl_FragColor.rgb = ACESFilmicToneMapping(gl_FragColor.rgb);
      #else
        gl_FragColor.rgb = CustomToneMapping(gl_FragColor.rgb);
      #endif
      gl_FragColor = sRGBTransferOETF(gl_FragColor);
    }`,
};

export function createFx(renderer, scene, camera, { ao = true, bloom = true, aoScale = 4, aoSamples = 4, msaa = 0 } = {}) {
  const size = renderer.getDrawingBufferSize(new THREE.Vector2());
  const target = new THREE.WebGLRenderTarget(size.x, size.y, {
    type: THREE.HalfFloatType, samples: msaa,
    depthTexture: new THREE.DepthTexture(size.x, size.y, THREE.UnsignedIntType),
  });
  const composer = new EffectComposer(renderer, target);
  composer.setPixelRatio(1);                  // sizes below are drawing-buffer pixels already
  composer.addPass(new RenderPass(scene, camera));

  let gtao = null;
  if (ao) {
    gtao = new GTAOPass(scene, camera, Math.ceil(size.x / aoScale), Math.ceil(size.y / aoScale));
    // read the main pass's depth (normals from depth): the pass's own normal render
    // would draw the whole scene a second time
    gtao.setGBuffer(composer.renderTarget1.depthTexture);
    gtao.updateGtaoMaterial({ radius: 0.35, distanceExponent: 1.5, thickness: 1.2, scale: 1.0, samples: aoSamples });
    gtao.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 6, rings: 2, samples: Math.min(aoSamples, 8) });
    gtao.blendIntensity = 0.85;
    composer.addPass(gtao);
  }
  let glow = null;
  if (bloom) {
    glow = new UnrealBloomPass(new THREE.Vector2(size.x / 2, size.y / 2), 0.22, 0.5, 1.6);
    composer.addPass(glow);
  }
  const out = new ShaderPass(OutputShader);
  const tm = renderer.toneMapping;
  out.material.defines = tm === THREE.AgXToneMapping ? { TM_AGX: '' } : tm === THREE.ACESFilmicToneMapping ? { TM_ACES: '' } : {};
  composer.addPass(out);
  const smaa = msaa ? null : new SMAAPass(size.x, size.y);
  if (smaa) composer.addPass(smaa);

  // quality levels, highest first: 2 = contact shadows + glow, 1 = glow, 0 = no effects
  // (the scene drawn straight to the screen with its own MSAA, as before fx), -1 = that at
  // a 1x pixel ratio. fx.level starts at the highest one this setup has.
  const fx = {
    composer,
    level: gtao ? 2 : glow ? 1 : 0,
    setLevel(level) {
      fx.level = level;
      if (gtao) gtao.enabled = level >= 2;
      if (glow) glow.enabled = level >= 1;
      const ratio = level >= 0 ? Math.min(window.devicePixelRatio, 1.5) : 1;
      if (renderer.getPixelRatio() !== ratio) { renderer.setPixelRatio(ratio); fx.setSize(); }
    },
    render() {
      if (fx.level <= 0) { renderer.render(scene, camera); return; }
      // count every pass's draws (the renderer resets its counters per render call)
      renderer.info.autoReset = false;
      renderer.info.reset();
      composer.render();
      renderer.info.autoReset = true;
    },
    setSize() {
      const s = renderer.getDrawingBufferSize(new THREE.Vector2());
      composer.setSize(s.x, s.y);
      gtao?.setSize(Math.ceil(s.x / aoScale), Math.ceil(s.y / aoScale));
      glow?.setSize(s.x / 2, s.y / 2);
      smaa?.setSize(s.x, s.y);
    },
  };
  return fx;
}

// Steps quality down while the game can't hold ~50 fps: averaged over 2 s windows (from
// 4 s after the load, so loading hitches don't count), one level per window, never back up
// (no flapping). Off when ?q= fixes the level, and under benchmarks (window.__bench).
export function governor(fx, { fps = 50, delay = 4000, window: span = 2000 } = {}) {
  let start = 0, frames = 0;
  const begin = performance.now() + delay;
  return (now) => {
    if (!fx || fx.level < 0 || window.__bench || now < begin) return;
    if (!start) { start = now; frames = 0; return; }
    frames++;
    if (now - start < span) return;
    const ms = (now - start) / frames;
    start = now; frames = 0;
    if (ms > 1000 / fps) {
      fx.setLevel(fx.level - 1);
      console.log(`quality: ${ms.toFixed(1)} ms/frame -> level ${fx.level}`);
    }
  };
}
