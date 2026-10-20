import * as THREE from 'three';
import { Signals } from './signals.js';

// Objects that carry an `interact` definition in their glTF extras (a custom
// property set in Blender). Types:
//   slide   moves `distance` metres along `axis` (parent space)       e.g. drawer
//   rotate  turns `angle` degrees about `axis` through its origin      e.g. door on a hinge
//   pickup  goes into the inventory; if it sits inside another interactable
//           (a card in a drawer) it can only be taken while that one is open
//   switch  E toggles signal `signal` (rocker, knob, button); the part moves by `travel`
//           ({axis, angle | distance}); every switch on a signal follows it (two-way switching)
//   use     with item `needs` armed, Enter sets `signal` to `value` (fuse -> "power");
//           `consume` uses the item up. Done while the signal holds that value.
// Common fields: duration, range (m), prompt / promptActive, side ("axis" = only
// from the side it opens toward, "both"), collide (moving collider), indicator
// (node name of a status light). A level can lock an item with an inventory
// item id (its `lockKey`); the player locks/unlocks it by arming that item and
// using it nearby (useArmed). E on a locked item only reports that it's locked.
//
// Nodes with a `react` definition ({signal, on, off?, duration?, power?, block_sight?}, or a
// list of them) follow a signal (prompts/interactivity.md): show / hide, emissive, slide /
// rotate / scale (animated), light (a real-time point light from a pool of MAX_LIGHTS, given
// to the nearest lit reactors). Reactors with light, emissive or visibility effects are
// electric: they're on only while their signal AND `power` are (react.power overrides).
// Axes are three.js / glTF space (y up), in the node's parent space, like slide/rotate's.

const ease = (t) => t * t * (3 - 2 * t);
const GREEN = new THREE.Color(0.05, 1.0, 0.25);
const RED = new THREE.Color(1.0, 0.04, 0.02);
const MAX_LIGHTS = 2;        // real-time point lights for `light` reacts (all room light is baked)
const truthy = (v) => v === true || v === 1 || v === 'true' || v === '1';
const AXES = { x: [1, 0, 0], y: [0, 1, 0], z: [0, 0, 1] };

// "y", "-x", [0, 0, -1] -> unit vector
export function axisOf(a, fallback = 'y') {
  if (Array.isArray(a)) return new THREE.Vector3(...a).normalize();
  const s = String(a ?? fallback).trim().toLowerCase();
  const v = new THREE.Vector3(...(AXES[s.replace(/^[-+]/, '')] ?? AXES[fallback]));
  return s.startsWith('-') ? v.negate() : v;
}

// a material copy that keeps the room lighting baked.js put on it (clone() drops onBeforeCompile)
export function cloneMaterial(m) {
  const c = m.clone();
  c.onBeforeCompile = m.onBeforeCompile;
  c.customProgramCacheKey = m.customProgramCacheKey;
  return c;
}

// effect -> channels: {visible, emissive, slide: Vector3, rotate: Quaternion, scale: Vector3, light}
function parseEffect(e, out = {}) {
  if (e == null) return out;
  if (Array.isArray(e)) { for (const x of e) parseEffect(x, out); return out; }
  if (typeof e === 'string') {
    if (e === 'show' || e === 'hide') out.visible = e === 'show';
    return out;
  }
  if ('show' in e) out.visible = truthy(e.show);
  if ('hide' in e) out.visible = !truthy(e.hide);
  if ('visible' in e) out.visible = truthy(e.visible);
  if ('emissive' in e) out.emissive = +e.emissive;
  if (e.slide) out.slide = axisOf(e.slide.axis).multiplyScalar(+e.slide.distance || 0);
  if (e.rotate) out.rotate = new THREE.Quaternion().setFromAxisAngle(axisOf(e.rotate.axis), THREE.MathUtils.degToRad(+e.rotate.angle || 0));
  if (e.scale != null) {
    const s = e.scale;
    out.scale = typeof s === 'number' ? new THREE.Vector3(s, s, s)
      : Array.isArray(s) ? new THREE.Vector3(...s)
      : new THREE.Vector3(1, 1, 1).add(axisOf(s.axis).multiplyScalar((+s.to || 0) - 1));
  }
  if (e.light) {
    const l = e.light;
    out.light = { color: new THREE.Color(...(Array.isArray(l.color) ? l.color : [1, 0.85, 0.7])),
                  intensity: +(l.intensity ?? 4), distance: +(l.distance ?? 8) };
  }
  return out;
}

// the value a channel has where an effect doesn't mention it (e.g. `on` = emissive 1 -> off = dark)
function neutral(ch, other, isOn) {
  switch (ch) {
    case 'visible': return !other;
    case 'emissive': return isOn ? 1 : 0;
    case 'slide': return new THREE.Vector3();
    case 'rotate': return new THREE.Quaternion();
    case 'scale': return new THREE.Vector3(1, 1, 1);
    case 'light': return { ...other, intensity: 0 };
  }
  return other;
}

export class Interactables {
  constructor(inventory, colliders, signals = new Signals(), scene = null) {
    this.items = [];
    this.reactors = [];
    this.inventory = inventory;
    this.colliders = colliders;   // shared with the player; moving parts add their box here
    this.signals = signals;
    this.scene = scene;           // for the point-light pool
    this.lights = null;           // [PointLight] once a `light` react exists
    this._box = new THREE.Box3();
    // who set each signal's initial value: reactors and use points only name it (0), a switch's
    // authored state (1), a placement's `state` (2), the level's "signals" (3). The highest wins
    // whatever the load order; unclaimed values resolve to false (power: on) in snapAll().
    this.claims = new Map();
    for (const n of signals.explicit ?? []) this.claims.set(n, { prio: 3, value: signals.get(n) });
    this.matCache = new Map();    // shared reactor / indicator materials (so they batch per room)
  }

  claim(name, value, prio) {
    if (!name) return;
    const c = this.claims.get(name);
    if (c && c.prio >= prio) return;
    this.claims.set(name, { prio, value });
    if (value !== undefined) this.signals.values.set(name, value);
  }

  // signals only reactors named start off
  resolve() {
    for (const n of this.claims.keys()) if (!this.signals.has(n)) this.signals.values.set(n, false);
  }

  // one material per (source material, what drives it): every mesh with the same key shows the
  // same thing at the same time, so the room batcher can merge them into one draw call
  sharedMaterial(src, key, make = cloneMaterial) {
    const k = `${src.uuid}|${key}`;
    if (!this.matCache.has(k)) {
      // the authored intensity: a source that is itself a reactor's copy may be dimmed right now
      const base = src.userData.emissiveBase ?? src.emissiveIntensity ?? 1;
      const m = make(src);
      m.userData.emissiveBase = base;
      m.emissiveIntensity = base;
      this.matCache.set(k, { m, base });
    }
    return this.matCache.get(k);
  }

  // placement options -> the signal a node uses: `signal` as a string renames every signal the
  // asset uses except `power`; as an object it maps authored names to placed ones
  signalFor(name, opts) {
    const o = opts.signal;
    if (o == null || name === 'power') return name;
    if (typeof o === 'string') return o;
    return o[name] ?? name;
  }

  collect(root, { lock = null, signal = null, state } = {}) {
    root.updateMatrixWorld(true);
    const opts = { signal, state };
    const added = [];
    root.traverse((node) => {
      const def = node.userData.interact;
      if (def) added.push(this.addItem(node, def, root, lock, opts));
      const react = node.userData.react;
      if (react) for (const r of Array.isArray(react) ? react : [react]) added.push(this.addReactor(node, r, opts));
    });
    // emissive / visibility reacts drive materials, shared by every mesh driven the same way
    const byNode = new Map();
    for (const a of added) if (a.isReactor && a.needsMats) (byNode.get(a.node) ?? byNode.set(a.node, []).get(a.node)).push(a);
    if (byNode.size) root.traverse((o) => {
      if (!o.isMesh || Array.isArray(o.material)) return;
      const rs = [];
      for (let n = o; n; n = n === root ? null : n.parent) rs.push(...(byNode.get(n) ?? []));
      if (!rs.length) return;
      const e = this.sharedMaterial(o.material, rs.map((r) => r.key).join('&'));
      o.material = e.m;
      for (const r of rs) if (!r.mats.includes(e)) r.mats.push(e);
    });
    // placement `state`: the initial value of the placement's own signal (its switch's / use
    // point's, else its reactors' other than power), set before anything is posed
    if (state !== undefined && state !== null) {
      const own = added.filter((a) => a.signal && (a.def?.type === 'switch' || a.def?.type === 'use'));
      const names = new Set((own.length ? own : added.filter((a) => a.isReactor && a.signal !== 'power')).map((a) => a.signal));
      for (const n of names) this.claim(n, typeof state === 'number' ? state : truthy(state), 2);
    }
    for (const a of added) this.snap(a);
    return added;
  }

  // add a prop built at runtime (tests, scripted scenes): collect + pose everything on its signals
  register(root, opts = {}) {
    const added = this.collect(root, opts);
    this.snapAll();
    return added;
  }

  addItem(node, def, root, lock, opts) {
    const motion = def.type === 'switch' ? def.travel : def;
    const it = {
      node, def, root, t: 0, target: 0, taken: false,
      lockKey: def.type === 'pickup' ? null : lock,
      locked: def.type !== 'pickup' && !!lock,
      axis: motion?.axis ? axisOf(motion.axis) : null,
      rest: node.position.clone(), restQuat: node.quaternion.clone(),
      host: def.type === 'pickup' ? this.hostOf(node) : null,
    };
    if (def.type === 'switch' || def.type === 'use') {
      it.signal = this.signalFor(def.signal, opts);
      if (def.type === 'switch') {
        this.claim(it.signal, truthy(def.state), 1);
        this.signals.on(it.signal, () => this.follow(it));
        this.signals.on('power', () => this.setSwitchIndicator(it));
      } else {
        it.value = def.value ?? true;
        this.claim(it.signal, undefined, 0);
      }
    }
    if (def.indicator) {
      it.indicator = root.getObjectByName(def.indicator);
      if (it.indicator) {
        it.indicatorColor = it.indicator.material.emissive.clone();
        // a switch's light is shared by every switch on its signal (they batch); a door's is its own
        it.indicator.material = def.type === 'switch' ? this.sharedMaterial(it.indicator.material, `led|${it.signal}`).m
          : it.indicator.material.clone();
      }
      if (def.type === 'switch') this.setSwitchIndicator(it);
      else this.setIndicator(it, it.locked ? RED : GREEN);
    }
    if (def.collide) {
      it.collider = new THREE.Box3();
      this.colliders.push(it.collider);
    }
    this.items.push(it);
    this.pose(it);
    return it;
  }

  addReactor(node, def, opts) {
    const on = parseEffect(def.on ?? 'show'), off = parseEffect(def.off);
    const chans = [...new Set([...Object.keys(on), ...Object.keys(off)])];
    for (const ch of chans) {
      if (!(ch in on)) on[ch] = neutral(ch, off[ch], true);
      if (!(ch in off)) off[ch] = neutral(ch, on[ch], false);
    }
    const moves = chans.some((c) => c === 'slide' || c === 'rotate' || c === 'scale');
    const electric = def.power !== undefined ? truthy(def.power) : chans.some((c) => c === 'light' || c === 'emissive' || c === 'visible');
    const r = {
      isReactor: true, node, def, on, off, chans, t: 0, target: 0,
      signal: this.signalFor(def.signal, opts),
      electric,
      blocksSight: truthy(def.block_sight) || truthy(node.userData.block_sight),
      duration: def.duration !== undefined ? +def.duration : moves ? 1.0 : 0.12,
      rest: node.position.clone(), restQuat: node.quaternion.clone(), restScale: node.scale.clone(),
      mats: [], level: 0,
      needsMats: chans.includes('emissive') || chans.includes('visible'),
    };
    // reactors that only change materials stay batchable; these keep their own nodes
    r.moves = moves || chans.includes('light') || r.blocksSight || truthy(def.collide);
    r.key = JSON.stringify([r.signal, r.electric, def.on ?? 'show', def.off ?? null, r.duration]);
    if (truthy(def.collide)) {      // solid once settled (a door that blocks when shut), like interact's
      r.collider = new THREE.Box3();
      this.colliders.push(r.collider);
    }
    if (chans.includes('light')) this.ensureLights();
    this.claim(r.signal, undefined, 0);
    this.signals.on(r.signal, () => this.aim(r));
    if (r.electric && r.signal !== 'power') this.signals.on('power', () => this.aim(r));
    this.reactors.push(r);
    return r;
  }

  ensureLights() {
    if (this.lights || !this.scene) return;
    // created once and kept (intensity 0 when unused): changing the number of lights in the
    // scene recompiles every material in the house
    this.lights = [];
    for (let i = 0; i < MAX_LIGHTS; i++) {
      const l = new THREE.PointLight(0xffffff, 0, 8, 2);
      l.castShadow = false;
      l.name = `ReactLight_${i}`;
      this.scene.add(l);
      this.lights.push(l);
    }
  }

  // is the signal live for this reactor (its signal on, and power for electric things)?
  live(r) {
    const v = this.signals.get(r.signal);
    return truthy(v) && (!r.electric || r.signal === 'power' || this.signals.get('power') !== false);
  }
  aim(r) { r.target = this.live(r) ? 1 : 0; }
  follow(it) {
    it.target = truthy(this.signals.get(it.signal)) ? 1 : 0;
    this.setSwitchIndicator(it);
  }

  // jump straight to the state the signals say (at load, no animation)
  snap(a) {
    if (a.isReactor) { this.aim(a); a.t = a.target; this.poseReactor(a); return; }
    if (a.def.type === 'switch') { this.follow(a); a.t = a.target; this.pose(a); }
  }
  snapAll() { this.resolve(); for (const a of [...this.items, ...this.reactors]) this.snap(a); }

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

  // a switch's status light: its authored glow (green if it has none) while on and powered
  setSwitchIndicator(it) {
    if (!it.indicator) return;
    const lit = truthy(this.signals.get(it.signal)) && this.signals.get('power') !== false;
    const c = it.indicatorColor.getHex() ? it.indicatorColor : GREEN;
    it.indicator.material.emissive.copy(c);
    it.indicator.material.emissiveIntensity = lit ? 1.5 : 0;
  }

  pose(it) {
    const k = ease(it.t);
    const d = it.def.type === 'switch' ? it.def.travel : it.def;
    const kind = it.def.type === 'switch' ? (d?.angle !== undefined ? 'rotate' : d?.distance !== undefined ? 'slide' : null) : it.def.type;
    if (kind === 'slide') {
      it.node.position.copy(it.rest).addScaledVector(it.axis, d.distance * k);
    } else if (kind === 'rotate') {
      const turn = new THREE.Quaternion().setFromAxisAngle(it.axis, THREE.MathUtils.degToRad(d.angle) * k);
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

  poseReactor(r) {
    const k = ease(r.t), { on, off, node } = r;
    if (on.slide) node.position.copy(r.rest).add(new THREE.Vector3().lerpVectors(off.slide, on.slide, k));
    if (on.rotate) node.quaternion.copy(r.restQuat).multiply(new THREE.Quaternion().slerpQuaternions(off.rotate, on.rotate, k));
    if (on.scale) node.scale.copy(r.restScale).multiply(new THREE.Vector3().lerpVectors(off.scale, on.scale, k));
    if (on.visible !== undefined) {
      const v = r.t >= 0.5 ? on.visible : off.visible;
      if (r.mats.length) for (const { m } of r.mats) m.visible = v;   // (works on the room's batch too)
      else node.visible = v;
    }
    if (on.emissive !== undefined) {
      const e = off.emissive + (on.emissive - off.emissive) * k;
      for (const { m, base } of r.mats) m.emissiveIntensity = base * e;
    }
    if (on.light) r.level = off.light.intensity + (on.light.intensity - off.light.intensity) * k;
    if (r.collider) {
      node.updateMatrixWorld(true);
      if (r.t === r.target) r.collider.setFromObject(node);
      else r.collider.makeEmpty();
    }
  }

  // closed blinds (and anything else with block_sight) whose signal is on: world boxes the
  // Grimble's sight rays can't pass
  sightBlockers() {
    const out = [];
    for (const r of this.reactors) {
      if (!r.blocksSight || r.t < 0.5) continue;
      out.push(new THREE.Box3().setFromObject(r.node));
    }
    return out;
  }

  // is the segment a -> b blocked by a sight blocker?
  blocksSight(a, b) {
    const dir = new THREE.Vector3().subVectors(b, a), len = dir.length();
    const ray = new THREE.Ray(a, dir.normalize()), hit = new THREE.Vector3();
    return this.sightBlockers().some((box) => ray.intersectBox(box, hit) && hit.distanceTo(a) < len);
  }

  done(it) { return it.def.type === 'use' && this.signals.get(it.signal) === it.value; }

  available(it) {
    if (it.def.type === 'use') return !this.done(it) || !!it.def.promptDone;
    if (it.def.type !== 'pickup') return true;
    return !it.taken && (!it.host || (it.host.t === 1 && it.host.target === 1));
  }

  centre(it) {
    return new THREE.Box3().setFromObject(it.node).getCenter(new THREE.Vector3());
  }

  // horizontal distance from a point to the nearest edge of the item (so an open
  // door that has swung away is still in reach from the doorway)
  reach(it, point) {
    const box = this._box.setFromObject(it.node);
    const dx = Math.max(box.min.x - point.x, 0, point.x - box.max.x);
    const dz = Math.max(box.min.z - point.z, 0, point.z - box.max.z);
    return Math.hypot(dx, dz);
  }

  range(it) { return it.def.range ?? (it.def.type === 'switch' || it.def.type === 'use' ? 1.2 : 1.5); }

  // what the player can use from here: pickups first, then the nearest thing
  nearest(player) {
    const off = new THREE.Vector3(), dir = new THREE.Vector3();
    let best = null, bestScore = Infinity;
    for (const it of this.items) {
      if (!this.available(it)) continue;
      const d = this.reach(it, player);
      if (d > this.range(it)) continue;
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

  itemName(id) {
    return (this.inventory.name(id) ?? id.replace(/^key_/, 'key ').replace(/_/g, ' ')).toLowerCase();
  }

  prompt(it) {
    const d = it.def;
    if (d.type === 'pickup') return d.prompt;
    if (it.locked) return d.lockedPrompt || 'Locked';
    if (d.type === 'switch') return truthy(this.signals.get(it.signal)) ? (d.promptActive || 'Turn off') : (d.prompt || 'Turn on');
    if (d.type === 'use') {
      if (this.done(it)) return d.promptDone;
      if (!d.needs) return d.prompt;
      const name = d.needsName?.toLowerCase() ?? this.itemName(d.needs);
      if (this.inventory.armed === d.needs) return d.prompt;
      if (this.inventory.has(d.needs)) return `${d.prompt} · arm the ${name}`;
      return `${d.prompt} · needs a ${name}`;
    }
    return it.target ? d.promptActive : d.prompt;
  }

  // the lockable item the armed key works on from here, if any
  lockTarget(itemId, player) {
    let best = null, bestD = Infinity;
    for (const it of this.items) {
      if (it.lockKey !== itemId) continue;
      const d = this.reach(it, player);
      if (d <= this.range(it) && d < bestD) { best = it; bestD = d; }
    }
    return best;
  }

  // the `use` point that wants the armed item, in reach and not done yet
  useTarget(itemId, player) {
    let best = null, bestD = Infinity;
    for (const it of this.items) {
      if (it.def.type !== 'use' || it.def.needs !== itemId || this.done(it)) continue;
      const d = this.reach(it, player);
      if (d <= this.range(it) && d < bestD) { best = it; bestD = d; }
    }
    return best;
  }

  // hint for the armed item ("Unlock door", "Throw vase", "Insert fuse"), or null if it does nothing here
  armedPrompt(itemId, player) {
    const entry = this.inventory.get(itemId);
    if (!entry) return null;
    if (entry.def.throwable) return `Throw ${entry.name.toLowerCase()}`;
    const use = this.useTarget(itemId, player);
    if (use) return use.def.prompt;
    const lock = this.lockTarget(itemId, player);
    if (lock) return lock.locked ? 'Unlock door' : 'Lock door';
    return null;
  }

  // Enter with an armed item: a `use` point that needs it, else a lock it fits; returns a
  // message, or null when the item has no target here
  useItem(itemId, player) {
    const it = this.useTarget(itemId, player);
    if (!it) return this.lockTarget(itemId, player) ? this.useKey(itemId, player) : null;
    this.signals.set(it.signal, it.value);
    if (it.def.consume !== false && it.def.consume !== 0) this.inventory.remove(itemId);
    return it.def.promptDone || 'Done';
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
    if (d.type === 'switch') {
      this.signals.toggle(it.signal);
      return null;
    }
    if (d.type === 'use') {
      if (this.done(it)) return null;
      if (!d.needs) { this.signals.set(it.signal, it.value); return d.promptDone || null; }
      const name = d.needsName?.toLowerCase() ?? this.itemName(d.needs);
      if (this.inventory.armed === d.needs) return `Press Enter to use the ${name}`;
      if (this.inventory.has(d.needs)) return `Arm the ${name} (I, then Enter)`;
      return `Needs a ${name}`;
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

  // advance animations; returns the items and reactors that moved this frame. `eye` (the
  // camera position) picks which lit reactors get the pool's point lights.
  update(dt, eye = null) {
    const moved = [];
    for (const it of this.items) {
      if (it.t === it.target || it.def.type === 'pickup') continue;
      const step = dt / (it.def.duration ?? 0.15);
      it.t = it.target > it.t ? Math.min(it.target, it.t + step) : Math.max(it.target, it.t - step);
      this.pose(it);
      moved.push(it);
    }
    for (const r of this.reactors) {
      if (r.t === r.target) continue;
      const step = r.duration > 0 ? dt / r.duration : 1;
      r.t = r.target > r.t ? Math.min(r.target, r.t + step) : Math.max(r.target, r.t - step);
      this.poseReactor(r);
      moved.push(r);
    }
    if (this.lights) this.assignLights(eye);
    return moved;
  }

  // the pool's lights go to the lit `light` reactors nearest the eye
  assignLights(eye) {
    const lit = this.reactors.filter((r) => r.on.light && r.level > 0);
    const wp = new THREE.Vector3();
    for (const r of lit) r._d = eye ? r.node.getWorldPosition(wp).distanceToSquared(eye) : 0;
    lit.sort((a, b) => a._d - b._d);
    this.lights.forEach((l, i) => {
      const r = lit[i];
      if (!r) { l.intensity = 0; return; }
      r.node.getWorldPosition(l.position);
      l.color.copy(r.on.light.color);
      l.distance = r.on.light.distance;
      l.intensity = r.level;
    });
  }
}

export class Inventory {
  // Items the player carries, stacked by item id (three vases are one "Glass vase x3" row).
  // One kind can be armed (held, ready to use); the inventory screen (I) picks which. `nodes`
  // are the picked-up 3D models (the last one is shown in the hand or thrown); `node` is it.
  constructor(onChange) {
    this.items = new Map();   // id -> { name, nodes, node, count, def }
    this.armed = null;
    this.open = false;
    this.sel = 0;
    this.onChange = onChange;
  }
  changed() { this.onChange?.(this); }
  add(id, name, node = null, def = {}) {
    const it = this.items.get(id) ?? { name, nodes: [], def, count: 0 };
    if (node) it.nodes.push(node);
    it.count++;
    it.node = it.nodes[it.nodes.length - 1] ?? null;
    this.items.set(id, it);
    this.changed();
  }
  // one of `id` is used up (thrown, consumed); the kind goes when the last one does
  remove(id) {
    const it = this.items.get(id);
    if (!it) return;
    it.count--;
    it.nodes.pop();
    it.node = it.nodes[it.nodes.length - 1] ?? null;
    if (it.count > 0) { this.changed(); return; }
    this.items.delete(id);
    if (this.armed === id) this.armed = null;
    this.sel = Math.min(this.sel, Math.max(0, this.items.size - 1));
    this.changed();
  }
  has(id) { return this.items.has(id); }
  get(id) { return this.items.get(id); }
  name(id) { return this.items.get(id)?.name; }
  count(id) { return this.items.get(id)?.count ?? 0; }
  label(id) { const n = this.count(id); return n > 1 ? `${this.name(id)} ×${n}` : this.name(id); }
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
