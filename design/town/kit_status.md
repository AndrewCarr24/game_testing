# Town buildings kit: status (kit agent -> layout agent)

Source of truth for names, sizes, footprints, entrances and triangle counts of `blender/assets/town_*.py`.
Updated as each asset is built. Exports: `assets/models/town_<name>.gltf` (+ `.bin`, Draco) and a sidecar
`assets/models/town_<name>.json` (size, bounds, `below_m`, colliders, entrances, tris).

## Direction (user, relayed 2026-10-22): a modern, quaint mountain town
Not the 1900-1960 mill town of `kit_request.md` v1: "no billionaire would live down the street from an old
Appalachian mill town". A present-day, polished Blue Ridge resort town in the manner of **Highlands NC,
Blowing Rock and Cashiers** (Main Street Highlands: stone bases, board-and-batten and cedar, black standing-seam
roofs, gable fronts with exposed timber trusses, black-framed storefronts, gooseneck lamps, blade signs, planters),
with a few older brick fronts kept (Marshall NC Main Street, `Main_Street,_Marshall,_NC_(39724136513).jpg`;
Saluda's `Saluda_Historic_District.jpg`). Wanted by the user: a fast-food drive-through (generic, no brand),
a modern gas station with a canopy and a convenience store, a small local-history museum, a video store that
survived, a bar (**the hero: cinematic, full interior**), coffee / boutique / outfitter fronts, a church, a
sheriff's office, homes, street furniture, cars. Mill houses, the mill and the old depot are deprioritised unless
you still ask for them (tell me in `kit_request.md`).

## Contract (as kit_request.md v1 asked)
- Frame: metres, origin = floor centre at the front door's sill height, front (street side, main door) -Y; yaw-only
  placement. Anything below z = 0 is `below_m` in the sidecar.
- **Materials: 2 for the whole kit.** `M_Town_Atlas` (opaque, base colour = `T_Town_Atlas`, 2048, WebP in the
  export) and `M_Town_Glow` (the same atlas as emission: neon tubes, lamps, lit signs; draw it unlit/additive or as
  emissive). No transparency anywhere: glass is painted into the atlas (window cells show curtains, blinds,
  lit shops, a cafe's pendants, shelves of tapes...), sash frames painted in. Colours are baked into the atlas
  (no tint factors); the atlas layout is `assets/textures/town_polyhaven.json` ("regions").
- How one atlas repeats: faces are split at every tile boundary of their world-scale UVs (u along a wall, v =
  height), so each piece maps inside its 512 or 256 px region (8 px wrapped gutters). The atlas is 64 % 512-px
  surfaces (board-and-batten white/charcoal, lap siding, ledgestone, fieldstone, brick, black standing seam,
  architectural shingle, cedar, wood floor, windows, signs) and 256-px ones (concrete, asphalt, deck, plaster,
  checker, dark wood, varnished wood, polished concrete, white brick, sage board-and-batten, green seam,
  corrugated, block, tile, white lap, the flat palette).
- `<Asset>_LOD1`: a child mesh in the same glTF, palette swatches only (no tiling), for > 120 m. Its triangles are
  in the table (usually far under 1/4). It is `hide_render` in Blender (the previews show LOD0).
- Colliders: AABBs `[x0, y0, z0, x1, y1, z1]` in the asset frame, in the sidecar and in the root node's extras
  (`town`, a JSON string). Walk-in buildings get walls split at their doors.
- Doors of walk-ins: `<Asset>_Door[_n]` empty at the hinge with `interact` (`rotate`) extras, leaf meshes under it.
- Signs: pictograms only (cup, burger, mountains, cassette, star, cocktail glass, pediment, pump), no lettering.
- Triangle budgets: houses <= 3k, commercial <= 5k, hero / walk-in <= 12k (the bar may take more: see its row).

## Built

| name | what | w x d x h (m) | footprint incl. canopy/steps (x0, y0, x1, y1) | entrances | walk-in | LOD0 / LOD1 tris | status |
|---|---|---|---|---|---|---|---|
| `town_shop` | main-street storefront, modern mountain: charcoal board-and-batten, ledgestone base, cedar king-post truss in the gable front, black canopy, cafe pictogram, blade sign | 8.9 x 16.8 x 7.2 | -4, -8.5, 4.45, 8.3 | front glass door (0, -7), back door (-2.3, 7) | no | 1.85k / 38 | v1 |

## Planned (in this order)
`town_bar` (hero, walk-in), `town_gas_station` (canopy + c-store, walk-in store), `town_fastfood` (drive-through,
walk-in), `town_shop_*` variants (cafe, outfitter, boutique), `town_video_store`, `town_museum`, `town_sheriff`
(walk-in), `town_church` (white frame, steeple ~21 m: the cove's backdrop shows it), `town_brick_front` (older
2-storey brick), homes (`town_house_farmhouse`, `town_house_cabin`, `town_house_bungalow`), street furniture
(`town_lamp_post`, `town_bench`, `town_planter`, `town_streetlight`, `town_pole`), vehicles (`town_car`, `town_pickup`,
`town_suv`, `town_van`, `town_cruiser`), `town_water_tower`, `town_truss_span`.
