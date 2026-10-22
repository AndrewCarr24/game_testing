import * as THREE from 'three';
import { clone as cloneSkinned } from 'three/addons/utils/SkeletonUtils.js';

// The invader character asset (blender/assets/invader.py; contract: design/invaders/character.md).
// Loading, per-instance setup (outfit, head attachments, weapon, LOD), clip playback with
// cross-fades and upper-body layering. No AI here: the behaviour code drives an Invader through
// play() / setWeapon() / update().
//
//   const asset = await InvaderAsset.load(gltfLoader, '../assets/models/invader.gltf');
//   const inv = asset.spawn({ outfit: 'Charcoal', head: 'cap', weapon: 'Rifle' });
//   scene.add(inv.root);  inv.play('Walk');  inv.play('AimRifle', { upper: true });
//   each frame: inv.update(dt, camera.position);

const LOD_NAMES = ['Invader_Body_LOD0', 'Invader_Body_LOD1', 'Invader_Body_LOD2'];
const ONCE = new Set(['OpenDoor', 'Vault', 'Shout', 'Signal', 'ShootRifle', 'ShootPistol', 'ReloadRifle',
  'ReloadPistol', 'MeleeBat', 'MeleeKnife', 'HitFront', 'HitBack', 'Stagger', 'DeathForward', 'DeathBack', 'Grab']);

export class InvaderAsset {
  static async load(loader, url) {
    const gltf = await new Promise((ok, fail) => loader.load(url, ok, undefined, fail));
    return new InvaderAsset(gltf, url.slice(0, url.lastIndexOf('/') + 1));
  }

  constructor(gltf, base) {
    this.gltf = gltf;
    this.base = base;
    // the numbers live on the root node's extras (blender/assets/invader.py)
    const rootNode = gltf.scene.getObjectByName('Invader');
    this.meta = { ...(gltf.scene.userData || {}), ...(rootNode ? rootNode.userData : {}) };
    this.clips = Object.fromEntries(gltf.animations.map((c) => [c.name, c]));
    this.upperSet = new Set(this.meta.upperBody || []);
    this.layered = new Map();
    this.outfitMaterials = new Map();   // outfit name -> material (shared by every invader wearing it)
    this.texLoader = new THREE.TextureLoader();
    let body = null;
    gltf.scene.traverse((o) => { if (o.isMesh && o.name === LOD_NAMES[0]) body = o; });
    this.bodyMaterial = body ? body.material : null;
    if (this.bodyMaterial) this.outfitMaterials.set(this.defaultOutfit(), this.bodyMaterial);
  }

  // load every outfit's base-colour map now (otherwise the first frames of a new outfit render untextured)
  async preloadOutfits() {
    await Promise.all((this.meta.outfits || []).map(async (o) => {
      const m = this.outfitMaterial(o.name);
      if (m && m !== this.bodyMaterial && m.map && !m.map.image) {
        await new Promise((ok) => { const t = setInterval(() => { if (m.map.image) { clearInterval(t); ok(); } }, 20); });
      }
    }));
  }

  defaultOutfit() { return (this.meta.outfits && this.meta.outfits[0] && this.meta.outfits[0].name) || 'default'; }

  outfitMaterial(name) {
    if (!this.bodyMaterial) return null;
    if (this.outfitMaterials.has(name)) return this.outfitMaterials.get(name);
    const o = (this.meta.outfits || []).find((x) => x.name === name);
    if (!o) return this.bodyMaterial;
    const m = this.bodyMaterial.clone();
    const src = this.bodyMaterial.map;
    const t = this.texLoader.load(`${this.base}textures/${o.map}.webp`);
    t.flipY = false;
    t.colorSpace = THREE.SRGBColorSpace;
    if (src) { t.channel = src.channel; t.wrapS = src.wrapS; t.wrapT = src.wrapT; t.anisotropy = src.anisotropy; }
    m.map = t;
    m.name = `M_Invader_Body_${name}`;
    this.outfitMaterials.set(name, m);
    return m;
  }

  // a clip whose upper-body joints come from `upper` and the rest from `lower`
  layeredClip(lower, upper) {
    const key = `${lower}|${upper}`;
    if (this.layered.has(key)) return this.layered.get(key);
    const lo = this.clips[lower], up = this.clips[upper];
    if (!lo || !up) return lo || up;
    const isUpper = (t) => this.upperSet.has(t.name.split('.')[0]);
    const tracks = [...lo.tracks.filter((t) => !isUpper(t)), ...up.tracks.filter(isUpper)];
    const c = new THREE.AnimationClip(key, lo.duration, tracks);
    this.layered.set(key, c);
    return c;
  }

  spawn(opts = {}) { return new Invader(this, opts); }
}

export class Invader {
  constructor(asset, { outfit, head = 'none', weapon = null, lod = null } = {}) {
    this.asset = asset;
    this.root = cloneSkinned(asset.gltf.scene);
    this.root.userData = { ...asset.meta };
    this.nodes = {};
    this.root.traverse((o) => {
      this.nodes[o.name] = o;
      if (o.isMesh) { o.frustumCulled = false; o.castShadow = false; }
    });
    this.lods = LOD_NAMES.map((n) => this.nodes[n]).filter(Boolean);
    this.mixer = new THREE.AnimationMixer(this.root);
    this.current = null;
    this.currentName = null;
    this.forcedLod = lod;
    this.setOutfit(outfit || asset.defaultOutfit());
    this.setHead(head);
    this.setWeapon(weapon);
    this.setLod(lod ?? 0);
  }

  setOutfit(name) {
    const m = this.asset.outfitMaterial(name);
    if (m) for (const o of this.lods) o.material = m;
    this.outfit = name;
  }

  // head: 'none' | 'mask' | 'cap' | 'hood' | 'mask+cap' | 'mask+hood'
  setHead(head) {
    const want = new Set(String(head || 'none').split('+'));
    for (const [k, n] of [['mask', 'Invader_Mask'], ['cap', 'Invader_Cap'], ['hood', 'Invader_Hood']]) {
      if (this.nodes[n]) this.nodes[n].visible = want.has(k);
    }
    this.head = head;
  }

  // weapon: null | 'Rifle' | 'Pistol' | 'Bat' | 'Knife'
  setWeapon(w) {
    for (const n of ['Rifle', 'Pistol', 'Bat', 'Knife']) {
      const o = this.nodes[`Invader_${n}`];
      if (o) o.visible = n === w;
    }
    this.weapon = w;
  }

  setLod(i) {
    this.lod = Math.max(0, Math.min(this.lods.length - 1, i));
    this.lods.forEach((o, k) => { o.visible = k === this.lod; });
  }

  // name: a clip; opts.upper: play `name` on the upper body over the current lower-body clip
  // (or opts.lower); opts.fade (s), opts.timeScale, opts.loop (default: loops except one-shots)
  play(name, opts = {}) {
    const a = this.asset;
    let clip, label = name;
    if (opts.upper || opts.lower) {
      const lower = opts.lower || this.lowerName || 'Idle';
      clip = a.layeredClip(lower, name);
      label = `${lower}|${name}`;
      this.lowerName = lower;
    } else {
      clip = a.clips[name];
      this.lowerName = name;
    }
    if (!clip) return null;
    const act = this.mixer.clipAction(clip);
    const once = opts.loop === false || (opts.loop === undefined && ONCE.has(name));
    act.setLoop(once ? THREE.LoopOnce : THREE.LoopRepeat, Infinity);
    act.clampWhenFinished = once;
    act.timeScale = opts.timeScale ?? 1;
    act.enabled = true;
    act.reset().play();
    if (this.current && this.current !== act) {
      act.crossFadeFrom(this.current, opts.fade ?? 0.25, false);
    }
    this.current = act;
    this.currentName = label;
    return act;
  }

  // world position of a socket / marker node (e.g. 'Invader_Rifle_Muzzle')
  worldPosition(node, out = new THREE.Vector3()) {
    const o = this.nodes[node];
    return o ? o.getWorldPosition(out) : null;
  }

  update(dt, camPos) {
    this.mixer.update(dt);
    if (camPos && this.forcedLod == null) {
      const d = camPos.distanceTo(this.root.position);
      const [d1, d2] = this.root.userData.lodDistance || [12, 30];
      this.setLod(d < d1 ? 0 : d < d2 ? 1 : 2);
    }
  }
}

// Test hook for the house (index.html ?invaders=...): stands invaders in the level playing clips.
// spec: ';'-separated 'x,z,rotDeg,Clip[,Weapon,Outfit,head[,y]]' (glTF metres; rot 0 faces +Z), e.g.
//   ?invaders=-2,12.5,0,AimRifle,Rifle,Navy,cap;2,13,-20,Search,,Olive,hood;0,11.5,0,Walk
// Returns { invaders, update(dt, camPos) }. Lighting: the scene environment (not the rooms' probes).
export async function placeInvaders(scene, loader, url, spec, envMap = null) {
  const asset = await InvaderAsset.load(loader, url);
  await asset.preloadOutfits();
  const invaders = spec.split(';').filter(Boolean).map((part) => {
    const [x, z, rot = '0', clip = 'Idle', weapon = '', outfit = '', head = 'none', y = '0'] = part.split(',');
    const inv = asset.spawn({ outfit: outfit || undefined, head, weapon: weapon || null });
    inv.root.position.set(+x, +y, +z);
    inv.root.rotation.y = THREE.MathUtils.degToRad(+rot);
    if (envMap) inv.root.traverse((o) => { if (o.isMesh) for (const m of [o.material].flat()) m.envMap = envMap; });
    scene.add(inv.root);
    inv.play(clip, { fade: 0 });
    return inv;
  });
  window.__invaders = invaders;
  return { invaders, asset, update: (dt, camPos) => { for (const i of invaders) i.update(dt, camPos); } };
}
