import * as THREE from 'three';

// What the player holds and throws.
//   Hand        shows the armed item in the lower right of the view
//   Throwables  flies a thrown item in an arc; glass shatters on impact into
//               shards (one instanced mesh, so a shattered vase is one draw call); the
//               impact is a noise ({position, loudness = the item's `noise`, default 1}).
//               `shatter: false` items (books) thud, bounce off walls and come to rest whole
//               (onRest gets them back, to be picked up again)
//   Flashlight  one SpotLight on the camera (created once, then only its intensity changes:
//               adding a light recompiles every material); a battery that drains while on

export class Hand {
  constructor(camera) {
    this.group = new THREE.Group();
    camera.add(this.group);
    this.id = null;
  }

  show(id, node) {
    if (id === this.id) return;
    this.group.clear();
    this.id = id;
    if (!id || !node) return;
    const model = node.clone(true);
    model.position.set(0, 0, 0);
    model.rotation.set(0, 0, 0);
    model.scale.set(1, 1, 1);
    // fit the item into a ~22 cm box, lower right of the view
    const box = new THREE.Box3().setFromObject(model);
    const size = box.getSize(new THREE.Vector3());
    const scale = Math.min(1, 0.22 / Math.max(size.x, size.y, size.z));
    model.scale.setScalar(scale);
    const centre = box.getCenter(new THREE.Vector3()).multiplyScalar(scale);
    model.position.sub(centre);
    const holder = new THREE.Group();
    holder.add(model);
    if (size.y < 0.02) {                      // flat things (a card) are held up, facing you
      holder.rotation.set(1.25, 0.35, 0.1);
      holder.position.set(0.17, -0.15, -0.38);
    } else {
      holder.rotation.set(0.1, -0.4, 0);
      holder.scale.setScalar(0.8);
      holder.position.set(0.25, -0.2, -0.55);
    }
    holder.traverse((o) => { if (o.isMesh) { o.castShadow = false; o.receiveShadow = false; } });
    this.group.add(holder);
  }
}

const GRAVITY = 12;

export class Throwables {
  constructor(scene, colliders, onShatter, onRest = null) {
    this.scene = scene;
    this.colliders = colliders;
    this.flying = [];
    this.shards = [];      // { mesh, parts: [{p, v, r, w, s, resting}] }
    this.onShatter = onShatter;   // (at, {loudness, item, thud}) on every first impact
    this.onRest = onRest;         // (obj, def) when a whole item has landed
  }

  // throw `node` from `origin` along `dir` (unit vector, world space); def = its pickup definition
  throw(node, origin, dir, def = {}) {
    const obj = node.clone(true);
    obj.position.copy(origin);
    obj.rotation.set(0, 0, 0);
    this.scene.add(obj);
    const vel = dir.clone().multiplyScalar(8).add(new THREE.Vector3(0, 1.8, 0));   // a lob, not a laser
    const spin = new THREE.Vector3(Math.random() * 6 - 3, Math.random() * 4 - 2, Math.random() * 6 - 3);
    const box = new THREE.Box3().setFromObject(obj);
    const radius = box.getSize(new THREE.Vector3()).length() * 0.25;
    const whole = def.shatter === false || def.shatter === 0;
    this.flying.push({ obj, vel, spin, radius, material: firstMaterial(obj), item: def.item, loudness: +(def.noise ?? 1), whole, def, bounces: 0 });
  }

  hit(p, r) {
    return this.colliders.find((c) =>
      p.x > c.min.x - r && p.x < c.max.x + r && p.y > c.min.y - r && p.y < c.max.y + r &&
      p.z > c.min.z - r && p.z < c.max.z + r);
  }

  update(dt) {
    let changed = false;
    for (let i = this.flying.length - 1; i >= 0; i--) {
      const f = this.flying[i];
      const steps = Math.max(1, Math.ceil((f.vel.length() * dt) / 0.03));
      const h = dt / steps;
      for (let s = 0; s < steps; s++) {
        const prev = f.obj.position.clone();
        f.vel.y -= GRAVITY * h;
        f.obj.position.addScaledVector(f.vel, h);
        f.obj.rotation.x += f.spin.x * h;
        f.obj.rotation.y += f.spin.y * h;
        f.obj.rotation.z += f.spin.z * h;
        const centre = new THREE.Box3().setFromObject(f.obj).getCenter(new THREE.Vector3());
        const box = this.hit(centre, f.radius);
        if (box && f.whole) {
          if (!f.heard) { f.heard = true; this.onShatter?.(centre, { loudness: f.loudness, item: f.item, thud: true }); }
          const before = centre.y - (f.obj.position.y - prev.y);
          if ((f.vel.y <= 0 && before >= box.max.y) || ++f.bounces > 12) {   // came down on top of it: rest there
            this.rest(f, box);
            this.flying.splice(i, 1);
            break;
          }
          // hit a side or an underside: back out and bounce off, slower
          f.obj.position.copy(prev);
          f.vel.x *= -0.3; f.vel.z *= -0.3;
          if (f.vel.y > 0) f.vel.y *= -0.3;
          f.spin.multiplyScalar(0.5);
        } else if (box) {
          this.shatter(centre, f.vel, f.material, box, f);
          this.scene.remove(f.obj);
          this.flying.splice(i, 1);
          break;
        }
        if (f.obj.position.y < -5) { this.scene.remove(f.obj); this.flying.splice(i, 1); break; }   // never fall forever
      }
      changed = true;
    }
    for (const group of this.shards) changed = this.updateShards(group, dt) || changed;
    return changed;
  }

  // a whole item lands: flat on the surface it came down on
  rest(f, box) {
    const o = f.obj;
    o.rotation.set(0, o.rotation.y, 0);
    o.updateMatrixWorld(true);
    const b = new THREE.Box3().setFromObject(o);
    o.position.y += box.max.y - b.min.y + 0.001;
    o.updateMatrixWorld(true);
    this.onRest?.(o, f.def);
  }

  shatter(at, vel, material, box, info = {}) {
    const count = 36;
    const geo = new THREE.TetrahedronGeometry(1, 0);
    const mat = material.clone();
    mat.side = THREE.DoubleSide;
    mat.depthWrite = false;
    const mesh = new THREE.InstancedMesh(geo, mat, count);
    mesh.frustumCulled = false;
    // push the burst out of the surface it hit
    const normal = surfaceNormal(at, box);
    const start = at.clone().addScaledVector(normal, 0.03);
    const parts = [];
    for (let i = 0; i < count; i++) {
      const v = new THREE.Vector3(Math.random() - 0.5, Math.random() * 0.8, Math.random() - 0.5)
        .normalize().multiplyScalar(0.8 + Math.random() * 2.2)
        .addScaledVector(normal, 1.2)
        .addScaledVector(vel, 0.15);
      parts.push({
        p: start.clone().add(new THREE.Vector3((Math.random() - 0.5) * 0.08, Math.random() * 0.1, (Math.random() - 0.5) * 0.08)),
        v, r: new THREE.Euler(Math.random() * 6, Math.random() * 6, Math.random() * 6),
        w: new THREE.Vector3(Math.random() * 20 - 10, Math.random() * 20 - 10, Math.random() * 20 - 10),
        s: new THREE.Vector3(0.006 + Math.random() * 0.03, 0.002 + Math.random() * 0.004, 0.006 + Math.random() * 0.025),
        resting: false,
      });
    }
    const group = { mesh, parts };
    this.shards.push(group);
    this.scene.add(mesh);
    this.updateShards(group, 0);
    this.onShatter?.(at, { loudness: info.loudness ?? 1, item: info.item });
  }

  updateShards(group, dt) {
    const m = new THREE.Matrix4(), q = new THREE.Quaternion();
    let moving = false;
    group.parts.forEach((s, i) => {
      if (!s.resting && dt > 0) {
        // small steps so fast shards can't skip through a thin floor or tabletop
        const steps = Math.max(1, Math.ceil((s.v.length() * dt) / 0.015));
        const h = dt / steps;
        for (let k = 0; k < steps && !s.resting; k++) {
          const prevY = s.p.y;
          s.v.y -= GRAVITY * h;
          s.p.addScaledVector(s.v, h);
          const c = this.hit(s.p, 0.002);
          if (!c) continue;
          if (s.v.y <= 0 && prevY >= c.max.y - 0.01) {         // came down onto the top of something
            s.p.y = c.max.y + s.s.y;
            s.v.multiplyScalar(0.3); s.v.y = -s.v.y * 0.3; s.w.multiplyScalar(0.4);
            if (s.v.length() < 0.25) { s.resting = true; s.r.x = s.r.z = 0; s.p.y = c.max.y + s.s.y; }  // lie flat
          } else {                                              // hit a side: step back out and bounce
            s.p.addScaledVector(s.v, -h);
            s.v.x *= -0.4; s.v.z *= -0.4;
          }
        }
        if (s.p.y < -5) s.resting = true;                       // safety: never fall forever
        s.r.x += s.w.x * dt; s.r.y += s.w.y * dt; s.r.z += s.w.z * dt;
        moving = true;
      }
      m.compose(s.p, q.setFromEuler(s.r), s.s);
      group.mesh.setMatrixAt(i, m);
    });
    group.mesh.instanceMatrix.needsUpdate = true;
    return moving;
  }
}

export class Flashlight {
  constructor(camera, { drain = 240, intensity = 40, distance = 20, cone = 35 } = {}) {
    this.camera = camera;
    this.o = { drain, intensity, distance, cone };   // drain: seconds of light per battery
    this.spot = null;
    this.on = false;
    this.battery = 1;
    this._t = 0;
  }

  // the light itself: made once (when the level has a flashlight, or one is first picked up)
  ensure() {
    if (this.spot) return this.spot;
    const o = this.o;
    const spot = new THREE.SpotLight(0xfff0dc, 0, o.distance, THREE.MathUtils.degToRad(o.cone / 2), 0.35, 2);
    spot.castShadow = false;
    spot.name = 'Flashlight';
    spot.position.set(0.12, -0.1, 0.05);        // held low and to the right
    spot.target.position.set(0, -0.02, -1);     // along the view
    this.camera.add(spot, spot.target);
    this.spot = spot;
    return spot;
  }

  // returns false when the battery is flat
  toggle() {
    if (!this.on && this.battery <= 0) return false;
    this.on = !this.on;
    this.ensure();
    return true;
  }
  refill() { this.battery = 1; }

  // where the beam is (house.js: the light cue the Grimble notices): world position and
  // direction of the lit beam, its range (m) and half-angle (degrees); on = false when it's dark
  beam() {
    const position = new THREE.Vector3(), direction = new THREE.Vector3();
    this.camera.getWorldPosition(position);
    this.camera.getWorldDirection(direction);
    return { on: this.on && this.battery > 0, position, direction, range: this.o.distance, cone: this.o.cone / 2 };
  }

  update(dt) {
    if (!this.spot) return;
    if (this.on) {
      this.battery = Math.max(0, this.battery - dt / this.o.drain);
      if (this.battery === 0) this.on = false;
    }
    this._t += dt;
    // a weak battery dims the beam and makes it stutter
    const b = this.battery;
    let k = b > 0.15 ? 1 : 0.35 + 0.65 * (b / 0.15);
    if (b < 0.1 && Math.sin(this._t * 23) * Math.sin(this._t * 7.3) > 0.55) k *= 0.25;
    this.spot.intensity = this.on ? this.o.intensity * k : 0;
  }
}

function firstMaterial(obj) {
  let mat = null;
  obj.traverse((o) => { if (!mat && o.isMesh) mat = o.material; });
  return mat || new THREE.MeshStandardMaterial({ color: 0x888888, transparent: true, opacity: 0.4 });
}

// which face of the box the point is nearest to -> its outward normal
function surfaceNormal(p, b) {
  const d = [
    [p.x - b.min.x, new THREE.Vector3(-1, 0, 0)], [b.max.x - p.x, new THREE.Vector3(1, 0, 0)],
    [p.y - b.min.y, new THREE.Vector3(0, -1, 0)], [b.max.y - p.y, new THREE.Vector3(0, 1, 0)],
    [p.z - b.min.z, new THREE.Vector3(0, 0, -1)], [b.max.z - p.z, new THREE.Vector3(0, 0, 1)],
  ];
  return d.sort((a, c) => Math.abs(a[0]) - Math.abs(c[0]))[0][1];
}
