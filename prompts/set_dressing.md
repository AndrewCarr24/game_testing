# Set dressing pass (instructions for a sub-agent)

> **One Blender command at a time.** Several agents share this machine; never run Blender builds in parallel (no loops of rooms with `&`, no batches). The build tools queue themselves (at most 2 house builds and 4 asset builds machine-wide); `SLOT ... waiting` means wait.

Read `CLAUDE.md` first, then `prompts/build_asset.md` (asset rules) and `prompts/detail_pass.md`
(the quality bar).

## The brief
The user finds the house "looks a bit cheap, like a late 90s computer game"; the reference is an
architectural-visualisation render of a lived-in luxury house (OpenAI's Astra archviz article:
rooms that look photographed for an interiors magazine). The architecture, furniture and lighting
are in place; what's missing is the life: rooms are big and their surfaces bare. Dress your rooms
the way a stylist dresses a house for a shoot:
- On surfaces: stacks of art books (varied sizes, a few lying flat with an object on top), a tray
  with a carafe and glasses, a bowl of fruit or lemons, ceramics and vases in groups of three
  (varied heights), candles, a small sculpture, a box, a clock, a bowl of keys by the door.
- Soft things: throws over the arm of a sofa or the foot of a bed, scatter cushions where they are
  missing, a folded towel stack in baths, a robe on a hook.
- Life: plants (floor plants in corners, small potted plants on shelves and counters), a coffee
  cup and an open book on a side table, reading glasses, a magazine fanned on a coffee table, a
  cutting board and a bowl on the kitchen counter, a fruit bowl, a laptop and a notebook on a desk,
  shoes by a bed, a towel over the tub edge.
- Shelves: fill bookcases and open shelving with rhythm (books upright and stacked, objects,
  breathing space), not wall-to-wall books everywhere.
- Restraint: luxury is curated, not cluttered. Each surface gets a composed vignette (odd numbers,
  varied heights, a focal object), floors stay clear for walking.

## What you make
- Small decor assets: `blender/assets/<prefix>_<thing>.py` (prefix in your task), same structure as
  every asset. Make a reusable kit (book stacks with a seed parameter, vase families, bowls, trays,
  throws, cushions, plants, cups) and vignette assets that group several objects (e.g. a
  `<prefix>_vignette_console` = books + bowl + vase), so a room module places one asset per
  vignette. Variants go through small wrapper modules (e.g. `<prefix>_books_b.py` calling the kit
  with another seed), like `art_*.py` wrap `picture_frame.py`. Reuse other agents' finished decor
  assets when they fit (`ls blender/assets`), but only edit your own files.
- Placements: add decor entries to your rooms' `PLACEMENTS` (room-local metres, z = height of the
  surface they sit on; `python3 blender/levels/room_info.py <room>` and the furniture placements in
  the room module tell you where surfaces are; read the furniture assets' `P` for their sizes).

## Cost (the game ships on the web; viewer/tools/budgets.json is a ceiling)
- Triangles: an object 50-800 (a vase is a 12-16-sided lathe, a book is a bevelled box), a
  vignette under 3,000, a plant under 2,500. Per room add at most ~10,000 (great room, kitchen,
  library: 15,000). Report what you added per room.
- Materials: reuse existing ones (`blender/lib/materials.py`; ceramics, metals, woods, fabrics,
  glass, the existing book/leaf materials in the library and plant assets). Every distinct material
  costs one draw call per room it appears in: at most 3 new materials per room, and share them
  across your rooms. No new textures (flat colours with roughness are fine; ceramics and glazes
  look good flat).
- Colliders: small things must not become colliders (thousands of tiny boxes slow the physics):
  name every part of an object smaller than ~0.4 m with `NoCollide` in its name (see
  `COLLIDER_SKIP` in `blender/lib/common.py`). Floor plants and big baskets may collide.

## Rules
- You own your rooms' decor `PLACEMENTS` entries and your `<prefix>_*` assets. Don't move or edit
  existing furniture, art, light fixtures, `LIGHTS`, `FINISHES`; don't edit lib/, viewer/,
  mansion.py, plan.py or other agents' files. Other agents may edit other rooms' files at the
  same time: small targeted Edits, re-read when an Edit fails.
- Keep interactables working: nothing on or in front of drawers and doors (the office desk's
  drawer holds the keycard), nothing blocking doorways, walkways or the stair.
- Things must sit on their surface (no floating, no intersecting), at believable scale.
- Don't export, save or bake the level; don't commit.

## Check loop
    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        --python blender/tools/build_level.py -- --no-export --no-save --only-room <room> --room <room>

(about 40 s; `build/previews/room_<room>.png`), plus `build_asset.py -- <asset> --no-export` for
each asset (`build/previews/<asset>.png`). Also render your own eye-level close-ups of the main
vignettes from 1-2 m (a scratch script in your scratchpad), since the player sees them that close.
Judge as a stylist and art director: would the room pass in a magazine shoot? Iterate.

## When done
Summarise per room: the vignettes added, triangles added, materials added; the kit you built;
anything you couldn't do.
