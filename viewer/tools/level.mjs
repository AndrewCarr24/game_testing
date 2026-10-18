// Positions for tests, read from assets/levels/mansion.json so tests survive layout changes.
// Prop offsets are given in the prop's own frame in Blender terms (x right, y = the
// prop's forward axis flipped: assets face -Y, so +y is "behind" a prop), z up.
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const here = path.dirname(fileURLToPath(import.meta.url));
export const level = JSON.parse(fs.readFileSync(path.join(here, '../../assets/levels/mansion.json'), 'utf8'));

export const props = (asset) => level.props.filter((p) => p.asset === asset && !p.attach);
export const prop = (asset, i = 0) => props(asset)[i];

// glTF [x, y, z] for an offset [bx, by, bz] in the prop's local Blender frame
export function fromProp(p, [bx, by, bz = 0]) {
  const a = (p.rotationY * Math.PI) / 180;
  const wx = bx * Math.cos(a) - by * Math.sin(a);     // rotate about Blender Z
  const wy = bx * Math.sin(a) + by * Math.cos(a);
  return [p.position[0] + wx, p.position[1] + bz, p.position[2] - wy];
}

export function room(name) {
  const r = level.rooms[name];
  const [x0, z0, x1, z1] = r.rect;
  return { ...r, cx: (x0 + x1) / 2, cz: (z0 + z1) / 2, x0, z0, x1, z1, y: r.floor };
}

export const fmt = (v) => v.map((n) => n.toFixed(2)).join(',');
export const url = (pos, look) =>
  `http://localhost:8765/viewer/index.html?level=mansion&pos=${fmt(pos)}&look=${fmt(look)}`;
