import * as THREE from 'three';

// What being in the river sounds and looks like (the physics is viewer/wild/player_hf.js; this
// reads its waterState each frame). No draw calls: the underwater tint, the breath meter and the
// wipeout fade are DOM overlays in wild.html.
//
//   sounds   window.__sfx?.play(name, position, {gain}) (none in wild.html yet: the audio
//            workstream's manifest needs these names): water_step (a wading stride; gain by
//            depth), swim_stroke, water_splash (falling / jumping in; gain by speed), water_gasp
//            (surfacing after a dive or a tumble), water_climb (a mantle out), water_swept
//            (losing your feet / the current taking you), water_wipeout (into the Narrows).
//            window.__sfx?.setMuffle?.(0..1) while the ear is under the water.
//   noise    window.__noise?.emit({position, loudness, source: 'water', kind}) for the invaders:
//            splashing is loud (a walk on dry litter is ~0.2 in their terms): an ankle-deep
//            stride 0.3, knee 0.5, waist 0.7 (x1.4 running, x0.5 crouched), a swim stroke 0.55,
//            a jump or fall in 0.8-2.2, a tumble 1.0
//   window.__swim  {state: player.waterState, log: [{t, kind, loudness, band}], counts}

const STEP_LOUD = { ankle: 0.3, knee: 0.5, waist: 0.7, chest: 0.8 };

export class SwimFx {
  constructor(player, { doc = document } = {}) {
    this.player = player;
    this.el = { tint: doc.getElementById('underwater'), breath: doc.getElementById('breath'), bar: doc.getElementById('breath-bar'), fade: doc.getElementById('wipeout') };
    this.log = []; this.counts = {};
    this._stride = 0; this._stroke = 0; this._noiseT = 0; this._under = 0; this._wasSwept = false; this._wasWipe = false; this._muffle = 0;
    this._last = player.pos.clone();
    this.t = 0;
    window.__swim = { state: player.waterState, log: this.log, counts: this.counts, fx: this };
  }

  emit(kind, loudness, gain = 1, force = false) {
    const p = this.player.pos, S = this.player.waterState;
    const pos = new THREE.Vector3(p.x, Number.isFinite(S.surface) ? S.surface : p.y, p.z);
    window.__sfx?.play?.(kind, pos, { gain });
    this.counts[kind] = (this.counts[kind] || 0) + 1;
    const entry = { t: +this.t.toFixed(2), kind, band: S.band, loudness: +loudness.toFixed(2) };
    if (loudness > 0 && (force || this.t - this._noiseT > 0.35)) {
      this._noiseT = this.t;
      window.__noise?.emit?.({ position: pos, loudness, source: 'water', kind });
      entry.noise = true;
    }
    this.log.push(entry);
    if (this.log.length > 400) this.log.shift();
  }

  update(dt) {
    this.t += dt;
    const pl = this.player, S = pl.waterState, p = pl.pos;
    const moved = Math.hypot(p.x - this._last.x, p.z - this._last.z);
    this._last.copy(p);
    if (S.entered > 2) this.emit('water_splash', Math.min(2.2, 0.6 + S.entered * 0.12), Math.min(1, S.entered / 12), true);
    if (S.climbed) this.emit('water_climb', 0.5);
    if (S.swept && !this._wasSwept) this.emit('water_swept', 1.0, 1, true);
    this._wasSwept = S.swept;
    if (S.wipeout && !this._wasWipe) this.emit('water_wipeout', 1.2, 1, true);
    this._wasWipe = !!S.wipeout;
    if (S.inWater && !S.swimming && pl.grounded && moved > 0) {
      // a wading stride (longer when running); the current's own push doesn't count as a stride
      this._stride += moved;
      const stride = pl.crouching ? 0.55 : moved / dt > 3 ? 1.1 : 0.75;
      if (this._stride > stride) {
        this._stride = 0;
        const run = moved / dt > 3 ? 1.4 : 1, crouch = pl.crouching ? 0.5 : 1;
        this.emit('water_step', (STEP_LOUD[S.band] || 0.3) * run * crouch, Math.min(1, 0.4 + S.imm));
      }
    } else this._stride = 0;
    if (S.swimming && !S.diving && Math.hypot(pl.vel.x, pl.vel.z) > 0.4) {
      this._stroke += dt;
      if (this._stroke > 1.05) { this._stroke = 0; this.emit('swim_stroke', S.swept ? 0 : 0.55); }
    } else this._stroke = 0.7;
    // under: tint, muffle; surfacing after a while under = a gasp
    if (S.submerged) this._under += dt;
    else { if (this._under > 1.2) this.emit('water_gasp', 0.35); this._under = 0; }
    const muffle = S.submerged ? 1 : 0;
    if (muffle !== this._muffle) { this._muffle = muffle; window.__sfx?.setMuffle?.(muffle); }
    const E = this.el;
    if (E.tint) E.tint.style.opacity = S.submerged ? '1' : '0';
    if (E.breath) {
      E.breath.style.opacity = S.breath < 0.995 ? '1' : '0';
      if (E.bar) E.bar.style.transform = `scaleX(${S.breath.toFixed(3)})`;
    }
    if (E.fade) {
      const w = S.wipeout;
      E.fade.style.opacity = !w ? '0' : !w.moved ? String(Math.min(1, w.t / 0.8)) : String(Math.max(0, 1 - (w.t - 0.9) / 1.1));
    }
  }
}
