import * as THREE from 'three';

// Gunfire you can see (tracers fading over 0.12 s, a muzzle flash quad; no real-time lights) and
// the debug overlay (?invaders=debug): each invader's cone of sight (focal and peripheral), its
// path, a line to where it thinks the player is (red while it sees them), and a label (role,
// state, notice meter) drawn on a 2D canvas over the game.

const TRACERS = 48;

export class InvaderFx {
  constructor(scene, camera, { debug = false } = {}) {
    this.scene = scene; this.camera = camera;
    const pos = new Float32Array(TRACERS * 6), col = new Float32Array(TRACERS * 6);
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('color', new THREE.BufferAttribute(col, 3).setUsage(THREE.DynamicDrawUsage));
    this.lines = new THREE.LineSegments(g, new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    this.lines.frustumCulled = false;
    this.lines.name = 'Invaders_Tracers';
    this.lines.visible = false;
    scene.add(this.lines);
    this.tracers = [];
    // muzzle flashes: camera-facing points
    const fg = new THREE.BufferGeometry();
    fg.setAttribute('position', new THREE.BufferAttribute(new Float32Array(16 * 3), 3).setUsage(THREE.DynamicDrawUsage));
    this.flash = new THREE.Points(fg, new THREE.PointsMaterial({ color: 0xffd38a, size: 0.35, sizeAttenuation: true, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, map: flashTexture() }));
    this.flash.frustumCulled = false;
    this.flash.name = 'Invaders_Flash';
    this.flash.visible = false;
    scene.add(this.flash);
    this.flashes = [];
    if (debug) this.makeDebug();
  }

  tracer(a, b, hit) {
    this.tracers.push({ a: a.clone(), b: b.clone(), t: 0, hit });
    if (this.tracers.length > TRACERS) this.tracers.shift();
    this.flashes.push({ p: a.clone(), t: 0 });
    if (this.flashes.length > 16) this.flashes.shift();
  }

  update(dt, agents = null, sq = null) {
    // tracers
    this.tracers = this.tracers.filter((t) => (t.t += dt) < 0.12);
    const P = this.lines.geometry.attributes.position, C = this.lines.geometry.attributes.color;
    this.tracers.forEach((t, i) => {
      // a short streak travelling along the shot
      const k0 = Math.min(1, t.t / 0.06), k1 = Math.min(1, k0 + 0.35);
      const x0 = t.a.x + (t.b.x - t.a.x) * k0, y0 = t.a.y + (t.b.y - t.a.y) * k0, z0 = t.a.z + (t.b.z - t.a.z) * k0;
      P.setXYZ(i * 2, x0, y0, z0);
      P.setXYZ(i * 2 + 1, t.a.x + (t.b.x - t.a.x) * k1, t.a.y + (t.b.y - t.a.y) * k1, t.a.z + (t.b.z - t.a.z) * k1);
      const f = 1 - t.t / 0.12;
      C.setXYZ(i * 2, 0.5 * f, 0.42 * f, 0.25 * f);
      C.setXYZ(i * 2 + 1, 1.0 * f, 0.85 * f, 0.55 * f);
    });
    this.lines.geometry.setDrawRange(0, this.tracers.length * 2);
    P.needsUpdate = C.needsUpdate = true;
    this.lines.visible = this.tracers.length > 0;
    this.flashes = this.flashes.filter((f) => (f.t += dt) < 0.05);
    const F = this.flash.geometry.attributes.position;
    this.flashes.forEach((f, i) => F.setXYZ(i, f.p.x, f.p.y, f.p.z));
    this.flash.geometry.setDrawRange(0, this.flashes.length);
    F.needsUpdate = true;
    this.flash.visible = this.flashes.length > 0;
    if (agents && this.dbg) this.drawDebug(agents, sq);
  }

  // ---------------------------------------------------------------- debug overlay
  makeDebug() {
    const N = 60000;
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(N * 3), 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(N * 3), 3).setUsage(THREE.DynamicDrawUsage));
    const m = new THREE.LineSegments(g, new THREE.LineBasicMaterial({ vertexColors: true, depthTest: false, transparent: true, opacity: 0.85 }));
    m.frustumCulled = false; m.renderOrder = 10; m.name = 'Invaders_Debug';
    this.scene.add(m);
    const cv = document.createElement('canvas');
    cv.style.cssText = 'position:absolute;inset:0;pointer-events:none;z-index:5';
    document.body.appendChild(cv);
    this.dbg = { m, N, cv, ctx: cv.getContext('2d') };
  }
  drawDebug(agents, sq) {
    const D = this.dbg, P = D.m.geometry.attributes.position, C = D.m.geometry.attributes.color;
    let n = 0;
    const seg = (a, b, c) => {
      if (n + 2 > D.N) return;
      P.setXYZ(n, a.x, a.y, a.z); C.setXYZ(n++, c[0], c[1], c[2]);
      P.setXYZ(n, b.x, b.y, b.z); C.setXYZ(n++, c[0], c[1], c[2]);
    };
    const v = (x, y, z) => new THREE.Vector3(x, y, z);
    const COL = { engage: [1, 0.2, 0.2], chase: [1, 0.3, 0.1], strike: [1, 0, 0], pursue: [1, 0.6, 0.1], search: [1, 0.9, 0.2], investigate: [0.3, 0.8, 1], check: [0.8, 0.4, 1],
      sweep: [0.5, 1, 0.5], post: [0.4, 0.7, 0.4], hold: [0.6, 0.6, 1], respond: [1, 0.7, 0.4], arrive: [0.7, 0.7, 0.7], breach: [1, 0.2, 0.8], flee: [0.9, 0.9, 0.9], cover: [1, 0.5, 0.5], dead: [0.3, 0.3, 0.3], idle: [0.5, 0.5, 0.5] };
    for (const a of agents) {
      if (!a.alive) continue;
      const col = COL[a.state] ?? [1, 1, 1], e = a.eyePos();
      // cones (focal: the state's colour; peripheral: dim), 8 m long
      for (const [half, R, k] of [[0.96, 8, 1], [1.75, 4, 0.4]]) {
        const c2 = col.map((x) => x * k);
        let prev = null;
        for (let i = 0; i <= 8; i++) {
          const ang = a.lookYaw - half + (2 * half * i) / 8;
          const p = v(e.x + Math.sin(ang) * R, e.y - 0.2, e.z + Math.cos(ang) * R);
          if (i === 0 || i === 8) seg(e, p, c2);
          if (prev) seg(prev, p, c2);
          prev = p;
        }
      }
      // the path
      if (a.path) {
        let prev = v(a.pos.x, a.pos.y + 0.1, a.pos.z);
        for (let i = a.pathI; i < a.path.length; i++) {
          const w = a.path[i], y = w.layer === 'upper' ? 4.7 : w.layer === 'stair' ? sq.world.nav.rampH(w.x) + 0.1 : 0.1;
          const p = v(w.x, y, w.z);
          seg(prev, p, w.door ? [1, 0.3, 1] : [0.3, 0.9, 1]);
          prev = p;
        }
      }
      // where it thinks the player is
      if (a.know && a.time - a.know.t < 20) seg(e, v(a.know.pos.x, a.know.pos.y + 1, a.know.pos.z), a.seenNow ? [1, 0, 0] : [0.6, 0.3, 0.3]);
    }
    D.m.geometry.setDrawRange(0, n);
    P.needsUpdate = C.needsUpdate = true;
    // labels
    const cv = D.cv, ctx = D.ctx, W = innerWidth, H = innerHeight;
    if (cv.width !== W || cv.height !== H) { cv.width = W; cv.height = H; }
    ctx.clearRect(0, 0, W, H);
    ctx.font = '11px ui-monospace, monospace';
    ctx.textAlign = 'center';
    const p = new THREE.Vector3();
    for (const a of agents) {
      p.set(a.pos.x, a.pos.y + 2.05, a.pos.z).project(this.camera);
      if (p.z > 1 || Math.abs(p.x) > 1.1 || Math.abs(p.y) > 1.1) continue;
      const x = (p.x * 0.5 + 0.5) * W, y = (-p.y * 0.5 + 0.5) * H;
      const txt = `${a.isLeader ? '*' : ''}${a.role} ${a.state}${a.alive ? ` ${Math.round(a.aware * 100)}% ${a.health}` : ''}`;
      ctx.fillStyle = 'rgba(0,0,0,.55)';
      const w = ctx.measureText(txt).width + 8;
      ctx.fillRect(x - w / 2, y - 11, w, 14);
      ctx.fillStyle = a.seenNow ? '#ff6b5b' : a.alive ? '#e8e8e8' : '#888';
      ctx.fillText(txt, x, y);
    }
    ctx.textAlign = 'left';
    ctx.fillStyle = 'rgba(0,0,0,.55)'; ctx.fillRect(8, H - 60, 330, 22);
    ctx.fillStyle = '#fff';
    const s = sq.summary();
    ctx.fillText(`invaders ${s.alive} alive · alert ${s.alert} · ${s.msPerFrame} ms/frame · plans ${s.stats.plans}`, 14, H - 45);
  }
}

function flashTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 32;
  const g = c.getContext('2d'), r = g.createRadialGradient(16, 16, 0, 16, 16, 16);
  r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(0.3, 'rgba(255,220,150,.8)'); r.addColorStop(1, 'rgba(255,160,60,0)');
  g.fillStyle = r; g.fillRect(0, 0, 32, 32);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
