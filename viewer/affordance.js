import * as THREE from 'three';

// Affordance: making what's usable readable, without spoiling the realistic look.
//   Highlight   the interactable in focus (what E acts on) gets a faint fresnel rim: overlay
//               meshes that share its geometry, additive, drawn in the main pass (no extra
//               full-screen pass). Only while playing (pointer locked), so a few draw calls at most.
//   Glints      usable things within a few metres twinkle briefly now and then, like light
//               catching an edge: one Points draw call for the whole house; walls and closed
//               drawers hide them (depth test). Frozen under window.__bench (shots repeat).
//   cue(it)     the crosshair's state for the focus: take / use / blocked (locked, needs an
//               item, a switch that can't go on) / armed (the armed item works on it).
//   itemInfo()  what an inventory item is FOR (one plain line, no story) and a small icon.
//               An asset may author `purpose` in its pickup definition; otherwise the line
//               comes from the table below or from what the item does (throwable, a `use` point
//               that needs it, a lock it fits).

const GLINT = { pickup: 1.0, use: 0.85, switch: 0.55, slide: 0.55 };   // rotate (doors, appliance doors): no glint
const GLINT_NEAR = 2.5, GLINT_FAR = 5.0;     // full strength inside NEAR, gone at FAR (m from the eye)
const MAX_GLINTS = 32;
const REFRESH = 0.2;                         // s between picks of which things glint
const truthy = (v) => v === true || v === 1 || v === 'true' || v === '1';
const shown = (o) => { for (; o; o = o.parent) if (!o.visible) return false; return true; };

const RIM_VERT = /* glsl */ `
  varying vec3 vN; varying vec3 vV;
  void main() {
    vec4 wp = modelMatrix * vec4(position, 1.0);
    vN = normalize(mat3(modelMatrix) * normal);
    vV = cameraPosition - wp.xyz;
    gl_Position = projectionMatrix * viewMatrix * wp;
  }`;
// Blending: out = rgb + dst * a (CustomBlending One / SrcAlpha). a > 1 brightens what's already
// there (the scene renders into a half-float target, where blend factors aren't clamped), so the
// rim reads in proportion to the room's light: strong in a lit room, not a ghost in a dark one;
// rgb is a small absolute lift so the outline still shows in the dark. Drawn straight to an
// 8-bit canvas (fx off), a clamps to 1 and only the small lift remains.
const RIM_FRAG = /* glsl */ `
  uniform vec3 uColor; uniform float uStrength; uniform float uGain; uniform float uTime;
  varying vec3 vN; varying vec3 vV;
  void main() {
    float ndv = abs(dot(normalize(vN), normalize(vV)));
    float rim = pow(1.0 - ndv, 2.5);
    float breathe = 0.7 + 0.3 * sin(uTime * 3.4);
    float r = breathe * (0.3 + 0.7 * rim);
    gl_FragColor = vec4(uColor * uStrength * r, 1.0 + uGain * r);
    #include <colorspace_fragment>
  }`;

const GLINT_VERT = /* glsl */ `
  attribute float aSeed; attribute float aLift; attribute float aFade;
  uniform float uTime; uniform float uScale;
  varying float vA;
  void main() {
    vec4 wp = modelMatrix * vec4(position, 1.0);
    wp.xyz += normalize(cameraPosition - wp.xyz) * aLift;      // just in front of the thing's surface
    vec4 mv = viewMatrix * wp;
    gl_Position = projectionMatrix * mv;
    // a short twinkle every ~4 s, each thing on its own beat
    float ph = fract(uTime / 4.2 + aSeed);
    float tw = smoothstep(0.0, 0.07, ph) * (1.0 - smoothstep(0.07, 0.2, ph));
    vA = tw * aFade;
    gl_PointSize = vA > 0.002 ? clamp(uScale * 0.055 / -mv.z, 7.0, 30.0) * (0.55 + 0.45 * tw) : 0.0;
  }`;
const GLINT_FRAG = /* glsl */ `
  uniform float uBright;
  varying float vA;
  void main() {
    vec2 p = gl_PointCoord * 2.0 - 1.0;
    float r = length(p);
    float core = exp(-r * r * 22.0);
    float rays = (exp(-abs(p.x) * 16.0) * exp(-abs(p.y) * 3.0) + exp(-abs(p.y) * 16.0) * exp(-abs(p.x) * 3.0)) * max(0.0, 1.0 - r);
    float a = (core + 0.55 * rays) * vA * uBright;
    gl_FragColor = vec4(vec3(1.0, 0.95, 0.86) * a, 1.0);
    #include <colorspace_fragment>
  }`;

export class Affordance {
  constructor({ scene, camera, renderer, interact, inventory }) {
    Object.assign(this, { scene, camera, renderer, interact, inventory });
    this.time = { value: 0 };
    this.focus = null;
    this.overlays = [];        // [{mesh, src}]
    this._t = REFRESH;         // refresh the glints on the first frame
    const rim = (side) => new THREE.ShaderMaterial({
      uniforms: { uColor: { value: new THREE.Color(1.0, 0.93, 0.8) }, uStrength: { value: 1 }, uGain: { value: 1 }, uTime: this.time },
      vertexShader: RIM_VERT, fragmentShader: RIM_FRAG, side,
      transparent: true, depthWrite: false, depthFunc: THREE.LessEqualDepth,
      blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.OneFactor, blendDst: THREE.SrcAlphaFactor,
      blendSrcAlpha: THREE.ZeroFactor, blendDstAlpha: THREE.OneFactor,
      polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -2, toneMapped: false,
    });
    this.rim = { [THREE.FrontSide]: rim(THREE.FrontSide), [THREE.DoubleSide]: rim(THREE.DoubleSide), [THREE.BackSide]: rim(THREE.BackSide) };
    // the glints: one Points object, attributes rewritten at each refresh
    const g = new THREE.BufferGeometry();
    this.gPos = new Float32Array(MAX_GLINTS * 3);
    this.gSeed = new Float32Array(MAX_GLINTS); this.gLift = new Float32Array(MAX_GLINTS); this.gFade = new Float32Array(MAX_GLINTS);
    g.setAttribute('position', new THREE.BufferAttribute(this.gPos, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aSeed', new THREE.BufferAttribute(this.gSeed, 1).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aLift', new THREE.BufferAttribute(this.gLift, 1).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aFade', new THREE.BufferAttribute(this.gFade, 1).setUsage(THREE.DynamicDrawUsage));
    g.setDrawRange(0, 1);
    this.glintMat = new THREE.ShaderMaterial({
      uniforms: { uTime: this.time, uScale: { value: 700 }, uBright: { value: 1.25 } },
      vertexShader: GLINT_VERT, fragmentShader: GLINT_FRAG,
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false,
    });
    this.glints = new THREE.Points(g, this.glintMat);
    this.glints.name = 'Affordance_Glints';
    this.glints.frustumCulled = false;
    this.glints.renderOrder = 10;
    scene.add(this.glints);
    // compile both shaders in the first frames (a hitch at the first focus otherwise): a
    // degenerate triangle with the rim material, the Points with one invisible point
    const warm = new THREE.BufferGeometry();
    warm.setAttribute('position', new THREE.BufferAttribute(new Float32Array(9), 3));
    warm.setAttribute('normal', new THREE.BufferAttribute(new Float32Array([0, 1, 0, 0, 1, 0, 0, 1, 0]), 3));
    this.warm = new THREE.Mesh(warm, this.rim[THREE.FrontSide]);
    this.warm.frustumCulled = false;
    scene.add(this.warm);
    this.warmFrames = 3;
    const q = new URLSearchParams(location.search);
    this.enabled = q.get('afford') !== '0';     // ?afford=0: compare without
    this.rimK = +(q.get('rim') ?? 0.05);         // ?rim=k: the highlight's absolute lift (tuning)
    this.rimGain = +(q.get('rimgain') ?? 2.0);   // ?rimgain=g: how much it brightens what's lit
    this.glintMat.uniforms.uBright.value = +(q.get('glint') ?? 1.25);
  }

  // ------------------------------------------------------------------ the focus highlight
  setFocus(it) {
    if (it === this.focus) return;
    for (const o of this.overlays) this.scene.remove(o.mesh);
    this.overlays = [];
    this.focus = it;
    if (!it || !this.enabled) return;
    const meshes = this.meshesOf(it);
    // the rim is about the object's edges: a vase can glow, a door leaf barely
    const size = this.interact.boxOf(it).getSize(new THREE.Vector3()).length();
    const k = THREE.MathUtils.clamp(0.45 / Math.max(size, 0.01), 0.3, 1.0);
    for (const m of Object.values(this.rim)) { m.uniforms.uStrength.value = this.rimK * k; m.uniforms.uGain.value = this.rimGain * k; }
    for (const src of meshes) {
      // outer surface only: a glass vase's inner wall would double the rim
      const side = src.material.side === THREE.DoubleSide && !src.material.transparent ? THREE.DoubleSide : THREE.FrontSide;
      const mesh = new THREE.Mesh(src.geometry, this.rim[side]);
      // a child of the scene (identity), so its local matrix is the source's world matrix; not a
      // child of the item: the hand and thrown copies clone the item's node
      mesh.matrixAutoUpdate = false;
      mesh.castShadow = mesh.receiveShadow = false;
      mesh.renderOrder = 10;
      mesh.name = 'Affordance_Rim';
      mesh.matrix.copy(src.matrixWorld);
      this.scene.add(mesh);
      this.overlays.push({ mesh, src });
    }
  }

  // the meshes that show the thing: its own node's; an empty (the breaker's fuse slot) borrows
  // the small visible meshes of its asset that overlap where it is
  meshesOf(it) {
    const out = [];
    const ok = (o) => o.isMesh && !o.isSkinnedMesh && !o.isInstancedMesh && !Array.isArray(o.material) && o.geometry?.attributes.normal;
    it.node.traverse((o) => { if (ok(o) && o.visible && o.material.visible) out.push(o); });
    if (out.length) return out;
    const box = this.interact.boxOf(it).clone().expandByScalar(0.03), b = new THREE.Box3(), s = new THREE.Vector3();
    it.root.traverse((o) => {
      if (!ok(o) || !o.visible || !o.material.visible) return;
      b.setFromObject(o);
      if (b.intersectsBox(box) && b.getSize(s).length() < 0.5) out.push(o);
    });
    return out;
  }

  // ------------------------------------------------------------------ per frame
  // focus: what E acts on (null while not playing); eye: the camera position
  update(dt, focus, eye) {
    this.time.value = window.__bench ? 0.35 : this.time.value + dt;
    if (this.warmFrames > 0 && --this.warmFrames === 0) { this.scene.remove(this.warm); }
    this.setFocus(focus);
    for (const { mesh, src } of this.overlays) {
      src.updateWorldMatrix(true, false);
      mesh.matrix.copy(src.matrixWorld);                // follows a drawer / door as it moves
      mesh.matrixWorldNeedsUpdate = true;
      mesh.visible = shown(src) && src.material.visible;
    }
    this._t += dt;
    if (this._t >= REFRESH || window.__bench) { this._t = 0; this.refreshGlints(eye); }
  }

  refreshGlints(eye) {
    const size = this.renderer.getDrawingBufferSize(new THREE.Vector2());
    this.glintMat.uniforms.uScale.value = size.y / (2 * Math.tan(THREE.MathUtils.degToRad(this.camera.fov) / 2));
    const cands = [];
    if (this.enabled && eye) {
      const wp = new THREE.Vector3();
      for (const it of this.interact.items) {
        const w = GLINT[it.def.type];
        if (!w || it === this.focus || !this.interact.available(it)) continue;
        if (it.locked) continue;
        if (it.def.type === 'use' && this.interact.done(it)) continue;
        const d0 = it.node.getWorldPosition(wp).distanceTo(eye);
        if (d0 > GLINT_FAR + 1.5 || !shown(it.node)) continue;
        const box = this.interact.boxOf(it).clone();
        const c = box.getCenter(new THREE.Vector3());
        const d = c.distanceTo(eye);
        if (d > GLINT_FAR || Math.abs(c.y - eye.y) > 2.4) continue;
        cands.push({ it, box, c, d, w });
      }
      cands.sort((a, b) => a.d - b.d);
    }
    let n = 0;
    for (const { it, box, c, d, w } of cands) {
      if (n >= MAX_GLINTS) break;
      // small things behind the room's wall lining (a switch back to back with this room's)
      if (this.interact.behindWall(eye, box)) continue;
      const s = box.getSize(new THREE.Vector3());
      this.gPos.set([c.x, c.y + s.y * 0.25, c.z], n * 3);     // nearer the top, where light catches
      this.gSeed[n] = seedOf(it);
      this.gLift[n] = Math.min(0.5 * Math.max(s.x, s.z), 0.22) + 0.01;
      this.gFade[n] = w * (1 - THREE.MathUtils.smoothstep(d, GLINT_NEAR, GLINT_FAR));
      n++;
    }
    const g = this.glints.geometry;
    for (const k of ['position', 'aSeed', 'aLift', 'aFade']) g.attributes[k].needsUpdate = true;
    if (this.warmFrames > 0 && n === 0) { this.gFade[0] = 0; n = 1; }   // (compile the shader)
    g.setDrawRange(0, n);
    this.glints.visible = n > 0;
  }

  // ------------------------------------------------------------------ the crosshair's state
  // 'take' (a pickup), 'use' (E does something), 'blocked' (locked, needs an item, can't be
  // switched on), 'armed' (the armed item works on it, Enter), null (nothing in focus)
  cue(it, armed) {
    if (!it) return null;
    const d = it.def, inv = this.inventory, sig = this.interact.signals;
    if (it.locked) return armed && armed === it.lockKey ? 'armed' : 'blocked';
    if (d.type === 'pickup') return 'take';
    if (d.type === 'use') {
      if (this.interact.done(it)) return 'done';
      if (!d.needs) return 'use';
      return inv.armed === d.needs ? 'armed' : 'blocked';
    }
    if (d.type === 'switch' && !truthy(sig.get(it.signal)) && d.requires && !truthy(sig.get(d.requires))) return 'blocked';
    return 'use';
  }

  // a second, smaller line under the prompt: what a pickup is for
  subline(it) {
    if (!it || it.def.type !== 'pickup') return '';
    return itemInfo(it.def.item, { name: it.def.name, def: it.def }, this.interact).purpose;
  }
}

function seedOf(it) {
  const s = it.node.uuid;
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return (h % 1000) / 1000;
}

// ------------------------------------------------------------------ items: purpose + icon
// One plain line: what the item does for the player, and how (keys are named as the game
// takes them: I opens the inventory, Enter uses the armed item).
const PURPOSE = {
  keycard: 'Unlocks the keycard door: arm it, then press Enter at the door.',
  flashlight: 'A torch for dark rooms: arm it, Enter switches it on and off. A battery lasts about 4 minutes.',
  battery: 'A fresh battery for the flashlight: arm it and press Enter to swap it in.',
  fuse: 'The main fuse for the breaker panel in the garage: arm it and press Enter at the panel.',
  tablet: 'Smart-home control: arm it and press Enter for room lights, blinds and the security cameras.',
  car_key: 'The key to the car in the garage.',
};

const SVG = (body) => `<svg class="ico" viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">${body}</svg>`;
const ICONS = {
  keycard: SVG('<rect x="2.5" y="5" width="15" height="10" rx="1.5"/><path d="M12.5 5v10" stroke-width="2.4" stroke="#4f7fe0"/><path d="M5 12h4"/>'),
  key: SVG('<circle cx="6" cy="10" r="3.2"/><path d="M9.2 10h8M15 10v2.6M12.6 10v2"/>'),
  flashlight: SVG('<path d="M3 8h8.5l3-2.2v8.4l-3-2.2H3z"/><path d="M16.5 7.5l1.6-.9M16.8 10h1.8M16.5 12.5l1.6.9" stroke-width="1.1"/>'),
  battery: SVG('<rect x="2.5" y="6.5" width="13" height="7" rx="1"/><path d="M15.5 8.7h2v2.6h-2"/><path d="M5.5 10h3M7 8.5v3"/>'),
  fuse: SVG('<rect x="6" y="3" width="8" height="14" rx="1.2"/><path d="M6 6h8M6 14h8M10 6v8" stroke-width="1.1"/>'),
  tablet: SVG('<rect x="3.5" y="2.5" width="13" height="15" rx="1.8"/><path d="M8.5 15h3"/>'),
  vase: SVG('<path d="M8 2.8h4M8.5 2.8v3c0 1-3.5 2.5-3.5 6.5 0 3 2 4.9 5 4.9s5-1.9 5-4.9c0-4-3.5-5.5-3.5-6.5v-3"/>'),
  bottle: SVG('<path d="M8.6 2.5h2.8v4.2c0 .8 2.6 1.6 2.6 4.3v6.5H6V11c0-2.7 2.6-3.5 2.6-4.3z"/><path d="M6 12h8" stroke-width="1"/>'),
  book: SVG('<path d="M4 3.5h9.5a2 2 0 0 1 2 2v11H6a2 2 0 0 1-2-2z"/><path d="M4 14.5a2 2 0 0 1 2-2h9.5M7.5 6.5h5"/>'),
  thing: SVG('<path d="M10 2.8l6.5 3.6v7.2L10 17.2l-6.5-3.6V6.4z"/><path d="M3.5 6.4L10 10l6.5-3.6M10 10v7.2"/>'),
};

function iconFor(id, def = {}) {
  if (ICONS[id]) return ICONS[id];
  if (id === 'car_key' || /^key_/.test(id)) return ICONS.key;
  if (/bottle/.test(id)) return ICONS.bottle;
  if (/book/.test(id)) return ICONS.book;
  if (/vase|glass|jar|cup|bowl|carafe/.test(id) || (def.throwable && def.shatter !== false && def.shatter !== 0)) return ICONS.vase;
  if (def.throwable) return ICONS.book;
  return ICONS.thing;
}

// "IX_BreakerPanel" -> "breaker panel"
const pretty = (name) => String(name ?? '').replace(/^IX_/, '').replace(/_/g, ' ').replace(/([a-z])([A-Z])/g, '$1 $2').trim().toLowerCase();

// entry: {name, def} (an inventory entry or a pickup's definition)
export function itemInfo(id, entry = {}, interact = null) {
  const def = entry.def ?? {};
  let purpose = def.purpose ?? PURPOSE[id];
  if (!purpose && def.throwable) {
    purpose = def.shatter === false || def.shatter === 0
      ? 'Throw it with Enter: it lands with a thud, a distraction where it falls. Pick it up again after.'
      : 'Throw it with Enter: it smashes loudly where it lands, a distraction that pulls attention there.';
  }
  if (!purpose && interact) {
    const use = interact.items.find((it) => it.def.type === 'use' && it.def.needs === id);
    if (use) purpose = `For the ${pretty(use.root?.name) || 'thing that needs it'}: arm it, then press Enter there (${(use.def.prompt || 'use').toLowerCase()}).`;
    else if (interact.items.some((it) => it.lockKey === id)) purpose = 'Locks and unlocks a door: arm it, then press Enter at the door.';
  }
  if (!purpose && /^key_/.test(id)) purpose = 'Opens a locked door: arm it, then press Enter at the door.';
  return { purpose: purpose ?? 'Something you can carry.', icon: iconFor(id, def) };
}
