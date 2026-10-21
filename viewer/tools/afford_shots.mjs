// Affordance shots: from the player's eye in several rooms, the crosshair ON a usable thing and
// turned AWAY from it (HUD visible: crosshair, prompt, glint/highlight), for before/after
// comparisons of "what is usable". Usage: node afford_shots.mjs <out-dir> [extra query string]
//   GT_BASE=http://localhost:<port> node viewer/tools/afford_shots.mjs build/afford/after
import fs from 'fs';
import { chromium } from 'playwright-core';
import { level, url } from './level.mjs';

const out = process.argv[2] || 'build/afford';
const qs = process.argv[3] || '';
fs.mkdirSync(out, { recursive: true });

// one browser slot of build/locks/browser_0..2 (shared by every agent on this machine)
let slot = null;
for (let tries = 0; slot === null; tries++) {
  for (let i = 0; i < 3 && slot === null; i++) { try { fs.mkdirSync(`build/locks/browser_${i}`); slot = i; } catch {} }
  if (slot === null) { if (tries > 600) throw new Error('no browser slot'); await new Promise((r) => setTimeout(r, 2000)); }
}
const release = () => { try { fs.rmdirSync(`build/locks/browser_${slot}`); } catch {} };
process.on('exit', release);

// [label, prop index or asset, height of the thing above its placement, distance, side angle]
const pick = (asset, room, k = 0) => level.props.filter((p) => p.asset === asset && (!room || p.room === room))[k];
const VIEWS = [
  ['den_vase', pick('vase', 'den', 1), 0.15, 1.15],
  ['kitchen_island', pick('ix_tablet_dock', 'kitchen'), 0.05, 1.3],
  ['entry_switches', pick('ix_switch', 'entry'), 0.0, 1.0],
  ['mudroom_flashlight', pick('ix_flashlight', 'mudroom'), 0.03, 1.1],
  ['garage_breaker', pick('ix_breaker_panel', 'garage'), 0.0, 1.1],
  ['library_book', pick('ix_book', 'library'), 0.1, 1.1],
  ['bedroom_nightstand', pick('nightstand', 'primary_bedroom'), 0.45, 1.1],
  ['locked_door', level.props.find((p) => p.lock === 'keycard'), 1.1, 1.6],
  ['great_room_fire_switch', pick('ix_switch_fire', 'great_room'), 0.0, 1.0],
  ['office_book_vase', pick('ix_book_b', 'office'), 0.08, 1.2],
];

const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
try {
  const p = await b.newPage({ viewport: { width: 1280, height: 800 } });
  p.on('pageerror', (e) => console.log('pageerror:', e.message));
  const first = VIEWS[0][1];
  await p.goto(url([first.position[0], first.position[1] + 1.65, first.position[2] + 2], first.position) + '&grimble=0' + qs);
  await p.waitForFunction(() => window.__loaded, null, { timeout: 90000 });
  await p.mouse.click(640, 400); await p.waitForTimeout(600);
  const info = {};
  for (const [label, pr, h, dist] of VIEWS) {
    const r = level.rooms[pr.room];
    const [x, y, z] = pr.position;
    const target = [x, y + h, z];
    // stand `dist` m from the thing, toward the room's centre (so the view looks back at it)
    let dx = (r.rect[0] + r.rect[2]) / 2 - x, dz = (r.rect[1] + r.rect[3]) / 2 - z;
    const n = Math.hypot(dx, dz) || 1; dx /= n; dz /= n;
    const eye = [x + dx * dist, r.floor + 1.65, z + dz * dist];
    const away = [eye[0] + (dx * Math.cos(1.3) - dz * Math.sin(1.3)) * 3, eye[1] - 0.3, eye[2] + (dz * Math.cos(1.3) + dx * Math.sin(1.3)) * 3];
    for (const [tag, look] of [['on', target], ['off', away]]) {
      await p.evaluate(([pos, look]) => {
        window.__player.pos.set(pos[0], pos[1] - 1.65, pos[2]); window.__player.vel.set(0, 0, 0);
        window.__player.syncCamera(); window.__camera.lookAt(...look);
      }, [eye, look]);
      await p.waitForTimeout(tag === 'on' ? 1400 : 900);
      await p.evaluate(([pos, look]) => { window.__player.syncCamera(); window.__camera.lookAt(...look); }, [eye, look]);
      await p.waitForTimeout(150);
      await p.screenshot({ path: `${out}/${label}_${tag}.png` });
      info[`${label}_${tag}`] = await p.evaluate(() => ({
        hint: document.getElementById('hint')?.textContent,
        sub: document.getElementById('hint-sub')?.textContent ?? null,
        cross: document.getElementById('cross')?.className ?? null,
      }));
      console.log(label, tag, JSON.stringify(info[`${label}_${tag}`]));
    }
  }
  // the inventory screen with one of every kind of item the level has (their real definitions)
  const shot = async (label) => {
    await p.screenshot({ path: `${out}/${label}.png` });
    info[label] = await p.evaluate(() => ({ hint: document.getElementById('hint')?.textContent, cross: document.getElementById('cross')?.className ?? null }));
    console.log(label, JSON.stringify(info[label]));
  };
  await p.evaluate(() => {
    const inv = window.__inventory, seen = new Set();
    for (const it of window.__interact.items) {
      const d = it.def;
      if (d.type !== 'pickup' || seen.has(d.item)) continue;
      seen.add(d.item);
      inv.add(d.item, d.name, it.node.clone(true), d);
      if (d.item === 'vase') inv.add(d.item, d.name, it.node.clone(true), d);
    }
  });
  await p.keyboard.press('KeyI'); await p.waitForTimeout(300);
  await shot('inventory_open');
  await p.keyboard.press('KeyI'); await p.waitForTimeout(200);
  // armed keycard at the locked door; armed vase looking down a room
  const door = level.props.find((q) => q.lock === 'keycard');
  const arm = (id) => p.evaluate((id) => { window.__inventory.armed = id; window.__inventory.changed(); }, id);
  const view = async (pos, look) => {
    await p.evaluate(([pos, look]) => {
      window.__player.pos.set(pos[0], pos[1] - 1.65, pos[2]); window.__player.vel.set(0, 0, 0);
      window.__player.syncCamera(); window.__camera.lookAt(...look);
    }, [pos, look]);
    await p.waitForTimeout(1200);
  };
  const a = (door.rotationY * Math.PI) / 180;   // the door's local +y (Blender) = the gallery side
  const dz = -Math.cos(a) * 1.6, dx = -Math.sin(a) * 1.6;
  await view([door.position[0] + dx, door.position[1] + 1.65, door.position[2] + dz], [door.position[0], door.position[1] + 1.2, door.position[2]]);
  await shot('locked_door_have_key');
  await arm('keycard');
  await view([door.position[0] + dx, door.position[1] + 1.65, door.position[2] + dz], [door.position[0], door.position[1] + 1.2, door.position[2]]);
  await shot('locked_door_armed_key');
  await arm('vase');
  const gr = level.rooms.great_room;
  await view([(gr.rect[0] + gr.rect[2]) / 2, gr.floor + 1.65, (gr.rect[1] + gr.rect[3]) / 2], [gr.rect[0], gr.floor + 1.0, (gr.rect[1] + gr.rect[3]) / 2]);
  await shot('armed_vase');
  fs.writeFileSync(`${out}/info.json`, JSON.stringify(info, null, 1));
} finally {
  await b.close();
  release();
}
