# Sourwood town kit: what the layout needs (request to the kit agent)

From: the town design/layout workstream (`design/town/brief.md`, `blender/wilderness/levels/laurel_town*.py`).
To: the town buildings-kit workstream (`blender/assets/town_*.py`, status in `design/town/kit_status.md`).
Status: **v1, 2026-10-22**. The names and footprints below are what the blockout places as massing
boxes today. Change a size if the building wants it, but say so in `kit_status.md`: the layout
reads the footprint from there. I re-read `kit_status.md` and swap boxes for your glTFs by name.

The town is **Sourwood, N.C.**: a Laurel River rail and tannery town. There was a chestnut tannin
extract plant, then a hosiery mill, both closed. Today it lives on a rafting outfitter, a motel
and a diner. Architecture: Hot Springs, Marshall and Bryson City (Madison and Swain counties),
1900-1960. There are brick commercial blocks on one street between the river and the hill, a
board-and-batten Southern Railway depot, white frame churches, and identical four-room mill
houses on brick piers climbing the hill behind the mill.

## Contract (so a glTF drops into the box it replaces)
- **Names**: `town_<type>[_<variant>]`, e.g. `town_mill_house_a`. Root empty = the asset name;
  parts `<Asset>_<Part>`. One `.py` per type; variants come from `build(variant=...)`
  or separate names, whichever you like. List every exported name in `kit_status.md`.
- **Frame** (CLAUDE.md): metres, origin at the **floor centre at the front door's sill
  height** (= the pad the layout flattens), **front (street side, main door) faces -Y**. The
  layout rotates by yaw only, so footprints are rectangles: give w (x) x d (y) x h (z, ridge or
  parapet top). The layout's footprint includes porches and steps. Anything below the pad
  (brick piers, a basement, a stoop on a slope) hangs below z = 0: say how deep (`below_m`).
  The layout sinks the hillside lots to fit it.
- **Runtime**: these load in the wilderness runtime (`viewer/wild/`, plain GLTFLoader + Draco),
  not the house's. It has no interactables, no real-time lights and no house materials. It lights
  by the low sun x a baked 1.5 m light map + sky, with aerial haze (`viewer/wild/level.js`
  `litMaterial`). So:
  - **One shared material for the whole kit** if you can: one base-colour atlas (trim sheet,
    2048, WebP) for brick, clapboard, board-and-batten, standing-seam tin, asphalt shingle,
    stone, concrete, painted window sash and doors, glass painted dark into the atlas, signs as
    plain shapes. Opaque only: no transparent glass, no alpha cards except at most one
    alpha-tested material for porch rails and fire escapes (say so if you add it).
    The town merges every static building into one mesh per material, so materials = draw calls.
    Target: **≤ 3 materials across the kit**; the town's whole budget is ~10 draws.
  - Vertex colour `COLOR_0` = baked AO (as `lib/vertex_ao.py` does) is welcome, and so is a
    darker grime ramp at the base.
  - **Triangles**: houses ≤ 3k, commercial blocks ≤ 5k, the hero buildings (church, mill, depot,
    diner, gas station, sheriff) ≤ 12k with interiors. Add a `_LOD1` child at about 1/4 the
    triangles for > 120 m: the town is seen whole from the rail grade at 300-900 m.
  - Draco, as `common.export_gltf`.
- **Interiors**: most buildings are **solid shells** (closed doors, dark windows). The ones
  marked **walk-in** need a real interior the player can enter: doorway ≥ 1.0 x 2.1 m, ceilings
  ≥ 2.6 m, floor at the pad, and room for my evidence props (I place those). Give me a
  `colliders` list in the glTF extras or `kit_status.md` (AABBs in the asset frame: walls, counters),
  or I box the walls myself from your plan.
- **Doors**: name the door node `<Asset>_Door[_n]`, with its hinge at the origin and `interact`
  extras (`rotate`). It is inert in the wild runtime today, but the house's interactables
  read it later.

## Buildings (counts = the blockout's)

| name | what | w x d x h (m) | storeys | walk-in | count | notes |
|---|---|---|---|---|---|---|
| `town_depot` | Southern Railway combination depot: waiting room, agent's bay window to the track, freight room with sliding doors, deep bracketed eaves, board-and-batten, standing-seam roof | 32 x 10 x 8 | 1 | **yes** (waiting room + freight room) | 1 | front -Y = the street; the track runs along +Y; a 1.1 m-high freight platform on the track side (in the footprint); crawl space under the platform (≥ 1.15 m clear: the crouch is 1.1 m) is a hiding place |
| `town_brick_row_a/b/c` | two-storey brick commercial front: storefront (recessed door, transom, big dark panes), three windows above, corbelled parapet; a = hardware/general, b = the old bank (stone trim, corner door), c = plain (post office, barber) | 8 x 20 x 9 | 2 | b and c: front room only | 9 | placed shoulder to shoulder (party walls flush at ±4 m); back door at +Y; vary the brick tone |
| `town_sheriff` | sheriff's office and jail: one-storey brick, flat roof, front office with a big window onto Main St, two barred cells at the back, a carport on the east side | 15 x 13 x 5 | 1 | **yes** (office + cells) | 1 | the window must read from the street: a desk with a phone faces it |
| `town_diner` | 1950s roadside diner: stainless-and-enamel diner car on a block base (Worcester-style barrel roof), kitchen box behind | 20 x 9 x 5 | 1 | **yes** (counter, 10 stools, 5 booths, kitchen, back door) | 1 | front door at the centre of the long side (-Y), steps up 0.6 m |
| `town_gas_station` | 1960s porcelain-panel station: office with a glass front, two service bays (roll-up doors, one open), flat canopy over two pump islands | 26 x 16 x 5 | 1 | **yes** (office + both bays) | 1 | footprint includes the canopy (canopy to -Y over the islands, building at +Y); the bays' back wall has a door to the back lot |
| `town_motel_office` | motor-court office with a carport and a lobby window | 9 x 9 x 4.5 | 1 | lobby only | 1 | |
| `town_motel_wing` | six motel units in a row under one low gable roof, doors and windows to a covered walk at -Y, bathroom windows at +Y | 26 x 10 x 4 | 1 | one unit open (`_Door_3`) | 2 | the two wings form an L; the back lot (+Y) is where the vans are |
| `town_church` | white frame Baptist church: gable-front nave, the **square steeple tower** on the front centre to **21 m** (the cove's backdrop shows it), tall pointed windows, double door up 5 steps | 13 x 26 x 21 | 1 | **yes** (nave with pews, pulpit) | 1 | |
| `town_church_hall` | fellowship hall / Sunday-school wing: one storey, block, low roof | 12 x 16 x 5 | 1 | **yes** (one hall: the long table) | 1 | joins the church's side; door at -Y |
| `town_church_small` | small white chapel (Methodist), gable front, belfry | 9 x 16 x 10 | 1 | no | 1 | |
| `town_school` | 1930s brick (WPA) consolidated school: two storeys, a central entry pavilion, tall windows in bands, a flat roof with parapet | 44 x 15 x 10 | 2 | entry hall only | 1 | |
| `town_mill` | the old extract plant / hosiery mill: three-storey brick block, segmental-arched windows in bays, a monitor roof, a stair tower | 64 x 24 x 14 | 3 | **ground floor** (one big room) | 1 | the loading dock is a separate piece (below) along its +Y track side |
| `town_mill_stack` | round brick smokestack, corbelled cap | 3.2 dia x 34 | | | 1 | the cove's backdrop shows a stack at about 26 m over the ground: 34 m is fine (it stands on a lower pad) |
| `town_mill_dock` | covered loading dock: a 1.2 m concrete platform with a shed roof, roll-up doors into the mill | 44 x 6 x 6 | | open | 1 | it runs along the siding; under the platform is open (cribbed, ≥ 1.15 m: a hiding place) |
| `town_water_tower` | steel tank on four legs with a balcony and ladder, conical cap | 9 dia x 24 | | | 1 | the cove's backdrop shows it: keep the 24 m top and the 8.4 m tank |
| `town_outfitter` | rafting outfitter: an old warehouse with a big sliding door, a wraparound deck, a lean-to of raft racks | 22 x 14 x 7 | 1 | **yes** (shop floor + the rack lean-to) | 1 | river side at +Y |
| `town_general_store` | false-front country store with a deep porch and posts | 12 x 20 x 7 | 1 | no | 1 | |
| `town_mill_house_a/b/c` | mill-village house: four rooms, hip roof (a), side-gable with a front gable (b), saltbox (c); front porch on posts; brick piers | 9 x 10 x 6 | 1 | no | 30 | **on piers**: `below_m` 0.6-1.4 (the lots are on the hill). Same house in a row is the point (the mill village), so vary the paint and porch only |
| `town_house_frame_a/b` | two-storey frame house: a = I-house (two rooms wide, one deep, central door, full porch), b = foursquare (hip roof, dormer) | 10 x 9 x 9 | 2 | no | 10 | |
| `town_bungalow` | craftsman bungalow, deep porch on tapered piers | 11 x 13 x 6 | 1 | no | 8 | |
| `town_garage_1/2` | detached frame garage, up-and-over door: 1 = one car, 2 = two cars | 4 x 7 x 3.5 / 7 x 7 x 3.8 | | `town_garage_2`: **yes** (door open variant `_open`) | 8 | the open two-car garage holds the estate's stolen goods (I place the mansion's own furniture glTFs in it) |
| `town_shed` | small board shed / smokehouse | 3 x 4 x 3 | | no | 10 | yards |

## Structures (walkable)

| name | what | size (m) | notes |
|---|---|---|---|
| `town_truss_span` | steel Pratt through truss, one rail track, ties and rails on a timber deck, a narrow walkway outside one truss | 36 long x 6 wide x 8 high | two spans end to end make the rail bridge into town (the cove's backdrop shows it at x -1585). **Deck walkable**: give me the deck's top z (above the bottom of the end posts) |
| `town_bridge_pier` | cut-stone pier with a pointed upstream nose | 4 x 8 x 10 (scaled in z by the layout) | |
| `town_road_bridge` | 1950s concrete highway bridge span: deck, two 1 m parapets, bent piers | 24 long x 10 wide | three end to end at the west end of town |
| `town_tunnel_portal` | rail tunnel portal: cut-stone face with a semicircular arch, wing walls into the hill, the date stone left blank | face 12 x 10, bore 6 x 7.5, 20 m of lined bore behind it | the rail leaves town through it to the west (an exit). The bore goes dark |
| `town_footbridge` | the outfitter's steel cable footbridge across the river | 60 x 1.5 | optional: the swinging bridge in the cove already exists as a prop |

## Vehicles and street props (instanced; low poly: ≤ 1.5k tris each)

| name | what | size (m) | count |
|---|---|---|---|
| `town_van` | **the invaders' van**: plain dark full-size cargo van, no markings, tinted windows | 5.9 x 2.1 x 2.4 | 8 (behind the motel, in the gas station bay, at the mill dock). If the invader workstream already has a vehicle, use theirs and say so |
| `town_cruiser` | the sheriff's cruiser: a 2000s sedan, light bar, a star on the door (a shape, no lettering) | 5.2 x 2.0 x 1.6 | 1 |
| `town_pickup` | old pickup | 5.4 x 2.0 x 1.9 | 6 |
| `town_car` | sedan | 4.9 x 1.9 x 1.45 | 6 |
| `town_school_bus` | school bus (the yellow is enough, no lettering) | 11 x 2.5 x 3.1 | 1 (parked at the mill dock) |
| `town_boxcar` | 40 ft boxcar, door open on one side | 12.5 x 3.2 x 4.5 | 4 (on the mill siding; inside an open one is a hiding place) |
| `town_raft` | 14 ft river raft (grey), stackable | 4.3 x 2.0 x 0.5 | 12 (racks, the put-in) |
| `town_pole` | utility pole with a crossarm (and a transformer variant `_tx`) | 0.3 x 2.4 x 10 | ~60 (the layout strings the wires) |
| `town_streetlight` | cobra-head streetlight on a pole | 9 high | 12 |
| `town_phone_box` | the telephone junction box on a pole (the one the player can cut later) | 0.4 x 0.3 x 0.7 | 1 |
| `town_pump` | gas pump | 0.9 x 0.6 x 1.8 | 4 |
| `town_crate_stack` | crates and pallets wrapped in plastic | 2.4 x 1.2 x 1.6 | 10 (the mill dock) |
| `town_clothesline` | two T-posts and a line | 8 long | 6 (mill-house yards; I hang the invaders' masks on one: their `Invader_Mask` node) |
| `town_table_phones` | a folding table with ~30 mobile phones laid out in rows, screens dark | 2.4 x 0.8 x 0.75 | 1 (the church hall) |
| `town_fence_picket` / `town_fence_wire` | fence runs, 3 m modules | | |

## Priority (what to build first)
1. `town_mill_house_a`, `town_brick_row_a`, `town_depot`, `town_church`: the silhouettes seen from the
   rail grade on arrival.
2. `town_truss_span` + `town_bridge_pier` (the way in) and `town_water_tower`, `town_mill` + `_stack`.
3. `town_diner`, `town_gas_station`, `town_motel_*`, `town_sheriff` (walk-in, where the turn happens).
4. Vehicles, then the rest.

Anything here that fights the architecture (a size, a style): change it and write why in
`kit_status.md`. That file is the source of truth for sizes once it exists.
