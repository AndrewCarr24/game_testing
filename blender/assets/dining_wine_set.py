"""Tasting set on a slim oak board: a crystal decanter with a little red wine, a standing
bottle, and three stemmed glasses (one with wine). Glass is alpha-blended. The decanter, the
bottle and each glass are throwable pickups (lib/pickups.py); the board stays.

Origin: centre of the underside of the board (z = 0). Board along X. Units are metres.
"""
import importlib
import math
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, pickups  # noqa: E402

importlib.reload(common)
importlib.reload(materials)
importlib.reload(pickups)

NAME = "DiningWineSet"

P = dict(name=NAME, board=(0.72, 0.26, 0.022))


def lathe(bm, profile, segs=20, x=0.0, y=0.0, z=0.0):
    rows = []
    for r, h in profile:
        if r < 1e-9:
            rows.append([bm.verts.new((x, y, z + h))] * segs)
        else:
            rows.append([bm.verts.new((x + r * math.cos(2 * math.pi * k / segs), y + r * math.sin(2 * math.pi * k / segs), z + h))
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

    oak = materials.smoked_oak()
    glass = materials.glass("M_Glass_Crystal", tint=(0.9, 0.93, 0.95), alpha=0.22, roughness=0.02)
    wine = common.pbr_material("M_Wine_Red", (0.12, 0.006, 0.012), roughness=0.08)
    bottle_mat = common.pbr_material("M_Bottle_Green", (0.022, 0.060, 0.028), roughness=0.15)
    label = common.pbr_material("M_Label_Cream", (0.62, 0.56, 0.42), roughness=0.8)
    foil = materials.bronze()

    bw, bd, bt = p["board"]
    board = common.mesh_object(f"{n}_Board", common.rounded_slab_bmesh(bw, bd, bt, 0.02), col, oak, root)
    board.location = (0, 0, bt / 2)
    common.add_bevel(board, 0.003, 2)
    common.box_uv(board, 0.5)
    z0 = bt

    # decanter: wide base, tapering neck (double wall: outer surface down the inside)
    dec_out = [(0.0, 0.0), (0.075, 0.0), (0.082, 0.015), (0.08, 0.05), (0.06, 0.11), (0.03, 0.16), (0.02, 0.22),
               (0.02, 0.255), (0.026, 0.268), (0.019, 0.268), (0.0165, 0.26), (0.0165, 0.22), (0.026, 0.16),
               (0.05, 0.11), (0.068, 0.05), (0.0, 0.025)]
    gb = bmesh.new()
    lathe(gb, dec_out, 16, -0.2, 0.0, z0)
    wb = bmesh.new()
    lathe(wb, [(0.0, 0.026), (0.067, 0.03), (0.07, 0.05), (0.055, 0.09), (0.0, 0.092)], 16, -0.2, 0.0, z0)
    pickups.make(f"{n}_Decanter", col, root, "decanter", [("Glass", gb, glass), ("Wine", wb, wine)],
                 (-0.2, 0.0, z0), uv_tile=0.5)

    # stemmed glasses
    glass_prof = [(0.0, 0.0), (0.04, 0.0), (0.04, 0.004), (0.006, 0.008), (0.005, 0.09), (0.02, 0.1), (0.04, 0.125),
                  (0.045, 0.15), (0.042, 0.19), (0.036, 0.215), (0.0345, 0.213), (0.0405, 0.19), (0.0435, 0.15),
                  (0.0385, 0.125), (0.019, 0.108), (0.0, 0.104)]
    for i, (gx, gy) in enumerate(((0.1, -0.04), (0.2, 0.05), (0.27, -0.045))):
        gb = bmesh.new()
        lathe(gb, glass_prof, 14, gx, gy, z0)
        parts_ = [("Glass", gb, glass)]
        if i == 1:
            wb = bmesh.new()
            lathe(wb, [(0.0, 0.108), (0.036, 0.13), (0.04, 0.15), (0.0, 0.153)], 14, gx, gy, z0)
            parts_.append(("Wine", wb, wine))
        pickups.make(f"{n}_WineGlass{i + 1:02d}", col, root, "wine_glass", parts_, (gx, gy, z0), uv_tile=0.5)

    # bottle (opaque green with label and foil)
    bt_bm = bmesh.new()
    lathe(bt_bm, [(0.0, 0.0), (0.0375, 0.0), (0.0375, 0.19), (0.032, 0.225), (0.0145, 0.265), (0.0125, 0.28),
                  (0.0125, 0.32), (0.0, 0.32)], 14, -0.04, 0.02, z0)
    lb = bmesh.new()
    lathe(lb, [(0.0382, 0.05), (0.0382, 0.15)], 14, -0.04, 0.02, z0)
    fb = bmesh.new()
    lathe(fb, [(0.0132, 0.285), (0.0132, 0.325), (0.0, 0.325)], 12, -0.04, 0.02, z0)
    pickups.make(f"{n}_Bottle", col, root, "wine_bottle", [("Bottle", bt_bm, bottle_mat), ("Label", lb, label),
                                                           ("Foil", fb, foil)], (-0.04, 0.02, z0), uv_tile=0.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
