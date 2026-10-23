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
arms them. **One attack per weapon, on Enter. No mouse buttons** (the user: "the knife should only
have a slash move (Enter)"): clicks only lock the pointer.

| weapon | attack (Enter) | other |
|---|---|---|
| kitchen_knife | slash 55 (two kill), 1.25 m, right to left across ~76 deg of the view, up to 2 targets, 0.66 s, 0.62 s cooldown | the same slash from behind an unaware target = takedown (instant kill) |
| bat (data) | swing 35, 1.7 m, up to 2 | |
| frying_pan (data) | swing 30, 1.45 m | louder (noise 1.1) |
| fireplace_poker (data) | swing 40, 1.6 m | |

An attack is view-model keyframes (`keys`: arm pose `p`/`r` plus the wrist bones `w` = flex,
deviation, twist; eases `in`/`out`), `duration`, `cooldown` and a `sweep`: where the blade travels
in the view while it can cut (`from`/`to` = [yaw, pitch] off the view's centre between `t0` and
`t1`). Each frame the step swept since the last one is a `combat.attack` cone (`exclude` = the
targets this swing already hit, `quiet`: the swing raises one `attack` event when it ends), so a
target on the right is cut early in the arc, one on the left late, a target 70 deg off isn't.

The slash (0.66 s): anticipation (0-0.13 s: the arm draws back and up to the right, the wrist
cocks back), the cut (0.13-0.27 s: accelerating right to left and a little down, the wrist snaps
through; it can hit from 0.15 to 0.27 s), follow-through (the wrist rolls over past the left of
the view), a beat, the recovery back to the guard. A faint streak trails the outer blade while it
cuts (one ribbon, positions re-evaluated from the clip, as bright as the room); the view leans
~1 deg with the swing (`attack.view`). On contact: hit stop (the arm holds 75 ms and shivers,
130 ms for a takedown, half for a second target), a small jolt of the view, `knife_hit` at the
point, a noise of 0.6 (half for a takedown). A wall or counter in the blade's path before any
target (0.9 m, `reach`) stops the swing: `knife_wall`, a short hit stop, the arm springs back,
noise 0.3. Swings are silent to the AI (`knife_swing` is for the player). No blood: the hit reads
from the sound, the hit stop and the target's own reaction.

The takedown is not a separate move: when an unaware target (`aware` false / `unaware` true) is
in reach with the player behind it (more than ~110 deg off its facing), the crosshair turns gold
and the prompt says "Takedown"; Enter plays the same slash, and when the blade's sweep reaches
that target it dies outright whatever its health (`stealth: true` on the hit and kill events,
`knife_takedown`). Seen (aware) or from the front it is an ordinary 55 slash.

## Guns (designed, not built)
The armory comes later. The controller already reads a gun definition (commented `pistol`
entry): `damage, range, rate, auto, pellets, spread {hip, ads, move}, recoil {pitch, yaw,
recover}, ammo {item, mag}, reload, ads {pos, fov, time}, noise, sfx`. Implemented: `fire()`
(magazine, `combat.shoot` with hip / aim spread, the gunshot noise, recoil kicking the view and
recovering), `reload()` (rounds from the inventory's ammo item, R); Enter fires. Aiming down
sights needs a key of its own when the first gun lands (no mouse buttons).
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
The arm is an asset, `blender/assets/viewmodel_arm.py` -> `assets/models/viewmodel_arm.gltf`
(+ `T_ViewmodelArm_BaseColor/ORM/Normal`, 1024, kept full size by optimize_textures): a bare right
hand closed round the chef's knife's handle in a hammer grip (four fingers in three phalanges
wrapping the handle, the thumb over the index and middle fingers, knuckles, nails, thenar and
hypothenar pads, the flesh pressed flat on the handle), the wrist, the forearm and the pushed-up
sleeve of a charcoal knit sweater with a ribbed cuff. Built as a signed distance field (the
invader's SDF toolkit), meshed at 0.8 mm, decimated to 7.2k triangles; the normal map is baked
from the field mesh (knuckle wrinkles, the cuff's ribs, pores and knit added in texture space),
occlusion baked with the handle as an occluder and tinted red in the base colour (light through
skin). Rig: Forearm -> Twist -> Hand (the slash bends and rolls the wrist; the twist is shared
along the forearm). It is built in the grip frame, so the weapon's `_Grip` goes in its
`ViewmodelArm_Socket` (on the Hand bone); the root's extras (`userData.viewmodel`) give the joint
axes. Loaded once at startup (~250 kB); a weapon shows when it has (the old code-built hand is
the fallback if it can't load). Placement: `hold` = the grip in camera space (`pos`), the forearm
direction (`arm`), the back of the hand (`back`, then `roll` about the forearm), the guard's
wrist bend; scale 1:1. The guard (second art pass): the fist low in the bottom-right, ~45 cm
from the eye, the back of the hand turned away and rolled so the curled fingers, their creases
and the PIP knuckles face the eye (the blade leans up-left from the thumb side, like a held
tool); nearest visible vertex 0.29 m (the near plane is 0.1 m). Proportions: wrist ~6.1 cm wide
x 4.1 cm deep, forearm to ~8.8 x 7.3 cm, fingers slimmer than their spacing (a crease between
each), knuckle ridges and PIP bumps in the field. Skin: low-saturation light base, paler palm,
redder knuckles and fingertips, visible veins on the back of the hand and wrist, roughness
~0.47-0.55; the room's SH is 35% desaturated on the skin so a warm room doesn't turn it orange.

Lighting is unchanged: lit by the room the eye is in (that room's baked SH, which dims with the
room's lights-off state, its panorama for reflections; no real-time sun in sunless rooms), plus a
small warm scatter term on the skin. Its depth is squeezed into the nearest slice of the depth
buffer, so it never pokes into walls. Idle breathing (a slow rise and fall), walk bob, a lowered
run pose, look lag; raised into view when armed. `vm.scrub(clip, t)` holds a pose (screenshots).

## Cost
- Armed: the view model is 4 draw calls (the arm: one skinned mesh, 3 bones; the knife's 3
  materials), 8.9k triangles (arm 7.2k, knife 1.7k), +1 draw call for the streak only during a
  cut's ~0.15 s. Textures: 3 x 1024 (~16 MB of GPU memory once armed). No lights, no shadows.
- Unarmed: nothing drawn. Download +~250 kB (the arm, loaded at start). The knife on the board
  uses the kitchen's existing materials, so it joins the room's batches (+1.6k triangles).
- Bench (`bench.mjs knife_vm --profile gpu`, 2026-10-22, unarmed route): draw calls mean 290.9 /
  max 830, triangles max 972,422, download 19.9 MB, textures 269 MB: counts within noise of the
  previous combat run. frame p95 8.2 ms (budget 7) on a machine shared with other agents' builds
  (33 hitches > 50 ms), timing only.
