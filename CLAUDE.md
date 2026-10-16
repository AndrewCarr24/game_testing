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
- Viewer: `viewer/?level=office` (click to walk, WASD; `&pos=x,y,z&look=x,y,z` sets the view).
- Variants come from overrides: `desk_chair.py` is `lounge_chair.build()` with different parameters.
- Screenshots / tests of the viewer: `viewer/tools/shot.mjs <url> <out.png>` and `walk.mjs` (Playwright with the installed Chrome; `npm i playwright-core` in a scratch dir). Plain headless Chrome `--screenshot` does not wait for multi-file levels to load.
