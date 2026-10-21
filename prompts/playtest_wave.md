# Playtest-and-improve wave (instructions for a sub-agent)

Twelve agents work at once, each on one workstream (yours is in your task), each in its own git
worktree. The user's main complaint: **the interactive items don't serve much of a purpose**.
Other things they named: light switches don't really work (a switch should toggle all lights in
its room), blind/curtain switches sit next to light switches, some vases and books can be picked
up and others can't, you can't go outside, and it isn't obvious what's usable. They want
playtesting to find many more problems like these, and fixes.

Ground rules from the user: no notes, lore or story text in the game; the game has no goal or
win condition yet (don't add one); the Grimble's swipe only knocks you down (no fail state);
power starts ON; keep the Grimble's shrink-and-crawl. Things should be useful in the sandbox:
against the Grimble (hide, distract, see it coming, keep it out of sight) and in the house's
systems (power, light, locks).

Read `CLAUDE.md`, `prompts/interactivity.md` (the interactivity contract) and the files your
workstream owns before changing anything.

## Your worktree
- You start in a fresh git worktree of the repo (its own branch). Run
  `tools/worktree_setup.sh <port>` from its root first (your port is in your task); it shares the
  main checkout's run slots, caches and node_modules and serves your worktree on that port. Then
  `export GT_BASE=http://localhost:<port>` so `viewer/tools/*.mjs` load YOUR files, e.g.
  `GT_BASE=http://localhost:<port> node viewer/tools/hunt_play.mjs build/x 60 ring`.
  Open `http://localhost:<port>/viewer/?level=mansion` URLs in your scripts the same way.
- **Machine limits (shared by all 12 agents):** Blender builds queue themselves through
  `blender/tools/slots.py` (2 house builds, 4 asset builds); browsers through
  `build/locks/browser_0..2` (take one with mkdir, rmdir when done, also on errors; the tools
  do this). Run ONE Blender command and ONE browser at a time yourself, never in the background
  in parallel. A full house rebuild (`build_level.py` with export) takes ~20 min: batch your
  level changes and rebuild rarely. Never run a full bake; only the lighting workstream may run
  `bake.py ... 64 --rooms <room>` draft bakes, one room at a time. Layout checks: `&bake=0`.
- Commit your work on your worktree's branch (small, descriptive commits; end each message with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`). Don't push, don't merge, don't
  touch the main checkout. The orchestrator merges the twelve branches, rebuilds and bakes.

## Staying mergeable
- Edit only your workstream's files, plus the smallest possible hooks elsewhere. In shared files
  (`viewer/index.html`, `viewer/interactables.js`, `blender/levels/rooms/*.py`, `plan.py`) keep
  changes small and in their own clearly commented block; don't reformat, rename or reorder code
  you don't own. If you need something from another workstream's file, add a tiny hook and say
  so in your report.
- Shared contracts: `window.__noise.emit({position, loudness, source})` for sounds the Grimble
  can hear; `window.__signals` for state; the interact/react custom properties in
  `prompts/interactivity.md` (extend them there if you add a type); `player.hidden` (true while
  the player is in a hiding spot: the Grimble can't see them); `window.__sfx.play(name, position)`
  for sound effects (the audio workstream provides it; call it with `?.` so it's optional).
- Performance budget (`viewer/tools/budgets.json`): no new real-time lights in the engine, keep
  draw calls and downloads modest. Run the existing tests that touch your area
  (`viewer/tools/*.mjs`: signals, drawer, keycard_door, inventory, throw, movement, tour, walls,
  jump_run) before you finish; `walls.mjs` must report 0 impossible positions if you changed
  geometry or colliders.

## Playtest like a player
Play your area in the real engine (scripted Playwright runs from the player's eye, screenshots),
before and after. Note problems outside your workstream in your report instead of fixing them.

## Report (your final message)
What you changed and why (files, commits), what you tested (commands, results, image paths),
what the orchestrator must do when merging (rebuild? bake? which rooms?), hooks you added in
others' files, and the problems you found that belong to other workstreams.
