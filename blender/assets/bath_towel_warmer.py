"""Heated towel rail: a wall-mounted brushed-brass ladder (two uprights, round rungs,
wall brackets with a small control knob) with a folded oat linen towel draped over
one rung and a bath sheet hanging from another.

Origin: centre of the ladder on the wall plane (back at y = 0, standing out toward
-Y); the ladder spans +-height/2 in Z. Hang it with a z in PLACEMENTS (about 1.05).
"""
import importlib
import math
import os
import sys

import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import bath_common as bc  # noqa: E402

importlib.reload(common)
importlib.reload(bc)

NAME = "BathTowelWarmer"

P = dict(
    name=NAME,
    width=0.56, height=1.35,
    rungs=9,
    stand_off=0.075,
    upright_r=0.0175, rung_r=0.0115,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    brass = bc.brass()
    oat = materials.fabric("M_Fabric_Oat", (0.42, 0.37, 0.30))
    oat2 = materials.fabric("M_Fabric_Linen_Ivory", (0.55, 0.52, 0.46))

    w, h, so = p["width"], p["height"], p["stand_off"]
    ur, rr = p["upright_r"], p["rung_r"]
    y = -so

    # uprights and rungs (one mesh each so the collider boxes stay few)
    ups = bmesh.new()
    for sx in (-1, 1):
        bc.cylinder_between(ups, (sx * w / 2, y, -h / 2), (sx * w / 2, y, h / 2), ur, 14)
    common.mesh_object(f"{n}_Uprights", ups, col, brass, root)
    for sx in (-1, 1):
        cap = bc.lathe([(0.0, 0.0), (ur * 1.0, 0.0), (ur * 0.8, 0.008), (0.0, 0.010)], 14)
        for z, flip in ((h / 2, 1), (-h / 2, -1)):
            c = common.mesh_object(f"{n}_Cap", cap.copy(), col, brass, root)
            c.location = (sx * w / 2, y, z)
            if flip < 0:
                c.rotation_euler = (math.pi, 0, 0)
    rungs = bmesh.new()
    zs = [-h / 2 + 0.11 + i * (h - 0.22) / (p["rungs"] - 1) for i in range(p["rungs"])]
    for z in zs:
        bc.cylinder_between(rungs, (-w / 2, y, z), (w / 2, y, z), rr, 10)
    common.mesh_object(f"{n}_Rungs", rungs, col, brass, root)

    # wall brackets (top and bottom, on both uprights)
    br = bmesh.new()
    for sx in (-1, 1):
        for z in (-h / 2 + 0.05, h / 2 - 0.05):
            bc.cylinder_between(br, (sx * w / 2, 0.0, z), (sx * w / 2, y, z), 0.013, 12)
    common.mesh_object(f"{n}_Brackets", br, col, brass, root)

    # folded hand towel over the 4th rung from the bottom: front flap long, back flap short
    zr = zs[3]
    tw = w - 0.12
    ty = y
    front = bc.box(col, root, f"{n}_Towel_Front", (tw, 0.022, 0.46), (0, ty - rr - 0.013, zr + 0.035 - 0.23 + 0.0), oat,
                   bevel=0.008, uv_tile=0.25)
    back = bc.box(col, root, f"{n}_Towel_Back", (tw, 0.018, 0.30), (0, ty + rr + 0.011, zr + 0.035 - 0.15 + 0.0), oat,
                  bevel=0.007, uv_tile=0.25)
    # rolled top edge round the rung
    roll = bmesh.new()
    bc.cylinder_between(roll, (-tw / 2, ty, zr + rr + 0.012), (tw / 2, ty, zr + rr + 0.012), rr + 0.016, 14)
    common.box_uv(common.mesh_object(f"{n}_Towel_Roll", roll, col, oat, root), tile=0.25)
    # bath sheet over the top rung
    zb = zs[8]
    bc.box(col, root, f"{n}_Sheet_Front", (w - 0.1, 0.024, 0.56), (0, ty - rr - 0.014, zb + 0.03 - 0.28), oat2,
           bevel=0.009, uv_tile=0.25)
    sheet_roll = bmesh.new()
    bc.cylinder_between(sheet_roll, (-(w - 0.1) / 2, ty, zb + rr + 0.012), ((w - 0.1) / 2, ty, zb + rr + 0.012), rr + 0.017, 14)
    common.box_uv(common.mesh_object(f"{n}_Sheet_Roll", sheet_roll, col, oat2, root), tile=0.25)
    bc.box(col, root, f"{n}_Sheet_Back", (w - 0.1, 0.016, 0.20), (0, ty + rr + 0.011, zb + 0.03 - 0.10), oat2,
           bevel=0.006, uv_tile=0.25)
    bc.merge(root, bc.by_material(root, brass), f"{n}_PipingBrass")
    bc.merge(root, bc.by_material(root, oat), f"{n}_PipingTowel")
    bc.merge(root, bc.by_material(root, oat2), f"{n}_PipingSheet")
    return root, bc.parts_of(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
