import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { ATMOSPHERE_PARS } from './atmosphere.js';
import { Vehicle, BoxGrid, CarAudio, CarHud, railSegments, blobShadow } from '../vehicle.js';
import { linkRegistry, GATE, OFFSET_Z } from '../estate_link.js';

// The estate's car in the wilderness worlds (viewer/vehicle.js has the vehicle). It arrives three ways:
//   - through the estate's gate from the house, with the player driving (the link registry's
//     'vehicle': the house's iframe host hands its state over with the player's)
//   - across the cove <-> town seam: wild.html reloads into the other world (town.js Exits); the
//     car's state (estate frame, so the two worlds' offsets don't matter) goes into
//     sessionStorage on the way out (pagehide) and is picked up on the way in, speed and all
//   - parked: a car left in a world (the player walked on) is put back there when that world
//     loads again in this tab
// URL (tests, a quick drive): car=drive starts in it on the county road just out of the gate (the
// town: at the seam); car=s:<m> on the road at <m> metres along it; car=<ex>,<ey>,<yawDeg> anywhere
// (estate frame); car=0 never loads it.
// Drawn like the Grimble: its PBR materials with the sky as environment and one sun
// (DirectionalLight), the shader taking the level's light map (canopy shadow, sky visibility)
// and the aerial perspective. ~25 draw calls while it's in view, 40k triangles, 0.25 MB (+ the
// textures shared with the estate).
// Ground: the heightfield (the road sits on the corridor's flat core) + the world's boxes (logs,
// rocks, decks); walls: the boxes (trunks, boulders, the estate's hedge and house) and the road's
// guardrails (one-sided, road.json `rails`).

const SEAM_KEY = 'gt_vehicle_seam', PARK_KEY = 'gt_vehicle_parked';
const read = (k) => { try { return JSON.parse(sessionStorage.getItem(k) || 'null'); } catch { return null; } };
const write = (k, v) => { try { if (v == null) sessionStorage.removeItem(k); else sessionStorage.setItem(k, JSON.stringify(v)); } catch { /* no storage */ } };
const _d = new THREE.Vector3();

export class WildCar {
  constructor({ world, worldName, scene, camera, player, colliders, uniforms, tex, sky, params, exits, embedded }) {
    Object.assign(this, { world, worldName, scene, camera, player, colliders, uniforms, tex, sky, params, exits, embedded });
    const [ox, oy] = world.meta?.estate_offset || [0, -810];
    this.estate = !!world.estate;
    this.ox = ox; this.oy = oy;
    this.car = null;
    this.away = true;                    // not in this world (until it arrives or is parked here)
    this.pending = null;
    this.hud = new CarHud(document);
    this.grid = new BoxGrid(colliders);
    this.rails = [];
    this.roadReady = fetch(`../build/wilderness/${world.name}/world/road.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null)
      .then((R) => { this.road = R; this.rails = railSegments(R); if (this.car) this.car.rails = this.rails; return R; });
    let own = null;
    this.audio = new CarAudio(() => {
      // (inside the house's iframe the parent has the user activation: its AudioContext can start)
      const host = embedded ? (() => { try { return window.parent.AudioContext ? window.parent : window; } catch { return window; } })() : window;
      if (!own) { const AC = host.AudioContext || host.webkitAudioContext; if (!AC) return null; own = new AC(); }
      return { ctx: own, out: own.destination };
    });
    const reg = linkRegistry();
    reg.accept('vehicle', (s) => { if (s?.driving) this.arrive(s); });
    reg.provide('vehicle', () => this.leaving());
    // how it comes into this world
    const seam = read(SEAM_KEY), park = read(PARK_KEY), q = params.get('car');
    if (q === '0') { this.disabled = true; return; }
    if (seam && seam.from !== worldName && Date.now() - seam.t < 60000) { write(SEAM_KEY, null); this.arrive(seam.state); }
    else if (q) this.fromParam(q);
    else if (park?.world === worldName) this.arrive({ ...park.state, driving: false });
    else if (embedded) this.load();      // (the house's gate: have it ready before the player drives through)
    addEventListener('pagehide', () => this.save());
    window.__car = this;
  }

  get driving() { return !!this.car?.driving && !this.away; }

  toEstate(x, z) { return [x + this.ox, -z + this.oy]; }
  fromEstate(ex, ey) { return [ex - this.ox, -(ey - this.oy)]; }

  // ---- the model, once
  load() {
    if (this.ready) return this.ready;
    const loader = new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath('https://unpkg.com/three@0.160.0/examples/jsm/libs/draco/gltf/'));
    this.ready = loader.loadAsync('../assets/models/car_ev.gltf').then((g) => {
      const root = g.scene;
      root.name = 'Wild_Car';
      const env = this.sky?.getEnv ? this.sky.getEnv() : null;
      this.shared = {
        uLight: { value: this.tex.light }, uMapXf: { value: new THREE.Vector4(-this.world.size / 2, -this.world.size / 2, 1 / this.world.size, 1) },
        uGroundY: { value: 0 }, uSkyK: { value: 1.0 }, uSunK: { value: 1.0 },
      };
      const atm = Object.fromEntries(Object.entries(this.uniforms).filter(([k]) => /^u(Horizon|Zenith|SunDir|Haze|FogDensity|FogFalloff|FogBase|Time|HazeMode|Ext|HazeAway|HazeSun|HazeScale|ForestAir|ForestAirK|Bounce)$/.test(k)));
      if (!atm.uBounce) atm.uBounce = { value: new THREE.Color(0.13, 0.14, 0.105) };
      root.traverse((o) => {
        if (!o.isMesh) return;
        o.castShadow = o.receiveShadow = false;
        for (const m of [o.material].flat()) {
          if (env) m.envMap = env;
          m.envMapIntensity = 1;
          if (m.transparent) m.depthWrite = false;
          wildShading(m, { ...atm, ...this.shared });
        }
      });
      // its sun (the Grimble's, if it has one already: one light for both)
      this.sun = this.scene.getObjectByName('Wild_Grimble_Sun') || this.scene.getObjectByName('Wild_Car_Sun');
      if (!this.sun) {
        this.sun = new THREE.DirectionalLight(this.uniforms.uSunColor.value.clone(), Math.PI);
        this.sun.name = 'Wild_Car_Sun';
        this.scene.add(this.sun, this.sun.target);
        this.ownSun = true;
      }
      root.visible = false;
      this.scene.add(root);
      this.blob = blobShadow();
      this.blob.visible = false;
      this.scene.add(this.blob);
      const W = this.world, half = W.size / 2;
      const env2 = {
        ground: (x, z) => W.heightAt(x, z),
        normal: (x, z) => W.normalAt(x, z, 1.5),
        boxes: (x0, z0, x1, z1, out) => this.grid.query(x0, z0, x1, z1, out),
        water: W.waterAt ? (x, z) => W.waterAt(x, z) : null,
        toEstate: (x, z) => this.toEstate(x, z),
        fromEstate: (ex, ey) => this.fromEstate(ex, ey),
        rails: this.rails,
      };
      const player = this.player;
      const hooks = {
        place: (feet) => {
          const g = W.heightAt(feet.x, feet.z);
          feet.y = Math.max(feet.y, g);
          return !(player.overlapping && player.overlapping(feet, player.o?.height ?? 1.8).length);
        },
        onEnter: () => { this.audio.start(); this.audio.chime(); },
        onExit: (feet) => {
          player.pos.copy(feet); player.vel.set(0, 0, 0);
          const e = new THREE.Euler().setFromQuaternion(this.camera.quaternion, 'YXZ');
          e.z = 0; e.x = Math.max(-0.6, Math.min(0.6, e.x));
          this.camera.quaternion.setFromEuler(e);
          player.syncCamera?.();
          this.audio.stop();
          this.car.seatCull(false);
          this.quiet = 0;
        },
        onImpact: (hit) => this.audio.thump(hit),
      };
      this.car = new Vehicle({ root, camera: this.camera, env: env2, player, hooks });
      this.car.rails = this.rails;
      void half;
      const red = new Set(); root.traverse((o) => { if (o.isMesh && /LampRed/.test(o.material.name)) red.add(o.material); });
      this.car.brakeMats = [...red];
      window.__vehicle = this.car;
      return this.car;
    });
    return this.ready;
  }

  // ---- in: state from the house (the gate), the other world (the seam), or parked here
  arrive(s) {
    this.pending = s;
    this.load().then(async () => {
      await this.roadReady;
      const s2 = this.pending;
      this.pending = null;
      if (!s2) return;
      this.away = false;
      this.car.root.visible = true;
      this.car.restore(s2);
      this.asleep = !s2.driving;
      if (s2.driving) this.audio.start();
    }).catch((e) => { console.warn('car:', e); this.pending = null; });
  }

  // ?car=drive | s:<m> | ex,ey,yawDeg
  fromParam(q) {
    this.roadReady.then((R) => {
      let ex, ey, yaw;
      const P = R ? [...R.points, ...(R.ring || [])] : null;
      if ((q === 'drive' || q === '1' || /^(s|back):/.test(q)) && P) {
        const back = q.startsWith('back:');
        const want = /^(s|back):/.test(q) ? +q.split(':')[1] : 12;
        let s = 0, i = 1;
        for (; i < P.length - 1 && s < want; i++) s += Math.hypot(P[i][0] - P[i - 1][0], P[i][2] - P[i - 1][2]);
        const a = P[i - 1], b = P[Math.min(P.length - 1, i + 2)];
        yaw = Math.atan2(b[0] - a[0], b[2] - a[2]) + (back ? Math.PI : 0);
        // the right-hand lane (US): 1.7 m right of the centre line
        const rx = -Math.cos(yaw), rz = Math.sin(yaw);
        [ex, ey] = this.toEstate(P[i][0] + rx * 1.7, P[i][2] + rz * 1.7);
      } else {
        const v = q.split(',').map(Number);
        if (v.length < 2 || v.some((n) => !Number.isFinite(n))) return;
        [ex, ey] = v; yaw = ((v[2] || 0) * Math.PI) / 180;
      }
      this.arrive({ v: 1, driving: true, ex, ey, y: null, yaw, vx: 0, vz: 0, t: Date.now() });
    });
  }

  // ---- out: to the house through the gate (it goes with the player)
  leaving() {
    if (!this.driving) return null;
    const s = this.car.state();
    this.away = true;
    this.car.driving = false;
    this.car.root.visible = false;
    if (this.blob) this.blob.visible = false;
    this.audio.stop(); this.audio.update(this.car);
    this.car.seatCull(false);
    this.hud.update(this.car, false);
    write(PARK_KEY, null);
    return s;
  }

  // the page is going (the seam's reload, or back to the house stand-alone): remember the car
  save() {
    if (!this.car || this.away) return;
    if (this.car.driving && this.exits?.leaving) write(SEAM_KEY, { from: this.worldName, state: this.car.state(), t: Date.now() });
    else if (!this.car.driving) write(PARK_KEY, { world: this.worldName, state: this.car.state() });
  }

  key(code) {
    if (this.disabled || !this.car || this.away) return false;
    const car = this.car;
    if (car.driving) {
      if (code === 'KeyE') car.exit();
      else if (code === 'KeyV') car.toggleCamera();
      return code !== 'Escape' && code !== 'KeyH';
    }
    if (code === 'KeyE' && this.prompt) { car.enter(); this.asleep = false; return true; }
    return false;
  }

  // each wilderness frame; returns true while the car has the player (the player's own update is skipped)
  update(dt, input) {
    if (this.disabled) return false;
    if (this.pending) return !!this.pending.driving;
    const car = this.car;
    if (!car || this.away) { this.hud.update({ driving: false }, false); return false; }
    if (car.driving || !this.asleep) {
      car.update(dt, car.driving ? input : {});
      car.updateCamera(dt);
      if (!car.driving) { this.quiet = car.speed < 0.05 ? (this.quiet || 0) + dt : 0; if (this.quiet > 0.6) this.asleep = true; }
      // the blob, the sun, the light-map lookups
      const g = this.world.heightAt(car.pos.x, car.pos.z);
      this.shared.uGroundY.value = g;
      this.blob.visible = true;
      this.blob.position.set(car.pos.x, Math.max(g, ...car.ground.filter(Number.isFinite)) + 0.02, car.pos.z);
      this.blob.rotation.set(-Math.PI / 2, 0, car.yaw, 'YXZ');
      this.blob.material.opacity = 0.55 * Math.max(0, 1 - Math.max(0, car.pos.y - g) / 2);
    }
    if (this.sun) {
      if (this.ownSun && this.scene.getObjectByName('Wild_Grimble_Sun')) { this.scene.remove(this.sun); this.sun = this.scene.getObjectByName('Wild_Grimble_Sun'); this.ownSun = false; }
      if (this.ownSun) {
        const d = this.uniforms.uSunDir.value;
        this.sun.target.position.copy(car.pos);
        this.sun.position.copy(car.pos).addScaledVector(d, 60);
      }
    }
    if (car.driving) {
      const seat = car.seatWorld(_d);
      this.player.pos.set(seat.x, seat.y - (this.player.eye ?? 1.65), seat.z);
      this.player.vel.copy(car.vel);
      // (the estate's gate looks for the player in a 3.6 m band inside its line: a car can cross that
      // between two frames, so the crossing frame reports the driver in it)
      const hz = seat.z - OFFSET_Z;
      if (this.estate && this.prevHz > GATE.back && hz <= GATE.back && seat.x > GATE.mouth[0] && seat.x < GATE.mouth[1])
        this.player.pos.z = Math.max(seat.z, GATE.back - 0.4 + OFFSET_Z);
      this.prevHz = hz;
    }
    this.audio.update(car);
    this.prompt = !car.driving && car.inReach(this.camera.position, this.camera.getWorldDirection(_d));
    this.hud.update(car, this.prompt);
    return car.driving;
  }
}

// the wild's light on the car's PBR materials (as viewer/wild/grimble_wild.js does for the Grimble):
// the sun term x the canopy's sun visibility where the sun ray meets the ground, the sky term x the
// sky visibility under it, the warm ground bounce, then the aerial perspective
function wildShading(m, shared) {
  if (m.userData._wildCar) return;
  m.userData._wildCar = true;
  m.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, shared);
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vGWorld;')
      .replace('#include <project_vertex>', '#include <project_vertex>\n\tvGWorld = (modelMatrix * vec4(transformed, 1.0)).xyz;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', ['#include <common>', ATMOSPHERE_PARS,
        'uniform sampler2D uLight;\nuniform vec4 uMapXf;\nuniform vec3 uBounce;\nuniform float uGroundY, uSkyK, uSunK;\nvarying vec3 vGWorld;'].join('\n'))
      .replace('#include <lights_fragment_begin>', [
        'float gH = max(vGWorld.y - uGroundY, 0.0);',
        'vec2 gXZ = vGWorld.xz - uSunDir.xz / max(uSunDir.y, 0.15) * gH;',
        'vec4 gL = textureLod(uLight, (gXZ - uMapXf.xy) * uMapXf.z, 0.0);',
        'vec4 gL0 = textureLod(uLight, (vGWorld.xz - uMapXf.xy) * uMapXf.z, 0.0);',
        'float gSun = gL.a * gL.g * uSunK, gSky = gL0.b * uSkyK;',
        THREE.ShaderChunk.lights_fragment_begin.replace('getDirectionalLightInfo( directionalLight, directLight );',
          'getDirectionalLightInfo( directionalLight, directLight );\n\t\tdirectLight.color *= gSun;'),
      ].join('\n'))
      .replace('#include <lights_fragment_maps>', '#include <lights_fragment_maps>\n\tiblIrradiance *= gSky;\n\tradiance *= gSky;\n#if defined( RE_IndirectDiffuse )\n\tirradiance += uBounce * (0.55 * PI);\n#endif')
      .replace('#include <tonemapping_fragment>', '\tgl_FragColor.rgb = applyAtmosphere(gl_FragColor.rgb, vGWorld);\n#include <tonemapping_fragment>');
  };
  m.customProgramCacheKey = () => 'car-wild';
  m.needsUpdate = true;
}
