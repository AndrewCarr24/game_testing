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
- Wall controls (`ix_common.switch`; each kind must read as itself from across the room):
  `ix_switch` lights = small graphite square, black rocker, amber LED; `ix_switch_blinds` =
  tall bronze plate, ivory rocker between up/down chevrons, white LED; `ix_switch_fire` =
  round bronze plate, quarter-turn knob, orange LED; `ix_switch_garage` = tall graphite plate,
  push button in a blue lit ring. Placing them: a light switch at each main way into a room
  (doors: latch side, ~0.17 m from the jamb, never behind the door's swing; z = 1.1),
  extra ones on the same signal (two-way); blinds by the glass they drive, never stacked
  or side by side with a light switch; the garage opener at 1.5 m. Prompts say what they
  do ("Turn off lights", "Lower blinds"). `viewer/tools/controls.mjs` checks every one
  (focus, prompt, nothing in front, room to stand, E toggles).
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

## Locks, keys and caches (blender/levels/caches.py)
- A placement's `lock` (an item id) locks only what opens in it (`slide` / `rotate`), never its
  switches or `use` points. Locked things say what they need, named from the key's pickup
  anywhere in the level: "Locked · needs the office key"; carrying it, "Locked · arm the office
  key (I, then Enter)"; armed, Enter unlocks ("Cabinet unlocked") and locks again once shut.
  Messages call the thing by `kind` if the interact has one, else by its prompt's noun ("Open
  safe" -> safe), else door / drawer.
- Containers with a hinged door: a static node inside (`<Asset>_Inside`, e.g. a safe's shelf)
  carries `inside: "<door node name>"`; a pickup attached to it can only be taken while that
  door is open, and doesn't swing with it (`attach: (asset, "<Asset>_Inside")`). Drawers need
  nothing: what's attached to the drawer rides in it.
- Keys are pickups `key_<id>` (one thin module per key: `ix_key_office`, `ix_key_safe`, ...).
  `caches.py` holds the whole design (every key, its lock, what's inside); `mansion.py` merges it
  into the rooms' PLACEMENTS. Locked doors take `lock=` in `plan.CUTS`.

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

## Power and darkness as gameplay (viewer/house.js)
- The house starts powered with the main fuse in (the garage breaker is placed with `state: true`:
  `power` and `fuse_garage` on). The Grimble's break-in flickers the lights for ~1.3 s, then
  `power` and `fuse_garage` go false (the isolator drops to off, its carrier is empty). The spare
  fuse is in the garage's steel locker (its key is in the wine room's climate cabinet, whose key is in the garage workbench drawer: blender/levels/caches.py); fuse in, then the isolator, = power back.
  While the Grimble moves through the house the isolator trips again now and then (150-330 s
  apart, fuse intact). The player can switch it off on purpose. `?trips=0|N`, `?breaktrip=0`.
- Motors: a moving react (slide / rotate / scale: blinds, the garage door) needs `power` to move;
  with it off it stops where it is and catches up when power is back. `"motor": false` (or an
  explicit `"power"`) in the react opts out. A switch whose signal drives electric or motorised
  things says "· no power" in its prompt (and "No power" when pressed) while the power is off.
- Darkness: `window.__house.lightAt(position)` = how lit a spot is (0..1): its room is lit while
  `power` and `lights_<room>` are on, else only its daylight share (house.js DAYLIGHT; x0.3 with
  `blinds_<room>` down; windowless rooms ~0); outdoors 1. Until the lights-off bake exists a
  fallback dims each room's baked light (lightmap, SH probe, reflections) to that level; it
  stands down when the bake provides signal-driven off states (`baked.signalDriven`,
  `baked.setLights`, or bake-JSON rooms with `off` / `lightmapOff` / `dark`), or with `?dark=0`.
- Flashlight: F toggles it (no need to arm it); signal `flashlight` mirrors whether it's lit;
  `window.__flashlight.beam()` -> {on, position, direction, range, cone (half-angle, deg)}.
  The light cue: while it's on in a dark spot (lightAt < 0.6), and the Grimble is inside, in the
  beam (within range + 6 m) or within 10 m, with no shell wall between, once a second:
  `window.__noise.emit({position: eye, loudness: 1, source: 'light'})`.
- Sound hooks (optional): `window.__sfx.play('power_flicker' | 'power_out' | 'power_on' | 'fuse_blow', position)`.

## Affordance (viewer/affordance.js): what's usable reads at a glance
- Focus = what E acts on: only things within 50 degrees of the view (or under the crosshair),
  in reach. The crosshair is a dot; a ring over something usable (`take` for pickups, `use`);
  amber dashes when it's `blocked` (locked, needs an item, a switch whose `requires` is off);
  gold when the armed item works on it (`armed`) or a throwable is aimed (`throw`). The prompt
  sits under it as key caps (`#hint` textContent is still "E · <prompt>   |   Enter · ...").
- The focused thing gets a faint fresnel rim (overlay meshes sharing its geometry; it
  brightens what's lit, plus a small lift in the dark). An interact node with no mesh (the
  breaker's fuse slot) borrows the asset's small meshes that overlap it.
- Usable things within ~5 m (pickups, `use` points not done, switches, drawers; not doors)
  twinkle briefly every ~4 s: one Points draw call for the house, hidden by walls and closed
  drawers. Frozen under `window.__bench`. `?afford=0` turns highlight and glints off;
  `?rim=`, `?rimgain=`, `?glint=` tune them.
- Pickups may carry `purpose`: one plain line (what it's FOR, how to use it; no story) shown
  in the inventory and under the pickup prompt. Without it the line comes from a table in
  affordance.js (keycard, flashlight, battery, fuse, tablet, car_key) or from what the item
  does: throwable (smashes / thuds), a `use` point that needs it, a lock it fits.
- Locked things say what's missing in the prompt: "Locked · needs the <item>" (or the
  authored `lockedPrompt`), "Locked · arm the <item> (I)" while carried but not armed.
