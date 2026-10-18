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
