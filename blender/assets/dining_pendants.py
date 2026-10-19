"""Row of three bronze cone pendants over the tasting table: spun-bronze shades with a
glowing warm inside and a bulb, on slim black cables to small ceiling roses.

Origin: the lower rim of the shades (z = 0); the ceiling mount is at the asset's top, so
place it at z = ceiling - height. Row along X. Units are metres.
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "DiningPendants"

P = dict(name=NAME, count=3, spacing=0.9, drop=2.3, shade_h=0.30, shade_r=0.22, emission=3.0)


def lathe(bm, profile, segs, z=0.0, x=0.0):
    rows = []
    for r, h in profile:
        if r < 1e-9:
            rows.append([bm.verts.new((x, 0, z + h))] * segs)
        else:
            rows.append([bm.verts.new((x + r * math.cos(2 * math.pi * k / segs), r * math.sin(2 * math.pi * k / segs), z + h))
                         for k in range(segs)])
    for a, b in zip(rows[:-1], rows[1:]):
        for k in range(segs):
            t = (k + 1) % segs
            quad = []
            for v in (a[k], a[t], b[t], b[k]):
                if v not in quad:
                    quad.append(v)
            if len(quad) >= 3:
                bm.faces.new(quad)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    bronze = materials.bronze()
    dark = materials.black_metal()
    inner = materials.emissive("M_Pendant_Glow", (1.0, 0.72, 0.42), p["emission"])
    bulb = materials.emissive("M_LampBulb", (1.0, 0.92, 0.74), 6.0)

    sh, sr = p["shade_h"], p["shade_r"]
    top = p["drop"] + 0.0
    outer, glow, cab, bulbs = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    for i in range(p["count"]):
        x = (i - (p["count"] - 1) / 2) * p["spacing"]
        t = 0.004
        # outer shell: a bell, wide at the bottom, with a rolled rim
        prof_o = [(sr, 0.0), (sr + 0.004, 0.006), (sr * 0.92, sh * 0.35), (sr * 0.5, sh * 0.78), (0.045, sh), (0.0, sh + 0.004)]
        lathe(outer, prof_o, 24, 0.0, x)
        # emissive inside
        prof_i = [(0.0, sh - 0.005), (0.04, sh - 0.006), (sr * 0.5 - t, sh * 0.78 - 0.003), (sr * 0.92 - t, sh * 0.35), (sr - t, 0.004)]
        lathe(glow, prof_i, 24, 0.0, x)
        bmesh.ops.create_uvsphere(bulbs, u_segments=10, v_segments=6, radius=0.03,
                                  matrix=Matrix.Translation((x, 0, sh * 0.72)))
        # cable and rose
        cz0 = sh + 0.004
        bmesh.ops.create_cone(cab, cap_ends=True, cap_tris=False, segments=6, radius1=0.0035, radius2=0.0035,
                              depth=top - cz0, matrix=Matrix.Translation((x, 0, (top + cz0) / 2)))
        bmesh.ops.create_cone(cab, cap_ends=True, cap_tris=False, segments=14, radius1=0.04, radius2=0.04,
                              depth=0.014, matrix=Matrix.Translation((x, 0, top - 0.007)))
    # orient the open shells: the bronze skin faces out, the glowing lining faces the bulb
    xs = [(i - (p["count"] - 1) / 2) * p["spacing"] for i in range(p["count"])]
    for bm_, sign in ((outer, -1), (glow, 1)):
        for f in bm_.faces:
            c = f.calc_center_median()
            ax = min(xs, key=lambda q: abs(q - c.x))
            to_axis = Vector((ax - c.x, -c.y, sh * 0.72 - c.z))      # toward the bulb
            if f.normal.dot(to_axis) * sign < 0:
                f.normal_flip()
    sh_ob = common.mesh_object(f"{n}_Shades", outer, col, bronze, root)
    gl_ob = common.mesh_object(f"{n}_Inside", glow, col, inner, root, smooth=True)
    ca_ob = common.mesh_object(f"{n}_Cables", cab, col, dark, root)
    bu_ob = common.mesh_object(f"{n}_Bulbs", bulbs, col, bulb, root)
    for ob in (sh_ob, gl_ob, ca_ob, bu_ob):
        common.box_uv(ob, 0.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
