import * as THREE from 'three';

// Things that make noise on purpose (prompts/interactivity.md, "noisemaker"): the den TV, the
// great room's speaker, the doorbell chime, the kitchen blender, the bedroom alarm clock, the
// car alarm. The player uses them to pull the Grimble away: a device sounds where it stands,
// for a few seconds (alarms) or until it's switched off (TV, music), and every `every` seconds
// it emits a noise the Grimble hears (window.__noise.emit({position, loudness, source, ...})).
//
// A node (an empty or a mesh) with the custom property `noisemaker` is a device:
//   signal      it sounds while this signal is on (and `power`, unless power: false); the
//               placement's `signal` option renames it like a switch's (interact.signalFor)
//   loudness    noise loudness (the Grimble hears it from 30 m x loudness), default 1
//   every       seconds between noise events while it sounds (the first one at once), default 1.5
//   for         seconds it sounds, then it switches its signal off itself (alarms, a chime);
//               without it, it sounds until switched off (TV, music)
//   delay       seconds between its signal coming on and the sound starting (an alarm clock set
//               to ring: run, it goes off behind you)
//   flash       a signal it toggles every `flashEvery` s (default 0.4) while sounding, back to
//               `flashRest` (default false) when silent: react nodes on it blink (hazard lights,
//               clock digits)
//   shake       node name(s) jittered (a few mm) while it sounds (the blender's jar)
//   sfx         window.__sfx?.play(sfx, position) on every noise event, __sfx?.stop?.(sfx, position)
//               when it falls silent (the audio workstream provides __sfx)
//   source      the noise event's `source` (default sfx, else the signal)
//   label       its name on the tablet's Devices page; tablet: false keeps it off that page
//   statusOn    what the tablet shows while it sounds (default ON, or RINGING with `for`)
// Devices sharing a signal (the great room's two speakers) are one source: one noise event per
// pulse from the middle of those sounding (each still plays its own sound effect).
//   remote-only devices (the car) are triggered by an item: a pickup with `remote: "<signal>"`
//               (the car key) toggles that signal when armed + Enter, anywhere
// Noise events carry {position (Vector3), loudness, source, device, room, continuous (no `for`),
// age (s since it started sounding)}: a TV that has been on for a minute may be worth less to
// the Grimble than a fresh alarm (its AI decides).

const truthy = (v) => v === true || v === 1 || v === 'true' || v === '1';
const list = (v) => (v == null ? [] : Array.isArray(v) ? v : [v]);

export class Devices {
  constructor({ signals, noise, interact, level = null }) {
    Object.assign(this, { signals, noise, interact, level });
    this.devices = [];
    this.time = 0;
    this.events = 0;              // noise events emitted (tests)
  }

  // a placed prop (after interact.collect): its noisemakers. opts = the placement's {signal, state, room}
  collect(root, opts = {}) {
    const added = [];
    root.traverse((node) => {
      const def = node.userData.noisemaker;
      if (!def) return;
      const map = (name) => (name ? this.interact.signalFor(name, opts) : null);
      const d = {
        node, def, root, room: opts.room ?? null,
        signal: map(def.signal),
        flash: map(def.flash),
        flashRest: truthy(def.flashRest),
        electric: def.power !== undefined ? truthy(def.power) : true,
        loudness: +(def.loudness ?? 1),
        every: Math.max(0.2, +(def.every ?? 1.5)),
        for: def.for != null ? +def.for : null,
        delay: +(def.delay ?? 0),
        flashEvery: +(def.flashEvery ?? 0.4),
        shake: [],
        state: 'off',             // off | waiting (delay) | sounding
        t: 0,                     // seconds in the current state
        next: 0,                  // time of the next noise event (sounding)
        flashT: 0, flashOn: false,
        label: def.label ?? def.source ?? def.signal,
        id: `${def.source ?? def.signal}${opts.room ? '@' + opts.room : ''}`,
      };
      for (const n of list(def.shake)) {
        const s = root.getObjectByName(n);
        if (s) d.shake.push({ node: s, rest: s.position.clone() });
      }
      // signals only a noisemaker names start off (like a reactor's); a flash signal starts at rest
      this.interact.claim(d.signal, undefined, 0);
      if (d.flash) this.interact.claim(d.flash, d.flashRest, 1);
      this.signals.on(d.signal, () => this.changed(d));
      if (d.electric) this.signals.on('power', () => this.changed(d));
      this.devices.push(d);
      added.push(d);
    });
    return added;
  }

  // after the level's signals are resolved (interact.snapAll): devices whose signal starts on sound
  syncAll() { for (const d of this.devices) this.changed(d); }

  // a prop built at runtime (tests): interact.register + its noisemakers
  register(root, opts = {}) {
    const items = this.interact.collect(root, opts);
    const added = this.collect(root, opts);
    this.interact.snapAll();
    for (const d of added) this.changed(d);
    return { items, devices: added };
  }

  // nodes that move while a device sounds: kept out of the room batches
  movingNodes() { return this.devices.flatMap((d) => d.shake.map((s) => s.node)); }

  live(d) {
    return truthy(this.signals.get(d.signal)) && (!d.electric || this.signals.get('power') !== false);
  }

  changed(d) {
    const on = this.live(d);
    if (on && d.state === 'off') this.start(d);
    else if (!on && d.state !== 'off') this.stop(d);
  }

  start(d) {
    d.t = 0;
    if (d.delay > 0) { d.state = 'waiting'; return; }
    this.sound(d);
  }

  // it starts sounding: the first noise this frame, the flash signal on at once
  sound(d) {
    d.state = 'sounding';
    d.t = 0; d.next = 0; d.flashT = 0;
    if (d.flash) { d.flashOn = true; this.signals.set(d.flash, !d.flashRest); }
  }

  stop(d) {
    const was = d.state;
    d.state = 'off';
    d.t = 0;
    if (d.flash) { d.flashOn = false; this.signals.set(d.flash, d.flashRest); }
    for (const s of d.shake) s.node.position.copy(s.rest);
    if (was === 'sounding') window.__sfx?.stop?.(d.def.sfx, this.position(d));
  }

  position(d) { return d.node.getWorldPosition(new THREE.Vector3()); }

  // seconds left before an alarm rings / stops (the tablet shows it)
  remaining(d) {
    if (d.state === 'waiting') return Math.max(0, d.delay - d.t);
    if (d.state === 'sounding' && d.for != null) return Math.max(0, d.for - d.t);
    return null;
  }

  update(dt) {
    this.time += dt;
    for (const d of this.devices) {
      if (d.state === 'off') continue;
      d.t += dt;
      if (d.state === 'waiting') {
        if (d.t < d.delay) continue;
        this.sound(d);
      }
      if (d.for != null && d.t >= d.for) {
        this.signals.set(d.signal, false);       // an alarm stops itself (its switch follows)
        if (d.state !== 'off') this.stop(d);
        continue;
      }
      if (d.t >= d.next) {
        d.next += d.every;
        this.pulse(d);
      }
      if (d.flash) {
        d.flashT += dt;
        if (d.flashT >= d.flashEvery) {
          d.flashT = 0;
          d.flashOn = !d.flashOn;
          this.signals.set(d.flash, d.flashOn ? !d.flashRest : d.flashRest);
        }
      }
      for (const s of d.shake) {
        s.node.position.set(s.rest.x + (Math.random() - 0.5) * 0.004, s.rest.y + (Math.random() - 0.5) * 0.003,
          s.rest.z + (Math.random() - 0.5) * 0.004);
      }
    }
  }

  pulse(d) {
    const position = this.position(d);
    const source = d.def.source ?? d.def.sfx ?? d.signal;
    window.__sfx?.play?.(d.def.sfx ?? source, position);
    // devices sharing a signal (a pair of speakers) are one source: the first of them emits one
    // noise from the middle of those sounding, the rest only play their sound effect
    const group = this.devices.filter((x) => x.signal === d.signal && x.state === 'sounding');
    if (group[0] !== d && group.includes(d)) return;
    if (group.length > 1) {
      position.set(0, 0, 0);
      for (const x of group) position.add(this.position(x));
      position.divideScalar(group.length);
    }
    this.noise.emit({ position, loudness: d.loudness, source, device: d.id, room: d.room,
      continuous: d.for == null, age: d.t });
    this.events++;
  }

  // ------------------------------------------------------------------ the tablet's Devices page
  // [{device, label, room, signal, status}] for the devices on the hub, in level room order
  tabletList() {
    const order = Object.keys(this.level?.rooms || {}), seen = new Set();
    // one row per signal (a pair of speakers is one sound system)
    return this.devices.filter((d) => d.def.tablet !== false && !seen.has(d.signal) && seen.add(d.signal))
      .sort((a, b) => (order.indexOf(a.room) + 1 || 1e3) - (order.indexOf(b.room) + 1 || 1e3))
      .map((d) => ({ device: d, label: d.label, room: d.room, signal: d.signal, status: this.status(d) }));
  }

  status(d) {
    const r = this.remaining(d);
    if (d.state === 'waiting') return `SET ${Math.ceil(r)}s`;
    if (d.state === 'sounding') return d.def.statusOn ?? (d.for != null ? 'RINGING' : 'ON');
    return 'OFF';
  }

  // toggle a device from the tablet; returns a message
  toggle(d) {
    const v = this.signals.toggle(d.signal);
    const what = `${d.label}`;
    if (!v) return `${what} · off`;
    if (d.electric && this.signals.get('power') === false) return `${what} · no power`;
    return d.delay > 0 ? `${what} · rings in ${d.delay} s` : `${what} · on`;
  }

  // ------------------------------------------------------------------ remote items (the car key)
  // Enter with an armed pickup whose def has `remote`: toggle that signal (anywhere). Returns a
  // message, or null when the item has no remote
  useRemote(def) {
    if (!def?.remote) return null;
    const d = this.devices.find((x) => x.signal === def.remote);
    const v = this.signals.toggle(def.remote);
    const name = def.remotePrompt ?? d?.label ?? def.remote;
    return v ? `${name} · on` : `${name} · off`;
  }

  remoteHint(def) {
    if (!def?.remote) return null;
    const name = def.remotePrompt ?? def.remote;
    return truthy(this.signals.get(def.remote)) ? `${name} off` : `${name} on`;
  }
}
