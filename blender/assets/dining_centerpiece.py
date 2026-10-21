"""Table centrepiece: a slim bronze tray carrying a hand-thrown oat-glazed bowl of
quinces and three bronze candlesticks of different heights with cream candles.

Origin: centre of the underside (z = 0). Long axis along X. Units are metres.
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, pickups  # noqa: E402

importlib.reload(common)
importlib.reload(materials)
importlib.reload(pickups)

NAME = "DiningCenterpiece"

P = dict(name=NAME, length=1.3, width=0.24, tray_t=0.012)


def lathe(bm, profile, segs=20, offset=(0, 0, 0)):
    rows = []
    for r, z in profile:
        if r < 1e-9:
            rows.append([bm.verts.new((offset[0], offset[1], z + offset[2]))] * segs)
        else:
            rows.append([bm.verts.new((offset[0] + r * math.cos(2 * math.pi * s / segs),
                                       offset[1] + r * math.sin(2 * math.pi * s / segs), z + offset[2]))
                         for s in range(segs)])
    for i in range(len(profile) - 1):
        a, b = rows[i], rows[i + 1]
        for s in range(segs):
            t = (s + 1) % segs
            quad = []
            for v in (a[s], a[t], b[t], b[s]):
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
    glaze = common.pbr_material("M_Ceramic_Oat", (0.55, 0.50, 0.40), roughness=0.35)
    wax = common.pbr_material("M_Candle_Cream", (0.78, 0.72, 0.58), roughness=0.55)
    quince = common.pbr_material("M_Quince", (0.50, 0.40, 0.05), roughness=0.5)

    L, W, T = p["length"], p["width"], p["tray_t"]
    tray = common.mesh_object(f"{n}_Tray", common.rounded_slab_bmesh(L, W, T, 0.03), col, bronze, root)
    tray.location = (0, 0, T / 2)
    common.add_bevel(tray, 0.003, 2)
    common.box_uv(tray, 0.5)

    # bowl (shell with real thickness)
    bm = bmesh.new()
    prof = [(0.0, 0.0), (0.045, 0.0), (0.075, 0.012), (0.105, 0.045), (0.115, 0.078), (0.111, 0.082),
            (0.100, 0.052), (0.074, 0.024), (0.0, 0.016)]
    lathe(bm, prof, 24, (-0.38, 0, T))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    fm = bmesh.new()
    pos = [(-0.40, 0.01, 0.05), (-0.35, -0.02, 0.05), (-0.37, 0.045, 0.05), (-0.345, 0.04, 0.05),
           (-0.39, -0.04, 0.05), (-0.37, 0.0, 0.095), (-0.405, 0.015, 0.085)]
    for x, y, z in pos:
        bmesh.ops.create_uvsphere(fm, u_segments=10, v_segments=7, radius=0.036,
                                  matrix=Matrix.Translation((x, y, T + z)) @ Matrix.Diagonal((1, 1, 1.12, 1)))
    # the bowl with its quinces, and each candlestick, are throwable pickups (lib/pickups.py)
    # (the middle of a table for 14, chairs all round: reached by leaning over it, range 1.9 m)
    pickups.make(f"{n}_Bowl", col, root, "bowl", [("Bowl", bm, glaze), ("Quinces", fm, quince)], (-0.38, 0, T),
                 uv_tile=0.5, range=1.9)

    # candlesticks
    for i, (x, h) in enumerate(((0.12, 0.11), (0.30, 0.17), (0.48, 0.23))):
        cb, cw, wk = bmesh.new(), bmesh.new(), bmesh.new()
        base_r = 0.035
        prof = [(0.0, 0.0), (base_r, 0.0), (base_r, 0.006), (0.014, 0.012), (0.0105, 0.03),
                (0.0105, h - 0.05), (0.017, h - 0.035), (0.022, h - 0.02), (0.022, h), (0.0, h - 0.008)]
        lathe(cb, prof, 16, (x, 0, T))
        cwh = 0.08 + 0.02 * i
        # a slightly burnt-down top (a shallow well round the wick) and the wick itself
        ct = h - 0.01 + cwh
        lathe(cw, [(0.0, h - 0.01), (0.0145, h - 0.01), (0.0145, ct), (0.0125, ct + 0.0015), (0.004, ct - 0.003),
                   (0.0, ct - 0.0035)], 12, (x, 0, T))
        lathe(wk, [(0.0016, ct - 0.004), (0.0014, ct + 0.009), (0.0, ct + 0.0105)], 5, (x, 0, T))
        pickups.make(f"{n}_Candle{i + 1:02d}", col, root, "candle", [("Candlestick", cb, bronze), ("Candle", cw, wax),
                     ("Wick", wk, materials.black_metal())], (x, 0, T), uv_tile=0.5, range=1.9)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
