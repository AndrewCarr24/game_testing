import * as THREE from 'three';

// Objects that carry an `interact` definition in their glTF extras (set as a
// custom property in Blender). Supported types:
//   slide: moves `distance` metres along `axis` (parent space) over `duration` s.
// The player can use one when within `range` metres of it, on the side it opens toward.

const ease = (t) => t * t * (3 - 2 * t);

export class Interactables {
  constructor() {
    this.items = [];
  }

  collect(root) {
    root.updateMatrixWorld(true);
    root.traverse((node) => {
      const def = node.userData.interact;
      if (!def || def.type !== 'slide') return;
      this.items.push({
        node, def,
        axis: new THREE.Vector3(...def.axis).normalize(),
        rest: node.position.clone(),
        t: 0,        // 0 = closed, 1 = open
        target: 0,
      });
    });
  }

  // nearest item in range whose opening side faces the player
  nearest(player) {
    const wp = new THREE.Vector3(), dir = new THREE.Vector3(), off = new THREE.Vector3();
    let best = null, bestD = Infinity;
    for (const it of this.items) {
      it.node.getWorldPosition(wp);
      dir.copy(it.axis).transformDirection(it.node.parent.matrixWorld);
      dir.y = 0;
      off.subVectors(player, wp);
      off.y = 0;
      const d = off.length();
      if (d > it.def.range || off.dot(dir) <= 0) continue;
      if (d < bestD) { best = it; bestD = d; }
    }
    return best;
  }

  prompt(it) {
    return it.target ? it.def.promptActive : it.def.prompt;
  }

  toggle(it) {
    it.target = it.target ? 0 : 1;
  }

  // advance animations; returns true if anything moved (so shadows need redrawing)
  update(dt) {
    let moved = false;
    for (const it of this.items) {
      if (it.t === it.target) continue;
      moved = true;
      const step = dt / it.def.duration;
      it.t = it.target > it.t ? Math.min(it.target, it.t + step) : Math.max(it.target, it.t - step);
      it.node.position.copy(it.rest).addScaledVector(it.axis, it.def.distance * ease(it.t));
    }
    return moved;
  }
}
