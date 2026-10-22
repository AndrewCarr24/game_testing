import * as THREE from 'three';
import { GATE, OFFSET_Z, STATE_KEY, splitGateLeaves, setLeaves, plain, linkRegistry, splitOuterLawn, HAY_GLSL } from './estate_link.js';
import { ROAD_SURFACE } from './wild/road.js';

// The house's side of the gate (viewer/estate_link.js has the design). The drive's sliding gate
// (drive_gate zone: two slatted steel leaves, baked into the grounds mesh) is split out of the
// grounds and opens by itself as the player comes down the drive toward it (an exit sensor, as
// on any electric estate gate). Opening it starts loading the wilderness (wild.html in a hidden,
// full-window iframe; ~1-3 s, while the leaves run); walking out through it suspends the house
// and hands the player to the wilderness. They come back the same way.
//   ?wild=0   the gate opens but leads nowhere (the old dead end)
//   ?wildq=N  the wilderness's quality level (wild.html ?q)

export class EstateGate {
  constructor({ scene, camera, player, controls, inventory, flashlight, colliders, renderer, params, toast }) {
    Object.assign(this, { scene, camera, player, controls, inventory, flashlight, colliders, renderer, params, toast });
    this.t = 0;                      // leaves: 0 shut .. 1 open
    this.opening = false;
    this.frame = null;               // the wilderness iframe
    this.ready = false;
    this.inWild = false;
    this.armed = true;               // re-armed once the player is back inside the drive
    this.reg = linkRegistry();
    const flat = scene.getObjectByName('Mansion_Outdoor_Flat');
    this.leaves = flat ? splitGateLeaves(flat) : null;
    // the leaves' colliders (grounds 'solid' boxes in the leaf line): gone once the gate is open
    this.leafBoxes = colliders.filter((c) => c.kind === 'solid' && c.min.x > GATE.x0 - 0.3 && c.max.x < GATE.x1 + 0.3
      && c.max.z > GATE.z - 0.3 && c.min.z < GATE.z + 0.3 && c.max.y < 3.2);
    this.hay = this.outerLawn(scene);
    this.road = null;
    this.countyRoad(scene).then((m) => (this.road = m)).catch(() => {});
    // the house's own systems that cross with the player
    this.reg.provide('house_flashlight', () => ({ on: flashlight?.on ?? false, battery: flashlight?.battery ?? 1 }));
    this.reg.returnFromWild = (state) => this.fromWild(state);
    window.__estateGate = this;
    // arriving from a stand-alone wild.html (it navigated here): stand inside the open gate
    try {
      const s = sessionStorage.getItem(STATE_KEY);
      if (s && params.get('from') === 'wild') {
        sessionStorage.removeItem(STATE_KEY);
        this.t = 1; this.opened();
        this.place(JSON.parse(s));
      }
    } catch { /* no storage: fine */ }
  }

  // the lawn beyond the hedge is the wilderness's hay meadow (estate_link.js splitOuterLawn): the
  // same baked texture x vertex colour, no mowing stripes, June greens toward straw
  outerLawn(scene) {
    const lawn = scene.getObjectByName('Mansion_Outdoor_Lawn');
    if (!lawn || !lawn.material?.map) return null;
    const src = lawn.material;
    const m = new THREE.MeshBasicMaterial({ map: src.map, vertexColors: true, color: src.color.clone(), name: 'M_Grounds_Hay' });
    m.onBeforeCompile = (sh) => {
      sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying vec2 vHay;')
        .replace('#include <project_vertex>', '#include <project_vertex>\nvHay = (modelMatrix * vec4(transformed, 1.0)).xz;');
      sh.fragmentShader = sh.fragmentShader.replace('#include <common>', `#include <common>\nvarying vec2 vHay;\n${HAY_GLSL}`)
        .replace('#include <map_fragment>', '#include <map_fragment>\ndiffuseColor.rgb = hay(diffuseColor.rgb, vHay);');
    };
    m.customProgramCacheKey = () => 'hay';
    return splitOuterLawn(lawn, m);
  }

  // the county road's first stretch, from the gate to the lawn's edge (beyond it the horizon band
  // has it): the wilderness's slab (wild/road.js ROAD_SURFACE), lit by the level's sun and sky
  async countyRoad(scene) {
    const R = await (await fetch('../build/wilderness/laurel_fork/world/road.json')).json();
    const lv = window.__level, sun = lv?.lights?.find((l) => l.type === 'sun'), sky = lv?.sky;
    const P = R.points.map((p) => new THREE.Vector3(p[0], p[1], p[2] - OFFSET_Z)).filter((p) => p.z > GATE.z - 1 && Math.abs(p.x) < 90 && p.z < 80.5);
    if (P.length < 2) return null;
    const half = R.paved / 2, W = half + R.shoulder, across = [-W - 0.25, -half, 0, half, W + 0.25], drop = [-0.12, 0, 0, 0, -0.12];
    const pos = [], uv = [], idx = [];
    let s = 0;
    P.forEach((p, i) => {
      if (i) s += p.distanceTo(P[i - 1]);
      const a = P[Math.max(0, i - 1)], b = P[Math.min(P.length - 1, i + 1)];
      const t = new THREE.Vector3(b.x - a.x, 0, b.z - a.z).normalize(), r = new THREE.Vector3(-t.z, 0, t.x);
      across.forEach((o, k) => { pos.push(p.x + r.x * o, p.y + 0.05 + drop[k], p.z + r.z * o); uv.push(o, s); });
    });
    const n = across.length;
    for (let i = 0; i < P.length - 1; i++) for (let k = 0; k < n - 1; k++) { const a = i * n + k; idx.push(a, a + 1, a + n, a + 1, a + n + 1, a + n); }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
    g.setIndex(idx);
    const sd = new THREE.Vector3(...(sun?.direction || [0.94, -0.32, -0.12])).normalize().negate();
    const light = new THREE.Color(...(sun?.color || [1, 0.7, 0.45])).multiplyScalar(((sun?.intensity || 6) / Math.PI) * Math.max(0, sd.y))
      .add(new THREE.Color(...(sky?.light || [0.42, 0.52, 0.72])).multiplyScalar(sky?.light_strength ?? 0.85));
    const mat = new THREE.ShaderMaterial({
      uniforms: { uHalf: { value: half }, uJoint: { value: R.joint || 4.5 }, uLight: { value: light } },
      vertexShader: 'varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      fragmentShader: `uniform float uHalf, uJoint; uniform vec3 uLight; varying vec2 vUv;
        ${ROAD_SURFACE}
        void main() { gl_FragColor = vec4(roadSurface(vUv, uHalf, uJoint) * uLight, 1.0);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }`,
      polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2,
    });
    const m = new THREE.Mesh(g, mat);
    m.name = 'Mansion_CountyRoad';
    scene.add(m);
    return m;
  }

  // ---- each house frame
  update(dt) {
    const p = this.player.pos;
    const inDrive = p.x > 12 && p.x < 28 && p.z > 46 && p.z < GATE.line + 0.5;
    const near = inDrive && p.z > GATE.z - 10;
    if (near && this.t < 1 && !this.opening && !window.__bench) { this.opening = true; this.preload(); }
    if (this.opening && this.t < 1) {
      this.t = Math.min(1, this.t + dt / 3.0);
      setLeaves(this.leaves, this.t);
      if (this.t >= 1) this.opened();
      this.renderer.shadowMap.needsUpdate = true;
    }
    if (p.z < GATE.z - 2) this.armed = true;
    // out through the gate
    if (this.t >= 1 && this.armed && p.z > GATE.line && p.x > GATE.mouth[0] && p.x < GATE.mouth[1] && this.params.get('wild') !== '0') this.toWild();
  }

  opened() {
    setLeaves(this.leaves, 1);
    for (const b of this.leafBoxes) { b.min.set(0, -101, 0); b.max.set(0, -100, 0); }
  }

  // the wilderness, loaded once into a hidden full-window iframe and kept (paused while unseen)
  preload() {
    if (this.frame || this.params.get('wild') === '0') return;
    const f = document.createElement('iframe');
    const q = this.params.get('wildq');
    f.src = `wild.html?world=laurel_fork&embed=1&hud=0${q ? `&q=${q}` : ''}`;
    Object.assign(f.style, { position: 'fixed', inset: '0', width: '100%', height: '100%', border: '0', opacity: '0',
      pointerEvents: 'none', zIndex: '50', transition: 'opacity 0.35s', background: 'transparent' });
    f.allow = 'pointer-lock';
    document.body.appendChild(f);
    this.frame = f;
    this.loadStart = performance.now();
    const poll = () => {
      const w = f.contentWindow;
      if (w?.__loaded && w.__wildGate) {
        this.ready = true;
        this.loadMs = Math.round(performance.now() - this.loadStart);
        if (!this.inWild) w.__wildGate.suspend();
        return;
      }
      setTimeout(poll, 100);
    };
    poll();
  }

  state() {
    const p = this.player, inv = this.inventory;
    return {
      from: 'house', t: performance.now(),
      player: { pos: p.pos.toArray(), vel: p.vel.toArray(), crouch: !!p.crouching, quat: this.camera.quaternion.toArray() },
      inventory: inv ? [...inv.items].map(([id, it]) => ({ id, name: it.name, count: it.count, def: plain(it.def) })) : [],
      armed: inv?.armed ?? null,
      extra: this.reg.collect(),
    };
  }

  // ---- out: the house suspends, the wilderness takes the player
  toWild() {
    if (this.inWild) return;
    this.inWild = true;
    const go = () => {
      const w = this.frame.contentWindow;
      const s = this.state();
      s.player.pos[2] += OFFSET_Z;
      w.__wildGate.arrive(s);
      window.__suspended = true;                       // index.html's loop: no frames, no update
      window.dispatchEvent(new Event('blur'));         // (the house lets go of the keys held)
      window.__sfx?.ctx?.suspend?.();
      this.frame.style.opacity = '1';
      this.frame.style.pointerEvents = 'auto';
      this.forward(true);
      this.crossedAt = performance.now();
    };
    if (this.ready) go();
    else {                                             // (not loaded yet: hold at the gate, dimmed)
      this.waiting = true;
      document.body.style.transition = 'filter 0.4s'; document.body.style.filter = 'brightness(0.35)';
      const wait = () => (this.ready ? (document.body.style.filter = '', this.waiting = false, go()) : setTimeout(wait, 100));
      wait();
    }
  }

  // ---- back: called by the wilderness (its gate) with its state
  fromWild(state) {
    if (!this.inWild) return;
    this.forward(false);
    this.frame.contentWindow.__wildGate.suspend();
    try { this.frame.contentDocument.exitPointerLock?.(); } catch { /* */ }
    this.frame.style.opacity = '0';
    this.frame.style.pointerEvents = 'none';
    this.place(state);
    window.__suspended = false;
    window.__sfx?.ctx?.resume?.();
    this.inWild = false;
    this.armed = false;
    this.renderer.shadowMap.needsUpdate = true;
    // (the wilderness's key presses count as user activation for this page too: relock)
    if (!this.controls.isLocked) try { this.controls.lock(); } catch { /* the next click does */ }
  }

  place(state) {
    const s = state.player, p = this.player;
    p.pos.set(s.pos[0], Math.max(s.pos[1], -0.08), Math.min(s.pos[2] - OFFSET_Z, GATE.back - 0.1));
    p.vel.set(...(s.vel || [0, 0, 0]));
    p.syncCamera?.();
    if (s.quat) this.camera.quaternion.fromArray(s.quat);
    this.reg.deliver(state.extra);
  }

  // while the wilderness is up and this page holds the pointer lock: its keys and mouse go there
  forward(on) {
    const w = () => this.frame?.contentWindow;
    if (on && !this._fw) {
      const key = (e) => {
        const cw = w();
        if (!cw || !window.__suspended) return;
        e.stopImmediatePropagation(); e.preventDefault();
        cw.dispatchEvent(new cw.KeyboardEvent(e.type, { code: e.code, key: e.key, repeat: e.repeat, bubbles: true }));
        if (e.type === 'keydown') this.downKeys.add(e.code); else this.downKeys.delete(e.code);
      };
      const move = (e) => { if (window.__suspended && document.pointerLockElement) w()?.__wildGate?.look(e.movementX, e.movementY); };
      this.downKeys = new Set();
      this._fw = { key, move };
      addEventListener('keydown', key, true); addEventListener('keyup', key, true);
      document.addEventListener('mousemove', move, true);
    } else if (!on && this._fw) {
      removeEventListener('keydown', this._fw.key, true); removeEventListener('keyup', this._fw.key, true);
      document.removeEventListener('mousemove', this._fw.move, true);
      const cw = w();
      for (const code of this.downKeys || []) cw?.dispatchEvent(new cw.KeyboardEvent('keyup', { code, bubbles: true }));
      this._fw = null;
    }
  }
}
