"""Smaller blossom arrangement (6 branches, shorter spray) for powder-room and cloakroom
surfaces: entry_flowers' vase and materials with fewer, shorter branches, carrying open
five-petal blossoms (cupped stars, two-sided) and closed buds instead of round blobs.
Built here rather than in entry_flowers so the entry's arrangement is untouched.
Origin: centre of the vase underside."""
import importlib
import math
import os
import random
import sys

import bmesh
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entry_flowers  # noqa: E402
import table_lamp  # noqa: E402
import bath_vanity as bv  # noqa: E402  (cone_between)

importlib.reload(entry_flowers)
importlib.reload(bv)
common = entry_flowers.common

NAME = "EntryFlowersSmall"
P = dict(name=NAME, branches=6, spray=(0.38, 0.62), seed=9, vase_h=0.36,
         vase_profile=entry_flowers.P["vase_profile"], vase_segs=28)


def blossom(bm, c, normal, r, rnd):
    """Open five-petal flower, cupped, closed underneath so it reads from any side: each
    petal has two shoulder points (a rounded, broad petal) and a deep notch between petals
    (15 rim points, 30 tris)."""
    n = Vector(normal).normalized()
    rot = n.to_track_quat("Z", "Y").to_matrix()
    spin = rnd.uniform(0, 2 * math.pi)
    rim = []
    for k in range(5):
        a0 = spin + 2 * math.pi * k / 5
        for da, rr, lift in ((-0.36, r, 0.26 * r), (0.36, r, 0.26 * r), (0.6283, 0.58 * r, 0.12 * r)):
            a = a0 + da
            rim.append(bm.verts.new(c + rot @ Vector((rr * math.cos(a), rr * math.sin(a), lift))))
    top = bm.verts.new(c + rot @ Vector((0, 0, 0.06 * r)))
    bot = bm.verts.new(c + rot @ Vector((0, 0, -0.20 * r)))
    m = len(rim)
    for k in range(m):
        a, b = rim[k], rim[(k + 1) % m]
        bm.faces.new((top, a, b))
        bm.faces.new((bot, b, a))


def bud(bm, c, d, r):
    """Closed bud: a small octahedron stretched along the twig direction (8 tris)."""
    d = Vector(d).normalized()
    rot = d.to_track_quat("Z", "Y").to_matrix()
    tip = bm.verts.new(c + rot @ Vector((0, 0, r * 1.6)))
    base = bm.verts.new(c + rot @ Vector((0, 0, -r * 0.8)))
    ring = [bm.verts.new(c + rot @ Vector((r * math.cos(a), r * math.sin(a), 0))) for a in
            (0, math.pi / 2, math.pi, 1.5 * math.pi)]
    for k in range(4):
        a, b = ring[k], ring[(k + 1) % 4]
        bm.faces.new((tip, a, b))
        bm.faces.new((base, b, a))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])          # same draw order as entry_flowers: same branch layout
    rnd2 = random.Random(p["seed"] + 101)   # flower spin and buds, so they do not disturb the layout

    ceramic = common.pbr_material("M_Entry_Stoneware", (0.60, 0.56, 0.50), roughness=0.62)
    twig = common.pbr_material("M_Entry_Twig", (0.045, 0.030, 0.020), roughness=0.8)
    blush = common.pbr_material("M_Entry_Blossom_Blush", (0.62, 0.36, 0.38), roughness=0.8)
    white = common.pbr_material("M_Entry_Blossom_White", (0.78, 0.74, 0.68), roughness=0.8)

    # ---- vase: same profile as entry_flowers, lighter tessellation, with a turned-in lip
    vp = p["vase_profile"]
    pr = [(0.0, 0.0)] + table_lamp.catmull(vp, per=3) + [(vp[-1][0] - 0.008, vp[-1][1] - 0.002),
                                                         (vp[-1][0] - 0.010, vp[-1][1] - 0.03),
                                                         (0.0, vp[-1][1] - 0.03)]
    common.mesh_object(f"{n}_Vase", table_lamp.lathe(pr, p["vase_segs"], sharp=50), col, ceramic, root)

    # ---- branches -----------------------------------------------------------------------
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
            r0 = 0.0065 * (1 - 0.55 * k / steps)
            r1 = 0.0065 * (1 - 0.55 * (k + 1) / steps)
            bv.cone_between(stems, pts[k], pts[k + 1] + (pts[k + 1] - pts[k]) * 0.04, r0, r1, 5, cap=False)
        # blossom clusters on the upper two thirds: short twigs carrying open flowers, buds at the tips
        for k in range(3, steps + 1):
            c = pts[k]
            axis = (pts[k] - pts[k - 1]).normalized()
            for _ in range(rnd.randint(1, 2) if k < steps else 3):
                off = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.3, 1))) * 0.045
                tgt = bl if rnd.random() < 0.5 else wh
                end = c + off * 0.8
                bv.cone_between(stems, c, end, 0.0026, 0.0016, 4, cap=False)
                for j in range(2):
                    o2 = off + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * 0.022
                    face = (o2.normalized() + Vector((0, 0, 0.6)) + axis * 0.3)
                    size = rnd.uniform(0.020, 0.030)
                    if j == 0 or rnd2.random() < 0.5:     # one or two open flowers per spur
                        blossom(tgt, c + o2, face, size * 1.08, rnd2)
                    for _ in range(42):      # entry_flowers jitters its 14-vertex sphere here
                        rnd.uniform(-1, 1)
                if k == steps or rnd2.random() < 0.35:
                    bud(tgt, end + off.normalized() * 0.006, off, 0.0065)
    common.mesh_object(f"{n}_Stems", stems, col, twig, root, smooth=False)
    common.mesh_object(f"{n}_BlossomBlush", bl, col, blush, root, smooth=False)
    common.mesh_object(f"{n}_BlossomWhite", wh, col, white, root, smooth=False)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
