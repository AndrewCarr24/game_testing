import * as THREE from 'three';
import { axisOf, cloneMaterial } from './interactables.js';

// Hiding spots (interact type `hide`, prompts/interactivity.md): E at a wardrobe, a pantry, under a
// table... and the player climbs in. The camera moves along a short path into the spot (doors swing
// open and pull to, leaving a crack to peek through), movement is locked, the view can only turn a
// little from the spot's facing, and E climbs back out to the spot's exit. While settled inside
// `player.hidden` is true (the Grimble can't see a hidden player) and `player.hideSpot` describes
// where (for the Grimble's behaviour round hiding spots); `player.hideSpot` is also set during the
// climb in and out, when the player can still be seen.
//
// Asset side: an empty with userData.interact = {type: "hide", eye, exit, doors?, facing?, pitch?,
// look?, cover?, duration?, noise?, prompt, promptActive}; `eye` / `exit` name empties (the camera
// inside, the feet outside). Interactables.addItem resolves the nodes (it.eye, it.exits, it.doors).

const smooth = (t) => t * t * (3 - 2 * t);
const clamp01 = (t) => Math.min(1, Math.max(0, t));
const seg = (t, a, b) => smooth(clamp01((t - a) / (b - a)));      // 0 -> 1 between a and b
const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
const DEG = THREE.MathUtils.degToRad;

export class Hiding {
  constructor({ player, camera, interact, noise = null, walls = [], onMove = null }) {
    Object.assign(this, { player, camera, interact, noise, walls, onMove });
    this.spot = null;       // the item while the player is in it (climbing in, inside, climbing out)
    this.phase = null;      // 'in' | 'hidden' | 'out'
    this.t = 0;
    this.time = 0;
    this._e = new THREE.Euler(0, 0, 0, 'YXZ');
    this.overlay = this.makeOverlay();
    interact.onHide = (it) => this.enter(it);
    player.onUnhide = () => this.leave({ instant: true });     // knocked down / pulled out
    for (const it of interact.items) if (it.def.type === 'hide') this.validate(it);
  }

  get active() { return !!this.spot; }
  get hidden() { return this.phase === 'hidden'; }

  // a dark vignette over the view while inside (stronger in a closed spot): the edges of the
  // wardrobe / the table's shadow, the crack of light in the middle
  makeOverlay() {
    if (typeof document === 'undefined') return null;
    const el = document.createElement('div');
    el.id = 'hide-vignette';
    Object.assign(el.style, { position: 'absolute', inset: '0', pointerEvents: 'none', opacity: '0', transition: 'opacity .35s' });
    document.body.appendChild(el);
    return el;
  }

  setOverlay(on, cover) {
    if (!this.overlay) return;
    this.overlay.style.background = cover === 'open'
      ? 'radial-gradient(ellipse 75% 70% at 50% 55%, rgba(0,0,0,0) 45%, rgba(0,0,0,.55) 100%)'
      : 'radial-gradient(ellipse 42% 62% at 50% 50%, rgba(0,0,0,0) 30%, rgba(0,0,0,.82) 100%)';
    this.overlay.style.opacity = on ? '1' : '0';
  }

  // world poses of a spot: the eye inside, the facing (yaw, pitch), the first exit that is clear
  // for a standing player (pushed further out if the authored one is blocked by a chair)
  validate(it) {
    const p = this.player, P = it.pose = {};
    it.node.updateWorldMatrix(true, true);
    P.eye = it.eye ? it.eye.getWorldPosition(new THREE.Vector3()) : it.node.getWorldPosition(new THREE.Vector3());
    if (this.walls.some((w) => w.containsPoint(P.eye))) { it.disabled = 'eye in a wall'; return; }
    for (const ex of it.exits) {
      const at = ex.getWorldPosition(new THREE.Vector3());
      const out = new THREE.Vector3(at.x - P.eye.x, 0, at.z - P.eye.z).normalize();
      for (let k = 0; k <= 4; k++) {
        const q = at.clone().addScaledVector(out, 0.3 * k);
        if (!p.overlapping(q, p.o.height).length && this.floorUnder(q)) { P.exit = q; break; }
      }
      if (P.exit) break;
    }
    if (!P.exit) { it.disabled = 'no clear exit'; return; }
    // facing: authored (a direction in the spot's frame), else from the eye toward the exit
    const f = it.def.facing ? axisOf(it.def.facing).transformDirection(it.node.parent.matrixWorld)
      : new THREE.Vector3().subVectors(P.exit, P.eye);
    P.yaw = Math.atan2(-f.x, -f.z);             // three.js cameras look down -z
    P.pitch = DEG(+(it.def.pitch ?? 0));
    const closed = (it.def.cover ?? (it.doors.length ? 'closed' : 'open')) !== 'open';
    P.cover = closed ? 'closed' : 'open';
    P.yawLimit = DEG(+(it.def.look?.yaw ?? (closed ? 28 : 50)));
    P.pitchLimit = DEG(+(it.def.look?.pitch ?? (closed ? 18 : 25)));
    P.quat = new THREE.Quaternion().setFromEuler(new THREE.Euler(P.pitch, P.yaw, 0, 'YXZ'));
    P.exitQuat = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, P.yaw, 0, 'YXZ'));
    // the crouch point: outside at the eye's height, where the climb in starts / out ends
    P.mouth = new THREE.Vector3(P.exit.x, P.eye.y, P.exit.z);
  }

  // something to stand on just under q (an exit over the stairwell / the courtyard void isn't one)
  floorUnder(q) {
    const p = this.player, probe = q.clone();
    probe.y -= 0.05;
    return p.overlapping(probe, 0.1).some((c) => c.max.y <= q.y + 0.06) || q.y < 0.2;
  }

  info(it) {
    const P = it.pose;
    return { name: it.def.name ?? it.root.name, cover: P.cover, eye: P.eye.clone(), exit: P.exit.clone(), node: it.node, root: it.root };
  }

  // every usable spot (for the Grimble: where a player could be)
  spots() {
    const out = [];
    for (const it of this.interact.items) {
      if (it.def.type !== 'hide') continue;
      if (!it.pose && !it.disabled) this.validate(it);
      if (!it.disabled) out.push(this.info(it));
    }
    return out;
  }

  enter(it) {
    if (!it.pose && !it.disabled) this.validate(it);       // (a spot registered after load)
    if (it.disabled) return 'No room in there';
    if (this.spot || this.player.isDown) return null;
    this.spot = it;
    this.phase = 'in';
    this.t = 0;
    this.from = { pos: this.camera.position.clone(), quat: this.camera.quaternion.clone() };
    const p = this.player;
    p.hideSpot = this.info(it);
    p.hidden = false;
    p.vel.set(0, 0, 0);
    p.pos.copy(it.pose.exit);                 // (where the player will stand when they come out)
    this.sound('in');
    this.setOverlay(true, it.pose.cover);
    return null;
  }

  leave({ instant = false } = {}) {
    const it = this.spot;
    if (!it) return false;
    this.player.hidden = false;
    if (instant) { this.t = 1; this.phase = 'out'; this.finish(); return true; }
    if (this.phase !== 'hidden') return false;   // (climbing in: let it settle first)
    this.phase = 'out';
    this.t = 0;
    this.from = { pos: this.camera.position.clone(), quat: this.camera.quaternion.clone() };
    this.sound('out');
    this.setOverlay(false);
    return true;
  }

  finish() {
    const it = this.spot, p = this.player;
    this.poseDoors(it, 0);
    this.dim(it, 0);
    p.pos.copy(it.pose.exit);
    p.vel.set(0, 0, 0);
    p.crouching = false;
    p.height = p.o.height;
    p.eye = p.o.eye;
    p.depenetrate();
    this.camera.quaternion.copy(it.pose.exitQuat);
    p.syncCamera();
    p.hideSpot = null;
    p.hidden = false;
    this.spot = null;
    this.phase = null;
    this.setOverlay(false);
    this.onMove?.();
  }

  sound(kind) {
    const it = this.spot, at = it.pose.exit;
    this.noise?.emit({ position: at.clone(), loudness: +(it.def.noise ?? (it.doors.length ? 0.3 : 0.15)), source: `hide_${kind}` });
    window.__sfx?.play?.(it.doors.length ? `hide_door_${kind}` : `hide_${kind}`, at);
  }

  // The inside of a shut door is in the dark, but props are lit by their room's probe as if they
  // stood in the open: while the player is in a closed spot its doors get dimmed copies of their
  // materials (k = 0 as authored .. 1 dark), the originals back once they're out
  dim(it, k) {
    if (it.pose.cover === 'open' || !it.doors.length) return;
    if (!it.dimmed) {
      if (k <= 0) return;
      it.dimmed = [];
      for (const d of it.doors) d.node.traverse((o) => {
        if (!o.isMesh || Array.isArray(o.material)) return;
        const m = cloneMaterial(o.material);
        it.dimmed.push({ o, orig: o.material, m });
        o.material = m;
      });
    }
    for (const { orig, m } of it.dimmed) {
      m.color.copy(orig.color).multiplyScalar(1 - 0.8 * k);
      m.envMapIntensity = (orig.envMapIntensity ?? 1) * (1 - 0.85 * k);
    }
    if (k <= 0) { for (const { o, orig, m } of it.dimmed) { o.material = orig; m.dispose(); } it.dimmed = null; }
  }

  // doors: k = 0 shut, 1 fully open; `ajar` is where they rest while the player is inside
  poseDoors(it, k, ajar = 0) {
    for (const d of it.doors) {
      const a = DEG(d.angle) * k + DEG(d.ajar ?? 0) * ajar * (1 - k);
      d.node.quaternion.copy(d.restQuat).multiply(new THREE.Quaternion().setFromAxisAngle(d.axis, a));
    }
  }

  // drive the camera while in a spot; returns true then (the player isn't simulated)
  update(dt) {
    const it = this.spot;
    if (!it) return false;
    const P = it.pose, cam = this.camera, dur = +(it.def.duration ?? (it.doors.length ? 1.1 : 0.9));
    this.time += dt;
    if (this.phase === 'in' || this.phase === 'out') {
      this.t = Math.min(1, this.t + dt / dur);
      const t = this.t, inn = this.phase === 'in';
      // doors: swing open first, pull to at the end (to the crack while in, shut when out)
      const open = seg(t, 0, 0.3) * (1 - seg(t, 0.72, 1));
      this.poseDoors(it, open, inn ? seg(t, 0.72, 1) : 1 - seg(t, 0, 0.3));
      this.dim(it, inn ? seg(t, 0.6, 1) : 1 - seg(t, 0, 0.3));
      // path: crouch down at the mouth, then in (climbing out: the reverse)
      if (inn) {
        const a = seg(t, 0, 0.45), b = seg(t, 0.4, 0.95);
        cam.position.lerpVectors(this.from.pos, P.mouth, a).lerp(P.eye, b);
        cam.quaternion.slerpQuaternions(this.from.quat, P.quat, seg(t, 0.1, 0.9));
      } else {
        const standing = P.exit.clone(); standing.y += this.player.o.eye;
        const a = seg(t, 0.05, 0.55), b = seg(t, 0.5, 1);
        cam.position.lerpVectors(this.from.pos, P.mouth, a).lerp(standing, b);
        cam.quaternion.slerpQuaternions(this.from.quat, P.exitQuat, seg(t, 0.1, 0.9));
      }
      this.onMove?.();
      if (t >= 1) {
        if (inn) { this.phase = 'hidden'; this.player.hidden = true; }
        else this.finish();
      }
      return true;
    }
    // inside: the view turns only so far from the spot's facing; a slow breath moves the eye
    const e = this._e.setFromQuaternion(cam.quaternion, 'YXZ');
    const dy = wrap(e.y - P.yaw);
    e.y = P.yaw + Math.max(-P.yawLimit, Math.min(P.yawLimit, dy));
    e.x = Math.max(P.pitch - P.pitchLimit, Math.min(P.pitch + P.pitchLimit, e.x));
    e.z = 0;
    cam.quaternion.setFromEuler(e);
    const breath = window.__bench ? 0 : 0.006 * Math.sin(this.time * 1.7);
    cam.position.copy(P.eye).y += breath;
    return true;
  }

  // the HUD line while in a spot
  hint() {
    if (!this.spot) return null;
    if (this.phase !== 'hidden') return '';
    return this.spot.def.promptActive || 'Leave';
  }
}
