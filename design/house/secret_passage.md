# The secret passage: library -> shaft -> armory -> tunnel -> pool house

## The meeting point (for the pool house workstream and the orchestrator)
**Kept as proposed: the landing is centred on world (40, 33), floor z = -4.2, x 38.5..41.5,
y 31.5..34.5, the tunnel arriving from the south.** It is the last 3 m of the room `tunnel_n`
(plan.py `UNDERGROUND`, rect (38.5, 1.5, 41.5, 34.5), ceiling 2.8 m: z -4.2..-1.4, its ceiling
slab's top at -1.2). Its north wall (y = 34.5) has a full-width opening, **x 38.65..41.35,
z -4.2..-1.4** (the tunnel's interior width and height: plan.CUTS, the last entry of the
underground block). The pool house's stair / lift / hatch starts at y = 34.5 and goes north.
Until it exists an invisible wall closes the opening (`plan.SECRET_EXIT_STUB`, a collider tagged
`stub: true` in mansion.json); delete that entry when the pool house's way up lands. The
landing's light is a cold bulkhead on its east wall at y 33 (rooms/tunnel_n.py); nothing of
mine stands north of y 34.5.

## The idea
The modal secret passage is a book you pull and a bookcase that swings. This one keeps the
library's surfaces exactly as they are and makes two everyday things into the mechanism, then
lets the descent change the light from warm to cold, so the armory reads as the library's
other self.

1. **The ladder is the latch.** The library's rolling ladder hangs on its bronze rail along the
   south bookcases. Push it (E: "Push the ladder") and it rolls 4.55 m east along the rail to the
   end of its run, beside a brass-inlaid panel in the oak floor. The floor answers: the panel's
   boards sink, the nearest first, each stopping one riser lower than the last, until the floor in
   front of the books has folded down into a stair (twelve treads and a landing plate). It's the
   real "hidden staircase" Creative Home Engineering builds (a staircase that folds flat into the
   floor), done with the library's own boards. Nothing says it: the clue is in plain sight (a
   ladder parked at one end of a long rail, a brass rectangle in the floor at the other end), and
   the reveal is a movement, not a door.
2. **A slot into the den.** Below the library the stair drops through a narrow concrete shaft that
   stands in the den's south-east corner. From the den it's a green fabric box in the corner by
   the screen wall: an AV closet with a dark glass strip in it (home theatres put the AV rack in a
   closet with a glass panel so the remotes reach it). From the shaft's middle landing that strip
   is a window into the den at eye height: you can stand in the dark and watch the room the
   invaders are searching. It's a modern laird's lug (Castle Fraser's hidden listening chamber
   over its great hall) or a hagioscope (the medieval "squint" that let you see the altar from a
   side room). The glass is smoked: from the lit den you see your own reflection.
3. **Warm to cold.** The shaft's stair is blackened steel plate with open risers (the entry's
   floating stair, in steel), a scissor stair round a steel spine in a 1.95 m concrete slot.
   Each flight's handrail has a LED line under it: 2700 K under the library, 4000 K at the den,
   6000 K at the bottom, the armory's colour. You walk out of the library's amber into a white
   that has no warmth in it at all.
4. **The library's twin.** The armory is the library again, in steel: the same 1.18 m bay rhythm
   along one long wall, but the bays are a gun-safe wall in brushed stainless, its five doors
   hinged at the top so that when the wheel turns they lift one after another from the centre out,
   like the lids of jewel cases, each bay lit inside on charcoal felt. Where the library has its
   reading table under a linear pendant, the armory has a stainless layout table under two cold
   ceiling lines; where the library has armchairs and lamps, the armory has a gunsmith's bench,
   a security desk with a bank of monitors, white battery units on the wall (the bunker's own
   power: its lights don't go out with the house's), a transfer switch, an NBC air-filter unit,
   and shelves of water drums and ration cases. Polished dark concrete underfoot holds the light
   lines. Expensive, cold and quiet: Vivos xPoint and the Survival Condo (a missile silo turned
   luxury bunker, with its own armory and shooting range), Rising S's vault armories, a Purdey
   gun room, an Apple Store's restraint.
5. **The tunnel makes the length a choice.** Through the blast door (Cheyenne Mountain; the
   Greenbrier's Project Greek Island, whose blast doors were hidden behind a hotel's wallpaper)
   the service tunnel runs 48 m east under the courtyard, the galleries, the garage and the
   terrace: raw concrete, a galvanised cable tray and conduit, a drainage channel, a caged bulkhead
   every 6 m (pools of light with dusk between them), standing water where the courtyard's
   planting leaks through. At the turn, the pump room: two blue sump pumps over a grated pit
   under an amber work lamp, the loudest thing down here. Then north, 30 m: two lit bays, then the
   bulkheads are dead for 16 m (one hangs off its screw) and the floor is a sheet of black water
   that holds the far lights upside down (Tarkovsky's Stalker, the flooded tunnel of the Meat
   Grinder), and the only light is ahead: the landing's cold lamp, like the disc of sky at the end
   of James Turrell's Alpha (East) Tunnel at Roden Crater. Then the landing, and the pool house.

## The route (world metres, Blender axes; plan.py "below ground")
| Stage | Where | Floor z |
|---|---|---|
| The folding floor | library, x -15.6..-14.65, y -19.49..-15.44 (local x 1.4..2.35, y -4.24..-0.19) | 4.6 -> 2.22 |
| The ladder | rest at library local (-3.7, -4.165), rolls to (0.85, -4.165) | 4.6 |
| `secret_stair` (shaft) | rect (-15.75, -20, -13.5, -14.52), z -4.2..4.2, in the den's SE corner | |
| L1 (button) | y -19.85..-18.8, under the library's bookcases | 2.22 |
| L2 (the slot) | y -15.72..-14.67; slot in the west wall y -15.55..-14.75, z 1.47..1.69 | 0.02 |
| L3 | y -19.85..-18.8 | -2.18 |
| bottom, steel door N | door x -15.45..-14.25 on y = -14.52 (`bunker_door`) | -4.2 |
| `armory` | rect (-17.5, -14.52, -10, -0.5), 3.4 m high | -4.2 |
| blast door | x = -10, y -3.4..-1.4 (`blast_door`, swings into the armory) | -4.2 |
| `tunnel_e` | rect (-10, -3.9, 38.5, -0.9), 2.8 m high, 48.2 m | -4.2 |
| `pump_room` | rect (38.5, -6.5, 45.5, 1.5), 3.2 m high | -4.2 |
| `tunnel_n` + landing | rect (38.5, 1.5, 41.5, 34.5); landing y 31.5..34.5 | -4.2 |

Stair: 48 risers of 0.1833 m, goings 0.28 m (33 degrees, a steep service stair), lanes 0.95 m;
F1 13 risers (the folding floor), F2 12, F3 12, F4 11. Headroom over every landing and under
every flight >= 1.98 m (L1 sits under the library's floor slab; the folding floor's landing plate
opens the slab over the rest of it).

From the library's door to the landing it's ~115 m of walking: ~10 m of stair (four flights),
14 m of armory, 48 m east, 6 m of pump room, 33 m north.

## How it's built (all general, for later spaces below ground)
- **plan.py** (block at the end): `LEVEL_Z[-1] = -4.2`, `HEIGHT[-1] = 2.8`; `UNDERGROUND` rooms
  merged into `ROOMS` (a room may give its own `z=(z0, z1)`); `kind="shaft"` pierces the rooms it
  stands in; `HATCHES` (rectangles cut out of every slab in their z range; `fold=` fills one with
  floor strips that drop into a stair); `FLIGHTS`, `LANDINGS`, `DIVIDERS`; `SECRET_EXIT_STUB`.
  Room flags: `nav=False` (off the invaders' nav), `sealed=True` (nothing above ground is seen
  from it), `power="own"` (lit whatever the house's power), `reverb`, `lightmap=(w, h)` (a fixed
  atlas outside the house's shared lightmap budget, so the house's rooms keep their sizes).
- **house.py**: `z_range` honours `z`; `slab()` (floor/ceiling minus the shafts through it and the
  hatches); `lining_shaft_holes()` (a host's walls are cut where a shaft stands) and `shaft_walls()`
  (the host's own walls round it, its finish, baseboards); the host's air minus the shaft (lightmap
  charts); `fold_floor()` (the strips: the hatch room's floor material and lightmap chart, each its
  own mesh `Mansion_<room>_<mat>_foldNN` with a `react`: slide down by its drop, collide, motor
  false; durations grow with the drop so the floor sinks and leaves a step behind at every
  strip); `flight()` (plate treads, rails, LED line, an invisible ramp `along: "z"`); exterior
  walls / roofs / exterior doors / facades skip everything below ground; smoked glass for a cut
  with `glass="smoked"`; ceiling strips may have their own `color`; colliders of rooms below ground
  are tagged `under` (kept out of the sun's shadow box).
- **mansion.py**: fixed lightmap sizes for rooms that ask; room flags into mansion.json; rooms below
  ground never get direct sun; placements may carry `weapon_slot` (written to props).
- **Engine**: `viewer/secret_passage.js` (new): registers the shell's moving pieces with the
  interactables; while the floor is shut it merges them into the library's floor mesh (0 extra
  draw calls) and hides them; moves the rooms below ground into their own group, culled with their
  room; hides the house's shell, the grounds and the sky while the eye is in a sealed room.
  `batching.js` RoomCuller: rooms below ground resolve first by their own height span (smallest
  wins), level -1, sealed rooms show nothing above ground, rooms below ground are drawn from above
  only when the room sees them (the den's slot) or a shaft's floor is open (`force`).
  `player.js`: ramps along z, and with stacked flights the highest ramp the feet can step onto.
  `invaders_world.js` / `invaders_nav.js`: rooms with `nav: false` are never swept, their cells are
  blocked on every layer whose floor lies in their height span, their doors aren't portals;
  reactors below ground aren't doors. `house.js`: `power: "own"` rooms stay lit with the power off;
  rooms below ground first in `roomAt`. `audio.js`: below ground no wind, more ventilation air, the
  hum on the bunker's power; per-room `reverb`. `index.html`: the hooks (marked "secret passage").
- **Interactables, no new types**: the ladder is a `switch` (library_ladder_secret: the whole
  ladder is the moving part, `travel` 4.55 m), the folding floor's strips are `react`s on its
  signal `secret_library`, the two buttons in the shaft (secret_button) are switches on the same
  signal (every switch on a signal follows it: press one below and the ladder rolls back above).
  The doors are `rotate` (bunker_door, blast_door). The safe wall's wheel is a `switch` and its
  doors `react`s on `armory_safe`. Everything here has `motor: false` / works without the house's
  power: the way out can't be cut off.

## Weapons (set dressing now)
The safe wall holds rifles, shotguns, a bat and pistols as static props. Each is a placement in
rooms/armory.py with `{"weapon_slot": "<kind>"}`, written to `mansion.json props[].weapon_slot`, so
the weapons workstream can find them and turn them into pickups. No weapon logic was added.

## Assets
Mine: library_ladder_secret, library_floor_inlay, secret_button, bunker_kit (the shared palette:
no new textures; the concrete reuses the garage's map). Built by sub-agents to specs.md "Below
ground": armory_safe_wall, armory_rifle, armory_shotgun, armory_pistol, armory_bat, armory_table,
armory_bench, armory_security, armory_power, armory_supplies, tunnel_bulkhead(_dead),
tunnel_conduit, tunnel_channel, tunnel_puddle(_small), pump_station, bunker_door, blast_door.

## Light
Baked like every room (LIGHTS in rooms/secret_stair.py, armory.py, tunnel_e.py, pump_room.py,
tunnel_n.py), every light `signal=None` (the bunker's own power: on in both bake states, never
switched). The library's and the den's atlases changed (the folding floor, the shaft's walls in the
den, the den's moved screen wall and sconces) and need re-baking with them.

## Tests
`node viewer/tools/secret_passage.mjs <out>`: the whole walk and back, screenshots at every stage.
`ROOMS=secret_stair,armory,tunnel_e,pump_room,tunnel_n node viewer/tools/walls.mjs`: 0 impossible
positions in the new rooms (walls.mjs learnt `ROOMS=` and floors below ground).

## Cost (measured 2026-10-23, M4 Pro, other agents' builds running)
`node viewer/tools/bench.mjs` (the house route never goes below ground), before = this branch's
start (main 2191042, label sp_base) / after (sp_after):

| | before | after | budget |
|---|---|---|---|
| download | 19.72 MB | 21.15 MB | 23.0 |
| textures (GPU) | 269 MB | 281 MB | 375 |
| draw calls mean / max | 294.8 / 827 | 290.7 / 830 | 296 / 850 |
| triangles max | 972k | 974k | 977k |
| gpu frame p95 | 9.6 ms | 6.6 ms | 7.0 (noise: the machine was busier for "before") |
| soft gpu p50 | 309.7 | 311.0 | 302 (over in both runs) |

The +1.4 MB are the five rooms' lightmaps, panoramas and lights-off maps (1024x512 for the
armory, 512 for the others: 8.4 MB GPU outside the house's lightmap budget, so no house room
changed size) and the props' Draco geometry (~0.3 MB); no new textures. While the folding floor is
shut it costs 0 draw calls (merged into the library floor); open, 13. Below ground (1600x900 @2,
`build/sp_cost.mjs`): armory 76 draw calls / 126k triangles, the tunnels 32 / 34k, the shaft at the
slot 124 / 200k (it sees the den), against the great room's 264 / 380k: the sealed rooms draw nothing
of the house, the grounds or the sky.

## Tests (2026-10-23)
- `node viewer/tools/secret_passage.mjs build/secret_passage/final`: all 83 checks pass. The whole
  walk with the real player physics at a fixed 60 Hz (W held, steered): the ladder (E, the real key),
  the floor folds, down F1-F4 (on each landing's floor, never inside a box, no falls), the steel door,
  the armory sealed, the safe wall's wheel, the blast door, the east tunnel, the pump room, the north
  tunnel's dark stretch, the landing; back to the shaft (not sealed), up F4-F1 into the library, the
  ladder back: the floor shuts. Screenshots 01-14 there (library before / after / shut again).
- `ROOMS=secret_stair,armory,tunnel_e,pump_room,tunnel_n,library,den node viewer/tools/walls.mjs`:
  672 runs, 0 impossible positions.
- In-page checks (build/sp_check.mjs): footsteps below ground are concrete (on the shaft's stair
  too); both buttons in the shaft toggle the floor and the ladder rolls with them; the safe wall's
  wheel lifts all five doors. From the lit den the slot reads as a strip of dark glass
  (`15_den_side_of_the_slot.png`). The standard 32 views (`shots.mjs sp_after`) show every
  unchanged room lit as before (the rebuilt shell's atlases match their bakes).
- `tour.mjs` (the entry stair, after the ramp change): all pass. `invaders_smoke.mjs`: runs, sweeps,
  doors as before.

## Bakes
Draft bakes only, of the rooms changed or added: library (256 samples: at 64 the folding floor's
strips came out blotchy), den, secret_stair, armory, tunnel_e, pump_room, tunnel_n (64, on + lights
off). The next full bake brings them to 1024 with the rest.

## Known limits / for later
- The landing's north edge is closed by `SECRET_EXIT_STUB` (a plain concrete wall + collider) until
  the pool house's way up is built from y = 34.5; remove the stub then.
- The invaders don't path below ground (nav false); a sighting through the den's slot is possible
  (glass passes sight) but they can't follow. Their bodies still draw while the player is in a sealed
  room (frustum-culled only): the invader workstream could hide them like the house.
- Weapons are set dressing with `weapon_slot` (15 placements: 7 rifles, 4 shotguns, a bat, 3
  pistols; rooms/armory.py); the pistols lie on the middle bay's tray (the pegboard's pegs are empty:
  placements only turn about z, so a pistol can't hang on them).
