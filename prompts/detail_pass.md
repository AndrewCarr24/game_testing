# Furniture detail pass (instructions for a sub-agent)


> **One Blender command at a time.** Several agents share this machine; never run Blender builds in parallel (no loops of rooms with `&`, no batches). The build tools queue themselves (at most 2 house builds and 4 asset builds machine-wide); `SLOT ... waiting` means wait.
The house's furniture already exists (`blender/assets/*.py`, placed by the room modules).
Your job is to make a group of those assets look like real, high-end furniture in an
architectural visualisation, at the same cost. Read `CLAUDE.md` first, then
`prompts/build_asset.md` (the asset rules still apply), then this file.

## The bar
Think of a premium archviz render of a modern house: furniture has real construction.
- Upholstery: separate cushions with welts/piping and seams, a slight crown, soft gaps
  between cushions, a visible frame/plinth below; cushions sit into each other.
- Case goods: drawer and door fronts with 2-4 mm reveals between them, real pulls or
  finger grooves, a recessed plinth or legs, back panels, shelves with depth.
- Tables and chairs: edge profiles (eased or chamfered edges), aprons, legs joined to tops
  believably, tapered or turned legs, feet/glides; chair seats with thickness.
- Beds: upholstered headboard panels, mattress with rounded edges, duvet with a fold-over and
  slight drape, pillows of varied sizes, a throw.
- Bath and kitchen: hollow basins and sinks (an actual bowl with a drain), taps with a spout
  and handle, cabinet fronts with reveals, appliance fronts (oven door with a window,
  cooktop with burners), worktop thickness and overhang.
- Lamps: shade with thickness (a rim), harp/fitting, cord where seen, base detail.
- Every visible hard edge gets a small bevel (2-10 mm), which catches light; smooth shading
  only on curved surfaces, with hard edges kept sharp (correct normals: no pinched or
  faceted-looking flats; if a flat face looks shaded wrong, fix its normals).

## Rules
- Keep each asset's file name, `NAME`, `P` keys, origin, front (-Y), overall size (within
  2 cm), and every interactable empty and its name/`interact` property exactly (e.g. the
  desk's `Desk_Drawer`, which the keycard is attached to; doors). Placements in the room
  modules must keep working unchanged.
- Materials and textures: reuse the existing ones (`blender/lib/materials.py`, the asset's
  own); no new textures. Shading of creases comes from the baked AO (automatic), so model
  the geometry that creates it.
- Budget: your group's total placed triangles (sum over placements; the build_asset REPORT
  gives each asset's count) may rise by at most 10%. Pay for new detail by removing what
  isn't seen: faces against walls and floors, undersides of things on the floor, insides
  of closed boxes, and over-tessellated curves (a vase doesn't need 2,900 triangles; a pot
  doesn't need 2,000). Report before/after per asset.
- Edit only your group's asset files (listed in your task). Not room modules, lib/,
  viewer/, other assets. Do not export, save or bake the level; do not commit.

## Check loop
Per asset (no export):

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        --python blender/tools/build_asset.py -- <asset> --no-export

and look at `build/previews/<asset>.png` as an art director would, against the bar above.
Then see the pieces in their room (about 40 s):

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        --python blender/tools/build_level.py -- --no-export --no-save --only-room <room> --room <room>

(`build/previews/room_<room>.png`). Iterate; hero pieces (sofas, beds, the kitchen island,
the dining table, the desk, vanities) deserve the most rounds.

## When done
Summarise per asset: what you added, triangles before -> after, the group total before ->
after, anything you couldn't do.
