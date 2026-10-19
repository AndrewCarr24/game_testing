"""Cascade chandelier for the double-height great room: a bronze ceiling plate and 30
hair-thin bronze drops of different lengths, each ending in a glowing opal sphere, so the
lights form an inverted dome about 3.4 m tall.

Hangs from the ceiling: the origin is the attachment point on the ceiling plate (place it
at z = ceiling height); everything is below it (negative z). Units are metres.
"""
import importlib
import math
import os
import sys

import bmesh
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "LivingChandelier"

P = dict(name=NAME, drops=30, radius=1.0, top_len=1.4, bottom_len=3.5, bulb_r=0.085, seed=9, glow=3.0)


def _sphere(bm, c, r, rings=6, segs=10):
    rows = []
    for i in range(1, rings):
        a = math.pi * i / rings
        rr, z = r * math.sin(a), -r * math.cos(a)
        rows.append([bm.verts.new((c.x + rr * math.cos(2 * math.pi * k / segs), c.y + rr * math.sin(2 * math.pi * k / segs), c.z + z))
                     for k in range(segs)])
    bot = bm.verts.new((c.x, c.y, c.z - r))
    top = bm.verts.new((c.x, c.y, c.z + r))
    for k in range(segs):
        j = (k + 1) % segs
        bm.faces.new((top, rows[0][j], rows[0][k]))
        bm.faces.new((bot, rows[-1][k], rows[-1][j]))
        for i in range(len(rows) - 1):
            bm.faces.new((rows[i][k], rows[i][j], rows[i + 1][j], rows[i + 1][k]))


def _rod(bm, p0, z1, r, segs=5):
    a = [bm.verts.new((p0.x + r * math.cos(2 * math.pi * k / segs), p0.y + r * math.sin(2 * math.pi * k / segs), p0.z))
         for k in range(segs)]
    b = [bm.verts.new((p0.x + r * math.cos(2 * math.pi * k / segs), p0.y + r * math.sin(2 * math.pi * k / segs), z1))
         for k in range(segs)]
    for k in range(segs):
        j = (k + 1) % segs
        bm.faces.new((a[k], a[j], b[j], b[k]))


def _cap(bm, c, r, h, segs=8):
    """Socket cap: a short cylinder with a chamfered top (no underside: it sits on the globe)."""
    rows = []
    for rr, z in ((r, 0.0), (r, h * 0.7), (r * 0.45, h)):
        rows.append([bm.verts.new((c.x + rr * math.cos(2 * math.pi * k / segs), c.y + rr * math.sin(2 * math.pi * k / segs),
                                   c.z + z)) for k in range(segs)])
    for a, b in zip(rows, rows[1:]):
        for k in range(segs):
            j = (k + 1) % segs
            bm.faces.new((a[k], a[j], b[j], b[k]))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rng = np.random.default_rng(p["seed"])
    bronze = materials.bronze()
    glow = materials.emissive("M_Living_ChandelierGlow", (1.0, 0.80, 0.52), p["glow"])

    plate_bm = bmesh.new()
    segs = 40
    for z0, z1, r in ((-0.03, 0.0, 1.05),):   # main disc
        rows = [[plate_bm.verts.new((rr * math.cos(2 * math.pi * k / segs), rr * math.sin(2 * math.pi * k / segs), z))
                 for k in range(segs)] for rr, z in ((0.0, z1), (r, z1), (r, z0), (0.0, z0))]
    # simple lid: fan
    top_c = plate_bm.verts.new((0, 0, 0.0))
    bot_c = plate_bm.verts.new((0, 0, -0.03))
    for k in range(segs):
        j = (k + 1) % segs
        plate_bm.faces.new((top_c, rows[1][j], rows[1][k]))
        plate_bm.faces.new((rows[1][k], rows[1][j], rows[2][j], rows[2][k]))
        plate_bm.faces.new((bot_c, rows[2][k], rows[2][j]))
    # a deeper canopy drum at the centre, where the fixture is fixed to the ceiling
    crow = [[plate_bm.verts.new((rr * math.cos(2 * math.pi * k / 24), rr * math.sin(2 * math.pi * k / 24), z))
             for k in range(24)] for rr, z in ((0.22, -0.03), (0.22, -0.075), (0.20, -0.085))]
    cb = plate_bm.verts.new((0, 0, -0.085))
    for a, b in zip(crow, crow[1:]):
        for k in range(24):
            j = (k + 1) % 24
            plate_bm.faces.new((a[k], a[j], b[j], b[k]))
    for k in range(24):
        plate_bm.faces.new((cb, crow[-1][(k + 1) % 24], crow[-1][k]))
    bmesh.ops.recalc_face_normals(plate_bm, faces=plate_bm.faces[:])
    plate = common.mesh_object(f"{n}_PlateNoCollide", plate_bm, col, bronze, root)
    common.add_bevel(plate, 0.004, segments=1)
    common.box_uv(plate, 0.5)

    rods = bmesh.new()
    bulbs = bmesh.new()
    count = p["drops"]
    for i in range(count):
        # golden-angle spiral on the plate; length cascades: long at the centre, shorter at the rim
        rr = p["radius"] * 0.9 * math.sqrt((i + 0.5) / count)
        ang = i * 2.399963
        x, y = rr * math.cos(ang), rr * math.sin(ang)
        t = rr / (p["radius"] * 0.9)
        L = p["bottom_len"] - (p["bottom_len"] - p["top_len"]) * (t ** 1.2) + rng.uniform(-0.12, 0.12)
        _rod(rods, Vector((x, y, -0.03)), -L + 0.01, 0.004)
        br = p["bulb_r"] * rng.uniform(0.85, 1.1)
        # a small bronze socket cap where the drop meets the globe
        _cap(rods, Vector((x, y, -L - p["bulb_r"] * 0.6 + br * 0.82)), 0.016, 0.03)
        _sphere(bulbs, Vector((x, y, -L - p["bulb_r"] * 0.6)), br)
    for bmx in (rods, bulbs):
        bmesh.ops.recalc_face_normals(bmx, faces=bmx.faces[:])
    ro = common.mesh_object(f"{n}_RodsNoCollide", rods, col, bronze, root, smooth=False)
    bo = common.mesh_object(f"{n}_BulbsNoCollide", bulbs, col, glow, root)
    common.box_uv(ro, 0.5)
    common.box_uv(bo, 0.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
