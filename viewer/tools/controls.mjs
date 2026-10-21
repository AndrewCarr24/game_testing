// Wall controls (light / blinds / fire / garage switches, the breaker, wall panels): for every
// one in the level, stand in front of it on the floor, look at it and check that it is the
// thing in focus, that its prompt says what it does, that nothing (furniture, art, a door, a
// wall) sits between the eye and it, and that E toggles its signal (pressed again to restore).
// Screenshots: a close-up with the prompt (the player's view) and a context view from further
// back (where it sits in the room), plus contact sheets.
// Usage: node viewer/tools/controls.mjs [out-dir] [room ...]   (GT_BASE picks the server)
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';
import { execFileSync } from 'child_process';
import { level } from './level.mjs';

const [outDir = 'build/controls/check', ...only] = process.argv.slice(2);
const base = process.env.GT_BASE || 'http://localhost:8765';
fs.mkdirSync(outDir, { recursive: true });

// what each control's prompt must name (both states)
const EXPECT = {
  ix_switch: /lights/i, ix_switch_blinds: /blinds/i, ix_switch_fire: /fire/i,
  ix_switch_garage: /garage/i, ix_breaker_panel: /power|fuse/i,
};
const isControl = (a) => a.startsWith('ix_switch') || a === 'ix_breaker_panel' || a === 'ix_control_panel';
const controls = level.props.filter((p) => isControl(p.asset) && (!only.length || only.includes(p.room)));

// machine-wide browser slots (build/locks), as review_room.mjs
const lockDir = 'build/locks';
fs.mkdirSync(lockDir, { recursive: true });
let slot = null;
for (;;) {
  for (let i = 0; i < 3 && slot === null; i++) {
    try { fs.mkdirSync(`${lockDir}/browser_${i}`); slot = i; } catch {}
  }
  if (slot !== null) break;
  await new Promise((ok) => setTimeout(ok, 3000));
}
const release = () => { try { fs.rmdirSync(`${lockDir}/browser_${slot}`); } catch {} };
process.on('exit', release);
process.on('SIGINT', () => { release(); process.exit(1); });

let fails = 0;
const results = [];
const closeups = [], contexts = [], toggledShots = [];
try {
  const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
  const p = await b.newPage({ viewport: { width: 960, height: 600 } });
  p.on('pageerror', (e) => console.log('pageerror:', e.message));
  const c0 = controls[0];
  await p.goto(`${base}/viewer/index.html?level=mansion&grimble=0&pos=${c0.position[0]},${c0.position[1] + 0.5},${c0.position[2] + 1}&look=${c0.position.join(',')}`);
  await p.waitForFunction(() => window.__loaded, null, { timeout: 120000 });
  await p.mouse.click(480, 300);
  await p.waitForTimeout(500);

  const seen = {};
  for (const c of controls) {
    const floor = level.rooms[c.room]?.floor ?? 0;
    const t = (c.rotationY * Math.PI) / 180;
    const n = [Math.sin(t), Math.cos(t)];                    // the plate's front (glTF x, z)
    // the plate's face centre (the breaker's origin is its box's back centre too)
    const at = [c.position[0], c.position[1], c.position[2]];
    const k = (seen[c.room] = (seen[c.room] || 0) + 1);
    const label = `${c.room}_${c.asset.replace(/^ix_/, '')}_${k}`;
    const r = await p.evaluate(async ([at, n, floor, dist]) => {
      const THREE = await import('three');
      const pl = window.__player, cam = window.__camera, it = window.__interact;
      // stand where a person would: straight out first, else a step to either side or closer
      // (a switch near a corner or beside a plant); `crowded` if no spot in reach is clear
      let crowded = 1;
      for (const [o, s] of [[dist, 0], [dist, 0.3], [dist, -0.3], [0.65, 0], [0.65, 0.35], [0.65, -0.35], [dist, 0.5], [dist, -0.5]]) {
        pl.pos.set(at[0] + n[0] * o + n[1] * s, floor, at[2] + n[1] * o - n[0] * s);
        if (!pl.overlapping(pl.pos.clone().setY(floor + 0.05)).length) { crowded = 0; break; }
      }
      if (crowded) pl.pos.set(at[0] + n[0] * dist, floor, at[2] + n[1] * dist);
      pl.vel.set(0, 0, 0);
      pl.syncCamera(); cam.lookAt(at[0], at[1], at[2]); cam.updateMatrixWorld(true);
      const eye = cam.position.clone(), target = new THREE.Vector3(...at);
      // the items of this control: interact items whose node is within 0.4 m of its origin
      const mine = it.items.filter((i) => i.node.getWorldPosition(new THREE.Vector3()).distanceTo(target) < 0.45);
      const focus = it.nearest(eye, cam.getWorldDirection(new THREE.Vector3()));
      // occlusion: the first mesh the eye->target ray hits must be the control itself (within
      // 3 cm of the plate) or one of its parts
      const ray = new THREE.Raycaster(eye, target.clone().sub(eye).normalize(), 0.05, eye.distanceTo(target) + 0.05);
      const meshes = [];
      window.__three.scene.traverseVisible((o) => { if (o.isMesh && !o.userData?.fx) meshes.push(o); });
      // (skip hidden reactor materials and see-through glass)
      const hit = ray.intersectObjects(meshes, false).find((h) => {
        const m = Array.isArray(h.object.material) ? h.object.material[0] : h.object.material;
        return m && m.visible !== false && !(m.transparent && m.opacity < 0.6);
      });
      let blocker = null;
      if (hit && hit.distance < eye.distanceTo(target) - 0.03) {
        const own = mine.some((i) => { let o = hit.object; while (o) { if (o === i.root || o === i.node) return true; o = o.parent; } return false; });
        if (!own) blocker = hit.object.name || '(unnamed mesh)';
      }
      return {
        stood: [+pl.pos.x.toFixed(2), +pl.pos.y.toFixed(2), +pl.pos.z.toFixed(2)],
        // something solid where the player stands to use it (a cabinet, a sofa in the way)
        crowded,
        eyeDist: +eye.distanceTo(target).toFixed(2),
        items: mine.map((i) => i.node.name),
        focus: focus ? focus.node.name : null,
        focusMine: !!focus && mine.includes(focus),
        signal: focus && mine.includes(focus) ? focus.signal ?? null : null,
        blocker,
      };
    }, [at, n, floor, 0.85]);
    await p.waitForTimeout(250);
    const hint = ((await p.textContent('#hint')) || '').trim();
    const shot = path.join(outDir, `${label}.png`);
    await p.screenshot({ path: shot });
    closeups.push(shot);
    // toggle with E, check the signal flipped, toggle back
    let toggled = null;
    if (r.signal) {
      const before = await p.evaluate((s) => window.__signals.get(s), r.signal);
      await p.keyboard.press('KeyE'); await p.waitForTimeout(450);
      const after = await p.evaluate((s) => window.__signals.get(s), r.signal);
      const hint2 = ((await p.textContent('#hint')) || '').trim();
      toggled = { before: !!before, after: !!after, hint2 };
      const flipped = path.join(outDir, `${label}_toggled.png`);   // the part moved, its LED changed
      await p.screenshot({ path: flipped });
      toggledShots.push(flipped);
      await p.keyboard.press('KeyE'); await p.waitForTimeout(450);
    }
    // context: 2.6 m out, eye height (the player's eye; pulled in if it lands in a collider)
    await p.evaluate(([at, n, floor]) => {
      const pl = window.__player, cam = window.__camera;
      pl.pos.set(at[0] + n[0] * 2.6 + n[1] * 0.6, floor, at[2] + n[1] * 2.6 - n[0] * 0.6); pl.vel.set(0, 0, 0);
      pl.syncCamera(); cam.lookAt(at[0], at[1] - 0.2, at[2]);
    }, [at, n, floor]);
    await p.waitForTimeout(300);
    const ctx = path.join(outDir, `${label}_context.png`);
    await p.screenshot({ path: ctx });
    contexts.push(ctx);

    const want = EXPECT[c.asset];
    const problems = [];
    if (c.asset === 'ix_control_panel') {
      if (r.items.length) problems.push(`has interact ${r.items}`);
    } else {
      if (!r.focusMine) problems.push(`focus is ${r.focus ?? 'nothing'}`);
      if (want && !want.test(hint)) problems.push(`prompt "${hint}" doesn't say ${want}`);
      if (toggled && toggled.before === toggled.after && c.asset !== 'ix_breaker_panel') problems.push('E did not toggle');
      if (toggled && want && !want.test(toggled.hint2)) problems.push(`prompt after E "${toggled.hint2}"`);
    }
    if (r.blocker) problems.push(`hidden behind ${r.blocker}`);
    if (r.crowded) problems.push('no room to stand within reach of it');
    const ok = problems.length === 0;
    if (!ok) fails++;
    results.push({ label, asset: c.asset, room: c.room, position: c.position, rotationY: c.rotationY, hint, ...r, toggled, problems });
    console.log(`${ok ? 'PASS' : 'FAIL'}  ${label.padEnd(36)} "${hint}"${toggled ? ` -> "${toggled.hint2}"` : ''}${problems.length ? '  ' + problems.join('; ') : ''}`);
  }
  await b.close();
} finally { release(); }

fs.writeFileSync(path.join(outDir, 'controls.json'), JSON.stringify(results, null, 1));
const here = path.dirname(new URL(import.meta.url).pathname);
for (const [name, list] of [['closeups', closeups], ['toggled', toggledShots], ['contexts', contexts]]) {
  for (let i = 0; i < list.length; i += 12) {
    try {
      execFileSync('node', [path.join(here, 'grid.mjs'), path.join(outDir, `_${name}_${i / 12 + 1}.png`), '4', ...list.slice(i, i + 12)], { stdio: 'ignore' });
    } catch (e) { console.log(`grid failed: ${e.message}`); }
  }
}
console.log(`${controls.length} controls, ${fails} failing -> ${outDir}`);
process.exit(fails ? 1 : 0);
