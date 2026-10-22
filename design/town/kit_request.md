# Sourwood town kit: what the layout needs (request to the kit agent)

From: the town design/layout workstream (`design/town/brief.md`, `blender/wilderness/levels/laurel_town*.py`,
worktree `agent-a409a99f3e84f45e5`).
To: the town buildings-kit workstream (`blender/assets/town_*.py`, status in `design/town/kit_status.md`).

**v2, 2026-10-22: replaces v1.** The user changed the brief. The town is now a **present-day, well-kept,
quaint mountain town**, the kind a tech billionaire drives through on the way to his estate. It is
**not** an old mill town. v1's mill-village houses, tannery and hosiery mill are gone or converted,
and new types are added: a fast-food drive-through, a modern gas station with a convenience store,
a small museum, a video store, and **the bar** (the hero location). The names and footprints below
are what the blockout places as massing boxes today. Change a size if the building wants it, but
say so in `kit_status.md`: the layout reads the footprint from there. I re-read `kit_status.md`
and swap boxes for your glTFs by name.

**The town is Sourwood, N.C.**, on the Laurel River flats.
- **Look**: the polished, touristy end of the Blue Ridge towns (Highlands, Blowing Rock, Cashiers,
  Saluda's main street, Dillsboro and Bryson City's depot blocks).
- **Downtown** is restored 1900-1930 brick shopfronts with fabric awnings, hanging flower baskets,
  acorn streetlights, and a repainted green steel truss bridge.
- **The highway end of town** is the real-world mix: a chain-style burger drive-through, a canopy
  gas station with a convenience store, and a 1980s strip plaza whose video store somehow never
  closed.
- **The old mill** is a brewery and lofts now. Its mill-hill cottages are pastel vacation rentals.
- **The roadhouse bar** by the river and the rail tunnel predates all the polish.

Everything is a little too well kept: fresh paint, mown verges, no litter, flower baskets watered.

## Contract (so a glTF drops into the box it replaces)

**Names**
- Use `town_<type>[_<variant>]`, e.g. `town_cottage_a`.
- The root empty is the asset name, and parts are `<Asset>_<Part>`.
- One `.py` per type. Variants come from `build(variant=...)` or from separate names.
- List every exported name in `kit_status.md`.

**Frame** (CLAUDE.md)
- Metres. The origin is the **floor centre at the main door's sill height** (the pad the layout
  flattens), and the **front (street side, main door) faces -Y**.
- The layout rotates by yaw only, so footprints are rectangles. Give w (x) x d (y) x h (z, ridge
  or parapet top).
- The footprint includes porches, steps and canopies.
- Anything below the pad (piers, a basement, a stoop on a slope) hangs below z = 0. Give its depth
  as `below_m`.

**Runtime**
These load in the wilderness runtime (`viewer/wild/`, plain GLTFLoader + Draco), not the house's.
That runtime has no interactables, no real-time lights and no house materials. It lights everything
by the low sun x a baked 1.5 m light map + sky, with aerial haze (`viewer/wild/level.js` `litMaterial`).
So:
- **One shared opaque material for the whole kit** if you can: one base-colour atlas (trim sheet,
  2048, WebP). Glass painted dark into the atlas.
- **Plus one emissive material** for neon, lit signs, the bar's back-bar, shopfront glow and
  streetlights. It is unlit colour x intensity, so neon reads at golden hour and at night with no
  lights.
- At most one alpha-tested material, for railings.
- Signs are **shapes and single generic words at most** (BAR, VIDEO, GAS, an arrow, a burger
  outline). The game has no story text, so no names, slogans, dates or chain branding.
- The town merges every static building into one mesh per material, so materials = draw calls.
  Target: **≤ 3 materials across the kit**.
- Vertex colour `COLOR_0` = baked AO (`lib/vertex_ao.py`) is welcome. Draco, as `common.export_gltf`.

**Triangles**
- Houses: ≤ 3k.
- Shops, the strip plaza, the motel: ≤ 5k.
- Hero walk-ins: ≤ 12k with interiors. **The bar: ≤ 25k**, it is the showpiece.
- Add a `_LOD1` child at about 1/4 the triangles, for > 120 m: the town is seen whole from the road
  and the river at 300-900 m.

**Interiors**
- Most buildings are **solid shells**: closed doors and dark windows. A lit window (the emissive
  material) is fine.
- **Walk-in** buildings need a real interior:
  - doorway ≥ 1.0 x 2.1 m;
  - ceilings ≥ 2.7 m;
  - floor at the pad;
  - room for my evidence props (I place those).
- Give me `colliders` (AABBs in the asset frame: walls, counters, booths) in the glTF extras or in
  `kit_status.md`.
- Name doors `<Asset>_Door[_n]`, with the hinge at the origin and `interact` extras (`rotate`).
  They are inert in the wild runtime for now.

## Buildings (counts = the blockout's)

| name | what | w x d x h (m) | walk-in | count | notes |
|---|---|---|---|---|---|
| **`town_bar`** | **the roadhouse** (hero, see "The bar" below): a long low 1950s cinder-block and board roadhouse with a shallow gable, a deep porch, neon in the windows, a gravel lot | 30 x 18 x 6 | **yes** | 1 | front -Y faces the lot and the road; the river deck is at +Y |
| `town_shop_a/b/c/d` | restored two-storey brick shopfront with a fabric awning, transom, big display windows, two windows above, corbelled parapet. a = boutique/outdoor gear, b = coffee (bench out front), c = ice cream/sweets, d = the bank branch (stone trim, an ATM) | 8 x 18 x 9 | b (coffee) and d: front room | 10 | placed shoulder to shoulder (party walls flush at ±4 m); back door at +Y; vary the brick tone and the awning colour (forest green, burgundy, navy, striped) |
| `town_shop_wide` | a double-width shopfront: outfitter/fly shop, or the real-estate office with photo boards of estates for sale in the window (blank photo rectangles) | 16 x 18 x 9 | real-estate front room | 2 | |
| `town_sheriff` | sheriff's office: a 1990s brick-and-stone public building, flat roof, a flagpole, a big front window, two holding cells, a sally port for the cruiser | 18 x 14 x 5.5 | **yes** (front office + cells) | 1 | the front window looks across the bridge: a desk with a phone faces it |
| `town_depot` | the old board-and-batten Southern Railway depot, restored as the **little history museum**: waiting room with vitrines, freight room with a scale-model table, platform canopy | 32 x 10 x 8 | **yes** (both rooms) | 1 | front -Y = the street; the heritage line runs along +Y; a 1.1 m freight platform on the track side; ≥ 1.15 m crawl space under the platform (a hiding place; the crouch is 1.1 m) |
| `town_church` | white frame church, gable-front nave, the **square steeple to 21 m** (the cove's backdrop shows it), tall pointed windows, double door up 5 steps | 13 x 26 x 21 | **yes** (nave with pews) | 1 | |
| `town_church_hall` | the fellowship hall wing: one storey, low roof | 12 x 16 x 5 | **yes** (one hall with a long table) | 1 | joins the church's side; door at -Y |
| `town_gas_station` | modern gas station: a flat **canopy over 3 pump islands** (white, with a thin lit band) in front, a **convenience store** behind (glass front, coolers, two aisles, the counter), an ice chest and a propane cage outside | 34 x 26 x 6 | **yes** (the store) | 1 | footprint = canopy (at -Y, by the road) + store (at +Y); the store's back door opens to the back lot |
| `town_fastfood` | **burger drive-through**: a chain-style box with a tilted red-brown roof band, big windows, a drive-through window on the east side, a menu-board pylon (blank panels), a dining room with booths | 18 x 14 x 6 | **yes** (counter, kitchen pass, booths) | 1 | the footprint is the building only; the layout lays the drive-through lane around it |
| `town_plaza` | a 1980s strip plaza: one-storey, a flat roof with a mansard fascia, a covered walk. Units: **video store** (lit, posters as blank coloured rectangles, a return slot), laundromat, pharmacy, one vacant | 64 x 16 x 5.5 | **the video store** (racks, counter, a back room behind a door: a wall of TV monitors, see brief) | 1 | units are 16 m each; the video store is the east unit |
| `town_inn` | the boutique inn: a big restored Victorian (wraparound porch, turret, rocking chairs) | 20 x 18 x 13 | lobby | 1 | |
| `town_motel` | a renovated 1960s motor lodge: office + 12 units in an L under a low roof, fresh paint, matching doors | office 10 x 9 x 4.5; wing 26 x 10 x 4 | one unit (`_Door_3`) | office 1, wing 2 | the wing's back lot (+Y) is where the vans are |
| `town_mill` | the old brick mill, **converted**: a brewery taproom on the ground floor (big new windows, a patio with string lights) and lofts above, a monitor roof | 64 x 24 x 14 | the taproom | 1 | +Y = the river side |
| `town_mill_stack` | the round brick smokestack, kept as a landmark | 3.2 dia x 34 | | 1 | |
| `town_water_tower` | steel tank on four legs, conical cap (freshly painted) | 9 dia x 24 | | 1 | the cove's backdrop shows it: keep the 24 m top and the 8.4 m tank |
| `town_school` | 1930s brick school, still in use: two storeys, a flat roof, a new entry canopy | 44 x 15 x 10 | no | 1 | |
| `town_cottage_a/b/c` | the mill-hill cottages, restored as **vacation rentals**: four rooms, front porch, pastel paint, a hot tub on the back deck (a box), a key lockbox by every door | 9 x 11 x 6 | no | 30 | on piers: `below_m` 0.6-1.4 (hill lots). That they are the same house in a row is the point; vary only the paint |
| `town_house_a/b/c` | Church Street houses: a = restored Victorian, b = foursquare, c = craftsman bungalow | 11 x 12 x 9 | no | 18 | |
| `town_garage` | a detached two-car garage, up-and-over door; `_open` variant | 7 x 7 x 3.8 | `_open`: **yes** | 6 | the open one holds the estate's stolen goods (I place the mansion's own glTFs in it) |
| `town_shed` | garden shed | 3 x 4 x 3 | | 8 | |

## Structures (walkable)

| name | what | size (m) | notes |
|---|---|---|---|
| `town_truss_span` | the old steel Pratt through truss, **rehabilitated as the road bridge** into town: repainted green, two 3.3 m lanes with a centre line on a concrete deck, a cantilevered sidewalk outside one truss, LED lamps on the portals | 38 long x 10 wide x 8 high | two spans end to end. The road from the estate crosses it into downtown (the cove's backdrop shows it). **Deck walkable and drivable**: give me the deck's top z |
| `town_bridge_pier` | cut-stone pier with a pointed upstream nose | 4 x 10 x 10 (z scaled by the layout) | |
| `town_footbridge` | a modern steel greenway footbridge (the river walk to Mill Hill) | 64 x 2.5 | |
| `town_tunnel_portal` | rail tunnel portal: cut-stone face, semicircular arch, wing walls, a blank date stone | face 12 x 10, bore 6 x 7.5, 20 m of lined bore | the heritage line leaves town through it to the west (an exit). The bore goes dark |

## Vehicles and street props (instanced; ≤ 1.5k tris each)

| name | what | size (m) | count |
|---|---|---|---|
| `town_van` | **the invaders' van**: plain dark full-size cargo van, no markings, tinted windows. If the invader workstream already has one, use theirs | 5.9 x 2.1 x 2.5 | 10 (behind the motel, the gas station's back lot, the bar's lot, the mill) |
| `town_cruiser` | the sheriff's SUV: a modern police SUV, light bar, a star shape on the door | 5.1 x 2.0 x 1.8 | 1 |
| `town_suv`, `town_car`, `town_pickup` | modern cars | 4.9 x 1.9 x 1.7 / 4.8 x 1.85 x 1.45 / 5.9 x 2.0 x 1.9 | 25 (angle parking downtown) |
| `town_train` | the heritage excursion train: a diesel locomotive and two coaches | 17 + 2 x 20 long x 3.1 x 4.5 | 1 set, parked at the depot |
| `town_raft` | river raft | 4.3 x 2.0 x 0.5 | 10 |
| `town_streetlight` | downtown acorn lamp post (emissive globe) | 4.5 high | 30 |
| `town_highway_light` | cobra-head pole for the highway end | 10 high | 10 |
| `town_bench`, `town_planter`, `town_flower_basket` (on a lamp arm), `town_bollard`, `town_trash_can` | the too-tidy street furniture | | ~60 |
| `town_menu_board`, `town_pump`, `town_ice_chest` | drive-through / gas station props | | |
| `town_crate_stack` | crates and pallets wrapped in plastic | 2.4 x 1.2 x 1.6 | 10 |
| `town_table_phones` | a folding table with ~30 phones laid out in rows, screens dark | 2.4 x 0.8 x 0.75 | 1 (the church hall) |
| `town_crt_wall` | a wall of 20 stacked old TV monitors (emissive screens) | 4 x 0.6 x 2.4 | 1 (the video store's back room) |
| `town_estate_model` | a museum vitrine with a scale model of the estate: the house's footprint, the lawn, the hedge, tiny figures | 3 x 2 x 1.2 | 1 (the museum) |

## The bar (hero): what the interior must hold
It is a long low room with a stage at one end and a back room at the other:
- the **long bar** (14 m) down one side, with a back-bar of lit bottle shelves (emissive) and a
  mirror strip;
- a line of red vinyl **booths** under the windows, each with a small shaded lamp (emissive);
- a **pool table** with one low hanging lamp in the middle of the room;
- a **jukebox** (glowing) by the stage;
- a small raised **stage** with a red curtain;
- ceiling fans, and neon in the windows (BAR, and a beer-bottle shape);
- a door to the **restrooms** corridor;
- the **back room** behind a door by the bar's end: a store room with a table and hooks on the
  wall. I hang the invaders' `Invader_Mask` there.

The river deck (+Y) has steps down to the water.

Shots it must support (brief, "The bar"):
- from the gravel lot at dusk, low, the neon on the porch;
- long down the bar from the door;
- top-down on the pool table's pool of light;
- the jukebox close;
- the back room door ajar.

Ceiling ≥ 3.2 m. Keep the room dark with pools of light; the emissive pieces carry it.

## Priority (what to build first)
1. `town_truss_span` + `town_bridge_pier`, `town_shop_a`, `town_church`, `town_water_tower`: the silhouettes
   seen from the road and the river on arrival.
2. **`town_bar`.**
3. `town_gas_station`, `town_fastfood`, `town_plaza` (video store), `town_depot` (museum), `town_sheriff`.
4. `town_cottage_a`, `town_house_*`, `town_mill` + `_stack`, then vehicles and props.

Anything here that fights the architecture (a size, a style): change it and write why in
`kit_status.md`. That file is the source of truth for sizes once it exists.
