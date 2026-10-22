"""Eye-height views of the gas station for viewer/tools/wild_shots.mjs --extra (three.js frame),
from the station's local frame (blender/assets/town2_gas.py): writes build/town/gas/views.json.

  python3 blender/town/gas/views.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
W = json.load(open(os.path.join(PROJECT, "build", "wilderness", "laurel_town", "world", "world.json")))
b = next(x for x in W["town"]["buildings"] if x["id"] == "gas")
OY = W["estate_offset"][1] if "estate_offset" in W else -810
BX, BY, BZ = b["x"], b["y"], b["z"]


def T(x, y, z):
    """local (x, y, z over the forecourt) -> three.js [x, y, z]"""
    return [round(BX + x, 3), round(BZ + z, 3), round(-(BY + y - OY), 3)]


# name: (eye (local x, y, z), look (local x, y, z))
V = {
    "gas_street": ((-2, -34, 1.7), (-3, 0, 3.0)),
    "gas_corner": ((24, -30, 1.7), (-4, -2, 2.5)),
    "gas_canopy": ((-7, -9.5, 1.7), (-6, 3, 1.8)),
    "gas_pump": ((-9.2, -13.0, 1.6), (-3, -6, 1.2)),
    "gas_door": ((-6.5, -1.5, 1.7), (-6.5, 10, 1.4)),
    "gas_inside": ((-6.5, 5.0, 1.85), (-8, 16, 1.2)),
    "gas_counter": ((-3.5, 5.0, 1.85), (2.0, 7.5, 1.45)),
    "gas_coffee": ((-13.6, 4.2, 1.85), (-15.8, 10.5, 1.6)),
    "gas_monitor": ((-1.0, 8.9, 1.85), (3.6, 9.05, 2.05)),
    "gas_restroom": ((-1.0, 12.2, 1.85), (-1.0, 16.5, 1.2)),
    "gas_van": ((14.0, 6.0, 1.7), (6.5, 14.5, 1.0)),
    "gas_west": ((-32.0, -8.0, 1.7), (-14.0, 6.0, 2.6)),
    "gas_coolers": ((-9, 11, 1.85), (-10, 17, 1.2)),
    "gas_back": ((19, 8, 1.7), (9, 15, 1.2)),
    "gas_high": ((40, -55, 24), (-3, 0, 0)),
    "gas_far": ((150, -20, 3.0), (-3, 0, 3.0)),
    "gas_near_lod": ((120, -20, 3.0), (-3, 0, 3.0)),
}
out = {k: {"pos": T(*e), "look": T(*l)} for k, (e, l) in V.items()}
os.makedirs(os.path.join(PROJECT, "build", "town", "gas"), exist_ok=True)
json.dump(out, open(os.path.join(PROJECT, "build", "town", "gas", "views.json"), "w"), indent=1)
print(",".join(out))
