import * as THREE from 'three';
import { Vehicle, BoxGrid, CarAudio, CarHud, blobShadow } from './vehicle.js';
import { linkRegistry, GATE } from './estate_link.js';
import { unbatch } from './batching.js';

// The car in the house level (viewer/vehicle.js has the vehicle): the estate's car_ev, parked in
// the garage's west bay, is driven out of the garage (its door opens from the switch by the
// mudroom door), down the motor court and the drive and out through the gate: the gate's
// handoff (estate_gate.js) carries it into the wilderness with the player in it (the link
// registry's 'vehicle' entry), and back.
//
// What the house does differently for it:
//   - parked in its bay it's merged into the garage's batch like a resting pickup (index.html; no
//     draw calls of its own), taken out of it the first time it's driven (batching.js unbatch), and
//     culled with the garage only while parked inside it
//   - its nine part colliders (from mansion.json) are taken out while it's driven (it would hit
//     itself) and put back round it wherever it's parked
//   - lit by the garage's probe while inside, by the sun + the sky outdoors (the materials as
//     loaded, with the sky as their environment); no real-time shadow once it has moved (a soft
//     blob under it instead: the shadow map is only redrawn on demand)
//   - the estate's see-through boundary beyond the hedge is no wall for it (the gate's line is
//     crossed by the driver, 2.6 m behind the bumper)
// Sound: the EV synth (vehicle.js CarAudio) on window.__sfx's context and master bus, the house's
// own door and thud one-shots. URL: ?car=0 leaves the car parked for good (not drivable).

const _d = new THREE.Vector3();

export class HouseCar {
  constructor({ root, proto, asset, batch = null, level, scene, camera, player, colliders, culler, sky, renderer, toast, params }) {
    Object.assign(this, { root, scene, camera, player, colliders, culler, renderer, toast, level, batch });
    this.enabled = params?.get('car') !== '0';
    root.updateMatrixWorld(true);
    // its own part boxes (pushed by index.html's prop loop): found by value
    this.parts = (asset.colliders || [asset.aabb]).map((c) => new THREE.Box3(new THREE.Vector3(...c.min), new THREE.Vector3(...c.max)));
    const placed = this.parts.map((b) => b.clone().applyMatrix4(root.matrixWorld));
    const same = (a, b) => a.min.distanceToSquared(b.min) < 1e-8 && a.max.distanceToSquared(b.max) < 1e-8;
    this.orig = placed.map((p) => colliders.find((c) => same(c, p))).filter(Boolean);
    // once it has moved: six boxes along its length instead (a rotated car's part boxes, made
    // axis-aligned, would stand up to 1.4 m proud of its sides), each as tall as the car there
    const S = 6, L0 = -2.45, L1 = 2.45;
    this.sliceDefs = [...Array(S)].map((_, k) => {
      const z0 = L0 + ((L1 - L0) * k) / S, z1 = L0 + ((L1 - L0) * (k + 1)) / S;
      const top = Math.max(0.6, ...this.parts.filter((b) => b.max.z > z0 + 0.05 && b.min.z < z1 - 0.05).map((b) => b.max.y));
      return { z0, z1, top };
    });
    this.slices = this.sliceDefs.map(() => { const b = new THREE.Box3(new THREE.Vector3(0, -101, 0), new THREE.Vector3(0, -100, 0)); colliders.push(b); return b; });
    this.own = [...this.orig, ...this.slices];
    const ownSet = new Set(this.own);
    this.grid = new BoxGrid(colliders);
    const env = {
      boxes: (x0, z0, x1, z1, out) => this.grid.query(x0, z0, x1, z1, out),
      skip: (b) => b.kind === 'bound' || ownSet.has(b),
      toEstate: (x, z) => [x, -z],
      fromEstate: (ex, ey) => [ex, -ey],
    };
    const hooks = {
      place: (feet) => {
        const h = player.o?.height ?? 1.8;
        if (player.overlapping && player.overlapping(feet, h).length) return false;
        return true;
      },
      onEnter: () => this.entered(),
      onExit: (feet) => this.exited(feet),
      onImpact: (hit, at) => { window.__sfx?.play?.('thud', at, { db: Math.min(6, hit - 4) }); this.audio.thump(hit); },
    };
    this.car = new Vehicle({ root, camera, env, player, hooks });
    this.home = root.position.clone();
    this.moved = false;
    this.away = false;                       // out in the wilderness (the iframe has it)
    this.asleep = true;
    this.quiet = 0;
    // materials: the garage's (as placed, lit by its probe) and outdoor ones (the loaded
    // materials with the sky's environment), swapped as it crosses the garage's door line
    this.meshes = [];
    const pm = [];
    proto.traverse((o) => { if (o.isMesh) pm.push(o); });
    let k = 0;
    const outCache = new Map(), brakeCache = new Map();
    const env2 = sky?.getEnv ? sky.getEnv() : null;
    root.traverse((o) => {
      if (!o.isMesh) return;
      const src = pm[k++]?.material || o.material;
      if (!outCache.has(src)) {
        const m = src.clone();
        if (env2) m.envMap = env2;
        m.envMapIntensity = 1;
        outCache.set(src, m);
      }
      let garage = o.material;
      // (the red lamps: this car's own copies, so its brake lights don't light the other car's)
      if (/LampRed/.test(garage.name)) {
        if (!brakeCache.has(garage)) {
          const m = garage.clone();
          m.onBeforeCompile = garage.onBeforeCompile; m.customProgramCacheKey = garage.customProgramCacheKey;
          brakeCache.set(garage, m);
        }
        garage = o.material = brakeCache.get(garage);
      }
      this.meshes.push({ mesh: o, garage, outdoor: outCache.get(src) });
    });
    this.car.brakeMats = [...new Set(this.meshes.flatMap((m) => [m.garage, m.outdoor]).filter((m) => /LampRed/.test(m.name)))];
    this.inside = true;
    this.garage = level.rooms?.garage?.rect || [13.5, 0, 26, 20];
    this.cullRoom = culler?.rooms.find((r) => r.name === 'garage') || null;
    // the blob shadow (once it has left its bay: the baked floor has its shadow there)
    this.blob = blobShadow();
    this.blob.visible = false;
    scene.add(this.blob);
    // sound
    let own = null;
    this.audio = new CarAudio(() => {
      const s = window.__sfx;
      if (s?.ctx) return { ctx: s.ctx, out: s.master || s.ctx.destination };
      if (!own) { const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return null; own = new AC(); }
      return { ctx: own, out: own.destination };
    });
    this.hud = new CarHud(document);
    this.hintEl = document.getElementById('hint');
    this.crossEl = document.getElementById('cross');
    // across the gate (estate_gate.js's registry): the car goes with the player if they're in it
    const reg = linkRegistry();
    reg.provide('vehicle', () => this.leaving());
    reg.accept('vehicle', (s) => this.arriving(s));
    window.__car = this;
    window.__vehicle = this.car;
  }

  get driving() { return this.car.driving && !this.away; }

  // ---- keys (index.html's keydown, while the pointer is locked); true = taken
  key(code, busy = false) {
    if (!this.enabled || this.away) return false;
    if (this.car.driving) {
      if (code === 'KeyE') {
        const r = this.car.exit();
        if (r === 'slow') this.toast?.('Slow down to get out');
        else if (!r) this.toast?.('No room to get out here');
      } else if (code === 'KeyV') this.car.toggleCamera();
      return code !== 'Escape';
    }
    if (code === 'KeyE' && !busy && this.prompt) { this.enter(); return true; }
    return false;
  }

  enter() {
    window.__sfx?.unlock?.();
    this.car.enter();
  }

  entered() {
    if (this.batch?.batched) unbatch(this.batch);   // (out of the garage's batch: its own meshes from now on)
    this.asleep = false;
    this.moved = true;
    for (const b of this.own) { b.min.set(0, -101, 0); b.max.set(0, -100, 0); }
    // no real-time shadow from here on (the map isn't redrawn per frame); the blob under it
    for (const { mesh } of this.meshes) mesh.castShadow = false;
    this.renderer.shadowMap.needsUpdate = true;
    if (this.cullRoom) { this.cullRoom.objects = this.cullRoom.objects.filter((o) => o !== this.root); this.root.visible = true; }
    this.blob.visible = true;
    window.__sfx?.play?.('door_close', this.car.doorWorld());
    this.audio.start();
    this.audio.chime();
  }

  exited(feet) {
    const p = this.player;
    p.pos.copy(feet); p.vel.set(0, 0, 0);
    p.crouching = false;
    // standing up: the view keeps its heading, level
    const e = new THREE.Euler().setFromQuaternion(this.camera.quaternion, 'YXZ');
    e.z = 0; e.x = Math.max(-0.6, Math.min(0.6, e.x));
    this.camera.quaternion.setFromEuler(e);
    p.syncCamera?.();
    window.__sfx?.play?.('door_close', this.car.doorWorld());
    this.audio.stop();
    this.quiet = 0;
  }

  // its part boxes round it where it stands (each part's box rotated, as an axis-aligned box)
  park() {
    this.root.updateMatrixWorld(true);
    const c = this.car, fx = Math.sin(c.yaw), fz = Math.cos(c.yaw), lx = fz, lz = -fx, w = 0.97;
    this.sliceDefs.forEach((d, i) => {
      const b = this.slices[i];
      b.makeEmpty();
      for (const z of [d.z0, d.z1]) for (const x of [-w, w]) b.expandByPoint(_d.set(c.pos.x + lx * x + fx * z, c.pos.y + 0.15, c.pos.z + lz * x + fz * z));
      b.max.y = c.pos.y + d.top;
    });
    if (this.cullRoom && this.isInside() && !this.cullRoom.objects.includes(this.root)) {
      this.cullRoom.objects.push(this.root);
      this.root.visible = this.cullRoom.shown !== false;
    }
    this.asleep = true;
  }

  isInside() {
    const [x0, z0, x1, z1] = this.garage, p = this.car.pos;
    return p.x > x0 && p.x < x1 && p.z > z0 && p.z < z1 - 0.3;
  }

  // ---- each house frame (index.html, before the player): input = the held keys
  // returns true while the player is in the car (index.html then skips the player's update)
  update(dt, input, { locked = true, busy = false } = {}) {
    if (!this.enabled || this.away) { this.hud.update(this.car, false); return false; }
    const car = this.car;
    if (car.driving || !this.asleep) {
      car.update(dt, car.driving ? input : {});
      car.updateCamera(dt);
      if (!car.driving) {
        this.quiet = car.speed < 0.05 ? this.quiet + dt : 0;
        if (this.quiet > 0.6) this.park();
      }
      // lighting: the garage's probe inside, the sky outside
      const inside = this.isInside();
      if (inside !== this.inside) {
        this.inside = inside;
        for (const m of this.meshes) m.mesh.material = inside ? m.garage : m.outdoor;
      }
      this.updateBlob();
    }
    if (car.driving) {
      // the gate's exit sensor sees a car sooner than a walker (estate_gate.js opens it at 10 m)
      const g = window.__estateGate, p = car.pos;
      if (g && g.t < 1 && !g.opening && !window.__bench && p.x > 12 && p.x < 28 && p.z > GATE.z - 28 && p.z < GATE.line) { g.opening = true; g.preload?.(); }
      // the player rides in the seat: everything that follows the player (the gate, the culler,
      // the invaders' senses) follows the car
      const seat = car.seatWorld(_d);
      this.player.pos.set(seat.x, seat.y - (this.player.eye ?? 1.65), seat.z);
      this.player.vel.copy(car.vel);
    }
    this.audio.update(car);
    // get-in prompt: at the driver's door, looking at the car
    this.prompt = !car.driving && locked && !busy && car.inReach(this.camera.position, this.camera.getWorldDirection(_d));
    this.hud.update(car, this.prompt);
    const hide = car.driving ? 'hidden' : '';
    if (this.hintEl && this.hintEl.style.visibility !== hide) this.hintEl.style.visibility = hide;
    if (this.crossEl && this.crossEl.style.visibility !== hide) this.crossEl.style.visibility = hide;
    return car.driving;
  }

  updateBlob() {
    const c = this.car, b = this.blob;
    const g = c.ground.filter(Number.isFinite);
    b.visible = !this.away && this.root.visible && (this.moved && c.pos.distanceTo(this.home) > 0.5);
    if (!g.length) { b.visible = false; return; }
    b.position.set(c.pos.x, Math.max(...g) + 0.012, c.pos.z);
    b.rotation.set(-Math.PI / 2, 0, c.yaw, 'YXZ');
    const air = Math.max(0, c.pos.y - Math.max(...g));
    b.material.opacity = 0.62 * Math.max(0, 1 - air / 2);
  }

  // ---- the gate: out with the player in it (it's in the wilderness now), or nothing
  leaving() {
    if (!this.car.driving) return null;
    const s = this.car.state();
    this.away = true;
    this.car.driving = false;
    this.root.visible = false;
    this.blob.visible = false;
    for (const b of this.own) { b.min.set(0, -101, 0); b.max.set(0, -100, 0); }
    this.audio.stop();
    this.audio.update(this.car);
    this.hud.update(this.car, false);
    if (this.hintEl) this.hintEl.style.visibility = '';
    if (this.crossEl) this.crossEl.style.visibility = '';
    return s;
  }

  arriving(s) {
    if (!s?.driving) return;
    if (this.batch?.batched) unbatch(this.batch);
    if (this.cullRoom) this.cullRoom.objects = this.cullRoom.objects.filter((o) => o !== this.root);
    this.away = false;
    this.root.visible = true;
    this.asleep = false;
    this.moved = true;
    for (const b of this.own) { b.min.set(0, -101, 0); b.max.set(0, -100, 0); }
    for (const { mesh } of this.meshes) mesh.castShadow = false;
    this.car.restore(s);
    this.inside = !this.isInside();             // (forces the material pass next frame)
    this.audio.start();
  }
}
