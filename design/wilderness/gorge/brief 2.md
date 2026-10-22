# Stairway of Power (wilderness concept, slug `gorge`)

**Hook:** 130 m past the gate the meadow just stops. The estate sits on the lip of a 170 m
gorge, the only bridge belongs to the invaders, and the way out is down: under their bridge,
down a hydro penstock's 850 steps, or into a slot canyon that starts as a crack in the grass.
At the bottom, a freight train you have to stop.

## Why it isn't the modal answer
- **The wilderness is mostly air.** The walk from the gate to the exit is about 320 m on the map
  and 150 m down. Distance doesn't decide anything; height does, and so does which wall you
  are on.
- **The routes aren't trails, they're infrastructure.** This is a worked canyon, like
  California's Feather River Canyon (the "Stairway of Power" hydro chain, the Western Pacific
  line, the Keddie Wye trestle). A 1910s penstock and its brick powerhouse, an active freight
  line running between two tunnels, a 1920s road whose north half was blasted away for the
  billionaire's white arch bridge. The old working gorge sits under the new glass and concrete.
- **Danger comes from across, not from behind.** Someone standing on the rim right above you
  can't see you past the lip. Someone on the far rim, 130 m away, sees your whole wall like a
  picture hung on it. The gunners' job is to get to the opposite rim.
- **Two climates face each other.** Real canyons are strongly asymmetric. The south-facing
  north wall is baked rock, chaparral and yucca under all-day sun. The north-facing south wall
  is wet and black-green: moss, maidenhair fern, bay laurel, seeps. The player is lit on one
  side and hidden on the other.
- **Scale inversion.** In the house the Grimble is a giant. Against a 170 m wall it is the
  right size for the land, and that's worse.

## Goal and arc (6-12 min)
**Goal: stop the westbound freight and get on it.** The track crosses the river on a steel
trestle and enters the West Tunnel in the north wall. Throw the block-signal lever at the
portal to red, and the next train grinds to a halt with its wagons strung back across the
trestle. Climb onto a wagon (E) and the run ends. Trains come every **4 min**. You hear the
horn echo out of the East Tunnel 60 s before the train reaches the trestle, anywhere on the
map, so the clock is audible and never written down.
Arc: the plateau (exposed, 30 s) → choose a descent (3-6 min) → the bottom, where every route
and the melee invaders meet → the trestle at the horn.

## Layout (world metres, estate frame: x east, y north, lawn z = 0; see map.svg)
- **The meadow apron** (y -80 to the rim). Unirrigated gold oat grass, a few valley oaks, gray
  pines. The estate's green ends at a sharp irrigation line just past the hedge (y -80). The
  drive runs on south from the gate (20, -62).
- **The gorge.** Runs east-west. Rim-to-rim 130 m at the bridge (x 20), 200 m in the
  powerhouse bowl (x 250-450), 90 m at the trestle (x -250). It pinches to **the Narrows**
  (25 m at the rim, 190 m deep) at x < -450, where the river leaves the map. The river flows
  west: z -150 at the dam toe, -170 under the bridge, -182 at the trestle. Walls are near
  vertical below z -100 and step back above it on ledges and talus.
- **Landmarks** (each visible from most of the map): the **white arch bridge** (centre, deck
  z 0); the **surge tower** on the east rim (225, -148), a 30 m concrete drum; the **dam**
  (east edge, x 650), a 140 m concrete arch with a bright reservoir behind it; the **black
  trestle** (west, deck z -152); the **Narrows** to the west, a black slit with the low sun in
  it (in the "golden" look, `mansion.py` LOOKS, the sun is ~19° up from just south of west, so
  it rakes straight down the gorge).
- **Edges, all natural:** north is the hedge. East is the dam's face. West is the Narrows
  (white water between vertical walls). South, past the south rim, is head-high chaparral
  (manzanita, chamise: genuinely impassable) and the invaders' road. Playable area about
  **1.1 km x 0.35 km x 190 m deep** (x -480..620, y -60..-400). Behind that is backdrop: the
  reservoir, the far chaparral hills, Sierra ridges.

### Three routes down
| Route | Path | Length / time (run 6.8 m/s; stairs and ladders slower) | Why take it / what it costs |
|---|---|---|---|
| **A. Under the bridge** | gate → north abutment (125 m) → inspection catwalk under the deck (120 m, grating, 170 m of air below) → 35 m ladder down the last spandrel column to the south springing (z -45) → the **old road**: 9 hairpins down the shaded south wall (~700 m at 15%; scree chutes between hairpins cut it in half at a fall-damage risk) → railway shelf (z -150) → west 180 m along the track → across the trestle (118 m) | ~1.3 km, 3-4 min | Fastest, and in shade the whole way down. But you cross directly under the invaders, and you descend their side: their pickup comes down the hairpins with its headlights sweeping the wall. You're exposed to anyone who followed you onto the north rim. |
| **B. The penstock** | rim path east to the surge tower (260 m) → **850 steps** beside the 2.4 m riveted pipe, 40°, 152 m drop, 8 concrete anchor blocks as landings → brick powerhouse (z -150) → low swinging footbridge, 8 m over the water → west along the track 560 m (an 80 m rock shed gives cover) → trestle | ~1.25 km, 5-6 min | Readable, no dead ends, and you can fight on it (bring armory weapons). The stair runs on the pipe's east side, so the pipe is a 2.4 m wall between you and the bridge and its convoy. You're exposed to the eastern perches the whole way down the sunlit wall. **The powerhouse control room has the dam-release lever.** |
| **C. The Cut** | 80 m west of the gate a crack opens in the meadow (-55, -95). It deepens south-west for ~360 m to a hanging mouth in the north wall (-245, -200, z -122): 9 pour-overs (2-8 m), two chockstone squeezes (crouch), a chest-deep keeper pothole (wade: slow and loud), "the Cathedral" (a chamber open to the sky) → a 30 m iron ladder pinned to the rock → the portal apron, at the lever | ~0.5 km, 4-5 min | The only route that's invisible from the rims (except the Cathedral and the mouth), and it **arrives at the lever**. You can't go back: past the first 4 m pour-over there's no climbing back up. Anyone who sees you drop in can follow you, and can drop rocks on you at the Cathedral. |

**Chokepoints:** the north abutment (one way onto the catwalk); hairpin 1 (vehicles and foot
meet); the penstock's anchor blocks; the swinging bridge; the trestle (exposed to everything
for 118 m, with refuge bays every 30 m); the Cut's mouth ladder.

## Pursuers and the Grimble
- **Where they come from:** the bridge's south end (their convoy; new waves keep arriving by
  road), out of the estate gate behind you, and a few already at the bottom around the
  powerhouse.
- **Gunners hold the rims.** They move along a graph of rim *perches* and shoot across the
  gorge. Three sight rules make going down survivable, and they're legible:
  1. **The lip:** nobody within ~10 m horizontally of a rim can see straight down past it.
  2. **River mist:** notice rate x exp(-L/35 m), where L = the length of the sight ray below
     z -110. A gunner on the rim can barely pick out someone at the bottom more than ~60 m away.
     **The bottom is safe from guns, not from knives.**
  3. **Shade:** a target on the shaded (south) wall is noticed at half rate. A target on the
     sunlit wall, or out on the trestle against the bright west sky, at full rate.
- **Melee invaders follow your route** down the same catwalk, stair or road. They converge on
  the bottom, which is where you have to be when the horn sounds.
- **Echo** (cheap, new): a noise below the rim is also heard as coming from its mirror point
  on the opposite wall at 0.8 loudness. Throw a rock at the far wall and the search goes
  there.
- **The Grimble (easter egg; never load-bearing).** If the house timer fired, or you've spent
  more than 12 min in the gorge, it steps over the dam crest at the next horn, a silhouette
  against the glare off the reservoir. It wades down the river (the water reaches its knees)
  hunting by sound, echo included. If you're in the Cut, it follows the slot's rim and
  straddles it, one foot on each lip.

## Player verbs and systems
Uses what exists: walk, run, crouch, jump, `switch` (signal lever, dam release), throwables
(rocks as lures, or dropped on heads below: `knockDown`), flashlight (tunnels, the Cut),
tablet cameras (add gorge feeds: bridge, powerhouse, portal), the Noise bus, the senses and
search AI.
New and needed: **ladders** (a climb volume), **fall damage** (<3 m nothing, 3-6 m a stagger
reusing `knockDown`, >8 m death), **wading** (water volume: speed x0.5, makes noise), the
**flood** (signal `dam_release`: the river mesh slides up 2.5 m over 30 s and a current volume
knocks you down and drags you), the **train** (a spline mover with moving colliders; boarding
is a `use` that ends the run, not a ride), **echo**, **height mist** in fog and AI notice,
and **river sound occlusion** (the river is silent on the plateau and swells in as you near
the lip; this is real, the rim makes an acoustic shadow).

## Signature moments
1. **The reveal.** Out of the gate, gold grass for 130 m, then nothing. The white bridge floats
   over a gap you can't see the bottom of. Headlights at its far end. The river is silent until
   you're 10 m from the lip, then it roars up out of the ground.
2. **Under their boots.** On the catwalk, boots and voices on the deck 1.5 m above you through
   the expansion joints. Someone flicks a cigarette over the parapet and it falls past you for
   six seconds.
3. **The sky goes out.** Deep in the Cut, the bright slit overhead goes black from one end to
   the other. Something is standing astride the slot.
4. **Opening the dam.** In the powerhouse, throw the release. A siren wails off the dam,
   45 s, then a brown surge comes round the bend. The invaders on the gravel bars run. The
   swinging bridge goes under, and so does your own way across.
5. **Stand By Me.** The horn, the lever thrown, and the train stops with its last wagons on
   the trestle. You run out along the trestle's walkway in full view of every rim, in the
   last orange light, toward the open wagon door.

## Look
Golden hour (the existing "golden" look, `sun_dir` (0.94, 0.12, -0.32); no new sun). The sun
is ~19° up in the west, so it rakes straight down the gorge's axis. Amber lands on every
west-facing face: buttresses, bends, the bridge piers and the arch, the trestle towers, the
top of the mist. The north wall gets a soft warm graze (~12% of full sun) and the south wall
gets none. Where the gorge runs straight, a shaft of late sun reaches the river under the
bridge while the trestle bend is already in shade. The two climates come from all-day
exposure, not from this hour. Mist lies below z -110. Rock: rust-orange
gneiss banded with pale pegmatite dikes (the Black Canyon's "Painted Wall"), dark desert
varnish, wet streaks on the shaded side. Bottom: bleached, polished granite boulders, green
pools, white water. New things are white concrete, glass and black steel; old things are rust
rivets, red brick, creosote. Sound: the river (occluded at the rim), wind whistling in the
Cut, white-throated swifts screaming past the walls, ravens, the powerhouse hum, and the
**canyon wren**, the western canyon's signature bird, whose song is a cascade of notes falling
down the scale. The horn and the siren echo along the whole gorge.
The house's south view changes. Over the hedge you see a thin dark seam in the far meadow
(from the upper floor, the top ~6 m of the far wall) and a white bridge that seems to lead
nowhere. `horizon.py` needs a south sector to match.

## Production plan and browser cost
**What keeps it cheap: walls are backdrop, routes are authored.** The player never walks on a
cliff. Every walkable surface (catwalk, stair, old road, slot floor, track shelf, gravel bars,
plateau) is an authored path with box colliders and `level.ramps`, the same controller as the
house. Off a path means a fall volume. For the same reason the AI nav is a **graph of
polylines** (routes plus rim perches), with a 2D grid only on the plateau and the riverbed.
Load it as a separate level at the gate; the gate doors hide the swap.
- `blender/levels/gorge_plan.py` (data: centreline, rim and contour half-widths per station,
  river profile, routes) → `gorge.py`. The walls are a profile swept along the centreline, with
  numpy strata, ledges and overhang lips, chunked to 64 m, 2 LODs (4 m / 12 m), box UVs at world
  scale, baked vertex lighting (the sunlit/shaded split falls out of the bake for free). The
  plateau and riverbed are heightfield grids as in `grounds.py`.
- Assets (`gorge_*`): bridge (arch, spandrels, deck, catwalk, ladders), trestle (instanced
  towers and girders), penstock (pipe, saddles, stair, anchor blocks), powerhouse, surge tower,
  swinging bridge, signal and lever (emissive react), rock shed, dam (backdrop card plus
  crest), the old road's guardrail and the stub of road that ends in air on the north wall.
  `train_loco`, `train_wagon` (x16, instanced). `plant_*`: manzanita, chamise, toyon, yucca
  whipplei, gray pine, valley oak, bay laurel, and fern/moss cards.
- **Cheap:** height fog plus the mist layer (one uniform), instanced vegetation, the
  structures, the river (scrolling normals and foam), the flood (a react slide), echo (one
  extra Noise emit), sound occlusion, signal and lever, the horizon band.
- **Expensive:** cliff art at this size (~370,000 m² of wall; the biggest art risk: stretched
  noise reads as fake); the slot (a hero mesh, ~20k tris, 0.5 m vertex bake for the
  Antelope-style bounce glow, plus an additive light-shaft card like `fire.js`); the train
  (moving colliders, timing it to the lever); the AI on a vertical graph; the Grimble wading.
- **Estimate per frame:** walls ~120k tris visible (LOD and fog), plateau and riverbed 25k,
  vegetation 60k, structures 60k, train 30k: **~300k tris, ~130 draw calls**, inside the
  house's 501k peak / 276 mean. Textures: 2 rock sets (sunny, shaded) + gravel + grass + water
  + steel/concrete at 1024: ~40 MB of GPU memory, ~4 MB to download (WebP), plus
  ~3 MB of Draco geometry, against the house's 13.3 MB total.

## Risks
Players at the lip may not see the routes: paint the infrastructure (white rails, a handrail
on the catwalk, a lit lever) so it reads from 200 m. Falls can be frustrating: rails everywhere
except the Cut and the scree chutes. If the mist rule is tuned too generous the gunners don't
matter; too strict and the penstock is suicide. The cliffs could look procedural (use
Poly Haven cliff scans per CLAUDE.md, with strata in vertex colour). The train end is
scripted, so make it robust: it must stop even if the player is on the track. The
`drive_gate` zone and the horizon band must match the new land.

## References
Real: Feather River Canyon, CA (the hydro "Stairway of Power", the Keddie Wye trestle, rock
sheds); the Black Canyon of the Gunnison, CO (the Painted Wall, the Narrows, the Cimarron
trestle); the Foresthill Bridge and the abandoned Auburn Dam site, American River, CA; Bixby
Bridge (open-spandrel arch); Caminito del Rey, El Chorro (a hydro workers' walkway on a cliff
face, with the railway through the gorge); Antelope Canyon and Buckskin Gulch (slots that open
from flat ground); Zion canyoneering (one-way rappels, keeper potholes); the Haiku Stairs,
Oahu. Film: *Stand By Me* (the trestle), *127 Hours* (the slot), *The Fugitive* (the dam).
Games: *Uncharted 2* (the train), *Firewatch* (western landscape and palette), *Inside*
(height as the axis of danger).
