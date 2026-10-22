# Wilderness terrain pipeline (tech spike)

Status: spike, 2026-10-21. It works end to end on macOS: numpy for the heightfield and Blender headless for meshes and renders. No concept has been chosen yet. Every concept in `design/wilderness/*/brief.md` drives this same generator through its parameters. Nothing here has been placed in a level or wired into the engine.

| | |
|---|---|
| Generator (numpy, no Blender) | `blender/wilderness/terrain.py` |
| Meshes, glTF, renders (Blender) | `blender/wilderness/terrain_blender.py` |
| Mask contact sheet | `blender/wilderness/sheet.py` |
| Outputs | `build/wilderness/<name>/` (the demo is `build/wilderness/demo/`) |

```sh
PY=/Applications/Blender.app/Contents/Resources/5.0/python/bin/python3.11   # Blender's Python: has numpy
$PY blender/wilderness/terrain.py                 # demo, 1.5 m cells, ~22 s
$PY blender/wilderness/terrain.py --quick         # 3 m cells, ~8 s, for iterating on shapes
$PY blender/wilderness/terrain.py --name x --set cell=1.0 --set erosion.droplets.per_cell=0.5
$PY blender/wilderness/sheet.py demo              # masks + previews on one sheet
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
    --python blender/wilderness/terrain_blender.py -- demo [--no-render] [--no-export]   # ~13 s
```

How it fits the project rules:
- **Reproducible.** The same `P` and seed give the same terrain bit for bit; two runs were checked and produced identical `.npz` and `.png` files. The work stays in the script, not in files.
- **Dependencies.** No new ones. Phase 1 needs only numpy and the standard library (no scipy, no PIL), so it runs on Blender's bundled Python 3.11 without starting Blender and needs no run slot.
- **One Blender command.** Phase 2 takes a `level` slot (`blender/tools/slots.py`) because it builds about 3M triangles and renders on the GPU.

## What the demo looks like

The demo layout is concept-agnostic and exists to exercise every feature:
- the estate gate at the south edge;
- a valley drained by a river towards the south-west, with a lake in a basin;
- a mesa with a carved cliff on its west rim;
- a mountain range across the north with a pass;
- a trail from the gate to the pass, with switchbacks, a ford, a camp pad, an overlook pad and a pass pad.

| | |
|---|---|
| ![relief](../../../build/wilderness/demo/relief.png) | ![macro vs final](../../../build/wilderness/demo/relief_macro_vs_final.png) |
| Shaded relief: hypsometric tint, water, trail (red), pads (yellow) | Authored large forms only (left) vs after erosion, hydrology and hooks (right) |

![masks](../../../build/wilderness/demo/sheet.png)

| | |
|---|---|
| ![aerial](../../../build/wilderness/demo/render_aerial.png) | ![engine look](../../../build/wilderness/demo/render_aerial_engine.png) |
| Eevee, mask-driven material, sun from the `golden` LOOK | **Engine look**: unlit vertex colour ("Bake" slot), what `MeshBasicMaterial` would draw |
| ![gate](../../../build/wilderness/demo/render_gate.png) | ![ford](../../../build/wilderness/demo/render_ford.png) |
| From above the gate, looking north at the pass | The trail fording the stream, with the trail's cut and fill banks |
| ![camp](../../../build/wilderness/demo/render_camp.png) | ![mesa](../../../build/wilderness/demo/render_mesa.png) |
| Eye height at the camp, looking at the lake | The carved cliff band on the mesa |

At eye height the bare 1.5 m surface reads as smooth dunes (the camp shot). That is expected: close-up realism comes from detail textures, scatter and props on top of this surface (see the next steps). The relief and the far views are what this spike is judged on.

## How it works (stage order matters)

Arrays are `[row, col] = [y, x]` with row 0 at the **south** edge. Every image and binary written to disk has row 0 at the **north** edge. That is the image convention, and it also equals the smallest three.js z, because three.js z = -Blender y. Units are Blender metres, z up, with the origin at the terrain centre.

1. **Macro (authored forms).**
   - Each control shape is a distance-field profile. `ridge` and `valley` take Catmull-Rom splines with height (or depth) and base width per point. `basin` and `plateau` are rotated ellipses.
   - There is also a regional tilt, plus an optional **sketch guide**: a grey PNG or `.npy` of any size over the square, white = +`guide_height` m.
   - Ridges combine with max, so junctions don't double up. Valleys and basins subtract.
   - `shape_jitter` adds noise to every distance field, so contours are never geometric.
   - Polyline distances are computed one segment at a time over that segment's bounding box, which is cheap.
2. **Detail.** Domain-warped fBm on the lowlands, plus a Musgrave ridged multifractal on the mountains. A mask from the ridge field (`detail.mountain`) controls where the ridged part applies.
   - The noise is gradient (Perlin) noise evaluated at world coordinates, with every octave rotated. It is not FFT noise, so the coarse backdrop samples the same function and meets the fine field without a seam.
3. **Fluvial erosion** (`erosion.fluvial`). Stream-power incision runs on a 4x coarser grid (6 m), using the implicit scheme of Braun & Willett 2013 with n = 1, plus hillslope diffusion, for 50 iterations.
   - Each iteration does an epsilon priority-flood, then D8 receivers, then flow accumulation, then an O(n) solve in receiver order.
   - Filled basins keep their beds, so lakes survive. The height change is upsampled to the fine grid.
   - This pass carves the dendritic valley networks. Droplets can't do that on their own, because each droplet only travels about 80 m.
4. **Droplet erosion** (`erosion.droplets`). Particle hydraulic erosion after Beyer 2015 / Lague, **vectorised across droplets**: 65,536 droplets advance together, one cell per step, for 56 steps.
   - Each step: bilinear height and gradient, inertia, sediment capacity proportional to drop × speed × water. Erosion goes through a radius-2 brush and deposition bilinearly; both are applied with `np.bincount`. Then evaporation.
   - The default is 0.15 droplets per cell (it was 0.8, which rilled old mountains into badlands at 1.5 m; the numbers below were measured at 0.8, which took about 4 s at 1.5 m).
   - `scales=(4, 1)` adds a coarse pass first. Tried and rejected for the demo: it leaves pockmarks and dams at the map border.
   - The net height change is kept as the **sediment** mask (deposits).
5. **Thermal erosion** (`erosion.thermal`). Talus relaxation at 38° over 8 neighbours for 40 iterations. It makes scree slopes and removes droplet spikes. What it piles up is also added to the sediment mask.
6. **Cliffs** (hook, applied after erosion so they stay crisp).
   - The edge height is the terrain sampled along the spline, then smoothed.
   - On the low side the ground drops `height` m across `edge` m and then runs out at the talus angle. On the high side it is kept at least as high as the edge.
   - The edge is ragged by noise, faded at the ends, and has faint strata.
   - Any trench left at the foot is filled by a local priority-flood (a 2° talus apron that drains), so it doesn't become a lake.
7. **Hydrology.**
   - **Fill and flow.** An epsilon priority-flood (Barnes et al. 2014, a heap in pure Python, about 1.5 s for 1M cells) gives the lowest surface that drains to the border. D8 receivers on that surface feed the flow accumulation: one Python loop in descending height order, about 0.5 s.
   - **Lakes.** Each lake is a connected component of fill depth, labelled vectorised by min-propagation with pointer jumping. A component becomes a lake when it is larger than `lake_min_area` and deeper than `lake_min_depth`. The lake is **flat at the spill level minus `freeboard`**.
   - **Lake shores.** A shelf under the water and a beach above it, both graded by distance to the shore (a jump flood).
   - **Rivers.** Cells whose catchment exceeds `river_area` become rivers. Width = `width_k`·√(area km²), clamped to 3–14 m; depth = `depth0 + depth_k`·width (the hydraulic geometry rule of thumb).
   - **River carving.** A jump-flood nearest-river-cell transform gives every cell its distance to the river and that river cell's width and bed level. The channel profile is parabolic, the banks are graded at `bank_deg` over `bank_w`, and the bank band is softened.
   - **Water surface.** The river water level is the ground minus `bank_drop`, smoothed along the channel. It is exported as its own mesh.
8. **Pads and corridors** (hooks, authoritative).
   - **Pads** flatten a disc at its median height (or a given height). Fills slope at up to 33°, cuts at up to 50°, and only the shoulders are rounded.
   - **Corridor height profile.** The terrain is sampled along the path spline, box-smoothed over `smooth` m, then **grade-limited** (forward and backward Lipschitz passes, averaged), which guarantees |dh/ds| ≤ `max_grade`.
   - **Corridor shape.** Within `width`/2 the ground is exactly the path height. Beyond that, the terrain is clamped between the lower and upper envelopes of fill and cut banks rising from **every** path point. Stacked switchback legs therefore cut and fill consistently, and the nearer leg wins where they conflict. The shoulders are rounded and the walking surface is not.
9. **Fords.** Where a river crosses a corridor and the overlap is short (a real crossing), the river channel is cut back through the path, so the path doesn't dam the river. A river running **along** a path is reported in `river_along_path` and the path wins there. Ford positions and widths are written to `stats.json`, ready for stepping stones or bridge props.
10. **Masks, light, backdrop.**
    - **Masks.** Recomputed on the final surface (list below).
    - **"Bake" stand-in.** A numpy light pass: Lambert sun × a soft heightfield shadow (40 marched samples to 600 m), plus sky visibility from horizon angles in 12 directions. Multiplied by a mask-driven albedo, it gives colour × light, normalised to the 99.5th percentile like `bake.py`'s outdoor scales.
    - **Backdrop.** A 4.6 km coarse ring at 12 m cells. It uses the same macro function plus framing hills towards the edge, the same fluvial and thermal erosion, and the fine field written into its centre.
    - **Backdrop seam.** The mismatch with the fine border is blended out: the smooth part over 320 m, the detail over 36 m. Albedo is blended the same way.

Changes since the spike (Laurel Fork blockout, `../blue_ridge/blockout.md`): pads take a `reach`
(and a rectangle form, `half`); a `knicks` hook makes river steps (after erosion, plunge pools after
the cliffs); `paths[].switchbacks` lays grade-limited switchback stacks where a climb is too steep for
`max_grade`; `masks.rock_deg` / `cliff_rock` and `backdrop.rock_deg` set where rock is painted; cliff
faces fade at their ends and run out below as lowered ground, not a trench; `backdrop.holes` hold
rects flat outside the square.

## Parameters (`P` at the top of `terrain.py`)

| key | what | demo |
|---|---|---|
| `seed`, `size`, `cell` | reproducibility; square side (m); sample spacing (m) | 7, 1536, 1.5 (1025² samples) |
| `base`, `tilt` | base height; slope (east, north) in m/m | 0, (0, 0.045) |
| `shapes` | `ridge` / `valley`: points (x, y, height or depth, width), `sharp`; `basin` / `plateau`: center, radius (rx, ry), angle, depth / height, edge | 3 ridges, 1 valley, 1 basin, 1 mesa |
| `guide`, `guide_height` | sketch image (grey PNG or .npy) added to the macro | none (tested with `build/wilderness/_guide/guide_example.png` → `guide_test`) |
| `shape_jitter` | noise on shape outlines (m) | 35 |
| `detail` | warp, low fBm (amp, wavelength, octaves), ridged high (amp, wavelength, octaves), mountain-mask range | 70 m warp, 22 m low, 80 m ridged |
| `erosion.fluvial` | factor, iters, k (= K·dt), m, diffusion | 4, 50, 0.02, 0.5, 0.15 |
| `erosion.droplets` | per_cell, batch, lifetime, inertia, capacity, erode / deposit / evaporate, radius, max_step (m), scales | 0.8, 65536, 56, 0.25, 4, 0.3/0.25/0.02, 2, 0.35, (1,) |
| `erosion.thermal` | talus_deg, iters, rate | 38, 40, 0.45 |
| `hydro` | river_area (m²), width_k, width (min, max), depth, bank_drop, bank_w, bank_deg, lake_min_area / depth, freeboard, beach / shelf | 1.2e5, 8, (3, 14), ... |
| `cliffs` | points, height, side (+1 raises the right of travel), edge, back, end_fade, jitter, talus_deg | mesa west rim, 18 m |
| `pads` | center, radius, falloff, height (None = median), bank_deg / cut_deg | gate, camp, overlook, pass |
| `paths` | points, width, shoulder, max_grade, smooth, bank_deg (fill), cut_deg, reach, ford | 1.9 km trail, 4 m, 14% |
| `masks` | path_range, water_range (m), curvature scales | 80, 40, (2, 8) m |
| `look`, `palette` | sun and sky for the light pass (= `mansion.py` LOOKS["golden"]); linear albedos | |
| `backdrop` | extent, cell, frame_height, frame_wavelength, blend | 4608 m, 12 m, 110 m |
| `chunks`, `lods` | chunks per side; LOD steps in cells | 8; (1, 2, 4, 8) |

`--set` takes dotted keys with JSON values. A concept should not edit the defaults: it passes overrides (see the last section).

## Outputs (`build/wilderness/<name>/`)

| file | format |
|---|---|
| `height16.png` | 16-bit grey, 1025², normalised to [min, max] from `stats.json` (6 mm steps over 360 m). Uses the PNG "Up" filter only, so a decoder unfilters with one cumulative sum. |
| `collider_u16.bin` | the same quantised heights, raw little-endian uint16, rows north → south (= three.js −z → +z). Metadata in `stats.json` `collider`. |
| `masks/*.png` | 8-bit: `slope` (0–90°), `altitude`, `flow` (log accumulation), `wetness` (TWI ln(a / tan β), blurred, max'd with water proximity), `curvature` (128 = flat, above = ridge or convex, below = gully; scales 2 m + 8 m), `aspect` (downslope bearing, 0 = north), `path` (distance 0–80 m), `rivers`, `lakes`, `sediment` (deposits) |
| `masks/splat_rgba.png` | packed for a splat shader: R slope, G wetness, B curvature, A sediment |
| `albedo.png`, `bake.png`, `relief.png`, `relief_macro_vs_final.png`, `sheet.png` | previews |
| `terrain.npz` | float heights, bake colours, water levels, backdrop (input to the Blender phase) |
| `stats.json` | parameters' results: lakes, rivers, fords, pads (resolved heights), paths (grade, cut/fill), walkability, timings, file sizes, grid and collider metadata |
| `models/terrain_L{0..3}.gltf` | one file per LOD, 64 chunk nodes `Wild_Terrain_<cx>_<cy>_L<k>` (extras: chunk, lod, step_m, outdoor), Draco, attributes POSITION, NORMAL, TEXCOORD_0 (0–1 over the square, for the masks), **COLOR_0 = "Bake"** |
| `models/lean/terrain_L*_lean.gltf` | the same without normals and UVs (for an unlit engine that derives them from position) |
| `models/water.gltf` | `Wild_Water_Lakes` (3 m grid at the lake level) + `Wild_Water_Rivers` (1.5 m grid on the river surface), extras `outdoor = "water"` |
| `models/backdrop.gltf` | `Wild_Backdrop_Ring` (12 m, with an inner skirt facing the play area), COLOR_0 = Bake |
| `manifest.json` (Blender phase) | LOD triangle counts, skirt depths, file sizes, import check, timings |
| `render_*.png` | Eevee renders + `render_aerial_engine.png` (unlit Bake) |

## Numbers (M4 Pro, 14 cores, 24 GB; other agents were using the CPU at the same time, so timings carry ±30%)

**Generation (numpy phase, single-threaded)**

| cell | samples | generate | + write | peak RAM |
|---|---|---|---|---|
| 3 m (`--quick`) | 513² | 8.3 s | 9.4 s | – |
| 2 m | 769² | 13.6 s | 16.2 s | 0.74 GB |
| **1.5 m (demo)** | **1025²** | **22.0 s** | **27.5 s** | **1.0 GB** |
| 1 m | 1537² | 49.5 s | 63.7 s | 2.0 GB |

Stage breakdown at 1.5 m (s):

| macro + detail | fluvial | droplets | thermal | cliffs | hydrology | hooks | masks | light | backdrop | write |
|---|---|---|---|---|---|---|---|---|---|---|
| 2.0 | 3.1 | 5.1 | 1.1 | 0.1 | 1.8 | 0.6 | 0.7 | 3.4 | 4.3 | 5.4 |

**Blender phase at 1.5 m: 13 s** (chunks 1.4 s, export 7.0 s, import check 2.0 s, 5 renders 2.6 s). At 1 m without renders: 22 s.

**Mesh LODs.** 8×8 chunks of 192 m, 128 cells each. Skirts hide LOD cracks. Each skirt's depth is that LOD's measured worst border error plus 0.5 m.

| LOD | spacing | tris / chunk | tris (all 64) | + skirts | skirt depth max / mean | glTF (Draco) | lean |
|---|---|---|---|---|---|---|---|
| 0 | 1.5 m | 32,768 | 2,097,152 | 2,162,688 | 0.5 / 0.5 m | 10.4 MB | 7.9 MB |
| 1 | 3 m | 8,192 | 524,288 | 557,056 | 1.9 / 1.4 m | 3.3 MB | 2.4 MB |
| 2 | 6 m | 2,048 | 131,072 | 147,456 | 3.2 / 2.1 m | 1.05 MB | 0.74 MB |
| 3 | 12 m | 512 | 32,768 | 40,960 | 8.3 / 3.9 m | 0.38 MB | 0.26 MB |

At 1 m cells, LOD0 is 4.7M tris and 21.7 MB.

Other meshes:
- backdrop: 263k tris, 0.96 MB;
- water: 3.7k tris for lakes and 18.2k for rivers, 0.03 MB in all.

Data:
- `height16.png` 1.42 MB;
- `collider_u16.bin` 2.1 MB raw, 1.9 MB gzipped (raw heights hardly compress, so ship the PNG);
- `splat_rgba.png` 2.4 MB (it would be well under 1 MB as WebP).

**Checks**
- LOD0 was re-imported (Draco decoded) and ray-cast at 3,000 random points against `terrain.height_at`, the collider's formula: **max 1.4 cm, mean 0.27 cm** off. That gap is Draco's 14-bit position quantisation per chunk.
- The 16-bit collider is at most 2.8 mm from the float heights.
- The "Bake" colour arrives as COLOR_0.

**Walkability (demo)**
- Terrain slope: p50 25°, p90 49°. 60% of the area is under 35°. The ranges are steep; that is a parameter.
- Trail, measured on the final surface every 0.5 m:
  - grade p50 6.6%, p99 14.3%;
  - the maximum, 65%, is the ford bank, a 1 m dip;
  - cross-slope p50 0.6°, p99 6°.
- Cut and fill on the trail is at most 18 m, at the pass.

**Hydrology (demo).** One lake (18k m², flat at −6.45 m), 3.7 km of carved rivers up to 8.2 m wide, and one ford at (−70, −604).

## Engine integration (not built; for whoever wires it in)

**Walkable surface / collider.** Load `collider_u16.bin`, or decode `height16.png` with `DecompressionStream('deflate')` plus an Up-filter cumulative sum (no library needed). Heights are `h = q * scale + height_min` (`stats.json` `collider`). Sample with the **same triangulation as the mesh**, in Blender (x, y):

```js
// u = (x - x0) / cell, v = (y - y0) / cell; i = floor(u), j = floor(v), fu = u - i, fv = v - j
// a = H[j][i], b = H[j][i+1], c = H[j+1][i+1], d = H[j+1][i]   (row j = south-up index)
h = fu >= fv ? a + (b - a) * fu + (c - b) * fv : a + (c - d) * fu + (d - a) * fv;
```

This matches LOD0 to 1.4 cm and the coarser LODs to within their skirt depth. Physics should always use the full-resolution field, never the LOD you are looking at.

`player.js` today knows boxes and ramps only. It needs:
- a `groundHeight(x, z)` query that falls back to this sampler outdoors;
- a maximum walkable slope taken from the normal or the slope mask (about 40°), so steep faces block like walls.

Water is meshes; `sky.js`'s water shader applies. Fords and pads in `stats.json` are where props (stepping stones, a bridge, a camp) belong.

**Draw budget.** The house peaks at 501k triangles and 657 draw calls. Estimates from the measured per-chunk counts, with LOD chosen by distance from the player to each chunk's bounds:

| layout | thresholds (LOD 0/1/2/3) | tris | draw calls |
|---|---|---|---|
| 8×8 chunks | < 60 / 250 / 600 m | 117k–291k (worst at a chunk corner, 4 LOD0 chunks) | 64 |
| 16×16 chunks (`chunks=16`) | < 40 / 200 / 500 m | ≤ 165k | 256 |

The backdrop adds 263k at 12 m; at `backdrop.cell = 24` it is about 66k.

Recommended path for the web build:
1. Ship `height16.png` plus a WebP bake/splat (about 3 MB for the whole 1.5 km, against 15.2 MB for all four glTF LODs).
2. Draw it with a **vertex-shader-displaced clipmap**: a few nested grid rings around the camera, one draw call each, about 100k tris, heights fetched from the texture (WebGL2 vertex texture fetch).
3. Keep the glTF chunks for Blender-side baking (Cycles via `bake.py`'s outdoor path), for previews, and as a fallback.

Either way the heightfield and masks are the source of truth.

**Lighting.** The "Bake" slot is a numpy stand-in (sun, shadow, sky visibility) in the same convention as the grounds: colour × light, normalised, with the scale `light_scale` in `stats.json`. It lets the engine draw the terrain unlit immediately, like `Mansion_Outdoor_Flat`. The objects carry `outdoor = "flat"`, so `bake.py`'s outdoor Cycles pass can overwrite the slot later. One caveat: vertex lighting at 3–12 m (LOD1–3) is coarse. A 1–2k lightmap over the square would be better, and the splat mask should multiply detail textures.

## How a chosen concept drives it

A concept becomes a parameter file, not a fork: `blender/wilderness/<concept>.py` with `P = dict(...)` overrides that calls `terrain.build(name=..., **P)`, then runs the Blender phase on that name. The brief's vocabulary maps onto the inputs:

| brief says | parameters |
|---|---|
| "a long ridge / a wall of mountains / a spine" | `ridge` shapes: points with height and width (width ≈ 4–5× height reads natural, about 30°); `detail.high_amp` for ruggedness |
| "a gorge / canyon / river valley" | `valley` shapes (narrow, deep) + lower `river_area` + `erosion.fluvial.k`; cliffs along the rims |
| "a lake / tarn / flooded basin / swamp" | `basin` shapes (lakes appear by themselves: the fill keeps any basin deeper than `lake_min_depth`); a swamp = a shallow wide basin, small `freeboard`, low `lake_min_depth`, the `wetness` mask for vegetation |
| "a mesa / plateau / tableland / caldera" | `plateau` shapes (+ an inner `basin` for a caldera) + `cliffs` on the rims |
| "the player's route / chokepoints / a chase line" | `paths` (width, max_grade; ford=False if a bridge is wanted), `pads` for arenas, camps, hiding hollows, landing spots for props |
| "a hand-drawn map" | `guide` PNG (white = high) with `guide_height`, then shapes and hooks on top |
| "fog-bound / desolate / lush / burnt" | `palette`, `look` (any `mansion.py` LOOK), `backdrop.frame_height`; masks feed vegetation scatter (wetness, slope, altitude, aspect) |
| "bigger / smaller" | `size`, `cell` (keep cell ≤ 2 m in the playable area), `backdrop.extent`; the budgets above scale with area |

Iterate with `--quick` and the relief or sheet, then run once at full resolution with the Blender phase. Erosion settings depend on the cell size (droplets move one cell per step, and river thresholds are in m² of catchment while D8 lines change with the grid). Settle a concept at the resolution it will ship at: the demo at 1 m found 4 fords where 1.5 m found 1.

## Limits and next steps

- **Heightfield only.** No overhangs, caves or arches; those are separate meshes placed on top. Cliffs are near-vertical faces stretched over 1.5 m cells, so close-up rock faces need rock-face props or cliff meshes along `cliffs`.
- **D8 channels are a bit straight at 45°.** Rivers don't meander. A spline fit through the river cells plus meander noise before carving would fix both. Rivers end at the map edge, and the backdrop has none.
- **LOD seams.** Hidden by skirts only, with no geomorphing, so the switch between LODs can pop. Fine for distant chunks; a clipmap with morphing is the clean fix.
- **The "Bake" is an approximation.** It has no bounce and no shadows from props. The lit Eevee renders here are flatter than the engine look and are only a preview.
- **Narrow features.** The hooks are exact, but the trail at 4 m is only about 3 cells wide at 1.5 m. Narrow paths want `cell ≤ 1 m` locally, or a path decal.
- **Erosion on sharp authored forms.** Very steep forms (mean slope over about 40°) keep a "tube" look that erosion can't break. Keep ridge width ≥ 4× height.
- **Vegetation scatter and detail textures (next stage).** From `wetness`, `slope`, `altitude`, `aspect`, `curvature` and `sediment`. `build/wilderness/veg/` belongs to another agent.
- **Streaming beyond 1.5 km.** Heights are one array; a bigger world would generate tiles with overlap. The noise is world-space, so tiles would match.

References: Beyer 2015 (droplet erosion); Lague 2019 (vectorisable variant); Braun & Willett 2013 (implicit stream power); Barnes, Lehman & Mulla 2014 (priority-flood); Musgrave 1989 (ridged multifractal); Rong & Tan 2006 (jump flooding); Beven & Kirkby 1979 (topographic wetness index); de Boer 2000 / Losasso & Hoppe 2004 (geomipmapping / geometry clipmaps).
