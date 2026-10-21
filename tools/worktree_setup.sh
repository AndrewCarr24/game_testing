#!/bin/bash
# Set up a git worktree of this repo for an agent: share the main checkout's machine-wide run
# slots (build/locks: Blender builds, browsers), its download/geometry caches and node_modules,
# and serve the worktree on its own port so the engine tests load the worktree's files.
#   tools/worktree_setup.sh <port>        (run from the worktree root)
#   then: export GT_BASE=http://localhost:<port>   for viewer/tools/*.mjs
set -e
PORT=${1:?usage: tools/worktree_setup.sh <port>}
MAIN=$(git worktree list --porcelain | awk '/^worktree /{print $2; exit}')
HERE=$(pwd)
[ "$MAIN" = "$HERE" ] && { echo "this is the main checkout, not a worktree"; exit 1; }
mkdir -p build
for d in locks polyhaven ao_cache grimble_cache texture_originals; do
  [ -e "build/$d" ] || ln -s "$MAIN/build/$d" "build/$d"
done
[ -e node_modules ] || ln -s "$MAIN/node_modules" node_modules
if ! curl -s -o /dev/null "http://localhost:$PORT/viewer/index.html"; then
  nohup python3 -m http.server "$PORT" > build/http_$PORT.log 2>&1 &
  sleep 1
fi
echo "worktree $HERE served at http://localhost:$PORT (export GT_BASE=http://localhost:$PORT)"
