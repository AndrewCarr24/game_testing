#!/bin/bash
# One iteration on the gas station: build + bake + export, refresh the town world (colliders,
# placement), then eye-height shots in the engine (build/wilderness/laurel_town/shots/<label>/).
#   blender/town/gas/cycle.sh <label> [samples] [views]   (GT_BASE: the worktree's server)
set -e
cd "$(dirname "$0")/../../.."
LABEL=${1:-gas}
SAMPLES=${2:-64}
VIEWS=${3:-gas_street,gas_corner,gas_canopy,gas_pump,gas_door,gas_inside,gas_counter,gas_coffee,gas_coolers,gas_back,gas_high}
if [ "$SAMPLES" != "0" ]; then
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python blender/town/gas/make.py -- --samples "$SAMPLES" 2>&1 | grep "\[gas\]\|Error\|Traceback" || true
fi
/Applications/Blender.app/Contents/Resources/5.0/python/bin/python3.11 blender/wilderness/levels/laurel_town.py --steps world 2>&1 | tail -1
python3 blender/town/gas/views.py > /dev/null
bash build/town/gas/restore.sh viewer assets/levels assets/textures assets/models > /dev/null 2>&1 || true
node viewer/tools/wild_shots.mjs "$LABEL" --world laurel_town --qs "${WILD_QS:-&veg=1}" --views "$VIEWS" --extra build/town/gas/views.json 2>&1 | grep -v "^error: Failed to load resource: the server responded with a status of 404" | tail -14
