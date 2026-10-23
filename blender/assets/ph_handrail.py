"""The secret stair's handrail (the bathhouse): a 40 mm dark bronze bar on the stair's east wall,
0.9 m over the nosings up the flight (16 treads of 0.28 m rising 0.1765 m) and level along the
landing, on five slim brackets to the wall. Origin: on the wall face at the foot of the flight
(the first riser), floor level; the rail runs along +y, 7 cm out from the wall (toward -x)."""
import importlib
import math
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ph_common as pc  # noqa: E402

importlib.reload(pc)
common = pc.common

NAME = "PHHandrail"
P = dict(name=NAME, run=4.48, rise=2.824, landing=0.5, height=0.9, out=0.07, r=0.02, first=0.1765)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = pc.start(n)
    bronze = pc.dark_bronze()
    x, z0 = -p["out"], p["first"] + p["height"]
    pts = [(x, -0.25, z0), (x, 0.0, z0), (x, p["run"], z0 + p["rise"]), (x, p["run"] + p["landing"], z0 + p["rise"])]
    pts = common.fillet_polyline(pts, 0.12, segments=6, closed=False)
    common.tube_object(f"{n}_Bar", pts, p["r"], col, bronze, root, closed=False)
    slope = p["rise"] / p["run"]
    for i, y in enumerate((0.15, 1.2, 2.3, 3.4, 4.4)):
        z = z0 + y * slope - 0.06
        pc.box(f"{n}_Bracket{i}", (x, y - 0.008, z - 0.008), (0.0, y + 0.008, z + 0.008), bronze, col, root)
        pc.box(f"{n}_Rose{i}", (-0.008, y - 0.03, z - 0.03), (0.0, y + 0.03, z + 0.03), bronze, col, root)
    return pc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
