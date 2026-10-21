import * as THREE from 'three';

// The smart-home tablet (item "tablet"; armed + Enter opens it). A HUD panel driven by the
// keyboard like the inventory: ↑/↓ choose a row, ←/→ choose within it, Enter toggles, I (or
// Esc, which also releases the mouse) closes. Two pages:
//   Rooms    every room with a lights_<room> or blinds_<room> signal in the level, with its
//            toggles (setting the signal, exactly like the wall switch)
//   Devices  the hub's noisy devices (viewer/devices.js: TV, speaker, doorbell chime, blender,
//            alarm clock): Enter switches one on / off, wherever the player is (distractions)
//   Cameras  one security-camera feed at a time: the scene from a fixed camera rendered at
//            320x180, ~5 times a second, into a canvas in the panel. Cameras come from the
//            level (mansion.json "cameras": [{name, position, lookAt, fov?}]) or, without
//            them, the defaults below (great room, entry, courtyard, kitchen).
// The hub needs house power: with `power` off the pages are offline (and nothing renders).
//
// The feed is drawn into a corner of the main canvas before the frame (so it gets the same
// tone mapping and colour output as the game), copied into the panel's canvas, then the
// frame draws over it. The room culler is pointed at the feed camera for that render (else
// rooms far from the player would show bare walls) and back; the shadow map isn't redrawn.

const FEED_W = 320, FEED_H = 180;

// [room, corner (0..3 = x0z0, x1z0, x1z1, x0z1), label]
const DEFAULT_CAMS = [
  ['great_room', 2, 'Great room'], ['entry', 1, 'Entry'], ['courtyard', 0, 'Courtyard'], ['kitchen', 3, 'Kitchen'],
];

export const roomLabel = (room) => {
  const dirs = { n: 'north', s: 'south', e: 'east', w: 'west' };
  const m = room.match(/^(u?)gallery_([nsew])$/);
  if (m) return `${m[1] ? 'Upper' : 'Gallery'} ${m[1] ? 'gallery ' : ''}${dirs[m[2]]}`;
  const s = room.replace(/_/g, ' ');
  return s[0].toUpperCase() + s.slice(1);
};

export function feedCameras(level) {
  const out = [];
  const make = (name, pos, look, fov = 70) => {
    const cam = new THREE.PerspectiveCamera(fov, FEED_W / FEED_H, 0.1, 120);
    cam.position.set(...pos);
    cam.lookAt(...look);
    cam.updateMatrixWorld();
    return { name, camera: cam };
  };
  if (Array.isArray(level.cameras) && level.cameras.length) {
    for (const c of level.cameras) out.push(make(c.name ?? c.label ?? `Camera ${out.length + 1}`, c.position, c.lookAt, c.fov));
    return out;
  }
  for (const [room, corner, label] of DEFAULT_CAMS) {
    const r = level.rooms?.[room];
    if (!r) continue;
    const [x0, z0, x1, z1] = r.rect, inset = 0.6;
    const x = corner === 1 || corner === 2 ? x1 - inset : x0 + inset;
    const z = corner >= 2 ? z1 - inset : z0 + inset;
    const y = r.floor + Math.min(r.height - 0.4, 3.6);
    out.push(make(label, [x, y, z], [(x0 + x1) / 2, r.floor + 0.8, (z0 + z1) / 2]));
  }
  return out;
}

export class Tablet {
  // hide: objects not to show in the feed (the player's held item)
  constructor({ renderer, scene, camera, level, signals, culler = null, hide = [], el, fps = 5, devices = null }) {
    Object.assign(this, { renderer, scene, camera, level, signals, culler, hide, el, fps, devices });
    this.open = false;
    this.page = 'rooms';
    this.row = 1;
    this.col = 0;
    this.cam = 0;
    this.msg = '';
    this.cams = feedCameras(level);
    this.canvas = document.createElement('canvas');
    this.canvas.width = FEED_W; this.canvas.height = FEED_H;
    this.canvas.className = 'feed';
    this.ctx = this.canvas.getContext('2d');
    this._acc = 0;
    this._last = 0;
    this.frames = 0;            // feed frames rendered (tests, cost checks)
    this.lastFeedMs = 0;        // CPU time of the last feed render
    this.feedCalls = 0;         // draw calls of the last feed render
    signals.on('*', () => this.open && this.draw());
  }

  // rooms with toggles, in the level's room order: [{room, lights?, blinds?}]
  rooms() {
    const found = new Map();
    for (const n of this.signals.names()) {
      const m = n.match(/^(lights|blinds)_(.+)$/);
      if (!m) continue;
      if (!found.has(m[2])) found.set(m[2], {});
      found.get(m[2])[m[1]] = n;
    }
    const order = Object.keys(this.level.rooms || {});
    return [...found.entries()].sort((a, b) => (order.indexOf(a[0]) + 1 || 1e3) - (order.indexOf(b[0]) + 1 || 1e3))
      .map(([room, s]) => ({ room, ...s }));
  }

  offline() { return this.signals.get('power') === false; }
  rowCount() { return this.page === 'rooms' ? this.rooms().length : this.page === 'devices' ? this.deviceRows().length : this.cams.length; }

  // (distractions) the Devices page sits between Rooms and Cameras when the level has devices
  deviceRows() { return this.devices ? this.devices.tabletList() : []; }
  pages() { return this.deviceRows().length ? ['rooms', 'devices', 'cameras'] : ['rooms', 'cameras']; }
  nextPage(step = 1) {
    const ps = this.pages(), i = Math.max(0, ps.indexOf(this.page));
    return ps[(i + step + ps.length) % ps.length];
  }

  toggle() { return this.open ? this.close() : this.show(); }
  show() {
    this.open = true;
    this.msg = '';
    this.row = this.rowCount() ? Math.min(Math.max(this.row, 1), this.rowCount()) : 0;
    this._acc = Infinity;       // render a feed frame right away
    this.draw();
    return true;
  }
  close() {
    if (!this.open) return false;
    this.open = false;
    this.el.classList.remove('open');
    return true;
  }

  setPage(page) {
    this.page = page;
    this.row = this.rowCount() ? (page === 'cameras' ? this.cam + 1 : 1) : 0;
    this.col = 0;
    this._acc = Infinity;
    this.draw();
  }

  // a key while the panel is open; returns true if it used it
  key(code) {
    const n = this.rowCount();
    if (code === 'KeyI' || code === 'Escape') { this.close(); return true; }
    if (code === 'ArrowUp' || code === 'ArrowDown') {
      this.row = Math.max(0, Math.min(n, this.row + (code === 'ArrowDown' ? 1 : -1)));
      if (this.page === 'cameras' && this.row > 0) { this.cam = this.row - 1; this._acc = Infinity; }
      this.msg = '';
      this.draw();
      return true;
    }
    if (code === 'ArrowLeft' || code === 'ArrowRight') {
      const step = code === 'ArrowRight' ? 1 : -1;
      if (this.row === 0) this.setPage(this.nextPage(step));
      else if (this.page === 'devices') { /* one toggle per row */ }
      else if (this.page === 'rooms') {
        const r = this.rooms()[this.row - 1];
        const cols = [r.lights && 0, r.blinds && 1].filter((c) => c !== undefined && c !== false);
        if (cols.length) this.col = cols[(cols.indexOf(this.col) + step + cols.length) % cols.length] ?? cols[0];
      } else {
        this.cam = (this.cam + step + this.cams.length) % this.cams.length;
        this.row = this.cam + 1;
        this._acc = Infinity;
      }
      this.draw();
      return true;
    }
    if (code === 'Enter' || code === 'NumpadEnter') {
      if (this.row === 0) { this.setPage(this.nextPage(1)); return true; }
      if (this.page === 'devices') {
        const r = this.deviceRows()[this.row - 1];
        if (this.offline()) this.msg = 'Hub offline · no power';
        else if (r) this.msg = `${roomLabel(r.room ?? '')} · ${this.devices.toggle(r.device).toLowerCase()}`;
      } else if (this.page === 'rooms') {
        const r = this.rooms()[this.row - 1];
        const sig = this.col === 1 ? r.blinds ?? r.lights : r.lights ?? r.blinds;
        if (this.offline()) this.msg = 'Hub offline · no power';
        else if (sig) {
          const v = this.signals.toggle(sig);
          this.msg = `${roomLabel(r.room)} · ${sig.startsWith('blinds') ? (v ? 'blinds closed' : 'blinds open') : (v ? 'lights on' : 'lights off')}`;
        }
      }
      this.draw();
      return true;
    }
    return false;
  }

  draw() {
    if (!this.open) return;
    this.el.classList.add('open');
    const off = this.offline();
    const tab = (p, label) => `<span class="ttab${this.page === p ? ' on' : ''}${this.row === 0 && this.page === p ? ' sel' : ''}">${label}</span>`;
    let body;
    if (this.page === 'rooms') {
      const rooms = this.rooms();
      body = rooms.length ? rooms.map((r, i) => {
        const sel = this.row === i + 1;
        const cell = (sig, col, onText, offText, name) => {
          if (!sig) return '<span class="tcell none"></span>';
          const v = !!this.signals.get(sig);
          return `<span class="tcell${sel && this.col === col ? ' sel' : ''}${v ? ' lit' : ''}">${name} <b>${off ? '--' : v ? onText : offText}</b></span>`;
        };
        return `<div class="trow${sel ? ' sel' : ''}"><span class="troom">${roomLabel(r.room)}</span>` +
          cell(r.lights, 0, 'ON', 'OFF', 'Lights') + cell(r.blinds, 1, 'CLOSED', 'OPEN', 'Blinds') + '</div>';
      }).join('') : '<div class="tempty">No connected rooms.</div>';
      body = `<div class="tlist">${body}</div>`;
    } else if (this.page === 'devices') {
      const rows = this.deviceRows();
      body = rows.map((r, i) => {
        const sel = this.row === i + 1, lit = r.status !== 'OFF';
        return `<div class="trow${sel ? ' sel' : ''}"><span class="troom">${roomLabel(r.room ?? '')}</span>` +
          `<span class="tcell${sel ? ' sel' : ''}${lit ? ' lit' : ''}" style="width:200px">${r.label} <b>${off ? '--' : r.status}</b></span></div>`;
      }).join('');
      body = `<div class="tlist">${body}</div>`;
    } else {
      const list = this.cams.map((c, i) => `<div class="trow${this.row === i + 1 ? ' sel' : ''}${this.cam === i ? ' live' : ''}">CAM ${String(i + 1).padStart(2, '0')} · ${c.name}</div>`).join('');
      body = `<div class="tcams"><div class="tfeed"><div class="tover">${off ? 'NO SIGNAL' : ''}</div><div class="tlabel"></div></div><div class="tlist">${list}</div></div>`;
    }
    this.el.innerHTML = `<div class="tbox"><div class="thead"><span class="ttitle">HOME</span>${tab('rooms', 'Rooms')}${this.pages().includes('devices') ? tab('devices', 'Devices') : ''}${tab('cameras', 'Cameras')}` +
      `<span class="tstat">${off ? 'OFFLINE' : 'ONLINE'}</span></div>${body}<div class="tmsg">${this.msg}</div>` +
      `<div class="thelp">↑ ↓ · choose &nbsp; ${this.page === 'devices' ? '' : `← → · ${this.page === 'rooms' ? 'lights / blinds' : 'camera'} &nbsp; `}Enter · ${this.page === 'devices' ? 'on / off' : 'toggle'} &nbsp; I · close</div></div>`;
    const feed = this.el.querySelector('.tfeed');
    if (feed) { feed.prepend(this.canvas); this.label(); }
  }

  label() {
    const l = this.el.querySelector('.tlabel');
    if (l) l.textContent = `CAM ${String(this.cam + 1).padStart(2, '0')} · ${this.cams[this.cam]?.name ?? ''} · ${new Date().toLocaleTimeString([], { hour12: false })}`;
  }

  // call once per frame, before the frame renders
  update(dt) {
    // (distractions) the Devices page counts down an alarm that's set: redraw twice a second
    if (this.open && this.page === 'devices') {
      this._devT = (this._devT ?? 0) + dt;
      if (this._devT >= 0.5) { this._devT = 0; this.draw(); }
      return;
    }
    if (!this.open || this.page !== 'cameras' || !this.cams.length) return;
    if (this.offline()) { this.ctx.fillStyle = '#050607'; this.ctx.fillRect(0, 0, FEED_W, FEED_H); return; }
    // real time (the game's dt is clamped), and never more than every 3rd frame: on a slow
    // machine 5 fps would otherwise be every frame, doubling its cost
    const now = performance.now();
    this._acc += 1;
    if (this._acc !== Infinity && (this._acc < 3 || now - this._last < 1000 / this.fps)) return;
    this._acc = 0;
    this._last = now;
    this.renderFeed();
    this.label();
  }

  renderFeed() {
    const t0 = performance.now();
    const r = this.renderer, cam = this.cams[this.cam].camera;
    const pr = r.getPixelRatio(), size = r.getDrawingBufferSize(new THREE.Vector2());
    const w = FEED_W / pr, h = FEED_H / pr;
    const bw = Math.floor(w * pr), bh = Math.floor(h * pr);
    const shadows = r.shadowMap.needsUpdate;
    r.shadowMap.needsUpdate = false;
    const hidden = this.hide.filter((o) => o.visible);
    for (const o of hidden) o.visible = false;
    this.culler?.update(cam.position, cam);
    const autoReset = r.info.autoReset;
    r.info.autoReset = false; r.info.reset();
    r.setScissorTest(true);
    r.setViewport(0, 0, w, h);
    r.setScissor(0, 0, w, h);
    r.render(this.scene, cam);
    this.feedCalls = r.info.render.calls;
    r.info.autoReset = autoReset;
    this.ctx.drawImage(r.domElement, 0, size.y - bh, bw, bh, 0, 0, FEED_W, FEED_H);
    r.setScissorTest(false);
    r.setViewport(0, 0, size.x / pr, size.y / pr);
    this.culler?.update(this.camera.position, this.camera);
    for (const o of hidden) o.visible = true;
    r.shadowMap.needsUpdate = shadows;
    this.frames++;
    this.lastFeedMs = performance.now() - t0;
  }
}
