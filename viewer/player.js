import * as THREE from 'three';

// First-person character: an upright box (feet at `feet`) moving through a
// world of axis-aligned boxes. Gravity, jumping, sprinting, crouching,
// automatic step-up onto low edges (rugs, thresholds), and landing on top of
// anything (desks, chairs). Movement is substepped so fast falls can't tunnel
// through thin parts like a desktop. Stairs carry an invisible ramp (level.ramps)
// that the feet follow, so climbing them is a smooth glide, not a pop per tread.

const DEFAULTS = {
  radius: 0.25,          // half-width of the player's footprint
  height: 1.8,           // standing
  crouchHeight: 1.1,
  eye: 1.65,             // eye height above the feet, standing
  crouchEye: 0.95,
  walk: 3.4,             // m/s
  run: 6.8,
  crouchSpeed: 1.2,
  gravity: 24,           // m/s² (snappier than 9.8, as in most games)
  jumpHeight: 1.05,      // apex in metres; clears a 0.74 m desk
  stepHeight: 0.3,       // edges this low are walked up without jumping
  airControl: 0.35,      // fraction of ground acceleration available mid-air
  jumpBuffer: 0.15,      // s: a press this long before landing still jumps
  coyoteTime: 0.1,       // s: a press this long after running off an edge still jumps
};

export const KEYS = {
  forward: ['KeyW', 'ArrowUp'], back: ['KeyS', 'ArrowDown'],
  left: ['KeyA', 'ArrowLeft'], right: ['KeyD', 'ArrowRight'],
  run: ['ShiftLeft', 'ShiftRight'], jump: ['Space'], crouch: ['KeyC'],
};

export class Player {
  constructor(camera, colliders, feetPosition, opts = {}) {
    this.o = { ...DEFAULTS, ...opts };
    this.camera = camera;
    this.boxes = colliders;
    // {x: [x0, x1], z: [z0, z1], y: [y0, y1]}: height y0 at x0 rising linearly to y1 at x1
    this.ramps = opts.ramps || [];
    this._onRamp = false;
    this.pos = new THREE.Vector3(...feetPosition);  // feet centre
    this.vel = new THREE.Vector3();
    this.grounded = false;
    this.crouching = false;
    this._jumpHeld = false;
    this._jumpBuffer = 0;     // time left on a remembered jump press
    this._sinceGround = 1;    // time since last grounded
    this.height = this.o.height;
    this.eye = this.o.eye;
    this._box = new THREE.Box3();
    this.syncCamera();
  }

  // player box at the given feet position and height
  boxAt(p, h = this.height) {
    const r = this.o.radius;
    this._box.min.set(p.x - r, p.y, p.z - r);
    this._box.max.set(p.x + r, p.y + h, p.z + r);
    return this._box;
  }

  overlapping(p, h = this.height) {
    const b = this.boxAt(p, h), e = 1e-4;
    return this.boxes.filter((c) =>
      b.max.x > c.min.x + e && b.min.x < c.max.x - e &&
      b.max.y > c.min.y + e && b.min.y < c.max.y - e &&
      b.max.z > c.min.z + e && b.min.z < c.max.z - e);
  }

  update(dt, input) {
    const o = this.o;
    // crouch: shrink now, stand up only when there's headroom
    const wantCrouch = input.crouch;
    if (wantCrouch && !this.crouching) this.crouching = true;
    if (!wantCrouch && this.crouching && this.overlapping(this.pos, o.height).length === 0) this.crouching = false;
    this.height = this.crouching ? o.crouchHeight : o.height;
    const eyeTarget = this.crouching ? o.crouchEye : o.eye;
    this.eye += (eyeTarget - this.eye) * Math.min(1, dt * 12);

    // desired horizontal velocity from input, relative to where the camera looks
    const fwd = new THREE.Vector3();
    this.camera.getWorldDirection(fwd);
    fwd.y = 0; fwd.normalize();
    const right = new THREE.Vector3(-fwd.z, 0, fwd.x);
    const wish = new THREE.Vector3()
      .addScaledVector(fwd, (input.forward ? 1 : 0) - (input.back ? 1 : 0))
      .addScaledVector(right, (input.right ? 1 : 0) - (input.left ? 1 : 0));
    if (wish.lengthSq() > 0) wish.normalize();
    const speed = this.crouching ? o.crouchSpeed : input.run ? o.run : o.walk;
    wish.multiplyScalar(speed);
    const accel = (this.grounded ? 14 : 14 * o.airControl) * dt;
    this.vel.x += (wish.x - this.vel.x) * Math.min(1, accel);
    this.vel.z += (wish.z - this.vel.z) * Math.min(1, accel);

    // jump on the press (not while held), remembered briefly, and still allowed just after
    // running off an edge: a tap never gets lost to a single frame's state
    if (input.jump && !this._jumpHeld) this._jumpBuffer = o.jumpBuffer;
    this._jumpHeld = input.jump;
    this._sinceGround = this.grounded ? 0 : this._sinceGround + dt;
    if (this._jumpBuffer > 0 && this._sinceGround <= o.coyoteTime && this.vel.y <= 0.5) {
      this.vel.y = Math.sqrt(2 * o.gravity * o.jumpHeight);
      this.grounded = false;
      this._jumpBuffer = 0;
      this._sinceGround = o.coyoteTime + 1;
    }
    this._jumpBuffer = Math.max(0, this._jumpBuffer - dt);
    this.vel.y -= o.gravity * dt;

    // substep so no single move exceeds 4 cm
    const travel = Math.max(Math.abs(this.vel.x), Math.abs(this.vel.y), Math.abs(this.vel.z)) * dt;
    const steps = Math.max(1, Math.ceil(travel / 0.04));
    const h = dt / steps;
    for (let i = 0; i < steps; i++) {
      this.moveHorizontal('x', this.vel.x * h);
      this.moveHorizontal('z', this.vel.z * h);
      this.moveVertical(this.vel.y * h);
      this.depenetrate();
    }
    // grounded = something solid right under the feet, decided once per frame. (Set per
    // substep it flickered: after landing in the first substep, the later ones move 0 m
    // vertically and touch nothing, so at a run the player read as airborne most frames.)
    if (this.vel.y <= 0) {
      const probe = this.pos.clone();
      probe.y -= 0.03;
      this.grounded = this._onRamp || this.overlapping(probe).some((c) => c.max.y <= this.pos.y + 0.01);
    } else {
      this.grounded = false;
    }
    this.syncCamera();
  }

  // Move along one horizontal axis. Boxes we run into stop us at the side we were
  // approaching from (the nearest one wins); low edges are stepped up onto. Boxes we
  // were already inside on this axis are left to depenetrate(), so a bad start
  // never flings the player through to a box's far side.
  moveHorizontal(axis, d) {
    if (d === 0) return;
    const r = this.o.radius;
    const start = this.pos[axis];
    this.pos[axis] += d;
    let limit = null;
    for (const c of this.overlapping(this.pos)) {
      if (this.tryStepUp(c)) continue;
      const side = d > 0 ? c.min[axis] - r - 1e-3 : c.max[axis] + r + 1e-3;
      const wasOutside = d > 0 ? start <= side + 1e-3 : start >= side - 1e-3;
      if (!wasOutside) continue;
      limit = limit === null ? side : d > 0 ? Math.min(limit, side) : Math.max(limit, side);
    }
    if (limit !== null) {
      this.pos[axis] = limit;
      this.vel[axis] = 0;
    }
  }

  // low edge (rug, threshold, step) right in front: climb onto it if there's room.
  // Never while rising: mid-jump it would boost the jump off the edge of a table.
  tryStepUp(c) {
    if (this.vel.y > 0) return false;
    const rise = c.max.y - this.pos.y;
    // full steps only on foot; in the air just enough to catch an edge when landing (more
    // would let a jump off a table "climb" onto a 2 m shelf on the way down)
    const max = this.grounded ? this.o.stepHeight : 0.1;
    if (rise <= 0 || rise > max) return false;
    const up = this.pos.clone();
    up.y = c.max.y;
    if (this.overlapping(up).length) return false;
    this.pos.y = c.max.y;
    return true;
  }

  // Fall/rise. Land only on tops that were under the feet before the move, bump only
  // on undersides that were above the head. A box overlapped from the
  // side (a wall) never moves the player vertically: that's what used to put players
  // on the roof, or under the floor when jumping against a wall.
  moveVertical(d) {
    const prev = this.pos.y;
    this.pos.y += d;
    const hits = this.overlapping(this.pos);
    if (!hits.length) {
      this.grounded = false;
    } else if (d < 0) {
      const under = hits.filter((c) => c.max.y <= prev + 0.01);   // (sinking into a low ledge is depenetrate's job)
      if (under.length) {
        this.pos.y = Math.max(...under.map((c) => c.max.y));
        this.grounded = true;
        this.vel.y = 0;
      }
    } else {
      const over = hits.filter((c) => c.min.y >= prev + this.height - 1e-3);
      if (over.length) {
        this.pos.y = Math.min(...over.map((c) => c.min.y)) - this.height - 1e-3;
        this.vel.y = 0;
      }
    }
    this.followRamp();
  }

  // Height of the ramp surface under the footprint (at its uphill edge, so the box clears
  // every tread below the slope), or -Infinity off the ramps.
  rampHeight(p) {
    const r = this.o.radius;
    let best = -Infinity;
    for (const { x: [x0, x1], z: [z0, z1], y: [y0, y1] } of this.ramps) {
      if (p.x + r <= Math.min(x0, x1) || p.x - r >= Math.max(x0, x1) || p.z + r <= z0 || p.z - r >= z1) continue;
      const up = (y1 - y0) * (x1 - x0) > 0 ? p.x + r : p.x - r;
      const t = Math.min(1, Math.max(0, (up - x0) / (x1 - x0)));
      best = Math.max(best, y0 + (y1 - y0) * t);
    }
    return best;
  }

  // Stand on a ramp: when the feet are up to a step below it (walking up), or just above it
  // after walking down it (rather than falling 18 cm per tread).
  followRamp() {
    const g = this.rampHeight(this.pos);
    const gap = g - this.pos.y;
    const snapDown = this._onRamp ? this.o.stepHeight : 0.01;
    this._onRamp = false;
    if (this.vel.y > 0 || g === -Infinity || gap > this.o.stepHeight || gap < -snapDown) return;
    const at = this.pos.clone();
    at.y = g;
    if (this.overlapping(at).length) return;
    this.pos.y = g;
    this.vel.y = 0;
    this.grounded = true;
    this._onRamp = true;
  }

  // Anything still overlapping after a move pushes the player out the shortest way
  // horizontally (or up, if it's only a step high).
  depenetrate() {
    for (let i = 0; i < 4; i++) {
      const hits = this.overlapping(this.pos);
      if (!hits.length) return;
      // tall obstacles first: a rug under an ottoman must not be resolved by sliding the
      // player sideways off the rug's far edge (and through the glass beyond it)
      const step = (c) => c.max.y - this.pos.y <= this.o.stepHeight;
      const c = hits.find((h) => !step(h)) ?? hits[0];
      if (!this.tryStepUp(c)) this.pushOut(c);
    }
  }

  // Out of `box` by the shortest exit that lands clear of everything: the plain shortest
  // exit could push the player out of a sofa into the glass wall beside it, and then out of
  // the glass on its far side, outside the house. Only if no exit is clear take the shortest.
  pushOut(box) {
    const r = this.o.radius;
    const moves = [
      ['x', box.min.x - r - 1e-3], ['x', box.max.x + r + 1e-3],
      ['z', box.min.z - r - 1e-3], ['z', box.max.z + r + 1e-3],
    ].sort((m, n) => Math.abs(m[1] - this.pos[m[0]]) - Math.abs(n[1] - this.pos[n[0]]));
    const t = this.pos.clone();
    for (const [axis, v] of moves) {
      t.copy(this.pos);
      t[axis] = v;
      if (!this.overlapping(t).length) { this.pos.copy(t); return; }
    }
    this.pos[moves[0][0]] = moves[0][1];
  }

  // a door that just finished opening may overlap the player: step clear of it
  pushOutOf(box) {
    if (!this.boxAt(this.pos).intersectsBox(box)) return;
    this.pushOut(box);
    this.depenetrate();
    this.syncCamera();
  }

  syncCamera() {
    this.camera.position.set(this.pos.x, this.pos.y + this.eye, this.pos.z);
  }
}
