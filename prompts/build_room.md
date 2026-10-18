# Dressing rooms of the mansion (instructions for a sub-agent)

You are furnishing one or more rooms of a modern tech billionaire's mansion for a
three.js game. The architecture already exists (walls, floors, ceilings, windows,
doors, stairs are generated from `blender/levels/plan.py`); you supply the furniture
and fittings, the room's lights and its finishes. Read `CLAUDE.md` first, then
`prompts/build_asset.md` (the rules for building each asset still apply), then your
room brief in the `## Rooms` section of `specs.md`.

## What you create
- Assets: `blender/assets/<prefix>_<thing>.py`, one per piece, where `<prefix>` is
  given in your brief (e.g. `kitchen_island.py`). 3-7 assets per room is typical. You
  may also place existing assets (`ls blender/assets/`) if they fit your room's palette.
- Room modules: `blender/levels/rooms/<room>.py` for each room in your brief, following
  the interface at the top of `blender/levels/mansion.py` (FINISHES, PLACEMENTS, LIGHTS,
  optional PROBE). See `rooms/office.py` and `rooms/primary_bedroom.py` as examples.
- Edit nothing else: not plan.py, mansion.py, lib/, viewer/, other rooms or assets,
  specs.md, CLAUDE.md. If the architecture itself needs a change (a window moved, an
  opening widened), say so in your final summary instead of changing it.

## Know your room
    python3 blender/levels/room_info.py <room>
prints the interior size, ceiling height and every door, opening, window and
balustrade on its walls in room-local coordinates ((0, 0) = the interior centre, +x
east, +y north, z = 0 the room's floor). Lay out around them:
- keep 1.2 m clear in front of every door and opening, and walking routes at least
  1.2 m wide between them (the player is a 0.5 m wide box; furniture is solid);
- furniture against a wall goes inside the interior limits (the walls are at the limits
  room_info prints); assets face -Y at rotation 0, so rotation 180 faces north, 90 faces
  east, -90 faces west;
- these are big rooms (often 15-20 m long): furnish them as a high-end interior designer
  would, in zones (e.g. a seating group, a dining group), not as a few pieces lost in a hall.

## Build and check
Each asset, as in build_asset.md:

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        --python blender/tools/build_asset.py -- <asset>

Then the dressed room (about 40 s; never pass anything that writes the shared level):

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        --python blender/tools/build_level.py -- --no-export --no-save --only-room <room> --room <room>

and look at `build/previews/room_<room>.png` (four eye-height views from the room's
corners, lit by your LIGHTS with EEVEE). Judge it as an art director: does the room
read as a believable, expensive, lived-in space? Is anything floating, intersecting a
wall, blocking a door, too small for the room, or repetitive? Iterate.

## Lights
- `strip` lights are recessed ceiling lines (emissive + an area light in the bake); use
  them for general light, 30-60 W per metre of strip area is a starting point for these
  4 m ceilings. `point` lights are for lamps and pendants (put an emissive shade/bulb in
  the asset and a point light at it). Keep it to about 6 lights per room.
- Lighting is baked later; your EEVEE preview is an approximation. Aim for a balanced,
  warm interior, not a dark one.

## Budget (per room)
- Under ~80k triangles for everything you place in a large room (~30k small rooms),
  under 15k per asset (20k for a hero piece).
- Reuse `blender/lib/materials.py` and existing materials by name; at most ~3 new
  1024 textures per room, uniquely named `T_<Prefix>_<Map>`.

## When done
Summarise per room: the assets you made (size, triangles), what you placed and where,
lights, finishes, anything you couldn't do or architecture changes you'd recommend.
Leave each asset's `.gltf` exported (the default build_asset run does this).
