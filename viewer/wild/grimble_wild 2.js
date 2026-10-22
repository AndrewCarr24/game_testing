import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { prepareGrimble, turnToward, blobShadow } from '../grimble.js';
import { NavGrid } from '../grimble_nav.js';
import { ATMOSPHERE_PARS } from './atmosphere.js';

// The Grimble at home in the forest: a friendly 7.3 m giant (specs.md "grimble"; the asset is
// blender/assets/grimble.py). It lives deep in Laurel Fork Cove, in the old-growth tulip poplars
// of Poplar Cove, on a quiet bench across the Poplar branch from the creek trail (route A passes
// ~70 m west, on the far side of the water): a curious player who leaves the trail finds it; the
// routes never run through it. Nothing it does is ever a threat, and nothing is said in text:
//
//   amble    it walks slowly among the giant trees (the Walk clip at its real stride, slowed:
//            speed = stride / cycle x playback rate, so the feet never slide)
//   look     it stops at a tree, the creek or a view and looks at it (Idle; head and eyes turn)
//   pat      at a big poplar it pats the trunk (the Knock clip) and a few leaves come down
//   rest     now and then it settles at home (Idle, slowed, head low)
//   notice   it sees the player (a notice meter: distance, the trunks and the ground between,
//            crouching): it turns to them and tilts its head
//   wave     it waves with its open hand (the Wave clip)
//   follow   it follows at a respectful distance (stops ~14 m off) for a while, never past its
//            leash from home, then waves goodbye and walks home (return)
//   aside    a player who walks up to it (inside ~4.5 m): it backs off or steps aside, so it
//            never blocks a path; its soft collider (one moving box) keeps the player out of it
//
// It never swipes, knocks down or hurts (window.__player.knockDown and the combat contract are
// never called from here). Where it can go: a nav grid (grimble_nav.js NavGrid) over ~300 m round
// its home: the world's trunk, log and boulder colliders (inflated by its footprint), slopes
// over 30 degrees, deep water and the laurel hell are closed; the shallow Poplar branch it steps
// through. Its footprint is also pushed out of the trunks every frame.
//
// Light: the wild scene has no three.js lights; it gets one DirectionalLight (the level's sun,
// as litColor in level.js: colour x strength / pi) and the sky as its environment (as the
// house's prepareGrimble outdoors), and its shader is patched to take the level's light map like
// everything else: the sun term x the canopy's sun visibility (looked up where the sun ray
// through each point meets the ground, so sunflecks slide over it), the sky term x the sky
// visibility under it, then the wild's aerial perspective + forest air (atmosphere.js).
// Cost: one skinned character (~40k triangles, 11 draw calls with its blob shadow, +1 for the
// leaves while they fall; ~0.03 ms/frame of CPU); hidden and not animated outside the view or past
// `farHide` m, its mind idles past `farSleep` m.
//
// Sound: there's no sound path in wild.html yet (viewer/wild/swim.js has the same note); it
// calls window.__sfx?.play?.(name, position, opts) for its footfalls (the Walk clip's contacts)
// and soft breaths, so they play once the wild runtime has an Sfx.
//
// URL (wild.html): grimble=0 leaves it out; view=grimble (the trail where it can first be seen)
// / view=grimble_home; gpos=x,z[,rotDeg] starts it there (still at home, as screenshots want).

// per world: its home (three.js x, z) and range; worlds without an entry have no Grimble
export const HOMES = {
  laurel_fork: {
    // estate frame (62, -430): Poplar Cove's old growth, the bench east of the Poplar branch
    home: [62, -380],
    range: 30,            // m round home it ambles in
    leash: 105,           // m from home it follows the player at most
    area: 150,            // m: the nav grid's half size round home
    views: {
      // on route A (the creek trail) at its nearest to home, looking east across the branch
      // (y = null: eye height over the ground; a look's y = null: 4 m over the ground there)
      grimble: { pos: [-3, null, -352], look: [62, null, -380] },
      grimble_home: { pos: [30, null, -362], look: [62, null, -380] },
    },
  },
};

const DEFAULTS = {
  stride: 4.2, cycle: 2.8,   // m / s per Walk cycle (grimble_rig.py; the asset's userData overrides)
  ambleRate: 0.62,           // Walk playback while ambling: ~0.93 m/s
  followRate: [0.8, 1.8],    // ... while following (with the gap): 1.2-2.7 m/s (a walking player is 3.4)
  returnRate: 0.75,
  turnRate: 0.75,            // rad/s while walking (in place: turnInPlace)
  turnInPlace: 0.55,
  footR: 1.05,               // m: its footprint (the cloak's hem in the Walk clip)
  navMargin: 0.35,           // m kept clear round the footprint on the grid
  lookAhead: 2.4,            // m along the path it steers at
  sight: 60,                 // m it can notice the player at
  noticeK: 1.2, noticeL: 18, // notice rate (1/s) = k x exp(-d / L) (+ the close bonus): a walker
                             // coming at it is noticed at ~25-30 m, a crouched one much closer
  forget: 0.2,               // /s the meter falls out of sight
  personal: 4.5,             // m: closer than this it steps aside
  followGap: [13, 18],       // m: it stops within the first, walks again past the second
  followTime: [55, 80],      // s it follows for
  lostAfter: 14,             // s out of sight while following: it gives up
  cooldown: 100,             // s after a follow before it follows again (it still looks and waves)
  waveCooldown: 45,          // s between waves
  look: [6, 12],             // s it looks at a thing
  rest: [18, 30],            // s it rests at home
  restEvery: 4,              // POIs between rests
  patChance: 0.45,           // of a big tree: it pats the trunk
  reach: 2.05,               // m from its origin to the knuckles (Knock; userData.knockReach)
  taps: [1.25, 1.95, 2.65],  // s into Knock when the knuckles touch
  headLimit: 0.7, eyeLimit: 0.5,
  tilt: 0.32,                // rad the head tilts when it notices you
  fade: 0.6,                 // s cross-fades
  lieDown: 1.6,              // s to settle into the rest (CrawlIdle at full size) or get up from it
  restBody: [4.2, 4.5, 1.9], // m: resting, its body reaches this far ahead / behind / to the side
  farHide: 180,              // m: beyond this it isn't drawn or animated
  farSleep: 420,             // m: beyond this its mind idles too (it ambles on, cheaply)
};

const rand = (a, b) => a + Math.random() * (b - a);
const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
const _v = new THREE.Vector3(), _w = new THREE.Vector3(), _sph = new THREE.Sphere(), _fr = new THREE.Frustum(), _pm = new THREE.Matrix4();

export async function loadWildGrimble({ scene, world, worldName, uniforms, tex, sky, colliders, player, camera, params, renderer, base = '../assets/models/' }) {
  const cfg = world.meta?.grimble || HOMES[worldName];
  if (!cfg) return null;
  const loader = new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath('https://unpkg.com/three@0.160.0/examples/jsm/libs/draco/gltf/'));
  const gltf = await loader.loadAsync(base + 'grimble.gltf');
  // built in a staging scene (with its sun: the programs depend on the lights), compiled off the
  // render loop, then moved into the level (whose other materials take no three.js lights)
  const stage = new THREE.Scene();
  const g = new WildGrimble(stage, gltf, { world, cfg, uniforms, tex, sky, colliders, player, camera, base, params });
  g.root.visible = g.blob.visible = g.leaves.pts.visible = true;
  if (renderer?.compileAsync) await renderer.compileAsync(stage, camera);
  g.leaves.pts.visible = false;
  for (const o of [...stage.children]) scene.add(o);
  g.scene = scene;
  window.__grimble = g;
  return g;
}

// the wild's light on its PBR materials (see the header)
function wildShading(m, shared) {
  if (m.userData._wild) return;            // (a material several meshes share)
  m.userData._wild = true;
  const prev = m.onBeforeCompile, detail = !!m.userData._detail;
  m.onBeforeCompile = (shader, renderer) => {
    if (prev) prev.call(m, shader, renderer);
    Object.assign(shader.uniforms, shared);
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vGWorld;')
      .replace('#include <project_vertex>', '#include <project_vertex>\n\tvGWorld = (modelMatrix * vec4(transformed, 1.0)).xyz;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', ['#include <common>', ATMOSPHERE_PARS,
        'uniform sampler2D uLight;\nuniform vec4 uMapXf;\nuniform vec3 uBounce;\nuniform float uGroundY, uSkyK, uSunK;\nvarying vec3 vGWorld;'].join('\n'))
      .replace('#include <lights_fragment_begin>', [
        // sun: where the ray from this point toward the sun meets the ground; sky: right under it
        'float gH = max(vGWorld.y - uGroundY, 0.0);',
        'vec2 gXZ = vGWorld.xz - uSunDir.xz / max(uSunDir.y, 0.15) * gH;',
        'vec4 gL = textureLod(uLight, (gXZ - uMapXf.xy) * uMapXf.z, 0.0);',
        'vec4 gL0 = textureLod(uLight, (vGWorld.xz - uMapXf.xy) * uMapXf.z, 0.0);',
        'float gSun = gL.a * gL.g * uSunK, gSky = gL0.b * uSkyK;',
        THREE.ShaderChunk.lights_fragment_begin.replace('getDirectionalLightInfo( directionalLight, directLight );',
          'getDirectionalLightInfo( directionalLight, directLight );\n\t\tdirectLight.color *= gSun;'),
      ].join('\n'))
      // (+ the warm bounce off the sunlit ground round it, as the props and bark get: level.js, trees.js)
      .replace('#include <lights_fragment_maps>', '#include <lights_fragment_maps>\n\tiblIrradiance *= gSky;\n\tradiance *= gSky;\n#if defined( RE_IndirectDiffuse )\n\tirradiance += uBounce * (0.55 * PI);\n#endif')
      .replace('#include <tonemapping_fragment>', '\tgl_FragColor.rgb = applyAtmosphere(gl_FragColor.rgb, vGWorld);\n#include <tonemapping_fragment>');
  };
  m.customProgramCacheKey = () => (detail ? 'grimble-wild-detail' : 'grimble-wild');
  m.needsUpdate = true;
}

// a few leaves coming down out of a crown (one draw call, only while they fall)
class Leaves {
  constructor(scene, uniforms, shared, n = 70) {
    this.n = n;
    const g = new THREE.BufferGeometry();
    this.pos = new Float32Array(n * 3);
    this.vel = new Float32Array(n * 4);       // fall speed, flutter phase, flutter radius, life
    g.setAttribute('position', new THREE.BufferAttribute(this.pos, 3));
    this.geo = g;
    this.mat = new THREE.ShaderMaterial({
      uniforms: { ...uniforms, ...shared, uTint: { value: new THREE.Color(0.32, 0.42, 0.12) }, uScale: { value: 1 } },
      vertexShader: /* glsl */`
        uniform float uScale; varying vec3 vW;
        void main() {
          vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz;
          vec4 mv = viewMatrix * w;
          gl_PointSize = clamp(0.16 * uScale / -mv.z, 1.0, 24.0);
          gl_Position = projectionMatrix * mv;
        }`,
      fragmentShader: /* glsl */`
        ${ATMOSPHERE_PARS}
        uniform vec3 uTint, uSunColor, uSkyColor; uniform sampler2D uLight; uniform vec4 uMapXf; varying vec3 vW;
        void main() {
          vec2 p = gl_PointCoord * 2.0 - 1.0;
          if (dot(p * vec2(1.0, 1.7), p * vec2(1.0, 1.7)) > 1.0) discard;   // a leaf-shaped ellipse
          vec4 l = textureLod(uLight, (vW.xz - uMapXf.xy) * uMapXf.z, 0.0);
          vec3 c = uTint * (uSunColor * 0.5 * l.a * l.g + uSkyColor * l.b * 0.9);
          gl_FragColor = vec4(applyAtmosphere(c, vW), 1.0);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }`,
    });
    this.pts = new THREE.Points(g, this.mat);
    this.pts.name = 'Wild_Grimble_Leaves';
    this.pts.frustumCulled = false;
    this.pts.visible = false;
    this.alive = 0;
    scene.add(this.pts);
  }
  // a handful from the crown over (x, z), between y0 and y1
  drop(x, z, y0, y1, count = 22, spread = 5) {
    for (let k = 0, i = 0; i < this.n && k < count; i++) {
      if (this.vel[i * 4 + 3] > 0) continue;
      this.pos[i * 3] = x + rand(-spread, spread); this.pos[i * 3 + 1] = rand(y0, y1); this.pos[i * 3 + 2] = z + rand(-spread, spread);
      this.vel[i * 4] = rand(0.7, 1.3); this.vel[i * 4 + 1] = rand(0, 6.28); this.vel[i * 4 + 2] = rand(0.3, 0.9); this.vel[i * 4 + 3] = 1;
      k++;
    }
    this.pts.visible = true;
  }
  update(dt, ground, scale) {
    if (!this.pts.visible) return;
    let alive = 0;
    for (let i = 0; i < this.n; i++) {
      if (this.vel[i * 4 + 3] <= 0) { this.pos[i * 3 + 1] = -1e4; continue; }
      const ph = (this.vel[i * 4 + 1] += dt * 2.2), r = this.vel[i * 4 + 2];
      this.pos[i * 3] += Math.cos(ph) * r * dt; this.pos[i * 3 + 2] += Math.sin(ph * 0.7) * r * dt;
      this.pos[i * 3 + 1] -= this.vel[i * 4] * (0.75 + 0.5 * Math.sin(ph * 2)) * dt;
      if (this.pos[i * 3 + 1] < ground(this.pos[i * 3], this.pos[i * 3 + 2]) + 0.05) this.vel[i * 4 + 3] -= dt * 0.25;   // lie a few s, then go
      else alive++;
      if (this.vel[i * 4 + 3] > 0 && this.pos[i * 3 + 1] < ground(this.pos[i * 3], this.pos[i * 3 + 2])) this.pos[i * 3 + 1] = ground(this.pos[i * 3], this.pos[i * 3 + 2]) + 0.03;
    }
    this.mat.uniforms.uScale.value = scale;
    this.geo.attributes.position.needsUpdate = true;
    this.alive = alive;
    if (!this.vel.some((v, i) => i % 4 === 3 && v > 0)) this.pts.visible = false;
  }
}

export class WildGrimble {
  constructor(scene, gltf, { world, cfg, uniforms, tex, sky, colliders, player, camera, base, params }) {
    this.o = { ...DEFAULTS, ...(cfg.opts || {}) };
    this.world = world; this.cfg = cfg; this.player = player; this.camera = camera; this.scene = scene;
    this.root = gltf.scene;
    const ud = this.root.userData;
    for (const k of ['stride', 'cycle']) if (ud[k]) this.o[k] = ud[k];
    if (ud.knockReach) this.o.reach = ud.knockReach;
    this.home = new THREE.Vector2(...cfg.home);
    // ---- look: the house's outdoor setup (sky env, single-sided, detail normals) + the wild's light
    prepareGrimble(this.root, sky.getEnv(), base);
    this.shared = {
      uLight: { value: tex.light }, uMapXf: { value: new THREE.Vector4(-world.size / 2, -world.size / 2, 1 / world.size, 1) },
      uGroundY: { value: 0 }, uSkyK: { value: 1.0 }, uSunK: { value: 1.0 },
    };
    const atm = Object.fromEntries(Object.entries(uniforms).filter(([k]) => /^u(Horizon|Zenith|SunDir|Haze|FogDensity|FogFalloff|FogBase|Time|HazeMode|Ext|HazeAway|HazeSun|HazeScale|ForestAir|ForestAirK|Bounce)$/.test(k)));
    if (!atm.uBounce) atm.uBounce = { value: new THREE.Color(0.13, 0.14, 0.105) };
    this.root.traverse((o) => { if (o.isMesh) for (const m of [o.material].flat()) wildShading(m, { ...atm, ...this.shared }); });
    // the sun (litColor: colour x strength / pi, so x pi here: three's Lambert divides by pi)
    this.sun = new THREE.DirectionalLight(uniforms.uSunColor.value.clone(), Math.PI);
    this.sun.name = 'Wild_Grimble_Sun';
    this.sunDir = uniforms.uSunDir.value;
    this.sun.target = this.root;
    scene.add(this.sun);
    scene.add(this.root);
    this.blob = blobShadow(scene);
    this.blob.material.opacity = 0.75;
    this.leaves = new Leaves(scene, uniforms, this.shared);
    // ---- animation
    this.mixer = new THREE.AnimationMixer(this.root);
    this.actions = Object.fromEntries(gltf.animations.map((c) => [c.name, this.mixer.clipAction(c)]));
    for (const n of ['Knock', 'Wave']) if (this.actions[n]) { this.actions[n].setLoop(THREE.LoopOnce); this.actions[n].clampWhenFinished = true; }
    this.current = null;
    this.head = this.root.getObjectByName('Head');
    this.root.updateMatrixWorld(true);
    if (this.head) {
      const fwd = new THREE.Vector3(0, 0, 1).applyQuaternion(this.root.getWorldQuaternion(new THREE.Quaternion()));
      this.headFwd = fwd.applyQuaternion(this.head.getWorldQuaternion(new THREE.Quaternion()).invert()).normalize();
    }
    this.eyes = [];
    this.root.traverse((o) => { if (o.userData.look) this.eyes.push({ o, rest: o.quaternion.clone() }); });
    // ---- where it can go
    this.buildNav(colliders);
    // its soft collider: one loose (not `fixed`) box the player's broadphase tests every frame
    this.box = new THREE.Box3();
    this.box.grimble = true;
    colliders.push(this.box);
    // ---- start: at home, or ?gpos=x,z[,rotDeg]
    const gp = params?.get('gpos')?.split(',').map(Number);
    const start = gp ? new THREE.Vector2(gp[0], gp[1]) : this.nav.centre(this.nav.nearest(this.home.x, this.home.y, 20));
    this.pos = start.clone();
    this.heading = gp && gp.length > 2 ? THREE.MathUtils.degToRad(gp[2]) : -1.75;   // (facing the trail, west)
    this.state = 'look'; this.t = 0; this.dur = rand(2, 5); this.lookAt = null;
    this.poiCount = 0; this.lastPoi = -1;
    this.aware = 0; this.seen = false; this.lastSeen = -1e9; this.time = 0;
    this.followedAt = -1e9; this.wavedAt = -1e9;
    this.tilt = 0; this.tiltTarget = 0;
    this.log = [];
    this.stats = { maxPen: 0, penFrames: 0, frames: 0, knockDowns: 0 };
    this.walkPhase = 0;
    this.play('Idle');
    this.place();
    this.mixer.update(0);
  }

  // ------------------------------------------------------------ the nav grid round home
  buildNav(colliders) {
    const W = this.world, o = this.o, A = this.cfg.area, hx = this.home.x, hz = this.home.y;
    const bounds = [hx - A, hz - A, hx + A, hz + A];
    // what it can't walk through: anything standing over 0.6 m off the ground under it (trunks,
    // boulders, logs; it doesn't climb), not overhead (a log on its root wad over a hollow)
    this.solid = [];
    for (const c of colliders) {
      if (c.max.x < bounds[0] - 3 || c.min.x > bounds[2] + 3 || c.max.z < bounds[1] - 3 || c.min.z > bounds[3] + 3) continue;
      const gy = W.heightAt((c.min.x + c.max.x) / 2, (c.min.z + c.max.z) / 2);
      if (c.max.y - gy < 0.6 || c.min.y - gy > 3.5) continue;
      this.solid.push(c);
    }
    const cell = 0.5;
    const nav = new NavGrid(this.solid, [bounds], { cell, radius: o.footR + o.navMargin, band: [-1e9, 1e9], bounds });
    // steep ground, deep water, the laurel hell (`hard`: what its feet can't stand on at all;
    // the grid's `blocked` adds the trunks inflated by its footprint and a margin, for planning)
    this.hard = new Uint8Array(nav.w * nav.h);
    const cosMax = Math.cos(THREE.MathUtils.degToRad(30));
    for (let j = 0; j < nav.h; j++) for (let i = 0; i < nav.w; i++) {
      const k = j * nav.w + i;
      const x = nav.x0 + (i + 0.5) * cell, z = nav.z0 + (j + 0.5) * cell;
      const n = W.normalAt(x, z, 1.0), wl = W.waterAt(x, z), tc = W.cellAt(x, z);
      if (n[1] < cosMax || (!Number.isNaN(wl) && wl - W.heightAt(x, z) > 0.7) || (tc >= 0 && W.thicket[tc])) { this.hard[k] = 1; nav.blocked[k] = 1; }
    }
    // the solids in 4 m buckets (its footprint test while it moves)
    this.bucket = new Map();
    for (const c of this.solid) for (let bi = Math.floor(c.min.x / 4); bi <= Math.floor(c.max.x / 4); bi++)
      for (let bk = Math.floor(c.min.z / 4); bk <= Math.floor(c.max.z / 4); bk++) {
        const key = bi * 100003 + bk;
        if (!this.bucket.has(key)) this.bucket.set(key, []);
        this.bucket.get(key).push(c);
      }
    nav.flood(hx, hz);
    nav.clearance();
    this.nav = nav;
    this.pois = this.findPois();
  }

  // can its footprint stand at (x, z)? (ground it can stand on, no trunk inside footR)
  free(x, z, r = this.o.footR) {
    const k = this.nav.idx(x, z);
    if (k < 0 || this.hard[k]) return false;
    for (let bi = Math.floor((x - r) / 4); bi <= Math.floor((x + r) / 4); bi++) for (let bk = Math.floor((z - r) / 4); bk <= Math.floor((z + r) / 4); bk++) {
      const L = this.bucket.get(bi * 100003 + bk);
      if (L) for (const c of L) {
        const qx = Math.max(c.min.x, Math.min(x, c.max.x)), qz = Math.max(c.min.z, Math.min(z, c.max.z));
        if ((x - qx) ** 2 + (z - qz) ** 2 < r * r) return false;
      }
    }
    return true;
  }

  // what it goes and looks at: the big trees round home (stand a little off the trunk, look up
  // into the crown; the biggest it may pat), the creek's edge, and home itself (where it rests)
  findPois() {
    const W = this.world, o = this.o, R = this.cfg.range, out = [];
    for (const [id, info] of Object.entries(W.speciesInfo)) {
      if (info.tier !== 'tree' || info.ring) continue;
      const a = W.species[id];
      for (let i = 0; i < a.length; i += 6) {
        const x = a[i], z = a[i + 2], h = a[i + 3] * info.height;
        if (h < 34 || Math.hypot(x - this.home.x, z - this.home.y) > R) continue;
        // the trunk's own collider (its half width), for where the knuckles meet the bark
        const tb = this.solid.find((c) => x >= c.min.x - 0.3 && x <= c.max.x + 0.3 && z >= c.min.z - 0.3 && z <= c.max.z + 0.3);
        const tr = tb ? Math.max(tb.max.x - tb.min.x, tb.max.z - tb.min.z) / 2 : 0.6;
        const gy = W.heightAt(x, z);
        // a stand point on the side toward home, at its knock reach from the bark
        const toHome = new THREE.Vector2(this.home.x - x, this.home.y - z).normalize();
        let stand = null;
        for (const da of [0, 0.5, -0.5, 1, -1, 1.6, -1.6, 2.4, -2.4, 3.1]) {
          const d = toHome.clone().rotateAround(new THREE.Vector2(), da);
          const p = new THREE.Vector2(x, z).addScaledVector(d, tr + o.reach);
          const k = this.nav.idx(p.x, p.y);
          if (this.nav.walkable(k)) { stand = p; break; }
        }
        out.push({ kind: 'tree', id, x, z, h, stand, trunk: new THREE.Vector3(x, gy + 1.8, z), crown: new THREE.Vector3(x, gy + h * 0.55, z), pat: !!stand && info.kind === 'broadleaf' });
      }
    }
    // the creek: the nearest water to home
    let best = null;
    for (let a = 0; a < 48; a++) for (let r = 4; r <= R + 25; r += 2) {
      const x = this.home.x + r * Math.cos((a / 48) * Math.PI * 2), z = this.home.y + r * Math.sin((a / 48) * Math.PI * 2);
      if (!Number.isNaN(W.waterAt(x, z))) { if (!best || r < best.r) best = { x, z, r }; break; }
    }
    if (best) {
      const k = this.nav.nearest(best.x, best.z, 8);
      if (k >= 0) {
        const s = this.nav.centre(k);
        out.push({ kind: 'creek', x: best.x, z: best.z, stand: s, look: new THREE.Vector3(best.x, W.waterAt(best.x, best.z), best.z) });
      }
    }
    out.push({ kind: 'home', x: this.home.x, z: this.home.y, stand: this.nav.centre(this.nav.nearest(this.home.x, this.home.y, 20)) });
    return out.filter((p) => p.stand && this.nav.walkable(this.nav.idx(p.stand.x, p.stand.y)));
  }

  // ------------------------------------------------------------ animation
  play(name, rate = 1) {
    const next = this.actions[name];
    if (!next) return;
    next.timeScale = rate;
    if (next === this.current) return;
    next.reset().play();
    // (lying down and getting up take longer than the other blends)
    const slow = name === 'CrawlIdle' || this.current === this.actions.CrawlIdle;
    if (this.current) next.crossFadeFrom(this.current, slow ? this.o.lieDown : this.o.fade, false);
    this.current = next;
  }
  speed() { const a = this.actions.Walk; return a && this.current === a ? (this.o.stride / this.o.cycle) * a.timeScale : 0; }

  event(ev, extra = {}) {
    const e = { t: +this.time.toFixed(2), ev, at: [+this.pos.x.toFixed(1), +this.pos.y.toFixed(1)], ...extra };
    this.log.push(e);
    if (this.log.length > 400) this.log.shift();
  }
  setState(s, extra) {
    if (s !== this.state) this.event(s, extra);
    // getting up from a rest before anything else (no walking while the pose blends)
    if (this.state === 'rest' && s !== 'rest') { this.play('Idle'); this.rising = this.o.lieDown + 0.2; }
    this.state = s; this.t = 0;
  }

  // ------------------------------------------------------------ the senses
  // can it see the player (eye to eye, past the trunks and over the ground)?
  canSee(eye) {
    const head = _v.set(this.pos.x, this.groundY + 6.3, this.pos.y);
    const d = head.distanceTo(eye);
    if (d > this.o.sight) return false;
    const W = this.world, n = Math.ceil(d / 3);
    for (let s = 1; s < n; s++) {
      const t = s / n, x = head.x + (eye.x - head.x) * t, y = head.y + (eye.y - head.y) * t, z = head.z + (eye.z - head.z) * t;
      if (W.heightAt(x, z) > y) return false;
    }
    // the trunks between (2D segment vs the boxes, at the ray's height there)
    const ax = head.x, az = head.z, dx = eye.x - ax, dz = eye.z - az;
    for (const c of this.solid) {
      if (Math.max(ax, eye.x) < c.min.x || Math.min(ax, eye.x) > c.max.x || Math.max(az, eye.z) < c.min.z || Math.min(az, eye.z) > c.max.z) continue;
      // slab test in xz
      let t0 = 0, t1 = 1;
      for (const [o0, dd, lo, hi] of [[ax, dx, c.min.x, c.max.x], [az, dz, c.min.z, c.max.z]]) {
        if (Math.abs(dd) < 1e-9) { if (o0 < lo || o0 > hi) { t0 = 2; break; } continue; }
        let ta = (lo - o0) / dd, tb = (hi - o0) / dd;
        if (ta > tb) [ta, tb] = [tb, ta];
        t0 = Math.max(t0, ta); t1 = Math.min(t1, tb);
      }
      if (t0 > t1 || t0 > 1) continue;
      const y = head.y + (eye.y - head.y) * ((t0 + t1) / 2);
      if (y >= c.min.y && y <= c.max.y && t0 > 0.02 && t1 < 0.98) return false;
    }
    return true;
  }

  sense(dt, eye) {
    const pp = this.player.pos, d = Math.hypot(pp.x - this.pos.x, pp.z - this.pos.y);
    this.playerDist = d;
    const see = d < this.o.sight && this.canSee(eye);
    this.seen = see;
    if (see) {
      this.lastSeen = this.time;
      const crouch = this.player.crouching ? 0.5 : 1;
      const moving = Math.hypot(this.player.vel?.x ?? 0, this.player.vel?.z ?? 0) > 0.5 ? 1.25 : 0.7;
      this.aware = Math.min(1.5, this.aware + dt * (this.o.noticeK * Math.exp(-d / this.o.noticeL) * crouch * moving + (d < 12 ? 0.8 * crouch : 0)));
    } else this.aware = Math.max(0, this.aware - dt * this.o.forget);
    return see;
  }

  // ------------------------------------------------------------ moving
  pathTo(x, z) {
    const p = this.nav.path(this.pos, new THREE.Vector2(x, z));
    this.path = p && p.length ? p : null;
    this.pathI = p && p.length > 1 && this.pos.distanceTo(p[0]) < 0.4 ? 1 : 0;   // (from here to the start cell first)
    this.pathLen = this.nav.lastLen;
    return !!this.path;
  }

  // steer along this.path at the Walk rate (pure pursuit); true when there
  walk(dt, rate, backwards = false) {
    if (!this.path) return true;
    const end = this.path[this.path.length - 1];
    if (this.pos.distanceTo(end) < 0.6) { this.path = null; return true; }
    // the point lookAhead m along the path from the nearest leg
    // (only past a waypoint it can see the next one from: the line from here must stay on the grid)
    while (this.pathI < this.path.length - 1 && this.pos.distanceTo(this.path[this.pathI]) < this.o.lookAhead &&
      (this.pos.distanceTo(this.path[this.pathI]) < 0.5 || this.nav.clearLine(this.pos, this.path[this.pathI + 1]))) this.pathI++;
    const tgt = this.path[this.pathI];
    const want = Math.atan2(tgt.x - this.pos.x, tgt.y - this.pos.y) + (backwards ? Math.PI : 0);
    const err = wrap(want - this.heading);
    const big = Math.abs(err) > 0.5;
    const tr = big ? this.o.turnInPlace : this.o.turnRate;
    this.heading = wrap(this.heading + Math.sign(err) * Math.min(Math.abs(err), tr * dt));
    // turning on the spot: slow steps in place; else walk on along its heading
    this.play('Walk', (big ? 0.35 : rate) * (backwards ? -1 : 1));
    if (big) return false;
    const v = (this.o.stride / this.o.cycle) * rate * dt * Math.cos(err);
    const dir = backwards ? -1 : 1;
    const nx = this.pos.x + Math.sin(this.heading) * v * dir, nz = this.pos.y + Math.cos(this.heading) * v * dir;
    // never into the player: it waits a moment, then goes round them (a plan with the ground
    // round them made costly)
    const pp = this.player.pos;
    const dn = Math.hypot(nx - pp.x, nz - pp.z), dNow = Math.hypot(this.pos.x - pp.x, this.pos.y - pp.z);
    if (dn < this.o.personal && dn < dNow && !backwards && this.state !== 'follow') {
      this.waitT = (this.waitT ?? 0) + dt;
      this.play('Idle');
      if (this.waitT > 1.0) { this.waitT = 0; this.roundPlayer(end); }
      return false;
    }
    this.waitT = 0;
    // (on the grid, or a footprint that fits right next to it: the grid's margin, not a way round)
    const N = this.nav, ok = (x, z) => {
      const k = N.idx(x, z);
      if (N.walkable(k)) return true;
      if (k < 0 || !this.free(x, z, this.o.footR + 0.05)) return false;
      return N.walkable(k - 1) || N.walkable(k + 1) || N.walkable(k - N.w) || N.walkable(k + N.w);
    };
    if (ok(nx, nz) || !ok(this.pos.x, this.pos.y)) { this.pos.set(nx, nz); return false; }
    // (its heading lags the line, or the line grazes a corner: the nearest way round toward the target)
    if (!backwards) {
      const base = Math.atan2(tgt.x - this.pos.x, tgt.y - this.pos.y);
      for (const da of [0, 0.25, -0.25, 0.5, -0.5, 0.8, -0.8, 1.1, -1.1]) {
        const a = base + da, mx = this.pos.x + Math.sin(a) * Math.abs(v), mz = this.pos.y + Math.cos(a) * Math.abs(v);
        if (ok(mx, mz)) { this.pos.set(mx, mz); return false; }
      }
    }
    // its heading lags the path round a bend: plan again from here (a few tries, then it's there)
    const end2 = end.clone();
    if (this.time - (this.replanAt ?? -9) > 2) this.replans = 0;
    this.replanAt = this.time;
    if (++this.replans > 4 || !this.pathTo(end2.x, end2.y)) { this.event('giveup', { to: [+end2.x.toFixed(1), +end2.y.toFixed(1)] }); this.stats.giveups = (this.stats.giveups ?? 0) + 1; this.path = null; return true; }
    return false;
  }

  // a new plan to `end` that keeps ~6 m off the player
  roundPlayer(end) {
    const pp = this.player.pos, e = end.clone();
    this.nav.markCost(pp.x, pp.z, 6, 40);
    this.pathTo(e.x, e.y);
    this.nav.markCost(pp.x, pp.z, 6, 0);
    this.event('round');
  }

  // its footprint out of the trunks (circle vs the boxes)
  depenetrate() {
    const r = this.o.footR;
    let maxPen = 0;
    for (const c of this.solid) {
      if (this.pos.x < c.min.x - r - 0.5 || this.pos.x > c.max.x + r + 0.5 || this.pos.y < c.min.z - r - 0.5 || this.pos.y > c.max.z + r + 0.5) continue;
      if (c.min.y > this.groundY + 3.5 || c.max.y < this.groundY + 0.6) continue;
      const qx = Math.max(c.min.x, Math.min(this.pos.x, c.max.x)), qz = Math.max(c.min.z, Math.min(this.pos.y, c.max.z));
      let dx = this.pos.x - qx, dz = this.pos.y - qz, d = Math.hypot(dx, dz);
      if (d >= r) continue;
      if (d < 1e-4) { dx = this.pos.x - (c.min.x + c.max.x) / 2; dz = this.pos.y - (c.min.z + c.max.z) / 2; d = Math.hypot(dx, dz) || 1; }
      maxPen = Math.max(maxPen, r - d);
      this.pos.x += (dx / d) * (r - d); this.pos.y += (dz / d) * (r - d);
    }
    return maxPen;
  }

  place() {
    const W = this.world, x = this.pos.x, z = this.pos.y, r = 0.7;
    const c = W.heightAt(x, z);
    const lo = Math.min(c, W.heightAt(x + r, z), W.heightAt(x - r, z), W.heightAt(x, z + r), W.heightAt(x, z - r));
    this.groundY = (c + lo) / 2;          // (on a slope the downhill foot would float; the uphill one sinks a little)
    this.root.position.set(x, this.groundY, z);
    this.root.rotation.y = this.heading;
    this.sun.position.copy(this.root.position).addScaledVector(this.sunDir, 100);
    this.shared.uGroundY.value = this.groundY;
    // the soft collider
    if (this.state === 'rest' && this.current === this.actions.CrawlIdle) {
      // lying down: a box round the body (its AABB along the heading)
      const [f, b, w] = this.o.restBody, sx = Math.sin(this.heading), sz = Math.cos(this.heading);
      const ax = [x + sx * f, x - sx * b], az = [z + sz * f, z - sz * b];
      const ex = Math.abs(sz) * w * 0.8, ez = Math.abs(sx) * w * 0.8;
      this.box.min.set(Math.min(...ax) - ex, this.groundY - 0.5, Math.min(...az) - ez);
      this.box.max.set(Math.max(...ax) + ex, this.groundY + 3.6, Math.max(...az) + ez);
    } else {
      this.box.min.set(x - 0.95, this.groundY - 0.5, z - 0.95);
      this.box.max.set(x + 0.95, this.groundY + 6.8, z + 0.95);
    }
    // the blob under it, on the slope
    const n = W.normalAt(x, z, 2);
    this.blob.position.set(x, c + 0.06, z);
    this.blob.quaternion.setFromUnitVectors(_w.set(0, 0, 1), _v.set(n[0], n[1], n[2]));
    this.blob.rotateZ(-this.heading);
  }

  // ------------------------------------------------------------ the mind
  update(dt, camera = this.camera) {
    if (!dt) return;
    const frozen = !!window.__bench;       // (benchmarks: it holds still, so runs repeat; it's still drawn and culled)
    const eye = camera.position;
    const camD = Math.hypot(eye.x - this.pos.x, eye.z - this.pos.y);
    if (!frozen) {
      this.time += dt;
      this.stats.frames++;
      if (camD < this.o.farSleep) this.think(dt, eye);
      const pen = this.depenetrate();
      if (pen > 0.02) { this.stats.penFrames++; this.stats.maxPen = Math.max(this.stats.maxPen, pen); }
      this.place();
      // the player out of its box (it moved into them)
      if (this.player.boxAt && this.player.boxAt(this.player.pos).intersectsBox(this.box)) this.player.pushOutOf?.(this.box);
    }
    // drawn? (in view and near enough; skinned bounds don't follow the animation, so a sphere)
    _pm.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    _fr.setFromProjectionMatrix(_pm);
    _sph.center.set(this.pos.x, this.groundY + 3.8, this.pos.y); _sph.radius = 6.5;
    const show = camD < this.o.farHide && _fr.intersectsSphere(_sph);
    this.root.visible = show;
    this.blob.visible = show;
    if (frozen) return;
    this.mixerDt = (this.mixerDt ?? 0) + dt;
    if (show) {
      this.mixer.update(this.mixerDt);
      this.mixerDt = 0;
      // full size always: the crawl clips (CrawlIdle, its rest) key the root at 0.68 for the house's openings
      (this.rootBone ??= this.root.getObjectByName('Root'))?.scale.setScalar(1);
      this.pose(eye);
      this.sounds();
    } else if (this.mixerDt > 0.5) { this.mixer.update(this.mixerDt); this.mixerDt = 0; }   // (cheap: keeps the cross-fades moving)
    this.leaves.update(dt, this.world.heightAt, window.innerHeight / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))));
  }

  think(dt, eye) {
    const o = this.o;
    this.t += dt;
    const see = this.sense(dt, eye);
    const pp = this.player.pos, d = this.playerDist;
    if (this.rising > 0) { this.rising -= dt; this.lookAt = see && d < 30 ? 'player' : null; return; }
    const toPlayer = Math.atan2(pp.x - this.pos.x, pp.z - this.pos.y);
    // (on its way home it only looks round at you)
    const calm = ['amble', 'look', 'pat', 'rest'].includes(this.state);
    // a player walking up to it: it makes room (never in the middle of a wave; not over and over:
    // a moment after the last time, unless they come closer still)
    const v = this.player.vel, closing = v ? -((pp.x - this.pos.x) * v.x + (pp.z - this.pos.y) * v.z) / Math.max(d, 0.1) : 0;
    if (d < o.personal && !['aside', 'wave', 'notice'].includes(this.state) && (closing > 0.4 || d < 2.8) &&
      (this.time - (this.asideEnd ?? -9) > 2.5 || d < o.personal * 0.6)) { this.stepAside(pp); return; }
    // noticing: the first time, or again once it's been a while since it last waved (it follows
    // again only once its follow cooldown, counted from the goodbye, is over)
    if (calm && this.aware >= 1 && see) {
      if (this.time - this.wavedAt > o.waveCooldown) {
        this.setState('notice', { d: +d.toFixed(1) });
        this.path = null;
        this.tiltTarget = o.tilt;
        this.lookAt = 'player';
        return;
      }
    }
    switch (this.state) {
      case 'amble': {
        this.lookAt = see && d < 30 ? 'player' : null;
        if (this.walk(dt, o.ambleRate)) this.arrive();
        break;
      }
      case 'look': case 'rest': {
        // resting: it turns to the way its body has room, then settles down on all fours
        if (this.state === 'rest') {
          if (this.restHeading != null && !this.face(this.restHeading, dt)) { this.play('Idle'); this.t = 0; break; }
          this.play(this.restHeading != null ? 'CrawlIdle' : 'Idle', this.restHeading != null ? 0.7 : 0.6);
        } else this.play('Idle');
        if (this.poi?.kind === 'tree' && this.state === 'look') this.lookAt = this.t < this.dur * 0.6 ? this.poi.crown : this.poi.trunk;
        else if (this.poi?.kind === 'creek') this.lookAt = this.poi.look;
        else if (this.state === 'rest') this.lookAt = _w.set(this.pos.x + Math.sin(this.heading) * 6, this.groundY + 0.5, this.pos.y + Math.cos(this.heading) * 6).clone();
        if (see && d < 25 && this.aware > 0.3) this.lookAt = 'player';
        // face what it looks at
        if (this.poi && this.poi.kind !== 'home' && this.state === 'look') this.face(Math.atan2(this.poi.x - this.pos.x, this.poi.z - this.pos.y), dt);
        if (this.t >= this.dur) this.next();
        break;
      }
      case 'pat': {
        // face the trunk, pat it; leaves come down out of the crown at each touch
        const want = Math.atan2(this.poi.x - this.pos.x, this.poi.z - this.pos.y);
        if (!this.patting) {
          if (this.face(want, dt)) { this.patting = true; this.t = 0; this.play('Knock'); this.event('touch', { tree: this.poi.id }); }
          else { this.play('Idle'); this.t = 0; }
          break;
        }
        this.lookAt = this.poi.trunk;
        for (const at of o.taps) if (this.t >= at && this.t - dt < at) {
          this.leaves.drop(this.poi.x, this.poi.z, this.groundY + 12, this.groundY + this.poi.h * 0.6, 9, 6);
          window.__sfx?.play?.('g_knock', [this.poi.x, this.groundY + 2.5, this.poi.z], { gain: 0.25 });
        }
        const len = this.actions.Knock?.getClip().duration ?? 3.5;
        if (this.t >= len) { this.patting = false; this.setState('look'); this.dur = rand(5, 8); this.play('Idle'); this.lookAt = this.poi.crown; }
        break;
      }
      case 'notice': {
        // stop, turn to them, the head tilts: then the wave
        this.lookAt = 'player';
        const faced = this.face(toPlayer, dt);
        if (!faced) this.play('Walk', 0.3); else this.play('Idle');
        if (faced && this.t > 1.6) {
          if (this.time - this.wavedAt > o.waveCooldown) { this.setState('wave'); this.play('Wave'); this.wavedAt = this.time; this.aware = 1; }
          else { this.tiltTarget = 0; this.afterWave(); }
        }
        break;
      }
      case 'wave': {
        this.lookAt = 'player';
        this.face(toPlayer, dt);
        const len = this.actions.Wave?.getClip().duration ?? 2.5;
        if (this.t > 0.8) this.tiltTarget = 0;
        if (this.t >= len + 0.3) this.afterWave();
        break;
      }
      case 'follow': {
        this.lookAt = see ? 'player' : null;
        const fromHome = Math.hypot(pp.x - this.home.x, pp.z - this.home.y);
        const lost = this.time - this.lastSeen > o.lostAfter;
        if (this.t > this.followFor || lost || fromHome > o.leash + 40) { this.farewell(lost ? 'lost' : this.t > this.followFor ? 'time' : 'leash'); break; }
        // a point followGap m short of them, inside the leash
        const away = new THREE.Vector2(this.pos.x - pp.x, this.pos.y - pp.z);
        const L = away.length() || 1;
        const goal = new THREE.Vector2(pp.x, pp.z).addScaledVector(away.divideScalar(L), o.followGap[0]);
        const gh = goal.clone().sub(this.home);
        if (gh.length() > o.leash) goal.copy(this.home).addScaledVector(gh.normalize(), o.leash);
        const far = d > o.followGap[1] && this.pos.distanceTo(goal) > 2;
        if (far || (this.moving && d > o.followGap[0] + 0.5 && this.pos.distanceTo(goal) > 1)) {
          if (!this.path || this.time - (this.planAt ?? -9) > 1.5) { this.planAt = this.time; this.pathTo(goal.x, goal.y); }
          const rate = THREE.MathUtils.clamp(o.followRate[0] + (d - o.followGap[0]) / 12, o.followRate[0], o.followRate[1]);
          this.moving = !this.walk(dt, rate) && !!this.path;
        } else {
          this.moving = false; this.path = null;
          this.play('Idle');
          this.face(toPlayer, dt);
        }
        break;
      }
      case 'farewell': {
        this.lookAt = see ? 'player' : null;
        if (see) this.face(toPlayer, dt);
        const len = this.actions.Wave?.getClip().duration ?? 2.5;
        if (!see || this.t >= len + 0.3) { this.setState('return'); this.pathTo(this.home.x, this.home.y); }
        break;
      }
      case 'return': {
        this.lookAt = see && d < 30 ? 'player' : null;
        if (!this.path && this.pos.distanceTo(this.home) > 3) this.pathTo(this.home.x, this.home.y);
        if (this.walk(dt, o.returnRate) || this.pos.distanceTo(this.home) < 3) { this.event('home'); this.poi = this.pois.find((p) => p.kind === 'home'); this.setState('look'); this.dur = rand(3, 6); this.path = null; }
        break;
      }
      case 'aside': {
        this.lookAt = 'player';
        // first round to them (quicker than its idle turns: someone is right there), then back off;
        // (no room to step back: it stays put, turned to them, a moment)
        if (!this.asideFaced) {
          const err = wrap(toPlayer - this.heading);
          this.heading = wrap(this.heading + Math.sign(err) * Math.min(Math.abs(err), 1.3 * dt));
          this.play('Walk', 0.4);
          if (Math.abs(err) < 0.35) this.asideFaced = true;
          if (this.t < 4) break;
        }
        const done = this.path ? this.walk(dt, 0.75, true) : (this.play('Idle'), this.face(toPlayer, dt), this.t > 1.5);
        if ((done && this.t > 1.2) || this.t > 9) {
          this.path = null;
          this.asideEnd = this.time;
          this.setState(this.resume ?? 'look');
          if (this.state === 'look') this.dur = rand(3, 6);
          if ((this.state === 'amble' || this.state === 'return') && this.resumeTo) this.pathTo(this.resumeTo.x, this.resumeTo.y);
          if (this.state === 'follow') this.t = this.followT ?? 0;
        }
        break;
      }
    }
  }

  // turn toward `want` on the spot; true once facing it
  face(want, dt) {
    const err = wrap(want - this.heading);
    this.heading = wrap(this.heading + Math.sign(err) * Math.min(Math.abs(err), this.o.turnInPlace * dt));
    return Math.abs(err) < 0.12;
  }

  afterWave() {
    if (this.time - this.followedAt > this.o.cooldown) {
      this.followedAt = this.time;
      this.followFor = rand(...this.o.followTime);
      this.setState('follow');
      this.moving = false;
    } else { this.setState('look'); this.dur = rand(4, 7); this.poi = null; this.lookAt = 'player'; }
  }

  farewell(why) {
    this.followedAt = this.time;          // (the follow cooldown runs from the goodbye)
    this.wavedAt = this.time;
    this.setState('farewell', { why });
    this.path = null;
    if (this.seen) this.play('Wave'); else this.play('Idle');
  }

  stepAside(pp) {
    // it turns to face them (if they came up from the side or behind), then backs off a few
    // steps, straight away from them or angled off to one side where the trunks leave room
    const away = new THREE.Vector2(this.pos.x - pp.x, this.pos.y - pp.z).normalize();
    let goal = null;
    const tries = [[0, 5], [0.6, 5], [-0.6, 5], [1.1, 4.5], [-1.1, 4.5], [1.6, 4], [-1.6, 4]];
    for (const [da, r] of tries) {
      const dir = away.clone().rotateAround(new THREE.Vector2(), da);
      const g = this.pos.clone().addScaledVector(dir, r);
      if (this.nav.walkable(this.nav.idx(g.x, g.y)) && this.nav.clearLine(this.pos, g)) { goal = g; break; }
    }
    // afterwards: back to following, or on its way (home, to what it was going to look at)
    this.resume = ['follow', 'return', 'amble'].includes(this.state) ? this.state : 'look';
    this.resumeTo = this.path ? this.path[this.path.length - 1].clone() : null;
    if (this.state === 'follow') this.followT = this.t;
    this.setState('aside', { room: !!goal });
    this.asideFaced = false;
    this.path = goal ? [this.pos.clone(), goal] : null;
    this.pathI = 1;
  }

  // where it goes next: another thing to look at, or home to rest
  next() {
    this.poiCount++;
    if (this.state !== 'rest' && this.poiCount % this.o.restEvery === 0) {
      const h = this.pois.find((p) => p.kind === 'home');
      this.poi = h;
      this.pathTo(h.stand.x, h.stand.y);
      this.resting = true;
      this.setState('amble', { to: 'rest' });
      return;
    }
    const cand = this.pois.map((p, i) => ({ p, i })).filter(({ p, i }) => i !== this.lastPoi && p.kind !== 'home');
    const w = cand.map(({ p }) => 1 / (6 + p.stand.distanceTo(this.pos)) * (p.kind === 'creek' ? 1.5 : 1));
    let r = Math.random() * w.reduce((a, b) => a + b, 0), k = 0;
    while (k < cand.length - 1 && (r -= w[k]) > 0) k++;
    const c = cand[k];
    if (!c) { this.setState('look'); this.dur = rand(...this.o.look); return; }
    this.lastPoi = c.i;
    this.poi = c.p;
    this.resting = false;
    if (!this.pathTo(c.p.stand.x, c.p.stand.y)) { this.setState('look'); this.dur = rand(2, 4); return; }
    this.setState('amble', { to: c.p.kind });
  }

  // which way its resting body (restBody) fits between the trunks here: the heading nearest its
  // own with the most room, or null (then it rests standing)
  roomToRest() {
    const [f, b, w] = this.o.restBody;
    let best = null, bd = 1e9;
    for (let k = 0; k < 16; k++) {
      const h = wrap(this.heading + (k % 2 ? 1 : -1) * Math.ceil(k / 2) * (Math.PI / 8));
      const sx = Math.sin(h), sz = Math.cos(h);
      let ok = true;
      for (let u = -b + w * 0.6; u <= f - w * 0.6 + 1e-3 && ok; u += 1) ok = this.free(this.pos.x + sx * u, this.pos.y + sz * u, w);
      if (ok && Math.abs(wrap(h - this.heading)) < bd) { bd = Math.abs(wrap(h - this.heading)); best = h; }
    }
    return best;
  }

  arrive() {
    this.path = null;
    if (this.resting) { this.resting = false; this.restHeading = this.roomToRest(); this.setState('rest'); this.dur = rand(...this.o.rest); return; }
    if (this.poi?.kind === 'tree' && this.poi.pat && Math.random() < this.o.patChance) { this.setState('pat'); this.patting = false; return; }
    this.setState('look', { what: this.poi?.kind });
    this.dur = rand(...this.o.look);
  }

  // ------------------------------------------------------------ head, eyes, tilt (after the mixer)
  pose(eye) {
    const tgt = this.lookAt === 'player' ? eye : this.lookAt;
    this.tilt += (this.tiltTarget - this.tilt) * Math.min(1, this.mixerDt + 0.05);
    this.root.updateMatrixWorld(true);
    const lying = this.current === this.actions.CrawlIdle;
    if (this.head && tgt) turnToward(this.head, tgt, lying ? 0.35 : this.o.headLimit, this.headFwd);
    if (this.head && Math.abs(this.tilt) > 1e-3) {
      this.head.quaternion.multiply(new THREE.Quaternion().setFromAxisAngle(this.headFwd, this.tilt));
      this.head.updateMatrixWorld(true);
    }
    for (const e of this.eyes) {
      e.o.quaternion.copy(e.rest);
      e.o.updateMatrixWorld(true);
      if (tgt) turnToward(e.o, tgt, this.o.eyeLimit);
    }
  }

  // footfalls from the Walk clip's phase (audio.js GAIT: both feet land at 0 and 0.5), soft breaths
  sounds() {
    const sfx = window.__sfx;
    const a = this.actions.Walk;
    if (!sfx?.play || !a || this.current !== a) { this.walkPhase = null; }
    else {
      const dur = a.getClip().duration, ph = (((a.time % dur) + dur) % dur) / dur;
      if (this.walkPhase != null) for (const at of [0, 0.5]) {
        const crossed = this.walkPhase <= ph ? this.walkPhase < at && at <= ph : at > this.walkPhase || at <= ph;
        if (crossed) sfx.play('g_step', [this.pos.x, this.groundY, this.pos.y], { gain: 0.45 });
      }
      this.walkPhase = ph;
    }
    if (sfx?.play && this.time >= (this.breathAt ?? 3)) {
      sfx.play(this.inhale ? 'g_breath_in' : 'g_breath_out', [this.pos.x, this.groundY + 6, this.pos.y], { gain: 0.3, jitter: 0.06 });
      this.inhale = !this.inhale;
      this.breathAt = this.time + rand(2.2, 3.4);
    }
  }
}
