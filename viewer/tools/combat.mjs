// Combat (viewer/combat.js, viewer/weapons.js): pick up the kitchen knife, stab / slash a practice
// dummy until it dies, a stealth takedown from behind (and none when it's aware), a hit-scan shot
// stopped by a wall, take damage (vignette, direction wedge, regeneration), die, restart.
// Screenshots of the view model. Positions from the level file; if the level has no knife yet
// (before the house rebuild) the test places the knife's model on the island's board itself.
//   node viewer/tools/combat.mjs [out-dir]        (GT_BASE=http://localhost:<port> for a worktree)
import fs from 'fs';
import { chromium } from 'playwright-core';
import { level, props, room, url } from './level.mjs';

const out = process.argv[2] || 'build/combat';
fs.mkdirSync(out, { recursive: true });
// one browser slot of build/locks/browser_0..2 (shared by every agent on this machine)
fs.mkdirSync('build/locks', { recursive: true });
let slot = null;
while (slot === null) {
  for (let i = 0; i < 3 && slot === null; i++) { try { fs.mkdirSync(`build/locks/browser_${i}`); slot = i; } catch {} }
  if (slot === null) await new Promise((r) => setTimeout(r, 2000));
}
const release = () => { try { fs.rmdirSync(`build/locks/browser_${slot}`); } catch {} };
process.on('exit', release);
process.on('SIGINT', () => { release(); process.exit(130); });

let fails = 0;
const check = (label, ok, detail = '') => { console.log(`${ok ? 'PASS' : 'FAIL'}  ${label}  ${detail}`); if (!ok) fails++; };

// the knife: placed by the kitchen (blender/levels/rooms/kitchen.py), else where it will be
const k = room('kitchen');
const placed = props('kitchen_knife')[0];
const knife = placed ? placed.position : [k.cx - 0.31, 0.965, k.cz + 1.52];
const eye = [knife[0], 1.65, knife[2] + 0.95];

const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
try {
  const p = await b.newPage({ viewport: { width: 1280, height: 760 } });
  p.on('pageerror', (e) => console.log('pageerror:', e.message));
  p.on('console', (m) => { if (m.type() === 'error') console.log('console:', m.text()); });
  await p.goto(url(eye, knife) + '&grimble=0');
  await p.waitForFunction(() => window.__loaded, null, { timeout: 120000 });
  await p.mouse.click(640, 380); await p.waitForTimeout(400);
  const press = async (key, wait = 300) => { await p.keyboard.press(key); await p.waitForTimeout(wait); };
  const teleport = (pos, look) => p.evaluate(([pos, look]) => {
    const pl = window.__player;
    pl.pos.set(pos[0], pos[1] - 1.65, pos[2]); pl.vel.set(0, 0, 0); pl.syncCamera(); window.__camera.lookAt(...look);
  }, [pos, look]);
  const hint = () => p.textContent('#hint');

  // ---- the knife
  if (!placed) {
    console.log('(no kitchen_knife in the level yet: placing its model on the island board)');
    await p.evaluate(async (at) => {
      const THREE = await import('three');
      const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js');
      const g = await (async () => { const { DRACOLoader } = await import('three/addons/loaders/DRACOLoader.js'); const l = new GLTFLoader(); l.setDRACOLoader(new DRACOLoader().setDecoderPath('https://unpkg.com/three@0.160.0/examples/jsm/libs/draco/gltf/')); return l.loadAsync('../assets/models/kitchen_knife.gltf'); })();
      const obj = g.scene.children[0] ?? g.scene;
      obj.position.set(...at); obj.rotation.y = THREE.MathUtils.degToRad(12);
      window.__three.scene.add(obj); obj.updateMatrixWorld(true);
      window.__interact.register(obj);
    }, knife);
  }
  await p.waitForTimeout(300);
  check('knife prompt in reach', /knife/i.test(await hint()), `hint="${(await hint()).trim()}"`);
  await press('KeyE', 500);
  const st = await p.evaluate(() => ({ has: window.__inventory.has('kitchen_knife'), armed: window.__inventory.armed, def: window.__weapons.def?.id }));
  check('picked up and armed', st.has && st.armed === 'kitchen_knife' && st.def === 'kitchen_knife', JSON.stringify(st));
  await p.waitForTimeout(600);
  const cost = await p.evaluate(() => {
    let meshes = 0, tris = 0;
    window.__weapons.vm.root.traverse((o) => { if (o.isMesh && o.visible) { meshes++; tris += (o.geometry.index ? o.geometry.index.count : o.geometry.attributes.position.count) / 3; } });
    return { meshes, tris: Math.round(tris) };
  });
  console.log(`view model cost: ${cost.meshes} draw calls, ${cost.tris} triangles`);
  check('view model is cheap (<= 8 draw calls, < 12k triangles)', cost.meshes <= 8 && cost.tris < 12000, JSON.stringify(cost));
  await p.evaluate(() => (document.getElementById('hint').style.visibility = 'hidden'));
  await p.screenshot({ path: `${out}/viewmodel_idle.png` });
  await p.evaluate(() => (document.getElementById('hint').style.visibility = ''));
  check('hint names the attacks', /Stab/.test(await hint()) && /slash/.test(await hint()), `hint="${(await hint()).trim()}"`);

  // ---- the rest in the north gallery (open floor), looking east (+x)
  const gn = room('gallery_n');
  const spot = [gn.x1 - 7.5, 0, gn.cz];
  const ahead = (d, y = 0) => [spot[0] + d, y, spot[2]];
  await teleport([spot[0], 1.65, spot[2]], ahead(3, 1.3));
  // a dummy facing the player (aware): stab 55, slash 38, stab -> dead
  const noises = [];
  await p.exposeFunction('__noted', (n) => noises.push(n));
  await p.evaluate(() => window.__noise.on((n) => window.__noted({ source: n.source, loudness: n.loudness })));
  const dummy = (pos, rotY, aware, id) => p.evaluate(async ([pos, rotY, aware, id]) => {
    const THREE = await import('three');
    const { spawnDummy } = await import('/viewer/weapons.js');
    const { scene } = window.__three;
    const t = spawnDummy({ scene, combat: window.__combat, colliders: window.__colliders, position: new THREE.Vector3(...pos), rotationY: rotY, aware, id });
    return t.id;
  }, [pos, rotY, aware, id]);
  const health = (id) => p.evaluate((id) => { const t = window.__combat.get(id); return t ? { h: Math.round(t.health), alive: t.alive } : null; }, id);
  await dummy(ahead(0.95), -90, true, 'd1');
  await p.waitForTimeout(200);
  await press('Enter', 120);
  await p.evaluate(() => (document.getElementById('hint').style.visibility = 'hidden'));
  await p.screenshot({ path: `${out}/viewmodel_stab.png` });
  await p.waitForTimeout(600);
  check('stab: 55 damage', (await health('d1')).h === 45, JSON.stringify(await health('d1')));
  await p.mouse.down({ button: 'right' }); await p.waitForTimeout(160);
  await p.screenshot({ path: `${out}/viewmodel_slash.png` });
  await p.mouse.up({ button: 'right' }); await p.waitForTimeout(700);
  check('slash: 38 damage', (await health('d1')).h === 7, JSON.stringify(await health('d1')));
  await p.mouse.down(); await p.mouse.up(); await p.waitForTimeout(700);
  const d1 = await health('d1');
  check('third hit kills', !d1.alive, JSON.stringify(d1));
  check('hits are a small noise', noises.filter((n) => n.source === 'melee').length === 3 && noises.every((n) => n.loudness <= 0.7), JSON.stringify(noises));
  const cooldown = await p.evaluate(() => { const w = window.__weapons; const a = w.attack('primary'); const b = w.attack('primary'); return [a, b]; });
  check('cooldown: a second attack right after is refused', cooldown[0] && !cooldown[1], JSON.stringify(cooldown));
  await p.waitForTimeout(900);
  await p.screenshot({ path: `${out}/dummy_dead.png` });
  await p.evaluate(() => (document.getElementById('hint').style.visibility = ''));

  // ---- takedown: an unaware dummy facing away, the player behind it
  await p.evaluate(() => window.__combat.get('d1').remove());
  await dummy(ahead(0.85), 90, false, 'd2');                 // faces +x, away from the player
  await p.waitForTimeout(300);
  check('takedown offered from behind', /Takedown/.test(await hint()), `hint="${(await hint()).trim()}"`);
  const kills = [];
  await p.exposeFunction('__kill', (k) => kills.push(k));
  await p.evaluate(() => window.__combat.on('kill', (e) => window.__kill({ id: e.target.id, stealth: e.stealth, by: e.from?.id })));
  await press('Enter', 200);
  await p.evaluate(() => (document.getElementById('hint').style.visibility = 'hidden'));
  await p.screenshot({ path: `${out}/viewmodel_takedown.png` });
  await p.waitForTimeout(800);
  const d2 = await health('d2');
  check('takedown kills in one hit', !d2.alive && kills.some((k) => k.id === 'd2' && k.stealth && k.by === 'player'), JSON.stringify({ d2, kills }));
  await p.evaluate(() => window.__combat.get('d2').remove());
  // aware (it has seen the player): no takedown, a plain stab
  await dummy(ahead(0.85), 90, true, 'd3');
  await p.waitForTimeout(300);
  check('no takedown when it is aware', !/Takedown/.test(await hint()), `hint="${(await hint()).trim()}"`);
  await press('Enter', 700);
  check('aware: a stab, 55', (await health('d3')).h === 45, JSON.stringify(await health('d3')));
  // in front of an unaware one: no takedown either
  await p.evaluate(() => window.__combat.get('d3').remove());
  await dummy(ahead(0.85), -90, false, 'd4');
  await p.waitForTimeout(300);
  check('no takedown from the front', !/Takedown/.test(await hint()), `hint="${(await hint()).trim()}"`);
  await p.evaluate(() => window.__combat.get('d4').remove());
  // a character whose box in the colliders isn't tagged (owner): still stabbed and shot
  await dummy(ahead(0.95), -90, true, 'd5');
  await p.evaluate(() => { for (const c of window.__colliders) if (c.owner?.id === 'd5') delete c.owner; });
  await p.waitForTimeout(700);
  await press('Enter', 700);
  const shot5 = await p.evaluate(async () => {
    const THREE = await import('three');
    const c = window.__combat, cam = window.__camera;
    return c.shoot({ from: 'player', origin: cam.position.clone(), dir: c.get('d5').position().clone().setY(cam.position.y - 0.4).sub(cam.position).normalize(), damage: 20 }).target?.id ?? null;
  });
  check('untagged character box: stab and shot still land', (await health('d5')).h === 25 && shot5 === 'd5', JSON.stringify({ h: await health('d5'), shot5 }));
  await p.evaluate(() => window.__combat.get('d5').remove());
  // a target shaped like the invaders workstream's (alive a getter, facing() a yaw, unaware()):
  // the takedown works and nothing throws
  const inv = await p.evaluate(async ([x, z]) => {
    const THREE = await import('three');
    const me = { pos: new THREE.Vector3(x, 0, z), health: 100, alive: true, yaw: Math.PI / 2, aware: 0 };
    const c = window.__combat;
    c.register({ id: 'invader:test', kind: 'invader', team: 'invader', position: () => me.pos, radius: 0.3, height: 1.8,
      get health() { return me.health; }, set health(v) { me.health = v; }, get maxHealth() { return 100; }, get alive() { return me.alive; },
      hit: (d) => { me.health = Math.max(0, me.health - d); if (me.health <= 0) me.alive = false; return d; },
      unaware: () => me.aware < 0.5, facing: () => me.yaw });
    const offered = !!window.__weapons.target();
    window.__weapons.attack('primary');
    await new Promise((r) => setTimeout(r, 700));
    c.unregister('invader:test');
    return { offered, health: me.health, alive: me.alive };
  }, ahead(0.85).filter((_, i) => i !== 1));
  check('invader-shaped target: takedown offered and kills', inv.offered && !inv.alive && inv.health === 0, JSON.stringify(inv));
  // 1 puts the knife away, 1 again raises it
  await press('Digit1', 200);
  const off = await p.evaluate(() => ({ armed: window.__inventory.armed, vm: window.__weapons.vm.root.visible }));
  await press('Digit1', 500);
  const on = await p.evaluate(() => ({ armed: window.__inventory.armed, vm: window.__weapons.vm.root.visible, equip: window.__weapons.vm.equip }));
  check('1 holsters, 1 re-arms (view model back up)', off.armed === null && !off.vm && on.armed === 'kitchen_knife' && on.vm && on.equip === 1, JSON.stringify({ off, on }));
  await p.evaluate(() => (document.getElementById('hint').style.visibility = ''));

  // ---- hitscan: down the gallery it hits, through the kitchen wall it doesn't
  const shots = await p.evaluate(async ([sx, sz]) => {
    const THREE = await import('three');
    const c = window.__combat;
    const { makeTarget } = await import('/viewer/combat.js');
    const t = c.register(makeTarget({ id: 'shot_dummy', position: new THREE.Vector3(sx + 4, 0, sz) }));
    const open = c.shoot({ from: 'player', origin: new THREE.Vector3(sx, 1.4, sz), dir: new THREE.Vector3(1, 0, 0), damage: 30 });
    const t2 = c.register(makeTarget({ id: 'behind_wall', position: new THREE.Vector3(sx, 0, sz - 3.5) }));
    const walled = c.shoot({ from: 'player', origin: new THREE.Vector3(sx, 1.4, sz), dir: new THREE.Vector3(0, 0, -1), damage: 30 });
    const r = { open: open.target?.id, h: t.health, walled: walled.target?.id ?? null, wall: walled.wall, d: +walled.distance.toFixed(2), h2: t2.health };
    c.unregister(t); c.unregister(t2);
    return r;
  }, [spot[0], spot[2]]);
  check('shoot: hits a target in the open', shots.open === 'shot_dummy' && shots.h === 70, JSON.stringify(shots));
  check('shoot: the wall stops it', shots.walled === null && shots.wall && shots.h2 === 100, JSON.stringify(shots));

  // ---- taking damage: vignette, direction wedge, health, regeneration
  await teleport([spot[0], 1.65, spot[2]], ahead(3, 1.4));
  await dummy([spot[0], 0, spot[2] - 1.5], 0, true, 'attacker');   // to the player's left (looking +x, -z is left)
  await p.evaluate(() => window.__combat.hit('player', 30, { from: 'attacker', weapon: 'knife' }));
  await p.waitForTimeout(120);
  const hurt = await p.evaluate(() => ({
    h: window.__vitals.health, vig: +getComputedStyle(document.getElementById('cb-vig')).opacity,
    wedges: document.querySelectorAll('.cb-ind').length, rot: document.querySelector('.cb-ind')?.style.transform }));
  check('hit: 30 damage, red vignette, a direction wedge', hurt.h === 70 && hurt.vig > 0.3 && hurt.wedges === 1, JSON.stringify(hurt));
  check('wedge points left (the attacker is on the left)', /rotate\(-\d/.test(hurt.rot || ''), hurt.rot);
  await p.screenshot({ path: `${out}/damage.png` });
  await p.evaluate(() => window.__combat.hit('player', 45, { from: 'attacker' }));
  await p.waitForTimeout(500);
  const low = await p.evaluate(() => ({ h: window.__vitals.health, breath: window.__vitals.breathLevel }));
  check('low health: breathing on', low.h === 25 && low.breath > 0.3, JSON.stringify(low));
  await p.screenshot({ path: `${out}/low_health.png` });
  const regen = await p.evaluate(async () => {
    const c = window.__combat, v = window.__vitals;
    const before = v.health;
    await new Promise((r) => setTimeout(r, 1000));
    const still = v.health;                                  // in combat: no regeneration yet
    c._last.set('player', c.time - 8);                       // 8 s since the last hit
    await new Promise((r) => setTimeout(r, 1500));
    return { before, still, after: v.health };
  });
  check('regenerates only out of combat', regen.still === regen.before && regen.after > regen.before + 2, JSON.stringify(regen));

  // ---- death and restart
  await p.evaluate(() => window.__combat.hit('player', 500, { from: 'attacker' }));
  await p.waitForTimeout(400);
  const dead = await p.evaluate(() => ({ dead: window.__vitals.dead, down: window.__player.isDown, alive: window.__combat.get('player').alive }));
  check('dies at 0: down for good', dead.dead && dead.down && !dead.alive, JSON.stringify(dead));
  await p.keyboard.press('KeyW');                             // input is ignored
  await p.waitForTimeout(3000);
  const scr = await p.evaluate(() => ({ text: document.getElementById('cb-death').innerText.trim(), shown: document.querySelector('#cb-death button').classList.contains('show'),
    op: +getComputedStyle(document.getElementById('cb-death')).opacity, stillDown: window.__player.isDown,
    visible: ['hud', 'hint', 'inventory', 'battery', 'cross', 'toast'].filter((id) => { const e = document.getElementById(id); return e && getComputedStyle(e).visibility !== 'hidden' && e.offsetParent !== null && e.textContent.trim() + e.className !== ''; }) }));
  check('death screen: faded, only a restart button', scr.shown && scr.op > 0.9 && scr.text === 'RESTART' && scr.stillDown && !scr.visible.length, JSON.stringify(scr));
  await p.screenshot({ path: `${out}/death.png` });
  await Promise.all([p.waitForNavigation({ timeout: 60000 }), p.click('#cb-death button')]);
  await p.waitForFunction(() => window.__loaded, null, { timeout: 120000 });
  const fresh = await p.evaluate(() => ({ h: window.__vitals.health, dead: window.__vitals.dead, down: window.__player.isDown }));
  check('restart: a new run', fresh.h === 100 && !fresh.dead && !fresh.down, JSON.stringify(fresh));
} finally {
  await b.close();
  release();
}
console.log(fails ? `${fails} FAILED` : 'all passed');
process.exit(fails ? 1 : 0);
