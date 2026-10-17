# game_testing

Modern tech-billionaire mansion game. Current phase: building game-ready assets in Blender (driven over the `blender` MCP server, see `.mcp.json`).

## Asset pipeline
- Every asset is a generator script: `blender/assets/<name>.py`, parameters in a `P` dict at the top, `build(**overrides)` rebuilds its collection from scratch. Run in Blender with
  `ASSET = "<name>"; exec(open("/Users/andrewcarr/Documents/projects/game_testing/blender/run.py").read())`.
  Change the script, not the .blend, so work stays reproducible. The working Blender file is `blender/levels/office.blend`.
- Shared helpers: `blender/lib/common.py` (cushions, bent tubes, bevels, box UVs, glTF export), `blender/lib/textures.py` (numpy-generated tileable maps → `assets/textures/`).
- Conventions: metres, origin at floor centre, front faces -Y, root empty named after the asset, parts named `<Asset>_<Part>`. Principled BSDF + image textures only (what glTF carries). UV scale = world scale (wood 0.5 m tile, leather 0.2 m tile).
- Export: `common.export_glb(root, "assets/models/<name>.glb")`. Check in engine: `python3 -m http.server 8765` from the project root, open `http://localhost:8765/viewer/?asset=<name>` (three.js 0.160, same stack as ../video_game).

## Levels
- `blender/levels/<level>.py` builds the shell (walls/floor/ceiling/glass), builds each prop from its asset script, places them, and exports `assets/models/<level>_shell.glb`, one `.glb` per prop, and `assets/levels/<level>.json` (props + transforms, AABB colliders, lights, spawn) in glTF Y-up coords. Blender→glTF is `(x, y, z) -> (x, z, -y)`; a Z rotation becomes the same angle about Y.
- Run: `import runpy; runpy.run_path(".../blender/levels/office.py", run_name="__main__")`. Working file: `blender/levels/office.blend`.
- Lights are data in the JSON (Blender lights don't transfer); the hemisphere light stands in for bounce until lightmaps are baked.
- Viewer: `viewer/?level=office` (click to play; WASD, Shift run, Space jump, C crouch, E interact; `&pos=x,y,z&look=x,y,z` sets the eye position/view).
- Collision: each prop gets one box per mesh part (`common.part_colliders`, skipping trim and moving parts) so seats and desktops can be stood on. Player: `viewer/player.js` (box character, gravity, ~1 m jump, 0.3 m auto step-up). Test: `viewer/tools/movement.mjs`.
- Crouch is C, not Cmd/Ctrl: Cmd+W / Ctrl+W close the tab and can't be blocked, and macOS drops other keys' keyup while Cmd is held.
- Variants come from overrides: `desk_chair.py` is `lounge_chair.build()` with different parameters.
- Screenshots / tests of the viewer: `viewer/tools/shot.mjs <url> <out.png>` and `walk.mjs` (Playwright with the installed Chrome; `npm i playwright-core` in a scratch dir). Plain headless Chrome `--screenshot` does not wait for multi-file levels to load.

## Interactables
- A moving part is its own empty (pivot/origin where it rests) with an `interact` custom property, written to glTF extras (`export_extras=True`) → three.js `userData.interact`, so every placement of the asset gets the behaviour with no level changes. Types: `slide` (drawer: axis, distance), `rotate` (door: axis through the empty's origin, angle), `pickup` (keycard: item, name). Shared fields: duration, range (to the item's nearest edge), prompt/promptActive, side, `collide` (moving collider, solid only once settled), `indicator` (status-light node).
- State lives in the level, not the asset: `PLACEMENTS` options `lock` (item id the interactable needs) and `attach` (parent to another placement's node, e.g. the keycard inside `Desk_Drawer`). A pickup inside another interactable can only be taken while that one is open.
- Engine: `viewer/interactables.js` (`Interactables`, `Inventory`), HUD in index.html (inventory slots, toast messages). Tests: `viewer/tools/drawer.mjs`, `keycard_door.mjs`.
- The corridor behind the office door (`corridor` in office.py's `P`) is a placeholder until the next room exists.

## Baked lighting
- `blender/levels/bake.py` (headless: `Blender -b blender/levels/office.blend --python blender/levels/bake.py -- office 512`, ~1 min on the M4 GPU) bakes Cycles diffuse lighting for every shell mesh with a `Lightmap` UV layer into `assets/textures/T_Office_Lightmap.png`, renders a 360° room panorama (sun hidden) to `T_Office_Env.hdr`, and writes `assets/levels/office_bake.json`. Save the .blend first; re-bake whenever the level layout changes.
- The lightmap UV atlas is generated in `office.py` (`common.lightmap_uv`); sun direction/strength, sky, cove power and exposure live in office.py's `P` and feed both the bake and the engine.
- Engine (`viewer/baked.js`): lightmapped materials have real-time diffuse switched off (no double lighting), keep real-time specular. Props: real-time sun + the panorama as environment. `?bake=0` shows the old unbaked lighting for comparison.

## Web performance budget (it ships as an online three.js game)
- Measured office (2026-10-16): 2.4 MB download, 81 draw calls, 33k tris, 34 MB GPU textures; 612 fps on the M4 Pro, 28 fps at 720p with no GPU at all (SwiftShader). Keep new rooms in that range: < ~5 MB download per room, < ~200 draw calls, 1024² textures by default.
- Export with `common.export_gltf` (WebP textures in the shared `assets/models/textures/`), not `export_glb` (embeds a copy of every texture per file).
- Viewer: pixel ratio capped at 1.5, one 2048 shadow map redrawn only when something moves, identical textures shared on the GPU.
- Measure: `viewer/tools/perf.mjs <url>` (download, draw calls, texture MB) and `viewer/tools/fps.mjs <url> swiftshader 1280 720 1` (worst-case frame rate).

## Building assets in parallel
- `blender/tools/build_asset.py` builds one asset in its own headless Blender (`Blender -b --factory-startup --python blender/tools/build_asset.py -- <asset> [--no-export]`, ~2-7 s): report with budget WARNs, `.gltf` export, preview sheet at `build/previews/<asset>.png`. Safe to run several at once; never touches the open Blender window.
- Sub-agents get `prompts/build_asset.md` plus one entry from `specs.md` (status DRAFT → READY once the user has answered its open questions). They create only `blender/assets/<asset>.py`; placing assets in a level, engine features and commits stay with the orchestrator.
