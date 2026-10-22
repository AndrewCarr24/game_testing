# Invaders: behaviour (the first five)

Wave 2, invader-behaviour workstream. The design of the invaders themselves (look, rig,
clips) is the character workstream's (`design/invaders/character.md`); combat is
`viewer/combat.js` (`design/combat.md`). This is how they act.

Code: `viewer/invaders_opening.js` (the first five: the arrival, the doorbell, the branches, the
break-in), `viewer/invaders_audio.js` (the chime, knocks and kicks, made in the browser),
`viewer/invaders.js` (the squad: the old waves, entries, shared knowledge, orders, the path
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
  `navigator.webdriver` or the bench, unless the URL asks). The five appear at the gate 30 s in
  and ring the bell ~65 s in. Quicker: `&seq=now&seqfrom=court` (they start on the motor court,
  2 s in: the ring at ~25 s) or `&seqfrom=step` (on the step: the ring at once).
- `?seq=0` no opening · `?seq=N` they appear after N s · `?seq=now` · `?seq=manual` (tests call
  `__invaders.opening.start({from})`) · `?seqk=K` the waits times K · `?seqfrom=gate|court|step`.
- `?waves=old` the old waves instead of the opening (6, 20, 50) · `?waves=fast` (the old schedule
  at a tenth) · `?waves=K` (times K) · `?waves=0` nobody comes.
- `?invaders=0` off · `?invaders=N` N at once (no opening, no waves) · `?invaders=debug` (or `&invdebug=1`)
  the overlay: each one's cones (focal bright, peripheral dim), its path (doors magenta), a line to
  where it thinks the player is (red while it sees them), a label (role, state, notice meter,
  health) · `?god=1` (combat's: hits show, never die).
- `window.__invaders`: `spawn(role, {entry | at, inside, yaw, post, extra})`, `agents`, `events`,
  `summary()` (with `opening`: phase, rings, knocks, handles, the timeline), `clear()`,
  `report(by, pos)`, `opening` (the sequence).

## The first five (the opening)
The user, 2026-10-22: "have the initial five invaders arrive together. They should go to the
front door and ring the doorbell. Scrap the subsequent waves of invaders for now; we should just
think through these five guys." The waves are behind `?waves=old`; the game opens with this.

**How they come: on foot, up the drive from the gate.** Five dark figures inside the shut gate,
walking the 45 m of drive and motor court in a loose group, past the fountain, under the bollards
and up the entry path, is the slow burn: from the entry's glass front the player can watch them
come for half a minute (the gate is 46 m from the door, 25 degrees off the entry's axis). It needs
nothing new (no vehicle asset, no gate interaction: the gate and the drive are the car
workstream's), and it reads as people who walked in like they own the place. The vehicle version
(a van stops at the drive's mouth, its lights sweep the glass, doors slam, they get out) is the
alternative to workshop: it needs a van asset, its arrival on the drive and a light reactor.

**The cast** (silhouettes from the character's variants; `CAST` in invaders_opening.js):
| who | role | weapon | look | in the group | at the door |
|---|---|---|---|---|---|
| the leader | leader | pistol, **holstered** (on the hip: he rings with empty hands) | Navy, cap | in front | beside the door: rings, knocks, tries the handle; draws when it breaks |
| gunman A | gun | rifle, low ready | Charcoal, mask + hood | 1.8 m behind, left | west of the door; looks in the glass |
| gunman B | gun | rifle, low ready | Olive, hood | 2.4 m behind, right | east of the door; stays outside as the watcher |
| the bat | bat | bat | Charcoal, bare balaclava, 7% bigger | 3.9 m behind | behind the leader; keeps looking back down the drive |
| the knife | knife | knife | Olive, the white hard mask, 5% smaller | at the back | at the back, restless (IdleAlert); the face at the glass |

**The sequence** (times in s, the waits scale with `?seqk`):
1. *approach*: they appear at the gate (30 s in) and walk up (1.35 m/s, ~32 s): the leader along
   the drive, the court and the entry path; the others in their places behind him on his trail
   (each keeps its slot: straight at it, or by a path round a planter), a slow sway in their
   spacing. The last 7 m: each to its own place on the step, under the canopy.
2. *gather* (2.5): they settle, facing the door.
3. *ring*: the leader reaches to the door's surround (OpenDoor's reach) and the house's chime
   sounds: `signals.set('doorbell', true)` on the entry's control panel (devices.js, 4 s, the
   panel's screen flashes); the chime is a two-tone ding-dong over the house's speakers, the same
   in every room (flat, with the room's reverb; from outside, from the panel through the glass).
   The tablet's Cameras page has a **Front door** camera (the doorbell's, in the surround).
4. *wait* (10): nobody moves much. The bat looks back down the drive, gunman B along the glass,
   gunman A toward the west lawn, the leader up at the house. Heads turn with the brain's look
   (invaders_rig.js `turnHead`: neck and head, up to 60 degrees).
5. *ring again*, *wait* (8).
6. *knock* on the door's glass (two raps of three knocks), *wait* (5).
7. *handle*: the leader steps to the doors' meeting stiles and tries the handle: locked, a rattle.
8. *peer* (8): the knife and gunman A step up to the glass either side of the door and look in;
   the leader steps back under the canopy.
9. *split*: the leader points (Signal) and they go round the house: the leader to the garage door,
   then back to the front glass; gunman A and the bat round the west to the great room's glass;
   the knife round the east to the mudroom's window, then its side door (the handle); gunman B on
   round the north: the kitchen's glass, the kitchen's door, the dining room's doors (handles).
   The player hears handles rattle round the house (doors 4 in all) for about a minute.
10. *break-in* (nobody answered, ~150 s after they appeared): at once, the leader kicks in the
    front door (four kicks, loud), the bat smashes the great room's glass (two blows), the knife
    kicks in the mudroom's side door; gunman A follows the bat in; gunman B takes the watcher's
    post on the north terrace (or the front door's, whichever is nearer). From there on: their
    brains (sweep, search, hiding spots checked; the leader gives orders).

**The doors are locked to them** while it runs: every outer door's `locked()` is true for the nav
(`latched`: no path goes through it, the brain's breach can kick it in). The player opens them
from inside as usual, and that door stays unlocked to them for good. Their own sounds (the
bell, knocks, handles, kicks) are tagged as theirs: nobody goes to investigate their own ring.

**Branches** (each ends the slow part; their brains keep what they know):
- **Answered**: the player opens a door one of them is near: they turn to it, the leader steps
  up (a 0.8 s beat), then in through it. Melee rush, guns engage: answering the door is deadly
  (in the test the player is hit 8 s after opening it, and dead soon after, without god mode).
- **Seen through the glass** (their senses never stop: a lit entry is seen from the gate, 38 m):
  on the way up, they keep coming (the one who saw points; the others look); at the door they
  ring anyway, once, and watch the player through the glass while they wait (shorter waits, no
  second ring), knock, try the handle, then **stare** (3.5 s: they turn to the player, the gunmen
  aim through the glass, nobody fires: glass stops bullets), then the front door is kicked in.
  Seen after they'd given up on the door (peer, probe): the stare, then in.
- **Heard**: a noise inside while they're at the house (running, a thrown thing, a device): they
  look toward it; a second one (3 s or more later) and they come in. A gunshot: at once.
- **Hiding**: nothing to see; the whole sequence, the break-in, then the sweep (spots included).
- **Seen outside** (the player went out to meet them, or ran for it): straight to their brains:
  the gunmen shoot.
- **Hurt** (the player stabs one through an open door): the hunt.
- **An open door**: one they try that the player left open: in through it, the rest follow.
- **The power is off**: the bell is dead (it needs power); they knock longer and harder.
- **The blinds are down** (the entry's switch or the tablet): they can't see in; it runs as if
  nobody's home.

**What to workshop with the user**
- The arrival: on foot from the gate (built) or a van at the motor court? From the gate's inside
  (they're simply there) or through it (the gate opening for them: the car workstream's gate)?
- The timing: they appear 30 s in, the first ring ~65 s, the break-in ~3 min in. Slower? Should
  the game wait for the player to do something first (go upstairs, open the tablet)?
- The doorbell camera on the tablet: keep it (a great way to see the white mask up close)?
- Answering the door: certain death now (a beat, then they rush). A talk at the door (the leader
  says something, waits for you to let them in, steps in calmly) would need voices; a chance to
  slam it shut again (a longer beat, the leader's foot in the door)?
- Seen through the glass: is the stare (guns raised through the glass, nobody shooting) the
  right beat? How long?
- Who stays outside: one watcher (gunman B) after the break-in. Two (the front and the back)?
  Going out the front would then be lethal again.
- Locked doors: the house is locked to them (a script rule, the player can open any door from
  inside). Real locks the player could set (and the invaders could pick or kick), a smart lock on
  the tablet?
- They have no voices (no `invader_shout` / `invader_alert` in the sound sprite yet): a muttered
  word at the door, the leader's "open up", would change it a lot.
- Missing clips that would help: a knock, a kick (OpenDoor stands in for both), hands cupped to
  the glass, pointing at the doorbell, drawing the pistol.

**Tests** (viewer/tools/invaders_opening.mjs, fast-forward, the suite's harness; scenarios in
invaders_opening_scenarios.js): `arrival` (5 spawned, on the step within 34 s of the gate, the
leader in front all the way, never closer than 0.9 m to each other, each within 0.4 m of its
place), `ring_heard` (the signal, the chime played flat from the kitchen, not unknown, nobody
investigates), `answer`, `glass` (seen, stare, kicked in, no shot before), `hide` (2 rings, 2
knocks, 4 handles, the break-in at 94 s with waits x0.4, nobody found before it, then sweeping),
`glass_left` (seen through a bay west of the door: the kicker turns to fight; still in within 7 s
of the break-in), `invaders_chime.mjs` (the chime and knocks really played through Web Audio,
autoplay allowed; no page errors),
`heard`, `power_off`, `blinds`, `outside`. Real time with photos from inside:
`invaders_opening_live.mjs [from] [ghost|entry]`. The game's default path:
`invaders_default.mjs`.

**Cost**: five invaders, ~0.09 ms/frame AI + 0.06 ms bodies (M4 Pro, `invaders_default.mjs`);
the chime/knock/kick buffers ~0.5 ms each once; the doorbell camera only renders while the
tablet's Cameras page shows it.

## The old waves (`?waves=old`)

`WAVES = [{at: 60, n: 6}, {at: 300, n: 20}, {at: 600, n: 50}]` (invaders.js): at time `at` the
next `n` arrive: 6, then 20, then 50, 76 in all (the user's call, 2026-10-22: arrivals, not the
squad's strength). At most 50 are alive at once (the perf ceiling): the rest wait outside and come
in as others fall; the dead don't come back. They arrive three at a time, 1.6 s apart, each at an entry; in mix order:

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
- (The first five: see "What to workshop" above.)
- The waves (if they come back): as strength after each wave (6 / 20 / 50 alive) or as arrivals (6 + 20 + 50)?
- How lethal: a rifle burst at a standing player 20 m away kills in about 2 s now; at the front
  door the watcher kills in ~1-2 s (as asked: going out that way gets you shot).
- The safe way out (the secret passage) isn't built: nothing here knows about it yet; it should
  be off the nav (they never find it).
