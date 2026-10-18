"""Low outdoor coffee table: a stepped honed-limestone plinth with an overhanging top slab,
styled with a wide ceramic bowl of sedge and a pair of linen-bound books on a teak tray.

Origin: floor centre. Long axis along X. Units are metres."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import courtyard_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common
rbox = cc.rbox

NAME = "CourtyardCoffeeTable"

P = dict(
    name=NAME,
    size=(1.30, 0.78),
    height=0.36,
    top_t=0.06,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    stone, teak, cer = cc.limestone_mat(), cc.teak_mat(), cc.ceramic_mat()
    sand, clay, sage = cc.sand_fabric(), cc.clay_fabric(), cc.sage_fabric()
    leaf = cc.foliage_mat()

    w, d = p["size"]
    h, t = p["height"], p["top_t"]
    # plinth: two stacked blocks, the lower a shadow-gap recess
    rbox(f"{n}_Foot", (w - 0.30, d - 0.20, 0.07), (0, 0, 0.035), stone, col, root, bevel=0.006, uv_tile=2.0)
    rbox(f"{n}_Plinth", (w - 0.18, d - 0.12, h - t - 0.07), (0, 0, 0.07 + (h - t - 0.07) / 2), stone, col, root,
         bevel=0.008, uv_tile=2.0)
    rbox(f"{n}_Top", (w, d, t), (0, 0, h - t / 2), stone, col, root, bevel=0.012, uv_tile=2.0)

    # teak tray with two books
    tz = h
    rbox(f"{n}_Tray", (0.46, 0.30, 0.025), (0.30, 0.04, tz + 0.0125), teak, col, root, bevel=0.004)
    b1 = rbox(f"{n}_BookA", (0.28, 0.21, 0.035), (0.30, 0.04, tz + 0.025 + 0.0175), sand, col, root, bevel=0.003, uv_tile=0.25)
    b2 = rbox(f"{n}_BookB", (0.24, 0.18, 0.028), (0.31, 0.045, tz + 0.025 + 0.035 + 0.014), clay, col, root, bevel=0.003, uv_tile=0.25)
    b2.rotation_euler = (0, 0, math.radians(14))
    # wide ceramic bowl
    prof = [(0.0, 0.0), (0.07, 0.0), (0.075, 0.006), (0.12, 0.04), (0.16, 0.085), (0.165, 0.095), (0.158, 0.098),
            (0.15, 0.094), (0.115, 0.05), (0.0, 0.02)]
    bowl = cc.lathe([(r, z) for r, z in prof], 36, f"{n}_Bowl", col, cer, root, sharp=45)
    bowl.location = (-0.30, -0.05, tz)
    # sedge tuft in the bowl
    cb = bmesh.new()
    uvl = cb.loops.layers.uv.new("UVMap")
    for j in range(4):
        ang = j * math.pi / 4 + 0.3
        right = Vector((math.cos(ang), math.sin(ang), 0)) * 0.17
        cc.add_card(cb, uvl, Vector((-0.30, -0.05, tz + 0.03 + 0.15)), right, Vector((0, 0, 0.15)), "grassB")
    common.mesh_object(f"{n}_Sedge", cb, col, leaf, root, smooth=False)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
