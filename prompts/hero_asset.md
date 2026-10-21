# Hero asset pass (instructions for a sub-agent)

> **One Blender command at a time.** About a dozen agents share this machine; never run Blender
> builds in parallel (no `&`, no loops of builds). The build tools queue themselves (at most 4
> asset builds machine-wide); `SLOT ... waiting` means wait. The browser tools also queue (3 slots).

Read `CLAUDE.md`, then `prompts/build_asset.md` (asset rules) and `prompts/detail_pass.md` (the
quality bar), then this file.

## The bar
The user looked at one piece, the mudroom locker wall, and after a dedicated pass it "looks
fantastic": coats are cloth-simulated and hang with weight, shoes are modelled, scanned Poly Haven
boots and a basket were decimated and brought in, cushions are upholstered with welts. They want
the same level of attention on your piece, which today reads fake: overly geometric, boxy,
low-poly, flat. Study what was done there (`blender/assets/garage_lockers.py`, `mud_common.py`:
cloth simulation baked headless and cached, procedural details on smooth bases, Poly Haven model
import + decimation) and use the same kind of craft. Make it look like a real, expensive object
photographed for an interiors magazine, seen from 0.5-3 m.

Use whatever technique gives the best result: proper profiles and lathes with enough segments,
bevels and eased edges everywhere, real construction details (seams, welts, joints, hardware),
subdivision and smoothing on organic forms, cloth simulation for anything soft (`mud_common.py`
shows a headless, cached cloth sim), procedural displacement or sculpted noise, leaf cards with
real leaf shapes for plants, and Poly Haven models or textures where they fit
(`blender/tools/polyhaven_models.py fetch_model(id)`; the Poly Haven API lists models by
category: https://api.polyhaven.com/assets?t=models). Decimate imported models to your budget and
bring their textures into the asset's materials (base colour + normal, named T_<Asset>_*).

## Rules
- Keep the asset's file name, `NAME`, `P` keys, origin, front (-Y), overall size (within a few
  cm), and every interactable empty and its `interact`/`react` properties exactly, so every
  placement keeps working. You may add `P` keys.
- Only edit your asset's files (and helper modules you create, prefixed with your asset's name).
  Not room modules, lib/, viewer/, other assets. Don't save or bake the level; don't commit.
- Budget: up to about 2.5x the current triangles for a single hero piece (more is OK for a piece
  placed once, if you report it); for pieces placed many times, keep the total sensible (your task
  says how many placements). Textures: at most 2 new texture sets (1024 max; the build shrinks
  prop textures to 512); reuse existing materials (blender/lib/materials.py, the asset's own)
  wherever you can: each new material costs a draw call per room. Colliders: small soft or thin
  parts (leaves, fabric, fringe, cables) named `NoCollide` (common.COLLIDER_SKIP).

## Check loop
- `/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python blender/tools/build_asset.py -- <asset>`
  builds and EXPORTS your asset (`assets/models/<asset>.gltf`, which the game loads directly) and
  renders `build/previews/<asset>.png`. Also render your own close-ups (a scratch script in your
  scratchpad) from 0.5-2 m.
- In the real engine (local server at http://localhost:8765 is running):
  `node viewer/tools/prop_closeups.mjs <out-dir> <asset>` (from the project root) shoots the
  first placement of the asset from two angles in its room; it loads your exported .gltf.
  (Colliders and the room's lighting bake don't update until the orchestrator rebuilds the level;
  that's expected.)
- Judge as an art director against real reference (describe the reference you're matching).
  Iterate: expect many rounds; the user will look closely.

## When done
Report: what you built and how, triangles before -> after (per asset and x placements), textures
and materials added, Poly Haven assets used, before/after image paths (engine close-ups), and
anything the orchestrator must do.
