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
- Status: DRAFT
- Model: sonnet
- What: a sculptural ceramic vase, the kind on a billionaire's coffee table
- Size: about 0.18 wide x 0.32 tall (proposed)
- Materials: new matte glazed ceramic (proposed: warm off-white or charcoal), subtle
  speckle texture
- Details that sell it: turned profile (built by revolving a curve), a thin lip with a
  visible wall thickness, a slightly glossier glaze inside the mouth, a faint unglazed
  foot ring
- Interact: pickup (item "vase", name "Vase"); also throwable once the arm feature exists
- Budget: under 3,000 triangles, one 1024 texture at most
- Placement: on the coffee table in the office (proposed)
- Open questions:
  1. Style: ceramic (matte white / charcoal / terracotta), glass, or bronze?
  2. Size: tabletop vase (~32 cm), or a tall floor vase?
  3. Empty, or with dried stems / a branch in it? (stems are much harder to make look good)
  4. When thrown: does it shatter, bounce and stay whole, or shatter and leave pieces?
     Can the player pick it up again?

## picture_frame
- Status: DRAFT
- Model: sonnet
- What: a framed artwork for the hall walls; one asset with parameters for size and
  artwork, so the hall can hang several different pieces
- Size: parameterised; e.g. 0.6 x 0.8, 0.9 x 1.2, 1.2 x 0.8 (w x h), ~4 cm deep
- Materials: thin black or walnut frame, white mat, artwork as a generated texture
- Details that sell it: mat bevel, a glass sheen (slight reflection), the frame casting a
  thin shadow line on the wall (it stands ~1 cm off the wall)
- Interact: none (proposed)
- Budget: under 500 triangles per frame; artwork textures 1024 at most
- Placement: hall walls
- Open questions:
  1. Artwork style: abstract colour fields (Rothko-like), geometric (Mondrian-like),
     line drawings, black-and-white "photographs" (generated, not real photos), or a mix?
  2. Any story role? e.g. one picture hides a safe, or shows the billionaire / his company.
  3. Frame: black, walnut (matches the office), or brushed metal?

## bedroom assets (one entry each once the list is agreed)
- Status: DRAFT
- Model: sonnet (bed: opus if it gets bedding with folds; that's the hardest piece)
- Proposed list: bed with headboard and bedding, two nightstands (one with a drawer),
  table lamp, wardrobe or built-in closet, rug, bench at the foot of the bed
- Open questions:
  1. What should the bedroom contain? Add or cut from the list above.
  2. Is anything in it interactive or part of the story? (a nightstand drawer with
     something in it, a closet that opens, a lamp you can switch...)
  3. Mood: same warm walnut / white / cognac palette as the office, or its own
     (e.g. darker, more private)?

---

## Orchestrator work (not sub-agent jobs)

### Arm feature (engine)
Proposed controls, to confirm:
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

### Hall (level)
Replaces the corridor stub behind the office door.
Open questions:
1. Length and shape: straight, ~10 m, ~2 m wide? Ceiling height?
2. Which side is the bedroom door on: the far end (as you described)? Any other doors
   now, even locked ones for later rooms?
3. Windows, or interior only?

### Bedroom (level)
Open questions:
1. Size (~6 x 5 m?) and does it have the same floor-to-ceiling glass as the office?
2. Is its door locked, and if so what opens it?
