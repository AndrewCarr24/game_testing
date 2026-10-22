# Invaders: behaviour and waves

Wave 2, invader-behaviour workstream. The design of the invaders themselves (look, rig,
clips) is the character workstream's (`design/invaders/character.md`); combat is
`viewer/combat.js` (`design/combat.md`). This is how they act.

Code: `viewer/invaders.js` (the squad: waves, entries, shared knowledge, orders, the path
planner's queue, AI LOD, sight / fire / hearing queries), `viewer/invaders_brain.js` (one
invader: senses, states, movement), `viewer/invaders_nav.js` (the nav over the whole house,
rays), `viewer/invaders_world.js` (what's built once for all of them), `viewer/invaders_rig.js`
(the rigged character driven by the brains), `viewer/invaders_body.js` (the instanced stand-in:
until the rig has loaded, or `?invbody=stand`), `viewer/invaders_fx.js` (tracers, muzzle
flashes, the debug overlay). Hook: `viewer/index.html` (one block after the sound effects, one
line in the frame, the great room's glass break shared with the Grimble; the character
workstream's posed-test form `?invaders=x,z,rot,Clip;...` is told apart by its clip names).

## How to see it
- `viewer/index.html?level=mansion`: on by default in the game (off for automated runs:
  `navigator.webdriver` or the bench, unless the URL asks).
- `?invaders=0` off · `?invaders=N` N at once (no waves) · `?invaders=debug` (or `&invdebug=1`)
  the overlay: each one's cones (focal bright, peripheral dim), its path (doors magenta), a line to
  where it thinks the player is (red while it sees them), a label (role, state, notice meter,
  health) · `?waves=fast` (the schedule at a tenth: 6 s / 30 s / 60 s) · `?waves=0` none ·
  `?waves=K` the schedule times K · `?god=1` (combat's: hits show, never die).
- `window.__invaders`: `spawn(role, {entry | at, inside, yaw, post})`, `agents`, `events`,
  `summary()`, `clear()`, `report(by, pos)`.

## Waves
`WAVES = [{at: 60, n: 6}, {at: 300, n: 20}, {at: 600, n: 50}]` (invaders.js): at time `at` the
squad is topped up to `n` alive (at most 50; the dead don't come back). "~6, then 20, then 50"
is read as the squad's strength after each wave, not 6 + 20 + 50 (the perf ceiling is 50 at
once). They arrive three at a time, 1.6 s apart, each at an entry; in mix order:

| invaders | roles |
|---|---|
| first 6 | 2 watchers, the leader (pistol), 2 bats, a knife |
| next 14 | 4 gunmen (rifle), 4 bats, 3 knives, 3 watchers |
| next 30 | gunmen, bats, knives about equally, a watcher in five |

Entries (found from the level: every door on the outer wall, plus the breakable glass): the
front door, the dining and kitchen terrace doors, the garage (its door opens on its signal), the
mudroom's side door, the great room's west glass (the first one there smashes it with two
blows, if the Grimble hasn't). Each entry has spawn points 20-30 m out (connected on the nav,
out of the player's sight when possible), an outside point, an inside point and a watcher post
~11 m out facing it; the facades have posts too (south, north, west, east) for the windows.

## Roles
- **Gunman** (rifle, 3-round bursts, 30 a hit; the leader's pistol 26): holds sightlines, needs a
  clear line of fire (no wall, glass, shut door, furniture or teammate: it sidesteps a teammate,
  and walks round through a door when it sees the player through glass), shoots after a reaction
  + aim delay (0.7-1.6 s after it notices), spread: a snap shot first, steadier over 2 s of
  tracking, worse at a moving target, kicked by each shot of a burst, doubled while it's being
  shot at; takes cover (a nearby spot hidden from the threat, crouched behind low furniture or
  round a corner) between bursts when it's under fire.
- **Bat / knife** (35 / 45 a hit): sweep rooms, chase at 5.5 / 5.8 m/s (the player runs 6.8:
  you can outrun them in the open), swing in reach (windup 0.42 / 0.28 s: a tell), smash the glass.
- **Leader** (the first gunman): turns each new contact into orders (below). While alive the radio
  takes ~1.6 s; once it's dead ~4 s, and everyone near just converges (they bunch).
- **Watcher** (rifle, outside): stands at a door's post or a facade's, scanning; sees further
  (60 m) and notices a player outside twice as fast; shoots anyone outside with a line of fire;
  someone seen through a window is only reported (glass stops bullets): it keeps its post.

## Senses (no cheating: never the player's true position)
- **Sight** (the Grimble's model at human size): a ray from its eyes (1.62 m) to the player's eye,
  stopped by walls, shut doors, closed blinds (`interact.sightBlockers()`), tall furniture, and,
  for a crouched player, low furniture close in front of them; glass doesn't stop a look. A focal
  cone of +-55 deg, a peripheral one of +-100 deg (2.6x slower to notice), and all round within
  1.6 m unless the player creeps up crouched and slow (how a knife takedown happens). The notice
  meter fills in ~0.85 s for a lit, standing, walking player at 10 m (proportional to distance),
  slower crouched (x1.7) or still (x1.4), faster running (x0.6), in the dark (x1/0.35), quicker
  when the squad has had contact lately (x0.45). Out of sight it falls at 0.25/s.
- **Hearing**: `window.__noise` events (thrown things, devices, running footsteps, the player's
  knife), 34 m for a loudness-1 noise in the open, x0.55 through each wall; or round by the
  walkable ways (one walking-distance flood per noise, shared) when that's shorter. The squad's
  own noises are tagged `team: 'invader'` and ignored (their gunshots, kicks, blows on the glass).
- **The squad**: a sighting is shouted (everyone within 20 m with at most one wall between knows
  at once) and radioed (everyone else, after the delay; a dead invader passes nothing on).

## States
arrive (to its entry, through it; a smash at the glass) -> sweep (the squad gives it a room not
cleared lately and not claimed, nearer and bigger first, pulled toward the last contact: 2-6
points spread through it, its hiding spots, some of them: 35%, 85% near a fresh contact; a spot
is checked at most once in 90 s by the whole squad) | post (watcher) | hold (a sightline the
leader gave it: 6-14 m from the contact, a clear look at it, back to a wall) | respond (go to
the reported place) | engage (gun, sees you) | chase -> strike (melee) | cover | pursue (to the
last place seen, then on along the way you were going for a moment) -> search (the rooms nearest
the loss: points it couldn't see from there, the hiding spots within 9 m) | investigate (a
noise: 2 go, 4 for loud ones; a look round, then a short search) | check (a hiding spot: to its
mouth, open it; if the player is in it they're dragged out, `hiding.leave({instant})`, and
attacked) | breach (a locked door between it and where it knows the player is: four kicks, loud,
then the door is unlocked and opened) | flee (under 30 health, not the leader: away to the
farthest entry's outside) | stagger (0.5 s, 0.9 s for a heavy hit) | dead.

Seen climbing into a hiding spot (seen within 1.5 s before `player.hidden`): it goes straight
to that spot and opens it. Not seen: only the sweep and search might.

Hit: stagger, a shout, it knows where the blow came from (it turns, reports, pursues), flees
when badly hurt. Death: falls back, stays; those within 18 m hear it and come to look.

## Doors and floors
The nav (`invaders_nav.js`) is three layers of one 0.25 m grid: the ground (the house's ground
floor, the terraces and the grounds out to the approach, 100 x 95 m), the upper floor (cells over
a floor slab: the upper rooms, the galleries and the stair's landing, not the voids) and the stair
(the ramp over the treads, its height the ramp's lerp; linked to the ground at its foot and to the
landing at its top). Blocked where a static collider reaches into the body's band (0.3-1.9 m above
that layer's floor) within 0.28 m. Doors are portals: their leaves are left out of the grid, their
cells carry the door's id; a shut door costs a little extra, a locked one is impassable (except
for a breach plan, at +40). On the way an invader stops at a shut door, opens it
(`it.target = 1`, the garage by its signal) and goes through when it has swung; doors are left
open behind them (a trace for the player to read). A* (weighted 1.4) over (layer, cell) with the
stair links; connected components (recomputed when a lock changes) reject impossible plans at
once; a goal off the nav (inside furniture, a locked room) goes to the nearest reachable cell.

## Cost (what it adds)
- CPU: 0.02 ms/frame for a few, ~0.3-0.55 ms/frame mean for 50 with the waves running (M4 Pro,
  `invaders_waves.mjs`; spikes of 2-5 ms when several plan at once, ~20 ms once when the glass
  breaks and the nav round it is rebuilt). Build: the nav + ray grids ~25 ms at load.
- AI LOD: senses + brain every frame within 22 m or in a fight, every 3rd frame within 45 m,
  every 8th beyond (staggered by id); movement every frame (every 2nd frame far away); the path
  planner takes at most 6 plans / 2 ms a frame (fights first).
- Draw calls with the rigged character, 50 in the house: ~35 (crowd 10, the 8 skinned ~25), up
  to ~150k triangles (8 x LOD0 10k close up + the crowd at 800 each); the stand-in: 8 draw calls,
  38k triangles. + 2 while shots are flying (tracers, flashes). No shadow casting, no real-time
  lights (the muzzle flash is an additive sprite). The asset: +1.9 MB download, +29 MB textures.
- Bench (`BENCH_QS="&invaders=50" bench.mjs --profile gpu`, harmless under the bench, M4 Pro):
  draw calls mean 290 -> 419, max 837 -> 1088, triangles max 972k -> 1125k, frame p95 6.8 -> 7.9
  ms, gpu p50 13.3 -> 14.0 ms. Most of the draw-call rise isn't the bodies: the great room's
  glass, smashed by an invader, becomes 160 separate shard meshes (grimble_hunt.js `shatter`,
  one Mesh per shard; one merged mesh would be 1 draw call), and every door they open redraws
  the sun's shadow map while it swings.

## Bodies (the character workstream's invader, design/invaders/character.md)
`invaders_rig.js`: the nearest 8 within 22 m are SkinnedMeshes (viewer/invader_asset.js:
cross-fades, a gun's aim / shot / ready pose layered over the legs, the asset's LODs by distance),
lit by their room's probe and panorama like the props (baked.js applyRoom, swapped room to room);
the rest are the instanced GPU-skinned crowd (viewer/invader_crowd.js, LOD2, one clip each).
Handed from one to the other as they come near or go away. The brain's state picks the clip:
dead DeathBack / DeathForward (by where the blow came from), staggered HitFront / HitBack, strike
MeleeBat / MeleeKnife (the brain's windup is taken from the clip's hit event), breach / opening a
hiding spot OpenDoor, legs Run / Walk / CrouchWalk / CrouchIdle (playback rate from the speed, so
the feet stay planted) / Search / IdleAlert / Idle, guns AimRifle / AimPistol, ShootRifle /
ShootPistol per shot, HoldRifle / HoldPistol. Tracers start at the gun's `_Muzzle` marker.
Outfits by id (the leader: a cap), heads: balaclava, mask, cap, hood and combinations.

## Open questions (for the user)
- Waves as strength after each wave (6 / 20 / 50 alive) or as arrivals (6 + 20 + 50)?
- How lethal: a rifle burst at a standing player 20 m away kills in about 2 s now; at the front
  door the watcher kills in ~1-2 s (as asked: going out that way gets you shot).
- The safe way out (the secret passage) isn't built: nothing here knows about it yet; it should
  be off the nav (they never find it).
