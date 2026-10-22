// The secret passage, walked like a player (design/house/secret_passage.md): in the library, E on
// the rolling ladder rolls it to the end of its rail and the floor folds down into a stair; down
// the shaft's four flights (the slot into the den at the middle landing), through the steel door
// into the armory, the blast door, the east tunnel, the pump room, the north tunnel's dark
// stretch, to the landing below the pool house. Then back: up to the library, and the ladder
// closes the floor. Screenshots from the player's eye at every stage (and the library before /
// after the reveal), checks at every leg: arrived, the right room (culler.here), on the floor it
// should be on, never inside a box, never a fall on the stairs, the house hidden while below
// ground in a sealed room. Usage: node viewer/tools/secret_passage.mjs [out-dir]
import fs from 'fs';
import { chromium } from 'playwright-core';
import { level } from './level.mjs';

const out = process.argv[2] || 'build/secret_passage';
fs.mkdirSync(out, { recursive: true });
const BASE = process.env.GT_BASE || 'http://localhost:8765';
const g = (x, y, z) => [x, z, -y];                 // Blender world (x, y, z) -> glTF [x, y, z]
const R = level.rooms;
const need = ['secret_stair', 'armory', 'tunnel_e', 'pump_room', 'tunnel_n'].filter((r) => !R[r]);
if (need.length) { console.log(`FAIL  the level has no ${need.join(', ')} (rebuild the house)`); process.exit(1); }

const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
p.on('pageerror', (e) => console.log('pageerror:', e.message));
let fails = 0;
const check = (label, ok, detail = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}  ${detail}`); if (!ok) fails++; };
const fmt = (v) => v.map((n) => n.toFixed(2)).join(',');
// the library: by the reading table, looking south at the bookcases, the ladder and the inlaid panel
const eye0 = g(-17.6, -13.6, 4.6 + 1.65), look0 = g(-15.1, -17.8, 4.9);
await p.goto(`${BASE}/viewer/index.html?level=mansion&invaders=0&pos=${fmt(eye0)}&look=${fmt(look0)}`);
await p.waitForFunction(() => window.__loaded, null, { timeout: 180000 });
await p.mouse.click(640, 360); await p.waitForTimeout(600);
const shot = async (name) => { await p.waitForTimeout(250); await p.screenshot({ path: `${out}/${name}.png` }); };
const state = () => p.evaluate(() => {
  const pl = window.__player;
  return { pos: pl.pos.toArray(), here: window.__culler.here?.name ?? null, inside: pl.overlapping(pl.pos).length,
           sealed: !!window.__secret?.sealed, shell: window.__secret?.shell.visible, open: window.__signals.get('secret_library') };
});
const look = (to) => p.evaluate((t) => window.__camera.lookAt(...t), to);

// walk to a point (glTF x, z), steering every frame; records the feet each frame
async function walkTo(label, x, z, { run = false, timeout = 20000, near = 0.25 } = {}) {
  await p.evaluate(([x, z, near]) => {
    window.__walk = { trace: [], done: false };
    const tick = () => {
      const pl = window.__player, c = window.__camera, w = window.__walk;
      const d = Math.hypot(x - pl.pos.x, z - pl.pos.z);
      w.trace.push([pl.pos.x, pl.pos.y, pl.pos.z, pl.grounded, pl.overlapping(pl.pos).length]);
      if (d < near) { w.done = true; return; }
      c.lookAt(x, c.position.y, z);
      w.raf = requestAnimationFrame(tick);
    };
    tick();
  }, [x, z, near]);
  if (run) await p.keyboard.down('ShiftLeft');
  await p.keyboard.down('KeyW');
  await p.waitForFunction(() => window.__walk.done, null, { timeout }).catch(() => {});
  await p.keyboard.up('KeyW');
  if (run) await p.keyboard.up('ShiftLeft');
  await p.waitForTimeout(250);
  const t = await p.evaluate(() => { cancelAnimationFrame(window.__walk.raf); return window.__walk; });
  const s = await state();
  const d = Math.hypot(x - s.pos[0], z - s.pos[2]);
  const inside = t.trace.filter((f) => f[4]).length;
  let drop = 0;                                    // the biggest one-frame fall (a stair must glide)
  for (let i = 1; i < t.trace.length; i++) drop = Math.max(drop, t.trace[i - 1][1] - t.trace[i][1]);
  return { ...s, d, inside, drop, frames: t.trace.length, label };
}
const leg = (r, { room, y, maxDrop = 0.12 }) => {
  check(`${r.label}: arrived`, r.d < 0.6, `${r.d.toFixed(2)} m short, ${r.frames} frames`);
  if (room) check(`${r.label}: in ${room}`, r.here === room, `here=${r.here}`);
  if (y !== undefined) check(`${r.label}: on the floor at ${y.toFixed(2)}`, Math.abs(r.pos[1] - y) < 0.08, `feet ${r.pos[1].toFixed(2)}`);
  check(`${r.label}: never inside a box`, r.inside === 0, `${r.inside} frames inside`);
  check(`${r.label}: no falls`, r.drop < maxDrop, `worst one-frame drop ${r.drop.toFixed(3)} m`);
};
const press = async (label) => {
  const f = await p.evaluate(() => {
    const it = window.__interact, c = window.__camera;
    const f = it.nearest(c.position, c.getWorldDirection(new c.position.constructor()));
    return f ? { prompt: it.prompt(f), type: f.def.type } : null;
  });
  check(`${label}: E is on offer`, !!f, f ? `"${f.prompt}" (${f.type})` : 'nothing in focus');
  await p.keyboard.press('KeyE');
  return f;
};

const SR = 8.8 / 48, L1 = 4.6 - 13 * SR, L2 = 4.6 - 25 * SR, L3 = 4.6 - 37 * SR;
await shot('01_library_before');
let s = await state();
check('library: shut', s.open !== true && s.here === 'library', `here=${s.here} open=${s.open}`);

// the ladder: walk up to it (it rests at local x -3.7 on the south wall) and push it
let r = await walkTo('to the ladder', -20.6, 17.9);
await look(g(-20.7, -19.6, 4.6 + 1.2));
await press('the ladder');
await p.waitForFunction(() => window.__signals.get('secret_library') === true, null, { timeout: 3000 }).catch(() => {});
await p.waitForFunction(() => [...window.__secret.groups.values()].every((gr) => gr.items.every((i) => i.t === 1)), null, { timeout: 15000 }).catch(() => {});
s = await state();
check('the floor has folded into a stair', s.open === true, `signal ${s.open}`);
await p.evaluate(([e, l]) => { window.__player.pos.set(e[0], e[1] - 1.65, e[2]); window.__player.syncCamera(); window.__camera.lookAt(...l); }, [eye0, look0]);
await shot('02_library_after');
// a look down the opening from its top
await walkTo('to the top step', -15.125, 15.0);
await look(g(-15.125, -19.0, 2.5));
await shot('03_down_the_stair');

// F1 down (south) to L1
r = await walkTo('F1 down the folding floor', -15.125, 19.25, { near: 0.2 });
leg(r, { room: 'secret_stair', y: L1 });
await look(g(-13.7, -19.0, L1 + 1.1));
await shot('04_landing_1_button');
// F2: lane E, north down to L2 (the slot)
await walkTo('across L1', -14.12, 19.3, { near: 0.2 });
r = await walkTo('F2 down to the slot', -14.12, 15.2, { near: 0.2 });
leg(r, { room: 'secret_stair', y: L2 });
await walkTo('to the slot', -15.3, 15.15, { near: 0.2 });
await look(g(-21.0, -14.6, 1.2));
await shot('05_slot_into_the_den');
// F3: lane W, south down to L3
r = await walkTo('F3 down', -15.125, 19.3, { near: 0.2 });
leg(r, { room: 'secret_stair', y: L3 });
await walkTo('across L3', -14.12, 19.3, { near: 0.2 });
// F4: lane E, north down to the bottom
r = await walkTo('F4 down to the bottom', -14.12, 15.2, { near: 0.2 });
leg(r, { room: 'secret_stair', y: -4.2 });
await walkTo('to the door', -14.85, 15.0, { near: 0.2 });
await look(g(-14.85, -13.0, -4.2 + 1.5));
await press('the steel door');
await p.waitForTimeout(1200);
r = await walkTo('into the armory', -14.85, 12.6);
leg(r, { room: 'armory', y: -4.2 });
s = await state();
check('armory: sealed (the house is not drawn)', s.sealed && s.shell === false, `sealed=${s.sealed} shell=${s.shell}`);
await look(g(-13.75, 0.0, -4.2 + 1.4));
await shot('06_armory');
// the safe wall
await walkTo('to the safe wall', -15.6, 7.5);
await look(g(-17.0, -7.51, -4.2 + 1.3));
await press('the safe wheel');
await p.waitForTimeout(4200);
await look(g(-17.2, -7.51, -4.2 + 1.4));
await shot('07_safe_wall_open');
// the blast door (east wall, its north end)
await walkTo('to the blast door', -11.3, 1.0);          // (out of its leaf's sweep: hinge at y -3.4)
await look(g(-9.5, -2.4, -4.2 + 1.3));
await press('the blast door');
await p.waitForTimeout(3800);
r = await walkTo('into the tunnel', -8.0, 2.4);
leg(r, { room: 'tunnel_e', y: -4.2 });
await look(g(38.0, -2.4, -4.2 + 1.5));
await shot('08_tunnel_east');
r = await walkTo('under the courtyard', 0.0, 2.4, { run: true });
leg(r, { room: 'tunnel_e', y: -4.2 });
await shot('09_under_the_courtyard');
r = await walkTo('to the pump room', 40.0, 2.4, { run: true, timeout: 30000 });
leg(r, { room: 'pump_room', y: -4.2 });
await look(g(43.5, -4.0, -4.2 + 1.0));
await shot('10_pump_room');
r = await walkTo('into the north tunnel', 40.0, -4.0);
leg(r, { room: 'tunnel_n', y: -4.2 });
await look(g(40.0, 34.0, -4.2 + 1.5));
await shot('11_tunnel_north');
r = await walkTo('the dark stretch', 40.0, -18.0, { run: true });
leg(r, { room: 'tunnel_n', y: -4.2 });
await shot('12_dark_stretch');
r = await walkTo('the landing', 40.0, -33.0, { run: true });
leg(r, { room: 'tunnel_n', y: -4.2 });
s = await state();
check('landing: sealed', s.sealed, `sealed=${s.sealed}`);
await look(g(40.0, 36.0, -4.2 + 2.0));
await shot('13_landing');

// back: to the shaft and up to the library
await walkTo('back to the pump room', 40.0, 2.4, { run: true });
await walkTo('back along the tunnel', -9.0, 2.4, { run: true, timeout: 30000 });
await walkTo('through the armory', -14.85, 13.2);
r = await walkTo('back into the shaft', -14.85, 15.3, { near: 0.2 });
check('back in the shaft: not sealed, the house drawn', !r.sealed && r.shell !== false, `here=${r.here} sealed=${r.sealed}`);
await walkTo('to F4', -14.12, 15.5, { near: 0.2 });
r = await walkTo('F4 up', -14.12, 19.3, { near: 0.2 });
leg(r, { y: L3 });
await walkTo('across L3', -15.125, 19.3, { near: 0.2 });
r = await walkTo('F3 up', -15.125, 15.2, { near: 0.2 });
leg(r, { y: L2 });
await walkTo('across L2', -14.12, 15.2, { near: 0.2 });
r = await walkTo('F2 up', -14.12, 19.3, { near: 0.2 });
leg(r, { y: L1 });
await walkTo('across L1', -15.125, 19.3, { near: 0.2 });
r = await walkTo('F1 up into the library', -15.125, 14.6, { near: 0.2 });
leg(r, { room: 'library', y: 4.6 });
// close it again with the ladder (now at the end of its rail, x 0.85 local = world -16.15)
await walkTo('to the ladder', -16.15, 17.9);
await look(g(-16.15, -19.6, 4.6 + 1.2));
await press('the ladder (back)');
await p.waitForFunction(() => [...window.__secret.groups.values()].every((gr) => gr.items.every((i) => i.t === 0)), null, { timeout: 15000 }).catch(() => {});
s = await state();
check('the floor is shut again', s.open === false, `signal ${s.open}`);
await p.evaluate(([e, l]) => { window.__player.pos.set(e[0], e[1] - 1.65, e[2]); window.__player.syncCamera(); window.__camera.lookAt(...l); }, [eye0, look0]);
await shot('14_library_shut_again');
await b.close();
console.log(fails ? `${fails} failed` : 'all passed');
process.exit(fails ? 1 : 0);
