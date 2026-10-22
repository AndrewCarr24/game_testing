# Blue Ridge plant kit (Laurel Fork Cove, mid-June)

Status: built 2026-10-21, not placed in a level, not committed. It is the plant kit for `brief.md`,
grown by the scripted generator from the vegetation spike (`_tech/vegetation.md`) and exported in the
spike's file format, so the runtime (`_tech/runtime.md`, `viewer/wild/main.js ?veg=1`) can load any of
these ids the way it loads `fir` and `ash`.

```
python3 blender/wilderness/veg_sources.py                    # once: Poly Haven scans (CC0)
Blender -b --factory-startup --python blender/wilderness/trees.py -- --kit blue_ridge
        [--species tulip_poplar,creek_boulder] [--no-variants] [--no-impostor] [--no-preview]
python3 -m http.server 8765  ->  http://localhost:8765/viewer/wild_veg.html?mode=kit&group=canopy
node blender/wilderness/veg_shots.mjs 'name=mode=cove&wind=0&hud=0'      # screenshots (browser slot)
python3 blender/wilderness/plants_doc.py                       # the tables below, from veg.json
```

The whole kit (46 entries: 25 species ids plus their variants) builds in about 60 s without impostors and
in about 6 min with them, in one headless Blender (one `asset` run slot).

## Budgets (measured from veg.json; ranges are over the variants)

| id (+ variants) | kind | height | LOD0 / LOD1 / LOD2 tris | far | draws / LOD | LOD switch (m) | geometry KB |
|---|---|---|---|---|---|---|---|
| `tulip_poplar` (+2) | broadleaf | 46.4 m | 8439-8735 / 2246-2304 / 682-726 | impostor 1024/512 | 2/2/2 | 25 / 60 / 120 | 597 |
| `northern_red_oak` (+1) | broadleaf | 28.0 m | 6263-6452 / 1502-1530 / 475-487 | impostor 1024/512 | 2/2/2 | 25 / 60 / 120 | 271 |
| `white_oak` (+1) | broadleaf | 22.8 m | 5474-6075 / 1318-1426 / 432-467 | impostor 1024/512 | 2/2/2 | 25 / 60 / 120 | 254 |
| `chestnut_oak` (+1) | broadleaf | 20.8 m | 3294-3367 / 833-958 / 239-323 | impostor 1024/512 | 2/2/2 | 25 / 60 / 120 | 163 |
| `shagbark_hickory` (+1) | broadleaf | 30.1 m | 5286-5550 / 1420-1474 / 420-436 | impostor 1024/512 | 2/2/2 | 25 / 60 / 120 | 272 |
| `sugar_maple` (+1) | broadleaf | 27.9 m | 8268-8523 / 2128-2154 / 656-675 | impostor 1024/512 | 2/2/2 | 25 / 60 / 120 | 397 |
| `yellow_buckeye` (+1) | broadleaf | 30.9 m | 5646-6200 / 1452-1606 / 464-517 | impostor 1024/512 | 2/2/2 | 25 / 60 / 120 | 263 |
| `eastern_hemlock` (+2) | conifer | 32.4 m | 7923-8637 / 2852-3042 / 606-642 | impostor 1024/512 | 2/2/2 | 22 / 50 / 110 | 664 |
| `white_pine` (+1) | conifer | 41.0 m | 8244-8519 / 2812-2824 / 382 | impostor 1024/512 | 2/2/2 | 24 / 55 / 120 | 436 |
| `rosebay_rhododendron` (+1) | shrub | 5.4 m | 3616-3779 / 1014-1022 / 330-344 | impostor 512/256 | 3/3/3 | 12 / 30 / 70 | 180 |
| `mountain_laurel` (+1) | shrub | 3.7 m | 5204-5614 / 1278-1370 / 428-480 | impostor 512/256 | 3/3/3 | 12 / 30 / 60 | 239 |
| `catawba_rhododendron` (+1) | shrub | 2.9 m | 5440-5445 / 1310-1436 / 452-478 | impostor 512/256 | 3/3/3 | 12 / 30 / 70 | 237 |
| `rhodo_thicket` | thicket | 4.7 m | 10212 / 1678 / 190 | LOD2 | 3/3/2 | 12 / 35 / 160 | 154 |
| `rhodo_tunnel` | thicket | 5.1 m | 7373 / 1342 / 176 | LOD2 | 3/3/2 | 12 / 35 / 160 | 120 |
| `doghobble` (+1) | clump | 0.6 m | 144 / 32 / 8 | culled | 1/1/1 | 10 / 25 / 50 | 16 |
| `christmas_fern` (+1) | clump | 0.4 m | 132 / 40 / 10 | culled | 1/1/1 | 8 / 18 / 30 | 16 |
| `cinnamon_fern` (+1) | clump | 0.7 m | 108 / 44 / 8 | culled | 1/1/1 | 10 / 22 / 36 | 15 |
| `moss_cushion` (+1) | mat | 0.1 m | 126 / 36 / 6 | culled | 2/2/1 | 8 / 20 / 40 | 18 |
| `hemlock_snag` | conifer | 24.0 m | 962 / 380 / 50 | impostor 512/256 | 1/1/1 | 25 / 60 / 140 | 16 |
| `chestnut_log` (+1) | log | 3.9 m | 1558-2651 / 440-987 / 105-469 | LOD2 | 3/3/3 | 25 / 60 / 150 | 63 |
| `chestnut_log_propped` | log | 2.2 m | 2836 / 761 / 195 | LOD2 | 3/3/3 | 25 / 60 / 150 | 40 |
| `blowdown_log` | log | 4.9 m | 3209 / 1205 / 589 | LOD2 | 3/3/3 | 25 / 60 / 150 | 46 |
| `chestnut_stump` | stump | 1.6 m | 270 / 70 / 30 | LOD2 | 1/1/1 | 20 / 50 / 120 | 7 |
| `cut_stump` | stump | 0.8 m | 198 / 70 / 30 | LOD2 | 2/2/2 | 20 / 50 / 100 | 11 |
| `creek_boulder` (+2) | rock | 1.1 m | 1280 / 320 / 80 | LOD2 | 2/2/2 | 25 / 60 / 200 | 59 |

- **Canopy LOD0 is 3.3-8.7k triangles.** The brief asked for 5-6k; the runtime spike says 8-12k is fine with LOD0 ≤ 20-25 m. The big four (poplar, maple, hemlock, pine) are 8-8.7k. LOD1 is 0.8-3k and LOD2 0.24-0.73k; then an 8 x 8 hemi-octahedral impostor (1024 albedo, 512 normal; shrubs 512/256). Dead wood and rock end on their LOD2.
- **Thicket tiles are the most expensive unit** (10.2k at LOD0, with a 12 m LOD0 range per runtime.md). At a 6.5 m tile grid, about 10 tiles are at LOD0 around a player inside a laurel hell.
- Ground clumps are 108-144 / 32-44 / 6-10 and are culled at 30-50 m (no impostor).
- **`lod_dist[3]` is the cull distance for every entry without an impostor**: thicket tiles 160 m, logs 150, stumps 100-120, boulders 200, clumps 30-50. Thickets get no impostor on purpose: they are tiles under the canopy, the 176-190-triangle hull is their far LOD, and the canopy shell takes over beyond.
- **Download: 11.1 MB for the whole kit, every variant** (geometry 4.4 MB). runtime.md's budget is ≤ 15 MB for world data *plus* vegetation (about 6.8 MB of world data today), so the full kit is over. A level ships only the communities and variants it places. The `*_impostor_*_2k.png` files in `build/wilderness/veg/` are bake artefacts, not shipped.
- Unique textures: 43 maps, 102 MB GPU (RGBA8 + mips); impostors: 26 maps, 67 MB GPU; download for the whole kit (gltf + bin + WebP, every variant): 11.1 MB (geometry 4.4 MB).
- The two 2048 leaf atlases cost 43 MB of that. Levers: KTX2 (about 4x), or 512 leaf normals (-8 MB). The kit as a whole (169 MB GPU) is over the runtime's ≤ 150 MB texture budget before terrain. Level by level, you'd load only the communities you place.

### Textures

| texture | px | GPU MB |
|---|---|---|
| T_Veg_BrBroadleaf_Leaf.png | 2048 | 21.3 |
| T_Veg_BrEvergreen_Leaf.png | 2048 | 21.3 |
| T_Veg_BrBroadleaf_Leaf_N.png | 1024 | 5.3 |
| T_Veg_BrEvergreen_Leaf_N.png | 1024 | 5.3 |
| T_Veg_BrGround_Leaf.png | 1024 | 5.3 |
| T_Veg_TreeBark03_poplar_5d8d_Bark.png | 512 | 1.3 |
| T_Veg_TreeBark03_Bark_N.png | 512 | 1.3 |
| T_Veg_JolchamOakBark01_redoak_392f_Bark.png | 512 | 1.3 |
| T_Veg_JolchamOakBark01_Bark_N.png | 512 | 1.3 |
| T_Veg_BarkWillow02_whiteoak_e9ea_Bark.png | 512 | 1.3 |
| T_Veg_BarkWillow02_Bark_N.png | 512 | 1.3 |
| T_Veg_BarkWillow_chestnutoak_5a05_Bark.png | 512 | 1.3 |
| T_Veg_BarkWillow_Bark_N.png | 512 | 1.3 |
| T_Veg_MetasequoiaBark_shagbark_f244_Bark.png | 512 | 1.3 |
| T_Veg_MetasequoiaBark_Bark_N.png | 512 | 1.3 |
| T_Veg_BarkWillow02_maple_8aab_Bark.png | 512 | 1.3 |
| T_Veg_BarkPlatanus_buckeye_93ef_Bark.png | 512 | 1.3 |
| T_Veg_BarkPlatanus_Bark_N.png | 512 | 1.3 |
| T_Veg_PineBark_hemlock_59a3_Bark.png | 512 | 1.3 |
| T_Veg_PineBark_Bark_N.png | 512 | 1.3 |
| T_Veg_BarkBrown02_wpine_6835_Bark.png | 512 | 1.3 |
| T_Veg_BarkBrown02_Bark_N.png | 512 | 1.3 |
| T_Veg_SakuraBark_rhodo_a070_Bark.png | 512 | 1.3 |
| T_Veg_SakuraBark_Bark_N.png | 512 | 1.3 |
| T_Veg_MetasequoiaBark_laurel_1263_Bark.png | 512 | 1.3 |
| T_Veg_SakuraBark_catawba_8a97_Bark.png | 512 | 1.3 |
| T_Veg_BrGround_Leaf_N.png | 512 | 1.3 |
| T_Veg_RoughWood_snag_82b7_Bark.png | 512 | 1.3 |
| T_Veg_RoughWood_Bark_N.png | 512 | 1.3 |
| T_Veg_RoughWood_ghost_8392_Bark.png | 512 | 1.3 |
| T_Veg_ForestLeaves02_soil_397f_Bark.png | 512 | 1.3 |
| T_Veg_ForestLeaves02_Bark_N.png | 512 | 1.3 |
| T_Veg_MossyRock_gneiss_7764_Bark.png | 512 | 1.3 |
| T_Veg_MossyRock_Bark_N.png | 512 | 1.3 |
| T_Veg_RoughWood_oldstump_46c5_Bark.png | 512 | 1.3 |
| T_Veg_RosebayTile_Tile.png | 320 | 0.5 |
| T_Veg_RosebayTile_Tile_N.png | 320 | 0.5 |
| T_Veg_LaurelTile_Tile.png | 320 | 0.5 |
| T_Veg_LaurelTile_Tile_N.png | 320 | 0.5 |
| T_Veg_CatawbaTile_Tile.png | 320 | 0.5 |
| T_Veg_CatawbaTile_Tile_N.png | 320 | 0.5 |
| T_Veg_MossTile_Tile.png | 256 | 0.3 |
| T_Veg_MossTile_Tile_N.png | 256 | 0.3 |

### Palette (brief vs measured)

| species | brief (Appendix B) | measured card means |
|---|---|---|
| Tulip poplar | #8DB04A | poplar_a: #8EB14B, poplar_b: #8BAC48 |
| Northern red oak | #3F5E2A | red_oak_a: #425F2B, red_oak_b: #425E2C |
| White oak | #4A6A36 | white_oak_a: #4C6A37, white_oak_b: #4D6B38 |
| Chestnut oak | #6B8A36 | chestnut_oak_a: #6B8937, chestnut_oak_b: #6A8836 |
| Shagbark hickory | #4F7230 | hickory_a: #537532, hickory_b: #517331, hickory_strips: #817B6E |
| Sugar maple | #4E7A2C | maple_a: #527A2D, maple_b: #4F772C |
| Yellow buckeye | #6E9438 | buckeye_a: #6E9039, buckeye_b: #71963B |
| Eastern hemlock | #2F4A3A | hemlock_a: #3C4A31, hemlock_b: #3C4B31 |
| Eastern white pine | #4D6E4A | pine_a: #547154, pine_b: #537053 |
| Rosebay rhododendron | #2E4A2C | rosebay_a: #3C5030, rosebay_b: #3C5032, rosebay_c: #83887C |
| Mountain laurel | #3F5A2E | laurel_a: #4E5C31, laurel_b: #CCA9AF |
| Catawba rhododendron | #33502F | catawba_a: #976081, catawba_b: #405635 |
| Laurel hell tile (rosebay thicket) | #2E4A2C | rosebay_a: #3C5030, rosebay_b: #3C5032, rosebay_c: #83887C |
| Laurel hell tile with a crawl tunnel | #2E4A2C | rosebay_a: #3C5030, rosebay_b: #3C5032, rosebay_c: #83887C |
| Doghobble | #355A2B | doghobble_a: #505E31, doghobble_b: #505E31 |
| Christmas fern | #2F5027 | xmas_fern_a: #365128, xmas_fern_b: #375329 |
| Cinnamon fern | #5E8838 | cinn_fern_a: #628A39, cinn_fertile: #875A2F |
| Moss cushion | #4F7A2A | moss_fringe: #588329 |


Hemlock measures warmer than its blue-black target, because its twig stems are brown. The flowering cards (`rosebay_c`, `laurel_b`, `catawba_a`) carry the blooms' colour on purpose.

## Weak-hardware numbers (viewer, shadows off; `node blender/wilderness/veg_perf.mjs '<query>'`)

| view | draw calls | triangles | M4 Pro Metal p50 / p95 | SwiftShader 1280x720 p50 / p95 |
|---|---|---|---|---|
| `mode=cove` (about 1,100 trees over 320 x 320 m, a 4,200-clump fern ring, logs, boulders, every variant instanced) | 171 | 677k | 1.2 / 3.3 ms | 444 / 472 ms |
| `mode=hell` (laurel-hell tiles on a 6.5 m grid, tunnel chain; shells on) | 51 | 443k | 2.0 / 2.7 ms | 282 / 560 ms |
| `mode=hell&shell=0` (same, shells hidden: the roof is open) | 45 | 391k | 2.0 / 2.6 ms | 206 / 407 ms |
| `mode=hell`, first shell budget (1.5k / 0.5k / 0.2k shell tris) | 51 | 554k | 1.8 / 2.7 ms | 326 / 481 ms |

- The viewer runs MSAA and instances every variant and the whole 320 m square with no culling. The runtime's q0 (no MSAA, LOD0 ≤ 8-12 m, fewer variants) is the comparison for its ≤ 200 ms SwiftShader budget, not these numbers.
- **The honest result on shells:** in the hell view the opaque shells cost more on SwiftShader than the early-z they save. Hiding them is 27% faster, but then the thicket has no roof and you see sky through it. Cutting the shell budget (1.5k → 0.8k at LOD0) took 44 ms off.
- What the shell buys is the look of solid volume with 2-3% of the cards at LOD2 (176-190 triangles per 8 m tile). If weak hardware needs more, the next levers are a shorter thicket LOD0 range and dropping LOD1's stems.


## Ids

Every id is a key of `build/wilderness/veg/veg.json` `species` (the same entry format as the spike:
`gltf`, `lods[{name, tris, ...}]`, `lod_dist`, `textures`, `impostor`, `height_m`, `preview`). Variants are
separate ids, `<id>_2` and `<id>_3`. `kits.blue_ridge.species` maps each species to its variant ids, and
`kits.blue_ridge.groups` maps canopy / understory / ground / deadwood / rock to species.

| group | ids | where (brief, Appendix C) |
|---|---|---|
| canopy | `tulip_poplar` (3 variants), `northern_red_oak` (2), `white_oak` (2), `chestnut_oak` (2), `shagbark_hickory` (2), `sugar_maple` (2), `yellow_buckeye` (2), `eastern_hemlock` (3), `white_pine` (2) | cove: poplar, buckeye, maple, hemlock. Oak-hickory: red/white oak, hickory, white pine emergents. Dry crest: chestnut oak |
| deadwood | `hemlock_snag`, `chestnut_log` (2: 1.2 m with root plate, 0.8 m jumpable), `chestnut_log_propped`, `blowdown_log`, `chestnut_stump`, `cut_stump` | logs where chestnut stood (upper slopes, c > 0.5), blowdowns in coves, 3-6 logs/ha |
| understory | `rosebay_rhododendron` (2), `mountain_laurel` (2), `catawba_rhododendron` (2), `rhodo_thicket`, `rhodo_tunnel` | laurel hell / creekside, dry crests and slicks, the Knob's bald; thicket tiles on a ~6.5 m grid |
| ground | `christmas_fern` (2), `cinnamon_fern` (2), `doghobble` (2), `moss_cushion` (2) | the fern ring (25 m), seeps, creek banks, rocks/logs/roots |
| rock | `creek_boulder` (3: 2.3 m, 1.1 m, 4.2 m) | the creek, the Narrows, cove boulder fields |

**Node names: read them from `lods[i].name`, don't derive them.** They follow `Veg_` plus the id with
its first letter upper-cased (`Veg_Tulip_poplar_LOD0`). That is the rule `viewer/wild/main.js` uses
(`name[0].toUpperCase() + name.slice(1)`). The spike's `.title()` naming would have given
`Veg_Tulip_Poplar`; trees.py now uses the runtime's rule (`node_name`), which is identical for the spike's ids.

## What each entry adds (additive fields; the spike's are unchanged)

- `kind`: `broadleaf`, `conifer`, `shrub`, `thicket`, `clump`, `mat`, `log`, `stump` or `rock`. `group`, `title`, `latin`, `community`.
- `reference`: the real-world look the species is art-directed against.
- `palette`: the brief's Appendix B leaf colour (sRGB). `leaf_mean_srgb`: the measured alpha-weighted mean of each twig card the species uses.
- `species`, `variant`, `variants`: the base id, this entry's variant number and the variant count.
- `collider` (three.js frame, y up, metres):
  - trees: `capsule {radius at 1.3 m, height, dbh_m}`;
  - shrubs and thickets: `box {min, max, soft: true}`. The tunnel tile adds `tunnel {axis: x, width 1.3, height 1.25, bend, length}`;
  - logs: `capsules [{a, b, r}]` plus `root_wad` box;
  - stumps: `cylinder`;
  - boulders: `ellipsoid`.
- `climb` (logs, stumps, rocks):
  - `top_height`;
  - `jump_over`: three.js x ranges along the log where the top is ≤ 0.95 m (the existing ~1 m jump); `jump_onto` for stumps and rocks;
  - `crawl_under {x0, x1, clearance}`;
  - `ramps`: polylines in the `level.ramps` format.

  For example: the 1.2 m chestnut ghost has a 1.6 m crawl-under for its first 1.5 m beside the root plate and a jumpable tip at x 13.5-18. `chestnut_log_2` is jumpable along its whole length. The propped log is a ramp to its high end, with a 1.25 m crawl-under at x 9-15.
- `lods[i].shell_tris`, `lods[i].draw_calls` (counted from what the LOD really has), `impostor.normal_px`, `impostor.shared_from` (variants reuse the base's atlas), `sources` (Poly Haven credits).

## Materials and the runtime contract

- `*_Leaf` (MASK 0.5, double-sided, no back-face normal flip), as in the spike. The flowers, fern fronds, moss sprigs and shagbark strips are cards in the same material.
- `*_Shell` (**new, opaque**): the leaf mass inside the rhododendrons, laurel and Catawba, the thicket's roof, and the moss mats.
  - It's a smoothed metaball hull of the foliage clumps, decimated per LOD, textured with a repeating tile of the same leaves (`T_Veg_*_Tile`).
  - **Draw it before the cards (renderOrder -1).** three sorts opaque draws by material id, which would put it after the leaves, and then early-z saves nothing. `wild_veg.html` does this; `?shell=0` hides shells for A/B.
  **The shell is a third primitive under the LOD node.** `viewer/wild/main.js`'s `?veg=1` loader pushes every mesh under `Veg_*_LOD<i>` as a part and would give it the tree material. Route `*_Shell` to an opaque material drawn first.
- Bark / wood / rock / soil / moss are opaque PBR materials with world-scale UVs.
- `COLOR_0` = AO everywhere: crown voxel AO for plants (now with the shell as a dense occluder), BVH ray AO for logs, stumps and rocks. `_WIND` is present on every mesh (zeros on dead wood and rock, so one shader handles everything).
- **Textures are shared by file**: one leaf atlas per family, shared barks (the blowdown uses the poplar's bark file). The glTFs reference the same `textures/*.webp`, but GLTFLoader makes a new texture per file. **De-duplicate by image URI at load** (the house does this with `shareMaterial`), or the GPU memory below multiplies. `wild_veg.html` `shareTextures()` is a working reference (it handles `EXT_texture_webp`).
- Draw calls: each LOD is 1-3 primitives (`draw_calls`). **Variants multiply draw calls**: 3 poplar variants are 3 instanced draws per tier. The kit has 46 ids, so instancing all of them would be about 46 x 3 tiers x 2 ≈ 280 calls against the runtime's ≤ 40. Choose per quality level: one variant per species at q0/q1, and per-instance scale/rotation/tint as the free variation. The cove view in the viewer instances everything and reads about 300 calls with shadows; that is a viewer, not a budget.

## How it's made (and why it looks like this forest)

- **Twig cards are baked, not borrowed** (vegetation.md gap #3, `blender/wilderness/leafcards.py`).
  - Each species' leaf is a parametric outline: the tulip's four lobes and notched tip, red oak's bristle-tipped lobes, white oak's rounded fingers, chestnut oak's wavy teeth, maple's five palmate lobes, the hickory's and buckeye's leaflets, the rhododendron's long elliptic leaf, laurel, Catawba, doghobble, and the fern pinnae (with the Christmas fern's "stocking" ear).
  - Veins are procedural. The fine grain is the high-pass of a Poly Haven leaf scan.
  - The leaves sit on procedural twigs in the real arrangement: poplar alternate on long petioles, oaks clustered at the tips, maple and buckeye opposite, hickory compound, heaths in terminal whorls with trusses. Hemlock has flat two-ranked lacy sprays with lime June tips. White pine has five-needle plumes.
  - The twigs are rendered flat with Eevee emission passes (albedo, tangent normal), auto-cropped, colour-dilated and shelf-packed into three shared atlases. Each card is cached by its definition hash, so editing one card re-renders only that card (~2-6 s per atlas).
  - Card rects use the spike's `(x0, y0, x1, y1, side, base)` 1/8-grid format. Real sizes are in metres.
- **Skeletons** (`trees.py`, parameters in `blender/wilderness/species/blue_ridge.py`):
  - The spike's recursive and whorled growth, plus explicit trunk radii (DBH from the brief) with root flare, bole stubs, and per-variant jitter of the crown envelope.
  - Hemlock: irregular whorls and a nodding leader. White pine: tiered whorls with skips, a flat-topped profile, secondary limbs and upturned plumes.
  - Shrubs grow from many leaning, sinuous stems. Thickets are 3 x 3 shrubs grown into one 8 m tile, with the tunnel cut through the wood.
  - Cards roll ±50-65° about their twig, so crowns don't go edge-on from the side.
- **Dead wood and rock** (`blender/wilderness/deadwood.py`):
  - Lumpy, checked log tubes with splintered tips, broken limb stubs and root plates. The blowdown lifts into its plate, giving a 0.9-1.2 m crawl-under.
  - The propped log rests on a built-in boulder.
  - Stumps have buttress lobes, with a jagged (chestnut) or sawn and mossy top.
  - Boulders are noise-displaced, joint-plane-faceted icospheres.
  - Moss is a material on the sky-facing faces (n.z plus noise), using the moss tile.
- **Palette** (mid-June, deliberately not uniform; the means are measured from the baked cards):
  - poplar yellow-green #8DB04A;
  - buckeye and chestnut oak lighter yellow-greens;
  - maple and hickory mid-greens;
  - red oak the darkest broadleaf (#3F5E2A, glossier, roughness 0.5);
  - white oak blue-green;
  - hemlock blue-black with lime tips;
  - white pine soft blue-green;
  - rhododendron and laurel dark and glossy (roughness 0.42-0.46), laurel's white-pink cups, Catawba's magenta trusses, rosebay's first white trusses.

## Weak hardware: thickets as volume, not layers of cards

The runtime spike found that SwiftShader pays per alpha-tested pixel. So the heaths and the laurel hell are built as an opaque shell plus fewer, bigger cards:

| asset | LOD0 | of which shell | cards | idea |
|---|---|---|---|---|
| `rhodo_thicket` (8 x 8 x 4.4 m) | 10.2k | ~1.5k tris (one continuous roof) | rosettes on the outside only | from outside a solid wall; from inside twisted stems under an opaque roof; LOD2 is the hull plus 3% of the cards |
| `rosebay_rhododendron`, `mountain_laurel`, `catawba_rhododendron` | 3.3-5.6k | 0.6-0.7k | 1-2 cards per twig | the shell fills the inside so the far side's cards are depth-rejected |

Measured A/B (`?shell=0` hides the shells): see "Weak-hardware numbers" above.

## Images

All under `build/wilderness/veg/previews/`:
- `blue_ridge_contact.png`: the contact sheet. Each species with its three.js render, its Blender LOD sheet, the reference text, budgets and palette.
- `viewer_<id>.png`: per-species heroes in three.js (golden hour, LOD0, sun shadows).
- `<id>.png`: the Blender LOD0 / LOD1 / LOD2 / close-up sheet, one per id and variant.
- Scenes at eye height in the viewer:
  - `viewer_br_cove.png`: Poplar Cove, looking up the grey columns;
  - `viewer_br_creek.png`: hemlock, rosebay, doghobble and boulders on the bank;
  - `viewer_br_ridge.png`: chestnut oak over laurel in bloom;
  - `viewer_br_bald.png`: the Catawba bald in bloom;
  - `viewer_br_hell.png`: in the rhododendron tunnel.
- Line-ups: `viewer_br_kit_canopy.png`, `viewer_br_kit_understory.png`, `viewer_br_kit_deadwood.png`.
- LOD chains: `viewer_br_row_poplar.png`, `viewer_br_row_hemlock.png`. Variants: `viewer_br_variants_poplar.png`.

## Per-species references

The `reference` text of each entry, side by side with the renders, is on the contact sheet
(`build/wilderness/veg/previews/blue_ridge_contact.png`, or live: `viewer/wild_veg.html?mode=sheet`). The
references are field-guide descriptions: USFS *Silvics of North America*, Sargent's *Manual of the Trees*,
NPS Great Smoky Mountains, and the brief's own places (Joyce Kilmer, Albright Grove, Roan and Craggy
Gardens for the June heath).

## Credits (Poly Haven, CC0)

| scan | used for |
|---|---|
| `tree_bark_03` | tulip poplar bark (pale, interlaced), the blowdown |
| `jolcham_oak_bark_01` | northern red oak |
| `bark_willow` | chestnut oak (deep blocky ridges) |
| `bark_willow_02` | white oak (pale, scaly) and sugar maple (greyer grade) |
| `metasequoia_bark` | shagbark hickory (grey grade, plus strip cards), mountain laurel stems (red-brown) |
| `bark_platanus` | yellow buckeye (sycamore-like plates) |
| `pine_bark` | eastern hemlock (cinnamon-grey grade) |
| `bark_brown_02` | eastern white pine |
| `sakura_bark` | rosebay and Catawba rhododendron stems |
| `rough_wood` | chestnut ghosts, snag, stumps (silver, checked) |
| `mossy_rock` | creek boulders (gneiss with lichen) |
| `forest_leaves_02` | root-wad soil |
| `island_tree_02` (leaf atlas) | fine grain inside every generated leaf |
| `moss_01` (sprite atlas) | moss fringe cards, moss tile (mats, moss caps) |

Downloaded by `blender/wilderness/veg_sources.py` into `build/wilderness/veg/src/`. Every entry's
`sources` field lists the scans it uses.

## Known gaps

- The shells are still a little lumpy at LOD2 (110-200 tris). They read as a dark mass at 30-70 m, but up close a gap in the cards shows a smooth hull.
- No dithered LOD cross-fade in the viewer (the runtime has one). Variants share the base's impostor, so a variant can pop slightly at the impostor switch.
- Card-level wind only (no per-leaf flutter on the shells). The Grimble's "wake of shaking treetops" is a uniform boost, as the brief says.
- Not built yet: understory trees (sourwood, dogwood, striped maple, holly, chestnut sprouts), flame azalea, hay-scented fern, the meadow/edge belt, galax.
- Texture memory is RGBA8 (numbers above). KTX2/Basis (BC7/ASTC) would cut it about 4x; the runtime has no transcoder yet.

## Additions, 2026-10-22 (Laurel Fork Cove blockout, pass 2)

**New species.** Three new ids, in a new 1024 atlas `br_understory` (`T_Veg_BrUnderstory_Leaf`), so no existing atlas or species re-packed. Built with `trees.py -- --kit blue_ridge --species flowering_dogwood,sourwood,flame_azalea`, about 1 minute:

| id | kind | height | LOD0 / LOD1 / LOD2 tris | look |
|---|---|---|---|---|
| `flowering_dogwood` | broadleaf (understory) | 8.1 m | about 2.9k / 0.7k / 0.2k | layered flat crown, opposite ovate leaves with arcuate veins, green June fruit; "alligator" bark (pine_bark, grey) |
| `sourwood` | broadleaf (understory) | 13.4 m | 3.0k / 0.9k / 0.2k | slender and leaning, drooping limbs, serrate glossy leaves, one-sided racemes still in creamy bud; furrowed grey bark (bark_willow) |
| `flame_azalea` | shrub, no hull | 2.2 m | 1.6k / 0.4k / 0.1k | open, few-stemmed, deciduous; pale leaves at the twig tips; orange funnel trusses (#F08A2A) with a yellow blotch |

Impostors: 512/256.

**How the runtime uses the kit** (`viewer/wild/veg.js`, `trees.js`):
- glTFs are parsed for geometry only. Base-colour maps are fetched once per URI (`EXT_texture_webp.source`) and capped at 1024. Normal maps and the kit's hemi-octahedral impostors aren't downloaded.
- Material roles: leaf (MASK); hull (`*_Shell`, and the moss tile on dead wood and rock); wood; soil (root plates).
- A heath's LOD0 draws its hull + wood opaque at renderOrder −1, before its cards. Far LODs are one merged draw, hull triangles first.
- All trees' and shrubs' impostors share one runtime-baked atlas: one draw.
- Ground cover draws its LOD0 only. Variants are used for poplar, hemlock and red oak at q3 only.
- Dead wood and rock (`chestnut_log_2`, `blowdown_log`, `creek_boulder`) are instanced as props from their LOD1.

The blockout's draw calls with the whole kit placed came to 19-48 at q3, against the ~280 of instancing every variant (`blockout.md`, "Pass 2 numbers").
