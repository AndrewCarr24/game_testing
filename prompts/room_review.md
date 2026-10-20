# Room review (instructions for a sub-agent)

You are reviewing ONE room of a three.js first-person game set in a modern tech-billionaire's
mansion (horror direction: a 7 m creature, the Grimble, breaks into the main spaces; the side
rooms are safe because their doors are too narrow for it). Read `CLAUDE.md` first (what the
house is, how it's built, the conventions), then this file.

## Your job
Go through your room as a player and an art director would and find what's wrong:
- **Bugs:** things floating or sunk into the floor, intersecting each other or the walls,
  z-fighting/flicker, holes, wrong-coloured or black/white faces, missing textures, stretched
  or tiled-looking textures, props blocking doors or walkways, things you can't reach or walk
  around, light switches/blinds/pickups that don't work, colliders that are too big or missing
  (walking through furniture), things that look broken up close.
- **Things that look bad:** fake-looking materials, scale errors (a 3 m chair, a tiny door),
  bad lighting (too dark, blown out, flat, light from nowhere, a lamp that isn't lit), clutter
  or emptiness, repetition, cheap-looking pieces, poor composition from the doorway.
- **Poor design choices:** furniture layouts a real interior designer wouldn't do (sofas with
  their backs to the view, a bed under a window wall, art hung too high, a TV in a bad spot,
  circulation blocked), things that don't belong in this kind of house or this room, missing
  things a real room of this kind has, and gameplay issues (hiding spots, sight lines, places
  the player gets stuck).

## How
- `python3 blender/levels/room_info.py <room>` prints the room's interior, doors and windows
  (room-local metres). Your room's module is `blender/levels/rooms/<room>.py` (galleries share
  `galleries.py`); the assets it places are `blender/assets/<asset>.py`. Rooms in
  `assets/levels/mansion.json` give the room's rect in world glTF coordinates
  ([x0, z0, x1, z1]; y up; floor height `floor`).
- Screenshots in the real engine: the local server http://localhost:8765 is running.
  `node viewer/tools/review_room.mjs <room>` (from the project root) writes 10 standard views to
  `build/review/<room>/` (4 corners, 4 walls from the centre, floor, ceiling). Add your own views
  with `node viewer/tools/review_room.mjs <room> build/review/<room>/extra "px,py,pz,lx,ly,lz" ...`
  (camera position and look-at point in world glTF coordinates; eye height = floor + 1.65).
  Take close-ups of anything suspicious (1-2 m away). The tool shares 3 browser slots
  machine-wide with the other reviewers: if it waits, that's why.
- `node viewer/tools/grid.mjs out.png 3 a.png b.png ...` makes a contact sheet if useful.
- The lighting is baked (Cycles) as of the last bake; the newest props (light switches, blinds,
  breaker panel, tablet dock, `ix_*` assets) haven't been baked into the lightmaps yet: a slightly
  flat look on those is known, not a finding. Lights switched off only darken fixtures until a
  "lights off" bake exists: also known.
- Don't edit any file, don't run Blender, don't commit. This is a review only.

## Report (your final message)
A ranked list, most important first, each item:
- **[bug | looks bad | design]** one-line title
- where (what, and a view file path that shows it)
- why it matters and the fix you recommend (concrete: which asset/placement/value, what to do)
Then a one-paragraph overall verdict on the room. Keep it to the ~10-15 findings that matter;
skip nitpicks. Be specific and honest: if the room is good, say so.
