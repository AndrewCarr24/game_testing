"""Tall leafy plant (bird-of-paradise style, 1.7 m) in a honed-stone cylinder planter
with a dark soil top. Leaves are curved folded ribbons on long stems.

Origin: floor centre of the planter. Rotationally almost symmetric; the front is -Y.
"""
import importlib
import math
import os
import random
import sys

import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import bath_common as bc  # noqa: E402

importlib.reload(common)
importlib.reload(bc)

NAME = "BathPlant"

P = dict(name=NAME, pot_r=0.20, pot_h=0.46, leaves=11, seed=5, height=1.65)


def leaf(bm, base, azim, rise, reach, length, width, segs=12, fold=0.12):
    """Curved leaf: a stem rising from `base`, arching outward along azimuth `azim`."""
    d = Vector((math.cos(azim), math.sin(azim), 0.0))
    side = Vector((-math.sin(azim), math.cos(azim), 0.0))
    rows = []
    prev = None
    for i in range(segs + 1):
        s = i / segs
        c = Vector(base) + d * (reach * s ** 2.2) + Vector((0, 0, rise * (s - 0.35 * s * s)))
        # blade starts at 35% of the length; before that only a thin stem
        sb = max(0.0, (s - 0.32) / 0.68)
        w = width * (math.sin(math.pi * min(sb ** 0.7, 1.0)) ** 0.75) * 0.5 + 0.004
        tip_taper = 1.0 if sb < 0.97 else 0.2
        w *= tip_taper
        mid_lift = Vector((0, 0, fold * w * 2.2)) if sb > 0 else Vector((0, 0, 0))
        rows.append([bm.verts.new(c - side * w), bm.verts.new(c + mid_lift), bm.verts.new(c + side * w)])
    for i in range(segs):
        a, b = rows[i], rows[i + 1]
        for j in range(2):
            bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    stone = bc.stone()
    soil = common.pbr_material("M_Bath_Soil", (0.02, 0.018, 0.015), roughness=0.95)
    green = common.pbr_material("M_Bath_Leaf", (0.055, 0.15, 0.05), roughness=0.45)
    green2 = common.pbr_material("M_Bath_Leaf_Dark", (0.035, 0.10, 0.04), roughness=0.5)

    r, h = p["pot_r"], p["pot_h"]
    prof = [(0.0, 0.0), (r * 0.9, 0.0), (r * 0.94, 0.01), (r, 0.04), (r * 1.01, h - 0.02), (r, h), (r - 0.012, h), (r - 0.012, h - 0.05),
            (0.0, h - 0.05)]
    pot = common.mesh_object(f"{n}_Pot", bc.lathe(prof, 40), col, stone, root)
    bc.cylindrical_uv(pot, tile=1.0)
    common.mesh_object(f"{n}_Soil", bc.lathe([(0.0, h - 0.06), (r - 0.012, h - 0.06), (r - 0.012, h - 0.05), (0.0, h - 0.045)], 32), col, soil, root)

    rng = random.Random(p["seed"])
    for mi, mat in enumerate((green, green2)):
        bm = bmesh.new()
        for k in range(p["leaves"]):
            if k % 2 != mi:
                continue
            az = 2 * math.pi * (k / p["leaves"]) + rng.uniform(-0.25, 0.25)
            top = p["height"] - h
            rise = (top / 0.65) * rng.uniform(0.70, 1.0)
            reach = rng.uniform(0.30, 0.70)
            length = rise
            base = (0.045 * math.cos(az), 0.045 * math.sin(az), h - 0.05)
            leaf(bm, base, az, rise, reach, length, rng.uniform(0.20, 0.30))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        ob = common.mesh_object(f"{n}_Leaves_{mi}", bm, col, mat, root)
    return root, bc.parts_of(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
