import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

// A whole house of furniture is thousands of small meshes. Two things keep it cheap:
//  1. batchRooms(): per room, every static, opaque prop mesh is merged into one mesh per
//     material (moving parts - doors, drawers, pickups - and transparent materials stay
//     separate). A room becomes tens of draw calls instead of hundreds.
//  2. RoomCuller: furniture in rooms far from the player isn't drawn, nor in ordinary rooms
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
  constructor(level, roomRoots, batches, radius = 18) {
    this.radius = radius;
    const upperY = Math.min(...Object.values(level.rooms).filter((r) => r.level === 1).map((r) => r.floor));
    this.upperY = upperY - 0.5;            // eye above this = on the upper floor
    this.rooms = Object.entries(level.rooms).map(([name, r]) => ({
      name, rect: r.rect, level: r.level,
      always: name.includes('gallery') || name === 'courtyard',
      // open to the other floor: double height (they reach the upper floor), the gallery
      // ring and courtyard (glass and balustrades), the library (glass into the great room)
      vertical: name.includes('gallery') || name === 'courtyard' || name === 'library' || r.height > 5,
      objects: [...(roomRoots[name] || []), ...(batches[name] || [])],
    }));
    this.visible = this.rooms.length;
  }

  // returns true when the set of drawn rooms changed (the shadow map then needs redrawing)
  update(pos) {
    let n = 0, changed = false;
    const level = pos.y > this.upperY ? 1 : 0;
    // the room the eye is in: if it's open to the other floor, so is the view
    const here = this.rooms.find((r) => r.level === level && pos.x >= r.rect[0] && pos.x <= r.rect[2] && pos.z >= r.rect[1] && pos.z <= r.rect[3])
      ?? this.rooms.find((r) => pos.x >= r.rect[0] && pos.x <= r.rect[2] && pos.z >= r.rect[1] && pos.z <= r.rect[3] && r.vertical);
    const crossFloor = !here || here.vertical;
    for (const r of this.rooms) {
      const [x0, z0, x1, z1] = r.rect;
      const dx = Math.max(x0 - pos.x, 0, pos.x - x1);
      const dz = Math.max(z0 - pos.z, 0, pos.z - z1);
      const sameFloor = r.level === level || (r.vertical && crossFloor);
      const show = r.always || (sameFloor && Math.hypot(dx, dz) < this.radius);
      if (show !== r.shown) {
        for (const o of r.objects) o.visible = show;
        r.shown = show;
        changed = true;
      }
      if (show) n++;
    }
    this.visible = n;
    return changed;
  }
}
