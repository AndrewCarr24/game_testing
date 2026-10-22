import * as THREE from 'three';
import { Player } from '../player.js';

// viewer/player.js on a heightfield. The player already follows "ramps" (the stairs): a
// surface height under the footprint that it snaps onto when walking up (up to a step) and
// stays glued to when walking down. Here the ramp is the terrain, so gravity, jumping, step-up
// onto boxes (trunks, rocks) and the box colliders all keep working unchanged. Added: a
// walkable-slope limit (steeper ground blocks like a wall), since a heightfield has no walls.
//
// Generated levels (load_world.js) add:
//   thickets  world.thicket cells (vertex grid): 255 = laurel hell, a solid box over the cell;
//             128 = tunnel, a ceiling box from 1.35 m over the ground up (standing blocks, the
//             1.1 m crouch fits; player.js already won't stand up without headroom)
//   water     setWater(water) with {surfaceAt, depthAt, flowAt} (viewer/wild/water.js, or
//             water_standin.js until it lands): the river is physical (below). Without it, the
//             old rule: in the creek walk and run at x0.6.
//
// In the water (imm = how deep the feet are under the surface):
//   wading    slower with depth (ankle x0.85, knee x0.6, waist x0.4, chest x0.3; no running past
//             the knee), jumps lower, the current pushes (ankle 3% of its speed .. chest 60%);
//             a push over FOOTING m/s, waist deep or more, takes the feet out: swept
//   swimming  past FLOAT (1.35 m) of depth the body floats, the eye ~0.3 m over the water: swim
//             at 1.3 m/s (no sprint), carried by the whole current; C dives (down to the bed,
//             BREATH s of air, then back up), Space + forward climbs out onto a rock or bank up
//             to REACH over the water (a mantle; also from wading)
//   swept     a current over SWEPT m/s while swimming (the shoals, the Narrows), or lost footing:
//             tumbling with the water, barely any control, until it slows
//   wipeout   swept in the Narrows (the ledge and the 18 m cascade below the bridge) or carried
//             out of the square: the screen goes dark, you come to on the last dry ground you
//             stood on upstream (a hit of WIPEOUT_DAMAGE through window.__combat when it exists).
//             Fair: the current builds over ~40 m from the bridge pool (0.5 m/s) to the ledge
//             (4+ m/s), so a swimmer who heads for a bank in time makes it
//   waterState  everything above, per frame, for the effects (viewer/wild/swim.js) and tests

const FLOAT = 1.35;          // m of water over the feet when floating
const SWIM_SPEED = 1.3, DIVE_SPEED = 1.1, BREATH = 20;
const REACH = 0.95;          // a mantle climbs onto tops up to this far over the water
const FOOTING = 0.95;        // m/s of push that takes the feet out (waist deep or more)
const SWEPT = 2.1;           // m/s of current a swimmer can't fight
const WIPEOUT_SPEED = 3.2, WIPEOUT_DAMAGE = 35;
const IMM = [0, 0.3, 0.7, 1.05, FLOAT];
const SPEED_K = [1, 0.85, 0.6, 0.4, 0.3];
const PUSH_K = [0.03, 0.08, 0.22, 0.42, 0.6];
const JUMP_K = [1, 0.85, 0.6, 0.35, 0.2];
const tab = (x, Y) => {
  if (x <= IMM[0]) return Y[0];
  for (let i = 1; i < IMM.length; i++) if (x <= IMM[i]) return Y[i - 1] + (Y[i] - Y[i - 1]) * (x - IMM[i - 1]) / (IMM[i] - IMM[i - 1]);
  return Y.at(-1);
};
const BANDS = ['ankle', 'knee', 'waist', 'chest'];
// flowAt may answer {x, z}, {x, y} (a Vector2) or [x, z]
const flowXZ = (f, out) => {
  if (!f) { out.x = out.z = 0; } else if (Array.isArray(f)) { out.x = f[0] || 0; out.z = (f.length > 2 ? f[2] : f[1]) || 0; }
  else { out.x = f.x || 0; out.z = (f.z ?? f.y) || 0; }
  out.speed = Math.hypot(out.x, out.z);
  return out;
};

export class HeightfieldPlayer extends Player {
  constructor(camera, colliders, feet, world, opts = {}) {
    super(camera, colliders, feet, { ...opts, ramps: [] });
    this.world = world;
    this.maxSlope = Math.tan(((opts.maxSlopeDeg ?? 42) * Math.PI) / 180);
    this._slopeDry = this.maxSlope;
    this._tb = [...Array(16)].map(() => new THREE.Box3());
    this._speeds = { walk: this.o.walk, run: this.o.run, crouchSpeed: this.o.crouchSpeed };
    this._base = { gravity: this.o.gravity, jumpHeight: this.o.jumpHeight, stepHeight: this.o.stepHeight };
    this.wading = false;
    this.water = null;
    this._flow = { x: 0, z: 0, speed: 0 };
    this._eyeLag = 0; this._bobT = 0; this._roll = 0;
    this.waterState = { inWater: false, imm: 0, depth: 0, surface: NaN, band: 'dry', swimming: false, swept: false, diving: false,
      submerged: false, breath: 1, flow: this._flow, hazard: false, wipeout: null, wipeouts: 0, climbed: 0, entered: 0, t: 0 };
  }

  // the river (viewer/wild/water.js or water_standin.js); `river` = world.json "river" (estate frame)
  setWater(water, { river = null, onHurt = null } = {}) {
    this.water = water;
    this.onHurt = onHurt;
    const oy = this.world.meta?.estate_offset?.[1] ?? 0, toW = ([x, y]) => [x, -(y - oy)];
    // the Narrows (no way back): the rapids within 100 m of the cascade (the ledge, the cascade,
    // the chute below), estate frame -> three
    this.hazards = [];
    if (river?.cascade) {
      const [cx, cz] = toW(river.cascade);
      this.hazards.push({ x: cx, z: cz, r: 36 });
      for (const [x, y, r] of river.rapids || []) { const [hx, hz] = toW([x, y]); if (Math.hypot(hx - cx, hz - cz) < 100) this.hazards.push({ x: hx, z: hz, r: r + 4 }); }
    }
    this._safe = [];        // recent dry footholds: [{x, y, z, t}]
    this._safeT = 0;
  }

  // highest terrain under the footprint (centre + 4 corners): the box never dips into a slope
  rampHeight(p) {
    const r = this.o.radius * 0.7, h = this.world.heightAt;
    return Math.max(h(p.x, p.z), h(p.x - r, p.z - r), h(p.x + r, p.z - r), h(p.x - r, p.z + r), h(p.x + r, p.z + r));
  }

  // thicket / tunnel cells under the box, as boxes (built on the fly: a few per query)
  overlapping(p, h = this.height) {
    const out = super.overlapping(p, h);
    const W = this.world, T = W.thicket;
    if (!T) return out;
    const r = this.o.radius, sp = W.spacing, half = W.size / 2, res = W.res;
    const i0 = Math.round((p.x - r + half) / sp), i1 = Math.round((p.x + r + half) / sp);
    const j0 = Math.round((p.z - r + half) / sp), j1 = Math.round((p.z + r + half) / sp);
    let n = 0;
    const e = 1e-4;
    for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
      if (i < 0 || j < 0 || i >= res || j >= res) continue;
      const v = T[i + j * res];
      if (!v || n >= this._tb.length) continue;
      const x = -half + i * sp, z = -half + j * sp, hs = sp / 2;
      const g = Math.max(W.heightAt(x - hs, z - hs), W.heightAt(x + hs, z - hs), W.heightAt(x - hs, z + hs), W.heightAt(x + hs, z + hs));
      const b = this._tb[n];
      b.min.set(x - hs, v === 255 ? g - 3 : g + 1.35, z - hs);
      b.max.set(x + hs, g + 6, z + hs);
      if (p.x + r > b.min.x + e && p.x - r < b.max.x - e && p.y + h > b.min.y + e && p.y < b.max.y - e &&
          p.z + r > b.min.z + e && p.z - r < b.max.z - e) { out.push(b); n++; }
    }
    return out;
  }

  update(dt, input) {
    const W = this.world;
    if (this.water && !this.hideSpot) {
      this.waterUpdate(dt, input);
      return;
    }
    if (W.waterAt) {
      const w = W.waterAt(this.pos.x, this.pos.z);
      // (not on a footlog or the swinging bridge over it: only with the feet in the water)
      this.wading = Number.isFinite(w) && w > W.heightAt(this.pos.x, this.pos.z) + 0.08 && this.pos.y < w + 0.15;
      const k = this.wading ? 0.6 : 1;
      this.o.walk = this._speeds.walk * k; this.o.run = this._speeds.run * k; this.o.crouchSpeed = this._speeds.crouchSpeed * k;
    }
    super.update(dt, input);
    this.terrainFloor();
  }

  // the terrain is a hard floor (a tunnel's ceiling box can refuse player.js's ramp snap)
  terrainFloor() {
    const g = this.rampHeight(this.pos);
    if (this.pos.y < g - 0.02) { this.pos.y = g; if (this.vel.y < 0) this.vel.y = 0; this.grounded = true; this.syncCamera(); }
  }

  // ---- the river
  sense() {
    const S = this.waterState, p = this.pos;
    const s = this.water.surfaceAt(p.x, p.z);
    const bed = this.world.heightAt(p.x, p.z);
    S.surface = s;
    S.depth = Number.isFinite(s) ? Math.max(0, s - bed) : 0;
    S.imm = Number.isFinite(s) ? Math.max(0, s - p.y) : 0;
    // (on the bridge deck, a footlog or a rock top the feet are over the water: dry)
    S.inWater = S.depth > 0.1 && S.imm > 0.1;
    flowXZ(S.inWater ? this.water.flowAt(p.x, p.z) : null, this._flow);
    S.hazard = S.inWater && this.hazards.some((h) => Math.hypot(p.x - h.x, p.z - h.z) < h.r);
    return S;
  }

  waterUpdate(dt, input) {
    const S = this.sense(), o = this.o, p = this.pos, B = this._base, sp = this._speeds;
    S.t += dt; S.climbed = 0; S.entered = 0;
    const wasIn = this._wasIn;
    if (S.inWater && !wasIn) S.entered = Math.max(0, -this.vel.y);           // the splash's size (m/s down)
    this._wasIn = S.inWater;
    this.wading = S.inWater;
    if (this.down) input = {};

    // a wipeout: dark, then back on the last dry foothold
    if (S.wipeout) return this.wipeoutStep(dt);

    // floating: deep enough to swim, and the feet at (or under) the float line (hysteresis: the
    // feet touch down as the bed comes up to 1.3 m)
    const floatY = S.surface - FLOAT;
    const buoyant = S.inWater && (this.swimming ? S.depth > FLOAT - 0.05 : S.depth > FLOAT + 0.05 && p.y <= floatY + 0.3);
    this.swimming = buoyant || (S.swept && S.depth > 0.7);
    const push = this.swimming ? 1 : tab(S.imm, PUSH_K);
    const pushV = this._flow.speed * push;

    // swept: by a current a swimmer can't fight, or off the feet (waist deep, a strong push)
    if (S.swept) {
      S.sweptT += dt;
      if (S.sweptT > 1.5 && (this.swimming ? this._flow.speed < SWEPT * 0.8 : pushV < FOOTING * 0.6)) S.swept = false;
    } else if (S.inWater && ((this.swimming && this._flow.speed > SWEPT) || (!this.swimming && S.imm > 0.55 && pushV > FOOTING))) {
      this._loseFooting = (this._loseFooting || 0) + dt;
      if (this.swimming || this._loseFooting > 0.3) { S.swept = true; S.sweptT = 0; this.crouching = false; }
    } else this._loseFooting = 0;
    // into the Narrows, or out of the square, with the water: no way back
    const half = this.world.size / 2, edge = Math.max(Math.abs(p.x), Math.abs(p.z)) > half - 4;
    // (pinned on the ledge's rocks counts: a strainer)
    if (S.inWater && (this.swimming || S.swept) && ((S.hazard && (this._flow.speed > WIPEOUT_SPEED || (this._pinned > 2 && this._flow.speed > 0.8))) || edge)) {
      this._doom = (this._doom || 0) + dt;
      if (this._doom > 0.4 || edge) { this.startWipeout(); return this.wipeoutStep(0); }
    } else this._doom = 0;

    // the controls this frame
    const inp = { ...input };
    const k = tab(S.imm, SPEED_K);
    this.maxSlope = S.inWater ? Math.tan((60 * Math.PI) / 180) : this._slopeDry;
    this._reach = 0;
    // a mantle: Space (with the feet in the water) climbs onto what's in front, up to REACH over the water
    if (S.inWater && input.jump && !S.swept) this._reach = Math.max(o.stepHeight, S.surface - p.y + REACH);
    if (this.swimming) {
      o.walk = o.run = S.swept ? SWIM_SPEED * 0.35 : SWIM_SPEED;
      o.crouchSpeed = SWIM_SPEED * 0.8;
      o.gravity = 0; o.jumpHeight = 0;
      // dive while C is held (with air left), float back up when it's let go
      const air = !this._gasp && S.breath > 0.02;
      if (this._gasp && S.breath > 0.4 && !input.crouch) this._gasp = false;     // (let go of C first)
      S.diving = !!input.crouch && air && !S.swept;
      const floor = this.world.heightAt(p.x, p.z) + 0.05;
      this._dive = S.diving ? Math.min(Math.max(0, floatY - floor), (this._dive || 0) + DIVE_SPEED * dt) : Math.max(0, (this._dive || 0) - 1.6 * dt);
      // the swept tumble pulls you under now and then
      const tumble = S.swept ? 0.45 * Math.max(0, Math.sin(S.sweptT * 2.3)) : 0;
      const target = floatY - this._dive - tumble;
      // a damped spring to the float line (a fall in is braked over a few metres)
      this.vel.y += ((target - p.y) * 18 - this.vel.y * 7) * dt;
      inp.crouch = false; inp.jump = false; inp.run = false;
      if (this.crouching && !this.overlapping(p, o.height).length) this.crouching = false;
    } else {
      S.diving = false; this._dive = 0;
      o.gravity = B.gravity;
      o.jumpHeight = B.jumpHeight * (S.inWater ? tab(S.imm, JUMP_K) : 1);
      o.walk = sp.walk * k;
      o.run = S.imm > 0.7 ? sp.walk * k : sp.run * k;
      o.crouchSpeed = sp.crouchSpeed * Math.max(0.5, k);
      if (S.swept) { inp.jump = false; inp.run = false; inp.crouch = false; }
    }
    if (S.swept) { for (const kk of ['forward', 'back', 'left', 'right']) if (Math.floor(S.sweptT * 3) % 3 === 0) inp[kk] = false; }
    // a mantle reaches higher than a step (player.js's followRamp: the bank; tryStepUp: a rock)
    o.stepHeight = this._reach || B.stepHeight;
    // (in deep water the jump key is the mantle, not a jump)
    if (this._reach && S.imm > 0.7) inp.jump = false;
    const y0 = p.y;

    super.update(dt, inp);
    this.terrainFloor();

    // the current: a push along the flow (collides like walking: rocks stop it; a floating body
    // pinned on a rock is carried round it, the side that's open, as the water goes)
    const ox = this._flow.x * push * dt, oz = this._flow.z * push * dt;
    if (S.inWater && (ox || oz)) {
      const carry = (dx, dz) => {
        const x0 = p.x, z0 = p.z, n = Math.max(1, Math.ceil(Math.max(Math.abs(dx), Math.abs(dz)) / 0.04));
        for (let i = 0; i < n; i++) { this.moveHorizontal('x', dx / n); this.moveHorizontal('z', dz / n); this.depenetrate(); this.terrainFloor(); }
        return ((p.x - x0) * dx + (p.z - z0) * dz) / (dx * dx + dz * dz);      // the fraction made
      };
      const made = carry(ox, oz);
      if (this.swimming && made < 0.4) {
        // round the rock in the way by its nearer side (kept while pinned; flipped if that's shut)
        if (!this._pinned) {
          const L = Math.hypot(ox, oz), ux = ox / L, uz = oz / L, px = -uz, pz = ux;
          const rock = this.overlapping(new THREE.Vector3(p.x + ux * 0.12, p.y, p.z + uz * 0.12))[0];
          if (rock) {
            const cs = [[rock.min.x, rock.min.z], [rock.max.x, rock.min.z], [rock.min.x, rock.max.z], [rock.max.x, rock.max.z]]
              .map(([x, z]) => (x - p.x) * px + (z - p.z) * pz);
            this._side = Math.max(...cs) < -Math.min(...cs) ? 1 : -1;
          }
        }
        this._pinned = (this._pinned || 0) + dt;
        const side = this._side || 1, k = 0.8;
        if (carry(-oz * side * k, ox * side * k) < 0.3) this._side = -side;
      } else this._pinned = 0;
      this.terrainFloor();
    }
    o.stepHeight = B.stepHeight;
    // a climb out pops the feet up: the eye follows over ~0.3 s instead
    const rise = p.y - y0;
    if (this._reach && rise > 0.35) { this._eyeLag -= rise; S.climbed = rise; }

    // air: the eye under the surface uses it, over it refills it
    const eyeY = p.y + this.eye + this._eyeLag;
    const se = this.water.surfaceAt(p.x, p.z);
    S.submerged = Number.isFinite(se) && eyeY < se - 0.03;
    S.breath = S.submerged ? Math.max(0, S.breath - dt / BREATH) : Math.min(1, S.breath + dt / 4);
    if (S.breath <= 0) this._gasp = true;
    S.swimming = this.swimming;
    S.band = !S.inWater ? 'dry' : this.swimming ? 'swim' : BANDS[Math.min(3, Math.floor(S.imm / 0.35))];
    // safe footholds: dry, grounded, away from the Narrows
    if (!S.inWater && this.grounded && !this.down) {
      this._safeT -= dt;
      if (this._safeT <= 0 && !this.hazards.some((h) => Math.hypot(p.x - h.x, p.z - h.z) < h.r + 12)) {
        this._safeT = 0.25;
        this._safe.push({ x: p.x, y: p.y, z: p.z, t: S.t });
        if (this._safe.length > 64) this._safe.shift();
      }
    }
    this._eyeLag *= Math.exp(-dt * 9);
    if (Math.abs(this._eyeLag) < 1e-3) this._eyeLag = 0;
    this._bobT += dt;
    this.syncCamera();
  }

  startWipeout() {
    const S = this.waterState;
    S.wipeout = { t: 0, moved: false };
    S.wipeouts++;
  }

  // 0.9 s carried on into the dark, then placed on the foothold, 1.1 s of fade back
  wipeoutStep(dt) {
    const S = this.waterState, w = S.wipeout, p = this.pos;
    w.t += dt;
    if (!w.moved) {
      // tumbling on with the water
      p.x += this._flow.x * dt; p.z += this._flow.z * dt;
      const s = this.water.surfaceAt(p.x, p.z);
      if (Number.isFinite(s)) p.y = Math.max(this.world.heightAt(p.x, p.z), s - FLOAT - 0.5);
      S.submerged = true;
      if (w.t >= 0.9) {
        const now = S.t, safe = this._safe;
        const spot = [...safe].reverse().find((q) => now - q.t > 1.5) || safe[0] || this.world.spawn && { x: this.world.spawn.pos[0], z: this.world.spawn.pos[2] };
        if (spot) p.set(spot.x, spot.y ?? this.world.heightAt(spot.x, spot.z), spot.z);
        this.vel.set(0, 0, 0);
        S.swept = false; S.diving = false; this.swimming = false; this._dive = 0; this._doom = 0; this._eyeLag = 0;
        w.moved = true; w.at = [p.x, p.y, p.z];
        S.breath = 1;
        this.onHurt?.(WIPEOUT_DAMAGE, { source: 'river', weapon: 'river' });
      }
    } else {
      S.submerged = false;
      this.grounded = true;
      if (w.t >= 2.0) S.wipeout = null;
    }
    S.inWater = false; this.wading = false; S.swimming = false; S.band = w.moved ? 'dry' : 'swept';
    this.syncCamera();
  }

  // a mantle (this._reach) lets a rock up to REACH over the water be climbed from the water
  tryStepUp(c) {
    if (this._reach > this._base.stepHeight && this.vel.y <= 0.8) {
      const rise = c.max.y - this.pos.y;
      if (rise <= 0 || rise > this._reach) return false;
      const up = this.pos.clone();
      up.y = c.max.y + 1e-3;
      if (this.overlapping(up).length) return false;
      this.pos.y = up.y;
      this.vel.y = 0;
      return true;
    }
    return super.tryStepUp(c);
  }

  moveHorizontal(axis, d) {
    if (d === 0) return;
    const before = this.pos[axis], y0 = this.world.heightAt(this.pos.x, this.pos.z);
    super.moveHorizontal(axis, d);
    const moved = this.pos[axis] - before;
    if (!moved) return;
    if (this.grounded) {
      const rise = this.world.heightAt(this.pos.x, this.pos.z) - y0;
      if (rise > Math.abs(moved) * this.maxSlope && !(this._reach && this.rampHeight(this.pos) <= this.pos.y + this._reach)) { this.pos[axis] = before; this.vel[axis] = 0; }
    } else if (this.water && this.waterState.inWater) {
      // floating against a bank: no climbing it a step at a time (only a mantle reaches up)
      if (this.rampHeight(this.pos) > this.pos.y + (this._reach || this._base.stepHeight)) { this.pos[axis] = before; this.vel[axis] = 0; }
    }
  }

  syncCamera() {
    this.camera.position.set(this.pos.x, this.pos.y + this.eye, this.pos.z);
    const S = this.waterState;
    if (!S) return;
    this.camera.position.y += this._eyeLag;
    // a swimmer bobs on the water; a swept one rolls
    if (S.swimming && !S.diving) this.camera.position.y += Math.sin(this._bobT * 2 * Math.PI * 0.55) * 0.05;
    const roll = S.swept ? Math.sin(S.sweptT * 3.1) * 0.14 : S.wipeout && !S.wipeout.moved ? Math.sin(S.wipeout.t * 7) * 0.4 : 0;
    if (roll !== this._roll) { this.camera.rotateZ(roll - this._roll); this._roll = roll; }
  }
}
