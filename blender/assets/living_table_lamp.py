"""Slim ceramic table lamp: a glazed gourd body on a bronze foot with a glowing linen
drum shade. Cheap lathe geometry (about 600 triangles). Origin: centre of the underside;
0.58 m tall. Units are metres.
"""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import living_side_table  # noqa: E402
from lib import common, materials  # noqa: E402

importlib.reload(living_side_table)
lathe = living_side_table.lathe

NAME = "LivingTableLamp"
P = dict(name=NAME, segs=24, glow=1.6)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    ceramic = common.pbr_material("M_Ceramic_Glaze", (0.55, 0.52, 0.46), roughness=0.18)
    bronze = materials.bronze()
    glow = materials.emissive("M_Living_LampGlow", (1.0, 0.78, 0.50), p["glow"])
    seg = p["segs"]
    body = [(0, 0.012), (0.045, 0.012), (0.075, 0.05), (0.09, 0.11), (0.075, 0.19), (0.03, 0.25), (0.018, 0.30),
            (0.018, 0.32), (0, 0.32)]
    b = common.mesh_object(f"{n}_Body", lathe(body, seg), col, ceramic, root)
    foot = common.mesh_object(f"{n}_Foot", lathe([(0, 0), (0.05, 0), (0.05, 0.012), (0, 0.012)], seg), col, bronze, root)
    stem = common.mesh_object(f"{n}_Neck", lathe([(0, 0.32), (0.012, 0.32), (0.012, 0.37), (0, 0.37)], 12), col, bronze, root)
    r0, r1, z0, z1 = 0.13, 0.17, 0.36, 0.58
    shade = common.mesh_object(f"{n}_Shade", lathe([(r0, z0), (r1, z0), (r1, z1), (r0, z1 - 0.005)], seg, closed=True),
                               col, glow, root)
    for ob in (b, foot, stem, shade):
        common.box_uv(ob, 0.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
