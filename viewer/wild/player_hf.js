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
//   wading    in the creek (world.waterAt above the ground) walk and run at x0.6

export class HeightfieldPlayer extends Player {
  constructor(camera, colliders, feet, world, opts = {}) {
    super(camera, colliders, feet, { ...opts, ramps: [] });
    this.world = world;
    this.maxSlope = Math.tan(((opts.maxSlopeDeg ?? 42) * Math.PI) / 180);
    this._tb = [...Array(16)].map(() => new THREE.Box3());
    this._speeds = { walk: this.o.walk, run: this.o.run, crouchSpeed: this.o.crouchSpeed };
    this.wading = false;
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
    if (W.waterAt) {
      const w = W.waterAt(this.pos.x, this.pos.z);
      // (not on a footlog or the swinging bridge over it: only with the feet in the water)
      this.wading = Number.isFinite(w) && w > W.heightAt(this.pos.x, this.pos.z) + 0.08 && this.pos.y < w + 0.15;
      const k = this.wading ? 0.6 : 1;
      this.o.walk = this._speeds.walk * k; this.o.run = this._speeds.run * k; this.o.crouchSpeed = this._speeds.crouchSpeed * k;
    }
    super.update(dt, input);
    // the terrain is a hard floor (a tunnel's ceiling box can refuse player.js's ramp snap)
    const g = this.rampHeight(this.pos);
    if (this.pos.y < g - 0.02) { this.pos.y = g; if (this.vel.y < 0) this.vel.y = 0; this.grounded = true; this.syncCamera(); }
  }

  moveHorizontal(axis, d) {
    if (d === 0) return;
    const before = this.pos[axis], y0 = this.world.heightAt(this.pos.x, this.pos.z);
    super.moveHorizontal(axis, d);
    const moved = this.pos[axis] - before;
    if (!moved || !this.grounded) return;
    const rise = this.world.heightAt(this.pos.x, this.pos.z) - y0;
    if (rise > Math.abs(moved) * this.maxSlope) { this.pos[axis] = before; this.vel[axis] = 0; }
  }
}
