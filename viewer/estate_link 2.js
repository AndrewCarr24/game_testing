import * as THREE from 'three';

// The estate <-> wilderness link (design/wilderness/estate_link.md), shared by the house
// (viewer/estate_gate.js, index.html) and the wilderness (viewer/wild/estate.js, wild.html).
//
// One place, two levels: the house level (index.html?level=mansion) and Laurel Fork Cove
// (wild.html?world=laurel_fork) share one frame up to a shift: wild three.js z = house z - 810
// (x and height identical; world.json estate_offset). The gate in the hedge (house z = 62, the
// drive's mouth x 15.8..23.7) is the seam: walking out through it hands the player to the
// wilderness, walking back in hands them to the house.
//
// The handoff (prototype): the house page is the game's shell. The first time its gate opens it
// loads the wilderness into a full-window iframe (same origin) and pauses it there; crossing the
// gate line suspends the house (no frames, no input) and shows the live wilderness with the
// player's state handed over (position, look, velocity, crouch, the carried items, flashlight,
// anything a system registers with `provide`). Walking back through the gate does the reverse,
// instantly: both levels stay alive, so the house keeps every door, pickup, broken window and
// invader exactly as it was. Opened on its own (no house around it), wild.html walks back by
// navigating to the house with the state in sessionStorage (estate_gate.js picks it up).

export const OFFSET_Z = -810;                     // wild z = house z + OFFSET_Z
export const GATE = {
  x0: 15.78, x1: 23.72, z: 62.0,                  // the two sliding leaves (gate_leaf: 3.96 m each)
  mouth: [15.9, 23.6],                            // the walkable opening between the piers
  line: 62.7,                                     // crossing this (house z) going out = into the wilderness
  back: 62.6,                                     // ... and this going in (from the wild) = into the house
  slide: 3.95,                                    // how far each leaf runs into the wing walls
};
export const STATE_KEY = 'gt_estate_link';

// The gate leaves out of a merged, baked grounds mesh (the house's Mansion_Outdoor_Flat or the
// wild's copy of it): the triangles inside each leaf's box become their own meshes (sharing the
// vertex buffers, so the baked vertex colours come along), left and right, ready to slide open.
export function splitGateLeaves(mesh) {
  const g = mesh.geometry, idx = g.index, pos = g.attributes.position;
  if (!idx) return null;
  mesh.updateMatrixWorld(true);
  const toLocal = new THREE.Matrix4().copy(mesh.matrixWorld);
  const keep = [], L = [], R = [];
  const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3();
  const x0 = GATE.x0 - 0.02, x1 = GATE.x1 + 0.02, mid = (GATE.x0 + GATE.x1) / 2;
  const zOff = mesh.userData.houseZ ?? 0;         // (the wild's copy sits at z - 810)
  for (let t = 0; t < idx.count; t += 3) {
    const i0 = idx.getX(t), i1 = idx.getX(t + 1), i2 = idx.getX(t + 2);
    a.fromBufferAttribute(pos, i0).applyMatrix4(toLocal); b.fromBufferAttribute(pos, i1).applyMatrix4(toLocal); c.fromBufferAttribute(pos, i2).applyMatrix4(toLocal);
    const cx = (a.x + b.x + c.x) / 3, cy = (a.y + b.y + c.y) / 3, cz = (a.z + b.z + c.z) / 3 - zOff;
    const inLeaf = cx > x0 && cx < x1 && cz > GATE.z - 0.16 && cz < GATE.z + 0.16 && cy > 0.04 && cy < 2.62
      && Math.min(a.y, b.y, c.y) > -0.02;
    (inLeaf ? (cx < mid ? L : R) : keep).push(i0, i1, i2);
  }
  if (!L.length && !R.length) return null;
  g.setIndex(keep);
  const leaf = (list, name) => {
    const lg = new THREE.BufferGeometry();
    for (const [k, v] of Object.entries(g.attributes)) lg.setAttribute(k, v);
    lg.setIndex(list);
    lg.computeBoundingSphere();
    const m = new THREE.Mesh(lg, mesh.material);
    m.name = name;
    m.matrixAutoUpdate = true;
    mesh.parent.add(m);
    m.position.copy(mesh.position); m.quaternion.copy(mesh.quaternion); m.scale.copy(mesh.scale);
    m.userData.base = m.position.clone();
    return m;
  };
  return { left: leaf(L, 'Mansion_GateLeaf_L'), right: leaf(R, 'Mansion_GateLeaf_R'), tris: (L.length + R.length) / 3 };
}

// leaves at t (0 shut, 1 open): each runs outward along x into its wing wall
export function setLeaves(leaves, t) {
  if (!leaves) return;
  const k = Math.max(0, Math.min(1, t)), e = k * k * (3 - 2 * k);
  leaves.left.position.x = leaves.left.userData.base.x - GATE.slide * e;
  leaves.right.position.x = leaves.right.userData.base.x + GATE.slide * e;
}

// a JSON-safe copy (item defs carry functions / nodes in places)
export const plain = (o) => JSON.parse(JSON.stringify(o ?? null, (k, v) => (v && typeof v === 'object' && (v.isObject3D || v.isMaterial || v.isTexture) ? undefined : v)));

// Systems that want to cross the gate with the player register here (both pages):
//   window.__estateLink.provide(name, () => data)   collected into state.extra[name] on leaving
//   window.__estateLink.accept(name, (data) => ...)  called with it on arriving
// e.g. the invaders following the player out (positions, kinds, how far behind), the player's
// health from viewer/combat.js. estate_gate.js already sends the player, inventory, flashlight.
export function linkRegistry() {
  const R = window.__estateLink || (window.__estateLink = {});
  R.providers = R.providers || {};
  R.acceptors = R.acceptors || {};
  R.provide = R.provide || ((name, fn) => { R.providers[name] = fn; });
  R.accept = R.accept || ((name, fn) => { R.acceptors[name] = fn; });
  R.collect = R.collect || (() => Object.fromEntries(Object.entries(R.providers).map(([k, fn]) => { try { return [k, plain(fn())]; } catch { return [k, null]; } })));
  R.deliver = R.deliver || ((extra) => { for (const [k, v] of Object.entries(extra || {})) try { R.acceptors[k]?.(v); } catch (e) { console.warn('estate link accept', k, e); } });
  return R;
}

// The lawn beyond the hedge is hay meadow (the wilderness's own meadow, mown only inside the
// hedge: brief "the hedge is the climate line"): the grounds' lawn triangles outside the hedge
// (|x| > 70.75 or |z| > 62.75, house frame) split into their own mesh. Returns it (or null).
export function splitOuterLawn(mesh, material, zOff = 0) {
  const g = mesh.geometry, idx = g.index, P = g.attributes.position;
  if (!idx) return null;
  const inside = [], outside = [];
  for (let t = 0; t < idx.count; t += 3) {
    const a = idx.getX(t), b = idx.getX(t + 1), c = idx.getX(t + 2);
    const cx = (P.getX(a) + P.getX(b) + P.getX(c)) / 3, cz = (P.getZ(a) + P.getZ(b) + P.getZ(c)) / 3 - zOff;
    (Math.abs(cx) > 70.75 || Math.abs(cz) > 62.75 ? outside : inside).push(a, b, c);
  }
  if (!outside.length) return null;
  g.setIndex(inside);
  const og = new THREE.BufferGeometry();
  for (const [k, v] of Object.entries(g.attributes)) og.setAttribute(k, v);
  og.setIndex(outside);
  og.computeBoundingSphere();
  const m = new THREE.Mesh(og, material);
  m.name = 'Mansion_Outdoor_Hay';
  m.position.copy(mesh.position); m.quaternion.copy(mesh.quaternion); m.scale.copy(mesh.scale);
  mesh.parent.add(m);
  return m;
}
// the hay's look over the lawn's texture and bake: June greens toward straw, patchy at 1-6 m,
// no mowing stripes (GLSL, `c` the lit colour, `p` the house-frame ground position)
export const HAY_GLSL = /* glsl */`
  float hh(vec2 q) { return fract(sin(dot(floor(q), vec2(127.1, 311.7))) * 43758.5453); }
  float hn(vec2 q) { vec2 i = floor(q), f = fract(q); f = f * f * (3.0 - 2.0 * f);
    return mix(mix(hh(i), hh(i + vec2(1, 0)), f.x), mix(hh(i + vec2(0, 1)), hh(i + vec2(1, 1)), f.x), f.y); }
  vec3 hay(vec3 c, vec2 p) {
    float m = 0.55 * hn(p * 0.17) + 0.3 * hn(p * 0.7) + 0.15 * hn(p * 3.1);
    float l = dot(c, vec3(0.3, 0.55, 0.15));
    vec3 h = l * mix(vec3(0.95, 1.0, 0.38), vec3(1.45, 1.22, 0.5), smoothstep(0.4, 0.85, m));
    return h * (0.78 + 0.34 * hn(p * 1.9 + 7.0));
  }`;
