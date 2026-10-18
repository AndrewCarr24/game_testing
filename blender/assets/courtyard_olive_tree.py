"""Mature olive tree in a large limestone bowl planter: a gnarled, fluted multi-stem
trunk that splits low into three limbs, thin branches and a canopy of clustered
alpha-tested leaf cards (silver-green olive sprigs from the shared foliage atlas).

Trunk, limbs and canopy are separate meshes, and the lower stems belong to the trunk
mesh (below 2.1 m) so the collision boxes (one per mesh) leave the ground under the
canopy free. Origin: planter centre on the floor. Units are metres.
"""
import importlib
import math
import os
import random
import sys

import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import courtyard_common as cc  # noqa: E402

importlib.reload(cc)
common = cc.common

NAME = "CourtyardOliveTree"

P = dict(
    name=NAME,
    seed=7,
    planter_h=0.64,
    soil_z=0.50,
    cards_per_lobe=64,
    card_size=(0.52, 0.74),     # min / max card edge (m)
    split_z=2.1,                # trunk mesh ends here, limbs mesh above
)


# ------------------------------------------------------------------ curves and sweeps

def spline(pts, per=6):
    q = [Vector(pts[0])] + [Vector(p) for p in pts] + [Vector(pts[-1])]
    out = []
    for i in range(1, len(q) - 2):
        p0, p1, p2, p3 = q[i - 1], q[i], q[i + 1], q[i + 2]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(Vector(pts[-1]))
    return out


def sweep(bm, pts, radii, sides, lobe=0.0, lobes=3, twist=0.0, noise=0.0, rng=None, cap_end=False):
    """Sweep a (fluted, twisted) round section along pts with per-point radii."""
    n = len(pts)
    tangents = []
    for i in range(n):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
        tangents.append((b - a).normalized())
    ref = Vector((1, 0, 0)) if abs(tangents[0].x) < 0.9 else Vector((0, 1, 0))
    nrm = (ref - tangents[0] * ref.dot(tangents[0])).normalized()
    rings = []
    for i in range(n):
        t = tangents[i]
        nrm = (nrm - t * nrm.dot(t)).normalized()        # parallel transport
        bin_ = t.cross(nrm)
        ring = []
        s = i / max(n - 1, 1)
        for k in range(sides):
            th = 2 * math.pi * k / sides
            f = 1 + lobe * math.sin(lobes * th + twist * s * 2 * math.pi)
            if noise and rng:
                f += noise * (rng.random() - 0.5)
            r = radii[i] * f
            ring.append(bm.verts.new(pts[i] + (nrm * math.cos(th) + bin_ * math.sin(th)) * r))
        rings.append(ring)
    for i in range(n - 1):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]))
    if cap_end:
        tip = bm.verts.new(pts[-1] + tangents[-1] * radii[-1] * 0.8)
        for k in range(sides):
            bm.faces.new((rings[-1][k], rings[-1][(k + 1) % sides], tip))
    return rings


def radius_profile(n, r0, r1, flare=0.0, flare_len=0.18):
    out = []
    for i in range(n):
        t = i / max(n - 1, 1)
        out.append(r0 + (r1 - r0) * t ** 0.85 + flare * math.exp(-t / flare_len))
    return out


# ------------------------------------------------------------------ planter

def build_planter(p, col, root, stone, soil):
    prof = [(0.0, 0.0), (0.74, 0.0), (0.78, 0.035), (0.90, 0.17), (1.01, 0.34), (1.075, 0.50),
            (1.085, 0.585), (1.07, 0.625), (1.03, 0.642), (0.97, 0.642), (0.935, 0.62),
            (0.915, 0.60), (0.90, 0.5)]
    prof = [(r, z) for r, z in cc_catmull(prof)]
    bowl = cc.lathe(prof, 64, f"{p['name']}_Planter", col, stone, root, sharp=50)
    cc.round_uv(bowl, tile=3.0)
    sp = [(0.0, p["soil_z"] + 0.03), (0.45, p["soil_z"] + 0.025), (0.92, p["soil_z"] - 0.005), (0.92, 0.35)]
    s = cc.lathe(sp, 32, f"{p['name']}_Soil", col, soil, root, sharp=80)
    # a ring of pale pebbles around the trunk collar for a finished look
    return bowl, s


def cc_catmull(pts, per=3):
    """Dense Catmull-Rom through (r, z) control points, keeping the first/last exact
    and leaving sharp points (rim) to the profile list itself."""
    q = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(q) - 2):
        p0, p1, p2, p3 = q[i - 1], q[i], q[i + 1], q[i + 2]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t +
                                    (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 +
                                    (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(pts[-1])
    return [(r, max(z, 0.0)) for r, z in out]


# ------------------------------------------------------------------ tree

STEMS = [   # fork -> end control points (x, y, z), radius at the fork and tip
    dict(pts=[(0.05, 0.0, 1.22), (-0.40, 0.18, 1.7), (-0.86, 0.30, 2.35), (-1.25, 0.38, 3.0), (-1.55, 0.30, 3.45)], r=(0.17, 0.06)),
    dict(pts=[(0.05, 0.0, 1.22), (0.40, -0.35, 1.75), (0.78, -0.62, 2.4), (1.12, -0.75, 3.05), (1.45, -0.72, 3.5)], r=(0.16, 0.055)),
    dict(pts=[(0.05, 0.0, 1.22), (0.02, 0.38, 1.85), (-0.05, 0.62, 2.6), (0.12, 0.72, 3.35), (0.35, 0.62, 3.95)], r=(0.15, 0.05)),
]


def build_tree(p, col, root, bark, leaf):
    rng = random.Random(p["seed"])
    n = p["name"]
    trunk_bm, limb_bm = bmesh.new(), bmesh.new()

    # trunk: slightly leaning, flared at the root
    base = spline([(0, 0, p["soil_z"] - 0.06), (0.03, -0.03, 0.62), (0.0, 0.02, 0.95), (0.05, 0.0, 1.22)], per=6)
    sweep(trunk_bm, base, radius_profile(len(base), 0.205, 0.19, flare=0.11, flare_len=0.12),
          sides=16, lobe=0.2, lobes=4, twist=0.6, noise=0.06, rng=rng)

    ends = []
    for k, st in enumerate(STEMS):
        pts = spline([(x * 0.85, y * 0.85, z) for x, y, z in st["pts"]], per=7)
        rad = radius_profile(len(pts), st["r"][0], st["r"][1])
        cut = next((i for i, q in enumerate(pts) if q.z >= p["split_z"]), len(pts) - 1)
        sweep(trunk_bm, pts[:cut + 1], rad[:cut + 1], sides=12, lobe=0.10, lobes=3, twist=0.8 + k, noise=0.04, rng=rng)
        sweep(limb_bm, pts[cut:], rad[cut:], sides=10, lobe=0.08, lobes=3, twist=0.8 + k, noise=0.03, rng=rng, cap_end=True)
        ends.append((pts[-1], pts[-6], pts[-12]))

    # canopy lobes (cx, cy, cz, rx, ry, rz); lowest leaves stay above ~2.3 m
    lobes = []
    for i in range(7):
        a = 2 * math.pi * i / 7 + rng.uniform(-0.2, 0.2)
        r = rng.uniform(1.0, 1.35)
        lobes.append((r * math.cos(a), r * math.sin(a) * 0.9, rng.uniform(3.15, 3.55),
                      rng.uniform(0.78, 0.95), rng.uniform(0.78, 0.95), rng.uniform(0.58, 0.72)))
    for i in range(4):
        a = 2 * math.pi * i / 4 + rng.uniform(0, 1.2)
        r = rng.uniform(0.2, 0.6)
        lobes.append((r * math.cos(a), r * math.sin(a), rng.uniform(3.8, 4.1),
                      rng.uniform(0.75, 0.9), rng.uniform(0.75, 0.9), rng.uniform(0.5, 0.62)))
    # thin branches from each limb tip up into the nearest lobes
    for L in lobes:
        c = Vector(L[:3])
        tip = min((e[0] for e in ends), key=lambda q: (q - c).length)
        mid = tip.lerp(c, 0.5) + Vector((rng.uniform(-0.15, 0.15), rng.uniform(-0.15, 0.15), 0.1))
        pts = spline([tip, mid, c.lerp(tip, 0.15)], per=4)
        sweep(limb_bm, pts, radius_profile(len(pts), 0.042, 0.012), sides=6, noise=0.04, rng=rng, cap_end=True)

    trunk = common.mesh_object(f"{n}_Trunk", trunk_bm, col, bark, root)
    limbs = common.mesh_object(f"{n}_Limbs", limb_bm, col, bark, root)

    # leaf cards
    cb = bmesh.new()
    uvl = cb.loops.layers.uv.new("UVMap")
    smin, smax = p["card_size"]
    for (cx, cy, cz, rx, ry, rz) in lobes:
        c = Vector((cx, cy, cz))
        for _ in range(p["cards_per_lobe"]):
            while True:
                d = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
                if 0.01 < d.length <= 1.0:
                    break
            d = d.normalized() * (0.45 + 0.55 * rng.random() ** 0.5)
            pos = c + Vector((d.x * rx, d.y * ry, d.z * rz))
            out = Vector((d.x / rx, d.y / ry, d.z / rz)).normalized()
            up = (out + Vector((0, 0, 0.45)) + Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.6, 0.6))) * 0.7).normalized()
            helper = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
            right = up.cross(helper)
            if right.length < 1e-3:
                right = up.cross(Vector((1, 0, 0)))
            right.normalize()
            size = rng.uniform(smin, smax)
            cc.add_card(cb, uvl, pos + up * size * 0.32, right * size * 0.5, up * size * 0.5,
                        "sprigA" if rng.random() < 0.5 else "sprigB", flip=rng.random() < 0.5)
    me_obj = common.mesh_object(f"{n}_Canopy", cb, col, leaf, root, smooth=False)
    return trunk, limbs, me_obj


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    stone, soil, bark, leaf = cc.limestone_mat(), cc.soil_mat(), cc.bark_mat(), cc.foliage_mat()
    build_planter(p, col, root, stone, soil)
    build_tree(p, col, root, bark, leaf)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
