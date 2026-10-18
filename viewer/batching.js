import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

// A whole house of furniture is thousands of small meshes. Two things keep it cheap:
//  1. batchRooms(): per room, every static, opaque prop mesh is merged into one mesh per
//     material (moving parts - doors, drawers, pickups - and transparent materials stay
//     separate). A room becomes tens of draw calls instead of hundreds.
//  2. RoomCuller: furniture in rooms far from the player isn't drawn. Walls (the shell)
//     always are, so nothing pops in at close range; galleries and the courtyard always draw.

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
      mesh.castShadow = mesh.receiveShadow = true;
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
    this.rooms = Object.entries(level.rooms).map(([name, r]) => ({
      name, rect: r.rect,
      always: name.includes('gallery') || name === 'courtyard',
      objects: [...(roomRoots[name] || []), ...(batches[name] || [])],
    }));
    this.visible = this.rooms.length;
  }

  // returns true when the set of drawn rooms changed (the shadow map then needs redrawing)
  update(pos) {
    let n = 0, changed = false;
    for (const r of this.rooms) {
      const [x0, z0, x1, z1] = r.rect;
      const dx = Math.max(x0 - pos.x, 0, pos.x - x1);
      const dz = Math.max(z0 - pos.z, 0, pos.z - z1);
      const show = r.always || Math.hypot(dx, dz) < this.radius;
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
