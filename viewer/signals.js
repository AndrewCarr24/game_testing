// Level-global signals (prompts/interactivity.md): named values that switches, `use` points
// and the tablet set, and that `react` nodes follow. `power` is whole-house power (on unless
// the level says otherwise); `lights_<room>`, `blinds_<room>`, `<thing>_<room>` by convention.
//
//   signals.get(name)          current value (undefined if nothing defined it)
//   signals.set(name, value)   change it; subscribers run only when the value changes
//   signals.on(name, fn)       fn(value, name) on every change; name '*' = any signal; returns off()
//   signals.define(name, v)    initial value, if the signal has none yet (no notification)
//   signals.names()            every signal defined so far
//
// Also the noise hook the Grimble listens to:
//   noise.on(fn)               fn({position, loudness, source}) per event; returns off()
//   noise.emit(event)          thrown items landing / shattering (loudness = the item's `noise`, default 1)
//                              and devices sounding (viewer/devices.js: TV, music, chime, alarms, car alarm)

export class Signals {
  constructor(initial = {}) {
    this.values = new Map(Object.entries({ power: true, ...initial }));
    this.explicit = new Set(Object.keys(initial));   // set by the level: beats every prop's default
    this.subs = new Map();      // name -> Set(fn)
  }

  get(name) { return this.values.get(name); }
  has(name) { return this.values.has(name); }
  names() { return [...this.values.keys()]; }

  define(name, value) {
    if (name && !this.values.has(name)) this.values.set(name, value);
  }

  set(name, value) {
    if (!name) return;
    const prev = this.values.get(name);
    this.values.set(name, value);
    if (prev === value) return;
    for (const key of [name, '*']) for (const fn of [...(this.subs.get(key) || [])]) fn(value, name);
  }

  toggle(name) { this.set(name, !this.get(name)); return this.get(name); }

  on(name, fn) {
    if (!this.subs.has(name)) this.subs.set(name, new Set());
    this.subs.get(name).add(fn);
    return () => this.subs.get(name).delete(fn);
  }
}

export class Noise {
  constructor() { this.subs = new Set(); this.last = null; this.count = 0; }
  on(fn) { this.subs.add(fn); return () => this.subs.delete(fn); }
  emit({ position, loudness = 1, ...rest }) {
    const event = { position, loudness, ...rest };
    this.last = event;
    this.count++;
    for (const fn of [...this.subs]) fn(event);
    return event;
  }
}
