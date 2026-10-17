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
