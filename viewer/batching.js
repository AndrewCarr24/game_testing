import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

// A whole house of furniture is thousands of small meshes. Two things keep it cheap:
//  1. batchRooms(): per room, every static, opaque prop mesh is merged into one mesh per
//     material (moving parts - doors, drawers, pickups - and transparent materials stay
//     separate). A room becomes tens of draw calls instead of hundreds.
//  2. RoomCuller: furniture is drawn within 14 m if a sight line could exist with doors open (so
//     turning round, or opening a door, finds it there), and out to
//     36 m for rooms in view that the player's room can see into (mansion.json rooms[r].sees,
//     from blender/levels/visibility.py: sight lines through openings and interior glass, doors
//     closed). A flat 18 m left rooms seen through a doorway from across the dining room as bare
//     walls with the furniture's baked shadows on them, which popped in late. Not drawn either:
//     ordinary rooms
//     on the other floor (a slab is in the way; only the double-height rooms, the gallery
//     ring around the courtyard and the library's window into the great room see across
//     floors). Walls (the shell) always draw, so nothing pops in at close range; galleries
//     and the courtyard always draw. Hidden furniture also leaves the sun's shadow pass.

// Resting pickups (`resting`: mesh -> its pickup item; the books, vases, candles... of the decor
// vignettes, hundreds of them) are merged too, so splitting a vignette into pickups costs no draw
// calls: their own meshes stay in place but hidden (boxes, the hand and throws still use them),
// each item remembers its range in the batch (`item.batched`), and unbatch() collapses that range
// and shows the item's own meshes when it is focused or taken. Glass pickups (transparent, never
// merged per room) merge per placement and material instead: what one vignette's glass cost before.
export function batchRooms(roomRoots, skip, resting = new Map()) {
  const batches = {};   // room -> [mesh]
  let before = 0, after = 0;
  for (const [room, roots] of Object.entries(roomRoots)) {
    const groups = new Map();
    for (const root of roots) {
      root.updateMatrixWorld(true);
      root.traverse((o) => {
        if (!o.isMesh || skip.has(o)) return;
        before++;
        const m = o.material;
        const glass = resting.has(o) && !Array.isArray(m) && m.transparent && !(m.alphaTest > 0);
        if (Array.isArray(m) || ((m.transparent || m.alphaTest > 0) && !glass)) return;
        const g = o.geometry;
        const key = `${glass ? root.uuid : ''}${m.uuid}|${Object.keys(g.attributes).sort().join(',')}|${g.index ? 1 : 0}`;
        if (!groups.has(key)) groups.set(key, { material: m, items: [] });
        groups.get(key).items.push(o);
      });
    }
    batches[room] = [];
    for (const { material, items } of groups.values()) {
      if (items.length < 2) continue;
      const geos = items.map((o) => o.geometry.clone().applyMatrix4(o.matrixWorld));
      const merged = mergeGeometries(geos, false);
      if (!merged) { geos.forEach((g) => g.dispose()); continue; }
      const mesh = new THREE.Mesh(merged, material);
      mesh.castShadow = items[0].castShadow;          // per room: off where the sun never reaches
      mesh.receiveShadow = items[0].receiveShadow;
      mesh.name = `Batch_${room}_${material.name}`;
      let start = 0;
      items.forEach((o, i) => {
        const count = geos[i].index ? geos[i].index.count : geos[i].attributes.position.count;
        const it = resting.get(o);
        if (it) {
          (it.batched ??= []).push({ geometry: merged, start, count, mesh: o });
          o.visible = false;
        } else o.removeFromParent();
        start += count;
      });
      geos.forEach((g) => g.dispose());
      batches[room].push(mesh);
    }
  }
  for (const roots of Object.values(roomRoots)) for (const r of roots) r.traverse((o) => { if (o.isMesh && o.visible) after++; });   // (resting pickups' own meshes are hidden)
  for (const b of Object.values(batches)) after += b.length;
  return { batches, before, after };
}

// a pickup leaves its room batch: its triangles there collapse to nothing, its own meshes show
export function unbatch(item) {
  for (const { geometry, start, count, mesh } of item.batched ?? []) {
    const index = geometry.index;
    if (index) {
      index.array.fill(index.array[start], start, start + count);
      index.needsUpdate = true;
    } else {
      const pos = geometry.attributes.position;
      for (let i = start + 1; i < start + count; i++) pos.setXYZ(i, pos.getX(start), pos.getY(start), pos.getZ(start));
      pos.needsUpdate = true;
    }
    mesh.visible = true;
  }
  item.batched = null;
}

export class RoomCuller {
  // shared: [{ obj, rooms }] drawn when any of its rooms is (doors join two rooms)
  constructor(level, roomRoots, batches, { near = 14, far = 36, shared = [] } = {}) {
    this.shared = shared;
    this.near = near;
    this.far = far;
    this._frustum = new THREE.Frustum();
    this._m = new THREE.Matrix4();
    this._box = new THREE.Box3();
    const upperY = Math.min(...Object.values(level.rooms).filter((r) => r.level === 1).map((r) => r.floor));
    this.upperY = upperY - 0.5;            // eye above this = on the upper floor
    // (below ground) rooms under the house (plan level -1): found first, by their own height
    // span (a shaft stands inside a room above ground); `sealed` ones see nothing above ground
    this.lowerY = Math.min(0, ...Object.values(level.rooms).filter((r) => r.level >= 0).map((r) => r.floor)) - 0.5;
    this.rooms = Object.entries(level.rooms).map(([name, r]) => ({
      name, rect: r.rect, level: r.level, floor: r.floor, height: r.height || 4, sealed: !!r.sealed,
      area: (r.rect[2] - r.rect[0]) * (r.rect[3] - r.rect[1]),
      always: name.includes('gallery') || name === 'courtyard',
      // open to the other floor: double height (they reach the upper floor), the gallery
      // ring and courtyard (glass and balustrades), the library (glass into the great room)
      vertical: name.includes('gallery') || name === 'courtyard' || name === 'library' || r.height > 5,
      sun: r.sun !== false,                     // its furniture casts real-time sun shadows
      sees: r.sees ? new Set(r.sees) : null,    // rooms visible from here, doors closed (visibility.py)
      outside: r.outside || null,               // its openings in the outer walls (going outside, below)
      seesOpen: r.seesOpen ? new Set(r.seesOpen) : null,   // ... with every door open
      box: new THREE.Box3(new THREE.Vector3(r.rect[0], r.floor, r.rect[1]),
                          new THREE.Vector3(r.rect[2], r.floor + (r.height || 4), r.rect[3])),
      objects: [...(roomRoots[name] || []), ...(batches[name] || [])],
    }));
    this.visible = this.rooms.length;
    this.outdoors = !!level.grounds && this.rooms.some((r) => r.outside);    // (a level with walkable grounds)
  }

  // outdoors: one of r's outer-wall openings faces the eye (it's in front of the opening's plane)
  facing(r, pos) {
    if (!r.outside) return false;
    return r.outside.some(([x0, z0, x1, z1, nx, nz]) => (pos.x - (x0 + x1) / 2) * nx + (pos.z - (z0 + z1) / 2) * nz > 0.05);
  }

  // outdoors: r is seen through a room whose opening faces the eye from within `near`
  seenThrough(r, pos) {
    for (const f of this.rooms) {
      if (f === r || !f.sees?.has(r.name) || !this.facing(f, pos)) continue;
      const [x0, z0, x1, z1] = f.rect;
      if (Math.hypot(Math.max(x0 - pos.x, 0, pos.x - x1), Math.max(z0 - pos.z, 0, pos.z - z1)) < this.near) return true;
    }
    return false;
  }

  // returns true when the set of drawn sunlit rooms changed (the shadow map then needs
  // redrawing; furniture in sunless rooms casts no real-time shadows)
  update(pos, camera = null) {
    let n = 0, changed = false;
    if (camera) this._frustum.setFromProjectionMatrix(this._m.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse));
    const inRect = (r) => pos.x >= r.rect[0] && pos.x <= r.rect[2] && pos.z >= r.rect[1] && pos.z <= r.rect[3];
    // (below ground) the smallest room below ground whose own span holds the eye wins
    let under = null;
    for (const r of this.rooms) {
      if (r.level >= 0 || !inRect(r) || pos.y < r.floor - 0.3 || pos.y > r.floor + r.height + 0.3) continue;
      if (!under || r.area < under.area) under = r;
    }
    const level = under ? under.level : pos.y > this.upperY ? 1 : pos.y < this.lowerY ? -1 : 0;
    // the room the eye is in: if it's open to the other floor, so is the view
    const here = under ?? this.rooms.find((r) => r.level === level && inRect(r))
      ?? this.rooms.find((r) => inRect(r) && r.vertical);
    this.here = here ?? null;            // (outdoors: null)
    const crossFloor = !here || here.vertical;
    const sealed = !!here?.sealed;       // (below ground) nothing above ground can be seen from here
    for (const r of this.rooms) {
      const [x0, z0, x1, z1] = r.rect;
      const dx = Math.max(x0 - pos.x, 0, pos.x - x1);
      const dz = Math.max(z0 - pos.z, 0, pos.z - z1);
      const sameFloor = r.level === level || (r.vertical && crossFloor);
      const d = Math.hypot(dx, dz);
      const inView = !camera || this._frustum.intersectsBox(r.box);
      const sight = !here?.sees || here.sees.has(r.name);               // sight line, doors closed
      const reach = !here?.seesOpen || here.seesOpen.has(r.name);       // ... or through a door opened
      let show = r.always || (sameFloor && d < this.near && reach) ||
        (d < this.far && inView && sight && (sameFloor || here?.sees));
      if (sealed && r.level >= 0) show = false;                          // (below ground)
      // (below ground) from above ground: only one the room sees (the den's slot), or a shaft
      // whose way in stands open (`force`)
      if (r.level < 0 && here?.level >= 0 && !(here.sees?.has(r.name) && inView && d < this.far)) show = false;
      if (r.level < 0 && !here) show = false;
      if (r.force && d < this.near) show = true;      // (a shaft whose floor is open: secret_passage.js)
      // ---- going outside: outdoors (no room here) a room is seen only through its own windows
      // and doorways in the outer walls (rooms[r].outside, ground_colliders.facades), from the
      // side they face; close to one (within `near`) also the rooms it sees into
      if (!here && this.outdoors) show = r.always || (d < this.far && inView && (this.facing(r, pos) || this.seenThrough(r, pos)));
      if (show !== r.shown) {
        for (const o of r.objects) o.visible = show;
        if (r.sun || r.shown === undefined) changed = true;
        r.shown = show;
      }
      // beyond close range furniture still draws but leaves the sun's shadow pass: its
      // real-time shadow is invisible from there (the baked ones carry the look), and in
      // big views (the entry seeing half the house through the courtyard) the shadow pass
      // would otherwise draw all of it a second time
      const far = show && !r.always && d >= this.near;
      if (r.sun && far !== r.far) {
        for (const root of r.objects) root.traverse((o) => {
          if (!o.isMesh) return;
          if (o.userData.cast === undefined) o.userData.cast = o.castShadow;
          o.castShadow = o.userData.cast && !far;
        });
        r.far = far;
        changed = true;
      }
      if (show) n++;
    }
    for (const s of this.shared) {
      const show = s.rooms.some((name) => this.rooms.find((r) => r.name === name)?.shown);
      if (show !== s.obj.visible) { s.obj.visible = show; changed = true; }
    }
    this.visible = n;
    return changed;
  }
}
