// Close-ups of placed props in the real engine (first placement of each asset): the camera
// stands in front of the prop (its local -Y = front) at a distance from its size, eye-ish height.
// Usage: node viewer/tools/prop_closeups.mjs <out-dir> asset [asset ...]   (from the project root)
// It loads the exported assets/models/<asset>.gltf, so re-export an asset (build_asset.py) to see changes.
import { chromium } from 'playwright-core';
import fs from 'fs';
import { level, props, fromProp } from './level.mjs';
const [out, ...names] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
// machine-wide browser slots (shared with review_room.mjs): at most 3 browsers at once
fs.mkdirSync('build/locks', { recursive: true });
let slot = null;
while (slot === null) {
  for (let i = 0; i < 3 && slot === null; i++) { try { fs.mkdirSync(`build/locks/browser_${i}`); slot = i; } catch {} }
  if (slot === null) await new Promise((ok) => setTimeout(ok, 3000));
}
const release = () => { try { fs.rmdirSync(`build/locks/browser_${slot}`); } catch {} };
process.on('exit', release);
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 900, height: 600 } });
await p.goto((process.env.GT_BASE || 'http://localhost:8765') + '/viewer/index.html?level=mansion&grimble=0' + (process.env.QS || ''));
await p.waitForFunction(() => window.__loaded, null, { timeout: 120000 });
await p.evaluate(() => { const c = window.__culler; c.update = () => false; for (const r of c.rooms) for (const o of r.objects) o.visible = true; document.querySelectorAll('#hud,#stats,#hint').forEach((e) => (e.style.display = 'none')); });
for (const n of names) {
  const pr = props(n)[+(process.env.PROP_I || 0)];
  if (!pr) { console.log('no placement', n); continue; }
  const bb = level.assets[n].aabb, sz = Math.max(bb.max[0] - bb.min[0], bb.max[1] - bb.min[1], bb.max[2] - bb.min[2]);
  const cy = (bb.min[1] + bb.max[1]) / 2;
  const d = Math.max(1.2, sz * 1.15);
  // from the prop toward its room's centre (props against walls face into the room, but not
  // always along their local -Y), offset sideways for the second view
  const rm = level.rooms[pr.room], [x0, z0, x1, z1] = rm.rect;
  const toC = [(x0 + x1) / 2 - pr.position[0], (z0 + z1) / 2 - pr.position[2]];
  const L = Math.hypot(...toC) || 1;
  const dir = [toC[0] / L, toC[1] / L], side = [-dir[1], dir[0]];
  for (const [k, s] of [['a', 0.35], ['b', -0.6]]) {
    const dd = Math.min(d, Math.max(0.8, L - 0.3));
    const eye = [pr.position[0] + dir[0] * dd + side[0] * s * dd, rm.floor + Math.max(cy + 0.4, 1.2), pr.position[2] + dir[1] * dd + side[1] * s * dd];
    const at = [pr.position[0], pr.position[1] + cy, pr.position[2]];
    await p.evaluate(([e, a]) => { const c = window.__camera; window.__bench = { frameStart() {}, drive() { c.position.set(...e); c.lookAt(...a); }, renderStart() {}, frameEnd() {} }; }, [eye, at]);
    await p.waitForTimeout(450);
    await p.screenshot({ path: `${out}/${n}_${k}.png` });
  }
}
await b.close();
