import * as THREE from 'three';
import { HouseNav, BoxGrid, UPPER_Y } from './invaders_nav.js';

// ------------------------------------------------------------------ the shared world
// Built once for every invader: the nav, the boxes rays test against, the doors, rooms, hiding
// spots. (The Grimble's hunt builds the same per instance; 50 copies would not do.)
//   sight     walls that stop a look (not glass, not the balustrades' invisible anti-vault boxes)
//   solid     everything that stops a bullet or a body (glass included)
//   cover     furniture (props, the grounds' furniture): a crouched player ducks behind low
//             pieces, tall ones hide anyone
export function buildWorld({ level, colliders, interact, signals }) {
  const nLevel = level.colliders.length;
  const tag = level.colliders;
  const rail = (c, j) => tag[j]?.seeThrough || (Math.abs(c.max.y - c.min.y - 2.2) < 0.05 && Math.min(c.max.x - c.min.x, c.max.z - c.min.z) <= 0.12);
  const glass = (c, j) => tag[j]?.glass || (Math.abs(Math.min(c.max.x - c.min.x, c.max.z - c.min.z) - 0.12) < 0.006 && c.max.y - c.min.y > 1);
  const own = new Set([...(interact?.items ?? []).map((i) => i.collider), ...(interact?.reactors ?? []).map((r) => r.collider)].filter(Boolean));
  const shell = [], sight = [], glassBoxes = [];
  for (let j = 0; j < nLevel; j++) {
    const c = colliders[j];
    if (!c || c.isEmpty()) continue;
    if (rail(c, j)) { c.rail = true; continue; }
    if (glass(c, j)) { c.glass = true; glassBoxes.push(c); } else sight.push(c);
    shell.push(c);
  }
  // props' part boxes and the grounds' boxes (everything pushed after the level's own, minus
  // interactables' moving colliders and parked blockers)
  const doors = collectDoors(interact, signals, level);
  // (the garage door's leaf is also a static part box of its prop: it would never open for them)
  const leaves = doors.filter((d) => d.kind === 'reactor').map((d) => d.box.clone().expandByScalar(0.2));
  const rest = colliders.slice(nLevel).filter((c) => !own.has(c) && !c.isEmpty() && c.max.y > -50 && !leaves.some((l) => l.containsBox(c)));
  const floorOf = (c) => (c.min.y > UPPER_Y - 0.4 ? UPPER_Y : 0);
  const cover = rest.filter((c) => !c.seeThrough && c.kind !== 'ground' && c.max.y - floorOf(c) > 0.5);
  const nav = new HouseNav({ boxes: [...shell, ...colliders.slice(0, nLevel).filter((c) => c.rail), ...rest], level, doors });
  const world = {
    level, interact, signals, nav, doors,
    sight: new BoxGrid(sight),
    solid: new BoxGrid([...shell, ...rest.filter((c) => !c.seeThrough && c.kind !== 'ground')]),
    walls: new BoxGrid(shell),
    coverTall: new BoxGrid(cover.filter((c) => c.max.y - floorOf(c) > 1.9)),
    coverLow: new BoxGrid(cover.filter((c) => c.max.y - floorOf(c) <= 1.9)),
    // what bodies are pushed out of (walls and furniture between the knees and the head)
    body: new BoxGrid([...shell, ...colliders.slice(0, nLevel).filter((c) => c.rail), ...rest.filter((c) => c.kind !== 'ground')]),
    // (secret passage) rooms with nav false (below ground) are never swept
    rooms: Object.entries(level.rooms).filter(([, r]) => r.nav !== false).map(([name, r]) => ({ name, rect: r.rect, floor: r.floor ?? 0, height: r.height ?? 4.2, sun: r.sun })),
  };
  world.roomAt = (x, y, z) => world.rooms.find((r) => y >= r.floor - 0.6 && y < r.floor + r.height && x >= r.rect[0] && x <= r.rect[2] && z >= r.rect[1] && z <= r.rect[3]) ?? null;
  return world;
}

// door portals: interactable doors (rotate, a leaf over 2 m tall) and reactor doors (the garage's)
export function collectDoors(interact, signals, level) {
  const out = [];
  if (!interact) return out;
  // (a door prop's placement names it: asset@room; appliances with tall doors, the fridge, aren't doors)
  // (secret passage) not the doors of rooms off the nav (below ground: their leaves would stamp
  // portal cells on the ground layer over them)
  const props = (level?.props ?? []).filter((p) => /(^|_)door/.test(p.asset) && !p.attach && level?.rooms?.[p.room]?.nav !== false);
  const v = new THREE.Vector3();
  for (const it of interact.items) {
    if (it.def.type !== 'rotate' || !it.collider) continue;
    const box = interact.boxAtRest(it);
    if (box.isEmpty() || box.max.y - box.min.y < 2.0) continue;
    it.root.getWorldPosition(v);
    const p = props.find((q) => Math.hypot(q.position[0] - v.x, q.position[1] - v.y, q.position[2] - v.z) < 0.05);
    if (level && !p) continue;
    out.push({
      kind: 'item', it, box, name: p ? `${p.asset}@${p.room}${p.lock ? `[${p.lock}]` : ''}` : it.node.name,
      isOpen: () => it.target === 1 && it.t === 1,
      opening: () => it.target === 1,
      locked: () => !!it.locked,
      open: () => { if (!it.locked && it.target !== 1) { it.target = 1; return true; } return false; },
      close: () => { if (it.target !== 0) it.target = 0; },
    });
  }
  for (const r of interact.reactors ?? []) {
    if (!r.collider || r.collider.isEmpty() || !r.signal) continue;
    const box = r.collider.clone();
    if (box.max.y - box.min.y < 2.0) continue;
    if (box.max.y < -0.5) continue;      // (secret passage) below ground: off the nav
    out.push({
      kind: 'reactor', r, box, name: r.node.name,
      isOpen: () => r.t === 1 && r.target === 1,
      opening: () => r.target === 1,
      locked: () => false,
      open: () => { if (!signals.get(r.signal)) { signals.set(r.signal, true); return true; } return false; },
      close: () => signals.set(r.signal, false),
    });
  }
  return out;
}
