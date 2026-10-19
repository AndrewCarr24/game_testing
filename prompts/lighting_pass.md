# Interior lighting design pass (instructions for a sub-agent)

> **One Blender command at a time.** Several agents share this machine; never run Blender builds in parallel (no loops of rooms with `&`, no batches). The build tools queue themselves (at most 2 house builds and 4 asset builds machine-wide); `SLOT ... waiting` means wait.

Read `CLAUDE.md` first (especially "Baked lighting"), then `prompts/build_asset.md` (the asset
rules apply to any fixture you make) and `prompts/detail_pass.md` (the quality bar).

## The brief
The user: "the entire house has these line lights on the ceiling. keep those in a couple places
where appropriate, but do not over use them. add some more creative forms of lighting."

Today almost every room is lit by 2-5 glowing ceiling slots (`kind="strip"` in its module's
`LIGHTS`) plus a few point lights at its lamps. Redesign each of your rooms' lighting the way a
lighting designer would light a high-end modern house (think archviz of a Bel Air or Aspen
house: layered light, pools and washes, light coming from fixtures you can see):
- Decorative fixtures that suit the room: sculptural pendants over islands and tables, a
  chandelier in a double-height space, wall sconces flanking a mirror, a bed or a doorway,
  table and floor lamps by seating, a reading light by a chair.
- Architectural light that's hidden: a cove or valance wash up a wall or across a ceiling,
  backlit shelving or a backlit headboard, under-cabinet light on a worktop, a toe-kick glow
  under a vanity, a lit niche.
- Accent light: picture lights or tight downlights on art, grazers on a stone or textured wall.
- Ceiling strips stay only where they're the right answer (working rooms): the house keeps them
  in a few places at most (the garage, the gym, the scullery: and only if you judge so). Other
  rooms lose them.
Each room should have a clear idea (what's the brightest thing, where your eye goes) and enough
light to play in: no room darker overall than today (the user already finds the library too dark),
and no room flat. Light colour: warm white (2700-3000 K, about (1.0, 0.8, 0.6)) for living spaces;
a little cooler in working rooms is fine.

## Tools
Light kinds (documented at the top of `blender/levels/mansion.py`; all room-local metres, (0, 0)
= interior centre, z = floor):
- `strip` (glowing ceiling slot + area light), `point` (a bulb, inside a fixture prop),
- `spot` (pos, aim, power, angle, blend: downlights, picture lights, grazers, reading lights),
- `area` (pos, size, aim, power: a hidden soft source with no glowing geometry: coves, backlit
  panels, under-cabinet; put it where the fixture/trim that motivates it is).
Every light is baked (Cycles) into the room's lightmap and light probe; none is real-time in the
engine, so their number costs nothing at runtime. What costs is fixture geometry and materials.

Fixtures are props: the existing ones are `blender/assets/*lamp*`, `*pendant*`, `*sconce*`,
`*chandelier*` (read them, reuse and re-place them across rooms where they fit). You may make
new fixture assets (`blender/assets/light_<thing>.py`): glowing parts use `materials.emissive`
(`blender/lib/materials.py`); reuse the existing metals, glass and fabrics. A hidden cove needs a
visible reason (a slot, a ledge, a valance): model it as a slim prop (e.g. a `light_cove_valance`
asset placed along a wall at the ceiling) with an `area` light in it aimed at the wall/ceiling.
Pendants hang from the ceiling: give them a cord/stem to the ceiling height of their room
(`python3 blender/levels/room_info.py <room>` prints each room's interior, height, doors and windows).
Put every fixture's `point` light inside its shade/bulb position.

## Cost (the game ships on the web; viewer/tools/budgets.json is a ceiling)
- Per room: at most 2 new materials (batching merges each room's static props into one draw call
  per material, so a new material costs a draw call in each room it's in; reusing materials costs
  nothing). Fixture triangles: a pendant 300-1,500, a sconce 200-800, a lamp up to ~2,000.
  Your group's added triangles must stay under 25,000 in total; report it.
- No new textures.

## Rules
- You own the `LIGHTS` (and, where needed, `PROBE`) of your rooms' modules, the lighting fixture
  entries in their `PLACEMENTS` (add/move/remove lamps, pendants, sconces, valances), and the new
  `light_*` assets you make. Other agents are editing the same room files at the same time (one
  is replacing the pictures in `PLACEMENTS`; another owns `courtyard.py`): make small, targeted
  Edits, never rewrite a whole room file, never touch picture entries, re-read a file when an
  Edit fails because it changed. Don't edit existing fixture assets other rooms use in a way that
  changes their size or origin (copy into a new `light_*` asset instead), and don't edit lib/,
  viewer/, mansion.py, plan.py, house.py or living_fireplace.py.
- Fixtures must not block doors, windows, walkways or the player's head (pendants over tables
  and islands are fine: the player can't walk there; elsewhere keep the bottom above 2.1 m).
- Don't export, save or bake the level; don't commit.

## Check loop
Per room (about 40 s; EEVEE with the room's lights, the closest preview we have to the bake):

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
        --python blender/tools/build_level.py -- --no-export --no-save --only-room <room> --room <room>

and look at `build/previews/room_<room>.png`. Render each room once before you change anything
and keep that image (copy it to `build/previews/before_<room>.png`) to compare brightness and
mood. Fixture assets: `build_asset.py -- <asset> --no-export`, `build/previews/<asset>.png`.
EEVEE differs from the final Cycles bake (softer bounce, more contrast); aim a bit brighter than
looks right there rather than darker. The orchestrator runs the real bake afterwards.

## When done
Summarise per room: the lighting idea, fixtures added/moved/removed, LIGHTS before -> after (counts
by kind), triangles added, materials added; which rooms keep strips and why; anything you'd change
in the shared setup.
