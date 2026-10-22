# The pool house: the bathhouse

## Meeting point with the secret passage (for the orchestrator)

Taken as given: the passage's tunnel ends at a landing centred on world (40, 33), floor z -4.2,
x 38.5..41.5, y 31.5..34.5, arriving from the south. The bathhouse owns everything north of
y = 34.5 at that landing:

- `bath stair` = plan room `ph_stair`: rect (38.5, 34.5, 41.5, 40.5), `level=-1`, `z0=-4.2`,
  `height=9.6` (a 9.6 m concrete shaft from the tunnel's floor to the bathhouse's roof).
- The opening between them: `plan.CUTS` axis "x", line y = 34.5, span x 38.65..41.35,
  z -4.2..-1.3 (2.7 x 2.9 m). It cuts the passage's landing's north lining too, if it has one on
  that line. Their landing's ceiling must be at least -1.3 (the opening's head) and their slab must
  stay under -1.0: the fire bath's hot pool basin sits over the landing down to z -0.95.
- Until their landing exists, `blender/levels/bathhouse_plan.py` adds a stand-in room
  `tunnel_landing` at exactly their landing's rect (z -4.2..-1.2, concrete), so the stair can be
  walked and tested. **Merge: set `STUB_LANDING = False`** in bathhouse_plan.py once their landing
  room is in the plan (and rebuild).
- My plan data lives in its own file (`blender/levels/bathhouse_plan.py`), merged at the end of
  `plan.py` by one marked block (`ROOMS.update`, `CUTS +=`, `LAWN_HOLES`), so it merges with
  whatever the passage workstream adds to plan.py. Rooms use explicit `z0` / `height` (house.py
  now honours them) rather than a new `LEVEL_Z` key; the passage's rooms can use either.

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
| `tunnel_landing` | (stand-in) | 3.0 | the passage's landing until it's merged |

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
  the underwater window, steam; one hook in index.html), `player.js` ramps `along: "z"`,
  `interactables.js` react `delay` / `delayOff`, `batching.js` the room under the eye below
  ground, `ground_colliders.py` / `grounds.py` (no lawn under the building, the house footprint
  is the main house only, stone facades), mansion.py (the buildings' own lightmap budget,
  `level.sunken`).
