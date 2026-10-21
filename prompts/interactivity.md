# Interactivity v2: the contract between assets, levels and the engine

Read with `CLAUDE.md` ("Interactables"). Today: `slide` (drawers), `rotate` (doors), `pickup`
(items; `throwable`), `lock` / `attach` placement options, one keycard and one locked door.
This adds switches, signals, things that react, usable items, a flashlight, power, noise.
No notes, lore or story anywhere in the game (the user's rule).

## Asset side (custom properties, exported as glTF extras -> three.js userData)
Existing types keep working unchanged. New:

- `interact = {type: "switch", prompt: "Turn on", promptActive: "Turn off", signal: "<name>",
  state: false, range: 1.2, indicator?: "<node>", duration?: 0.15, travel?: {axis, angle|distance}}`
  on the moving part (rocker, knob, button). E toggles `state` and sets signal `<name>` to it;
  the part animates by `travel` (a rocker tips 12 degrees). The level may override `signal`
  and the initial `state` per placement (below).
- A switch may carry `requires: "<signal>"` (+ `requiresPrompt`): it can only be switched on while that signal is on (the main breaker needs `fuse_garage`); switching off always works.
- `interact = {type: "use", needs: "<item id>", consume: true, prompt: "Insert fuse",
  promptDone?: "...", signal: "<name>", value: true}`: with that item ARMED, Enter sets the
  signal (e.g. a fuse into the breaker restores "power"). Without it, the prompt says what's missing.
- `react = {signal: "<name>", on: <effect>, off?: <effect>, duration?: s}` on any node: how it
  responds when its signal changes. Effects:
  - `"show"` / `"hide"`: visibility (a lamp's glow shell, a TV picture);
  - `{"emissive": k}`: multiply the node's emissive intensity (0 = dark, 1 = as authored);
  - `{"slide": {axis: "y", distance: -2.4}}` / `{"rotate": {axis, angle}}`: animate to that
    offset when on, back when off (blinds rolling down, an oven door, a garage door);
    axes are three.js / glTF space (y up) in the node's parent space, like today's drawer
    `axis` (`"x"`, `"-y"` or `[0, 0, -1]`);
  - `{"scale": {axis: "y", to: 0.05}}` (or a number / `[x, y, z]`): scale relative to the
    authored scale, animated (a roller blind furling into its cassette);
  - `{"light": {color, intensity, distance}}`: a real-time point light while on. Use sparingly
    (the flashlight, maybe one hero lamp): all room light is baked; the budget is ~2 extra lights.
  A node may carry a list of reacts; an effect may itself be a list (`["show", {"emissive": 1}]`).
  `off` defaults to the opposite (hidden / emissive 0 / rest pose / no light). `duration`
  defaults to 1 s for moving effects, 0.12 s otherwise. Nodes with `react` + `"block_sight": true`
  (in the react or as its own custom property; closed blinds) block the Grimble's line of sight
  while their signal is on. `"power": true|false` in a react forces whether it needs `power`.
  Put reacts on a child node, not the asset's root (the room culler sets the root's visibility).
- Switch extras: `indicator` glows (its authored emissive colour, green if none) while the
  signal is on and powered. `use` extras: `value` defaults to true, `consume` to true;
  `needsName` (optional) is how the prompt names the missing item.
- `pickup` gains item kinds through `item`: `flashlight` (armed: a real-time spot from the
  camera, Enter toggles it, battery drains), `battery`, `fuse`, `key_<id>` / `keycard`,
  `car_key`, `tablet` (opens the smart-home screen), and any `throwable: true` item
  (`noise: 1.0` loudness when it lands or shatters).

## Level side (room modules' PLACEMENTS options)
- `{"signal": "power_kitchen"}` overrides a switch's or reactor's signal for that placement (a
  string renames every signal the asset uses except `power`; `{"tv": "tv_den"}` maps names);
  `{"state": true}` the initial value of the placement's own signal (its switch's / use point's,
  else its reactors'; `{"state": false}` on the breaker starts the house without power); `{"lock": "<item>"}` as today; `{"attach": ...}` as today.
- Signals are level-global strings. Conventions:
  - `power`: whole-house power (initially on). Everything lit electrically also depends on it.
  - `lights_<room>`: a room's light switch. A room's lamps/glows react to `lights_<room>` AND `power`.
  - `blinds_<room>`: motorised blinds for a room's glass.
  - `<thing>_<room>`: anything else (`tv_den`, `fire_great_room`, `garage_door`).

## Engine side
- `viewer/signals.js`: a tiny store `{get(name), set(name, value), on(name, fn)}` exposed as
  `window.__signals`, initialised from the level (switch states, placement `state`s).
- Interactables: `switch` and `use` types; `react` nodes registered per placement and driven
  by signals (their animation shares the slide/rotate code); prompts like today.
- Items: stacking (done), flashlight (one SpotLight on the camera, cone ~35 degrees, ~20 m,
  shadow off; battery 4 min, `battery` refills), throwables emit `noise` events
  `{position, loudness}` on landing (`window.__noise` hook the Grimble listens to).
- Power: `power` off = every `react` with `light`/`emissive`/`show` tied to electric things goes
  off, and (later, needs a "lights off" bake) the rooms' lightmaps swap to the dark bake. Until
  that bake exists, power off just switches the reactive parts.
- The smart-home tablet: armed + Enter opens a HUD panel listing rooms with toggles for
  lights / blinds and the security camera feeds (render-to-texture views from fixed cameras,
  one at a time, low resolution).
- Player knockdown: `player.knockDown(from)` = a shove away, the camera drops and rolls to
  the floor, ~2.5 s, then the player gets up (used by the Grimble's swipe). `from` is the
  attacker's world position (Vector3 or [x, y, z]); `{dir}` gives the direction toward it instead.
  `player.isDown` while on the floor.

## Engine as built (viewer/signals.js, interactables.js, items.js, tablet.js, player.js)
- `window.__signals` {get, set, toggle, on(name | '*', fn) -> off, define, names};
  `window.__noise` {on(fn) -> off, emit({position, loudness, source?, item?})}.
- Initial signal values, highest first, whatever the load order: mansion.json `"signals"`, a
  placement's `state`, a switch's authored `state`; signals only reactors / use points name start
  false (`power` on).
- Draw calls: reactors that only change materials (emissive, show/hide) are batched per room with
  everything else that shares their (material, signal, effect); show/hide sets `material.visible`.
  Moving reactors (slide/rotate/scale), lights, block_sight and `"collide": true` ones keep their
  own nodes (a react with `collide` blocks the player once settled, like interact's `collide`).
- Throwables with `"shatter": false` (books) thud (noise), bounce off walls, land whole and
  become a pickup again.
- `window.__interact`: `sightBlockers()` -> [Box3] of block_sight reactors that are on,
  `blocksSight(a, b)`, `register(root, opts)` (a prop built at runtime), `reactors`.
- Real-time lights: `light` reacts share a pool of 2 point lights (nearest lit reactors to the
  eye); the flashlight is one spot. Both are created at level load only if the level has them
  (adding a light later recompiles every material, ~2 s). Point/spot light also lights the baked
  shell (baked.js keeps it); the unlit outdoor meshes don't take it.
- The tablet's hub needs `power`: with power off its pages show offline / no signal. Cameras
  come from mansion.json `"cameras": [{name, position, lookAt, fov?}]` (glTF coords) if present,
  else defaults in the great room, entry, courtyard and kitchen. Optional `"signals": {...}`
  in mansion.json sets initial values.

## Distractions: things that make noise on purpose (viewer/devices.js)
- A node with the custom property `noisemaker = {signal, loudness?: 1, every?: 1.5, for?, delay?,
  flash?, flashRest?: false, flashEvery?: 0.4, shake?: "<node>", sfx?, source?, label?, statusOn?,
  tablet?: true, power?: true}` is a device. While `signal` is on (and `power`, unless
  `power: false`) it *sounds*: every `every` s (the first at once) it emits
  `window.__noise.emit({position, loudness, source, device, room, continuous, age})` from the
  node's world position, and calls `window.__sfx?.play(sfx, position)`; `__sfx?.stop?.(sfx,
  position)` when it falls silent. `for`: it sounds that long, then sets its own signal off (alarms,
  a chime; `continuous` is false); without it, until switched off (TV, music: `continuous: true`,
  `age` = seconds it has been sounding). `delay`: seconds from the signal coming on to the sound
  starting (an alarm clock you set and run from). `flash`: a signal it toggles every `flashEvery`
  s while sounding and leaves at `flashRest` otherwise (react nodes on it blink: the car's lamps,
  the clock's digits). `shake`: a node jittered while it sounds (kept out of the room batches).
  Placement `signal` renames `signal` / `flash` like a switch's. Switches on the same signal
  (the device's button) follow it, so an alarm that stops itself flips its switch back.
- A pickup with `remote: "<signal>"` (+ `remotePrompt`) toggles that signal when armed + Enter,
  anywhere (the car key's panic button -> `car_alarm`). A `use` point or lock in reach wins.
- The tablet's Devices page lists every device without `tablet: false` (one row per signal), and
  Enter toggles it from anywhere (needs `power`).
- In the level: `tv_den` (living_media_wall, starts off), `music_great_room` (two ix_speaker),
  `doorbell` (ix_control_panel in the entry, tablet only), `blender_kitchen` (ix_blender),
  `alarm` (ix_alarm_clock, primary bedroom; `alarm_display` = its digits), `car_alarm` (car_ev in
  the garage, via the car key; `car_alarm_flash` = its lamps). sfx names (one play() per noise
  pulse, for viewer/audio.js to add): music, doorbell, blender, alarm_clock, car_alarm; the TV
  has none (audio.js loops its sound from the tv_* signal). Throwables' `noise`: vase 1.4, wine bottle 1.2, book 0.6.
  The Grimble hears 30 m x loudness (grimble_hunt.js `hearing`): car alarm 2.0, doorbell 1.3,
  music / alarm clock 1.2, blender 1.1, TV 1.0.
