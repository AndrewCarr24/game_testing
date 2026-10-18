// Fixed inputs of the optimisation loop: the benchmark route (bench.mjs) and the camera
// views of the visual check (shots.mjs). Change them only on purpose: results are only
// comparable between runs that used the same route and views.
import { level, room, props, fromProp } from './level.mjs';

const EYE = 1.65;
const UP = 4.6;          // upper floor level (plan.py LEVEL_Z[1])
export const RUN = 4.4;  // m/s: the run speed when the baseline was taken (player.js now 5.2); keep it fixed so runs stay comparable

// Waypoints in floor-plan metres (plan.py: x east, y north) + floor level; `spin` = seconds
// spent turning a full circle on the spot. The run starts at the spawn, crosses the ground
// floor (entry, galleries, great room, dining, kitchen), climbs the stair and ends upstairs
// in the office: the busiest views (entry, great room) and the most room changes.
const PLAN = [
  [0, -17, 0, 2],          // entry, look around
  [4.75, -13, 0], [4.75, -8.75, 0],                    // -> south gallery
  [-11.75, -8.75, 0], [-11.75, 3.5, 0],                // west gallery
  [-17, 4.2, 0, 2],        // great room, look around
  [-19, 8.5, 0], [-20, 12.2, 0],                       // -> dining
  [-13, 12.3, 0], [-10.5, 14, 0], [-7, 13.2, 0],       // -> kitchen
  [-3.5, 12.3, 0], [0, 8.75, 0],                       // -> north gallery
  [11.75, 8.75, 0], [11.75, -8.75, 0], [4.75, -8.75, 0],
  [4.75, -13, 0], [3, -17.5, 0], [-6, -17.5, 0], [-7, -14, 0], [-7, -11.85, 0],   // back to the stair
  [-6, -11.85, 0], [1.5, -11.85, UP], [3, -11.85, UP],  // up the stair
  [3, -8.75, UP], [-11.75, -8.75, UP], [-11.75, 8.75, UP], // upper galleries (over entry / great room)
  [6.75, 8.75, UP], [6.75, 10.5, UP], [6.75, 13.5, UP],
  [6.5, 14.5, UP, 2],      // office, look around
];

// glTF metres: (x, y, z) = (plan x, floor + eye, -plan y)
export const ROUTE = PLAN.map(([x, y, f, spin = 0]) => ({ p: [x, f + EYE, -y], spin }));

// ---------------------------------------------------------------- visual check views
// One wide view per room (from near a corner, looking across it, as house_tour.mjs)
// and close-ups of hero props, where lost detail (bevels, texture resolution) shows.
const CORNERS = {
  entry: [0.85, 0.85], great_room: [0.8, 0.9], den: [0.85, 0.15], dining: [0.85, 0.2], kitchen: [0.15, 0.8],
  scullery: [0.5, 0.85], wine_room: [0.15, 0.8], mudroom: [0.2, 0.8], garage: [0.5, 0.1], courtyard: [0.5, 0.92],
  powder: [0.5, 0.85], cloak: [0.5, 0.85], gallery_s: [0.05, 0.5], library: [0.9, 0.2], primary_bedroom: [0.85, 0.2],
  primary_bath: [0.15, 0.2], office: [0.15, 0.8], gym: [0.15, 0.8], guest_room: [0.15, 0.8], ugallery_n: [0.05, 0.5],
};
// [asset, room, optional camera offset from the prop's centre in its Blender frame]
// (first placement of that asset in that room)
const HEROES = [
  ['lounge_chair', 'office'], ['desk', 'office'], ['door', 'ugallery_n', [0.6, 2.4, 0.4]], ['bed', 'primary_bedroom'],
  ['car_ev', 'garage'], ['kitchen_island', 'kitchen'], ['bath_tub', 'primary_bath'], ['entry_chandelier', 'entry'],
  ['living_fireplace', 'great_room'], ['library_bookcase_a', 'library'], ['dining_table', 'dining'],
  ['courtyard_olive_tree', 'courtyard'],
];

export function views() {
  const out = [];
  for (const [name, [fx, fz]] of Object.entries(CORNERS)) {
    const r = room(name);
    const x = r.x0 + (r.x1 - r.x0) * fx, z = r.z0 + (r.z1 - r.z0) * fz;
    out.push({ name, pos: [x, r.y + EYE, z], look: [r.cx, r.y + 1.3, r.cz] });
  }
  for (const [asset, roomName, offset] of HEROES) {
    const p = props(asset).find((q) => q.room === roomName);
    if (!p) continue;
    const { min, max } = level.assets[asset].aabb;          // glTF, in the asset's own frame
    const size = Math.max(max[0] - min[0], max[1] - min[1], max[2] - min[2]);
    // centre in the asset's Blender frame (x, y = -z, z = y)
    const c = [(min[0] + max[0]) / 2, -(min[2] + max[2]) / 2, (min[1] + max[1]) / 2];
    const look = fromProp(p, c);
    const floor = room(roomName).y;
    let pos;
    if (offset) {
      pos = fromProp(p, [c[0] + offset[0], c[1] + offset[1], c[2] + offset[2]]);
    } else if (look[1] - floor > 2.4) {
      // hung from the ceiling: look up at it from eye height, in front of it
      pos = fromProp(p, [c[0] + 1.2, c[1] - 3.2, 0]); pos[1] = floor + EYE;
    } else {
      // front-right, three-quarter view, a bit above
      const d = Math.min(3.2, Math.max(1.1, size * 0.9));
      pos = fromProp(p, [c[0] + d * 0.55, c[1] - d, c[2] + Math.min(1.0, 0.25 + size * 0.3)]);
    }
    // stay inside the room (big props would otherwise put the camera behind a wall)
    const r = room(roomName);
    pos[0] = Math.min(r.x1 - 0.5, Math.max(r.x0 + 0.5, pos[0]));
    pos[2] = Math.min(r.z1 - 0.5, Math.max(r.z0 + 0.5, pos[2]));
    out.push({ name: `detail_${asset}`, pos, look });
  }
  return out;
}
