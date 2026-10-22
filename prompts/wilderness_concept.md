# Wilderness concept (instructions for a sub-agent)

Read `design/game_direction.md` (what the game is) and skim `CLAUDE.md` (how the house and the
grounds are built, the web budget). Then write ONE wilderness concept from the creative lens in
your task.

## The ask
The player escapes the estate through its gate (south drive, `plan.GROUNDS`: the perimeter hedge
at x +-70, y +-62, the drive gap at x 14..25.5 on the south side) into the wilderness. Design what
is out there. Best practice says start from gameplay (where you enter, where you're trying to get
to, 2-3 routes, landmarks visible from afar, chokepoints, where pursuers come from, the world's
edges), then the land. The user's explicit request: **be creative. AI tends toward the modal
answer from its training data (the stock forest with a river and mountains; the stock mansion).
Subvert it.** Your lens is a starting push, not a cage: find the version of it nobody would
expect, that is still defensible as a real place, plays well, and fits a tech billionaire's
estate and a home-invasion horror game. Specific, strange, real beats generic and epic.

Think about: what's the player trying to do out there (reach something? survive until? lose
the pursuers?), how invaders (some with guns: long sightlines are deadly) and possibly the
Grimble (7 m, it came "over the horizon") use the terrain, what makes each route a real choice,
signature moments a player would describe to a friend, how the land itself tells a story with
no text, and what the first 30 seconds past the gate look like. Real geography and ecology make
the best references (name real places, phenomena, land uses); use the web if useful.

Respect what we can build: a browser three.js game (instanced vegetation, terrain chunks, fog,
baked vertex lighting, no per-object real-time lights), authored on a Mac with scripted Blender
+ numpy generators. Say what's cheap and what's expensive in your concept, and how big the
playable area is (aim ~1-2 km across; more as unwalkable backdrop).

## Deliverables (only these files; no code, no Blender, no edits elsewhere)
In `design/wilderness/<your-slug>/`:
- `brief.md`: name; one-line hook; why it isn't the modal answer; the player's goal and the
  run's arc; the layout (zones, routes, landmarks, chokepoints, edges, distances in metres);
  pursuers and the Grimble; player verbs and systems it uses or needs; 3-5 signature moments;
  look (palette, light, weather, time of day, sound); production plan and browser cost (cheap /
  expensive, asset list); risks; references (real places, games, films). 1-3 pages, concrete.
- `map.svg`: a top-down sketch at a stated scale (metres; north up; the gate marked; the estate's
  hedge for reference), routes, landmarks, contours or height notes. Then render it to `map.png`
  (e.g. `node viewer/tools/grid.mjs design/wilderness/<slug>/map.png 1 design/wilderness/<slug>/map.svg`,
  or a tiny playwright script; the browser slots are build/locks/browser_0..2, take one with
  mkdir and rmdir it after).
Your final message: the hook, a 5-line summary, and the file paths.
