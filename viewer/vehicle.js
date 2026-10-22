import * as THREE from 'three';

// The estate's car (car_ev: blender/assets/car_ev.py), drivable: the same vehicle in the house
// level (viewer/vehicle_house.js) and in the wilderness worlds (viewer/wild/vehicle_wild.js), so
// it feels the same on both sides of the gate and of the cove <-> town seam.
//
//   E at the driver's door (the car's left, +x)   get in: the camera moves to the driver's seat
//   W / S   throttle / brake (S at a standstill: reverse; W while rolling back: brake)
//   A / D   steer (rate-limited, less lock at speed)      Space  handbrake (the rear wheels lock)
//   V       driver's seat <-> chase camera                E      get out (below ~7 km/h)
//
// The model ("arcade-sim"): a planar rigid body (mass, yaw inertia) on four tyres with slip-angle
// grip saturating at mu x load (a friction circle per tyre: braking or driving eats cornering
// grip; the handbrake drops the rear's), AWD drive limited by force and power, drag, rolling
// resistance, regen when coasting and an auto-hold at a standstill (it doesn't creep down
// grades). The body rides four spring-damper struts on the ground under each wheel: heave, pitch
// and roll, so it squats, dives, leans in corners, follows grades and banks and gets light over
// crests. Each tyre's load is its strut's force (load transfer for free). On a slope the ground's
// reaction pushes it downhill. Collisions: the body's footprint (a rotated rectangle) against
// the level's boxes (house walls, props, the hedge, trunks and rocks), impulses with friction, so
// a glancing hit slides and turns it; guardrails are one-sided walls along the road. Fixed
// 1/120 s substeps.
//
// The environment it drives in (`env`, from the adapters):
//   ground(x, z, yRef)  height of the drivable surface at (x, z): the highest one at most STEP
//                       over yRef (a kerb is driven up; anything taller is a wall)
//   normal(x, z)        the ground normal there ([x, y, z]); optional (flat)
//   boxes(x0, z0, x1, z1, out)   the level's Box3s overlapping that rectangle (walls and ground)
//   rails               [{ax, az, bx, bz, nx, nz}] one-sided walls (n points back to the road)
//   water(x, z)         the water surface there (NaN = none); optional
//   toEstate(x, z) -> [ex, ey] / fromEstate(ex, ey) -> [x, z]   the shared estate frame
//   skip(box)           boxes the car ignores (the estate's see-through boundary)

export const SPEC = {
  mass: 2150,                // kg
  yawInertia: 4300,          // kg m^2
  pitchInertia: 3600, rollInertia: 900,
  cgHeight: 0.52,
  // wheels (car frame: x left, z forward, y up; the origin is the floor centre, tyres on y = 0)
  wheels: [[0.822, 1.55], [-0.822, 1.55], [0.822, -1.50], [-0.822, -1.50]],   // FL FR RL RR
  wheelRadius: 0.36,
  halfWidth: 0.98, front: 2.45, rear: 2.45, roof: 1.42,
  // suspension (per wheel): ~1.45 Hz heave, ~0.35 damping ratio; sag at rest = m g / 4k
  spring: 45000, damper: 3400, bump: 0.10, bumpStiff: 400000,
  // tyres
  mu: 1.05, corner: 13,      // grip coefficient; cornering stiffness (x load per rad of slip)
  // drive (AWD, 40/60), brakes, resistances
  driveForce: 13500, power: 330000, vmax: 50, reverseForce: 6500, vReverse: 8,
  brake: 1.0, regen: 0.05, roll: 0.012, dragArea: 0.62,
  frontDrive: 0.4,
  // steering
  steerMax: 0.6, steerFade: 17, steerRate: 1.5, steerReturn: 2.6,
  STEP: 0.42,                // highest kerb driven up
  seat: [0.40, 1.16, -0.16], // the driver's eye
  door: [1.05, 0.9, 0.05],   // the driver's door handle (for the prompt)
  exitSide: 1.55,            // m out from the centre line where the driver stands after getting out
};

const G = 9.81;
const H = 1 / 120;
const _v = new THREE.Vector3(), _q = new THREE.Quaternion(), _e = new THREE.Euler(0, 0, 0, 'YXZ');
const clamp = (x, a, b) => (x < a ? a : x > b ? b : x);
const FLIP = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), Math.PI);

// ------------------------------------------------------------------ boxes broadphase
// The level's Box3s in a 2D grid (fixed ones; the rest, which may move, tested one by one).
// The colliders array only grows; new entries are indexed as they appear.
export class BoxGrid {
  constructor(boxes, cell = 8) { this.boxes = boxes; this.cell = cell; this.grid = new Map(); this.loose = []; this.n = 0; this.stamp = 0; }
  refresh() {
    const C = this.cell;
    for (; this.n < this.boxes.length; this.n++) {
      const b = this.boxes[this.n];
      if (!b.fixed) { this.loose.push(b); continue; }
      for (let i = Math.floor(b.min.x / C); i <= Math.floor(b.max.x / C); i++)
        for (let k = Math.floor(b.min.z / C); k <= Math.floor(b.max.z / C); k++) {
          const key = (i + 4096) * 8192 + (k + 4096);
          let cell = this.grid.get(key);
          if (!cell) this.grid.set(key, (cell = []));
          cell.push(b);
        }
    }
  }
  query(x0, z0, x1, z1, out) {
    this.refresh();
    const s = ++this.stamp, C = this.cell;
    const hit = (b) => b._vs !== s && b.max.x > x0 && b.min.x < x1 && b.max.z > z0 && b.min.z < z1;
    for (const b of this.loose) if (hit(b)) { b._vs = s; out.push(b); }
    for (let i = Math.floor(x0 / C); i <= Math.floor(x1 / C); i++)
      for (let k = Math.floor(z0 / C); k <= Math.floor(z1 / C); k++) {
        const cell = this.grid.get((i + 4096) * 8192 + (k + 4096));
        if (cell) for (const b of cell) if (hit(b)) { b._vs = s; out.push(b); }
      }
    return out;
  }
}

// ------------------------------------------------------------------ the vehicle
export class Vehicle {
  // root: the car's Object3D (its position / rotation are driven); camera; env (above);
  // player: {pos, vel, eye?, overlapping?(p, h)}; hooks: {onEnter, onExit, onImpact, place(feet), canExit}
  constructor({ root, camera, env, player, hooks = {}, spec = {}, name = 'car_ev' }) {
    this.spec = { ...SPEC, ...spec };
    Object.assign(this, { root, camera, env, player, hooks, name });
    const S = this.spec;
    this.sag = (S.mass * G) / 4 / S.spring;
    // state (world frame): the car origin (floor centre), velocity, yaw (0 = facing +z), body
    this.pos = root.position.clone();
    this.vel = new THREE.Vector3();
    this.yaw = root.rotation.y;
    this.yawRate = 0;
    this.pitch = 0; this.roll = 0; this.pitchRate = 0; this.rollRate = 0;
    this.steer = 0;
    this.comp = [0, 0, 0, 0].map(() => this.sag);   // strut compressions
    this.load = [0, 0, 0, 0];
    this.slip = [0, 0, 0, 0];                       // grip used (0..1+) per tyre, for the squeal
    this.ground = [0, 0, 0, 0];
    this.contact = 0;                               // wheels on the ground
    this.spin = 0;                                  // wheel rotation (rad), for wheel nodes
    this.driving = false;
    this.camMode = 'seat';
    this.gear = 'D';
    this.acc = 0;
    this.aLong = 0; this.aLat = 0;
    this.impact = 0;                                // the last hit's speed (m/s), decays
    this.odo = 0;
    this.stats = { hits: 0, maxHit: 0, air: 0, steps: 0 };
    this.rails = env.rails || [];
    this._cand = [];
    this._q = new THREE.Quaternion();
    this._prevQ = new THREE.Quaternion();
    this.trans = null;                              // the get-in / get-out camera move
    this.wheelNodes = null;
    this.steeringNode = null;
    this.settle();
    this.applyTransform();
  }

  // ---- put the car down at its current pos / yaw: struts at rest on the ground under them
  settle() {
    const S = this.spec;
    const y0 = this.pos.y;
    let hi = -Infinity;
    const f = [Math.sin(this.yaw), Math.cos(this.yaw)], l = [f[1], -f[0]];
    this.gather();
    for (let i = 0; i < 4; i++) {
      const [x, z] = S.wheels[i];
      const g = this.groundAt(this.pos.x + l[0] * x + f[0] * z, this.pos.z + l[1] * x + f[1] * z, y0 + 1.0);
      this.ground[i] = g;
      hi = Math.max(hi, g);
    }
    if (Number.isFinite(hi)) this.pos.y = hi;
    // pitch / roll from the ground plane under the wheels
    const [gFL, gFR, gRL, gRR] = this.ground;
    const len = S.wheels[0][1] - S.wheels[2][1], tr = S.wheels[0][0] - S.wheels[1][0];
    this.pitch = Number.isFinite(gFL + gRR) ? ((gFL + gFR) / 2 - (gRL + gRR) / 2) / len : 0;
    this.roll = Number.isFinite(gFL + gRR) ? ((gFL + gRL) / 2 - (gFR + gRR) / 2) / tr : 0;
    this.pos.y = Number.isFinite(gFL + gRR) ? (gFL + gFR + gRL + gRR) / 4 : this.pos.y;
    this.pitchRate = this.rollRate = 0;
    this.vel.y = 0;
    this.comp = this.comp.map(() => this.sag);
  }

  // ---- the level round the car: candidate boxes for this frame
  gather() {
    const r = this.spec.front + 1.5 + Math.hypot(this.vel.x, this.vel.z) * 0.06;
    this._cand.length = 0;
    this.env.boxes(this.pos.x - r, this.pos.z - r, this.pos.x + r, this.pos.z + r, this._cand);
  }

  groundAt(x, z, yRef) {
    const S = this.spec;
    let g = this.env.ground ? this.env.ground(x, z, yRef) : -Infinity;
    for (const b of this._cand) {
      if (x < b.min.x || x > b.max.x || z < b.min.z || z > b.max.z) continue;
      if (b.max.y > yRef + S.STEP || b.max.y <= g || this.env.skip?.(b)) continue;
      if (b.max.y - b.min.y > 1.5 && b.max.y > yRef + 0.05) continue;   // (a wall's top isn't a road)
      g = b.max.y;
    }
    return g;
  }

  get speed() { return Math.hypot(this.vel.x, this.vel.z); }
  get forwardSpeed() { return this.vel.x * Math.sin(this.yaw) + this.vel.z * Math.cos(this.yaw); }

  // ---- one frame: input {forward, back, left, right, jump} (keys) or {throttle, brake, steer, handbrake}
  update(dt, input = {}) {
    dt *= this.timeScale || 1;                      // (tests: faster than real time)
    const ctl = this.controls(input);
    this._thr = ctl.throttle;
    this._brk = ctl.brake > 0 || ctl.handbrake || (this.driving && ctl.reverse);
    this.gather();
    this.acc += Math.min(dt, 0.2);
    let n = 0;
    while (this.acc >= H && n < 24) { this.step(H, ctl); this.acc -= H; n++; }
    if (n === 24) this.acc = 0;
    this.impact = Math.max(0, this.impact - dt * 4);
    this.applyTransform();
    this.animate(dt);
  }

  // ---- an autopilot (tests, demos): pure pursuit along a polyline [[x, z], ...] (world frame) at up
  // to `speed` m/s, slowing for its curvature (lateral `aLat` m/s²) and for the end; it drives
  // through controls() like the keys would (throttle / brake / steer)
  autopilot(path, { speed = 20, aLat = 5.5, aBrake = 6, stop = true } = {}) {
    // (resampled every metre: the nearest-point search walks it)
    const P = [];
    for (let i = 0; i < path.length; i++) {
      const [x, z] = path[i];
      if (i) {
        const [px, pz] = path[i - 1], d = Math.hypot(x - px, z - pz), n = Math.ceil(d);
        for (let k = 1; k < n; k++) P.push({ x: px + ((x - px) * k) / n, z: pz + ((z - pz) * k) / n });
      }
      P.push({ x, z });
    }
    const s = [0];
    for (let i = 1; i < P.length; i++) s.push(s[i - 1] + Math.hypot(P[i].x - P[i - 1].x, P[i].z - P[i - 1].z));
    // curvature at each point (from the neighbours ~4 m away)
    const kap = P.map((p, i) => {
      let a = i, b = i;
      while (a > 0 && s[i] - s[a] < 4) a--;
      while (b < P.length - 1 && s[b] - s[i] < 4) b++;
      if (a === i || b === i) return 0;
      const ax = p.x - P[a].x, az = p.z - P[a].z, bx = P[b].x - p.x, bz = P[b].z - p.z;
      const t = Math.atan2(ax * bz - az * bx, ax * bx + az * bz);
      return Math.abs(t) / Math.max(1, (s[b] - s[a]) / 2);
    });
    this.auto = { P, s, kap, i: 0, speed, aLat, aBrake, stop, done: false, start: performance.now() };
    return this.auto;
  }

  autoControls() {
    const A = this.auto, S = this.spec, P = A.P;
    const v = this.speed;
    // nearest point ahead of the last one
    let best = Infinity, bi = A.i;
    for (let i = A.i; i < Math.min(P.length, A.i + 400); i++) {
      const d = (P[i].x - this.pos.x) ** 2 + (P[i].z - this.pos.z) ** 2;
      if (d < best) { best = d; bi = i; }
    }
    A.i = bi;
    A.offset = Math.sqrt(best);
    const sNow = A.s[bi], end = A.s[A.s.length - 1];
    if (end - sNow < 2.5 && (!A.stop || v < 0.5)) { A.done = true; }
    // the look-ahead point
    const L = clamp(4 + 0.45 * v, 5, 22);
    let j = bi;
    while (j < P.length - 1 && A.s[j] - sNow < L) j++;
    const fx = Math.sin(this.yaw), fz = Math.cos(this.yaw);
    const tx = P[j].x - this.pos.x, tz = P[j].z - this.pos.z;
    const ang = Math.atan2(fz * tx - fx * tz, fx * tx + fz * tz);       // > 0: the target is to the left
    const wb = S.wheels[0][1] - S.wheels[2][1];
    const delta = Math.atan2(2 * wb * Math.sin(ang), Math.max(L, 1));
    const lock = S.steerMax / (1 + (v / S.steerFade) ** 2);
    // the speed the road ahead allows (the tightest curve within braking distance)
    let vt = A.speed;
    const look = v * v / (2 * A.aBrake) + 15;
    for (let k = bi; k < P.length && A.s[k] - sNow < look; k++) {
      const dist = Math.max(0, A.s[k] - sNow - 4);
      const vc = Math.sqrt(A.aLat / Math.max(A.kap[k], 1e-4));
      vt = Math.min(vt, Math.sqrt(vc * vc + 2 * A.aBrake * dist));
    }
    if (A.stop) vt = Math.min(vt, Math.sqrt(2 * A.aBrake * 0.8 * Math.max(0, end - sNow - 1.5)));
    const vf = this.forwardSpeed;
    const err = vt - vf;
    return { throttle: err > 0.3 ? clamp(err / 3, 0, 1) : 0, brake: err < -0.8 ? clamp(-err / 4, 0, 1) : 0, steer: clamp(delta / lock, -1, 1), handbrake: false };
  }

  controls(i) {
    if (this.hold) return { throttle: 0, brake: 1, steer: 0, handbrake: false };   // (held: the gate's wilderness still loading)
    if (this.auto && !this.auto.done && this.driving) return this.autoControls();
    if (i.throttle !== undefined) return { throttle: clamp(i.throttle, 0, 1), brake: clamp(i.brake || 0, 0, 1), steer: clamp(i.steer || 0, -1, 1), handbrake: !!i.handbrake, reverse: !!i.reverse };
    if (!this.driving) return { throttle: 0, brake: 0, steer: 0, handbrake: false };
    const w = !!i.forward, s = !!i.back, vf = this.forwardSpeed;
    let throttle = 0, brake = 0, reverse = false;
    // W drives forward (brakes while rolling back); S brakes, then reverses from a near stop
    if (w && !s) { if (vf < -0.8) brake = 1; else throttle = 1; }
    else if (s && !w) { if (vf > 0.8) brake = 1; else { throttle = 1; reverse = true; } }
    else if (s && w) brake = 1;
    return { throttle, brake, reverse, steer: (i.left ? 1 : 0) - (i.right ? 1 : 0), handbrake: !!i.jump };
  }

  step(h, c) {
    const S = this.spec, m = S.mass;
    this.stats.steps++;
    const fx = Math.sin(this.yaw), fz = Math.cos(this.yaw), lx = fz, lz = -fx;
    const vLongCar = this.vel.x * fx + this.vel.z * fz;
    const v = Math.hypot(this.vel.x, this.vel.z);
    // steering: rate-limited toward the lock the speed allows
    const lock = S.steerMax / (1 + (v / S.steerFade) ** 2);
    const target = c.steer * lock;
    const rate = Math.abs(target) < Math.abs(this.steer) || target * this.steer < 0 ? S.steerReturn : S.steerRate;
    this.steer += clamp(target - this.steer, -rate * h, rate * h);
    this.gear = c.reverse ? 'R' : vLongCar < -0.5 ? 'R' : 'D';
    // ---- struts: the ground under each wheel, spring + damper (+ bump stop)
    let Fsum = 0, Mp = 0, Mr = 0, contact = 0, nxs = 0, nzs = 0;
    const F = this.load;
    const nrm = this.env.normal;
    for (let i = 0; i < 4; i++) {
      const [x, z] = S.wheels[i];
      const wx = this.pos.x + lx * x + fx * z, wz = this.pos.z + lz * x + fz * z;
      const yb = this.pos.y + z * this.pitch + x * this.roll;       // where this corner's tyre would touch (at rest)
      const g = this.groundAt(wx, wz, yb);
      this.ground[i] = g;
      const c0 = this.comp[i];
      const ci = Number.isFinite(g) ? g - yb + this.sag : -1;
      const cdot = (ci - c0) / h;
      this.comp[i] = ci;
      let f = 0;
      if (ci > 0) {
        f = S.spring * ci + S.damper * cdot;
        if (ci > this.sag + S.bump) f += S.bumpStiff * (ci - this.sag - S.bump);
        f = clamp(f, 0, m * G * 3);
        contact++;
        if (nrm && f > 0) { const n = nrm(wx, wz); nxs += f * n[0] / n[1]; nzs += f * n[2] / n[1]; }
      }
      F[i] = f;
      Fsum += f; Mp += f * z; Mr += f * x;
    }
    this.contact = contact;
    if (!contact) this.stats.air += h;
    // ---- tyres
    let Fx = nxs, Fz = nzs, Tq = 0;
    const cs = Math.cos(this.steer), sn = Math.sin(this.steer);
    // drive force (both axles), limited by power; electronic top speed
    let drive = 0;
    if (c.throttle > 0) {
      if (c.reverse) drive = -c.throttle * S.reverseForce * clamp(1 - (-vLongCar) / S.vReverse, 0, 1);
      else drive = c.throttle * Math.min(S.driveForce, S.power / Math.max(Math.abs(vLongCar), 1)) * clamp((S.vmax - vLongCar) / 3, 0, 1);
    }
    const hold = c.throttle === 0 && v < 0.35 && contact >= 3;
    const water = this.env.water ? this.env.water(this.pos.x, this.pos.z) : NaN;
    const wet = Number.isFinite(water) ? clamp((water - this.pos.y - 0.15) / 0.6, 0, 1) : 0;
    if (wet > 0.8) drive = 0;                                       // (flooded: no drive)
    for (let i = 0; i < 4; i++) {
      const Fzi = F[i];
      if (Fzi <= 0) { this.slip[i] = 0; continue; }
      const [x, z] = S.wheels[i];
      const front = i < 2;
      const wfx = front ? fx * cs + lx * sn : fx, wfz = front ? fz * cs + lz * sn : fz;
      const wlx = wfz, wlz = -wfx;
      const rx = lx * x + fx * z, rz = lz * x + fz * z;
      const cvx = this.vel.x + this.yawRate * rz, cvz = this.vel.z - this.yawRate * rx;
      const vL = cvx * wfx + cvz * wfz, vT = cvx * wlx + cvz * wlz;
      const grip = (this.env.grip ? this.env.grip(this.pos.x + rx, this.pos.z + rz) : 1) * S.mu * (1 - 0.5 * wet);
      const rearLock = c.handbrake && !front;
      const muT = grip * (rearLock ? 0.42 : 1);
      const alpha = Math.atan2(vT, Math.max(Math.abs(vL), 4));
      let fT = -muT * Fzi * Math.tanh((S.corner * alpha) / muT);
      // longitudinal
      let fL = drive * (front ? S.frontDrive : 1 - S.frontDrive) / 2;
      const sgn = Math.tanh(vL / 0.4);
      fL -= c.brake * S.brake * grip * Fzi * sgn;
      if (rearLock) fL = -grip * 0.85 * Fzi * Math.tanh(vL / 0.25);
      if (c.throttle === 0 && !c.brake) fL -= (S.regen + S.roll) * Fzi * Math.tanh(vL / 1.2);
      else fL -= S.roll * Fzi * Math.tanh(vL / 1.2);
      if (wet > 0) fL -= wet * 0.4 * Fzi * Math.tanh(vL / 1.0);
      // friction circle
      const tot = Math.hypot(fL, fT), cap = grip * Fzi * (rearLock ? 0.85 : 1);
      this.slip[i] = tot / Math.max(cap, 1);
      if (tot > cap) { const k = cap / tot; fL *= k; fT *= k; }
      const wx = fL * wfx + fT * wlx, wz = fL * wfz + fT * wlz;
      Fx += wx; Fz += wz;
      Tq += rz * wx - rx * wz;
    }
    // aerodynamic drag
    const drag = 0.5 * 1.2 * S.dragArea * v;
    Fx -= drag * this.vel.x; Fz -= drag * this.vel.z;
    // ---- integrate the plane
    const ax = Fx / m, az = Fz / m;
    this.vel.x += ax * h; this.vel.z += az * h;
    this.yawRate += (Tq / S.yawInertia) * h;
    if (hold && !c.reverse) {                                        // auto-hold: stopped means stopped
      this.vel.x *= 0.6; this.vel.z *= 0.6; this.yawRate *= 0.6;
      if (Math.hypot(this.vel.x, this.vel.z) < 0.05) { this.vel.x = this.vel.z = 0; this.yawRate = 0; }
    }
    if (!contact) this.yawRate *= 1 - 0.2 * h;
    this.aLong = ax * fx + az * fz; this.aLat = ax * lx + az * lz;
    this.pos.x += this.vel.x * h; this.pos.z += this.vel.z * h;
    this.yaw += this.yawRate * h;
    this.odo += v * h;
    // ---- integrate the body: heave, pitch, roll (+ squat / dive / lean from the plane's accelerations)
    this.vel.y += (Fsum / m - G) * h;
    this.pitchRate += ((Mp + m * this.aLong * S.cgHeight * 0.55) / S.pitchInertia) * h;
    this.rollRate += ((Mr + m * this.aLat * S.cgHeight * 0.55) / S.rollInertia) * h;
    if (!contact) { this.pitchRate *= 1 - 1.5 * h; this.rollRate *= 1 - 1.5 * h; }
    this.pos.y += this.vel.y * h;
    this.pitch = clamp(this.pitch + this.pitchRate * h, -0.7, 0.7);
    this.roll = clamp(this.roll + this.rollRate * h, -0.7, 0.7);
    // ---- the floor: never through the ground (bottoming out is a hard stop)
    let lift = 0;
    for (let i = 0; i < 4; i++) {
      const g = this.ground[i];
      if (!Number.isFinite(g)) continue;
      const [x, z] = S.wheels[i];
      const yb = this.pos.y + z * this.pitch + x * this.roll;
      const over = g - yb + this.sag - (this.sag + S.bump + 0.06);
      if (over > lift) lift = over;
    }
    if (lift > 0) { this.pos.y += lift; if (this.vel.y < 0) this.vel.y = 0; }
    // safety net: off the edge of the world (no ground at all): back to the last place it stood
    if (contact >= 3 && this.stats.steps % 60 === 0) (this.lastGood ??= { pos: new THREE.Vector3() }).pos.copy(this.pos), this.lastGood.yaw = this.yaw;
    if (this.lastGood && this.pos.y < this.lastGood.pos.y - 40) {
      this.pos.copy(this.lastGood.pos); this.yaw = this.lastGood.yaw;
      this.vel.set(0, 0, 0); this.yawRate = this.pitchRate = this.rollRate = 0;
      this.stats.rescues = (this.stats.rescues || 0) + 1;
      this.settle();
    }
    // ---- walls
    this.collide(h);
  }

  // the footprint (a rotated rectangle) against the boxes and the rails
  collide(h) {
    const S = this.spec, m = S.mass, I = S.yawInertia;
    const y0 = this.pos.y + S.STEP, y1 = this.pos.y + S.roof;
    for (let pass = 0; pass < 3; pass++) {
      let any = false;
      const fx = Math.sin(this.yaw), fz = Math.cos(this.yaw), lx = fz, lz = -fx;
      const hl = (S.front + S.rear) / 2, off = (S.front - S.rear) / 2, hw = S.halfWidth;
      const cx = this.pos.x + fx * off, cz = this.pos.z + fz * off;
      for (const b of this._cand) {
        if (b.max.y <= y0 || b.min.y >= y1 || this.env.skip?.(b)) continue;
        const bx = (b.max.x - b.min.x) / 2, bz = (b.max.z - b.min.z) / 2;
        if (bx <= 0 || bz <= 0) continue;
        const bcx = (b.max.x + b.min.x) / 2, bcz = (b.max.z + b.min.z) / 2;
        const dx = cx - bcx, dz = cz - bcz;
        // SAT on the four axes; the least overlap is the contact normal (from the box to the car)
        let best = Infinity, nx = 0, nz = 0, carAxis = false;
        const axes = [[1, 0, false], [0, 1, false], [fx, fz, true], [lx, lz, true]];
        let sep = false;
        for (const [ax, az, ca] of axes) {
          const rA = hl * Math.abs(fx * ax + fz * az) + hw * Math.abs(lx * ax + lz * az);
          const rB = bx * Math.abs(ax) + bz * Math.abs(az);
          const d = dx * ax + dz * az;
          const o = rA + rB - Math.abs(d);
          if (o <= 0) { sep = true; break; }
          if (o < best) { best = o; const s = d >= 0 ? 1 : -1; nx = ax * s; nz = az * s; carAxis = ca; }
        }
        if (sep) continue;
        // the contact point: the car's corner deepest in the box, or the box's corner deepest in the car
        let px, pz;
        if (!carAxis) {
          const sf = fx * nx + fz * nz >= 0 ? 1 : -1, sl = lx * nx + lz * nz >= 0 ? 1 : -1;
          px = cx - sf * hl * fx - sl * hw * lx; pz = cz - sf * hl * fz - sl * hw * lz;
        } else {
          px = bcx + (Math.abs(nx) > 1e-3 ? Math.sign(nx) * bx : 0); pz = bcz + (Math.abs(nz) > 1e-3 ? Math.sign(nz) * bz : 0);
          px = clamp(px, b.min.x, b.max.x); pz = clamp(pz, b.min.z, b.max.z);
        }
        this.resolve(nx, nz, best, px, pz, m, I);
        any = true;
      }
      // guardrails: one-sided; a corner past the rail line (within its length) is pushed back
      if (this.rails.length) {
        const corners = [[hl, hw], [hl, -hw], [-hl, hw], [-hl, -hw]];
        for (const r of this.rails) {
          if (Math.abs(r.mx - this.pos.x) > r.half + 4 || Math.abs(r.mz - this.pos.z) > r.half + 4) continue;
          for (const [a, b2] of corners) {
            const px = cx + fx * a + lx * b2, pz = cz + fz * a + lz * b2;
            const tx = r.bx - r.ax, tz = r.bz - r.az, L2 = tx * tx + tz * tz;
            const t = ((px - r.ax) * tx + (pz - r.az) * tz) / L2;
            if (t < 0 || t > 1) continue;
            const d = (px - r.ax) * r.nx + (pz - r.az) * r.nz;          // > 0 on the road side
            if (d < 0 && d > -1.2 && Math.abs(r.y - this.pos.y) < 3) { this.resolve(r.nx, r.nz, -d, px, pz, m, I); any = true; }
          }
        }
      }
      if (!any) break;
    }
  }

  resolve(nx, nz, depth, px, pz, m, I) {
    this.pos.x += nx * (depth + 0.001); this.pos.z += nz * (depth + 0.001);
    const rx = px - this.pos.x, rz = pz - this.pos.z;
    const cvx = this.vel.x + this.yawRate * rz, cvz = this.vel.z - this.yawRate * rx;
    const vn = cvx * nx + cvz * nz;
    if (vn >= 0) return;
    const rn = rz * nx - rx * nz;
    const e = 0.18;
    const j = (-(1 + e) * vn) / (1 / m + (rn * rn) / I);
    this.vel.x += (j * nx) / m; this.vel.z += (j * nz) / m;
    this.yawRate += (j * rn) / I;
    // friction along the wall
    let tx = cvx - vn * nx, tz = cvz - vn * nz;
    const tl = Math.hypot(tx, tz);
    if (tl > 1e-4) {
      tx /= tl; tz /= tl;
      const rt = rz * tx - rx * tz;
      const jt = clamp(-tl / (1 / m + (rt * rt) / I), -0.35 * j, 0.35 * j);
      this.vel.x += (jt * tx) / m; this.vel.z += (jt * tz) / m;
      this.yawRate += (jt * rt) / I;
    }
    const hit = -vn;
    if (hit > 1.2) {
      this.impact = Math.max(this.impact, hit);
      this.stats.hits++; this.stats.maxHit = Math.max(this.stats.maxHit, hit);
      this.hooks.onImpact?.(hit, new THREE.Vector3(px, this.pos.y + 0.6, pz));
    }
  }

  // ---- the model follows the state
  applyTransform() {
    const r = this.root;
    r.position.copy(this.pos);
    r.rotation.set(-this.pitch, this.yaw, this.roll, 'YXZ');
    r.updateMatrixWorld(true);
    // (the camera's frame in the car: three cameras look down their -z, the car faces +z)
    this._q.setFromEuler(r.rotation).multiply(FLIP);
  }

  // wheel spin + steer, steering wheel (if the model has the nodes: car_ev's CarEV_Wheel_* / CarEV_SteeringWheel)
  animate(dt) {
    const S = this.spec;
    // brake lights (and reversing): the red lamps brighter; `brakeMats` are this car's own copies
    const brk = !!this._brk && this.driving;
    if (brk !== this._brkOn && this.brakeMats) {
      this._brkOn = brk;
      for (const m of this.brakeMats) m.emissiveIntensity = (m.userData.e0 ??= m.emissiveIntensity) * (brk ? 3.2 : 1);
    }
    this.spin += (this.forwardSpeed / S.wheelRadius) * dt;
    if (!this.wheelNodes) {
      const find = (re) => { let o = null; this.root.traverse((n) => { if (!o && re.test(n.name)) o = n; }); return o; };
      this.wheelNodes = ['FL', 'FR', 'RL', 'RR'].map((k) => find(new RegExp(`_Wheel_${k}$`)));
      this.steeringNode = find(/_SteeringWheel$/);
      for (const n of this.wheelNodes) if (n) n.userData.q0 = n.quaternion.clone();
      if (this.steeringNode) this.steeringNode.userData.q0 = this.steeringNode.quaternion.clone();
    }
    this.wheelNodes.forEach((n, i) => {
      if (!n) return;
      const st = i < 2 ? this.steer : 0;
      n.quaternion.setFromEuler(_e.set(this.spin, st, 0, 'YXZ')).premultiply(n.userData.q0);
      // the wheel drops with its strut (rebound) and rides up over bumps
      const ext = clamp(this.sag - this.comp[i], -this.spec.bump, 0.12);
      n.position.y = (n.userData.y0 ??= n.position.y) - ext;
    });
    const sw = this.steeringNode;
    if (sw) {
      const ax = sw.userData.axis ? _v.fromArray(sw.userData.axis) : _v.set(0, 0.407, -0.914);
      sw.quaternion.setFromAxisAngle(ax, this.steer * 14.5 * 0.5).premultiply(sw.userData.q0);
    }
  }

  // ---- the driver
  seatWorld(out = new THREE.Vector3()) { return out.fromArray(this.spec.seat).applyMatrix4(this.root.matrixWorld); }
  doorWorld(out = new THREE.Vector3()) { return out.fromArray(this.spec.door).applyMatrix4(this.root.matrixWorld); }

  // can the player get in from where they stand (eye position, view direction)?
  inReach(eye, dir) {
    if (this.driving || this.speed > 1.0) return false;
    const d = this.doorWorld(_v);
    const dx = d.x - eye.x, dz = d.z - eye.z, dist = Math.hypot(dx, dz);
    if (dist > 1.9 || Math.abs(d.y - eye.y) > 1.6) return false;
    if (dist < 1.4) return true;                    // (right at the door: whichever way they look)
    // facing the car (its centre or the door)
    const cx = this.pos.x - eye.x, cz = this.pos.z - eye.z, cl = Math.hypot(cx, cz) || 1;
    const fl = Math.hypot(dir.x, dir.z) || 1;
    return (cx * dir.x + cz * dir.z) / (cl * fl) > 0.2 || (dx * dir.x + dz * dir.z) / ((dist || 1) * fl) > 0.5;
  }

  enter() {
    if (this.driving) return false;
    this.driving = true;
    this.camMode = 'seat';
    this.trans = { t: 0, dur: 0.55, from: this.camera.position.clone(), fromQ: this.camera.quaternion.clone() };
    this._prevQ.copy(this._q);
    this.hooks.onEnter?.();
    return true;
  }

  // out on the driver's side (or the other, or behind) where there's room; returns false if not possible now
  exit() {
    if (!this.driving) return false;
    if (this.speed > 2.0) return 'slow';
    const S = this.spec, p = this.player;
    const fx = Math.sin(this.yaw), fz = Math.cos(this.yaw), lx = fz, lz = -fx;
    const tries = [[S.exitSide, 0.1], [-S.exitSide, 0.1], [0, -S.rear - 0.8], [0, S.front + 0.8], [S.exitSide, 1.4], [S.exitSide, -1.4]];
    for (const [a, b] of tries) {
      const x = this.pos.x + lx * a + fx * b, z = this.pos.z + lz * a + fz * b;
      this.gather();
      const g = this.groundAt(x, z, this.pos.y + 0.3);
      if (!Number.isFinite(g)) continue;
      const feet = new THREE.Vector3(x, g + 0.02, z);
      if (this.hooks.place ? this.hooks.place(feet, this) : true) {
        this.driving = false;
        this.trans = null;
        this.hooks.onExit?.(feet);
        return true;
      }
    }
    return false;
  }

  // the camera while driving: the seat (free look relative to the car) or the chase camera
  updateCamera(dt) {
    if (!this.driving) return;
    const cam = this.camera;
    const seat = this.seatWorld(new THREE.Vector3());
    if (this.camMode === 'seat') {
      // the look the mouse has made relative to the car, carried with the car's turn, pitch and roll
      _q.copy(this._prevQ).invert().multiply(cam.quaternion);
      _e.setFromQuaternion(_q, 'YXZ');
      _e.y = clamp(_e.y, -2.3, 2.3); _e.x = clamp(_e.x, -1.1, 0.9); _e.z = 0;
      if (this.trans) _e.set(0, 0, 0, 'YXZ');
      _q.setFromEuler(_e);
      const want = new THREE.Quaternion().copy(this._q).multiply(_q);
      // a little head sway: the body's accelerations
      const sway = new THREE.Vector3(clamp(this.aLat * 0.004, -0.04, 0.04), 0, clamp(this.aLong * 0.003, -0.03, 0.03)).applyQuaternion(this._q);
      seat.add(sway);
      if (this.impact > 0) seat.add(new THREE.Vector3((Math.random() - 0.5) * 0.02, (Math.random() - 0.5) * 0.02, 0).multiplyScalar(Math.min(this.impact, 6)));
      if (this.trans) {
        const tr = this.trans;
        tr.t += dt;
        const k = clamp(tr.t / tr.dur, 0, 1), e = k * k * (3 - 2 * k);
        cam.position.lerpVectors(tr.from, seat, e);
        cam.quaternion.slerpQuaternions(tr.fromQ, want, e);
        if (k >= 1) this.trans = null;
      } else {
        cam.position.copy(seat);
        cam.quaternion.copy(want);
      }
    } else {
      // chase: behind and above, lagging the car's heading a little
      const fx = Math.sin(this.yaw), fz = Math.cos(this.yaw);
      this._chaseYaw = this._chaseYaw ?? this.yaw;
      let dy = this.yaw - this._chaseYaw; dy = Math.atan2(Math.sin(dy), Math.cos(dy));
      this._chaseYaw += dy * Math.min(1, dt * 4);
      const cx = Math.sin(this._chaseYaw), cz = Math.cos(this._chaseYaw);
      const want = new THREE.Vector3(this.pos.x - cx * 6.4, this.pos.y + 2.4, this.pos.z - cz * 6.4);
      const g = this.env.ground ? this.env.ground(want.x, want.z, want.y + 50) : -Infinity;
      if (Number.isFinite(g)) want.y = Math.max(want.y, g + 1.0);
      // the boom stops short of walls (the garage, the house, trunks)
      const head = _v.set(this.pos.x, this.pos.y + 1.5, this.pos.z), dir = want.clone().sub(head);
      let len = dir.length();
      dir.divideScalar(len || 1);
      const boxes = [];
      this.env.boxes(Math.min(head.x, want.x) - 0.5, Math.min(head.z, want.z) - 0.5, Math.max(head.x, want.x) + 0.5, Math.max(head.z, want.z) + 0.5, boxes);
      const ray = new THREE.Ray(head.clone(), dir), hit = new THREE.Vector3();
      for (const b of boxes) {
        if (b.max.y < this.pos.y + 0.6 || this.env.skip?.(b) || b.containsPoint(head)) continue;
        if (ray.intersectBox(b, hit)) { const d = hit.distanceTo(head); if (d < len) len = d; }
      }
      want.copy(head).addScaledVector(dir, Math.max(0.8, len - 0.35));
      if (len < 6) this._chase = null;              // (pulled in: no lag through the wall)
      if (!this._chase) this._chase = want.clone();
      this._chase.lerp(want, Math.min(1, dt * 6));
      cam.position.copy(this._chase);
      cam.lookAt(this.pos.x + fx * 3, this.pos.y + 1.0, this.pos.z + fz * 3);
    }
    this._prevQ.copy(this._q);
    this.seatCull(true);
  }

  // the wheels, brakes and underbody aren't seen from the driver's seat: not drawn there
  seatCull(on) {
    if (!this._unseen) {
      this._unseen = [];
      this.root.traverse((o) => { if (o !== this.root && /_(Wheel_[FR][LR]|Brakes|Underbody)$/.test(o.name)) this._unseen.push(o); });
    }
    const hide = on && this.driving && this.camMode === 'seat';
    if (hide === this._hidden) return;
    this._hidden = hide;
    for (const o of this._unseen) o.visible = !hide;
  }

  toggleCamera() {
    this.camMode = this.camMode === 'seat' ? 'chase' : 'seat';
    this._chase = null; this._chaseYaw = this.yaw;
    if (this.camMode === 'seat') this.camera.quaternion.copy(this._q);
  }

  // ---- the car's state in the estate frame (house x, north y), for the gate and the seam
  state() {
    this.auto = null;
    const [ex, ey] = this.env.toEstate(this.pos.x, this.pos.z);
    return { v: 1, driving: this.driving, ex, ey, y: this.pos.y, yaw: this.yaw, vx: this.vel.x, vz: this.vel.z,
      yawRate: this.yawRate, steer: this.steer, cam: this.camMode, look: this.driving ? this.lookLocal() : null, t: Date.now() };
  }
  lookLocal() { return _q.copy(this._q).invert().multiply(this.camera.quaternion).toArray(); }
  restore(s) {
    this.auto = null;                               // (an autopilot doesn't cross levels)
    const [x, z] = this.env.fromEstate(s.ex, s.ey);
    const gy = this.env.ground ? this.env.ground(x, z, Infinity) : NaN;
    this.pos.set(x, s.y ?? (Number.isFinite(gy) ? gy : this.pos.y), z);
    this.yaw = s.yaw; this.vel.set(s.vx || 0, 0, s.vz || 0); this.yawRate = s.yawRate || 0; this.steer = s.steer || 0;
    this.gather();
    // keep the speed but sit the body on this world's ground
    const keep = this.vel.clone(), yr = this.yawRate;
    this.settle();
    this.vel.copy(keep); this.yawRate = yr;
    this.applyTransform();
    this._prevQ.copy(this._q);
    if (s.driving) {
      this.driving = true;
      this.camMode = s.cam || 'seat';
      this.trans = null;
      if (s.look) this.camera.quaternion.copy(this._q).multiply(_q.fromArray(s.look));
      else this.camera.quaternion.copy(this._q);
      this.updateCamera(0);
    }
  }
}

// ------------------------------------------------------------------ guardrails from the road
// road.json `rails` ({side, s: [s0, s1]}) along the centreline: one-sided segments at the rail's
// offset (the paved half + the shoulder + 0.35 m), their normals pointing back to the road
export function railSegments(R, toWorld = (p) => p) {
  if (!R?.rails?.length) return [];
  const pts = [...R.points, ...(R.ring || [])].map(toWorld);
  const n = pts.length, s = new Float64Array(n);
  for (let i = 1; i < n; i++) s[i] = s[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][2] - pts[i - 1][2]);
  const at = (si) => {
    let lo = 0, hi = n - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (s[m] <= si) lo = m; else hi = m; }
    const t = (si - s[lo]) / Math.max(1e-6, s[hi] - s[lo]);
    const a = pts[Math.max(0, lo - 1)], b = pts[Math.min(n - 1, hi + 1)];
    const tx = b[0] - a[0], tz = b[2] - a[2], tl = Math.hypot(tx, tz) || 1;
    return { x: pts[lo][0] + (pts[hi][0] - pts[lo][0]) * t, y: pts[lo][1] + (pts[hi][1] - pts[lo][1]) * t, z: pts[lo][2] + (pts[hi][2] - pts[lo][2]) * t, rx: -tz / tl, rz: tx / tl };
  };
  const off = R.paved / 2 + R.shoulder + 0.35, out = [];
  for (const r of R.rails) {
    const [s0, s1] = r.s;
    let prev = null;
    for (let si = s0; si <= s1 + 1e-6; si += Math.min(2, Math.max(0.5, s1 - s0))) {
      const p = at(Math.min(si, s1));
      const q = { x: p.x + p.rx * off * r.side, z: p.z + p.rz * off * r.side, y: p.y };
      if (prev) {
        const nx = -p.rx * r.side, nz = -p.rz * r.side;
        out.push({ ax: prev.x, az: prev.z, bx: q.x, bz: q.z, nx, nz, y: (prev.y + q.y) / 2,
          mx: (prev.x + q.x) / 2, mz: (prev.z + q.z) / 2, half: Math.hypot(q.x - prev.x, q.z - prev.z) / 2 });
      }
      prev = q;
    }
  }
  return out;
}

// ------------------------------------------------------------------ sound (Web Audio, synthesised)
// An EV: the inverter's whine and the motor's hum rising with speed (and louder on the throttle),
// tyre roar and wind with speed, a squeal when the tyres run out of grip, a thump on a hit.
// ctx/out: window.__sfx's context and master bus when there is one (the house), else its own.
export class CarAudio {
  constructor(getCtx) { this.getCtx = getCtx; this.on = false; this.nodes = null; }
  start() {
    const r = this.getCtx();
    if (!r?.ctx) return;
    const { ctx, out } = r;
    if (ctx.state === 'suspended') ctx.resume?.();
    if (this.nodes && this.nodes.ctx === ctx) { this.on = true; return; }
    const g = (v = 0) => { const n = ctx.createGain(); n.gain.value = v; return n; };
    const master = g(0); master.connect(out);
    const noise = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
    { const d = noise.getChannelData(0); let b0 = 0, b1 = 0, b2 = 0;
      for (let i = 0; i < d.length; i++) { const w = Math.random() * 2 - 1; b0 = 0.997 * b0 + 0.029 * w; b1 = 0.985 * b1 + 0.032 * w; b2 = 0.95 * b2 + 0.048 * w; d[i] = (b0 + b1 + b2) * 0.6 + w * 0.05; } }
    const src = (buf) => { const s = ctx.createBufferSource(); s.buffer = buf; s.loop = true; s.start(0, Math.random() * 1.5); return s; };
    // whine: two partials through a band-pass
    const w1 = ctx.createOscillator(); w1.type = 'sawtooth';
    const w2 = ctx.createOscillator(); w2.type = 'sine';
    const wbp = ctx.createBiquadFilter(); wbp.type = 'bandpass'; wbp.Q.value = 2.5;
    const wg = g(0), w2g = g(0);
    w1.connect(wbp).connect(wg).connect(master); w2.connect(w2g).connect(master);
    // hum: low sine + its octave
    const h1 = ctx.createOscillator(); h1.type = 'sine';
    const h2 = ctx.createOscillator(); h2.type = 'triangle';
    const hg = g(0); h1.connect(hg); h2.connect(hg); hg.connect(master);
    // road / tyre roar, wind
    const road = src(noise), rlp = ctx.createBiquadFilter(); rlp.type = 'lowpass'; rlp.Q.value = 0.7;
    const rg = g(0); road.connect(rlp).connect(rg).connect(master);
    const wind = src(noise), whp = ctx.createBiquadFilter(); whp.type = 'bandpass'; whp.frequency.value = 900; whp.Q.value = 0.5;
    const windg = g(0); wind.connect(whp).connect(windg).connect(master);
    // squeal
    const sq = src(noise), sbp = ctx.createBiquadFilter(); sbp.type = 'bandpass'; sbp.frequency.value = 1500; sbp.Q.value = 9;
    const sqg = g(0); sq.connect(sbp).connect(sqg).connect(master);
    for (const o of [w1, w2, h1, h2]) o.start();
    this.nodes = { ctx, master, w1, w2, wbp, wg, w2g, h1, h2, hg, rlp, rg, windg, sbp, sqg, noise };
    this.on = true;
  }
  stop() { this.on = false; }
  update(car) {
    const N = this.nodes;
    if (!N) return;
    const t = N.ctx.currentTime, k = 0.08;
    const set = (p, v) => p.setTargetAtTime(v, t, k);
    const v = car.speed, thr = car._thr || 0;
    set(N.master.gain, this.on ? 0.9 : 0);
    const f = 140 + v * 34;
    set(N.w1.frequency, f); set(N.w2.frequency, f * 2.01); set(N.wbp.frequency, f * 1.6);
    set(N.wg.gain, 0.006 + 0.03 * thr * Math.min(1, v / 4 + 0.3) + 0.008 * Math.min(1, v / 25));
    set(N.w2g.gain, 0.003 + 0.012 * thr + 0.004 * Math.min(1, v / 30));
    set(N.h1.frequency, 46 + v * 1.4); set(N.h2.frequency, 92 + v * 2.8);
    set(N.hg.gain, 0.05 + 0.03 * thr);
    set(N.rlp.frequency, 220 + v * 45);
    set(N.rg.gain, Math.min(0.5, 0.004 * Math.pow(v, 1.25)) * (car.contact ? 1 : 0.2));
    set(N.windg.gain, Math.min(0.25, 0.00012 * v * v));
    const slip = Math.max(...car.slip) - 0.82;
    set(N.sqg.gain, v > 3 && slip > 0 ? Math.min(0.35, slip * 1.6) : 0);
    set(N.sbp.frequency, 1300 + 400 * Math.min(1, v / 20));
  }
  thump(hit) {
    const N = this.nodes;
    if (!N) return;
    const c = N.ctx, t = c.currentTime;
    const o = c.createOscillator(), gg = c.createGain();
    o.type = 'sine'; o.frequency.setValueAtTime(90, t); o.frequency.exponentialRampToValueAtTime(38, t + 0.25);
    gg.gain.setValueAtTime(Math.min(0.9, 0.15 + hit * 0.06), t); gg.gain.exponentialRampToValueAtTime(0.001, t + 0.35);
    o.connect(gg).connect(N.master); o.start(t); o.stop(t + 0.4);
    const n = c.createBufferSource(); n.buffer = N.noise;
    const ng = c.createGain(), lp = c.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 2200;
    ng.gain.setValueAtTime(Math.min(0.6, 0.1 + hit * 0.05), t); ng.gain.exponentialRampToValueAtTime(0.001, t + 0.18);
    n.connect(lp).connect(ng).connect(N.master); n.start(t, Math.random()); n.stop(t + 0.2);
  }
  chime() {
    const N = this.nodes;
    if (!N) return;
    const c = N.ctx, t = c.currentTime;
    [[880, 0], [1318.5, 0.12]].forEach(([f, d]) => {
      const o = c.createOscillator(), gg = c.createGain();
      o.type = 'sine'; o.frequency.value = f;
      gg.gain.setValueAtTime(0, t + d); gg.gain.linearRampToValueAtTime(0.05, t + d + 0.01); gg.gain.exponentialRampToValueAtTime(0.0005, t + d + 0.5);
      o.connect(gg).connect(N.master); o.start(t + d); o.stop(t + d + 0.55);
    });
  }
}

// ------------------------------------------------------------------ HUD (speed, gear, keys)
export class CarHud {
  constructor(doc = document) {
    const st = doc.createElement('style');
    st.textContent = `
      #car-hud { position: fixed; left: 50%; bottom: 18px; transform: translateX(-50%); display: none; z-index: 60;
        font: 13px system-ui, sans-serif; color: #eee; text-shadow: 0 1px 3px #000; text-align: center; pointer-events: none; }
      #car-hud.show { display: block; }
      #car-hud .spd { font-size: 34px; font-weight: 600; letter-spacing: .02em; line-height: 1; }
      #car-hud .unit { font-size: 11px; letter-spacing: .14em; color: #bbb; margin-left: 4px; }
      #car-hud .gear { display: inline-block; margin-left: 10px; padding: 1px 7px; border: 1px solid rgba(255,255,255,.6); border-radius: 4px; font-size: 13px; vertical-align: 6px; }
      #car-hud .keys { margin-top: 8px; font-size: 12px; color: #ccc; }
      #car-hud .k, #car-prompt .k { display: inline-block; min-width: 12px; padding: 0 6px; margin: 0 4px 0 10px; border: 1px solid rgba(255,255,255,.7); border-radius: 4px;
        background: rgba(0,0,0,.35); font-size: 11px; font-weight: 600; line-height: 18px; text-shadow: none; }
      #car-prompt { position: fixed; left: 0; width: 100%; top: calc(50% + 64px); text-align: center; display: none; z-index: 60;
        font: 15px system-ui, sans-serif; color: #fff; text-shadow: 0 1px 3px #000, 0 0 8px rgba(0,0,0,.7); pointer-events: none; }
      #car-prompt.show { display: block; }
      #car-prompt .k { margin-left: 0; margin-right: 8px; font-size: 12px; line-height: 19px; }`;
    doc.head.appendChild(st);
    this.el = doc.createElement('div'); this.el.id = 'car-hud';
    this.el.innerHTML = '<div><span class="spd">0</span><span class="unit">MPH</span><span class="gear">D</span></div>' +
      '<div class="keys"><span class="k">W</span>drive<span class="k">S</span>brake / reverse<span class="k">A D</span>steer<span class="k">Space</span>handbrake<span class="k">V</span>view<span class="k">E</span>get out</div>';
    this.prompt = doc.createElement('div'); this.prompt.id = 'car-prompt';
    this.prompt.innerHTML = '<span class="k">E</span>Drive';
    doc.body.appendChild(this.el); doc.body.appendChild(this.prompt);
    this.spd = this.el.querySelector('.spd'); this.gear = this.el.querySelector('.gear');
    this._last = '';
  }
  update(car, showPrompt, msg = null) {
    this.el.classList.toggle('show', car.driving);
    this.prompt.classList.toggle('show', !car.driving && (showPrompt || !!msg));
    if (msg) this.prompt.innerHTML = msg;
    else if (showPrompt && this.prompt.dataset.p !== 'drive') { this.prompt.innerHTML = '<span class="k">E</span>Drive'; this.prompt.dataset.p = 'drive'; }
    if (!car.driving) return;
    const mph = Math.round(Math.abs(car.forwardSpeed) * 2.23694);
    const key = `${mph}|${car.gear}`;
    if (key !== this._last) { this._last = key; this.spd.textContent = mph; this.gear.textContent = car.gear; }
  }
}

// ------------------------------------------------------------------ a soft dark ellipse under the car (one draw call)
export function blobShadow() {
  const c = document.createElement('canvas');
  c.width = 64; c.height = 128;
  const x = c.getContext('2d');
  const g = x.createRadialGradient(32, 64, 4, 32, 64, 62);
  g.addColorStop(0, 'rgba(0,0,0,1)'); g.addColorStop(0.55, 'rgba(0,0,0,0.85)'); g.addColorStop(1, 'rgba(0,0,0,0)');
  x.fillStyle = g;
  x.fillRect(0, 0, 64, 128);
  const t = new THREE.CanvasTexture(c);
  const m = new THREE.MeshBasicMaterial({ map: t, color: 0x000000, transparent: true, opacity: 0.6, depthWrite: false,
    polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -4 });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(2.5, 5.4), m);
  mesh.name = 'Car_Blob';
  mesh.renderOrder = 2;
  mesh.castShadow = mesh.receiveShadow = false;
  return mesh;
}
