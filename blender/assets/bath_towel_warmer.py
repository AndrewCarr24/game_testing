"""Heated towel rail: a wall-mounted brushed-brass ladder (two round uprights with domed
caps, round rungs) on proper wall brackets (a clamp collar round each upright, a round
stand-off post, a stepped wall rosette), plumbed through a pair of corner valves under
the uprights (union nut, valve body, wall tail with its rosette; a knurled handwheel on
the left, a plain lockshield cap on the right).

Two ivory terry towels hang on it, cloth-simulated (bath_towel_warmer_cloth.py, cached):
a bath sheet folded over the top rung, its long front flap resting against the rungs
below, and a hand towel over a lower rung, set a touch off-centre and askew. Both have a
looped terry pile (own texture), a flat-woven hem and dobby border band near each end,
where the pile steps down, and flat selvedges.

Origin: centre of the ladder on the wall plane (back at y = 0, standing out toward
-Y); the ladder spans +-height/2 in Z. Hang it with a z in PLACEMENTS (about 1.05).
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials  # noqa: E402
import bath_common as bc  # noqa: E402
import bath_towel_warmer_cloth as tc  # noqa: E402

importlib.reload(common)
importlib.reload(bc)
importlib.reload(tc)

NAME = "BathTowelWarmer"

P = dict(
    name=NAME,
    width=0.56, height=1.35,
    rungs=9,
    stand_off=0.075,
    upright_r=0.0175, rung_r=0.0115,
    segs=16,                 # round sections of the uprights, collars and valves
    rung_segs=12,
    sheet_rung=8,            # rung the bath sheet hangs over (0 = bottom)
    towel_rung=3,            # rung the hand towel hangs over
)


def lathe(profile, segs, origin=(0, 0, 0), axis=(0, 0, 1), rib=0.0, spin=0.0):
    """Revolve [(r, z) or (r, z, ribbed)] about +axis at origin. Ribbed rows alternate their
    radius by `rib` (knurling). No caps unless a row has r = 0."""
    bm = bmesh.new()
    rows = []
    for row in profile:
        r, z = row[0], row[1]
        ribbed = len(row) > 2 and row[2]
        if r < 1e-9:
            rows.append([bm.verts.new((0.0, 0.0, z))] * segs)
            continue
        ring = []
        for s in range(segs):
            a = 2 * math.pi * s / segs + spin
            rs = r - (rib if (ribbed and s % 2) else 0.0)
            ring.append(bm.verts.new((rs * math.cos(a), rs * math.sin(a), z)))
        rows.append(ring)
    for a, b in zip(rows[:-1], rows[1:]):
        for s in range(segs):
            t = (s + 1) % segs
            quad = list(dict.fromkeys((a[s], a[t], b[t], b[s])))
            if len(quad) >= 3:
                bm.faces.new(quad)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-7)
    rot = Vector(axis).normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation(origin) @ rot, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    brass = bc.brass()
    terry = tc.terry_material()
    band = materials.fabric("M_Fabric_Linen_Ivory", tc.IVORY)

    w, h, so = p["width"], p["height"], p["stand_off"]
    ur, rr = p["upright_r"], p["rung_r"]
    sg = p["segs"]
    y = -so
    zs = [-h / 2 + 0.11 + i * (h - 0.22) / (p["rungs"] - 1) for i in range(p["rungs"])]

    metal = bmesh.new()

    def add(bm_part):
        mc_merge(metal, bm_part)

    # ---- uprights: a domed cap with a shadow line on top; at the foot the tube necks down
    # into a union tail
    zt = h / 2 + 0.0015
    zb = -h / 2 + 0.072
    for sx in (-1, 1):
        x = sx * w / 2
        prof = [(0.0078, zb - 0.013), (0.0078, zb - 0.0065), (0.0105, zb - 0.0035), (ur * 0.9, zb - 0.0004),
                (ur, zb + 0.004), (ur, zt - 0.0062), (ur - 0.0011, zt - 0.0054), (ur - 0.0011, zt - 0.0040),
                (ur, zt - 0.0032), (ur * 0.93, zt + 0.0018), (ur * 0.66, zt + 0.0058), (0.0, zt + 0.0072)]
        add(lathe(prof, sg, (x, y, 0.0)))
        # union nut (hex) and the corner valve under it
        zn1 = zb - 0.013
        zn0 = zn1 - 0.012
        add(lathe([(0.0080, zn1 + 0.0005), (0.0118, zn1), (0.0128, zn1 - 0.0016), (0.0128, zn0 + 0.0016),
                   (0.0118, zn0), (0.0085, zn0 - 0.0005)], 6, (x, y, 0.0), spin=math.pi / 6))
        zv = zn0 - 0.0135                          # valve body centre (its ports: up, to the wall, forward)
        add(lathe([(0.0085, zn0 + 0.001), (0.0085, zv + 0.006), (0.0, zv + 0.006)], 12, (x, y, 0.0)))
        body = [(0.0215, 0.0), (0.0208, 0.0046), (0.0150, 0.0068), (0.0074, 0.0076),     # rosette, tail
                (0.0074, so - 0.0068), (0.0108, so - 0.0052), (0.0124, so - 0.0018),         # valve body
                (0.0124, so + 0.0018), (0.0108, so + 0.0052), (0.0, so + 0.0057)]
        add(lathe(body, 14, (x, 0.0, zv), axis=(0, -1, 0)))
        # bonnet + head facing the room: knurled handwheel (left), plain lockshield cap (right)
        if sx < 0:
            head = [(0.0090, so + 0.005), (0.0090, so + 0.0105), (0.0142, so + 0.0122, 1), (0.0142, so + 0.0300, 1),
                    (0.0128, so + 0.0326), (0.0070, so + 0.0340), (0.0, so + 0.0343)]
            add(lathe(head, 20, (x, 0.0, zv), axis=(0, -1, 0), rib=0.0010))
        else:
            head = [(0.0090, so + 0.005), (0.0090, so + 0.0095), (0.0110, so + 0.0108), (0.0112, so + 0.0228),
                    (0.0090, so + 0.0252), (0.0, so + 0.0257)]
            add(lathe(head, 16, (x, 0.0, zv), axis=(0, -1, 0)))

    # ---- rungs (ends buried in the uprights)
    for z in zs:
        add(lathe([(rr, -w / 2 + ur * 0.4), (rr, w / 2 - ur * 0.4)], p["rung_segs"], (0.0, y, z), axis=(1, 0, 0)))

    # ---- wall brackets: clamp collar round the upright, a round stand-off post, a stepped rosette
    for z in (zs[-1] + 0.055, (zs[0] + zs[1]) / 2):
        for sx in (-1, 1):
            x = sx * w / 2
            add(lathe([(ur + 0.0002, -0.0105), (ur + 0.0041, -0.0088), (ur + 0.0041, 0.0088), (ur + 0.0002, 0.0105)],
                      16, (x, y, z)))
            post = [(0.0235, 0.0), (0.0233, 0.0032), (0.0200, 0.0062), (0.0092, 0.0078), (0.0072, 0.0094),
                    (0.0072, so - ur - 0.002)]
            add(lathe(post, 10, (x, 0.0, z), axis=(0, -1, 0)))

    ob = common.mesh_object(f"{n}_PipingBrass", metal, col, brass, root)
    ob.data.set_sharp_from_angle(angle=math.radians(38))

    # ---- towels (cloth-simulated, cached)
    lower = lambda k, below: [zs[i] for i in range(max(0, k - below), k)]
    ks, kt = p["sheet_rung"], p["towel_rung"]
    sheet = tc.drape("sheet", y, zs[ks], rr, width=0.44, front=0.50, back=0.20, t=0.013, lower=lower(ks, 4),
                     x_off=-0.004, skew=0.010, gather=0.006, folds=0.036, tilt=0.12, seed=2, tris=1250)
    towel = tc.drape("hand", y, zs[kt], rr, width=0.30, front=0.48, back=0.29, t=0.011, lower=lower(kt, 3),
                     x_off=0.045, skew=-0.014, gather=0.005, folds=0.026, tilt=0.12, seed=5, tris=850)
    mc_merge(sheet, towel)
    ob = common.mesh_object(f"{n}_PipingTowels", sheet, col, terry, root)
    ob.data.materials.append(band)
    return root, bc.parts_of(root)


def mc_merge(dst, src):
    tc.mc._merge_into(dst, src)


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
