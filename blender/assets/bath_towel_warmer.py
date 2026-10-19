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
import bath_vanity as bv  # noqa: E402  (soft_extrude, rosette)

importlib.reload(common)
importlib.reload(bc)
importlib.reload(bv)

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

    # wall brackets (top and bottom, on both uprights) with wall rosettes, and the
    # thermostat knob on the lower right bracket
    br = bmesh.new()
    for sx in (-1, 1):
        for z in (-h / 2 + 0.05, h / 2 - 0.05):
            bc.cylinder_between(br, (sx * w / 2, 0.0, z), (sx * w / 2, y, z), 0.013, 12)
            bv.rosette(col, root, f"{n}_Rosette", brass, (sx * w / 2, 0.0, z), 0.024, t=0.007, segs=20)
    kz = -h / 2 + 0.05
    bv.cone_between(br, (w / 2 + ur * 0.6, -so * 0.5, kz), (w / 2 + 0.024, -so * 0.5, kz), 0.0105, 0.0105, 16)
    bv.cone_between(br, (w / 2 + 0.024, -so * 0.5, kz), (w / 2 + 0.028, -so * 0.5, kz), 0.0105, 0.0085, 16)
    bv.cone_between(br, (w / 2 + ur * 0.4, -so * 0.5, kz), (w / 2 + ur * 0.4, -so + 0.002, kz), 0.006, 0.006, 8)
    common.mesh_object(f"{n}_Brackets", br, col, brass, root)

    def drape(zr, front, back, t, x0, x1, flare=0.008):
        """Cloth hung over the rung at height zr: a front flap `front` m long, a back flap
        `back` m long, thickness t; the front flap swings slightly away at its hem."""
        R = rr + 0.0012 + t / 2
        path = [(y - R - flare, zr - front), (y - R - flare * 0.35, zr - front * 0.55), (y - R, zr - 0.04)]
        for k in range(9):
            a = math.pi - math.pi * k / 8
            path.append((y + R * math.cos(a), zr + R * math.sin(a)))
        path += [(y + R, zr - 0.04), (y + R + 0.002, zr - back)]
        a_side, b_side = [], []
        from mathutils import Vector as V
        P_ = [V(q) for q in path]
        for i, q in enumerate(P_):
            d = (P_[min(i + 1, len(P_) - 1)] - P_[max(i - 1, 0)]).normalized()
            nrm = V((d.y, -d.x))          # points outward (away from the rung)
            a_side.append(q + nrm * t / 2)
            b_side.append(q - nrm * t / 2)
        outline = [(q.x, q.y) for q in a_side] + [(q.x, q.y) for q in b_side[::-1]]
        return bv.soft_extrude(outline, x0, x1, ease=0.010, inset=0.005)

    # folded hand towel over the 4th rung from the bottom: front flap long, back flap short
    tw = w - 0.12
    ob = common.mesh_object(f"{n}_PipingTowel", drape(zs[3], 0.42, 0.27, 0.020, -tw / 2, tw / 2), col, oat, root)
    common.box_uv(ob, tile=0.25)
    # bath sheet over the top rung
    sw = w - 0.10
    ob = common.mesh_object(f"{n}_PipingSheet", drape(zs[8], 0.55, 0.19, 0.022, -sw / 2, sw / 2, flare=0.010), col, oat2, root)
    common.box_uv(ob, tile=0.25)
    bc.merge(root, bc.by_material(root, brass), f"{n}_PipingBrass")
    bc.merge(root, bc.by_material(root, oat), f"{n}_PipingTowel")
    bc.merge(root, bc.by_material(root, oat2), f"{n}_PipingSheet")
    return root, bc.parts_of(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
