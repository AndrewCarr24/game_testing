# Town buildings kit: status (kit agent -> layout agent)

Source of truth for the names, sizes, footprints, entrances and triangle counts of `blender/assets/town_*.py`.
**Generated** from the sidecars by `python3 blender/assets/town_status.py` (re-run after builds).
Each asset exports `assets/models/<name>.gltf` (+ `.bin`, Draco) and a sidecar `assets/models/<name>.json`
(size, bounds, `below_m`, colliders, entrances, tris, lights, notes). Answers `kit_request.md` **v2**.

## Contract
- **Frame**: metres; origin = floor centre at the main door's sill (z = 0 = the pad); front (street, main door) -Y;
  yaw-only placement. `below_m` = how far anything hangs below the pad. Footprints below include porches,
  steps, canopies, platforms and decks: `[x0, y0, x1, y1]` in the asset frame.
- **Materials: 2 for the whole kit.** `M_Town_Atlas` (opaque; base colour `T_Town_Atlas`, 2048, WebP in the
  export) and `M_Town_Glow` (the same atlas as emission: neon tubes, lamp shades, bulbs, back-lit bottles,
  screens, lit signs, streetlight globes; draw it unlit, colour x intensity). No transparency anywhere, no
  alpha-tested material: glass is painted into the atlas (window cells show curtains, blinds, a cafe's pendants,
  shelves, tapes...; sash frames painted in). Materials are single-sided (`doubleSided` false): from inside a
  walk-in, its windows' painted glass culls and the street shows through.
- **COLOR_0 (`AO` in Blender) on every mesh**: 1 = unchanged. Two uses, both multiplied into the base colour:
  (1) **tints** (`tints` in the sidecar: whole parts recoloured, e.g. brick tones, so one region serves several
  buildings); (2) **baked interior light** in the walk-ins (their lamps and glowing pieces baked with Cycles:
  warm pools under the shades, a pink wash under the neon, dark between). Outside the rooms it stays 1 (or the
  tint). For the film-set look inside a walk-in, shade its interior unlit (albedo x COLOR_0, about x 1.3) or at
  least do not let the sky light flatten it; the lamps are also listed in the sidecar (`lights`).
- **How one atlas repeats**: faces are split at every tile boundary of their world-scale UVs (u along a wall, v =
  height), so each piece maps inside its region (8 px wrapped gutters). Regions: board-and-batten white /
  charcoal / sage, lap siding cream / white, ledgestone, fieldstone, red brick, white brick, black and green
  standing seam, architectural shingle, corrugated, cedar, painted block, concrete, asphalt, deck boards, plaster,
  wood floor, checker, tile, dark wood, varnished wood, polished concrete, windows, signs, a flat palette (64
  swatches incl. each big region's mean colour, which the LOD1s use). Layout: `assets/textures/town_polyhaven.json`.
- **LOD1**: a child mesh `<Root>_LOD1` in the same glTF, palette swatches only, for > 120 m (hidden in the
  Blender previews). Triangles below.
- **Colliders**: AABBs `[x0, y0, z0, x1, y1, z1]` in the asset frame, in the sidecar and in the root node's extras
  (`town`, a JSON string). Walk-ins: walls split at the doors; counters, booths, tables, shelves, stairs.
- **Doors** of walk-ins: `<Root>_Door_<n>` empties at the hinge with `interact` (`rotate`) extras, leaf meshes under
  them. The door openings have no static collider (a closed leaf is inert in the wild runtime). Other doors are
  closed and part of the walls.
- **Signs**: pictograms only (cup, burger, mountains, cassette, star badge, cocktail glass, pediment, pump), plus
  neon tube shapes; one generic word, **BAR**, in neon at the roadhouse. No names, slogans, dates, brands.
- **Scans** (Poly Haven, CC0) behind the atlas: weathered_plank_siding, white_planks_clean, rustic_stone_wall_02,
  stone_wall, factory_brick, whitewashed_brick, japanese_cedar_planks, worn_corrugated_iron, metal_plate,
  concrete_floor_02, asphalt_02, weathered_planks, painted_plaster_wall, wood_floor_worn, dark_wood, wood_table_001,
  smooth_concrete_floor, old_linoleum_flooring_01, square_tiles.
- **References** (what the look is matched to): Marshall NC Main Street (Commons `Main_Street,_Marshall,_NC_(39724136513).jpg`),
  Saluda's Main Street (`Saluda_Historic_District.jpg`, `Thompson's_Grocery_Market.jpg`, `Saluda_Library_and_Old_Rail_Depot.jpg`),
  Hot Springs NC (`Town_of_Hot_Springs_and_Bridge_Street.jpg`, `Bridge_over_the_French_Broad_River.jpg`,
  `Dorland_Memorial_Presbyterian_Church,_Hot_Springs,_NC_(46619175092).jpg`), the polished new-build look of
  Highlands / Blowing Rock / Cashiers main streets (stone bases, board-and-batten, black standing seam).

## Assets

| name | what | w x d x h (m) | footprint [x0, y0, x1, y1] | below_m | walk-in | entrances | LOD0 / LOD1 tris |
|---|---|---|---|---|---|---|---|
| `town_bar` | **the roadhouse (hero)**: cinder block + board, deep porch with neon (BAR, bottle, cocktail, star), roof sign, river deck with steps to the water; inside a 14 m bar, back bar, 5 booths, pool table, jukebox, stage, restroom hall, back room (table, hook rail, monitors) with its door ajar | 30.9 x 21.05 x 9.269 | [-14.9, -9.05, 15.95, 12.0] | 1.8 | **yes** | door -Y at (5.5, -9.1) w 1.2 (TownBar_Door_1, across the porch); door +X at (14.1, -1.0) w 1.0 (TownBar_Door_2, back exit from the hall); door +Y at (-9.5, 6.1) w 1.0 (TownBar_Door_4, to the river deck (steps down at x -6.9..-5.1)) | 25042 / 66 |
| `town_bench` | park bench, cedar slats, black ends | 1.8 x 0.59 x 0.95 | [-0.9, -0.3, 0.9, 0.3] | 0.0 | no | - | 272 / 10 |
| `town_bollard` | black bollard | 0.24 x 0.24 x 0.95 | [-0.12, -0.12, 0.12, 0.12] | 0.0 | no | - | 54 / 10 |
| `town_bridge_pier` | cut-stone pier with a pointed cutwater; origin = cap top (bearing seat 0.95 m under the spans' deck top); scale in z | 4.6 x 10.14 x 10.12 | [-2.3, -5.9, 2.3, 6.0] | 10.0 | no | - | 220 / 10 |
| `town_car` | modern sedan, silver | 2.04 x 5.04 x 1.444 | [-0.925, -2.4, 0.925, 2.4] | 0.0 | no | - | 466 / 20 |
| `town_car_blue` | sedan, navy | 2.04 x 5.04 x 1.444 | [-0.925, -2.4, 0.925, 2.4] | 0.0 | no | - | 466 / 20 |
| `town_car_red` | sedan, red | 2.04 x 5.04 x 1.444 | [-0.925, -2.4, 0.925, 2.4] | 0.0 | no | - | 466 / 20 |
| `town_church` | white frame church, square steeple to 21 m (belfry, clock face without numerals, spire, cross), pointed windows, double door up 5 steps; walk-in nave (20 pews, chancel) | 12.9 x 29.18 x 21.9 | [-6.45, -16.9, 6.45, 12.35] | 0.9 | **yes** | door -Y at (0.0, -16.8) w 1.7 (TownChurch_Door_1 (left leaf), up five steps) | 11073 / 92 |
| `town_church_hall` | fellowship hall wing: white lap, low gable; walk-in hall with the long table (folding tables, chairs), serving hatch | 12.8 x 17.7 x 5.571 | [-6.4, -9.4, 6.4, 8.3] | 0.0 | **yes** | door -Y at (0.0, -8.1) w 1.4 (TownChurchHall_Door_1) | 4308 / 18 |
| `town_clearance_bar` | drive-through clearance gantry | 4.16 x 0.16 x 3.1 | [-2.08, -0.08, 2.08, 0.08] | 0.0 | no | - | 86 / 10 |
| `town_cottage_a` | mill-hill cottage as a vacation rental (mint): hip roof, front porch, brick piers (below_m 0.9), back deck with a covered hot tub, key lockboxes | 7.9 x 14.54 x 7.825 | [-3.95, -7.02, 3.95, 7.52] | 0.9 | no | door -Y at (0.0, -7.02) w 0.95 (front door, closed (up the porch steps)) | 2810 / 26 |
| `town_cottage_b` | the same cottage, sky blue | 7.9 x 14.54 x 7.825 | [-3.95, -7.02, 3.95, 7.52] | 0.9 | no | door -Y at (0.0, -7.02) w 0.95 (front door, closed (up the porch steps)) | 2810 / 26 |
| `town_cottage_c` | the same cottage, butter yellow | 7.9 x 14.54 x 7.825 | [-3.95, -7.02, 3.95, 7.52] | 0.9 | no | door -Y at (0.0, -7.02) w 0.95 (front door, closed (up the porch steps)) | 2810 / 26 |
| `town_crate_stack` | crates on pallets, shrink-wrapped | 2.42 x 1.22 x 1.59 | [-1.2, -0.6, 1.2, 0.6] | 0.0 | no | - | 372 / 10 |
| `town_crt_wall` | a wall of twenty old TV sets, screens glowing | 4.0 x 0.6 x 2.36 | [-2.0, -0.3, 2.0, 0.3] | 0.0 | no | - | 530 / 10 |
| `town_cruiser` | the sheriff's SUV: white over black, light bar (red/blue glow), push bar, star badge pictogram on the front doors | 2.1 x 5.24 x 1.822 | [-0.95, -2.45, 0.95, 2.45] | 0.0 | no | - | 528 / 20 |
| `town_depot` | the depot museum: board-and-batten, deep bracketed eaves, the agent's bay; walk-in waiting room (benches, vitrines, ticket window) and freight room (raised 1.25 m, model table spot); freight platform with a 1.15 m crawl space | 33.8 x 15.6 x 8.6 | [-16.9, -6.6, 16.9, 9.0] | 0.3 | **yes** | door -Y at (-9.0, -6.1) w 1.2 (TownDepot_Door_1, the street door (one step)); door +Y at (-6.0, 5.1) w 1.2 (TownDepot_Door_2, to the passenger platform) | 9460 / 42 |
| `town_estate_model` | museum vitrine with a scale model of the estate | 3.0 x 2.0 x 1.2 | [-1.5, -1.0, 1.5, 1.0] | 0.0 | no | - | 366 / 10 |
| `town_fastfood` | burger drive-through: chain-style box, tilted red-brown roof band (lit underside), burger pictogram, big windows, drive-through window on +X; walk-in dining room (booths, tables), counter, kitchen | 20.75 x 16.55 x 5.8 | [-9.55, -9.0, 11.2, 7.55] | 0.0 | **yes** | door -Y at (-4.5, -7.1) w 1.2 (TownFastFood_Door_1, under the entry canopy); door +Y at (6.0, 7.1) w 1.0 (TownFastFood_Door_2, kitchen back door) | 7698 / 34 |
| `town_flower_basket` | a hanging flower basket (hook at z 0.75) | 0.763 x 0.786 x 0.752 | [-0.2, -0.2, 0.2, 0.2] | 0.0 | no | - | 230 / 10 |
| `town_footbridge` | modern weathering-steel greenway footbridge, 64 m Warren pony truss, 2.5 m deck; deck top z = 0 | 4.0 x 66.0 x 7.43 | [-2.0, -33.0, 2.0, 33.0] | 6.0 | no | path -Y at (0.0, -32.0) w 2.5 (deck top z = 0; the other end at +Y) | 1364 / 58 |
| `town_garage` | detached two-car garage, up-and-over door closed | 7.6 x 8.45 x 4.632 | [-3.8, -4.7, 3.8, 3.75] | 0.0 | no | garage -Y at (0.0, -3.6) w 5.2 (door down) | 570 / 20 |
| `town_garage_open` | the garage with its door up: walk-in, empty floor for the stolen goods (goods_area), bare bulb | 7.6 x 8.45 x 4.632 | [-3.8, -4.7, 3.8, 3.75] | 0.0 | **yes** | garage -Y at (0.0, -3.6) w 5.2 (door up (walk-in)) | 758 / 20 |
| `town_gas_station` | canopy over 3 pump islands (6 dispensers, lit band, LED panels), price pylon, walk-in convenience store (2 aisles, coolers, counter, coffee), ice chest, propane cage, air pump | 27.615 x 30.1 x 6.2 | [-13.5, -21.9, 10.5, 8.3] | 0.0 | **yes** | door -Y at (0.0, -6.1) w 2.4 (glass pair: TownGasStation_Door_1 (left leaf) opens); door +Y at (5.5, 6.1) w 1.0 (TownGasStation_Door_2, back) | 8756 / 122 |
| `town_highway_light` | cobra-head pole, 10 m | 3.3 x 0.7 x 10.05 | [-0.35, -0.35, 0.35, 0.35] | 0.0 | no | - | 98 / 10 |
| `town_house_a` | Church Street: restored Victorian, cross gable with scrolled trim, wraparound porch, a bay | 10.85 x 12.31 x 12.248 | [-4.35, -7.46, 6.4, 4.85] | 0.6 | no | door -Y at (-0.9, -7.46) w 0.95 (front door, closed (up the porch steps)) | 3675 / 26 |
| `town_house_b` | Church Street: brick foursquare, hip roof with a hipped dormer, full porch on brick piers | 9.3 x 12.11 x 10.293 | [-4.65, -7.46, 4.65, 4.65] | 0.6 | no | door -Y at (0.0, -7.46) w 0.95 (front door, closed (up the porch steps)) | 3160 / 26 |
| `town_house_c` | Church Street: craftsman bungalow, cedar shakes, deep bracketed eaves, gabled porch on tapered columns over fieldstone piers | 10.88 x 13.96 x 7.407 | [-5.6, -8.16, 5.6, 5.8] | 0.6 | no | door -Y at (0.0, -8.16) w 0.95 (front door, closed (up the porch steps)) | 2486 / 26 |
| `town_ice_chest` | ice chest | 2.0 x 0.83 x 1.2 | [-1.0, -0.4, 1.0, 0.4] | 0.0 | no | - | 36 / 10 |
| `town_inn` | boutique inn: big restored Victorian, round turret with a conical roof, cross gable, wraparound porch with rocking chairs; walk-in lobby (desk, stairs, fireplace) | 21.2 x 18.35 x 14.8 | [-11.2, -9.9, 10.3, 8.45] | 0.6 | **yes** | door -Y at (-1.0, -9.9) w 1.2 (TownInn_Door_1, up three steps) | 8726 / 70 |
| `town_menu_board` | drive-through menu board (lit panels, blank rows) + speaker post | 3.8 x 0.65 x 2.7 | [-1.45, -0.25, 2.25, 0.25] | 0.0 | no | - | 140 / 10 |
| `town_mill` | the converted brick mill: 3 storeys in bays, segmental arches, monitor roof, stair tower; walk-in brewery taproom (bar, tap wall, tanks, communal tables), river patio with string lights; lofts above lit | 64.6 x 33.35 x 18.381 | [-32.5, -14.35, 32.5, 19.0] | 0.1 | **yes** | door -Y at (-22.0, -12.1) w 1.6 (TownMill_Door_1, the taproom); door +Y at (-26.0, 12.1) w 1.8 (TownMill_Door_2, to the patio) | 21538 / 230 |
| `town_mill_stack` | the round brick smokestack, 35.5 m with its lightning rod | 4.3 x 4.3 x 35.5 | [-2.1500000000000004, -2.1500000000000004, 2.1500000000000004, 2.1500000000000004] | 0.0 | no | - | 1194 / 32 |
| `town_motel_office` | motor-lodge office: lobby window, carport; walk-in lobby (counter, key board, brochures) | 12.4 x 11.1 x 4.921 | [-5.4, -6.0, 7.0, 5.1] | 0.0 | **yes** | door -Y at (-3.3, -4.6) w 1.0 (TownMotelOffice_Door_1, the lobby) | 2299 / 32 |
| `town_motel_wing` | six motel units under a low gable, covered walk on posts, matching red doors, AC units; unit 3 walk-in (bed, TV) | 26.8 x 12.6 x 4.869 | [-13.4, -6.3, 13.4, 6.3] | 0.0 | **yes** | door -Y at (-11.725, -6.1) w 0.95 (unit 1, closed); door -Y at (-7.392, -6.1) w 0.95 (unit 2, closed); door -Y at (-3.058, -6.1) w 0.95 (unit 3, TownMotelWing_Door_3 (walk-in)); door -Y at (1.275, -6.1) w 0.95 (unit 4, closed); door -Y at (5.608, -6.1) w 0.95 (unit 5, closed); door -Y at (9.942, -6.1) w 0.95 (unit 6, closed) | 3112 / 30 |
| `town_pickup` | full-size pickup, red | 2.2 x 6.14 x 1.89 | [-1.0, -2.95, 1.0, 2.95] | 0.0 | no | - | 468 / 20 |
| `town_pickup_grey` | pickup, grey | 2.2 x 6.14 x 1.89 | [-1.0, -2.95, 1.0, 2.95] | 0.0 | no | - | 468 / 20 |
| `town_pickup_white` | pickup, white | 2.2 x 6.14 x 1.89 | [-1.0, -2.95, 1.0, 2.95] | 0.0 | no | - | 468 / 20 |
| `town_planter` | cedar planter with boxwood and flowers | 0.96 x 0.96 x 1.15 | [-0.48, -0.48, 0.48, 0.48] | 0.0 | no | - | 190 / 10 |
| `town_plaza` | 1980s strip plaza, 4 x 16 m units (vacant, laundromat, pharmacy with a green neon cross, video store), shingled mansard over a covered walk; walk-in video store (racks, counter, posters) and its back room (CRT wall spot) | 64.5 x 18.6 x 5.21 | [-32.25, -8.35, 32.0, 10.3] | 0.0 | **yes** | door -Y at (-19.0, -8.1) w 1.2 (vacant, closed); door -Y at (-3.0, -8.1) w 1.2 (laundry, closed); door -Y at (13.0, -8.1) w 1.2 (pharmacy, closed); door -Y at (29.0, -8.1) w 1.2 (TownPlaza_Door_1, the video store) | 5592 / 28 |
| `town_pump` | fuel dispenser | 1.16 x 1.285 x 2.0 | [-0.58, -0.3, 0.58, 0.3] | 0.0 | no | - | 278 / 10 |
| `town_raft` | 14 ft grey river raft | 4.696 x 2.054 x 0.48 | [-2.15, -1.0, 2.15, 1.0] | 0.0 | no | - | 478 / 10 |
| `town_school` | 1930s brick school: two storeys of window bands, flat roof, entry pavilion with a new steel canopy (shell) | 44.12 x 19.46 x 10.32 | [-22.0, -11.9, 22.0, 7.5] | 0.0 | no | door -Y at (0.0, -8.8) w 3.0 (double doors under the canopy, closed) | 7908 / 104 |
| `town_shed` | board-and-batten garden shed | 3.4 x 4.4 x 3.446 | [-1.7, -2.2, 1.7, 2.2] | 0.0 | no | door -Y at (0.0, -2.1) w 1.0 (closed) | 292 / 18 |
| `town_sheriff` | 1990s brick-and-stone sheriff's office: flat roof, stone portico, big front window, monument sign with the star, flagpole, sally port; walk-in lobby + office (the window desk with the phone faces the window), corridor, two barred holding cells | 18.19 x 18.12 x 9.15 | [-9.0, -11.1, 9.0, 7.0] | 0.0 | **yes** | door -Y at (-5.0, -9.5) w 1.2 (TownSheriff_Door_1, under the portico); door +Y at (-0.5, 7.1) w 1.0 (TownSheriff_Door_2, back, from the cell corridor); garage +Y at (6.3, 7.1) w 4.2 (sally port overhead door, closed) | 6311 / 40 |
| `town_shop_a` | brick shopfront, boutique / outdoor gear, forest-green awning | 8.1 x 19.624 x 9.21 | [-4.0, -10.5, 4.0, 9.3] | 0.0 | no | door -Y at (0.0, -9.1) w 1.1 (closed, recessed 1.2 m); door +Y at (2.5, 9.1) w 1.0 (back door, closed) | 2266 / 28 |
| `town_shop_b` | brick shopfront, coffee, burgundy awning, a bench; walk-in front room (counter, espresso, pastry case, tables) | 8.1 x 19.624 x 9.21 | [-4.0, -10.5, 4.0, 9.3] | 0.0 | **yes** | door -Y at (0.0, -9.1) w 1.1 (TownShopB_Door_1, recessed 1.2 m); door +Y at (2.5, 9.1) w 1.0 (back door, closed) | 4082 / 28 |
| `town_shop_c` | painted-brick shopfront (pale pink), ice cream / sweets, striped awning | 8.1 x 19.624 x 9.21 | [-4.0, -10.5, 4.0, 9.3] | 0.0 | no | door -Y at (0.0, -9.1) w 1.1 (closed, recessed 1.2 m); door +Y at (2.5, 9.1) w 1.0 (back door, closed) | 2370 / 28 |
| `town_shop_d` | the bank branch: dark brick, stone pilasters and cornice, an ATM; walk-in front room (teller line, vault door) | 8.6 x 18.78 x 9.21 | [-4.0, -10.5, 4.0, 9.3] | 0.0 | **yes** | door -Y at (0.0, -9.1) w 1.1 (TownShopD_Door_1, recessed 1.2 m); door +Y at (2.5, 9.1) w 1.0 (back door, closed) | 3610 / 24 |
| `town_shop_mountain` | extra: a new-build mountain-style shop (gable front, cedar king-post truss, board-and-batten, black canopy) | 8.9 x 16.802 x 7.2 | [-4.0, -8.5, 4.45, 8.3] | 0.0 | no | door -Y at (0.0, -7.1) w 1.1 (closed (glass)); door +Y at (-2.3, 7.1) w 1.0 (closed (back)) | 1816 / 38 |
| `town_shop_realty` | double shopfront, the real-estate office: photo boards of estates in the windows; walk-in front room | 16.1 x 19.624 x 9.21 | [-8.0, -10.5, 8.0, 9.3] | 0.0 | **yes** | door -Y at (-4.0, -9.1) w 1.1 (TownShopRealty_Door_1, recessed 1.2 m); door -Y at (4.0, -9.1) w 1.1 (TownShopRealty_Door_2, recessed 1.2 m); door +Y at (6.5, 9.1) w 1.0 (back door, closed) | 5392 / 38 |
| `town_shop_wide` | double shopfront, outfitter / fly shop, navy awnings | 16.1 x 19.624 x 9.21 | [-8.0, -10.5, 8.0, 9.3] | 0.0 | no | door -Y at (-4.0, -9.1) w 1.1 (closed, recessed 1.2 m); door -Y at (4.0, -9.1) w 1.1 (closed, recessed 1.2 m); door +Y at (6.5, 9.1) w 1.0 (back door, closed) | 3848 / 38 |
| `town_streetlight` | downtown acorn lamp post, 4.5 m (glow globe) | 0.48 x 0.48 x 4.5 | [-0.24, -0.24, 0.24, 0.24] | 0.0 | no | - | 199 / 10 |
| `town_streetlight_basket` | the acorn lamp post with a flower-basket arm | 1.334 x 0.786 x 4.5 | [-0.24, -0.24, 0.24, 0.24] | 0.0 | no | - | 441 / 10 |
| `town_suv` | modern SUV, white | 2.1 x 5.14 x 1.692 | [-0.95, -2.45, 0.95, 2.45] | 0.0 | no | - | 452 / 20 |
| `town_suv_black` | SUV, black | 2.1 x 5.14 x 1.692 | [-0.95, -2.45, 0.95, 2.45] | 0.0 | no | - | 452 / 20 |
| `town_suv_green` | SUV, forest green | 2.1 x 5.14 x 1.692 | [-0.95, -2.45, 0.95, 2.45] | 0.0 | no | - | 452 / 20 |
| `town_table_phones` | folding table with thirty phones, screens dark | 2.4 x 0.8 x 0.765 | [-1.2, -0.4, 1.2, 0.4] | 0.007 | no | - | 404 / 10 |
| `town_train` | heritage excursion train: road-switcher diesel + two coaches (green and cream, lit windows), 58.7 m; z = 0 at the top of rail | 3.116 x 58.65 x 4.38 | [-1.55, -29.4, 1.55, 29.4] | 0.0 | no | - | 982 / 30 |
| `town_trash_can` | black litter bin with cedar slats | 0.66 x 0.68 x 1.1 | [-0.33, -0.33, 0.33, 0.33] | 0.0 | no | - | 184 / 10 |
| `town_truss_span` | steel Pratt through truss, 38 m, repainted green: two lanes on a concrete deck, a cantilevered sidewalk, LED portal lamps; deck top z = 0 | 10.18 x 39.0 x 8.5 | [-4.3, -19.0, 5.9, 19.0] | 1.0 | no | road -Y at (0.0, -19.0) w 7.0 (deck top z = 0; the other end at +Y) | 4590 / 226 |
| `town_tunnel_portal` | rail tunnel portal: fieldstone face, voussoir arch, keystone, blank date stone, wing walls, 20 m lined bore going dark, track | 24.736 x 26.11 x 10.4 | [-12.0, -4.5, 12.0, 20.0] | 0.0 | no | rail -Y at (0.0, -0.5) w 6.0 (the track enters the bore (+Y), dark at 20 m) | 1404 / 32 |
| `town_van` | **the invaders' van**: plain dark cargo van, no markings, tinted cab and rear glass only | 2.3 x 6.14 x 2.461 | [-1.05, -2.95, 1.05, 2.95] | 0.0 | no | - | 424 / 20 |
| `town_water_tower` | steel tank on four legs (9 m tank, 24 m top), catwalk, ladder, the mountain pictogram, a red beacon | 11.064 x 11.064 x 24.0 | [-6.4, -6.4, 6.4, 6.4] | 0.0 | no | - | 1374 / 100 |

## Notes per asset
- `town_bar`: hooks: {'rail': [13.65, 1.0, 1.7, 13.8, 4.6, 1.8], 'count': 10, 'spacing': 0.36}; rooms: ['bar room 21.7 x 11.6 (14 m bar, back bar, 5 booths, pool table, jukebox, stage)', 'hall 5.8 x 1.8 (restroom doors closed, back exit)', "back room 5.8 x 5.7 (table, hook rail, monitors, safe, kegs): TownBar_Door_3 ajar 28 deg from the bar's end"]; lighting: emissive only (M_Town_Glow) + lamps baked into COLOR_0
- `town_car`: tints: {'Body': [0.62, 0.63, 0.65]}
- `town_car_blue`: tints: {'Body': [0.07, 0.13, 0.32]}
- `town_car_red`: tints: {'Body': [0.55, 0.05, 0.05]}
- `town_church`: rooms: ['nave 11.6 x 23.6 (20 pews, chancel, pulpit)']; top_m: 21.0
- `town_church_hall`: rooms: ['hall 11.6 x 15.6 (the long table)']
- `town_cottage_a`: tints: {'Walls': [0.74, 0.92, 0.82]}
- `town_cottage_b`: tints: {'Walls': [0.76, 0.86, 0.98]}
- `town_cottage_c`: tints: {'Walls': [1.0, 0.92, 0.7]}
- `town_cruiser`: tints: {'Body': [1, 1, 1]}
- `town_depot`: crawl_space: {'box': [1.5, 5.0, -0.3, 16.0, 9.0, 1.15], 'clear_m': 1.15, 'open': '+Y and both ends'}; model_table_spot: [9.0, 0.0, 1.25]; rooms: ['waiting room 13.7 x 9.6 (benches, vitrines, ticket window)', "agent's office 3.8 x 9.6 (bay window, steps up)", 'freight room 13.7 x 9.6 at z 1.25 (open floor, model table spot)']
- `town_fastfood`: rooms: ['dining 7.7 x 10.6', 'kitchen 7.6 x 10.6']; lane: drive-through window on +X at x 9.0, y -2.6..-1.2 (sill 1.0); menu board / speaker / clearance bar: town_menu_board
- `town_footbridge`: deck_top_z: 0.0
- `town_gas_station`: rooms: ['store 17.6 x 11.6 (aisles, coolers, counter, coffee)']; lighting: store interior baked into COLOR_0; canopy LEDs and pylon are glow
- `town_house_a`: tints: {'Walls': [0.95, 0.95, 0.9], 'Bay': [0.95, 0.95, 0.9]}
- `town_house_b`: tints: {'Walls': [0.92, 0.86, 0.82], 'Dormer': [0.92, 0.86, 0.82]}
- `town_house_c`: tints: {'Walls': [1.0, 1.0, 1.0]}
- `town_inn`: rooms: ['lobby 10.8 x 8.8 (desk, stairs to a landing, fireplace, sofa)']; tints: {'Walls': [0.98, 0.96, 0.9], 'Turret': [0.98, 0.96, 0.9]}
- `town_mill`: rooms: ['taproom 19.6 x 23.2 (bar, tap wall, tanks, tables)']; tints: {'Walls': [0.78, 0.68, 0.64], 'Reveals': [0.78, 0.68, 0.64], 'Arches': [0.7, 0.6, 0.56], 'Pilasters': [0.74, 0.64, 0.6], 'Cornice': [0.74, 0.64, 0.6], 'Tower': [0.74, 0.64, 0.6], 'TaproomWalls': [0.78, 0.68, 0.64]}
- `town_mill_stack`: top_m: 34.0; tints: {'Base': [0.72, 0.6, 0.55], 'Shaft': [0.66, 0.54, 0.5], 'Crown': [0.62, 0.5, 0.46], 'Bands': [0.62, 0.5, 0.46]}
- `town_motel_office`: rooms: ['lobby 7.6 x 8.6 (counter, key board, brochures)']
- `town_motel_wing`: units: 6; rooms: ['unit 3: 4.1 x 7.4 (bed, nightstand, TV)']
- `town_pickup`: tints: {'Body': [0.5, 0.06, 0.05]}
- `town_pickup_grey`: tints: {'Body': [0.33, 0.34, 0.35]}
- `town_pickup_white`: tints: {'Body': [0.9, 0.9, 0.88]}
- `town_plaza`: crt_wall_spot: [26.45, 7.45, 0.0]; units: ['vacant', 'laundry', 'pharmacy', 'video']; rooms: ['video store 15.8 x 9.2 (racks, counter, posters)', 'back room 15.8 x 3.9 (CRT wall spot)']
- `town_school`: tints: {'Walls': [0.86, 0.76, 0.7], 'Reveals': [0.86, 0.76, 0.7], 'Pavilion': [0.8, 0.7, 0.64]}
- `town_sheriff`: rooms: ['lobby + front office 12.4 x 6.5 (counter, window desk with phone, gun cabinet)', 'corridor', 'two holding cells 3.1 x 4.9 (barred fronts, bunks)']; tints: {'Walls': [0.9, 0.84, 0.8]}
- `town_shop_a`: party_walls: flush at x = +-4.0; tints: {'Walls': [1.0, 1.0, 1.0], 'Cornice': [1.0, 1.0, 1.0]}
- `town_shop_b`: party_walls: flush at x = +-4.0; tints: {'Walls': [0.86, 0.78, 0.72], 'Cornice': [0.86, 0.78, 0.72]}
- `town_shop_c`: party_walls: flush at x = +-4.0; tints: {'Walls': [1.0, 0.86, 0.84], 'Cornice': [1.0, 0.86, 0.84]}
- `town_shop_d`: party_walls: flush at x = +-4.0; tints: {'Walls': [0.72, 0.66, 0.64]}
- `town_shop_realty`: party_walls: flush at x = +-8.0; tints: {'Walls': [0.92, 0.9, 0.86], 'Cornice': [0.92, 0.9, 0.86]}
- `town_shop_wide`: party_walls: flush at x = +-8.0; tints: {'Walls': [1.0, 1.0, 1.0], 'Cornice': [1.0, 1.0, 1.0]}
- `town_suv`: tints: {'Body': [0.92, 0.92, 0.9]}
- `town_suv_black`: tints: {'Body': [0.03, 0.03, 0.035]}
- `town_suv_green`: tints: {'Body': [0.12, 0.2, 0.14]}
- `town_truss_span`: deck_top_z: 0.0; sidewalk: x 4.3..5.9 at z 0.12
- `town_van`: tints: {'Body': [0.035, 0.037, 0.04]}
- `town_water_tower`: top_m: 24.0; tank: [9.0, 8.4]

## Changed from kit_request.md v2 (and why)
- `town_bar` 30.9 x 21.1 (incl. the chimney, the porch, the deck and its steps down 1.8 m to the water): the brief's 30 x 18
  plus the steps. LOD0 25.0k (the budget's 25k).
- `town_church` 12.9 x 29.2 x 21.9: the 26 m nave + tower depth plus the five steps in front (below_m 0.9).
- `town_gas_station` 27.6 x 30.1: canopy 27 m wide (3 islands), store 18 x 12 behind it, the pylon at the canopy's front corner.
- `town_fastfood` 20.8 x 16.6 incl. the tilted band (0.55 m out all round) and the drive-through canopy on +X; the menu
  board, speaker and clearance bar are separate props (`town_menu_board`, `town_clearance_bar`).
- `town_depot` 33.8 x 15.6: the 32 x 10 depot plus its eaves and the 4 m platforms on +Y. The freight platform is 1.25 m
  high (not 1.1) so the crawl space under it is 1.15 m clear.
- Downtown shops are 8.1 x 19.6 (incl. the awning and back cornice): party walls flush at +-4.
- `town_mill` LOD0 21.5k (over the 12k hero line): 64 m of three-storey bays (~100 arched windows) plus the taproom; its
  LOD1 is 230. Tell me if it must drop further (fewer bays on the far side, or the lofts' windows as painted cells).
- Over the request's lines, modestly: `town_house_a` 3.7k and `town_house_b` 3.2k (houses <= 3k: the Victorian's wraparound
  porch and two storeys of windows; the foursquare's dormer and porch), `town_shop_realty` 5.4k and `town_plaza` 5.6k
  (shops <= 5k: their walk-in rooms' finer faces for the baked light). Say if any must come down.
- `town_motel` is two assets: `town_motel_office` and `town_motel_wing` (place the wing twice for the L).
- Colours of the cars, cottages and brick tones come from COLOR_0 tints (one atlas region, several looks).
- Walk-in floors are at z = 0 exactly: **sink the terrain 0.05-0.1 m under every footprint** (or cut it), or the floors
  z-fight with the pad (the asset viewer's ground shows it).
- Not built: `town_flower_basket` on lamp arms is separate (also `town_streetlight_basket`); nothing else from v2 is missing.

