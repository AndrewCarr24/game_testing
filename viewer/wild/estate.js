import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { ATMOSPHERE_PARS } from './atmosphere.js';
import { GATE, OFFSET_Z, STATE_KEY, splitGateLeaves, setLeaves, linkRegistry, splitOuterLawn, HAY_GLSL } from '../estate_link.js';

// The real estate in the wilderness (design/wilderness/estate_link.md), replacing level.js's
// stand-in boxes: the house level's own exported grounds (assets/models/mansion_outdoor.gltf:
// the facades and roofs, terrace, hedge, gate, pool and pool house, every zone's planting and
// furniture, with the house's baked lighting in its vertex colours) and the shell's glazing
// (mansion_shell.gltf, its glass and frames only: the interior isn't loaded). Placed exactly where
// the house level has it (wild z = house z - 810). Drawn as the house draws its grounds (unlit:
// texture x baked vertex colour x the bake's scale) plus the wilderness's aerial perspective, so
// it reads the same at the gate and fades into the haze from the lookouts. Glass: opaque, dark,
// the sky in it by Fresnel. ~76k triangles, ~11 draw calls, 1.7 MB.
//   ?estate=0  the stand-in again        ?estate=far  skip the textures (flat colours)
// The gate: its leaves are split out and stand open; walking in through it goes back to the house
// (window.__wildGate, used by the house's estate_gate.js when this page runs in its iframe).

const VERT = /* glsl */`
  attribute vec3 color;
  varying vec3 vWorld, vCol, vN; varying vec2 vUv;
  void main() {
    vec4 w = modelMatrix * vec4(position, 1.0);
    vWorld = w.xyz; vCol = color; vUv = uv; vN = normalize(mat3(modelMatrix) * normal);
    gl_Position = projectionMatrix * viewMatrix * w;
  }`;

function groundsMaterial(uniforms, src, bake, lawn, hay = false) {
  const textured = !!src.map;
  return new THREE.ShaderMaterial({
    uniforms: { ...uniforms, tMap: { value: src.map || null }, uScale: { value: textured ? bake.textured : bake.flat },
      uBase: { value: textured ? src.color.clone() : new THREE.Color(1, 1, 1) }, uWorldZ: { value: -OFFSET_Z } },
    defines: { ...(textured ? { USE_TMAP: 1 } : {}), ...(lawn && !hay ? { LAWN: 1 } : {}), ...(hay ? { HAY: 1 } : {}) },
    vertexShader: VERT,
    fragmentShader: /* glsl */`
      uniform sampler2D tMap; uniform float uScale, uWorldZ; uniform vec3 uBase;
      varying vec3 vWorld, vCol, vN; varying vec2 vUv;
      ${ATMOSPHERE_PARS}
      ${HAY_GLSL}
      void main() {
        vec3 c = uBase * vCol * uScale;
        #ifdef USE_TMAP
          c *= texture2D(tMap, vUv).rgb;
        #endif
        #ifdef LAWN
          // the house's mowing stripes (sky.js addLawnStripes), in the house's own frame
          vec2 p = vec2(vWorld.x, vWorld.z + uWorldZ);
          float stripe = step(0.5, fract(p.x / 3.6));
          float broad = sin(p.x * 0.043 + 2.0 * sin(p.y * 0.031)) * sin(p.y * 0.057 + 1.3);
          c *= mix(0.84, 1.06, stripe) * (1.0 + 0.12 * broad);
        #endif
        #ifdef HAY
          c = hay(c, vec2(vWorld.x, vWorld.z + uWorldZ));
        #endif
        gl_FragColor = vec4(applyAtmosphere(c, vWorld), 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
    // (the estate lies on the cove's terrain held at lawn height: it wins the tie)
    polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -2,
  });
}

function glassMaterial(uniforms, tint = 0.02) {
  return new THREE.ShaderMaterial({
    uniforms: { ...uniforms, uTint: { value: tint } },
    vertexShader: VERT.replace('attribute vec3 color;', '').replace('vCol = color;', 'vCol = vec3(1.0);'),
    fragmentShader: /* glsl */`
      uniform float uTint;
      varying vec3 vWorld, vCol, vN; varying vec2 vUv;
      ${ATMOSPHERE_PARS}
      void main() {
        vec3 v = normalize(vWorld - cameraPosition), n = normalize(vN);
        if (dot(n, v) > 0.0) n = -n;
        vec3 r = reflect(v, n);
        float f = 0.04 + 0.96 * pow(1.0 - max(dot(-v, n), 0.0), 5.0);
        vec3 sky = r.y > 0.0 ? skyAlong(r) : uHazeAway * 0.35;
        vec3 c = mix(vec3(uTint, uTint * 1.05, uTint * 1.08), sky, f);
        gl_FragColor = vec4(applyAtmosphere(c, vWorld), 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}

// the stand-in (level.js buildEstate merges it with the town's glimpses): drop its estate triangles
function trimStandIn(scene) {
  const m = scene.getObjectByName('Wild_Estate');
  if (!m) return;
  const g = m.geometry, n = g.attributes.position.count, P = g.attributes.position;
  const keep = [];
  for (let t = 0; t < n; t += 3) {
    const cx = (P.getX(t) + P.getX(t + 1) + P.getX(t + 2)) / 3, cz = (P.getZ(t) + P.getZ(t + 1) + P.getZ(t + 2)) / 3 - OFFSET_Z;
    if (!(Math.abs(cx) < 100 && Math.abs(cz) < 95)) keep.push(t, t + 1, t + 2);
  }
  const ng = new THREE.BufferGeometry();
  for (const [k, a] of Object.entries(g.attributes)) {
    const out = new a.array.constructor(keep.length * a.itemSize);
    keep.forEach((v, i) => { for (let c = 0; c < a.itemSize; c++) out[i * a.itemSize + c] = a.array[v * a.itemSize + c]; });
    ng.setAttribute(k, new THREE.BufferAttribute(out, a.itemSize));
  }
  m.geometry = ng;
}

export async function loadEstate({ world, scene, uniforms, params }) {
  if (params.get('estate') === '0') return null;
  const t0 = performance.now();
  const base = '../assets/';
  const loader = new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath('https://unpkg.com/three@0.160.0/examples/jsm/libs/draco/gltf/'));
  const far = params.get('estate') === 'far';
  const parse = async (file, strip) => {
    const json = await (await fetch(base + file)).json();
    if (strip) { delete json.images; delete json.textures; delete json.samplers; for (const m of json.materials || []) { delete m.normalTexture; if (m.pbrMetallicRoughness) delete m.pbrMetallicRoughness.baseColorTexture; delete m.extensions; } }
    if (strip && json.extensionsUsed) json.extensionsUsed = json.extensionsUsed.filter((e) => e === 'KHR_draco_mesh_compression');
    return loader.parseAsync(JSON.stringify(json), base + file.slice(0, file.lastIndexOf('/') + 1));
  };
  const [bakeJ, outdoor, shell] = await Promise.all([
    fetch(base + 'levels/mansion_bake.json').then((r) => (r.ok ? r.json() : null)).catch(() => null),
    parse('models/mansion_outdoor.gltf', far),
    parse('models/mansion_shell.gltf', true),
  ]);
  const bake = bakeJ?.outdoor || { flat: 1.41, textured: 2.15 };
  const group = new THREE.Group();
  group.name = 'Wild_Mansion';
  group.position.z = OFFSET_Z;
  // grounds: one material each, the lawn beyond the hedge on the cove's side dropped (the hay
  // meadow is the wilderness's own terrain there)
  const cache = new Map();
  let tris = 0;
  outdoor.scene.traverse((o) => {
    if (!o.isMesh) return;
    const src = o.material;
    if (/Water/.test(src.name)) o.material = glassMaterial(uniforms, 0.012);
    else if (src.name === 'M_Out_Glass') o.material = glassMaterial(uniforms);
    else {
      if (!cache.has(src)) { if (src.map) src.map.colorSpace = THREE.SRGBColorSpace; cache.set(src, groundsMaterial(uniforms, src, bake, src.name === 'M_Grounds_Lawn')); }
      o.material = cache.get(src);
    }
    if (src.name === 'M_Grounds_Lawn') {
      const g = o.geometry, idx = g.index, P = g.attributes.position, keep = [];
      for (let t = 0; t < idx.count; t += 3) {
        const a = idx.getX(t), b = idx.getX(t + 1), c = idx.getX(t + 2);
        const cx = (P.getX(a) + P.getX(b) + P.getX(c)) / 3, cz = (P.getZ(a) + P.getZ(b) + P.getZ(c)) / 3;
        if (cz > 42 && (cz > 62.75 || Math.abs(cx) > 70.75)) continue;     // (house frame: south of the hedge)
        keep.push(a, b, c);
      }
      g.setIndex(keep);
      o.userData.splitHay = true;
    }
    tris += (o.geometry.index ? o.geometry.index.count : o.geometry.attributes.position.count) / 3;
  });
  // the rest of the lawn beyond the hedge (north, east, west) is hay meadow, as the house shows it
  let lawnMesh = null;
  outdoor.scene.traverse((o) => { if (o.userData.splitHay) lawnMesh = o; });
  if (lawnMesh) {
    const u = lawnMesh.material.uniforms;
    splitOuterLawn(lawnMesh, groundsMaterial(uniforms, { map: u.tMap.value, color: u.uBase.value }, bake, true, true));
  }
  group.add(outdoor.scene);
  // the shell's glazing and frames
  const frames = glassMaterial(uniforms, 0.03);
  shell.scene.traverse((o) => {
    if (!o.isMesh) return;
    if (/_M_Glass$/.test(o.name) && !/Rail/.test(o.name)) o.material = glassMaterial(uniforms);
    else if (/_M_Aluminium_Black$/.test(o.name)) o.material = frames;
    else { o.visible = false; return; }
    tris += (o.geometry.index ? o.geometry.index.count : o.geometry.attributes.position.count) / 3;
  });
  const drop = []; shell.scene.traverse((o) => { if (o.isMesh && !o.visible) drop.push(o); });
  for (const o of drop) o.parent.remove(o);
  group.add(shell.scene);
  scene.add(group);
  group.updateMatrixWorld(true);
  trimStandIn(scene);
  // the gate: its leaves split out and standing open
  const flat = group.getObjectByName('Mansion_Outdoor_Flat');
  if (flat) flat.userData.houseZ = OFFSET_Z;
  const leaves = flat ? splitGateLeaves(flat) : null;
  setLeaves(leaves, 1);
  const ms = Math.round(performance.now() - t0);
  return { group, leaves, tris: Math.round(tris), ms };
}

// ---- the gate back to the house, and the wilderness's side of the handoff
// (window.__wildGate: arrive(state) / suspend() / look(dx, dy) for the house's iframe host)
export function wildGate({ world, camera, player, wild, params }) {
  const reg = linkRegistry();
  const embedded = params.get('embed') === '1' && window.parent !== window;
  let armed = false, suspended = false, sent = false;
  const euler = new THREE.Euler(0, 0, 0, 'YXZ');
  const api = {
    carried: null,                     // the house's inventory, as handed over (read-only here for now)
    arrive(state) {
      const s = state.player;
      const x = s.pos[0], z = s.pos[2];
      player.pos.set(x, Math.max(world.heightAt(x, z), s.pos[1]), z);
      player.vel.set(...(s.vel || [0, 0, 0]));
      if (s.quat) camera.quaternion.fromArray(s.quat);
      player.syncCamera?.();
      api.carried = { inventory: state.inventory, armed: state.armed };
      reg.deliver(state.extra);
      armed = false; sent = false;
      api.resume();
    },
    suspend() { suspended = true; wild.pause(true); },
    resume() { suspended = false; wild.pause(false); },
    look(dx, dy) {
      euler.setFromQuaternion(camera.quaternion);
      euler.y -= dx * 0.002; euler.x -= dy * 0.002;
      euler.x = Math.max(-Math.PI / 2 + 0.01, Math.min(Math.PI / 2 - 0.01, euler.x));
      camera.quaternion.setFromEuler(euler);
    },
    get suspended() { return suspended; },
    state() {
      return { from: 'wild', t: performance.now(),
        player: { pos: player.pos.toArray(), vel: player.vel.toArray(), crouch: !!player.crouching, quat: camera.quaternion.toArray() },
        extra: reg.collect() };
    },
    // each wilderness frame: back in through the gate = to the house
    update() {
      if (suspended || sent) return;
      const p = player.pos, hz = p.z - OFFSET_Z;
      if (hz > GATE.line + 1.8) armed = true;               // (out past the gate's apron once)
      if (!armed || hz > GATE.back || hz < GATE.z - 3 || p.x < GATE.mouth[0] || p.x > GATE.mouth[1]) return;
      sent = true;
      const s = api.state();
      s.player.pos[2] -= OFFSET_Z;                          // to the house's frame
      if (embedded && window.parent.__estateLink?.returnFromWild) {
        window.parent.__estateLink.returnFromWild(s);
      } else {
        try { sessionStorage.setItem(STATE_KEY, JSON.stringify(s)); } catch { /* */ }
        location.href = 'index.html?level=mansion&from=wild';
      }
    },
  };
  window.__wildGate = api;
  return api;
}
