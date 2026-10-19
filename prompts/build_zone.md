# Dressing an outdoor zone of the estate (instructions for a sub-agent)


> **One Blender command at a time.** Several agents share this machine; never run Blender builds in parallel (no loops of rooms with `&`, no batches). The build tools queue themselves (at most 2 house builds and 4 asset builds machine-wide); `SLOT ... waiting` means wait.
You are building one zone of the grounds around a modern tech billionaire's mansion
(think a Bezos / Medina or Beverly Hills modern estate) for a three.js game. The lawn,
the stone terrace around the house and the perimeter hedge already exist
(`blender/levels/grounds.py`); you supply your zone's hardscape, structures, furniture
and planting. Read `CLAUDE.md` first, then `prompts/build_asset.md` (its rules for
building each asset still apply, except where this file overrides them), then your
zone's brief in the `## Grounds` section of `specs.md`.

## How the player sees it
The player is inside the house and sees the grounds through its glass walls: ground-floor
eye height 1.65 m, upper floor 6.25 m, at distances from 5 m (the terrace) to 60 m (the
hedge). Massing, silhouette, colour, composition and how it frames the view from the
windows matter most; things within ~10 m of the house are seen in detail. It must read as
a real, expensive, designed landscape, not props dropped on grass.

## What you create
- Assets: `blender/assets/<prefix>_<thing>.py`, one per piece (prefix in your brief), same
  structure as every asset (`NAME`, `P`, `build(**overrides)` returning `(root, parts)`).
- Your zone module: `blender/levels/outdoor/<zone>.py` with
      PLACEMENTS = [("<asset>", (x, y), rotation_deg), ("<asset>", (x, y, z), rotation_deg), ...]
  in zone-local metres: (0, 0) = the centre of your zone's rect (`plan.GROUNDS["zones"]`),
  +x east, +y north, z = 0 the lawn surface; rotation 0 = the asset's front faces -y
  (south), 180 faces north, 90 east, -90 west. An asset may be placed many times.
- Edit nothing else: not `plan.py`, `grounds.py`, `lib/`, `viewer/`, other zones or other
  agents' assets, `specs.md`, `CLAUDE.md`. If the zone rect or something shared needs to
  change, say so in your final summary.

## The site
- Plan coordinates (metres): the house block is x -26..26, y -20..20, its floor 0.08 m
  above the lawn. The stone terrace rings it out to x ±31 / y ±25 (6 cm above the lawn).
  The perimeter hedge (2.8 m tall, 1.4 m thick) runs at x ±70, y ±62, with a gap for the
  drive at x 14..25.5 on the south side. North = the back of the house (pool side), south
  = the front (entry glass wall x -6..6, garage door x 15.5..24).
- Big windows: north - dining x -24..-12, kitchen x -8..6 (ground); primary bedroom
  x -24..-12, office x 1..12.5, gym x 15..24.5 (upper). West - great room y -8..8 (8.4 m
  tall glass), library y -19..-11.5 (upper). South - entry x -6..6 (8.4 m tall glass).
  East - mudroom y 3..7.5 (ground), guest room y 1.5..9 (upper). Compose your zone for
  the views from the windows that face it.
- The lawn can't be cut: anything "sunken" (a pool) is built as a raised deck with the
  water plane just below its coping. Stay inside your rect (other zones border it); the
  planting agent owns trees along the hedge and between zones.

## Materials: `blender/lib/outdoor.py` only (this overrides build_asset.md)
Everything outdoors is merged and its lighting baked into vertex colours, then drawn
unlit. So:
- Untextured materials are free: make as many flat colours as you need with
  `outdoor.flat("M_Out_<What>", colour)` or the shared ones (`dark_metal`, `bronze`,
  `render_white`, `concrete`, `bark`, `cushion`, `soil`, `lamp`). Choose colours with
  care, in linear RGB (real albedos: limestone ~0.5, white render ~0.7, foliage 0.03-0.1,
  dark metal ~0.03); colour is what reads at a distance.
- Textured materials: only `outdoor.stone()`, `teak()`, `foliage()`, `grass()`, `gravel()`
  (each costs a draw call, already paid for). No new textures, no normal maps.
- Water: only `outdoor.water()`, on flat upward-facing planes. Glass: only `outdoor.glass()`.
- Roughness and metalness don't show (lighting is baked diffuse).

## Geometry for baked lighting
Lighting is stored per vertex, so:
- Any surface larger than ~1.5 m that gets shadows (decks, paths, court surfaces, walls,
  roofs) must be cut into cells of 1.5 m or less (a grid, or `bmesh.ops.subdivide_edges`);
  otherwise a shadow across it can't be shown. Small props need nothing special.
- No long sliver triangles; no faces hidden inside other geometry (they waste the budget).
- Textured parts need UVs at world scale: `common.box_uv(ob, tile=...)` (stone 2.0,
  teak 0.5, foliage 1.5, grass 3.0, gravel 2.0).

## Budget
Your zone's triangle budget is in `plan.GROUNDS["zones"]` (printed by the zone preview:
`ZONE <zone>: N triangles (budget B)`). Stay under it. Assets typically 200-3,000 triangles;
spend triangles where they're seen (silhouettes, near the house), not on hidden detail.
Trees and shrubs come from the planting agent's assets (`plant_tree_round`,
`plant_tree_olive`, `plant_tree_cypress`, `plant_tree_multistem`, `plant_tree_fruit`,
`plant_shrub_round`, `plant_shrub_box`, `plant_shrub_grass`, `plant_shrub_lavender`); they
count against your budget when you place them. They may appear while you work (the
preview prints SKIP until they exist); place them anyway.

## Build and check
Each asset (no export needed; the level merges them):

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        --python blender/tools/build_asset.py -- <asset> --no-export

Your zone (about 40 s; never pass anything that writes the shared level):

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        --python blender/tools/build_level.py -- --no-export --no-save --zone <zone>

and look at `build/previews/zone_<zone>.png`: top-left an overview from above, top-right
the view from the house's nearest upper-floor window, bottom two eye-level views from
your rect's corners (EEVEE, the level's sun). Judge it as a landscape architect and art
director: scale against the house, proportions, believable construction (things sit on
the ground, nothing floats or intersects), composition from the window, colour harmony
with the house (white render, pale limestone, dark metal, teak). Iterate; usually 4-8
rounds.

## When done
Summarise: assets made (size, triangles), what you placed where, total triangles against
the budget, and anything you couldn't do or would change in the shared setup.
Do not commit, do not bake, do not run anything without `--no-export --no-save`.
