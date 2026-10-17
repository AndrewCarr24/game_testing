import * as THREE from 'three';

// Objects that carry an `interact` definition in their glTF extras (a custom
// property set in Blender). Types:
//   slide   moves `distance` metres along `axis` (parent space)       e.g. drawer
//   rotate  turns `angle` degrees about `axis` through its origin      e.g. door on a hinge
//   pickup  goes into the inventory; if it sits inside another interactable
//           (a card in a drawer) it can only be taken while that one is open
// Common fields: duration, range (m), prompt / promptActive, side ("axis" = only
// from the side it opens toward, "both"), collide (moving collider), indicator
// (node name of a status light). A level can lock an item: it then needs that
// inventory item once, after which it stays unlocked.

const ease = (t) => t * t * (3 - 2 * t);
const GREEN = new THREE.Color(0.05, 1.0, 0.25);
const RED = new THREE.Color(1.0, 0.04, 0.02);

export class Interactables {
  constructor(inventory, colliders) {
    this.items = [];
    this.inventory = inventory;
    this.colliders = colliders;   // shared with the player; moving parts add their box here
  }

  collect(root, { lock = null } = {}) {
    root.updateMatrixWorld(true);
    root.traverse((node) => {
      const def = node.userData.interact;
      if (!def) return;
      const it = {
        node, def, root, t: 0, target: 0, taken: false,
        locked: def.type === 'pickup' ? null : lock,
        axis: def.axis ? new THREE.Vector3(...def.axis).normalize() : null,
        rest: node.position.clone(), restQuat: node.quaternion.clone(),
        host: def.type === 'pickup' ? this.hostOf(node) : null,
      };
      if (def.indicator) {
        it.indicator = root.getObjectByName(def.indicator);
        if (it.indicator) it.indicator.material = it.indicator.material.clone();  // per-door colour
        this.setIndicator(it, it.locked ? RED : GREEN);
      }
      if (def.collide) {
        it.collider = new THREE.Box3();
        this.colliders.push(it.collider);
      }
      this.items.push(it);
      this.pose(it);
    });
  }

  hostOf(node) {
    for (let n = node.parent; n; n = n.parent) {
      const host = this.items.find((it) => it.node === n);
      if (host) return host;
    }
    return null;
  }

  setIndicator(it, color) {
    if (!it.indicator) return;
    it.indicator.material.emissive.copy(color);
    it.indicator.material.emissiveIntensity = 1.5;   // bright enough to glow, low enough to keep its colour
    it.indicator.material.color.copy(color).multiplyScalar(0.05);
  }

  pose(it) {
    const k = ease(it.t);
    if (it.def.type === 'slide') {
      it.node.position.copy(it.rest).addScaledVector(it.axis, it.def.distance * k);
    } else if (it.def.type === 'rotate') {
      const turn = new THREE.Quaternion().setFromAxisAngle(it.axis, THREE.MathUtils.degToRad(it.def.angle) * k);
      it.node.quaternion.copy(it.restQuat).multiply(turn);
    }
    if (it.collider) {
      it.node.updateMatrixWorld(true);
      // a part in motion doesn't block (it would trap the player mid-swing);
      // it becomes solid again once it settles
      if (it.t === it.target) it.collider.setFromObject(it.node);
      else it.collider.makeEmpty();
    }
  }

  available(it) {
    if (it.def.type !== 'pickup') return true;
    return !it.taken && (!it.host || (it.host.t === 1 && it.host.target === 1));
  }

  centre(it) {
    return new THREE.Box3().setFromObject(it.node).getCenter(new THREE.Vector3());
  }

  // horizontal distance from a point to the nearest edge of the item (so an open
  // door that has swung away is still in reach from the doorway)
  reach(it, point) {
    const box = new THREE.Box3().setFromObject(it.node);
    const dx = Math.max(box.min.x - point.x, 0, point.x - box.max.x);
    const dz = Math.max(box.min.z - point.z, 0, point.z - box.max.z);
    return Math.hypot(dx, dz);
  }

  // what the player can use from here: pickups first, then the nearest thing
  nearest(player) {
    const off = new THREE.Vector3(), dir = new THREE.Vector3();
    let best = null, bestScore = Infinity;
    for (const it of this.items) {
      if (!this.available(it)) continue;
      const d = this.reach(it, player);
      if (d > it.def.range) continue;
      off.subVectors(player, this.centre(it));
      off.y = 0;
      if ((it.def.side || 'axis') === 'axis' && it.def.type === 'slide') {
        dir.copy(it.axis).transformDirection(it.node.parent.matrixWorld);
        dir.y = 0;
        if (off.dot(dir) <= 0) continue;
      }
      const score = d - (it.def.type === 'pickup' ? 10 : 0);
      if (score < bestScore) { best = it; bestScore = score; }
    }
    return best;
  }

  prompt(it) {
    const d = it.def;
    if (d.type === 'pickup') return d.prompt;
    if (it.locked) return this.inventory.has(it.locked) ? d.unlockPrompt || 'Unlock' : d.lockedPrompt || 'Locked';
    return it.target ? d.promptActive : d.prompt;
  }

  // press E on an item; returns a message to show, or null
  use(it, playerBox) {
    const d = it.def;
    if (d.type === 'pickup') {
      it.taken = true;
      it.node.parent.remove(it.node);
      this.inventory.add(d.item, d.name);
      return `Picked up: ${d.name}`;
    }
    if (it.locked) {
      if (!this.inventory.has(it.locked)) return d.lockedPrompt || 'Locked';
      const name = this.inventory.name(it.locked);
      it.locked = null;
      this.setIndicator(it, GREEN);
      it.target = 1;
      return `Unlocked with ${name}`;
    }
    if (it.target === 1 && it.collider) {
      // don't close a door on the player
      const closed = this.boxAtRest(it);
      if (closed.intersectsBox(playerBox)) return 'Something is in the way';
    }
    it.target = it.target ? 0 : 1;
    return null;
  }

  boxAtRest(it) {
    const t = it.t, target = it.target;
    it.t = it.target = 0;
    this.pose(it);
    const box = it.collider.clone();
    it.t = t; it.target = target;
    this.pose(it);
    return box;
  }

  // advance animations; returns the items that moved this frame
  update(dt) {
    const moved = [];
    for (const it of this.items) {
      if (it.t === it.target || it.def.type === 'pickup') continue;
      const step = dt / it.def.duration;
      it.t = it.target > it.t ? Math.min(it.target, it.t + step) : Math.max(it.target, it.t - step);
      this.pose(it);
      moved.push(it);
    }
    return moved;
  }
}

export class Inventory {
  constructor(onChange) {
    this.items = new Map();   // id -> display name
    this.onChange = onChange;
  }
  add(id, name) { this.items.set(id, name); this.onChange?.(this); }
  has(id) { return this.items.has(id); }
  name(id) { return this.items.get(id); }
}
