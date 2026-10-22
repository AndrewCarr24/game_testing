# Asset specs

One entry per asset a sub-agent can build on its own (see `prompts/build_asset.md`).
Engine features and level layout are not asset work; they're listed at the end for
the orchestrator.

Entry format:

```
## <asset_id>                     file name: blender/assets/<asset_id>.py
- Status: DRAFT | READY | BUILT | APPROVED
- Model: sonnet | opus            who builds it
- What: one line
- Size: w x d x h in metres (approximate is fine)
- Materials: reuse existing where possible; new ones described
- Details that sell it: the 3-5 things a real one has that make it believable
- Interact: none | pickup | ... (and its fields)
- Budget: triangles, textures
- Placement: where it goes (the orchestrator places it; the agent doesn't)
- Open questions: for the user, before Status becomes READY
```

---

## vase
- Status: APPROVED
- Model: sonnet
- What: a heavy, hand-blown-looking smoked-glass vase for the office coffee table; empty
- Size: about 0.13 diameter x 0.28 tall
- Shape: built by revolving a profile (bmesh spin or your own lathe): a thick solid glass
  base (~2 cm, visibly solid when seen through the walls), a body that swells to a
  rounded shoulder, a narrower neck and a slightly flared lip. Real wall thickness
  (~4-5 mm): outer surface, inner surface and a rounded top of the lip joining them.
  Shallow vertical flutes (12-16 ribs) around the body so light catches it.
- Materials: `materials.glass("M_Glass_Smoke", tint=(0.42, 0.40, 0.37), alpha=0.35,
  roughness=0.04)` for the walls; the solid base may use a second, slightly denser glass
  material (alpha ~0.55) so the thickness reads. Alpha-blended only (no transmission).
- Details that sell it: the wall thickness visible at the lip, the solid base, the flutes,
  smooth shading (no faceting on the curved profile: enough segments around, ~48).
- Interact: on the root empty:
  `{"type": "pickup", "item": "vase", "name": "Glass vase", "prompt": "Take vase",
    "range": 1.4, "throwable": true}`
  The engine handles throwing and shattering; don't model fracture pieces.
- Origin: centre of the underside, sitting on z = 0.
- Budget: under 3,000 triangles; no textures needed.
- Placement: on the office coffee table (the orchestrator places it).

## picture_frame
- Status: APPROVED
- Model: sonnet
- What: framed artworks for the hall: one script with a `variant` parameter that sets the
  size and the artwork, so the hall can hang several different pieces
- Frame: slim gallery frame in `materials.black_metal()`: 2 cm face, 4 cm deep, with a
  bright white mat (8-10 cm border) whose window has a small 45-degree bevel, and the
  artwork recessed behind it. A faint glass layer over the front
  (`materials.glass("M_Glass_Picture", alpha=0.06, roughness=0.02)`).
- Artwork: generated with numpy, 1024 px on the long side, one texture per variant named
  `T_Art_<Variant>`. A cohesive set that suits a modern collector's hallway, palette of warm
  neutrals, ink blue, cognac and ochre:
  - `colorfield_a` 0.9 x 1.2 (w x h): two or three soft-edged stacked colour fields with
    brush texture and slightly feathered edges (Rothko-like)
  - `colorfield_b` 1.2 x 0.8: a horizontal variant in different colours
  - `geometric_a` 0.8 x 0.8: hard-edged geometric composition (rectangles, one circle),
    flat paint with a faint canvas grain
  - `geometric_b` 0.6 x 0.8: a quieter geometric piece, mostly negative space
  - `linework_a` 0.9 x 1.2: a single continuous ink line drawing on cream paper
  The default variant (`build()` with no arguments) is `colorfield_a`. Put the variant
  table in a `VARIANTS` dict at the top of the script.
- Orientation: hangs on a wall. Origin at the centre of the frame's back, on the wall
  plane; the picture faces -Y, extends ±w/2 in X and ±h/2 in Z, and sits 1 cm off the wall
  (a hidden spacer behind it). Ignore the "not on the ground" report line for this asset.
- Interact: none.
- Budget: under 600 triangles per frame; one 1024 texture per variant.
- Check every variant's preview (`--no-export --set variant=<name>`), not just the default.
- Placement: hall walls (the orchestrator places them).

## Bedroom palette (shared by every bedroom asset)
Evening, private, warmer and darker than the office. Use these exactly (blender/lib/materials.py):
- wood: `materials.smoked_oak()`; metal: `materials.bronze()`
- ink upholstery: `materials.fabric("M_Fabric_Ink", (0.018, 0.024, 0.04), roughness=0.8)`
- oat linen: `materials.fabric("M_Fabric_Oat", (0.42, 0.37, 0.30))`
- stone throw / accents: `materials.fabric("M_Fabric_Stone", (0.16, 0.15, 0.135))`
- recessed plinths / shadow gaps: `materials.black_metal()`

## bed
- Status: APPROVED
- Model: sonnet
- What: a king platform bed, the hero piece of the bedroom
- Size: 1.95 wide x 2.15 long; headboard 1.15 tall and ~2.1 wide
- Build: smoked oak platform 0.30 tall on a recessed black plinth so it seems to float;
  mattress 0.25 thick (oat, soft rounded edges: `common.cushion_bmesh` + subdivision);
  a tailored duvet that overhangs the sides by ~0.12 with softly rounded edges, turned back
  at the head end so a second layer shows; two sleeping pillows (oat) and two smaller
  cushions (ink) leaning against the headboard; a folded throw (stone) across the foot.
  Headboard: ink upholstery in vertical channels (6-8 padded channels) on a smoked oak frame.
- Details that sell it: soft, slightly irregular bedding (not perfect boxes: vary crowns and
  rotate pillows a few degrees), seams/piping on pillows, the floating platform shadow gap.
- Orientation: origin at the floor centre; the foot of the bed faces -Y, headboard at +Y.
- Interact: none
- Budget: under 20,000 triangles (hero piece); fabric/wood textures come from the palette.

## nightstand
- Status: APPROVED
- Model: sonnet
- What: a floating-look nightstand with one drawer and an open shelf below
- Size: 0.55 wide x 0.42 deep x 0.55 tall
- Build: smoked oak case on a recessed black plinth; one drawer on top that opens (copy the
  desk drawer pattern in `desk.py`: an empty `<Asset>_Drawer` carrying
  `{"type": "slide", "axis": common.to_gltf((0, -1, 0)), "distance": 0.25, "duration": 0.4,
  "range": 1.4, "prompt": "Open drawer", "promptActive": "Close drawer"}`; note this drawer
  opens toward -Y, the front); a real drawer box inside; a slim recessed bronze pull; an open
  shelf below with a visible back panel.
- Orientation: origin at the floor centre; the front (drawer side) faces -Y.
- Budget: under 4,000 triangles.

## table_lamp
- Status: APPROVED
- Model: sonnet
- What: a bedside lamp that gives the room its warm glow
- Size: 0.62 tall; drum shade 0.36 diameter x 0.26 tall; base ~0.16 diameter
- Build: weighted round base (smoked oak or bronze), slim bronze stem, a drum shade in
  glowing linen (`materials.emissive("M_LampShade_Warm", (1.0, 0.78, 0.52), 1.5)`) with a
  thin bronze rim top and bottom, an open top and bottom so the inside of the shade reads,
  a small bright bulb shape inside.
- Orientation: origin at the centre of the underside.
- Interact: none (it's on; switching comes later)
- Budget: under 4,000 triangles.

## wardrobe
- Status: APPROVED
- Model: sonnet
- What: a tall two-door wardrobe in smoked oak
- Size: 1.8 wide x 0.62 deep x 2.4 tall
- Build: two full-height doors with 3 mm reveal gaps, vertical grain, full-height slim bronze
  bar pulls at the meeting edges, a recessed black plinth (5 cm), a top shadow gap; the sides
  and top a touch thicker than the doors so it reads as furniture, not a box.
- Orientation: origin at the floor centre; doors face -Y.
- Interact: none for now (static doors).
- Budget: under 4,000 triangles.

## bench
- Status: APPROVED
- Model: sonnet
- What: an upholstered bench for the foot of the bed
- Size: 1.45 wide x 0.42 deep x 0.46 tall
- Build: a boxed cushion top in ink upholstery with piping (see the lounge chair cushions),
  on a slim bronze flat-bar frame (two sled-style ends joined by a stretcher).
- Orientation: origin at the floor centre; front faces -Y.
- Budget: under 6,000 triangles.

## bedroom_rug
- Status: APPROVED
- Model: sonnet
- What: a large, soft wool rug under the bed
- Size: 3.2 x 2.6, 15 mm thick, small rounded corners
- Build: like `rug.py`, but oat/cream wool with a quiet tone-on-tone pattern (a soft inset
  border or broad low-contrast stripes) and visible pile texture: generate `T_BedroomRug_BaseColor`
  (and optionally a normal map) at 1024, tiled or mapped once across the rug.
- Orientation: origin at the floor centre.
- Budget: under 1,000 triangles.

---

## Orchestrator work (not sub-agent jobs)

### Arm feature (engine) — DONE
Decided: I opens the inventory, the up/down arrows choose, Enter arms; with an item armed,
Enter uses it and Delete (Backspace on a Mac) puts it away. The keycard only works armed
(locks and unlocks doors with a reader); the vase is thrown in an arc and shatters.
Original proposal, for reference:
- Number keys 1-9 (or the mouse wheel) choose an inventory slot; the armed slot is
  highlighted in the HUD and the item shows in the player's hand (bottom-right of view).
- Left click uses the armed item. E stays for the world (drawers, door handles, pickups).
- Keycard: armed + left click near a door with a reader toggles lock / unlock.
- Vase: armed + left click throws it in an arc where you're looking; it hits walls and
  furniture and lands on the floor.
Open questions:
1. Should an unarmed keycard still open the door (current behaviour), or is arming now
   required? (Proposed: arming required, so the mechanic matters.)
2. Can the player lock a door behind them, and does locking matter later (e.g. keeping
   someone out)?
3. Mouse wheel or number keys, or both?

### Hall (level) — DONE (10 m gallery hall, five artworks, door to the bedroom; more to come)
Replaces the corridor stub behind the office door.
Open questions:
1. Length and shape: straight, ~10 m, ~2 m wide? Ceiling height?
2. Which side is the bedroom door on: the far end (as you described)? Any other doors
   now, even locked ones for later rooms?
3. Windows, or interior only?

### Bedroom (level) — DONE (evening mood, west window, lamps baked)
Open questions:
1. Size (~6 x 5 m?) and does it have the same floor-to-ceiling glass as the office?
2. Is its door locked, and if so what opens it?

---

## Rooms (main house; see prompts/build_room.md)
Interior sizes and every door/window: `python3 blender/levels/room_info.py <room>`.
House palette: warm minimal modern. Walnut, smoked oak, bronze, polished steel, cognac
leather, ink blue, oat linen, white marble, limestone. Each room may lean its own way.

### great_room + den (prefix `living_`)
- great_room: 12.2 x 20.7 m, double height (8.4 m), a full-height west glass wall, two wide
  openings to the gallery (east), opening to dining (north), door to the den (south). The
  house's main living space: two or three seating groups (sofas, lounge chairs, coffee
  tables, rugs), a fireplace or media wall as a focal point, side tables, floor lamps, a
  large plant or sculpture. Limestone or oak floor; consider a feature wall.
- den: 12.2 x 9.2 m, no windows: a media room / snug. Deep sectional facing a screen wall,
  dimmer and cosier, darker finishes (e.g. green or ink fabric wall, smoked oak).

### kitchen + scullery (prefix `kitchen_`)
- kitchen: 17.7 x 9.2 m, glass north wall, openings to dining (west), gallery (south),
  scullery (east). A chef's kitchen: a long waterfall-marble island with stools, a wall of
  tall walnut or black-oak cabinetry with integrated fridge and ovens, a range with a hood,
  pendants over the island, a breakfast table near the glass. Stone or large-tile floor.
- scullery: 5.2 x 9.2 m: the working back kitchen: open shelving, a second sink, pantry
  cabinets, a coffee station.

### dining + wine_room (prefix `dining_`)
- dining: 15.7 x 9.2 m, glass north wall, openings to the great room, kitchen and gallery.
  A long table for 12-14, upholstered dining chairs, a sculptural chandelier or row of
  pendants (point lights), a sideboard, art.
- wine_room: 12.2 x 9.2 m, door from the scullery: a collector's cellar. Floor-to-ceiling
  wine racking with bottles (instanced, cheap geometry), a glass-fronted climate wall, a
  tasting table.

### entry + powder + cloak (prefix `entry_`)
- entry: 15.7 x 9.2 m, double height, an 8.4 m glass front (south), the floating stair along
  the north wall (keep it and 1 m in front clear), doors to the powder room (west) and
  cloakroom (east), opening to the gallery (north-east). Pale limestone floor. A statement
  chandelier or light sculpture in the double-height volume, a round console table with a
  sculpture or flowers, a bench, a large artwork.
- powder: 5.2 x 9.2 m: a luxurious powder room: stone vanity with vessel basin, a large
  mirror, a wall-hung WC, sconces. Dramatic finish (dark stone or veined marble walls).
- cloak: 5.2 x 9.2 m: coat cloakroom: walnut wardrobes, a bench, a mirror.

### courtyard (prefix `courtyard_`)
- courtyard: 20 x 14 m, open to the sky (sun and sky light it), glass on all four sides on
  both floors, a doorway from the south gallery at x -1.5..1.5. Limestone paving (FINISHES
  floor), an olive tree (or two) in a large stone planter, a long reflecting pool or
  fountain, an outdoor lounge (teak and cushions), low planting. Keep a clear path from the
  doorway. No ceiling; no ceiling LIGHTS (it's outdoors).

### garage + mudroom (prefix `garage_`)
- garage: 12.2 x 19.7 m, garage door on the south wall, door to the mudroom (north).
  Polished concrete floor, a showroom feel: 4-6 parking bays (leave them clear: the car is
  built separately and will be placed by the orchestrator in two bays at local
  (-3, -5.5) and (+3, -5.5), facing south), a tool wall / cabinetry, EV chargers, good bright
  strip lighting.
- mudroom: 12.2 x 10.2 m, doors to the gallery (west) and garage (south), a window east:
  lockers with a bench, a laundry wall (washer, dryer, sink, folding counter).

### car (prefix `car_`; Opus) — asset only
- `car_ev`: one hero asset: a sleek modern luxury electric car (an original design, no real
  brand), ~4.9 x 2.0 x 1.4 m, origin at the floor centre, front facing -Y. Body panels with
  clean surfaces and shut lines, glass canopy, wheels with tyres and brake discs, light bars
  front and rear (emissive), interior visible through the glass (seats, dashboard, wheel).
  Up to 25k triangles. Paint parameter (colour) so the garage can show two different cars.

### primary_bath (prefix `bath_`)
- primary_bath: 9.7 x 9.2 m, upper floor, door from the primary bedroom (east wall of the
  bedroom, the bath's west wall). Book-matched marble walls and floor, a freestanding stone
  tub, a double vanity with mirrors, a walk-in glass shower, a towel warmer, sconces.

### guest_room + gym (prefix `guest_`)
- guest_room: 12.2 x 10.2 m, upper floor, glass east wall, door from the east gallery: a
  calm guest suite in a lighter palette (oak, linen, sage): bed (a new guest bed asset, or
  the existing `bed`), nightstands, a desk, an armchair, a rug.
- gym: 12.2 x 9.2 m, upper floor, glass north wall, door from the office (west): rubber
  floor (FINISHES), a mirror wall, treadmill, bench and weight rack, a cable machine or
  rower, mats.

### library + office (prefix `library_`)
- library: 17.7 x 9.2 m, upper floor, interior glass looking into the great room (north
  wall, west part), glass west wall, door from the south gallery: floor-to-ceiling walnut
  bookshelves with books (cheap repeated geometry with a book-spine texture), a rolling
  ladder, reading chairs, a large library table, a rug, reading lamps.
- office: 13.2 x 9.2 m (rooms/office.py exists: keep the desk, desk chair, the lounge
  group, the vase and the keycard attachment exactly as they are): add what the big room
  lacks: bookshelves or a credenza on the walls, a sofa or second seating, a plant, art.

## Grounds (outdoor zones; see prompts/build_zone.md)
Estate character, shared by every zone: a modern tech-billionaire estate. Clean
rectilinear architecture and hardscape matching the house (white render, pale limestone,
dark bronze/black metal, weathered teak), generous scale, restraint; planting in a
Mediterranean / Pacific-coast palette (olive, Italian cypress, clipped boxwood and yew,
ornamental grasses, lavender), immaculately kept. Nothing rustic or cute. Everything is
seen through the house's windows, mostly from 5-60 m away.

### pool_terrace (prefix `pool_`), rect x -8..24, y 25..52, 7,000 tris
The view from the kitchen (ground floor) and the office and gym (upper floor). A raised
limestone pool deck (about 0.45 m above the lawn, with broad steps down to the lawn on
its open sides) carrying a 25 x 6 m lap pool running east-west, roughly centred on the
office windows. Its north long side is an infinity (vanishing) edge: the water runs to a
knife edge with a catch trough a step lower outside it. A sun shelf (very shallow water)
at the west end with two in-water loungers. Six to eight teak sun loungers with sand
cushions in pairs, two large square cantilever umbrellas (charcoal canvas, dark metal),
a low limestone bench wall, side tables, a pair of large stone planters with clipped
shrubs. Keep the deck's edge 2 m clear of the house terrace so the two read as levels.

### pool_house (prefix `cabana_`), rect x 24..66, y 25..58, 7,000 tris
The pool's companion, seen from the gym and office (upper) at an angle. A modern pool
pavilion about 14 x 7 m: a thin cantilevered flat roof (0.3 m slab, white render) on
slender dark metal columns, floor-to-ceiling glass on the pool side (outdoor.glass()),
teak screen walls on the others; inside, glimpsed through the glass, a sofa, a bar and a
daybed. Beside it an outdoor kitchen: an 8 m stone counter run (grill, sink, dark metal
cabinet fronts) under a teak-and-dark-metal pergola with an outdoor dining table for ten.
Stone stepping slabs set in the lawn link it to the pool deck to the west.

### fire_garden (prefix `firepit_`), rect x -48..-8, y 25..58, 5,000 tris
Seen from the dining room (ground) and the primary bedroom (upper). A circular stone
terrace about 10 m across, slightly raised, with a built-in curved bench (stone base,
cushion top) around three quarters of it and a central fire bowl (dark metal or stone,
low embers using outdoor.lamp()); four lounge chairs. A ring of low clipped hedge
(outdoor.foliage(), ~0.9 m) with openings frames it. Gravel paths lead from the house
terrace to it and on to a small gravel pétanque court with a teak bench. Beds of
ornamental grass and lavender (planting assets) soften the edges.

### west_garden (prefix `garden_`), rect x -66..-31, y -22..25, 6,000 tris
The most visible zone: the great room's 8.4 m glass wall looks straight down it (great
room centre line y = 0) and the library looks over it from above. A formal axial garden
on the great room's axis: a long reflecting pool (about 30 x 4 m, crisp stone coping,
water almost flush) running west from the terrace on y = 0; parallel stone walks either
side; symmetrical rows of clipped box cubes and an allée of olive trees (plant_tree_olive)
or cypress; at the far west end a large abstract sculpture (bronze or dark metal, 4-5 m)
as the focal point of the view; a pair of stone benches facing the pool.

### motor_court (prefix `court_`), rect x -14..30, y -46..-25, 6,000 tris (may also use the south terrace band y -25..-20)
The arrival court in front of the entry's glass wall (x -6..6) and the garage door
(x 15.5..24): a large paved court (limestone banding framing a pale gravel field), a
central circular fountain (raised stone basin about 8 m across, still water, a monolithic
stone or bronze sculpture rising from it), a cantilevered entrance canopy over the front
of the entry (thin flat roof about 12 x 5 m on two slender columns, on the terrace band),
large planters with multi-stem trees, bollard lights (outdoor.lamp()) at the edges. The
drive (drive_gate) arrives at the court's south edge around x 14..25.

### drive_gate (prefix `gate_`), rect x 12..30, y -66..-46, 5,000 tris
The drive from the motor court south to the gap in the hedge (x 14..25.5 at y -62): a 7 m
wide drive (stone edging, gravel or stone surface), lined with an avenue of Italian
cypress (plant_tree_cypress) and low bollard lights. At the hedge: a modern gate - two
monolithic stone piers about 3 m tall, sliding dark metal gates of vertical slats - and a
small gatehouse (white render and glass, flat roof) just inside it.

### south_lawn (prefix `lawn_`), rect x -66..-14, y -60..-25, 4,000 tris
Seen from the entry's glass front at an angle and the library above. A sculpture lawn: two
or three large modern sculptures (abstract stone and bronze forms, 3-6 m) placed with
care on the open lawn, a gravel walk looping between them, a low limestone retaining
wall with a bench, and a grove of specimen trees (planting assets) at one side.

### tennis (prefix `tennis_`), rect x 33..68, y -22..25, 4,000 tris
Seen from the guest room (upper) and mudroom windows to the east. A tennis court running
north-south: 36.6 x 18.3 m surround, playing area 23.77 x 10.97 m, a dark green hard
court with a blue-grey playing area and crisp white lines (thin strips 3 mm proud), net
with posts; a refined dark metal fence (slim posts and rails, about 3 m behind the
baselines and lower at the sides), a small shaded viewing pavilion with a bench and a
teak umpire's chair.

### kitchen_garden (prefix `kgarden_`), rect x 30..68, y -60..-25, 6,000 tris
The estate's working garden, south-east. A glass greenhouse about 12 x 6 m (slim dark metal
frame, outdoor.glass(), gabled roof, potting benches inside), a grid of raised beds (teak
or dark metal sides, soil, rows of crops as low foliage strips), gravel paths, a small
orchard of fruit trees (plant_tree_fruit) and a timber potting shed.

### planting (prefix `plant_`), rect: the whole estate, 12,000 tris
Owns every tree and shrub asset; write these FIRST (other zones place them), then plant
the estate. Assets (each a thin wrapper of one `plant_tree.py` / `plant_shrub.py`
generator, like `door_plain.py` wraps `door.py`): `plant_tree_round` (broad deciduous
crown, 12 m), `plant_tree_olive` (gnarled multi-trunk olive, 5 m, silver-green crown as
a flat colour), `plant_tree_cypress` (Italian cypress, 10 m, slim), `plant_tree_multistem`
(multi-stem birch-like, 7 m, light green flat crown), `plant_tree_fruit` (small apple
tree, 4 m); `plant_shrub_round` (boxwood ball 1 m), `plant_shrub_box` (clipped cube
1 x 1 x 0.8 m), `plant_shrub_grass` (ornamental grass clump, straw colour),
`plant_shrub_lavender` (grey-violet mound). Budgets: trees 400-900 triangles (cypress
~300), shrubs under 150. Crowns read as masses of leaves, not balls: lumpy, layered, with
gaps and some limbs showing; foliage() for green crowns, flat colours for olive, birch,
lavender and grass. Then the zone module (zone-local = plan coordinates, the estate centre
is (0, 0)): groups of trees inside the hedge (within 4 m of it, irregular groups, not a
row), a few specimen trees on open lawn between other zones (stay out of every other
zone's rect, `plan.GROUNDS["zones"]`), and planting just outside the terrace's outer edge
(1-2 m beds of shrubs and grasses, keeping the big windows' views open).

## Characters

### grimble (the villain; Opus; asset `blender/assets/grimble.py` + engine `viewer/grimble.js`)
- Status: READY
- Concept: `concept/grimble/front.png` (the user's image). Cute-uncanny: a small-looking
  creature blown up to giant scale. The horror is the contrast: it's adorable, it's
  4.6 m tall, and it's at your window.
- What: a hunched, cloaked, furry biped leaning on a gnarled staff.
- Size: about 4.6 m (15 ft) standing, hunched; the head alone ~1 m across, the eyes
  ~0.3 m. Next to the house: half the height of the great room's 8.4 m glass wall; it
  steps over the 2.8 m perimeter hedge.
- Look (from the concept):
  - eyes: huge, glossy, near-black with a warm brown iris and a bright catch-light; a
    real eyeball + clear cornea so they reflect the sky and the house; they track the
    player once it's close (the creepiest thing it does);
  - face: short fur, pale tan muzzle and cheeks, darker crown, a small wrinkled nose,
    a closed sly smile;
  - cloak: heavy, coarse, near-black woven wool, hood up framing the face, frayed and
    fringed edges, pooling at the feet; drapes in big folds at this scale;
  - hands: long thin fingers, wrinkled leathery brown skin, dark claws; feet: bird-like
    toes with long claws showing under the hem;
  - staff: taller than it, gnarled dark wood, knotted, a carved hooked head; held in the
    right hand, planted with each step.
- Behaviour (first milestone): it starts far out on the horizon on the west garden's axis
  (golden-hour sun behind it, so it arrives as a silhouette), walks toward the house
  with slow giant strides, planting the staff, steps over the hedge, crosses the lawn
  and the terrace, stops at the great room's glass wall, knocks on the glass (three
  slow taps, the glass shudders), then waves. Keeps waving / watching while the player
  is near. Later: chooses the window the player is at, and eventually comes inside.
- Movement: walks (no running). Animations needed: walk (hunched, staff-assisted, heavy),
  stop, knock, wave, idle (breathing, head tilt as in the concept, blinks), eye/head
  look-at.
- Sound: none for now.
- Build plan: base sculpt from the concept via image-to-3D (Blender MCP `generate_3d`,
  costs a credit per try; ask first), then rebuilt where it matters: eyes, hands/claws,
  staff (procedural), cloak (cloth sim on the body + woven fabric texture); retopology
  to ~30-40k triangles; rig (body + face: eyes, lids, smile; a few cloak bones);
  animations from Mixamo clips retargeted plus custom keys (knock, wave, head tilt).
- Engine: one skinned glTF, AnimationMixer, path follower + scripted event; lit by the
  real-time sun plus the sky (outdoors has no baked light for a moving thing); a soft
  blob shadow on the unlit lawn; cheap shell fur on the face and hands; always drawn
  while in view.
- Budget: ~30-40k triangles, 2-3 texture sets at 1024 (body/fur, cloak, eyes+staff).
- Decided (2026-10-19): the great room's west glass for the first milestone; it starts a
  short delay after the game loads; image-to-3D credits are OK (2-3 tries).
- Open (later): its personality / the "turn" (does the cute ever drop?), choosing the
  player's window, coming inside, sound.

## Below ground: the secret passage (design/house/secret_passage.md)
Shared by every asset here: the palette is `blender/assets/bunker_kit.py` (import it like
`library_kit`; use ONLY its materials plus `lib/materials.py` ones: walnut, steel, black_metal,
bronze, glass; no new textures: the whole download budget for these rooms is ~0.5 MB). The
armory is the library's cold twin: expensive, quiet, precise (Vivos / Rising S / Survival Condo
armories, a Purdey gun room, an Apple Store's restraint): brushed stainless, graphite powder
coat, charcoal felt, cold white LED. The tunnels are utilitarian and old-feeling but well built
(CERN service tunnels, Cheyenne Mountain, the Greenbrier's Project Greek Island): raw concrete,
galvanised steel, grey conduit, caged bulkhead lights. Seen mostly from 1-6 m, by the light of
a few baked lamps and the player's flashlight. Props are lit by their room's probe; emissive
parts named `*_Glow` or `*_LED` (fixtures: asset names containing `light`/`lamp` get the
bake's fixture rules). Conventions as everywhere (metres, origin at the floor centre, front
-Y, parts `<Asset>_<Part>`; few parts: one mesh per material where nothing moves).
Every hand-sized loose thing here stays FIXED set dressing (no pickups) unless stated.

### armory_safe_wall (Model: opus)                       blender/assets/armory_safe_wall.py
- Status: READY
- What: the armory's hero: a built-in gun safe wall, five 1.18 m bays wide (5.9 x 0.62 x 2.75 m),
  a monolith of brushed stainless doors in a graphite frame; turn the wheel and the five doors
  lift one after another like the lids of a jewel case, each bay lit inside.
- Size: 5.90 wide (x), 0.62 deep (y; the back is against the wall at y = +0.31), 2.75 tall.
- Construction: graphite carcass (back, top, sides, 4 mullions 0.05 wide between the bays, a
  0.08 recessed plinth); per bay an interior: charcoal felt back panel and sides, a felt-covered
  floor at 0.22, cradles (two rows of padded U-rests, graphite) for long guns standing upright at
  x -0.35..+0.35 of the bay centre, a slim cold LED line down both inner sides and across the
  top inside (`*_LED`, static emissive), a small stainless nameless plate (no text) at the
  bottom. Doors: one per bay, 1.12 x 2.45 x 0.05, brushed stainless with a fine 3 mm shadow-gap
  border, a recessed vertical pull channel, hinged at the TOP (hinge axis along x at z 2.6, at
  the front face): opening = rotate up 95 degrees outward to become a horizontal canopy over
  the bay (keep it clear of a 3.4 m ceiling: the open door's top must stay under 3.3 m).
  The middle bay (bay 3) has no long-gun cradles: a felt pegboard for pistols and a drawer-like
  felt shelf at 1.0; its door carries the wheel.
- The wheel: a 0.42 m spoked stainless handwheel (5 spokes, a knurled rim, a graphite hub) on
  the middle door at 1.3 m, standing 0.08 proud.
- Interact: the wheel is a `switch` on an empty at its hub: `{type: "switch", signal:
  "armory_safe", state: false, prompt: "Turn the wheel", promptActive: "Close the safe",
  range: 1.4, duration: 1.1, travel: {axis: "z", angle: 270}}` (glTF axes: the wheel turns
  about its own axis, which points out of the wall: -Y in Blender = +Z in glTF, so `axis: "z"`).
  Each door hangs from its own empty at its hinge with a `react` (NOT an interact):
  `{signal: "armory_safe", on: {rotate: {axis: "x", angle: A}}, duration: D, collide: true,
  motor: false}` where A is the sign that lifts the door outward (+/-95: check in the preview
  with `--set` variants or a test pose), D = 2.0, 2.35, 2.7, 3.05, 3.4 from the middle bay
  outward... i.e. middle first (2.0), then its neighbours (2.35), then the ends (2.7): the doors
  rise from the centre outward. The wheel's door must carry the wheel's empty as a child (the
  wheel rises with its door). Put reacts on the door empties, not the root.
- Weapon slots (report them in your summary, in the asset's local coordinates): per long-gun bay
  three upright positions (x = bay centre -0.3, 0, +0.3; y = +0.12; z = 0.22 the felt floor),
  and in bay 3 four pistol positions on the pegboard (z 1.25 and 1.65, x +-0.2, y +0.2).
- Budget: 14,000 triangles; no textures.
- Placement: against the armory's west wall, rotation -90 (faces east), centred on the room.

### armory_rifle, armory_shotgun, armory_pistol, armory_bat (Model: opus)   one file each
- Status: READY
- What: set dressing for the safe wall's slots (later the weapons workstream turns them into
  pickups: NO interact now). Believable at 0.5 m, modern, unbranded, nothing tactical-cosplay.
- armory_rifle: an AR-pattern carbine STANDING UPRIGHT (muzzle up, the buttstock's base on the
  origin), its left side facing -Y: 0.86 tall, 16" barrel, M-LOK handguard, a small optic,
  sling swivels; gunmetal + black polymer (+ one in `variant=tan` with a tan stock and handguard).
- armory_shotgun: a pump shotgun standing upright, 1.0 m, black polymer stock, gunmetal receiver
  and barrel, a side saddle.
- armory_pistol: a polymer-frame pistol lying on its right side (origin at the underside centre),
  0.19 x 0.03 x 0.14, gunmetal slide.
- armory_bat: an aluminium baseball bat standing on its knob end... no: standing on its barrel
  end is how they lean: stand it upright on the barrel's end cap (handle up), 0.84 m, satin
  black anodised barrel with a thin stainless band, black grip tape.
- Budget: rifle/shotgun 3,500 tris each, pistol 1,500, bat 600; no textures.

### armory_table (Model: sonnet)
- Status: READY
- What: the layout table in the room's middle (the twin of the library's reading table): a
  2.4 x 1.0 m stainless top 0.92 high on a graphite frame with a lower shelf of olive ammo cans,
  a black rubber bench mat on the top with an open hard rifle case (black, foam with cut-outs:
  felt), a cleaning rod, a few gunmetal tools, a torque driver; under-shelf cold LED strip (`*_LED`).
- Budget: 9,000 tris.

### armory_bench (Model: sonnet)
- Status: READY
- What: the gunsmith's bench against a wall: 2.2 x 0.75 m walnut butcher-block top at 0.95 on a
  graphite drawer base (4 drawers), a heavy gunmetal bench vise at one end, a padded gun cradle,
  behind it a 2.2 x 1.2 m graphite french-cleat wall (starts 0.15 above the top) holding
  screwdrivers, punches, a hammer, a torque wrench, a scope box, a coil of cord; an articulated
  task lamp (name the part `..._Lamp`, a cold emissive `*_LED` head).
- Budget: 10,000 tris.

### armory_security (Model: sonnet)
- Status: READY
- What: the security station: a graphite desk 2.4 x 0.8 m with a 3 x 2 bank of thin 27" monitors
  on a wall-mount frame (screens: `bunker_kit.screen()`), a keyboard, a radio handset in a cradle,
  a black mesh task chair (pushed in).
- Budget: 8,000 tris.

### armory_power (Model: sonnet)
- Status: READY
- What: the emergency power and air wall: three white wall-hung battery units (1.15 x 0.75 x
  0.15 each, a thin vertical cold LED line on each: `*_LED`), a graphite transfer-switch cabinet
  (0.6 x 0.3 x 0.9) with a big red rotary handle, grey conduit up into the ceiling (to 3.4), and an
  NBC air-filtration unit (a white steel cabinet 0.7 x 0.5 x 1.3 with two round gauges, a hand
  crank and a flexible duct up to a ceiling blast valve).
- Size: about 3.6 wide x 0.55 deep x 3.4 tall (against a wall).
- Budget: 9,000 tris.

### armory_supplies (Model: sonnet)
- Status: READY
- What: a run of graphite steel shelving (2.4 x 0.5 x 2.2, four shelves): blue water drums on the
  floor shelf, kraft ration cases, olive ammo cans, a white medical cabinet with a red cross
  (shape only) beside it on the wall (part of the asset), two gas masks and two olive plate
  carriers hanging from hooks at the end.
- Budget: 9,000 tris.

### tunnel_bulkhead, tunnel_bulkhead_dead (Model: sonnet)
- Status: READY
- What: a cast-aluminium caged oval bulkhead light on the tunnel wall (0.28 x 0.12 x 0.18),
  galvanised cage, an opal lens (`bunker_kit.lens()`, part `..._Glow`), a short conduit up out of
  it. `tunnel_bulkhead_dead`: the same, lens dead (`lens(False)`), cage bent, hanging off one
  screw at an angle, a dangling cable (it's a thin module importing the first with a variant).
  Origin: the centre of its back on the wall plane; it faces -Y (place on walls with rotation).
- Budget: 800 tris each.

### tunnel_conduit (Model: sonnet)
- Status: READY
- What: a 6.0 m run of services along a tunnel wall: a galvanised ladder cable tray (0.3 wide) at
  2.35 with a few black and grey cables in it, three grey conduits below it on galvanised strut
  brackets every 1.5 m, a junction box at one end. Origin: floor point under the run's middle on
  the wall plane; the run lies along x, standing off the wall toward -Y.
- Budget: 3,500 tris.

### tunnel_channel (Model: sonnet)
- Status: READY
- What: a 6.0 x 0.3 m drainage channel grate set into the floor at the tunnel's edge: galvanised
  bar grate 0.01 above the floor over a dark recess (fake depth: a dark inner floor 0.002 under
  the grate's top: keep everything within 0.012 of the floor so it walks flat).
- Budget: 1,500 tris.

### tunnel_puddle (Model: sonnet)
- Status: READY
- What: standing water: an irregular flat patch (3.0 x 2.2 m outline, soft lobed edge, a few
  islands) `bunker_kit.wet()`, 2 mm above the floor; plus `variant=small` 1.2 x 0.8.
- Budget: 600 tris.

### pump_station (Model: sonnet)
- Status: READY
- What: the pump room's sump: a 1.6 x 1.6 m galvanised (rusting at the edges) pit grate in a
  concrete kerb, two vertical blue pump motors on it, discharge pipes rising, joining and running
  up to 2.6 then along (2.0 m) into the wall, a gate valve with a red handwheel, a grey control
  box with two lamps (one green `*_LED`), a yellow-painted kerb edge. 2.2 x 1.8 x 3.0.
- Budget: 9,000 tris.

### bunker_door, blast_door (Model: sonnet)                  one file each
- Status: READY
- What: doors for `plan.CUTS` (like `door.py`: origin = bottom centre of the opening on the
  wall's centre plane, the room it swings into is +Y, the hinge empty carries
  `interact = {type: "rotate", axis: "y", angle: 90 (or -90: into +Y), prompt: "Open door" /
  "Close door", collide: true, side: "both", duration}`).
  `bunker_door`: a 1.2 x 2.15 opening in a 0.3 m wall; graphite steel door 0.06 thick with a
  stainless lever handle both sides, a narrow vertical vision slot of ballistic glass, a steel
  frame; duration 0.9.
  `blast_door`: a 2.0 x 2.2 opening; a 0.28 m thick steel door (graphite with a stainless edge
  band), four heavy bolt-heads, big external hinge knuckles on a steel frame that stands 0.1
  proud on both faces, a 0.6 m spoked wheel on each face (fixed: part of the leaf), a
  safety-yellow kick plate on the frame sill; duration 3.2 (it's heavy).
- Budget: bunker_door 3,000, blast_door 7,000; no textures.
