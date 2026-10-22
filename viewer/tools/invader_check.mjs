// Contract test of the invader asset (design/invaders/character.md) in three.js, plus the house hook.
//   GT_BASE=http://localhost:8826 node viewer/tools/invader_check.mjs
// 1. viewer/invader_view.html: every clip (and its duration), the 34 joints, the root's userData,
//    the outfit maps load, LOD triangle counts, sockets/markers exist, guns point along +Z when aimed.
// 2. the house (index.html?level=mansion&invaders=...): invaders standing in the entry playing clips
//    (screenshot build/invader/house_*.png), their mixers advancing.
import fs from 'fs';
import { chromium } from 'playwright-core';

const base = process.env.GT_BASE || 'http://localhost:8826';
fs.mkdirSync('build/invader', { recursive: true });
let slot = null;
for (let tries = 0; slot === null; tries++) {
  for (let i = 0; i < 3 && slot === null; i++) { try { fs.mkdirSync(`build/locks/browser_${i}`); slot = i; } catch {} }
  if (slot === null) { if (tries > 600) throw new Error('no browser slot'); await new Promise((r) => setTimeout(r, 2000)); }
}
const release = () => { try { fs.rmdirSync(`build/locks/browser_${slot}`); } catch {} };
process.on('exit', release);

const CLIPS = ['Idle', 'IdleAlert', 'Walk', 'Run', 'CrouchIdle', 'CrouchWalk', 'Search', 'HoldRifle', 'HoldPistol', 'AimRifle',
  'AimPistol', 'Drag', 'OpenDoor', 'Vault', 'Shout', 'Signal', 'ShootRifle', 'ShootPistol', 'ReloadRifle', 'ReloadPistol',
  'MeleeBat', 'MeleeKnife', 'HitFront', 'HitBack', 'Stagger', 'DeathForward', 'DeathBack', 'Grab'];
const NODES = ['Invader_Armature', 'Invader_Body_LOD0', 'Invader_Body_LOD1', 'Invader_Body_LOD2', 'Invader_Mask', 'Invader_Cap',
  'Invader_Hood', 'Invader_Rifle', 'Invader_Pistol', 'Invader_Bat', 'Invader_Knife', 'Invader_Rifle_Muzzle', 'Invader_Pistol_Muzzle',
  'Invader_Bat_Tip', 'Invader_Knife_Tip', 'Socket_Hand_R', 'Socket_Hand_L', 'Socket_Head', 'Socket_Back', 'Socket_Hip_R', 'Head', 'Hand_R'];
const KEYS = ['walkStride', 'walkCycle', 'runStride', 'runCycle', 'crouchWalkStride', 'crouchWalkCycle', 'dragStride', 'dragCycle',
  'events', 'lods', 'lodDistance', 'outfits', 'attachments', 'weapons', 'sockets', 'upperBody', 'height', 'eyeHeight', 'crouchEyeHeight'];

let fails = 0;
const check = (ok, msg) => { console.log(`${ok ? 'ok  ' : 'FAIL'} ${msg}`); if (!ok) fails++; };

const b = await chromium.launch({ channel: 'chrome', args: ['--use-angle=metal'] });
try {
  const p = await b.newPage({ viewport: { width: 900, height: 700 } });
  p.on('pageerror', (e) => { console.log('pageerror:', e.message); fails++; });
  await p.goto(`${base}/viewer/invader_view.html`);
  await p.waitForFunction(() => window.__loaded, null, { timeout: 90000 });
  const r = await p.evaluate(({ NODES }) => {
    const I = window.__inv;
    const info = I.info();
    const nodes = Object.fromEntries(NODES.map((n) => [n, !!I.inv.nodes[n]]));
    const maps = Object.fromEntries((I.meta.outfits || []).map((o) => {
      const m = I.asset.outfitMaterial(o.name);
      return [o.name, !!(m && m.map && m.map.image && m.map.image.width)];
    }));
    // aim: the muzzle marker's +Z in world, the invader facing +Z
    const THREE = I.inv.root.constructor;   // (Object3D)
    const dir = (clip, weapon) => {
      I.inv.setWeapon(weapon);
      I.pose(clip, 0.5);
      I.inv.root.updateMatrixWorld(true);
      const m = I.inv.nodes[`Invader_${weapon}_Muzzle`].matrixWorld.elements;
      const z = [m[8], m[9], m[10]];
      const n = Math.hypot(...z);
      const pos = [m[12], m[13], m[14]];
      return { z: z.map((v) => +(v / n).toFixed(3)), pos: pos.map((v) => +v.toFixed(3)) };
    };
    return { info, nodes, maps, rifle: dir('AimRifle', 'Rifle'), pistol: dir('AimPistol', 'Pistol') };
  }, { NODES });
  const clips = r.info.clips;
  for (const c of CLIPS) check(c in clips, `clip ${c} ${clips[c] ?? ''} s`);
  check(Object.keys(clips).length === CLIPS.length, `${Object.keys(clips).length} clips (${CLIPS.length} in the contract)`);
  check(r.info.joints.length === 34, `${r.info.joints.length} joints`);
  check(r.info.joints.every((n) => !n.includes('.')), 'joint names have no dots');
  for (const k of KEYS) check(k in r.info.userData, `userData.${k}`);
  for (const [n, ok] of Object.entries(r.nodes)) check(ok, `node ${n}`);
  for (const [n, ok] of Object.entries(r.maps)) check(ok, `outfit ${n} base colour loads`);
  const [t0, t1, t2] = r.info.tris;
  check(t0 >= 8000 && t0 <= 12000 && t1 <= 3600 && t2 <= 1000, `LOD triangles ${t0} / ${t1} / ${t2}`);
  check(r.rifle.z[2] > 0.95 && r.rifle.pos[1] > 1.35, `AimRifle: muzzle +Z = ${r.rifle.z}, at ${r.rifle.pos}`);
  check(r.pistol.z[2] > 0.95 && r.pistol.pos[1] > 1.35, `AimPistol: muzzle +Z = ${r.pistol.z}, at ${r.pistol.pos}`);
  check(Math.abs((clips.Walk ?? 0) - r.info.userData.walkCycle) < 0.02, `Walk duration ${clips.Walk} = walkCycle ${r.info.userData.walkCycle}`);
  await p.close();

  // ---- the house
  const spec = ['-2.2,12.6,15,AimRifle,Rifle,Navy,cap', '2.4,12.2,-25,Search,,Olive,hood', '0.2,11.2,0,Walk,,Charcoal,mask',
    '-4.5,14.5,60,HoldPistol,Pistol,Charcoal,none', '4.6,15.2,-70,MeleeBat,Bat,Navy,mask+hood'].join(';');
  const h = await b.newPage({ viewport: { width: 1400, height: 820 } });
  h.on('pageerror', (e) => { console.log('pageerror:', e.message); fails++; });
  await h.goto(`${base}/viewer/index.html?level=mansion&grimble=0&invaders=${spec}&pos=0,1.65,18.6&look=0,1.2,11`);
  await h.waitForFunction(() => window.__loaded, null, { timeout: 180000 });
  await h.waitForTimeout(2500);
  const s = await h.evaluate(() => (window.__invaders || []).map((i) => ({ clip: i.currentName, t: +i.current.time.toFixed(2), lod: i.lod })));
  check(s.length === 5, `house: ${s.length} invaders placed`);
  check(s.every((x) => x.t > 0 || x.clip === 'MeleeBat'), `house: clips playing ${JSON.stringify(s)}`);
  await h.evaluate(() => { for (const id of ['hud', 'hint', 'cross']) { const e = document.getElementById(id); if (e) e.style.display = 'none'; } });
  await h.screenshot({ path: 'build/invader/house_entry.png' });
  console.log('shot build/invader/house_entry.png');
  await h.close();
} finally {
  await b.close();
  release();
}
console.log(fails ? `${fails} FAILED` : 'all ok');
process.exit(fails ? 1 : 0);
