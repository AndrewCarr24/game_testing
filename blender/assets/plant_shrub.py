"""Shrub generator for the estate's planting (wrapped by plant_shrub_round / _box / _grass /
_lavender). Tiny, low-poly, lit per vertex (baked) like everything outdoors.

Origin: centre of the base on the ground (z = 0, slightly sunk), z up, units metres.
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plant_common as pc  # noqa: E402

importlib.reload(pc)
common, outdoor = pc.common, pc.outdoor

NAME = "PlantShrub"
P = dict(name=NAME, kind="round", seed=1)

STRAW = (0.36, 0.27, 0.115)          # dry ornamental grass blades
STRAW_BASE = (0.17, 0.17, 0.055)     # greener at the crown of the clump
LAV_MOUND = (0.07, 0.085, 0.06)    # grey-green leaves
LAV_FLOWER = (0.125, 0.105, 0.17)   # grey-violet spikes


def v3(x, y, z):
    return Vector((x, y, z))


def shrub_round(p, rng, mats):
    """Boxwood ball, 1 m: a clipped, faintly lumpy sphere sitting on the ground."""
    bm = mats["foliage"]
    pc.blob(bm, v3(0, 0, 0.49), (0.5, 0.5, 0.5), rng, subdiv=2, lump=0.035, jitter=0.012, flat_bottom=1.0)


def shrub_box(p, rng, mats):
    """Clipped cube 1 x 1 x 0.8 m with softly rounded edges."""
    bm = mats["foliage"]
    g = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(1.0, 1.0, 0.8), verts=g["verts"])
    bmesh.ops.translate(bm, vec=(0, 0, 0.4), verts=g["verts"])
    r = bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.09, segments=1, affect="EDGES")
    for f in bm.faces:
        f.smooth = False


def blade(bm_top, bm_low, base, azimuth, length, arch, width):
    """Arching blade, 3-sided tapered prism: lower part (green-straw) + upper part (straw).
    arch 0 = upright, 1 = fully arched over."""
    dirv = v3(math.cos(azimuth), math.sin(azimuth), 0)
    side = dirv.cross(v3(0, 0, 1))
    pts = [base,
           base + dirv * (length * (0.04 + 0.26 * arch)) + v3(0, 0, length * (0.5 - 0.04 * arch)),
           base + dirv * (length * (0.10 + 0.72 * arch)) + v3(0, 0, length * (0.97 - 0.66 * arch))]

    def ring(bm, c, t, w):
        nm = side.cross(t).normalized()
        return [bm.verts.new(c + side * w), bm.verts.new(c - side * w * 0.5 + nm * w * 0.85),
                bm.verts.new(c - side * w * 0.5 - nm * w * 0.85)]
    t0 = (pts[1] - pts[0]).normalized()
    t1 = (pts[2] - pts[0]).normalized()
    r0 = ring(bm_low, pts[0], t0, width)
    r1 = ring(bm_low, pts[1], t1, width * 0.72)
    for k in range(3):
        j = (k + 1) % 3
        bm_low.faces.new((r0[k], r0[j], r1[j], r1[k]))
    r1b = ring(bm_top, pts[1], t1, width * 0.72)
    tip = bm_top.verts.new(pts[2])
    for k in range(3):
        j = (k + 1) % 3
        bm_top.faces.new((r1b[k], r1b[j], tip))


def shrub_grass(p, rng, mats):
    """Ornamental grass clump (Miscanthus / Stipa): a fountain of arching straw blades."""
    top, low = mats["straw"], mats["straw_base"]
    n = 13
    for i in range(n):
        a = 2.399 * i + rng.uniform(-0.2, 0.2)
        arch = min(1.0, (i / n) ** 0.7 * rng.uniform(0.75, 1.15) + 0.05)
        ln = rng.uniform(0.85, 1.1) * (1.0 - 0.18 * arch)
        base = v3(rng.uniform(-0.04, 0.04), rng.uniform(-0.04, 0.04), -0.02)
        blade(top, low, base, a, ln, 1 - arch if i % 2 else arch, 0.028)


def shrub_lavender(p, rng, mats):
    """Lavender mound, 0.9 m wide x 0.6 m: grey-green leaves under a bumpy dome of
    grey-violet flower heads with a few spikes standing out."""
    pc.blob(mats["lav_leaf"], v3(0, 0, 0.12), (0.38, 0.38, 0.34), rng, subdiv=1, lump=0.1, jitter=0.05,
            flat_bottom=0.4)
    fl = mats["lav_flower"]
    spots = [(0, 0, 0.3, 0.27)]
    for i in range(5):
        a = 2 * math.pi * i / 5 + rng.uniform(-0.3, 0.3)
        spots.append((0.24 * math.cos(a), 0.24 * math.sin(a), 0.2 + rng.uniform(-0.02, 0.03), 0.22))
    for x, y, z, r in spots:
        pc.blob(fl, v3(x, y, z), (r * 1.15, r * 1.15, r * 0.85), rng, subdiv=1, lump=0.25, jitter=0.1,
                flat_bottom=0.6)
    for i in range(5):
        a = 2 * math.pi * i / 5 + rng.uniform(-0.4, 0.4)
        r = rng.uniform(0.1, 0.3)
        base = v3(r * math.cos(a), r * math.sin(a), 0.36 + 0.08 * (1 - r / 0.3))
        tilt = 0.35 * r / 0.3
        L = rng.uniform(0.14, 0.2)
        d = v3(math.cos(a) * tilt, math.sin(a) * tilt, 1).normalized()
        side = d.cross(v3(0, 0, 1))
        side = side.normalized() if side.length > 1e-3 else v3(1, 0, 0)
        nrm = d.cross(side).normalized()
        w = 0.026
        ring = [fl.verts.new(base + (side * math.cos(th) + nrm * math.sin(th)) * w) for th in (0, 2.094, 4.189)]
        tv = fl.verts.new(base + d * L)
        for k in range(3):
            fl.faces.new((ring[k], ring[(k + 1) % 3], tv))


KINDS = {"round": shrub_round, "box": shrub_box, "grass": shrub_grass, "lavender": shrub_lavender}


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rng = pc.rng_for(p["seed"])
    col, root = pc.new_asset(n)
    kind = p["kind"]
    bms = {k: bmesh.new() for k in ("foliage", "straw", "straw_base", "lav_leaf", "lav_flower")}
    KINDS[kind](p, rng, bms)
    mats = {"foliage": ("Leaves", outdoor.foliage),
            "straw": ("Blades", lambda: outdoor.flat("M_Out_GrassStraw", STRAW)),
            "straw_base": ("Base", lambda: outdoor.flat("M_Out_GrassBase", STRAW_BASE)),
            "lav_leaf": ("Leaves", lambda: outdoor.flat("M_Out_LavenderLeaf", LAV_MOUND)),
            "lav_flower": ("Flowers", lambda: outdoor.flat("M_Out_LavenderFlower", LAV_FLOWER))}
    for bm in bms.values():
        for v in bm.verts:
            v.co.z = max(v.co.z, 0.0)
    for key, bm in bms.items():
        if not bm.verts:
            bm.free()
            continue
        part, mk = mats[key]
        ob = common.mesh_object(f"{n}_{part}", bm, col, mk(), root)
        if key == "foliage":
            common.box_uv(ob, tile=1.5)
    return root, pc.parts_of(root)


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
