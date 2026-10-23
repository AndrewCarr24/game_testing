"""The diner's preview cameras (build/diner/cams.json, written by build.py in the asset frame) as
wild_shots.mjs extra views (three.js frame) on the diner's site in the built town world:
  python3 blender/town/diner/tools/views.py [--world laurel_town] [--out blender/town/diner/views.json]
then  node viewer/tools/wild_shots.mjs <label> --world laurel_town --extra blender/town/diner/views.json --views d_front,...
Views are prefixed "d_"."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
args = sys.argv[1:]


def opt(k, d):
    return args[args.index(k) + 1] if k in args else d


world = opt("--world", "laurel_town")
out = opt("--out", os.path.join(ROOT, "blender", "town", "diner", "views.json"))
W = json.load(open(os.path.join(ROOT, "build", "wilderness", world, "world", "world.json")))
b = next(q for q in W["town"]["buildings"] if q["id"] == "diner")
oy = W["estate_offset"][1]
ox, oyk = b.get("kit_offset", [0, 0])
cams = json.load(open(os.path.join(ROOT, "build", "diner", "cams.json")))


def three(p):
    u, v, z = p
    tx, ty = b["x"] + (u - ox), b["y"] + (v - oyk)
    return [round(tx, 3), round(b["z"] + z, 3), round(-(ty - oy), 3)]


views = {f"d_{n}": dict(pos=three(c["loc"]), look=three(c["at"]), lens=c.get("lens")) for n, c in cams.items()}
json.dump(views, open(out, "w"), indent=1)
print(f"{len(views)} views -> {out}: " + ", ".join(views))
