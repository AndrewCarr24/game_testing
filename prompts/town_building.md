# A town building at the mansion's fidelity (instructions for a sub-agent)

Three agents each build ONE building of Sourwood, N.C. (the town downstream of the estate:
design/town/brief.md, design/game_direction.md): the bar, the gas station, the diner. The user had
the earlier kit town removed because it wasn't good enough: "the resulting buildings should be the
same level of fidelity as the mansion." Study what makes the mansion good before you start: its
generator-built shell (blender/lib/house.py, blender/levels/plan.py), rooms dressed with real
furniture assets (blender/levels/rooms/*.py, blender/assets/*.py, the hero-asset bar in
prompts/hero_asset.md), Poly Haven scans (blender/tools/polyhaven_*.py), and above all the Cycles
baked lighting (blender/levels/bake.py, viewer/baked.js: lightmaps, SH probes, reflections). Look at
it in the engine (viewer/index.html?level=mansion, the review/shots tools) and aim for that: real
proportions, layered materials, bevelled edges, set-dressed interiors, believable light.

## Where it goes
Your building's site is in `blender/wilderness/levels/laurel_town.py` `layout_buildings()` (bar,
gas, diner: footprint centre, yaw, the KIT "site_*" size). You may change ONLY your own site's
size/position (small, marked edit); the world builder flattens its pad. The town is seen in the
wilderness runtime: `viewer/wild.html?world=laurel_town` (views in laurel_town.py `views()`; e.g.
`&view=bar_room`, `main_street`, `strip`). Rebuild the town world after a change:
`/Applications/Blender.app/Contents/Resources/5.0/python/bin/python3.11 blender/wilderness/levels/laurel_town.py`
(~40 s, after `laurel_fork.py` has been run once in your worktree).

## The contract (viewer/wild/town.js `loadSites`, laurel_town_world.py)
- Export `assets/models/town2_<id>.gltf` (id = bar | gas | diner; Draco ok) with the asset origin at
  its floor centre, front facing -Y (Blender), like every asset; and a sidecar
  `assets/models/town2_<id>.json` = `{ "footprint": [x0, y0, x1, y1], "size": [w, d, h],
  "colliders": [[x0, y0, z0, x1, y1, z1], ...] }` in the asset's Blender frame (walls split at
  doorways, counters, booths, pumps...: the player walks in and around). With the sidecar the world
  builder adds your colliders and the runtime places your model on the site.
- Baked light: bake your building's lighting in Cycles (its own lamps, neon, the sun/sky of the
  "golden" look in blender/levels/mansion.py LOOKS, interior and exterior) into lightmap texture(s)
  on a second UV set (TEXCOORD_1), and name them in each material's extras: `lightmap`
  (path relative to assets/models/, e.g. "textures/T_Town2_Bar_Lightmap.webp") and
  `lightmapIntensity`. The runtime sets `material.lightMap` (channel 1) from them. Emissive
  surfaces (neon, screens, signs) as emissive materials. No real-time lights. Write your own
  bake script under `blender/town/<id>/` (reuse bake.py's ideas: denoise, light strips).
- Budget for one building: ~60-150k triangles total incl. interior (LOD1 far version `<Root>_LOD1`
  for the outside), <= ~25 draw calls, textures <= ~20 MB GPU (1-2k lightmap + shared material
  maps), download <= ~6 MB. Measure with viewer/tools/wild_bench.mjs (`WILD_QS="&world=laurel_town"`)
  and say what you cost.
- No readable signage text beyond what a real place has (the bar's neon "BAR" is fine; no lore,
  no notes). The town is in cahoots with the invaders: environmental hints only (brief "The turn").

## Rules
- Own only: `blender/town/<id>/`, `blender/assets/town2_<id>*.py`, `assets/models/town2_<id>*`,
  `assets/models/textures/T_Town2_<Id>_*`, `design/town/<id>.md`, and your site's entry. Small
  marked hooks elsewhere only if unavoidable.
- One Blender command at a time (blender/tools/slots.py governs machine-wide slots); browsers via
  build/locks/browser_0..2.
- Iterate as an art director against real references (name them; e.g. a real Blue Ridge roadhouse,
  a modern Sheetz/Buc-ee's-style or a small-town gas station, a classic chrome diner or a modern
  mountain-town diner): many rounds of renders and in-engine screenshots from the player's eye,
  outside (day) and inside. Write design/town/<id>.md (what, references, numbers, images).
