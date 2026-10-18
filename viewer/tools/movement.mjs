// Character controller checks. Positions come from the level file. Usage: node movement.mjs [out-dir]
import { chromium } from 'playwright-core';
import { prop, props, fromProp, room, url } from './level.mjs';
const out = process.argv[2] || '.';
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
let fails = 0;
const check = (label, ok, detail) => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}  ${detail}`); if (!ok) fails++; };

async function session(pos, look) {
  const p = await b.newPage({ viewport: { width: 1000, height: 650 } });
  p.on('pageerror', (e) => console.log('pageerror:', e.message));
  await p.goto(url(pos, look));
  await p.waitForFunction(() => window.__loaded, null, { timeout: 60000 });
  await p.mouse.click(500, 325);
  await p.waitForTimeout(500);
  const state = () => p.evaluate(() => {
    const pl = window.__player;
    return { x: pl.pos.x, y: pl.pos.y, z: pl.pos.z, eye: pl.eye, grounded: pl.grounded, crouching: pl.crouching };
  });
  const hold = async (keys, ms) => {
    for (const k of keys) await p.keyboard.down(k);
    await p.waitForTimeout(ms);
    for (const k of keys) await p.keyboard.up(k);
  };
  return { p, state, hold };
}
const f2 = (v) => v.toFixed(2);

{ // the upper north gallery: 26 m of clear floor, running east
  const g = room('ugallery_n');
  const { p, state, hold } = await session([g.x0 + 2, g.y + 1.65, g.cz], [g.x1, g.y + 1.65, g.cz]);
  const s0 = await state();
  check('spawn on the floor', s0.grounded && Math.abs(s0.y - g.y) < 0.01, `feet=${f2(s0.y)} (floor ${g.y})`);
  await hold(['KeyW'], 500); const s1 = await state();
  const walk = (s1.x - s0.x) / 0.5;
  await hold(['ShiftLeft', 'KeyW'], 500); const s2 = await state();
  const run = (s2.x - s1.x) / 0.5;
  check('sprint is faster than walk', run > walk * 1.5, `walk≈${f2(walk)} m/s, run≈${f2(run)} m/s`);
  await p.waitForTimeout(400);
  await p.keyboard.down('Space'); let apex = 0;
  for (let i = 0; i < 25; i++) { await p.waitForTimeout(20); apex = Math.max(apex, (await state()).y - g.y); }
  await p.keyboard.up('Space'); await p.waitForTimeout(700);
  const s3 = await state();
  check('jump height ≈ 1 m and lands again', apex > 0.85 && apex < 1.2 && s3.grounded && s3.y - g.y < 0.02, `apex=${f2(apex)}`);
  await p.keyboard.down('KeyC'); await p.waitForTimeout(400);
  const s4 = await state(); await p.keyboard.up('KeyC'); await p.waitForTimeout(400);
  const s5 = await state();
  check('crouch lowers the eye, releasing stands up', s4.crouching && s4.eye < 1.1 && !s5.crouching && s5.eye > 1.5, `eye ${f2(s4.eye)} -> ${f2(s5.eye)}`);
  await p.close();
}
{ // visitor side of the desk, facing it
  const desk = prop('desk');
  const { p, state, hold } = await session(fromProp(desk, [0, -1.4, 1.65]), fromProp(desk, [0, 0, 1.0]));
  const top = desk.position[1] + 0.74;
  await hold(['KeyW'], 1200); let s = await state();
  check('walking into the desk is blocked', s.y < desk.position[1] + 0.01, `feet=${f2(s.y)}`);
  await p.keyboard.down('KeyW'); await hold(['Space'], 120); await p.waitForTimeout(700); await p.keyboard.up('KeyW');
  await p.waitForTimeout(400); s = await state();
  check('jump + forward lands on the desktop', Math.abs(s.y - top) < 0.02 && s.grounded, `feet=${f2(s.y)} (desktop ${f2(top)})`);
  await p.close();
}
{ // drop onto the middle of a lounge chair's seat from 1 m up
  const chair = props('lounge_chair')[1];
  const seat = chair.position[1] + 0.46;
  const { p, state } = await session(fromProp(chair, [0, -0.2, 2.65]), fromProp(chair, [0, -3, 1.0]));
  await p.waitForTimeout(900); const s = await state();
  check('lands on the lounge chair seat, not the top of its bounding box', s.grounded && Math.abs(s.y - seat) < 0.03, `feet=${f2(s.y)} (seat ${f2(seat)})`);
  await p.close();
}
await b.close();
console.log(fails ? `${fails} failed` : 'all passed');
process.exit(fails ? 1 : 0);
