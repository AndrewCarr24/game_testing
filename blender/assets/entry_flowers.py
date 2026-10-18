"""Entry flower arrangement: a tall matte stoneware vase with a loose, sweeping spray of
blossom branches (blush and white clusters on dark twigs). Sits on the round centre
table. Origin: centre of the underside of the vase. Units are metres.
"""
import importlib
import math
import os
import random
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import table_lamp  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "EntryFlowers"

P = dict(
    name=NAME,
    branches=11,
    seed=5,
    vase_h=0.36,
    vase_profile=[(0.075, 0.0), (0.085, 0.03), (0.105, 0.12), (0.100, 0.21), (0.062, 0.30), (0.052, 0.345), (0.058, 0.36)],
    spray=(0.5, 0.85),       # branch length range
)


def sphere(bm, c, r, segs=6, rings=4, jitter=0.0, rnd=None):
    ret = bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=r, matrix=Matrix.Translation(c))
    if jitter and rnd:
        for v in ret["verts"]:
            v.co += Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * (r * jitter)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])

    ceramic = common.pbr_material("M_Entry_Stoneware", (0.60, 0.56, 0.50), roughness=0.62)
    twig = common.pbr_material("M_Entry_Twig", (0.045, 0.030, 0.020), roughness=0.8)
    blush = common.pbr_material("M_Entry_Blossom_Blush", (0.62, 0.36, 0.38), roughness=0.8)
    white = common.pbr_material("M_Entry_Blossom_White", (0.78, 0.74, 0.68), roughness=0.8)

    # ---- vase ---------------------------------------------------------------------------
    pr = [(0.0, 0.0)] + table_lamp.catmull(p["vase_profile"], per=5) + [(0.0, p["vase_profile"][-1][1])]
    common.mesh_object(f"{n}_Vase", table_lamp.lathe(pr, 40, sharp=50), col, ceramic, root)

    # ---- branches ------------------------------------------------------------------------
    stems = bmesh.new()
    bl, wh = bmesh.new(), bmesh.new()
    top = p["vase_h"]
    for b in range(p["branches"]):
        th = 2 * math.pi * (b + rnd.uniform(-0.2, 0.2)) / p["branches"] + 0.4
        lean = math.radians(rnd.uniform(6, 40))
        L = rnd.uniform(*p["spray"])
        d_out = Vector((math.cos(th), math.sin(th), 0))
        base = Vector((rnd.uniform(-0.02, 0.02), rnd.uniform(-0.02, 0.02), top - 0.12))
        pts = []
        steps = 9
        for k in range(steps + 1):
            t = k / steps
            out = L * math.sin(lean) * t ** 1.5
            up = L * math.cos(lean) * t
            wob = 0.03 * math.sin(t * 5 + b)
            pts.append(base + d_out * out + Vector((-d_out.y, d_out.x, 0)) * wob + Vector((0, 0, up)))
        for k in range(steps):
            table_lamp.cylinder_between(stems, pts[k], pts[k + 1], 0.0065 * (1 - 0.55 * k / steps), segs=5)
        # blossom clusters on the upper two thirds, with short twigs
        for k in range(3, steps + 1):
            c = pts[k]
            for _ in range(rnd.randint(1, 2) if k < steps else 3):
                off = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.3, 1))) * 0.045
                tgt = bl if rnd.random() < 0.5 else wh
                table_lamp.cylinder_between(stems, c, c + off * 0.8, 0.0028, segs=4)
                for _ in range(2):
                    o2 = off + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * 0.022
                    sphere(tgt, c + o2, rnd.uniform(0.018, 0.034), 6, 3, 0.25, rnd)
    common.mesh_object(f"{n}_Stems", stems, col, twig, root, smooth=False)
    common.mesh_object(f"{n}_BlossomBlush", bl, col, blush, root)
    common.mesh_object(f"{n}_BlossomWhite", wh, col, white, root)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
