import * as THREE from 'three';

// Objects that carry an `interact` definition in their glTF extras (a custom
// property set in Blender). Types:
//   slide   moves `distance` metres along `axis` (parent space)       e.g. drawer
//   rotate  turns `angle` degrees about `axis` through its origin      e.g. door on a hinge
//   pickup  goes into the inventory; if it sits inside another interactable
//           (a card in a drawer) it can only be taken while that one is open
// Common fields: duration, range (m), prompt / promptActive, side ("axis" = only
// from the side it opens toward, "both"), collide (moving collider), indicator
// (node name of a status light). A level can lock an item with an inventory
// item id (its `lockKey`); the player locks/unlocks it by arming that item and
// using it nearby (useArmed). E on a locked item only reports that it's locked.

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
        lockKey: def.type === 'pickup' ? null : lock,
        locked: def.type !== 'pickup' && !!lock,
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
    if (it.locked) return d.lockedPrompt || 'Locked';
    return it.target ? d.promptActive : d.prompt;
  }

  // the lockable item the armed key works on from here, if any
  lockTarget(itemId, player) {
    let best = null, bestD = Infinity;
    for (const it of this.items) {
      if (it.lockKey !== itemId) continue;
      const d = this.reach(it, player);
      if (d <= it.def.range && d < bestD) { best = it; bestD = d; }
    }
    return best;
  }

  // hint for the armed item ("Unlock door", "Throw vase"), or null if it does nothing here
  armedPrompt(itemId, player) {
    const entry = this.inventory.get(itemId);
    if (!entry) return null;
    if (entry.def.throwable) return `Throw ${entry.name.toLowerCase()}`;
    const lock = this.lockTarget(itemId, player);
    if (lock) return lock.locked ? 'Unlock door' : 'Lock door';
    return null;
  }

  // use the armed key on the nearest thing it locks; returns a message
  useKey(itemId, player) {
    const it = this.lockTarget(itemId, player);
    const name = this.inventory.name(itemId);
    if (!it) return `Nothing to use the ${name.toLowerCase()} on here`;
    if (!it.locked && (it.t > 0 || it.target > 0)) return 'Close the door first';
    it.locked = !it.locked;
    this.setIndicator(it, it.locked ? RED : GREEN);
    return it.locked ? 'Door locked' : 'Door unlocked';
  }

  // press E on an item; returns a message to show, or null
  use(it, playerBox) {
    const d = it.def;
    if (d.type === 'pickup') {
      it.taken = true;
      it.node.parent.remove(it.node);
      this.inventory.add(d.item, d.name, it.node, d);
      return `Picked up: ${d.name} · press I for inventory`;
    }
    if (it.locked) {
      if (this.inventory.has(it.lockKey)) {
        const name = this.inventory.name(it.lockKey).toLowerCase();
        return this.inventory.armed === it.lockKey ? `Locked · press Enter to use the ${name}`
                                                   : `Locked · arm the ${name} (I, then Enter)`;
      }
      return d.lockedPrompt || 'Locked';
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
  // Items the player carries. One can be armed (held, ready to use); the
  // inventory screen (I) picks which. `node` is the item's 3D model, kept for
  // showing it in the hand or throwing it.
  constructor(onChange) {
    this.items = new Map();   // id -> { name, node, def }
    this.armed = null;
    this.open = false;
    this.sel = 0;
    this.onChange = onChange;
  }
  changed() { this.onChange?.(this); }
  add(id, name, node = null, def = {}) { this.items.set(id, { name, node, def }); this.changed(); }
  remove(id) {
    this.items.delete(id);
    if (this.armed === id) this.armed = null;
    this.sel = Math.min(this.sel, Math.max(0, this.items.size - 1));
    this.changed();
  }
  has(id) { return this.items.has(id); }
  get(id) { return this.items.get(id); }
  name(id) { return this.items.get(id)?.name; }
  ids() { return [...this.items.keys()]; }
  toggle() { this.open = !this.open; this.sel = Math.max(0, this.ids().indexOf(this.armed)); this.changed(); }
  move(step) {
    const n = this.items.size;
    if (n) this.sel = (this.sel + step + n) % n;
    this.changed();
  }
  armSelected() {
    const id = this.ids()[this.sel];
    if (id) this.armed = id;
    this.open = false;
    this.changed();
    return id;
  }
  holster() { const id = this.armed; this.armed = null; this.changed(); return id; }
}
