# Wave 2 (instructions for a sub-agent)

Eight agents work at once, each on one workstream (yours is in your task), each in its own git
worktree of the `wilderness` branch. Read `CLAUDE.md`, `design/game_direction.md` (what the game
is now: a home-invasion escape; invaders kill you; a secret passage -> armory -> pool house; the
gate -> the Blue Ridge wilderness; a large river leads to a town that seems safe but is in cahoots
with the invaders; the Grimble is an easter egg) and the files your workstream owns.

## Your worktree
- Run `tools/worktree_setup.sh <port>` from its root first (your port is in your task); it shares
  the main checkout's run slots, caches, node_modules and the wilderness plant kit
  (build/wilderness/veg, ground: read-only for you unless the kit is your job) and copies the
  generated Laurel Fork world into your worktree. Then `export GT_BASE=http://localhost:<port>`
  for `viewer/tools/*.mjs`. The wilderness runtime is `viewer/wild.html` (+ `viewer/wild/*`,
  levels in `blender/wilderness/levels/`, docs in `design/wilderness/blue_ridge/`); the house is
  `viewer/index.html?level=mansion`.
- Machine limits (shared by all): Blender builds queue through `blender/tools/slots.py`;
  browsers through `build/locks/browser_0..2` (mkdir to take, rmdir after, also on errors). One
  Blender command and one browser at a time yourself. A house rebuild (`build_level.py`) takes
  ~15-20 min: batch changes. Never run a house bake.
- Commit on your branch (small commits; end each message with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`). Don't push, don't merge, don't
  touch the main checkout. The orchestrator merges.

## Staying mergeable
- Edit only your workstream's files plus the smallest commented hooks elsewhere. Shared files
  (`viewer/index.html`, `viewer/interactables.js`, `viewer/player.js`, `viewer/wild/main.js`,
  `blender/wilderness/levels/laurel_fork*.py`, room modules) get small, clearly marked blocks.
- No notes/lore/story text in the game. The web performance budget applies (no per-room
  real-time lights; measure with the bench tools; say what you cost).

## Combat contract (the invader and weapon workstreams share it)
- `window.__combat` (viewer/combat.js, owned by the player-weapons workstream; the invader
  workstreams code against this interface and may stub it until merged):
  `register(target)` where a target is `{ id, kind: 'player'|'invader', team, position() ->
  Vector3, radius, height, health, maxHealth, alive, hit(damage, { from, dir, weapon, part }) }`;
  `attack({ from, origin, dir, weapon, range, arc, damage })` melee sweep -> hits;
  `shoot({ from, origin, dir, spread, range, damage })` hitscan ray vs the walls
  (`window.__colliders` / level colliders) and targets -> hit or miss point (for tracers, impacts,
  noise); `on(event, fn)` events `hit`, `kill`, `shot`, `playerDown`.
- The player: health ~100, regenerates slowly out of combat; a gunshot ~25-40, a bat ~35, a knife
  (theirs) ~45; at 0 the player dies (death screen, restart the run; for now a simple fade and a
  restart button). The Grimble's knockdown stays a knockdown.
- Invaders: health ~100; the kitchen knife ~55 a stab, ~100 from behind unseen (a stealth
  takedown); they react to being hit (stagger, call out, flee if badly hurt).
- Every gunshot is a loud `window.__noise.emit({position, loudness: 2.5, source: 'gunshot'})`;
  melee hits ~0.6. Sounds through `window.__sfx?.play(name, position)` (names: gunshot, bat_swing,
  bat_hit, knife_swing, knife_hit, body_fall, invader_shout, invader_alert, ...).

## Report (your final message)
What you built (files, commits), how to see it (URL), what you tested (commands, results, image
paths), what the orchestrator must do when merging (rebuild? which levels?), hooks in others'
files, and problems you found in other workstreams.
