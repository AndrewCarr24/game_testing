# Laurel Fork Cove (wilderness concept, slug `blue_ridge`)

**Hook:** past the gate is a living Blue Ridge cove in mid-June. It is a green tunnel of
45 m tulip poplars over ferns and fallen chestnut ghosts. Below, a creek drops 16 m into a
plunge pool. Above, Laurel Ridge has three rock lookouts where the canopy finally opens. From
them you look back 1 km at the glass house, sitting above its treeline. Ridge after ridge goes
blue behind it.

The user chose this concept: a verdant mountain forest, unburned, with a canyon creek, a
waterfall, a log bridge and a ridge with outcrops and long views. It has no twist, no fog
mechanic and no cabin. What makes it distinctive is how faithfully it follows the real
southern Appalachians.

## What makes it the Blue Ridge, not a stock forest
- **It is a cove, not a valley.** In the southern Appalachians a cove is a bowl-shaped hollow,
  closed by ridges on three sides and open downstream. The estate sits on the gap at the
  cove's north rim. Raven Spur closes the east side and Laurel Ridge the south. Laurel Fork
  drains west through the Narrows, straight into the setting sun.
- **These are old mountains, rounded and soil-mantled.** Slopes are convex at the top and
  concave below, cut by dendritic hollows. Erosion is tuned soft (see Appendix A), so there
  are no alpine knife-edges. Rock shows only at cliff bands and lookouts. In the test terrain
  the slopes are 28° at p50 and 41° at p90, which is Smokies-steep. 67% of the area is under
  35°.
- **The forest is sorted by water.** Coves, hollows and north faces carry mixed
  mesophytic "cove hardwood" forest: tulip poplar, yellow buckeye, sugar maple and eastern
  hemlock. South faces and convex spurs carry oak-hickory with white pine emergents. Dry
  crests carry chestnut oak over mountain laurel. Steep wet banks are "laurel hells", where
  rosebay rhododendron is too dense to walk through. The Knob carries a heath bald of Catawba
  rhododendron. These communities come straight from the generator's `wetness`, `curvature`,
  `aspect` and `slope` masks (Appendix C), and the map is coloured by them.
- **Its history shows on the ground, with no text.** American chestnut was roughly a
  quarter of these forests until the blight reached the southern mountains in the late 1920s
  and 1930s. Its rot-resistant trunks still lie on the slopes as silver-grey "chestnut
  ghosts", and its root sprouts still come up as shrubs and die back. The coves that were too
  steep to log (Joyce Kilmer, Albright Grove) kept their 400-year-old poplars. Poplar Cove is
  one of those.
- **Views are rare, and that is the point.** The Appalachian Trail's nickname is "the green
  tunnel". Under a 35-45 m summer canopy you can see 30-60 m. You see the land only from
  outcrops, balds and overlooks. We checked every view against the terrain and a canopy model
  (Appendix A), so the lookouts work and the rest of the forest is honestly blind.

## Season, light, weather
**Mid-June (about June 15), golden hour, clear, humid.** The canopy is fully out and still
fresh green. Mountain laurel is in late bloom (white-pink) on the crests. Catawba
rhododendron is at peak (magenta) on the Knob, the way it peaks in the first half of June on
Newfound Gap Road and at Roan. Rosebay rhododendron is in bud, with its first white trusses
along the creek (it blooms from late June into July). Hay in the estate's meadow stands
0.6-0.9 m, before the first cutting. We use the existing `golden` LOOK (`mansion.py`: sun 19°
up from just south of west), so the house is not rebaked. The low western sun runs straight
up the west-flowing creek. The creek corridor and the west-facing falls glow gold while the
cove floor sits at about a fifth of open light.

**Haze, not fog.** The blue is real. Oaks, poplars and conifers emit isoprene and terpenes,
which form a scattering aerosol. Natural visual range in the Smokies is about 130-145 km
(80-90 mi). Summer averages in 1999-2003 were around 32 km (20 mi), and they have since
improved. We set aerial perspective to a 32 km summer visual range (extinction 3.912/V, about
1.2e-4 per m). That gives transmittance of 0.89 at 1 km, 0.69 at 3 km, 0.38 at 8 km and
0.16 at 15 km. Inside the 1.3 km playable area the air is effectively clear, and the
layered, ever-paler ridgelines appear only in the backdrop and the horizon band. The haze
colour depends on the sun angle: blue (#8FA6C4) away from the sun, peach (#E6C49A) toward it.

## Goal and arc (6-10 min)
**Goal: reach the Gap.** The Gap is a saddle in Laurel Ridge 1.2 km south of the gate, at
+87 m. There a parkway-style road crosses at a stone-walled overlook. What happens there (a
car, a ride) is open. Every trail goes to the Gap. You can't see it from the gate: you hear
the falls below and follow worn trail. The arc runs: the meadow (exposed, about 18 s) → the
green tunnel (choose a route) → a lookout or the creek → the Gap.

## Layout (estate frame: x east, y north, z = lawn; see map.svg)
The playable area is about 1.3 x 1.25 km (x -700..600, y -62..-1300). The terrain square is
1536 m (terrain local = estate + (0, 810)), spanning estate y -1578..-42. Its north 20 m
underlaps the hedge, so that strip is clipped or held at lawn height. The 4.6 km backdrop
ring needs a flat hole over the estate lawn rect (x ±90, y ±80), with the horizon band beyond. If the gate is at 1,040 m above sea level (3,410 ft), the creek is at 884-924 m
and the Knob at 1,283 m. Linville Gorge's Wiseman's View is at 1,036 m and the river runs
460 m below it. Our cove is a third of Linville's length and nearly 400 m deep.

| landmark | where (x, y) | z | what |
|---|---|---|---|
| Gate, meadow | (20, -62) | 0 | The hay meadow runs 110-130 m to the forest edge. The estate road turns east along the bench. |
| Gate Rock | (-40, -205) | -7 | An 18 m mossy gneiss ledge at the bench rim, where the creek trail steps down. You get no view here (checked). |
| Poplar Cove | (10, -380) | -68 | A tributary hollow of old-growth tulip poplar, 1.5-2 m thick and 40-48 m tall. |
| Laurel Fork Falls | (-92, -658) | lip -116 | A 16 m drop facing west into a plunge pool (450 m², 2-3 m deep). It is built with the proposed `knicks` hook. |
| Footlog | (-155, -672) | -133 | A 16 m sawn log with a handrail over the 6 m creek (the `stats.json` ford). |
| Hemlock Hollow | (-260, -900) | -53 | A north-facing draw under hemlock and rosebay, climbed by switchbacks to the Gap. |
| Raven Rock | (384, -880) | +178 | A rock shoulder at the south-west end of the 22 m Raven Rock cliff band on Raven Spur. **From this point the house's upper floor is visible at 960 m (checked).** |
| The Knob | (466, -1068) | +243 | A heath bald about 140 m across, and the square's high point. **The checked view is from its west rock (384, -1060): the house at 1.13 km.** A 4-5 m gneiss summit rock (a prop you climb) puts the eye above the 4 m heath for the horizon. The far band is unchecked but follows from the geometry. |
| Painted Rock | (162, -1018) | +174 | An outcrop below the crest, reached by a 130 m spur trail. **Sees the house, 1.03 km.** |
| The Gap | (-300, -1218) | +87 | The exit: overlook wall, parkway. |

### Routes (gate to the Gap; run 6.8 m/s, walk 3.4, crouch slower)
| route | path | length / time | why take it, what it costs |
|---|---|---|---|
| **A. Down the creek** | Gate Rock → Poplar Cove → the creek (-100) → the north bank to the falls → a root-and-rock scramble down beside the falls (about 40 m) → the footlog → Hemlock Hollow switchbacks → the Gap | 1.76 km, down 133 m then up 220 m; 6-7 min | Under the canopy all the way. The creek masks your noise (and theirs). The low sun lights the creek corridor, which is the only long sightline (60-120 m along the channel). The falls scramble and the footlog are single-file. From the rims the creek can't be seen at all: the canopy closes over a 6 m creek (checked from all three lookouts). |
| **B. Along the ridge** | East up Raven Spur → Raven Rock → the Knob → the crest trail west → (spur to Painted Rock) → the Gap | 1.92 km, up 245 m; 5-6 min | Dry footing and an open oak understory, so it's the fastest, and you get the views. You are seen at 60-80 m under the oaks and across the whole bald. **Wave 2 comes up the east side onto the Knob from about 4 min**, so it's a race. |
| **C. Through the laurel hell** | Off the spur at (250, -255), down into the cove head, through rhododendron tunnels (about 300 m of crouching), up a bear path to Painted Rock, then the crest to the Gap | 1.43 km (0.81 km off-trail); 6-8 min | Invisible: sight inside a thicket is under 5 m. It's slow and disorienting (people really do get lost in laurel hells). It ends on an exposed lookout. Nobody follows you in unless they heard you go in. |

**Chokepoints:** the meadow (110-130 m in view of the house and gate); Gate Rock's step; the
falls scramble; the footlog (16 m, 2.5 m over the water); the stacked Hemlock Hollow
switchbacks (legs visible from the leg above); the Knob bald; the Gap's open overlook.
**Edges, all natural:**
- N: the hedge and meadow.
- W: the Narrows, a boulder-choked chute of 3-5 m boulders and white water.
- E: Raven Spur drops 40° to the estate road.
- S: the parkway under the crest.
- Everywhere: laurel hells (thicket colliders) and slopes over 40° (14% of the play area, blocked by the slope limit).

## Pursuers and the Grimble
- **Sight rule (new, cheap).** A sight ray is attenuated by the vegetation it crosses:
  notice x exp(-Σ ds/λ), where λ comes from a 2D community map. λ = 3 m in laurel hell, 25 m
  creekside, 35 m in cove forest, 60 m in oak, 150 m on the bald, open in the meadow. Guns
  matter only where the land opens: the meadow, the bald, the creek corridor, the lookouts
  and the Gap. That is legible, and it's true of a summer forest.
- **Wave 1** (about 6, two with guns) comes out of the gate 30-60 s behind you. At the forest
  edge they split. Melee follows your noise and route. Gunners take the ridge trail, because
  it is fast and dry and gives them the open places: the oak crest at 60-80 m and the bald.
  The lookouts see only the estate, not into the forest (checked). So route B is the
  contested one. **Wave 2** (from about 4 min)
  arrives by vehicle on the estate road, east of the spur. They climb onto the crest at the
  Knob, which puts them ahead of a slow ridge runner. Nobody waits at the Gap. A parkway
  vehicle at about 10 min can be a soft limit (optional).
- **Grimble (a friendly forest giant, 2026-10-22).** It lives here now, not in the house: in
  Poplar Cove's old growth on the bench east of the Poplar branch (three.js (62, -380), estate
  (62, -430)), ~70 m off the creek trail across the water. Under 40 m crowns the 7.3 m creature is
  small. It ambles, looks, pats a poplar, rests; it notices the player, waves, follows a little way
  and goes home; it never hurts anyone (`viewer/wild/grimble_wild.js`; CLAUDE.md "Characters").
  (The earlier idea, a pursuer travelling the creek with a wake of shaking treetops, is dropped.)

## Player verbs and systems
Already built: walk, run, crouch, jump, the Noise bus, the senses and search AI, throwables
(rocks as lures), the flashlight (under the hemlocks at dusk), the tablet cameras (feeds of
the gate and meadow).

New:
- terrain ground + 40° slope limit (terrain.md);
- trunk capsules (vegetation.md gap #5);
- thicket colliders with tunnel holes (from the laurel-hell mask);
- wading (creek volume: speed x0.6, splash noise);
- creek noise masking (loudness reduced near water);
- the vegetation sight rule above;
- crouch-in-hay concealment (notice x0.5 in the meadow);
- climb-over for fallen giants: logs ≤ 0.9 m use the existing ~1 m jump; giants of 1.2-2 m use a root-wad or leaning-log ramp (`level.ramps`) or a crawl under the propped end. No mantle verb is needed.

## Signature moments
1. **Into the green tunnel.** You sprint the meadow under the house's windows. Twenty steps
   past the forest edge the light drops to a fifth and the air goes still. The falls is a low
   roar coming up out of the ground.
2. **Poplar Cove.** Grey trunks 2 m thick rise 25 m before the first limb, over knee-high
   Christmas fern. A chestnut ghost, silver and 1.2 m thick, lies across the trail. You climb
   its root wad or crawl under where it rests on a boulder.
3. **The golden creek.** The creek runs west into the low sun and is the only bright thing in
   the cove. The falls is lit from the front. Stand in its spray with the sun behind you and a
   rainbow hangs in the mist; it is physically right, because the antisolar point is ahead of
   you.
4. **The laurel hell.** You crouch in a tunnel of twisted rhododendron stems under leathery
   leaves. Boots go by on the trail 3 m away. You can't see each other.
5. **The view back.** Painted Rock, with the canopy below like a green sea. A kilometre away
   is the white house, its Italian cypresses black spikes, its pool glinting. Behind it the
   ridges go blue, layer after layer. Trucks are moving on the estate road.

## Look and sound
- **Colour.** Leaf and bark colours per species are in Appendix B. Flowers: laurel #F3D9E0,
  Catawba #B65A9E, flame azalea #F08A2A. Grey gneiss with pale lichen and black water
  streaks; moss #4F7A2A on every wet, north-facing surface; leaf litter #4A3A28; tea-clear
  water over gold-brown cobbles.
- **Sound.** The creek, swelling toward the falls. Wood thrush (the flute at dusk, the June
  signature of eastern forests), red-eyed vireo all day, ovenbird, black-throated blue
  warbler in the rhododendron, pileated woodpecker, ravens at the rocks, wind on the bald.

## The gate: a Californian estate in the Appalachians
The estate reads as Californian: olive, Italian cypress, lavender, a white render box. At
1,000 m in western North Carolina (USDA zone 6b-7a, winter lows of about -15 to -20 °C),
olives die. Italian cypress is marginal, while boxwood, yew, lavender and ornamental grasses
are fine.

Recommendation (cheapest first):
1. **Keep the hedge as the climate line.** Inside it is the billionaire's imported Mediterranean
   garden. Outside is Appalachia. From the lookouts the contrast reads as an implant: the dark
   cypress spikes and a too-green lawn. That is environmental storytelling at no cost.
2. **Swap `plant_tree_olive` for the existing `plant_tree_multistem`** (river birch is native).
   It is a one-line change in each zone that places olives, and the user decides.
3. **Build the seam outside the gate.** The lawn ends at the hedge. Then comes the mown-edge
   hay meadow (orchard grass, timothy, ox-eye daisy), then a 10 m edge belt of blackberry in
   flower, sumac, sassafras, black locust and poplar saplings, then the forest wall. The drive
   becomes the gravel estate road and turns east.
4. **Re-render `horizon.py`** (required). The house's horizon becomes forested mountains: this
   cove's own walls near, then layered blue ridges.
5. **Keep `LOOK = "golden"`** (no house rebake).

There is one practical gain: the house's upper south windows already see Raven Rock, the Knob
and Painted Rock (the sight checks are symmetric). The player sees the ridge before escaping.

## Production plan and browser cost
Load it as its own level at the gate (the gate leaves hide the swap). Only a low-LOD estate
silhouette ships with it for the views back: house massing, hedge, cypress cards and pool, at
about 5k tris with a baked colour.

| item | how | cost |
|---|---|---|
| Terrain 1.5 km | `terrain.py` + the parameter set in Appendix A; clipmap from `height16.png` (about 100k tris, 5 draws) or the glTF chunks | cheap; about 3 MB shipped |
| Forest floor | splat from the masks: litter, moss, gneiss, cobble, trail dirt (5 x 1024 sets) | cheap |
| **Canopy shell** (new) | beyond about 120 m, individual trees become one surface: terrain + crown height per community, bump texture, vertex colour (poplar lime, oak dark, hemlock black-green), 16 chunks, about 40k tris; it is what every lookout view is made of | cheap, and the key saving |
| Trees near | `trees.py` species (Appendix B), instanced; LOD0 5-6k within 25 m (measured to the crown, so a 45 m poplar's crown is rarely LOD0), LOD1 1.5k to 60 m, LOD2 0.5k to 120 m, then the shell | **expensive**: about 250k tris |
| Understory | rhododendron and laurel clumps (LOD0 3k under 12 m, 300 beyond), fern clumps within 25 m, doghobble | expensive in fill; about 100k tris |
| Water | the generator's river mesh + `sky.js` water shader; a falls sheet card (scrolling, additive mist like `fire.js`); the plunge pool | cheap |
| Props | boulders (cove boulder fields, the creek), chestnut ghosts and blowdowns with root wads, footlog, stepping stones at the 3 small fords, outcrop slabs on the lookouts, overlook wall, trail log-steps | moderate; about 40k tris |
| Light | outdoor vertex bake as for the grounds. Generator add: cast the canopy shell into the numpy light pass, so the floor gets about 20% light with sunflecks and the gaps and creek get full sun | cheap offline |

The estimate is about 450-500k tris at peak (the house peaks at 501k) and about 160-200 draw
calls (house mean 276).

GPU textures come to about 190 MB:
- 3 shared 2048 leaf atlases: 66 MB;
- impostors for 6 species at 1k: 66 MB;
- terrain sets: 30 MB;
- bark, shell and bake: the rest.

Download is about 15 MB (the house is 13.3 MB). The real risk is fill and overdraw from
alpha cards near the eye. The vegetation spike's forest test ran SwiftShader at 3 fps. Budget
foliage by screen coverage and quality level.

## Risks
- **Overdraw** under a closed canopy and in thickets (above). Weak hardware may need ferns
  off and a shorter LOD0 range.
- **Generic trees.** A poplar, an oak and a buckeye are recognised by their leaves. That needs
  the twig-card baker (vegetation.md gap #3) and a long-needle card for white pine. Without
  them it reads as "a forest", not this forest.
- **Getting lost** in the green tunnel. Trails must read: worn dirt, root steps, log
  water-bars, blue paint blazes on the side trails (marks, not text). The falls' roar and the
  ridge's sky light serve as compasses.
- **The views are fragile.** The checked margins are 1-5 m. Re-run the sight check after
  every terrain change (sample the terrain plus the canopy model of Appendix A), and keep the foreground of
  each lookout heath or talus (real overlooks are kept open by vista clearing).
- **Hemlock realism.** Since the early 2000s the hemlock woolly adelgid has killed most untreated
  hemlocks in the Smokies; Usis, the record at 52.8 m, died months after it was measured. Healthy hemlocks match
  the treated stands the park keeps. The user might want a few grey hemlock snags as an
  honest detail.
- **Generator issues found in the test** (Appendix A): pads have no reach; cliffs can't make
  river steps; switchback cut and fill reaches 26-29 m.

## References
Real places:
- Joyce Kilmer Memorial Forest, NC: tulip poplars over 30 m visible height, 15-20 ft girth, about 400 years old.
- Albright Grove and the Fork Ridge Tuliptree (58.5 m, the tallest known broadleaf in temperate North America), Great Smoky Mountains.
- Boogerman Pine (57.6 m) and Longfellow Pine (56 m) in Cataloochee; the Usis hemlock (52.8 m).
- Linville Gorge: Wiseman's View at 3,400 ft with the river about 1,500 ft below; Hawksbill; Table Rock; Linville Falls, 90 ft.
- Smokies falls: Grotto 25 ft (7.6 m), Mouse Creek 45 ft (14 m, a tributary falling into Big Creek), Laurel 80 ft, Ramsey Cascades about 100 ft.
- Big Creek and Midnight Hole; Kephart Prong footlogs.
- Craggy Gardens, Roan and Andrews Bald (heath and grassy balds, June rhododendron).
- Blue Ridge Parkway overlooks and their vista management; Shenandoah's Whiteoak Canyon and Old Rag.

Science: NPS Great Smoky Mountains air quality; the NC regional haze plan (visual range);
blue haze from isoprene and terpenes.

Art and games: Asher Durand's *Kindred Spirits* and Frederic Church's Hudson River school
haze; *Firewatch* (wordless landscape and long views); *The Last of Us Part II* (dense forest
stealth).

---

## Appendix A: driving `terrain.py` (checked in a scratch run, 1.5 m, 19 s)
Every number below comes from a 1.5 m run of `terrain.build(**overrides)` with the
proposed `knicks` hook patched in (finding 2). All of the data needed to reproduce the run is
listed here. Coordinates are in the estate frame; add (0, 810) for terrain local.

**Globals:**
- `seed=11, size=1536, cell=1.5, base=-55, tilt=(0.03, 0.04)`: the east and north edges sit higher, so the bench drains south into the cove and the creek drains west;
- `shape_jitter=28`;
- `detail`: `low_amp=16 / 280 m`, `high_amp=28 / 320 m`, `mountain=(0.1, 0.7)`, `warp 60 / 600 m`;
- **erosion for old, rounded mountains:**
  - `fluvial k=0.018, iters=50, diffusion=0.8`: hillslope diffusion rounds the crests;
  - `droplets per_cell=0.15`: the 0.8 default rills the slopes into badlands at 1.5 m;
  - `thermal talus_deg=36`;
- `hydro`: `river_area=8e4, width=(2.5, 12), bank_drop=0.25, bank_w=5, bank_deg=18, lake_min_area=300, lake_min_depth=1.5, freeboard=0.2, beach_w=3`;
- `palette` (linear), for the forest floor: grass→moss `(0.045, 0.075, 0.025)`, dry→litter `(0.13, 0.085, 0.045)`, alpine→heath `(0.05, 0.07, 0.035)`, rock→gneiss `(0.20, 0.20, 0.18)`, gravel→cobble `(0.22, 0.19, 0.14)`, mud→creek bed `(0.12, 0.09, 0.05)`, dirt→trail `(0.10, 0.07, 0.04)`.

**Control shapes** (points are x, y, height or depth, base width; width ≥ 4x height):

| shape | points |
|---|---|
| ridge `laurel_ridge` | (-900,-1180,175,1000) (-560,-1200,160,950) (-300,-1215,125,850) = the Gap, (-80,-1190,195,1000) (60,-1175,215,1050) (290,-1120,245,1100) (470,-1070,270,1150) = the Knob, (700,-1110,245,1100) (900,-1150,220,1000) |
| ridge `raven_spur` | (470,-1070,270,700) (455,-860,210,620) (430,-650,165,560) (360,-420,100,480) (250,-230,42,380) (150,-120,8,240) |
| valley `cove` (bowl) | (430,-560,20,420) (250,-600,45,700) (0,-650,55,900) (-400,-700,58,900) (-900,-740,60,900) |
| valley `gorge` (inner) | (320,-590,8,100) (120,-620,24,180) (-100,-660,32,220) (-450,-705,36,240) (-900,-745,38,240) |
| valley `poplar_branch` | (-30,-170,6,110) (0,-320,20,200) (55,-480,26,230) (95,-600,8,160) |
| valley `hemlock_hollow` | (-320,-1110,8,160) (-265,-930,24,220) (-200,-760,12,200) |

**Hooks:**
- **cliffs** (name: height, points, side):
  - `falls`: 14 m, (-80,-720) (-92,-660) (-100,-600), side +1, edge 1.5, talus 45°;
  - `raven_rock`: 22 m, (418,-735) (420,-800) (430,-860), side -1, edge 3, talus 40°;
  - `painted_rock`: 18 m, (80,-1022) (132,-1020) (185,-1010), side +1, edge 2.5;
  - `knob_face`: 30 m, (415,-1050) (465,-1036) (515,-1048), side +1, edge 2;
  - `gate_rock`: 18 m, (10,-212) (-40,-205) (-90,-200), side +1, edge 1.5, talus 42°.
  - All use back 15-25 m, end_fade 18-30 m, jitter 1.2-3 m.
- **knicks** (proposed): `laurel_falls`, height 16, width 170, lip 4, fade 60, along
  (-88,-657) (-130,-664) (-200,-680) (-330,-695) (-450,-705) (-620,-725) (-900,-745); plunge
  pool at (-104,-662), r 15, depth 5. The recipe, run after erosion and before cliffs:
  ```
  pts = spline(points, 3); d, _, s, _ = poly_field(grid, pts, width/2)
  t = clip(d / (width/2), 0, 1); across = (1 - t*t)**2
  along = smoothstep(0, lip, s) * (1 - smoothstep(total - fade, total, s))
  H -= height * across * along          # where d is finite
  # after cliffs: H -= depth * (1 - (r/R)^2)^2 inside the pool disc, so hydrology makes the lake
  ```
- **pads:**
  - `gate`: (20,-95), r 32, falloff 30, height 0 (it meets the lawn);
  - `gap`: (-300,-1218), r 24, falloff 16.
  - **Lookouts are not pads** (see below).
- **paths** (`ford=True`; `reach` small so trails don't refill cliffs):
  - `creek_trail`: w 2, shoulder 3, max_grade 0.22, smooth 24, reach 16:
    (20,-100) (-20,-150) (-62,-225) (-48,-330) (-12,-440) (32,-540) (58,-596) (10,-603)
    (-50,-612) (-88,-616) (-122,-622) (-146,-642) (-155,-672) (-162,-702) (-205,-775)
    (-300,-805) (-205,-870) (-320,-925) (-220,-990) (-330,-1050) (-250,-1110) (-320,-1165)
    (-300,-1215);
  - `ridge_trail`: w 2, shoulder 3, max_grade 0.24, smooth 30, reach 14:
    (20,-100) (110,-130) (200,-200) (280,-300) (340,-400) (388,-520) (415,-640) (428,-730)
    (436,-800) (450,-880) (458,-990) (466,-1065) (360,-1108) (240,-1140) (120,-1158)
    (62,-1160) (-60,-1185) (-180,-1205) (-300,-1215);
  - `painted_spur`: w 1.5, max_grade 0.30, smooth 12, reach 10: (185,-1152) (170,-1100)
    (180,-1060) (163,-1027).
  - Route C is **not** a corridor. It is a thicket-mask lane (a 45 m band in the laurel-hell
    mask, with tunnels authored inside): (250,-255) (262,-340) (300,-460) (318,-575)
    (300,-700) (255,-820) (200,-930) (175,-990) (163,-1027). As a corridor it cut a 20 m scar
    across the cove head.

**Results.** Heights run -159 to +254 m. Slope is p50 27.6°, p90 40.6°. There is 2.7 km of
carved creek 2.5-9.1 m wide (6.0 m at the footlog ford, 9 m at the west edge). The creek
gradient is about 4% plus the falls. Four fords: the footlog, and three of 2.5-2.8 m where
the Hemlock Hollow switchbacks cross its branch, at (-283,-904), (-271,-826) and (-270,-792),
which get stepping stones. One lake: the plunge pool, 450 m² at -133.1. Trails:
- creek: 1.76 km, grade p50 21%, cross-slope p99 22°;
- ridge: 1.92 km, grade p50 22%, p99 40%, cross-slope p99 12°.

**Sight checks.** These are line-of-sight samples against the terrain plus a canopy model.
Canopy is 35 m in coves, 25 m above +120, 15 m on dry crests, 4 m on laurel slicks (over 33°,
convex, above +90) and on the bald, 8 m on talus within 110 m of a cliff, and 0 in the meadow.
The outcrop counts as open rock for 22 m. The house's upper floor (z 7) is visible from:
- Raven Rock (384,-880): 960 m, margin 3.0 m;
- Knob west rock (384,-1060): 1,127 m, 1.2 m;
- Painted Rock (162,-1018): 1,031 m, 4.6 m.

Out of 40k probe cells at 6 m, 917 see the house, all of them on the upper north face of
Laurel Ridge or the spur's west face. Hidden from all lookouts: the footlog, the plunge pool,
the meadow (behind the bench treeline), each other and the Gap. From Gate Rock and the meadow
edge you can see nothing across the cove. That is the green tunnel, and the brief is built on
it.

**Generator findings (fix before building):**
1. **`apply_pads` has no reach.** `bank_clamp` runs over the whole map, so a pad on a summit
   or lookout raises every slope steeper than 33° within hundreds of metres. In the test a
   +180 m lookout pad buried the creek 440 m away under 12 m of fill. Add `reach` to pads as
   paths have. (This also affects the demo's overlook pad.)
2. **Cliffs can't make a river step.** The hook carves down and then trench-fills at 2°. Below
   a gently graded channel (4%) the foot fills back in, and the 14 m falls came out as a ramp.
   A macro step is also erased by erosion. A **`knicks` hook** (post-erosion, pre-cliffs:
   lower a channel-following band by `height` below a lip, with a taper across of
   (1-t²)², `width` 170, faded at the far end; plus a plunge basin after cliffs) produced the
   16 m falls and its pool. The test monkey-patched it in (`run_knick.py`, about 25 lines):
   `laurel_falls`: height 16, width 170, lip 4 m, along (-88,-657)→(-900,-745), pool r 15 m
   depth 5 at (-104,-662).
3. **Switchback cut and fill reached 26-29 m** on the 35-40° faces. Add legs along the
   contours until it is ≤ 3 m.
4. `albedo()` hard-codes rock at 36-48°. Forested Appalachian slopes reach 45°, so expose it
   as a parameter (rock above 50° or on cliffs only).
5. Add the canopy shell as an occluder to `light()`.

## Appendix B: species for `trees.py` (and understory)
Card sources: today's broadleaf card is jacaranda fronds. That pinnate frond actually suits
**hickory**, but poplar, oak, maple and buckeye need the twig-card baker. Hemlock reuses the
fir sprays (flatter, smaller, drooping leader). White pine needs a long-needle card. Tall
trees change impostor texel density: a 45 m poplar gets about 3 px/m at 1k frames, so ship the
2k atlas for the big two or rely on the canopy shell.

| species | kind | height / DBH | crown | leaf (colour) | bark | where | share |
|---|---|---|---|---|---|---|---|
| tulip poplar | broadleaf | 40-48 m (hero 52) / 1.0-2.0 m | clear bole to 25 m; narrow tall ellipsoid, rx 7 rz 9 at the top | 4-lobed tulip leaf, 12 cm, #8DB04A | grey, interlaced furrows | coves, hollows, lower north slopes | 30% |
| eastern hemlock | conifer | 30-38 m / 0.8-1.3 m | broad cone from 5 m, drooping leader, flat lacy sprays | 1.5 cm needles, #2F4A3A, white undersides | cinnamon-grey scaly ridges | creekside (≤ 40 m), north faces | 12% |
| northern red oak | broadleaf | 28-34 m / 0.7-1.2 m | broad rounded, crown base 10 m, rx 9 rz 7 | pointed lobes, #3F5E2A | dark, "ski-track" stripes | mid and upper slopes, convex, S/W | 18% |
| chestnut oak | broadleaf | 18-25 m / 0.5-0.9 m | crooked, open | wavy-edged, #6B8A36 | very deep blocky furrows | dry crests, outcrop rims | 10% |
| hickory (pignut, shagbark) | broadleaf | 25-30 m / 0.6 m | narrow oval | compound (existing frond card), #4F7230 | shagbark strips | mid slopes, convex | 7% |
| sugar maple | broadleaf | 25-30 m / 0.6-0.9 m | dense oval, crown base 8 m | palmate 5-lobed, #4E7A2C | grey plated | rich coves | 8% |
| yellow buckeye | broadleaf | 25-35 m / 0.7-1.2 m | rounded, crown base 12 m | 5 palmate leaflets, #6E9438 | smooth grey, sycamore-like plates | high coves (wet, above -40) | 6% |
| eastern white pine | conifer | 35-45 m, emergent / 0.8-1.2 m | tiered horizontal limbs, windswept top | 5-needle 10 cm bundles, #4D6E4A | dark furrowed | south slopes, spurs, emergent above the oaks | 5% |
| understory: sourwood, dogwood, striped maple, holly, **chestnut sprouts** | broadleaf/shrub | 3-12 m | small | per species | | under the canopy | 4% |
| **rosebay rhododendron** | shrub (sinuous multi-stem, 8-15 cm stems) | 3-6 m (to 9) | layered, interlocking | 15-25 cm leathery whorls at the tips, #2E4A2C; buds, first white trusses | grey-brown, twisted | laurel hell and creekside | mask |
| mountain laurel | shrub | 2-4 m | gnarled, dense | 5-10 cm glossy, #3F5A2E; white-pink bloom clusters | red-brown, shreddy | dry crests, slicks, lookout rims | mask |
| Catawba rhododendron | shrub | 1.5-3 m | dome | 10 cm, magenta trusses #B65A9E | | the Knob bald | mask |
| flame azalea | shrub | 2-3 m | open | orange flowers #F08A2A | | bald edges, sparse | accent |
| doghobble | clump/shrub | 1-1.5 m, arching | | evergreen, glossy | | creek banks | mask |
| ferns: Christmas, hay-scented, cinnamon, maidenhair | clump (existing fern, tinted) | 0.4-1.2 m | | dark evergreen, lime carpets in gaps, tall in seeps | | cove floor, gaps, seeps | ring within 25 m |
| moss | **material, not geometry** | | | #4F7A2A | | rocks, logs, roots: shader term = up-facing x wetness x north aspect | |
| dead: chestnut ghosts, blowdowns, snags | props / a no-card `snag` kind | logs 15-25 m long, 0.5-1.5 m thick; root wads 3-5 m | | | silver, barkless | chestnut on upper slopes, blowdowns in coves | 3-6 logs/ha |

## Appendix C: masks → placement
Masks are on 0..1 scales from `masks/*.png`: wetness w, curvature c (0.5 flat, below = concave),
aspect a (downslope bearing), slope s, distance to water r, height z.

| community | rule (in order; later wins) | density (stems ≥ 20 cm) | map |
|---|---|---|---|
| oak-hickory (default) | everything else; S/W aspects (a 140-290°) or c > 0.54 | 200/ha | 51% |
| cove / mesic | (c < 0.47 or w > 0.55) and not S/W, **or** N/NE/E aspect below +160 | 220/ha, 60/ha emergents | 30% |
| dry crest | c > 0.56 and z > +120 | 150/ha, laurel understory | 9% |
| creekside | r < 28 m | 180/ha: hemlock + rosebay + doghobble | 3% |
| laurel hell | s 22-46°, w > 0.33, N/NE/E, r < 220 m; plus the authored route C band (45 m) | thicket 100%, collider; tunnels authored | 5.5% |
| laurel slick / talus | s > 33°, c > 0.5, z > +90, and below cliffs | shrubs, scattered 8 m trees | (keeps views open) |
| heath bald | the Knob, about 140 m irregular | Catawba + laurel, grass | |
| rock | s > 48°, cliffs | lichen, moss in cracks | 1.6% |

Logs go where chestnut stood (upper slopes, c > 0.5). Blowdowns and boulder fields go in
coves (high sediment, c < 0.5). Ferns ring the player at 25 m and are densest in coves and
gaps. Moss goes on every prop with an up-facing, wet, north-facing surface.
