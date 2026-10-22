# Combat (the player's weapons, health and death)

Wave 2, combat workstream. Contract shared with the invader workstreams: `prompts/wave2.md`
"Combat contract". Code: `viewer/combat.js` (targets, damage, sweeps, shots, events, the
player's health), `viewer/weapons.js` (weapon data, the attack controller, the practice
dummy), `viewer/weapons_viewmodel.js` (the first-person hand and weapon). Test:
`viewer/tools/combat.mjs`.

## The interface (`window.__combat`)
- `register(target)`: `{ id, kind: 'player'|'invader'|'dummy', team, position() (feet centre),
  radius, height, health, maxHealth, alive, hit(damage, info) }`. Optional: `facing()` (unit,
  horizontal), `aware` (bool or `fn(attacker)`), `parts` (`{head, body, legs}` damage
  multipliers for shots). `target.hit` applies the damage itself (stagger, call-outs, death
  animation are the target's); combat reads `health`/`alive` after and raises the events.
  `makeTarget(opts)` builds a plain one.
- `hit(target, damage, info)`: damage from anywhere (`info = { from, dir, weapon, part, point,
  stealth, kind }`).
- `attack({ from, origin, dir, weapon, range, arc, damage, takedown, maxTargets })`: a melee
  sweep (cone of `arc` degrees, `range` to the body's surface, line of sight through the level's
  colliders, nearest `maxTargets`); an unaware target hit from behind with `takedown` damage
  set dies outright (stealth).
- `shoot({ from, origin, dir, spread, range, damage, weapon, pellets })`: hitscan against the
  colliders (walls, props and glass stop it, `seeThrough` rails and boundaries don't) and the
  targets (vertical cylinders) -> `{ target, point, normal, distance, part, wall, glass, killed }`.
  The shooter emits its own gunshot noise (`window.__noise`, loudness 2.5).
- `canTakedown(target, from)`, `lineOfSight(a, b)`, `raycast(origin, dir, range)`, `lastCombat(id)`.
- For the invader workstreams: implement `facing()` (a Vector3, or a yaw in radians with
  direction (sin, 0, cos)) and `aware` or `unaware` (bool or function; neither counts as
  aware, so no takedowns); `alive` may be a getter; a Box3 a character pushes into `window.__colliders` should carry `owner` = its
  target (rays skip it and meet the body's cylinder; an untagged box round a living target's
  middle is recognised too, at a small cost per ray). Listen for `playerDown` to stop
  attacking. The player is target `'player'` (team `'player'`); hurt it with
  `__combat.hit('player', dmg, { from: me, weapon })` or `attack()` / `shoot()` with `from: me`.
- Events (`on(name | '*', fn)`): `hit`, `kill`, `shot`, `attack` (every swing), `playerDown`.

## The player
- Health 100 (`window.__vitals`). Out of combat (7 s without dealing or taking damage) it comes
  back at 3.5/s (~30 s from nearly dead to full).
- Feedback, no HUD numbers: a red edge vignette flashes with each hit and pulses under 40 health;
  a red wedge at the edge of the view points to where the hit came from and follows it as the
  player turns (1.4 s); the view jolts up and rolls away from the hit's side; under 40 health a
  synthesised heavy breathing (band-passed noise, faster and louder the lower it is).
- Death: an endless knockdown (`player.knockDown(.., {duration: Infinity})`: the eye drops to the
  floor, the view rolls, input is ignored), the screen fades to black over ~2.5 s, then one
  RESTART button (reloads the page = a new run). Nothing else on screen.
- `?god=1`: hits show but never take the last point (playtests).

## Weapons (`WEAPONS` in viewer/weapons.js)
A weapon is a pickup whose interact definition names it (`weapon: '<id>'`), so a new melee
weapon is data: a `WEAPONS` entry and a pickup asset with `_Grip`, `_Tip`, `_Edge` empties
(the view model holds the model by them). Arming: picked up with nothing in hand it is armed at
once; keys 1-4 arm the carried weapons in pickup order (again: put away); the inventory (I) also
arms them. Attacks: click or Enter = primary, right click = secondary.

| weapon | primary | secondary | other |
|---|---|---|---|
| kitchen_knife | stab 55, 1.05 m, 26 deg cone, hit at 0.15 s, 0.52 s cooldown | slash 38, 1.2 m, 100 deg, up to 2 targets, 0.66 s | takedown 100 (instant) from behind an unaware target, 1.25 m |
| bat (data) | swing 35, 1.7 m, 110 deg | jab 15 | |
| frying_pan (data) | swing 30, 1.45 m | | louder (noise 1.1) |
| fireplace_poker (data) | swing 40, 1.6 m | thrust 30 | |

Each attack is view-model keyframes (poses relative to the hold pose), a hit frame (`hitAt`),
`duration` and `cooldown`. On a hit: hit stop (the view model holds 75 ms, 130 ms for a
takedown), a small jolt of the view, the weapon's hit sound at the point, a noise of 0.6 (half
for a takedown); a blade that meets a wall or counter in reach clinks (noise 0.3). Swings are
silent to the AI. No blood: the hit reads from the sound, the hit stop and the target's own
reaction (the dummy flashes and wobbles; invaders stagger).

The takedown: the crosshair turns gold and the prompt says "Takedown" when an unaware target
(`aware` false) is in reach with the player behind it (more than ~110 deg off its facing); the
primary attack becomes an overhand stab that kills whatever its health.

## Guns (designed, not built)
The armory comes later. The controller already reads a gun definition (commented `pistol`
entry): `damage, range, rate, auto, pellets, spread {hip, ads, move}, recoil {pitch, yaw,
recover}, ammo {item, mag}, reload, ads {pos, fov, time}, noise, sfx`. Implemented: `fire()`
(magazine, `combat.shoot` with hip / aim spread, the gunshot noise, recoil kicking the view and
recovering), `reload()` (rounds from the inventory's ammo item, R), right mouse held = `ads`.
Still to build with the first gun: its asset and view-model pose, the aim-down-sights blend
(position + FOV), muzzle flash / tracer / impact decals (from the `shot` event), auto fire.

## Sounds
Played through `window.__sfx` by the contract names (`knife_swing`, `knife_hit`, `knife_wall`,
`knife_takedown`, `body_fall`, `player_hurt`, `bat_swing`, `bat_hit`, `pan_hit`, `gunshot`, ...).
Until the sound sprite has them, `weapons.js` `sfx()` plays stand-ins from the existing sprite
(a whoosh, a hit, a metal clink, a fall).

## The practice dummy
`spawnDummy({ scene, combat, colliders, position, rotationY, aware })` (weapons.js), or
`?dummy=x,y,z[,rotY[,aware]]` in the URL: a mannequin (capsule body, head, a nose showing its
facing) on a base, 100 health, solid to the player. Hit: flashes and wobbles away from the blow;
dead: topples over along it. Stand-in until the invaders are in.

## The view model
The hand is built in code (`buildHand`): four fingers wrapped round the handle (capsules on a
loop round its axis), knuckles, palm, thenar and thumb closing over the fingers, a wrist and
forearm bent toward the little finger, a dark sleeve; soft occlusion in the vertex colours.
One mesh for the skin, one for the sleeve, plus the weapon's own (2 extra draw calls + the
weapon's). It is lit by the room the eye is in (that room's baked SH, its panorama for
reflections; no real-time sun in sunless rooms), so it matches the furniture. Its depth is
squeezed into the nearest slice of the depth buffer, so it never pokes into walls. Idle sway,
walk bob, look lag; raised into view when armed.

## Cost
- Armed: the view model is 5 draw calls (hand, sleeve, the knife's 3 materials: its meshes are
  merged per material) and 8.8k triangles (hand ~7k, knife 1.7k). No lights, no shadows.
- Unarmed: nothing drawn. The knife on the board uses the kitchen's existing materials
  (M_Steel_Brushed, M_Steel_Polished, M_Carcass_Black), so it joins the room's batches: +1.6k
  triangles, no draw calls. The combat code is a few loops over the registered targets.
- Bench (`bench.mjs`, gpu, 2026-10-22, vs the `wave` run at d1b4f4f): 184 fps, frame p95 6.6 ms,
  draw calls mean 289.9 / max 837, triangles max 971,750 (+1,612 = the knife), every budget
  PASS. The draw calls are +3 mean over `wave` whatever the knife's materials (the commits
  between). SwiftShader ran over its GPU-time budget while 8 agents shared the CPU (timings
  only; counts within noise).
