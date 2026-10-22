# Vegetation pipeline spike (wilderness)

Status: spike, 2026-10-21. Concept-agnostic: how we make game-ready trees and plants for a big
browser wilderness on macOS. Nothing here is placed in a level, and nothing is committed.

## Recommendation

**Build trees with our own scripted generator (`blender/wilderness/trees.py`), dressed with leaf and
bark scans from Poly Haven. Don't decimate scanned trees. Don't buy The Grove or SpeedTree for now.**

- The generator produced 2 trees, a shrub and a ground-cover clump, each with 3 LODs, wind data, crown AO
  and (for the trees and shrub) an impostor atlas. One headless Blender run takes ~55 s for all four.
  Each LOD is regenerated from the same skeleton, so the LODs agree in silhouette and shading.
  Decimating a scan cannot do that.
- Decimating a scan fails where it matters (numbers below). At 12k triangles a 1.07M-triangle
  Poly Haven tree keeps 1.1% of its leaf triangles (7,667 of 714,744), and about a third of the
  leaf mass looks intact in the render. At 3k its leaves are gone (0 leaf triangles) and
  the trunk breaks into slivers. A scan is only usable as "scan trunk + our cards", and that is the
  generator's job anyway.
- What The Grove or SpeedTree would add is better growth and a species library. That matters for
  hero trees, not for the wilderness's first pass. Revisit once the concept picks its species (see
  "Grove / SpeedTree").

## What was built

| file | what |
|---|---|
| `blender/wilderness/trees.py` | generator: skeletons, bark tubes, cards, LODs, crown AO, wind attribute, glTF export, impostor bake, preview sheets, manifest |
| `blender/wilderness/veg_sources.py` | fetches Poly Haven leaf/twig atlases **with their separate alpha maps**, plus bark textures (`build/wilderness/veg/src/`) |
| `blender/wilderness/scan_decimate.py` | route (b): imports a scanned tree, collapse-decimates it, renders, exports, measures |
| `blender/wilderness/veg_shots.mjs`, `veg_perf.mjs` | viewer screenshots (centre crops with `crop=N`) and uncapped frame times on Metal and SwiftShader; they take a `build/locks/browser_N` slot |
| `viewer/wild_veg.html` | three.js 0.160 viewer: `single` / `row` (LOD0, LOD1, LOD2 and impostor side by side) / `forest` (instanced, LOD per instance per frame); wind; distance slider and `sweep` |
| `build/wilderness/veg/` | `<species>.gltf` (+ `textures/`), `<species>_impostor_{albedo,normal}.webp` (1k) and `_2k.png`, `veg.json` manifest, `previews/`, `scan/` |

```
python3 blender/wilderness/veg_sources.py                      # once: Poly Haven maps
Blender -b --factory-startup --python blender/wilderness/trees.py [-- --species fir,ash --no-impostor --no-preview --seed 7]
Blender -b --factory-startup --python blender/wilderness/scan_decimate.py -- island_tree_02
python3 -m http.server 8765   ->  http://localhost:8765/viewer/wild_veg.html?species=fir&mode=row&dist=26
node blender/wilderness/veg_shots.mjs ; node blender/wilderness/veg_perf.mjs 'mode=forest&n=1500'
```

Both Blender scripts take an `asset` run slot (`slots.py`).

## Route (a): scripted generator (built; recommended)

How it works (`trees.py`; every species is a dict in `SPECIES`):
- **Skeletons.** Conifer: an excurrent leader with whorls of 4-6 primaries every ~0.6 m. Their length follows
  a cone; they droop, then turn up at the tip. Card anchors alternate along each primary.
  Broadleaf and shrub: recursive growth (tropism, wobble, sag; children at a set angle and
  golden-angle azimuth). Child lengths are clipped to a crown ellipsoid, so the envelope sets the
  crown's shape and the branching gives the detail. The shrub starts 7 stems from the base.
- **Real taper.** Pipe model: `r = r_tip * n_tips^(1/2)` (da Vinci), plus root flare. Bark is a
  parallel-transport tube. U wraps a whole number of bark tiles around the branch, V runs in world
  metres, and each branch sinks into its parent, so joints don't gap.
- **Cards.** Regions cut by hand from Poly Haven atlases (`FIR_SPRAYS`, `JACARANDA_FRONDS`,
  `WILLOW_LEAVES`, `FERN_FRONDS`: rect + which side the stem base is on). Each card is placed from
  its stem base with real aspect ratio and droop. Poly Haven's glTF leaf JPEGs have no alpha, so
  `veg_sources.py` fetches the separate `*_alpha` map. The combined RGBA atlas is colour-dilated
  under transparent texels (no dark mip halos) and tinted per species.
- **LODs are regenerated, not decimated.** Each LOD sets tube sides, polyline step, a minimum branch
  length and the share of cards to keep. Kept cards prefer the outer crown, and survivors grow by
  `sqrt(1/keep)` so the crown keeps its leaf area. The conifer also gets a base layer of one
  crossed spray pair per primary branch. Alone, that layer is its LOD2.
- **Bake and export.** Crown AO, wind attribute and foliage normals (see "Per-vertex data") →
  `common.export_gltf` (Draco, WebP, `export_attributes=True`). Leaf materials are post-set to
  `MASK` 0.5 and double-sided. Then the impostor bake and an Eevee preview sheet.

Results (seed 7; tris per LOD; Draco geometry for all three LODs; textures shipped as WebP):

| species | height | LOD0 | LOD1 | LOD2 | impostor | geometry | textures | build (+imp) |
|---|---|---|---|---|---|---|---|---|
| `fir` conifer (spruce-like) | 15.7 m | 9,448 (3.2k wood / 6.2k cards) | 2,562 | 590 | 2 tris, 8x8 frames | 190 KB | 323 KB | 22 s |
| `ash` broadleaf | 12.8 m | 11,486 (4.6k / 6.9k) | 2,512 | 659 | 2 tris, 8x8 frames | 201 KB | 403 KB | 19 s |
| `shrub` (willow-leaf) | 1.6 m | 4,390 | 956 | 340 | 2 tris, 8x8 frames | 113 KB | 190 KB | 12 s |
| `fern` clump (ground cover) | 0.5 m | 96 | 32 | 10 | none (fade out at 30 m) | 7 KB | 95 KB | 1 s |

LOD switch distances in `veg.json` (`lod_dist`): fir 22 / 50 / 95 m, ash 20 / 45 / 85 m, shrub
10 / 22 / 40 m, fern 8 / 18 / 30 m (then culled). Every LOD is 2 draw calls (bark + leaf), 1 for the fern.

Blender previews (LOD0, LOD1, LOD2, LOD0 close-up):

![fir](../../../build/wilderness/veg/previews/fir.png)
![ash](../../../build/wilderness/veg/previews/ash.png)
![shrub](../../../build/wilderness/veg/previews/shrub.png)
![fern](../../../build/wilderness/veg/previews/fern.png)

In three.js (`mode=row`; the labels give each representation's triangle count):

![fir row](../../../build/wilderness/veg/previews/viewer_fir_row.png)
![ash row](../../../build/wilderness/veg/previews/viewer_ash_row.png)

Strengths: every parameter is code, so it's reproducible and diffable. Variants come from the seed.
Each species is ~40 lines of parameters. LODs, AO, wind and impostors come out of the same run.
Weaknesses so far: no light competition or self-pruning (crowns are envelope-shaped), no
branch-collision avoidance, and close-ups show the cards are cards. The cards come from atlases
that were never authored as game cards, and the jacaranda fronds give the broadleaf a slightly
exotic, pinnate look.

## Route (b): Poly Haven scan, decimated (tested; rejected)

`island_tree_02`: 1,072,212 tris (715k leaves, 330k branches, 27k trunk). 40 MB `.bin` at 1k
textures. Imports in 4.3 s. Collapse decimation takes ~4.3 s per target.

| target | result | leaf tris | geometry | textures |
|---|---|---|---|---|
| original | 1,072,212 | 714,744 | 40 MB | 1k JPEG |
| 12k | 12,000 | 7,667 (1.1% of the leaf tris; roughly a third of the leaf mass looks intact in the render) | 223 KB | 1.2 MB |
| 3k | 3,401 | **0** (collapse removed every leaf quad) | 66 KB | 1.0 MB |

![scan decimated](../../../build/wilderness/veg/scan/island_tree_02_decimated.png)
*(original, 12k, 3k)*

Collapse decimation treats leaf cards as geometry to simplify. Each leaf is 2-4 triangles with its
own UV island, so it can only vanish or smear. The trunk survives at 12k and shreds at 3k. Other
problems: no wind data, no LOD coherence, scan-specific UV atlases (no world-scale bark), and of
the 5 scanned trees in `build/polyhaven/models/`, three are iCloud "dataless" on this Mac
(`fir_tree_01` 478 MB, `jacaranda_tree` 208 MB, `island_tree_01` 60 MB: evicted, re-downloaded on read). Still useful: the scans' leaf, twig and bark *maps* (route (a) uses them),
offline renders (`horizon.py` already does that), and maybe a hero trunk with our cards on top.
That "scan trunk + our cards" path converges with route (a).

## Route (c): The Grove and SpeedTree (not bought; what they would add)

- **The Grove** (Blender add-on; per the brief ~EUR 89-149 one-off, prices not re-checked; runs on Mac).
  It adds a real growth simulation: light competition, gravity, self-pruning and years of growth,
  so crowns and branch spacing look grown rather than enveloped. It also adds sold-separately twig
  packs (game-ready twig cards) and its own wind bake. Our gap there is mostly crown realism and
  twig-card quality. It's still Blender, so it slots in before our export: our AO, wind and impostor
  code would run on its meshes. Worth trying for 1-2 hero species if the concept wants
  recognisable real trees.
- **SpeedTree** (per the brief ~$19/mo Indie, library ~$999/yr; Modeler runs on Mac). It adds a
  large library of ready species, automatic LOD chains and billboard/impostor atlases, and a mature
  wind model. Its wind and runtime target Unity and Unreal. For three.js we'd export FBX/OBJ, lose
  that wind, and redo vertex data, impostors and materials. That is most of what this spike already
  does. It's also a subscription plus library fees.
- Neither changes the runtime side (instancing, LOD selection, impostor shader, alpha handling),
  and that's where the browser budget is won or lost.

## Comparison

| | (a) generator | (b) scan, decimated | (c) Grove | (c) SpeedTree |
|---|---|---|---|---|
| look at 5-20 m | good (cards) | excellent only at 1M tris | very good | very good |
| LOD0/1/2 quality | coherent, regenerated | breaks below ~12k | regenerated | automatic |
| impostors | ours (8x8 hemi-octa) | would need ours | would need ours | built in (format to adapt) |
| wind data in glTF | `_WIND` (ours) | none | own bake, convert | engine-specific |
| reproducible / scripted | yes (seeded code) | partly | partly (GUI-first, has Python) | no (GUI) |
| variety cost | free (seeds, params) | 1 scan = 1 tree | free (growth sim) | library |
| cost | time | free (CC0) | ~EUR 89-149 | ~$19/mo + $999/yr |
| macOS | yes | yes | yes | yes |

## Budgets per species (proposal)

| | LOD0 | LOD1 | LOD2 | impostor | leaf atlas | bark | impostor atlas |
|---|---|---|---|---|---|---|---|
| tree | 8-12k | 2-3k | 0.5-0.8k | 2 tris | 1024 RGBA (+512 normal) | 512 + 512 normal (shared) | 1024 albedo + 1024 normal (8x8 x 128 px) |
| shrub | 3-4.5k | ~1k | ~0.3k | 2 tris | 1024 (+512) | shared | 1024 + 1024 |
| ground cover | ~100 | ~30 | ~10 | culled at ~30 m | 1024 (+512) | none | none |

GPU memory per tree species (RGBA8 + mips): leaf atlas ~5.6 MB plus a 512 normal ~1.4 MB, bark
pair ~2.8 MB (shared), and the impostor pair ~11 MB at 1k (~45 MB at 2k). This set (3 impostor
species + fern) ≈ 60-65 MB, against the house's ~210 MB.
Download for this whole set: ~0.5 MB geometry + 0.9 MB textures + 2.4 MB impostors ≈ 3.8 MB (the
house is 13.3 MB). Impostor frame size: at 1k, a 15 m tree gets ~100 px of texture per frame, which
is about its on-screen size at 100 m and 900 p. So 1k frames suit a switch at ~120 m+ (or ship the
baked 2k atlas, `*_2k.png`, for a 95 m switch at DPR 2).

**Forest test** (`viewer/wild_veg.html?mode=forest&n=1500`): 1,500 trees (60% fir) over 600 x 600 m,
1,800 shrubs within 120 m and 6,000 ferns within 45 m. All are InstancedMeshes per species x LOD
x material, re-bucketed by distance every frame on the CPU.

| profile | draw calls | triangles | frame p50 / p95 |
|---|---|---|---|
| M4 Pro, Metal, 1600x900, uncapped | 25 | 305k | 1.5 / 2.5 ms |
| same, every tree forced to impostor | 5 | 30k | 0.9 / 2.4 ms |
| SwiftShader 1280x720 | 25 | 305k | 334 / 379 ms (3 fps) |
| SwiftShader, forced impostors | 5 | 30k | 176 / 206 ms |

![forest](../../../build/wilderness/veg/previews/viewer_forest.png)

Draw calls stay flat as the forest grows. Triangles fit the 501k peak the house runs at. What
hurts weak hardware is **fill/overdraw**: alpha-tested cards with MSAA and alpha-to-coverage,
layered near the camera (ferns, LOD0 crowns). Forcing impostors halves the SwiftShader time but
doesn't fix it. The runtime agent should budget foliage by screen coverage. Options: ground-cover
density by quality level, a shorter LOD0 range, the main viewer's SMAA instead of MSAA, and maybe
opaque "crown shell" meshes inside dense crowns.

## Per-vertex data and engine notes

File contract for the runtime: one `<species>.gltf` per species (Draco, shared `textures/`), root node
`Veg_<Species>` with children `Veg_<Species>_LOD0..2`. Each LOD has two primitives: bark, and a
`*_Leaf` material that is MASK 0.5, double-sided, with no back-face normal flip (the fern has the
leaf primitive only). Impostor files and parameters, LOD distances and triangle counts are in `veg.json`.

- **`_WIND` (vec3, Draco-compressed, arrives in three.js as `geometry.attributes._wind`; checked for all
  four species)**: x = branch bend weight (0 at the trunk, 1 at the outermost tips, by path length from
  the trunk), y = leaf flutter (0 at a card's stem, 1 at its tip; 0 on bark), z = phase 0..1 (per
  primary branch; children inherit). Trunk sway comes from height in the shader. The viewer's
  `patchMaterial` is a working reference: sway ∝ h², branch bend, flutter along the normal, a
  per-instance phase hashed from the instance position, and wind direction rotated into object
  space. The fern stores the bend weight along the frond.
- **AO (`COLOR_0`, exported from the "AO" attribute and multiplied into base colour by three.js)**: sky
  visibility through a 30³ voxel grid of LOD0 leaf area, with Beer-Lambert transmittance along 16
  mostly-upward rays and ground contact darkening. Every LOD samples the same grid, so LODs shade
  alike. `lib/vertex_ao.py` is the wrong tool for crowns: it bakes cards opaque at a 0.3 m distance
  and skips large faces. It's fine for trunks and props.
- **Normals**: cards are blended 65% toward the crown normal (cone for the conifer, ellipsoid for the
  broadleaf), so a crown shades as one volume. Cards are single double-sided quads. **The engine
  must not flip back-face normals for foliage.** The viewer removes three's `normal *= faceDirection`
  for leaf materials.
- **Alpha**: use MASK/alphaTest, never BLEND (no sorting). Alpha-tested crowns erode with distance
  because mip-averaged alpha drops under the cutoff. The viewer boosts alpha by mip level and
  sharpens it into alpha-to-coverage (Golus). The ash at 90 m and the fir at 100 m: no boost,
  boost, impostor:

  ![transition](../../../build/wilderness/veg/previews/viewer_transition_grid.png)
- **Translucency**: a cheap back-light term in the leaf shader,
  `pow(dot(-view, sun), 3) + 0.35 * dot(-n, sun)`, × leaf albedo × sun. There's no transmission
  (it would need a screen copy). The baked outdoor path (`sky.js` `applyOutdoor`, unlit vertex light)
  would need the same term added to stay consistent.
- **Impostor** (`bake_impostor`): an 8x8 hemi-octahedral grid of orthographic Eevee emission renders of
  LOD0. One pass for albedo × AO, one for the stored object-space normal; both keep the card alpha
  cut. Renders go to linear EXR, then are un-premultiplied, dilated and encoded. ~10-20 s per species
  (128 renders at 256 px). Runtime (viewer `impostorMaterial`): an instanced camera-facing quad.
  It blends the 4 nearest frames, projects each frame into its own basis, sharpens alpha into
  alpha-to-coverage, and lights from the normal atlas (hemisphere + sun + back-light).
  Manifest fields: `frames`, `center` (three coordinates), `radius`,
  `normal_space` (`n_three = (x, z, -y)`). No depth/parallax yet. Up close the quad reads ~12%
  smaller than the mesh (orthographic bake vs perspective view), which is invisible past the switch.

## Known gaps and next steps

1. LOD transitions pop. Add a dithered crossfade over ~10% of each band. Select LODs by screen size
   instead of distance.
2. Impostor depth (alpha of the normal atlas) for parallax and soft ground contact. Frame blending
   ghosts slightly when the view sits between frames.
3. A twig-card baker: compose single scanned leaves (island_tree_02, shrub_02, tree_small_02) onto
   procedural twigs and render them to a card atlas with alpha and normal. That frees the broadleaf
   from the jacaranda look and gives any species its own cards. It's the same emission-render code
   as the impostor.
4. Grove-like growth for crowns: light competition (space colonisation with a shadow grid) and
   self-pruning. Seasonal and dead variants (strip cards, keep wood) are free with the generator.
5. A colliders/trunk capsule in the manifest for `player.js`. Wind direction and strength from a
   global uniform shared with grass.
6. `prep_textures` caches the prepared atlases in `build/wilderness/veg/src_prep/`. After changing
   a species' leaf `tint` or source, delete its `T_Veg_<Species>_Leaf*.png` (or add a hash to the name).
7. More species are params, not code: pine (long-needle card), birch (white bark tile, small-leaf
   card), dead snag (no cards). The concept should name the palette.
