# Building one asset (instructions for a sub-agent)


> **One Blender command at a time.** Several agents share this machine; never run Blender builds in parallel (no loops of rooms with `&`, no batches). The build tools queue themselves (at most 2 house builds and 4 asset builds machine-wide); `SLOT ... waiting` means wait.
You are building ONE game asset for a three.js game set in a modern tech-billionaire's
mansion. Read `CLAUDE.md` first for the project conventions. Your asset's spec is the
entry in `specs.md` you were given. Build it to final, game-ready quality; it will be
placed in the game as-is.

## Rules
- Create exactly one file: `blender/assets/<asset>.py`. Do not edit anything in
  `blender/lib/`, `blender/levels/`, `viewer/`, other assets, `CLAUDE.md` or `specs.md`.
  If you need a helper or texture generator that isn't in `blender/lib/`, write it inside
  your asset file.
- Follow the existing asset scripts as patterns: `lounge_chair.py` (cushions, bent tube,
  textures), `desk.py` (an interactable drawer), `keycard.py` (a pickup), `door.py`.
  Same structure: `NAME`, a parameter dict `P`, `build(**overrides)` that rebuilds its
  collection from scratch and returns `(root, parts)`.
- Materials: use `blender/lib/materials.py` (`walnut()`, `steel()`, `black_metal()`,
  `smoked_oak()`, `bronze()`, `fabric(name, colour)`, `glass(...)`, `emissive(...)`) whenever
  the spec names one, so every asset shares the same material and texture. Only create a
  new material when nothing there fits.
- Conventions: metres; origin at the floor centre (or the centre of the underside for
  small items); the front faces -Y; parts named `<Asset>_<Part>`; Principled BSDF plus
  image textures only. Reuse existing materials by name where they fit (`M_Walnut`,
  `M_Steel_Polished`, `M_Aluminium_Black`, `M_Leather_Cognac`, ...), so the game shares them.
- New textures: generate them with numpy (see `blender/lib/textures.py` for the approach),
  1024x1024 at most, saved with a name unique to your asset (`T_<Asset>_<Map>`), and only
  regenerate when the file is missing, because other agents run at the same time.
- Budget: under 15,000 triangles unless the spec says otherwise; 1024 textures; every
  textured part needs UVs (`common.box_uv`).
- Interactive behaviour (pickup, drawer, door...) goes in an `interact` custom property
  on an empty, exactly like the existing assets. Do not write any engine code.
- Do not commit, do not open or drive the Blender window (no MCP), do not install anything.

## Build and check loop
Build headless (its own Blender process, safe to run alongside other agents):

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        --python blender/tools/build_asset.py -- <asset>

To preview a parameter variant without exporting it:

    ... build_asset.py -- <asset> --no-export --set variant=<name>
    (preview: build/previews/<asset>_<name>.png)

Then:
1. Read the REPORT lines: size against the spec, `bottom z = 0`, triangles, textures.
   Fix every `WARN` line.
2. Look at `build/previews/<asset>.png` (front, three-quarter, side, top). Compare it with
   the spec as a demanding art director would: proportions, silhouette, parts floating or
   intersecting, materials that read as plastic, flat or repetitive textures, missing
   detail that a real object of this kind would have.
3. Change the script and rebuild. Repeat until it holds up; usually 3-6 rounds.

If Blender raises an error or a `bpy` call doesn't behave as you remember, read the
traceback and adjust. Blender 5.0's API differs from older versions in places; don't guess.

## When done
Finish with a short summary: final size, triangle count, materials and textures (new or
reused), the interact definition if any, and anything in the spec you could not meet
and why. Leave the final `.gltf` exported (the default build does this).
