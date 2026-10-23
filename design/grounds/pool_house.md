# The pool house: the bathhouse

## Status (2026-10-23)
Built, rebuilt on main 87454de (the secret passage merged), draft-baked (64 samples, on + lights off:
the six bathhouse rooms and the passage's `tunnel_n`), tested end to end. The next full bake brings
them to 1024 samples with the rest of the house.

## Meeting point with the secret passage (connected)
The passage's room `tunnel_n` (plan.py `UNDERGROUND`) ends at the landing (40, 33), z -4.2,
x 38.5..41.5, y 31.5..34.5; its north wall's opening (y 34.5, x 38.65..41.35, z -4.2..-1.4, the
passage's cut) is the foot of the bathhouse's stair. Merging made these changes: `plan.SECRET_EXIT_STUB`
(their temporary wall) is deleted; `bathhouse_plan.STUB_LANDING = False` (my stand-in landing room is
gone); my duplicate cut on y = 34.5 is gone (theirs does it).
- `ph_stair` is `level=0` with its own `z=(-4.2, 5.4)` (the passage's convention), so the grounds
  still clad its outside and roof it; it carries the passage's below-ground flags: `nav=False`
  (off the invaders' nav), `power="own"` (its lights are the bunker's: `signal=None`, on whatever
  the house's power and the bathhouse's switch), `reverb`, and one new flag, `below=True`. That
  flag is exported to mansion.json; `secret_passage.js` moves its shell into the below-ground group,
  culled with its room, and `batching.js` keeps it drawn from the sealed tunnel. Without it the
  tunnel's `sealed` rule hid the stair: from the landing you saw a blank sky-coloured hole.
- The plan's other bathhouse rooms keep `height` (house.py honours both `z` and `height`).

## The idea

A billionaire in the Blue Ridge who swims would not build a glass box with a bar by his lap pool.
He'd build a bath: the lap pool's axis carried on indoors into still, warm water, a ritual of hot,
cold and steam in rooms of stone, and a long room to rest in with the mountains in a window.

The bathhouse is **half stone, half glass**. One idea answers the three briefs:

- the **glass** half (the bath hall, open to the lawn and the lap pool) is where the beauty is:
  golden light on water, the coursed stone wall lit by moving reflections, the view down the
  water to the house. It's also where the danger is: you are seen;
- the **stone** half (cold plunge, steam, fire bath, the shaft) is where the secret is, and the
  safe way through: rooms of thick walls, no outside glass, steam that no one can see through.

### References

- **Peter Zumthor, Therme Vals (1996)**: the whole vocabulary. Stone laid in thin courses
  (Valser quartzite; here the Blue Ridge's own grey-green gneiss, with its rusty iron stains),
  the same stone inside and out; the baths in stone blocks with no doors, just turns (you turn a
  corner into each room); the *Feuerbad* (a hot pool in a red room) and the cold bath in a dark
  block; the roof's narrow glazed slots that wash the stone walls with light; the rest rooms
  with their reclining chairs facing big framed windows; Vals's grass roof (here sedum).
- **Tadao Ando**: the Water Temple at Awaji (1991), where you descend a stair cut through a lotus
  pond into the temple under it: here the stair rises the other way, out of the earth, past the
  water, and comes up through the bottom of a pool. Ando's board-formed concrete (910 x 1820
  panels, six tie holes each) for the secret stair, a 9.6 m slot of it, lit from a skylight and
  through the water. His sheets of still water (the Church on the Water) for the black reflecting
  pool under the rest room's window.
- **Kengo Kuma**: the cedar lattice veil on the hall's glass (Sunny Hills, the GC Prostho
  Museum, his ryokan at Ginzan Onsen): close-set battens that read as a soft surface and strain
  the low west sun into stripes across the hall. Hung above head height only (3.1 m up), so the
  view down the water stays clear, and so does the danger.
- **Carlo Scarpa**'s water-as-floor (the Querini Stampalia, the Brion tomb's pavilion): the
  stepping stones across the hall's pool.
- The light: the late sun off a pool onto a ceiling or a wall (anyone who has sat by a pool at
  5 pm), here on the 5.4 m stone wall at the end of the hall, and through the pool's glass end
  into the stair as moving blue light.

## The building

World x 27..45, y 31..48.5 (18 x 17.5 m), on the lap pool's axis (the lap pool: y 34.9..40.9,
x -5.5..19.5; the bathhouse's pool has exactly its width and continues its line 7.5 m further
east, behind glass). Floor z 0 (the lawn -0.08). Seven plan rooms, all `building="bathhouse"`.

```
    y 48.5 +-------------------------------------------------+
           |  ph_rest (oak, cedar ceiling, 15 m north window) |  -> black reflecting pool
    y 44.5 +----------------------+-----------+---------------+
           |  north walkway       | ph_cold   |               |
           |~~~~~~~~~~~~~~~~~~~~~~|  plunge   |               |
           |~ pool (6 x 11.2 m)  ~+-----+-----+----------+----+ y 40.5
           |~ stepping stones by ~|ph_  |   ph_steam     |
           |~ the glass          ~|stair|  (hide here)   |
           |~~~~~~~~~~~~~~~~~~~~~~|-4.2 |                |
    y 34.5 |  south walkway       +-----+----------------+
           |  ph_hall (5.4 m)     |  ph_fire (red, hot pool)  |
    y 31.0 +---door---------------+-----------------door-E----+
          x 27 (glass, door)    x 38.5  41.5               x 45
```

| room | size (inside) | height | what |
|---|---|---|---|
| `ph_hall` | 11.2 x 13.2 | 5.4 | the bath hall: glass to the west (1.5 m bays, a glass door on the south walkway), the pool wall to wall, a skylight slot along the east wall, a slot window south |
| `ph_cold` | 6.2 x 3.7 | 3.6 | the cold plunge, dark coursed stone, a slit window east framing a birch |
| `ph_steam` | 3.2 x 5.7 | 2.6 | dark teal glazed mosaic, two-tier benches, frosted glass doors at both ends |
| `ph_fire` | 6.2 x 3.2 | 3.0 | oxblood lime plaster, a 3.5 x 1.2 m hot pool, a sky slot along the north wall, a door east |
| `ph_stair` | 2.7 x 5.7 | 9.6 | the secret stair: z -4.2 to the plunge's floor at -1.2 (17 risers), Ando concrete, a skylight at the top, the pool's glass end as its west wall |
| `ph_rest` | 17.7 x 3.7 | 3.2 | oak floor, cedar ceiling, loungers facing a 15 m window to the north |

The pool runs from the west glass to the east wall, so it **cuts the hall in two**: the north
half (where you arrive) reaches the south half (the doors out) only through the stone rooms
(cold -> steam -> fire) or over seven stepping stones across the water half a metre inside the
glass. That one decision is the whole crossing game.

## The arrival (the secret, no keys)

1. The tunnel ends; ahead, a narrow concrete slot rises 9.6 m to a skylight. Halfway up the
   stair, on the left, the wall becomes glass: you are beside the pool, under its water. Blue
   light moves on the opposite wall (fx caustics), the glass shows the water's depth, the stone
   floor under drifting light, the silver underside of the surface (fx "underwater": the view ray
   is followed into the pool's box, so it has real depth and parallax). Climbing, the water line
   comes down to meet your eye.
2. The head of the stair is a stone wall. On the side wall, a bronze handwheel.
3. Turn it (E, "Open the valve"): above you, the cold plunge drains (its water slides away), and
   after it the stone slab in front of you sinks into the floor (react `delay`): the way opens onto
   the empty plunge's floor, its stone steps rising to the cold room's light.
4. Up the steps: you come up out of a pool. From the cold room's side it's just a plunge with a
   drain valve on the wall: the door to the passage is under the water. Turning that wheel back
   raises the slab, then refills the plunge. The same wheel works from both sides (two switches on
   one signal, `ph_plunge`), so the way back down is there for a player who comes back.

## Golden hour, and being seen

The golden sun (mansion.py LOOKS["golden"]: 19 degrees up, from just south of west) comes straight
down the lap pool's axis into the hall: through the veil it lays stripes across the floor and the
water, and reaches the 5.4 m east wall, where the water's reflections move (fx caustics, warm).
Calm: the water still, the stone warm, the lights low (underwater lights, wall washers in the
skylight slot).

The hall's lower glass is clear. Watchers on the lawn (the invaders' north post, the pool deck)
can see straight in. How a player crosses it:

- **the hidden way** (slow, safe): cold room -> the steam room (its steam blocks sight: the
  `block_sight` react covers the whole room; a player can also "Sit in the steam", a hiding
  spot) -> the fire bath -> its east door -> the garden court, on the side of the building away
  from the house and its watchers; from there south past the tennis lawn and the kitchen garden to
  the drive and the gate;
- **the open way** (fast, exposed): along the hall's north walkway and over the stepping stones,
  half a metre from the glass, in full view; the hall's glass door then opens onto the lawn and
  the lap pool's deck, the south door onto the house's terrace;
- low cover: the hall's long stone benches (crouched behind one, a player is hidden from the side
  it faces).

The invaders don't treat the bathhouse's doors as ways into the house (their entries are the
main house's outer doors: `grounds.house` is the main house only), so none spawn at it; it is a
room they can sweep like any other once they know you're there.

## Exits and the way to the gate

- the hall's **glass door** (west, door_glass, swings out) -> stepping slabs -> the lap pool's
  deck (its east steps) -> the house's north terrace;
- the hall's **south door** (door_plain) -> slabs to the house's terrace (its NE corner) -> the
  east terrace -> the drive -> the gate (x 14..25.5, y -62; viewer/estate_gate.js opens it as you
  come down the drive);
- the fire bath's **east door** -> the garden court (outdoor kitchen, dining pergola) -> south
  across the tennis lawn and the kitchen garden -> the drive.

## Engineering

- `blender/levels/bathhouse_plan.py`: the rooms, cuts and every dimension. Merged into plan.py.
- `blender/lib/house.py`: per-room `z0` / `height`, `floor_holes` / `ceiling_holes` (the slabs
  split round sunken pools and skylights), `exterior_walls(with_room=True)`, roofs skip skylights.
- `blender/levels/bathhouse_shell.py` (called by mansion.py after House.build): the pools' basins
  (the hall's with its glass end), the hot pool, the plunge with its steps, the stepping stones,
  the stair's solid treads + landing + ramp (`along: "z"`), skylight glass, invisible blockers
  over the water, world-aligned UVs so the stone's courses stay level across piers.
- `blender/levels/rooms/bathhouse.py`: finishes, placements, lights (all baked), probes.
- `blender/lib/ph_textures.py`: coursed gneiss, honed slabs, Ando concrete, oxblood lime plaster,
  teal mosaic (numpy, tileable). `outdoor.coursed_stone()`: the same stone for the facades.
- Assets `blender/assets/ph_*.py`: `ph_plunge` (water, blocker, slab: three reacts on one
  signal), `ph_valve` (the wheel: a switch), `ph_pool_water`, `ph_hot_water`, `ph_pool_window`,
  `ph_caustics(_stair)`, `ph_steam` (benches, steam, hiding spot), `ph_door_steam`, `ph_bench`
  (`_long`, `_short`), `ph_lounger`, `ph_handrail`, `ph_towels`. Outdoor (zone): `cabana_veil`,
  `cabana_court`, `cabana_mirror_pool`; `blender/levels/outdoor/pool_house.py` re-laid round the
  building.
- Engine: `viewer/water_fx.js` (new: water surfaces with ripples and Fresnel alpha, caustics,
  the underwater window, steam; one hook in index.html), `interactables.js` react `delay` /
  `delayOff`, the room flag `below` (`batching.js`, `secret_passage.js`; the passage's ramps
  `along: "z"` and below-ground culling carry the stair), `ground_colliders.py` / `grounds.py`
  (no lawn or ground collider under the building, the house footprint is the main house only,
  stone facades), `visibility.py` (cuts marked `facade`), mansion.py (the buildings' own
  lightmap budget, `level.sunken`, the `below` flag).

## Tests (2026-10-23, after the merge, draft bake)
- `node viewer/tools/bathhouse.mjs final`: 38 checks, all pass. The real controller at 60 Hz from the
  passage's landing: up the stair (it glides: max 3.6 cm a frame, at z -1.2 at its head), E at the
  wheel ("Open the valve"), the plunge drains and the slab sinks (all three reacts settle), through the
  slab's opening into the empty plunge, up its steps onto the cold room's floor, into the hall, along
  the north walkway, over the stepping stones, out of the glass door to the lap pool's deck, back in,
  out of the south door to the house's terrace, the east terrace, the motor court, the drive and the
  gate; then the hidden way: cold room -> steam (both doors) -> fire bath -> its east door -> the
  garden court. Screenshots in `build/bathhouse/final/` (`sheet.png`: 12 of them).
- `node viewer/tools/secret_passage.mjs`: 83/83 pass (library -> shaft -> armory -> tunnels -> the
  landing, and back). Together with bathhouse.mjs: library -> the pool deck and the gate.
- `ROOMS=ph_,tunnel node viewer/tools/walls.mjs`: 672 runs, 0 impossible positions. walls.mjs now
  takes name prefixes in `ROOMS`, knows `level.sunken` (the drained plunge), and drops starts its
  spiral found outside their room's rect. The stair has no start of its own (its floor is all
  treads); bathhouse.mjs walks it.
- `outside.mjs`: the hall's glass door passes; the fire bath's east door "fails" only because the
  test walks 2 m straight in and the hot pool's blocker is 1.2 m inside that door (it did get in).

## Cost (perf.mjs, M4 Pro, 1600x900 @2, invaders off)
| view | draw calls | triangles | ms/frame |
|---|---|---|---|
| the hall (south walkway) | 68 | 98k | 0.37 |
| the lawn by the lap pool, looking at it | 110 | 125k | 0.48 |
| the stair | 65 | 93k | 0.36 |
| the passage's landing, looking up the stair | 17 | 16k | 0.23 |
| (the great room, for scale) | 51 | 194k | 0.36 |

The level downloads 21.77 MB and holds 319.6 MB of GPU textures. The bathhouse's share of that:
- ~0.5 MB download: lightmaps, panoramas, nine textures, 19 small models (192 KB).
- ~40 MB GPU:
  - textures: the stone and the slab at 1024, the other seven at 512, plus the facade's copy of
    the stone outdoors (one more outdoor textured draw call);
  - lightmaps, in the buildings' own budget (`lightmap_mb_buildings` 14 MB: the hall at 1024²,
    the rest room at 1024x512, the others at 512), so the house's rooms keep their atlas sizes
    (checked against main: none changed).
- The fx: one draw call each for the pool surfaces, the caustic cards, the window and the steam.
  The bench route never passes the building, so the bench is unchanged.

## Problems found / for later
- iCloud keeps evicting worktree and `.git` files ("dataless") when the disk fills up. Sandboxed
  Blender, node and git can't read them: git SIGBUS, numpy EOF, Cycles "not a PNG". Reading every
  dataless file outside the sandbox before builds and bakes fixes it until the next eviction.
- Every house build must be followed by `bake.py ... --outdoor-only`: the raw export's
  `Mansion_Outdoor_Flat` has 62 primitives (a Group in three.js), and estate_link's
  `splitGateLeaves` throws on it, so the page never loads.
- Audio has no water: no drain, splash or stone-slab sound yet (the valve plays the switch sound).
- The stair's head (the slab, before it sinks) is still on the dark side in the draft bake.
