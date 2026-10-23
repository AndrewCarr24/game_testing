import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';

// The invaders' rigged bodies: the character workstream's asset (assets/models/invader.gltf,
// design/invaders/character.md) driven by the brains. Two paths, as that contract recommends:
// - near the player (within `near` m, at most `maxNear` at once, nearest first): a SkinnedMesh
//   each (viewer/invader_asset.js Invader: cross-fades, the upper body layered over the legs:
//   walking while aiming), its LODs by distance, lit by its room's probe like the props;
// - the rest: the instanced GPU-skinned crowd (viewer/invader_crowd.js InvaderCrowd: one clip
//   each, ~10 draw calls for all of them).
// An invader is handed from one to the other as it comes near / goes away. Same interface as the
// stand-in (invaders_body.js): add(a), remove(a), update(agents, dt, camera).
//
// What the brain's state plays (clip names from the contract):
//   dead            DeathBack / DeathForward (by where the blow came from)
//   staggered       HitFront / HitBack
//   strike          MeleeBat / MeleeKnife (the brain's windup is set from the clip's hit event)
//   breach, check   OpenDoor (a kick / shove at the door, opening a hiding spot)
//   legs            Run / Walk (playback rate from the speed: feet planted) / CrouchWalk /
//                   CrouchIdle / Search (looking round in a sweep or search) / IdleAlert / Idle
//   arms (guns)     AimRifle / AimPistol while aiming, ShootRifle / ShootPistol for each shot,
//                   HoldRifle / HoldPistol at the ready
export async function loadRig(scene, max, base = '../assets/models/') {
  const [{ InvaderAsset }, { InvaderCrowd }] = await Promise.all([import('./invader_asset.js'), import('./invader_crowd.js')]);
  const loader = new GLTFLoader();
  loader.setDRACOLoader(new DRACOLoader().setDecoderPath('https://unpkg.com/three@0.160.0/examples/jsm/libs/draco/gltf/'));
  const asset = await InvaderAsset.load(loader, `${base}invader.gltf`);
  await asset.preloadOutfits();
  const crowd = await InvaderCrowd.load(asset, `${base}invader_anim.json`, { lod: 2, max });
  return new RigBodies(scene, asset, crowd);
}

const WEAPON = { rifle: 'Rifle', pistol: 'Pistol', bat: 'Bat', knife: 'Knife' };
const _q1 = new THREE.Quaternion(), _q2 = new THREE.Quaternion(), _ax = new THREE.Vector3();
const HEADS = ['none', 'mask', 'cap', 'hood', 'mask+hood', 'mask', 'none', 'mask+cap'];
const LOOK_STATES = new Set(['search', 'sweep', 'investigate', 'check', 'post', 'hold']);   // (not 'scene': the opening picks)

export class RigBodies {
  constructor(scene, asset, crowd, { near = 22, maxNear = 8 } = {}) {
    Object.assign(this, { scene, asset, crowd, near, maxNear });
    this.meta = asset.meta;
    this.outfits = (this.meta.outfits || []).map((o) => o.name);
    crowd.mesh.traverse((o) => { if (o.isMesh) { o.castShadow = false; o.receiveShadow = false; } });
    scene.add(crowd.mesh);
    this.pool = [];
    this.list = [];
    this.hidden = new THREE.Vector3(0, -200, 0);
    this.rig = true;
  }

  // the brain's melee timings from the clips' hit events
  tune(WEAPONS) {
    const ev = this.meta.events || {};
    for (const [w, clip] of [['bat', 'MeleeBat'], ['knife', 'MeleeKnife']]) {
      const e = ev[clip], W = WEAPONS[w];
      if (!e?.hit || !W) continue;
      W.windup = e.hit[0] + 0.04;
      W.recover = Math.max(0.2, (e.duration ?? 1) - W.windup);
    }
  }

  add(a) {
    // (a.look: the opening's cast picks each one's outfit and headgear)
    const outfit = a.look?.outfit && this.outfits.includes(a.look.outfit) ? a.look.outfit : a.role === 'leader' ? this.outfits[1] ?? this.outfits[0] : this.outfits[(a.id * 7) % Math.max(1, this.outfits.length)];
    const head = a.look?.head ?? (a.role === 'leader' ? 'cap' : HEADS[(a.id * 5) % HEADS.length]);
    a.rig = { outfit, head, weapon: WEAPON[a.weaponName] ?? null, skinned: null, key: null, ckey: null };
    a.rig.cid = this.crowd.add({ position: a.pos.clone(), rotationY: a.yaw, outfit, head: head === 'none' ? null : head, weapon: a.rig.weapon, clip: 'Idle', time: -Math.random() * 3 });
    a.rig.muzzle = () => {
      const s = a.rig.skinned;
      if (!s || !(a.weaponName === 'rifle' || a.weaponName === 'pistol')) return null;
      return s.worldPosition(`Invader_${a.rig.weapon}_Muzzle`);
    };
    this.list.push(a);
  }
  remove(a) {
    if (!a.rig) return;
    this.release(a);
    this.crowd.set(a.rig.cid, { position: this.hidden });
    this.list = this.list.filter((b) => b !== a);
  }

  acquire(a) {
    let s = this.pool.pop();
    if (!s) {
      s = this.asset.spawn({});
      s.root.traverse((o) => { if (o.isMesh) { o.castShadow = false; o.receiveShadow = false; } });
      this.scene.add(s.root);
    }
    s.setOutfit(a.rig.outfit); s.setHead(a.rig.head); s.setWeapon(a.rig.weapon);
    s.root.scale.setScalar(a.scale ?? 1);
    this.holster(s, a, true);
    s.root.traverse((o) => { if (o.isMesh) o.userData.invBase = o.material; });
    a.rig.room = undefined;
    s.root.visible = true;
    s.current = null; s.mixer.stopAllAction();
    a.rig.skinned = s; a.rig.key = null;
    this.crowd.set(a.rig.cid, { position: this.hidden });
  }
  release(a) {
    const s = a.rig?.skinned;
    if (!s) return;
    s.root.visible = false;
    s.mixer.stopAllAction();
    s.root.traverse((o) => { if (o.isMesh && o.userData.invBase) o.material = o.userData.invBase; });
    if (s.holstered) this.holster(s, { holstered: false, rig: a.rig }, true);
    s.root.scale.setScalar(1);
    this.pool.push(s);
    a.rig.skinned = null; a.rig.ckey = null;
  }

  // a holstered weapon hangs from the hip socket (the opening's leader rings the bell with empty
  // hands); drawn, it's back in the right hand
  holster(s, a, force = false) {
    const want = !!a.holstered;
    if (!force && s.holstered === want) return;
    const w = s.nodes[`Invader_${a.rig?.weapon}`], to = s.nodes[want ? 'Socket_Hip_R' : 'Socket_Hand_R'];
    if (w && to && w.parent !== to) { to.add(w); w.position.set(0, 0, 0); w.quaternion.identity(); }
    s.holstered = want;
  }

  // what it should be playing: {lower, upper?, rate, once, key}
  clipFor(a) {
    const M = this.meta, gun = a.holstered ? null : a.weaponName === 'rifle' ? 'Rifle' : a.weaponName === 'pistol' ? 'Pistol' : null;
    if (!a.alive) return { lower: a.fellForward ? 'DeathForward' : 'DeathBack', once: true };
    // (a one-shot the opening asks for: the bell, a knock, a handle, a point)
    if (a.pose && a.state === 'scene' && !(a.staggerUntil > a.time)) return { lower: a.pose.name, once: true, key: a.pose.key, rate: a.pose.rate ?? 1 };
    if (a.staggerUntil > a.time) return { lower: a.hitFromBehind ? 'HitBack' : 'HitFront', once: true, key: `hit${a.stats.hitsTaken}` };
    if (a.state === 'strike' && a.anim.swing >= 0) return { lower: a.weaponName === 'knife' ? 'MeleeKnife' : 'MeleeBat', once: true, key: `swing${a.stats.swings}` };
    if (a.state === 'breach' || (a.state === 'check' && a.sub?.phase !== 'go')) return { lower: 'OpenDoor', once: true, key: `door${a.sub?.n ?? 0}` };
    if (a.anim.swing >= 0 && a.state === 'arrive') return { lower: 'MeleeBat', once: true, key: `glass${a.sub?.n ?? 0}` };
    const v = a.moveSpeed ?? 0;
    let lower, rate = 1;
    if (a.crouch > 0.5) { lower = v > 0.2 ? 'CrouchWalk' : 'CrouchIdle'; if (v > 0.2) rate = v / ((M.crouchWalkStride ?? 1.1) / (M.crouchWalkCycle ?? 1.4)); }
    else if (v > 2.6) { lower = 'Run'; rate = v / ((M.runStrideMeasured ?? M.runStride ?? 3.3) / (M.runCycle ?? 0.733)); }
    else if (v > 0.25) { lower = 'Walk'; rate = v / ((M.walkStrideMeasured ?? M.walkStride ?? 1.42) / (M.walkCycle ?? 1.133)); }
    else lower = a.idleClip ?? (LOOK_STATES.has(a.state) && !gun ? 'Search' : (a.sq?.alert > 0.5 ? 'IdleAlert' : 'Idle'));
    let upper = null;
    if (gun) {
      if (a.time - (a.anim.shotAt ?? -1e9) < 0.18) upper = `Shoot${gun}`;
      else if (a.anim.aim > 0.5) upper = `Aim${gun}`;
      else upper = `Hold${gun}`;
    }
    return { lower, upper, rate: Math.min(2.2, Math.max(0.4, rate)) };
  }

  update(agents, dt, camera) {
    this.crowd.update(dt);
    const eye = camera.position;
    // who gets a SkinnedMesh: the nearest within `near` (the living first)
    const near = this.list.filter((a) => a.pos.distanceTo(eye) < this.near)
      .sort((p, q) => (p.alive === q.alive ? p.pos.distanceTo(eye) - q.pos.distanceTo(eye) : p.alive ? -1 : 1)).slice(0, this.maxNear);
    const want = new Set(near);
    for (const a of this.list) if (a.rig.skinned && !want.has(a)) this.release(a);
    for (const a of near) if (!a.rig.skinned) this.acquire(a);
    for (const a of this.list) {
      const c = this.clipFor(a), s = a.rig.skinned;
      const yaw = a.alive ? a.yaw : a.dieYaw ?? a.yaw;
      if (s) {
        s.root.position.copy(a.pos);
        s.root.rotation.y = yaw;
        const key = `${c.lower}|${c.upper ?? ''}|${c.key ?? ''}`;
        if (key !== a.rig.key) {
          const first = a.rig.key == null;
          const act = c.upper ? s.play(c.upper, { upper: true, lower: c.lower, fade: first ? 0 : 0.2 }) : s.play(c.lower, { fade: first ? 0 : c.once ? 0.1 : 0.22 });
          if (act && c.once) { act.setLoop(THREE.LoopOnce, 1); act.clampWhenFinished = true; act.timeScale = c.rate ?? 1; }
          a.rig.key = key;
        }
        // (a bigger or smaller one: the same stride in its own steps)
        if (s.current && c.rate && !c.once) s.current.timeScale = c.rate / (a.scale ?? 1);
        this.holster(s, a);
        s.update(dt, eye);
        this.turnHead(s, a);
        this.light(a);
      } else {
        // the crowd: one clip each (an aiming gunman standing still aims; moving, its legs win)
        const clip = c.once ? c.lower : (a.moveSpeed ?? 0) < 0.25 && c.upper && !/^Shoot/.test(c.upper) ? c.upper : c.lower;
        const ck = `${clip}|${c.key ?? ''}`;
        const opts = { position: a.pos, rotationY: yaw, speed: c.once ? 1 : c.rate ?? 1 };
        if (ck !== a.rig.ckey) { opts.clip = clip; a.rig.ckey = ck; }
        this.crowd.set(a.rig.cid, opts);
      }
    }
  }

  // the head and neck follow where the brain looks (lookYaw, relative to the body; up to ~60
  // degrees): turning toward a noise, scanning a room, staring at someone through the glass
  turnHead(s, a) {
    if (!a.alive || a.staggerUntil > a.time) return;
    const off = Math.max(-1.05, Math.min(1.05, Math.atan2(Math.sin(a.lookYaw - a.yaw), Math.cos(a.lookYaw - a.yaw))));
    s._headOff = (s._headOff ?? 0) + (off - (s._headOff ?? 0)) * 0.25;
    if (Math.abs(s._headOff) < 0.01) return;
    const neck = s.nodes.Neck, head = s.nodes.Head;
    if (!neck || !head) return;
    s.root.updateMatrixWorld(true);
    for (const [b, k] of [[neck, 0.4], [head, 0.6]]) {
      const pq = b.parent.getWorldQuaternion(_q1).invert();
      _ax.set(0, 1, 0).applyQuaternion(pq).normalize();
      b.quaternion.premultiply(_q2.setFromAxisAngle(_ax, s._headOff * k));
      b.updateMatrixWorld(true);
    }
  }

  // lit like the props: the room's probe (SH) and panorama (viewer/baked.js applyRoom), swapped
  // as it walks from room to room; outdoors the scene's own environment
  light(a) {
    const L = window.__lighting;
    if (!L?.applyRoom || !a.sq?.world) return;
    const room = a.sq.world.roomAt(a.pos.x, a.pos.y + 0.5, a.pos.z)?.name ?? null;
    if (room === a.rig.room) return;
    a.rig.room = room;
    const s = a.rig.skinned;
    s.root.traverse((o) => { if (o.isMesh && o.userData.invBase) o.material = o.userData.invBase; });
    if (room) L.applyRoom(s.root, room, a.sq.level.rooms[room]?.sun === false);
  }

  dispose() {
    this.scene.remove(this.crowd.mesh);
    for (const a of this.list) if (a.rig?.skinned) this.scene.remove(a.rig.skinned.root);
    for (const s of this.pool) this.scene.remove(s.root);
  }
}
