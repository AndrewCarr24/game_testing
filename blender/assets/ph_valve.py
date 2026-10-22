"""A bronze handwheel valve on a square plate (the bathhouse): the plunge's drain. A `switch` on
signal `plunge` (the level names it `ph_plunge`); turning it drains the cold plunge and sinks the
slab in its wall (ph_plunge), turning it back raises the slab and refills it. Two of them on the one
signal: one on the cold room's wall by the plunge (any plunge has a drain valve), one on the
secret stair's landing below. The wheel turns 270 degrees in the wall's plane.
Origin: the plate's back centre on the wall surface; the front faces -Y (like ix_switch)."""
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

NAME = "PHValve"
P = dict(name=NAME, plate=(0.22, 0.022, 0.22), wheel_r=0.15, rim_r=0.012, stand=0.075, signal="plunge")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = pc.start(n)
    bronze, dark = pc.bronze(), pc.dark_bronze()
    pw, pt, ph = p["plate"]
    pc.box(f"{n}_Plate", (-pw / 2, -pt, -ph / 2), (pw / 2, 0, ph / 2), dark, col, root, bevel=0.003)
    # the stem out of the plate
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.016, radius2=0.016, depth=p["stand"])
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=__import__("mathutils").Matrix.Rotation(math.radians(90), 3, "X"))
    bmesh.ops.translate(bm, vec=(0, -pt - p["stand"] / 2, 0), verts=bm.verts)
    common.mesh_object(f"{n}_Stem", bm, col, dark, root, smooth=True)

    wheel = common.empty(f"{n}_Wheel", col, (0, -pt - p["stand"], 0))
    wheel.parent = root
    wheel["interact"] = {
        "type": "switch", "signal": p["signal"], "state": False,
        "prompt": "Open the valve", "promptActive": "Close the valve",
        "range": 1.4, "duration": 1.4,
        "travel": {"axis": "z", "angle": 270},
    }
    R = p["wheel_r"]
    pts = [(R * math.cos(2 * math.pi * i / 20), 0, R * math.sin(2 * math.pi * i / 20)) for i in range(20)]
    common.tube_object(f"{n}_Wheel_Rim", pts, p["rim_r"], col, bronze, wheel, closed=True)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        bm = common.box_bmesh((R, 0.012, 0.016))
        bmesh.ops.translate(bm, vec=(R / 2, 0, 0), verts=bm.verts)
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=__import__("mathutils").Matrix.Rotation(-a, 3, "Y"))
        common.mesh_object(f"{n}_Wheel_Spoke{k}", bm, col, bronze, wheel, smooth=False)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.032, radius2=0.026, depth=0.04)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=__import__("mathutils").Matrix.Rotation(math.radians(90), 3, "X"))
    common.mesh_object(f"{n}_Wheel_Hub", bm, col, bronze, wheel, smooth=True)
    return pc.finish(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
