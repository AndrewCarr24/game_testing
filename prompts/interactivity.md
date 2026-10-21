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
  - `lights_<room>`: a room's light switch. A room's lamps/glows react to `lights_<room>` AND `power`,
    and so does the room's baked light (the lights-off bake, below). Room modules wire their
    fixtures with `ix_common.wire(PLACEMENTS, "<room>")` (every asset in `ix_common.FIXTURES`:
    lamps, pendants, downlights, coves, built-ins with LED strips). Shared spaces share one
    signal: the 8 galleries `lights_galleries` (no switch: the tablet), the courtyard's festoons
    `lights_courtyard`. A room's signal is written to mansion.json `rooms[r].lights`
    (`LIGHTS_SIGNAL` in the module overrides it); a `LIGHTS` entry may say `signal=None` (not
    electric: candles) or another signal. A lamp with its own switch should also be wired to
    its room's signal (its baked light can only follow one signal: the room's).
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
  off, and every room fades to its lights-off bake.
- Lights off (built: `bake.py --state off|both`, `viewer/baked.js`): while a room's light signal
  is false or `power` is off, its baked light fades (0.45 s) to a second bake with its own
  lights, ceiling strips and fixture glows off (daylight and the neighbours' light still come
  in): the shell's lightmap, the props' SH probe, the reflections, the strips' glow. No
  real-time lights, no extra GPU texture (the off lightmap rides in the on lightmap's alpha).
  `window.__lighting`: `lightLevel(room)` (1 = lit, down to the dark state's share of the light),
  `isDark(room)`, `roomSignal` (room -> signal) for gameplay (the Grimble's eyes, hiding).
  Signals for rooms without a switch (galleries, courtyard) are defined on (true) at load.
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
