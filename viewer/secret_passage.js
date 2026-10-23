import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

// The secret passage (design/house/secret_passage.md) and, generally, the rooms below ground.
//
//  - Moving pieces of the shell: shell meshes with a `react` in their extras (the library's
//    folding floor: house.py fold_floor) are registered with the interactables like any prop's
//    reactors (signal `secret_library`, set by the rolling ladder and the buttons below; slide
//    down, solid once settled). They're lightmapped with their room's floor. While the floor is
//    shut and settled they cost nothing: their geometry is merged into the floor mesh they lie
//    in (same material) and the pieces are hidden; the moment their signal changes the floor
//    mesh gets its own geometry back and the pieces draw (with their room's furniture).
//  - Rooms below ground (mansion.json rooms[r].level < 0): their shell meshes move out of the
//    house's shell into their own group and are culled with their room (RoomCuller: drawn only
//    from below ground, from a room that sees into one (the den's slot), or while a shaft's way
//    in stands open). While the eye is in a `sealed` room (the armory, the tunnels) the house's
//    shell, the grounds and the sky aren't drawn: nothing above ground can be seen from there.
export class SecretPassage {
  constructor({ scene, shell, outdoor = null, sky = null, culler, level, interact, renderer }) {
    Object.assign(this, { scene, shell, outdoor, sky, culler, level, interact, renderer });
    const rooms = level.rooms;
    const names = Object.keys(rooms).sort((a, b) => b.length - a.length);   // longest first ("tunnel_e" before "tunnel")
    const roomOf = (o) => names.find((n) => o.name.startsWith(`Mansion_${n}_`));
    const cullRoom = (name) => culler.rooms.find((r) => r.name === name);
    this.below = new THREE.Group();
    this.below.name = 'Mansion_BelowGround';
    scene.add(this.below);
    const moving = [], under = [];
    shell.updateMatrixWorld(true);
    shell.traverse((o) => {
      if (o.isMesh && o.userData.react) moving.push(o);
      else if (o.isMesh) { const room = roomOf(o); if (room && (rooms[room].level < 0 || rooms[room].below)) under.push([o, room]); }   // (below: the bathhouse's stair)
    });
    for (const [o, room] of under) {
      this.below.attach(o);              // (keeps its world transform)
      cullRoom(room)?.objects.push(o);
    }
    // the moving pieces, grouped by the floor mesh they lie in (room + material)
    this.groups = new Map();
    for (const o of moving) {
      const room = roomOf(o);
      const host = room && shell.getObjectByName(`Mansion_${room}_${o.material?.name}`);
      const key = host ? host.name : o.name;
      if (!this.groups.has(key)) this.groups.set(key, { room, host, pieces: [], items: [], closedGeo: null, openGeo: host?.geometry, shut: null });
      const g = this.groups.get(key);
      g.pieces.push(o);
      g.items.push(...interact.register(o));
    }
    for (const g of this.groups.values()) {
      if (g.host) {
        // the shut floor: the floor mesh's own geometry plus every piece in place (one draw call)
        const inv = new THREE.Matrix4().copy(g.host.matrixWorld).invert();
        const parts = [g.host.geometry, ...g.pieces.map((p) => p.geometry.clone().applyMatrix4(new THREE.Matrix4().multiplyMatrices(inv, p.matrixWorld)))];
        try { g.closedGeo = mergeGeometries(parts, false); } catch (err) { console.warn('secret_passage: merge failed', err); }
      }
      g.cull = g.room ? cullRoom(g.room) : null;
    }
    // shafts below ground that a moving floor opens into: drawn from above while it's open
    this.shafts = culler.rooms.filter((r) => r.level < 0 && rooms[r.name]?.kind === 'shaft');
    this.sealed = false;
    this.stats = { pieces: moving.length, below: under.length, groups: this.groups.size };
    this.update(true);
  }

  // is a group shut and settled (every piece at rest and staying there)?
  shutOf(g) { return g.items.every((r) => r.t === 0 && r.target === 0); }

  update(first = false) {
    let open = false;
    for (const g of this.groups.values()) {
      const shut = this.shutOf(g);
      open ||= !shut;
      if (shut !== g.shut) {
        g.shut = shut;
        if (g.host && g.closedGeo) g.host.geometry = shut ? g.closedGeo : g.openGeo;
      }
      const vis = !(shut && g.closedGeo) && (!g.cull || g.cull.shown !== false);
      for (const p of g.pieces) if (p.visible !== vis) p.visible = vis;
    }
    for (const s of this.shafts) s.force = open;
    const sealed = !!this.culler.here?.sealed;
    if (sealed === this.sealed && !first) return;
    this.sealed = sealed;
    this.shell.visible = !sealed;
    if (this.outdoor) this.outdoor.visible = !sealed;
    if (this.sky?.dome) this.sky.dome.visible = !sealed;
    if (this.renderer) this.renderer.shadowMap.needsUpdate = true;
  }
}
