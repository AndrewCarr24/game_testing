// Hiding spots (interact type `hide`, viewer/hiding.js): a fixture wardrobe built in the page (in the
// upper north gallery) checks the mechanics: the prompt, E in, doors swing and rest ajar, movement
// locked, the view clamped, player.hidden, E out to the exit, noise, knockdown pulls the player
// out. Then every hiding spot in the level: walk up, E in, a screenshot from inside
// (<out>/hide_<n>_<name>.png), E out, and the player must be able to walk away.
// Usage: node hide.mjs [out-dir] [name-filter]
import fs from 'fs';
import { chromium } from 'playwright-core';
import { room, url } from './level.mjs';
const out = process.argv[2] || 'build/hide';
const only = process.argv[3] || '';
fs.mkdirSync(out, { recursive: true });

// one of the shared browser slots (build/locks/browser_0..2)
fs.mkdirSync('build/locks', { recursive: true });
let slot = null;
while (slot === null) {
  for (let i = 0; i < 3 && slot === null; i++) { try { fs.mkdirSync(`build/locks/browser_${i}`); slot = i; } catch {} }
  if (slot === null) await new Promise((ok) => setTimeout(ok, 3000));
}
const release = () => { try { fs.rmdirSync(`build/locks/browser_${slot}`); } catch {} };
process.on('exit', release);
process.on('SIGINT', () => process.exit(1));

const g = room('ugallery_n');
const Z = g.z1 - 1.0, FIX_Z = g.z1 - 2.6;
const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
const p = await b.newPage({ viewport: { width: 1100, height: 700 } });
p.on('pageerror', (e) => console.log('pageerror:', e.message));
p.on('console', (m) => { if (m.type() === 'error') console.log('console:', m.text()); });
let fails = 0;
const check = (label, ok, detail = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}  ${detail}`); if (!ok) fails++; };
const X = 2;
try {
  await p.goto(url([X, g.y + 1.65, Z], [X, g.y + 1.2, FIX_Z]) + '&grimble=0');
  await p.waitForFunction(() => window.__loaded, null, { timeout: 120000 });
  await p.mouse.click(550, 350); await p.waitForTimeout(400);
  const press = async (k, wait = 350) => { await p.keyboard.press(k); await p.waitForTimeout(wait); };
  const hint = () => p.textContent('#hint');
  // (the climb takes ~1 s of game time; slow frames stretch it: wait for the state, not a time)
  const settled = (inside) => p.waitForFunction((v) => (v ? window.__player.hidden : !window.__player.hideSpot), inside, { timeout: 15000 })
    .then(() => p.waitForTimeout(250), () => {});
  const st = () => p.evaluate(() => {
    const pl = window.__player, c = window.__camera;
    return { hidden: pl.hidden, spot: pl.hideSpot?.name ?? null, feet: pl.pos.toArray(), eye: c.position.toArray(),
             yaw: Math.atan2(-c.getWorldDirection(c.position.clone()).x, -c.getWorldDirection(c.position.clone()).z) };
  });

  // ---------------------------------------------------------------- the fixture: a wardrobe
  await p.evaluate(async ([x, y, fz]) => {
    const THREE = await import('three');
    const { scene } = window.__three, it = window.__interact;
    const mat = new THREE.MeshStandardMaterial({ color: 0x6b4a33 });
    const box = (w, h, d, px, py, pz) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat); m.position.set(px, py, pz); return m; };
    const root = new THREE.Group(); root.name = 'TestWardrobe';
    // carcass (front = +z, like a placed asset with rotation 0): back, sides, top
    root.add(box(1.2, 2.2, 0.03, 0, 1.1, -0.3), box(0.03, 2.2, 0.6, -0.6, 1.1, 0), box(0.03, 2.2, 0.6, 0.6, 1.1, 0), box(1.2, 0.03, 0.6, 0, 2.2, 0));
    const doors = [];
    for (const [s, hx] of [['L', -0.585], ['R', 0.585]]) {
      const piv = new THREE.Object3D(); piv.name = `TestWardrobe_Door${s}`; piv.position.set(hx, 0, 0.3);
      piv.add(box(0.58, 2.1, 0.02, -Math.sign(hx) * 0.29, 1.08, 0));
      root.add(piv); doors.push(piv);
    }
    const eye = new THREE.Object3D(); eye.name = 'TestWardrobe_HideEye'; eye.position.set(0, 1.6, 0.05);
    const exit = new THREE.Object3D(); exit.name = 'TestWardrobe_HideExit'; exit.position.set(0, 0, 0.85);
    const spot = new THREE.Object3D(); spot.name = 'TestWardrobe_Hide';
    spot.userData.interact = { type: 'hide', prompt: 'Hide in the test wardrobe', promptActive: 'Leave the test wardrobe',
      eye: eye.name, exit: exit.name, cover: 'closed', range: 1.4,
      doors: [{ node: 'TestWardrobe_DoorL', axis: [0, 1, 0], angle: -100, ajar: -7 }, { node: 'TestWardrobe_DoorR', axis: [0, 1, 0], angle: 100, ajar: 3 }] };
    root.add(eye, exit, spot);
    root.position.set(x, y, fz);
    scene.add(root); root.updateMatrixWorld(true);
    // the carcass and closed doors are solid, like a prop's part colliders
    for (const m of root.children) if (m.isMesh) window.__colliders.push(new THREE.Box3().setFromObject(m));
    for (const d of doors) window.__colliders.push(new THREE.Box3().setFromObject(d));
    window.__testNoise = [];
    window.__noise.on((n) => window.__testNoise.push(n.source));
    it.register(root);
  }, [X, g.y, FIX_Z]);
  await p.waitForTimeout(300);
  check('prompt at the wardrobe', (await hint()).includes('E · Hide in the test wardrobe'), await hint());
  const before = await st();
  await press('KeyE', 300);
  const mid = await p.evaluate(() => window.__three.scene.getObjectByName('TestWardrobe_DoorR').rotation.y);
  check('doors swing open while climbing in', mid > 0.5, `R door ${mid.toFixed(2)} rad`);
  await settled(true);
  let s = await st();
  check('hidden once inside', s.hidden && s.spot === 'TestWardrobe', JSON.stringify(s.spot));
  check('camera at the eye', Math.hypot(s.eye[0] - X, s.eye[1] - (g.y + 1.6), s.eye[2] - (FIX_Z + 0.05)) < 0.03, s.eye.map((v) => v.toFixed(2)).join(','));
  const ajar = await p.evaluate(() => window.__three.scene.getObjectByName('TestWardrobe_DoorR').rotation.y);
  check('doors rest ajar (a crack to peek through)', ajar > 0.02 && ajar < 0.1, `${ajar.toFixed(3)} rad`);
  check('hint says how to leave', (await hint()).includes('E · Leave the test wardrobe'), await hint());
  await p.screenshot({ path: `${out}/fixture_inside.png` });
  // movement locked
  await p.keyboard.down('KeyW'); await p.waitForTimeout(600); await p.keyboard.up('KeyW');
  const s2 = await st();
  check('WASD does nothing inside', Math.hypot(s2.eye[0] - s.eye[0], s2.eye[2] - s.eye[2]) < 0.02);
  // the view is clamped: turn it 120 degrees, a frame later it's back within the limit
  await p.evaluate(() => { window.__camera.rotateY(2.1); });
  await p.waitForTimeout(100);
  const clamp = await p.evaluate(() => {
    const c = window.__camera, f = c.getWorldDirection(c.position.clone());
    return Math.atan2(-f.x, -f.z);    // spot faces +z (out of the wardrobe) = yaw pi
  });
  const off = Math.abs(Math.atan2(Math.sin(clamp - Math.PI), Math.cos(clamp - Math.PI)));
  check('view turns only a little from the spot facing', off < 0.6, `${(off * 180 / Math.PI).toFixed(1)} deg off`);
  // E out
  await press('KeyE', 100); await settled(false);
  s = await st();
  check('out: not hidden, at the exit', !s.hidden && !s.spot && Math.hypot(s.feet[0] - X, s.feet[2] - (FIX_Z + 0.85)) < 0.05, s.feet.map((v) => v.toFixed(2)).join(','));
  const shut = await p.evaluate(() => window.__three.scene.getObjectByName('TestWardrobe_DoorR').rotation.y);
  check('doors shut after leaving', Math.abs(shut) < 1e-3, shut.toFixed(4));
  await p.keyboard.down('KeyW'); await p.waitForTimeout(500); await p.keyboard.up('KeyW');
  const s3 = await st();
  check('can walk again', Math.hypot(s3.feet[0] - s.feet[0], s3.feet[2] - s.feet[2]) > 0.3);
  const heard = await p.evaluate(() => window.__testNoise);
  check('climbing in and out makes a little noise', heard.includes('hide_in') && heard.includes('hide_out'), heard.join(','));
  // knocked down while hidden: dragged out to the exit first
  await p.evaluate(([x, y, z]) => { const pl = window.__player; pl.pos.set(x, y, z); pl.syncCamera(); window.__camera.lookAt(x, y + 1.2, z - 2); }, [X, g.y, Z]);
  await p.waitForTimeout(200);
  await press('KeyE', 100); await settled(true);
  check('in again', (await st()).hidden);
  await p.evaluate(([x, y, z]) => window.__player.knockDown([x, y, z]), [X, g.y, FIX_Z + 2.5]);
  await p.waitForTimeout(100);
  s = await st();
  check('knockDown pulls the player out', !s.hidden && !s.spot && (await p.evaluate(() => window.__player.isDown)));
  await p.waitForTimeout(3000);

  // ---------------------------------------------------------------- the level's hiding spots
  const spots = await p.evaluate(() => {
    const disabled = window.__interact.items.filter((i) => i.def.type === 'hide' && i.disabled).map((i) => `${i.root.name}: ${i.disabled}`);
    return { disabled, spots: window.__hiding.spots().filter((s) => s.name !== 'TestWardrobe').map((s) => ({ name: s.name, cover: s.cover, eye: s.eye.toArray(), exit: s.exit.toArray() })) };
  });
  for (const d of spots.disabled) console.log(`note  disabled: ${d}`);
  console.log(`${spots.spots.length} hiding spots in the level`);
  let n = 0;
  for (const sp of spots.spots) {
    n++;
    if (only && !sp.name.toLowerCase().includes(only.toLowerCase())) continue;
    // stand at the exit, look at the spot's eye
    await p.evaluate(([e, ey]) => {
      const pl = window.__player; pl.pos.set(e[0], e[1], e[2]); pl.vel.set(0, 0, 0); pl.syncCamera();
      window.__camera.lookAt(ey[0], Math.min(ey[1], e[1] + 1.2), ey[2]);
    }, [sp.exit, sp.eye]);
    await p.waitForTimeout(500);
    const h = await hint();
    const ok = h.includes('E · ') && !h.includes('Leave');
    await press('KeyE', 100); await settled(true);
    s = await st();
    const tag = `${String(n).padStart(2, '0')}_${sp.name}`;
    await p.screenshot({ path: `${out}/hide_${tag}.png` });
    check(`${sp.name}: in (${sp.cover})`, ok && s.hidden, `hint "${h.trim()}"`);
    await press('KeyE', 100); await settled(false);
    s = await st();
    await p.keyboard.down('KeyW'); await p.waitForTimeout(400); await p.keyboard.up('KeyW');
    const s4 = await st();
    check(`${sp.name}: out and free to move`, !s.hidden && Math.hypot(s4.feet[0] - s.feet[0], s4.feet[2] - s.feet[2]) > 0.2,
      `exit ${s.feet.map((v) => v.toFixed(2)).join(',')}`);
  }
} finally {
  await b.close();
  release();
}
console.log(fails ? `${fails} FAILED` : 'all passed');
process.exit(fails ? 1 : 0);
