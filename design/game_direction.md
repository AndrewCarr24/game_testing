# Game direction (as of 2026-10-21, from the user)

Working shape: **a home-invasion escape game**. Nothing here is final; it records what the user has
said so far.

## Phase 1: get out of the house
- The player is in the mansion (`blender/levels/plan.py`: ~52 x 40 m, two floors, a courtyard,
  galleries, side rooms; grounds with a lawn, terrace, perimeter hedge, pool, pool house, motor
  court and a gated drive) when **invaders** start arriving in waves: ~6 at first, then 20, then
  50. Still in the house after the 50: nearly impossible to win.
- Invaders kill you. Some have guns, some bats, knives, etc.
- The goal is to get out. The front door or a side door: the invaders outside spot you and shoot
  you. **The safe way out is a secret passage**: it leads under the house to an **armory**, and
  on to the **pool house**.
- At the armory the player has weapons to fend the invaders off. From there they may go back into
  the house and fight, or just leave: through the estate's gate (it has doors) **into the
  wilderness**.

## Phase 2: the wilderness
Beyond the gate. Chosen (2026-10-21): **a living Blue Ridge mountain forest, unburned** —
Laurel Fork Cove (design/wilderness/blue_ridge/): tall cove hardwoods and hemlock on steep
slopes, ferns and moss, fallen giants; a ridge with rock outcrops and long views back to the
estate. The user wants **a much larger river** (not a creek) that **leads the player to a
town**. No fog gimmick, no fire; a cabin may come later.

## The road
A real, drivable two-lane road (concrete/asphalt with lane paint) leaves the estate's gate and
winds down the valley along the river to the town. The road and the river both lead there.

## The town
Downstream along the river and the road. Not the goal of the game, just a town: it seems safe at
first, but it turns out the town is in cahoots with the invaders. **Modern and quaint** (no
billionaire lives near an old mill town): a fast-food place, a gas station, maybe a small museum,
maybe a video store, and a **very cinematic bar**.

## The Grimble
A 7.3 m cloaked creature (built; `viewer/grimble*.js`). It becomes an **easter egg**: if the
player stays in the house long enough, the Grimble comes. (It walks in over the west lawn from
the horizon today.)

## Rules that stand
- No notes, lore or story text in the game (environmental storytelling only).
- It ships as an online three.js game: the web performance budget applies (viewer/tools/budgets.json,
  CLAUDE.md "Web performance budget"); no per-room real-time lights; baked lighting.
- The user works on a Mac: tools must run on macOS (Blender headless, numpy, node/playwright).
  Gaea is Windows-only; The Grove (Blender add-on) and SpeedTree (subscription) run on Mac.
- Systems already built that the invaders and the wilderness can reuse: the Grimble's senses and
  search AI (viewer/grimble_hunt.js: sight cone, notice meter, hearing with wall muffling, search,
  doors block sight), hiding spots, noise lures and devices, power and darkness, locks and keys,
  the tablet's cameras, going outside (exterior doors, walkable grounds with colliders), sound.
