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

export function batchRooms(roomRoots, skip) {
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
        if (Array.isArray(m) || m.transparent || m.alphaTest > 0) return;
        const g = o.geometry;
        const key = `${m.uuid}|${Object.keys(g.attributes).sort().join(',')}|${g.index ? 1 : 0}`;
        if (!groups.has(key)) groups.set(key, { material: m, items: [] });
        groups.get(key).items.push(o);
      });
    }
    batches[room] = [];
    for (const { material, items } of groups.values()) {
      if (items.length < 2) continue;
      const geos = items.map((o) => o.geometry.clone().applyMatrix4(o.matrixWorld));
      const merged = mergeGeometries(geos, false);
      geos.forEach((g) => g.dispose());
      if (!merged) continue;
      const mesh = new THREE.Mesh(merged, material);
      mesh.castShadow = items[0].castShadow;          // per room: off where the sun never reaches
      mesh.receiveShadow = items[0].receiveShadow;
      mesh.name = `Batch_${room}_${material.name}`;
      for (const o of items) o.removeFromParent();
      batches[room].push(mesh);
    }
  }
  for (const roots of Object.values(roomRoots)) for (const r of roots) r.traverse((o) => { if (o.isMesh) after++; });
  for (const b of Object.values(batches)) after += b.length;
  return { batches, before, after };
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
    this.rooms = Object.entries(level.rooms).map(([name, r]) => ({
      name, rect: r.rect, level: r.level,
      always: name.includes('gallery') || name === 'courtyard',
      // open to the other floor: double height (they reach the upper floor), the gallery
      // ring and courtyard (glass and balustrades), the library (glass into the great room)
      vertical: name.includes('gallery') || name === 'courtyard' || name === 'library' || r.height > 5,
      sun: r.sun !== false,                     // its furniture casts real-time sun shadows
      sees: r.sees ? new Set(r.sees) : null,    // rooms visible from here, doors closed (visibility.py)
      seesOpen: r.seesOpen ? new Set(r.seesOpen) : null,   // ... with every door open
      box: new THREE.Box3(new THREE.Vector3(r.rect[0], r.floor, r.rect[1]),
                          new THREE.Vector3(r.rect[2], r.floor + (r.height || 4), r.rect[3])),
      objects: [...(roomRoots[name] || []), ...(batches[name] || [])],
    }));
    this.visible = this.rooms.length;
  }

  // returns true when the set of drawn sunlit rooms changed (the shadow map then needs
  // redrawing; furniture in sunless rooms casts no real-time shadows)
  update(pos, camera = null) {
    let n = 0, changed = false;
    if (camera) this._frustum.setFromProjectionMatrix(this._m.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse));
    const level = pos.y > this.upperY ? 1 : 0;
    // the room the eye is in: if it's open to the other floor, so is the view
    const here = this.rooms.find((r) => r.level === level && pos.x >= r.rect[0] && pos.x <= r.rect[2] && pos.z >= r.rect[1] && pos.z <= r.rect[3])
      ?? this.rooms.find((r) => pos.x >= r.rect[0] && pos.x <= r.rect[2] && pos.z >= r.rect[1] && pos.z <= r.rect[3] && r.vertical);
    this.here = here ?? null;            // (outdoors: null)
    const crossFloor = !here || here.vertical;
    for (const r of this.rooms) {
      const [x0, z0, x1, z1] = r.rect;
      const dx = Math.max(x0 - pos.x, 0, pos.x - x1);
      const dz = Math.max(z0 - pos.z, 0, pos.z - z1);
      const sameFloor = r.level === level || (r.vertical && crossFloor);
      const d = Math.hypot(dx, dz);
      const inView = !camera || this._frustum.intersectsBox(r.box);
      const sight = !here?.sees || here.sees.has(r.name);               // sight line, doors closed
      const reach = !here?.seesOpen || here.seesOpen.has(r.name);       // ... or through a door opened
      const show = r.always || (sameFloor && d < this.near && reach) ||
        (d < this.far && inView && sight && (sameFloor || here?.sees));
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
