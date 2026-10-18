"""Pierced stone stele: a tall tapering monolith of honed pale stone with a slanted top and
a circular opening lined with a bronze sleeve, standing in a shallow stone footing.
About 5.4 m tall; the broad faces look north-south. Origin: floor centre."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lawn_common as lc  # noqa: E402

importlib.reload(lc)
common, outdoor = lc.common, lc.outdoor

NAME = "LawnSculptureStele"

P = dict(
    name=NAME,
    base_w=2.15, top_w=1.45,           # width at the foot / at the top
    thick=0.70,                         # front to back
    h_left=5.95, h_right=5.25,          # the top edge slopes
    hole=(0.06, 3.85, 0.70),            # x, z, radius of the opening
    foot=(2.8, 1.4, 0.15),            # footing slab
    ring_n=20,                          # segments round the opening
    sleeve=0.05,                        # how far the bronze sleeve stands proud
)


def _ray_hit(poly, c, ang):
    """Distance along `ang` from c to the boundary of the convex polygon."""
    d = Vector((math.cos(ang), math.sin(ang)))
    best = 1e9
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        e = b - a
        den = d.x * e.y - d.y * e.x
        if abs(den) < 1e-9:
            continue
        w = a - c
        t = (w.x * e.y - w.y * e.x) / den
        s = (w.x * d.y - w.y * d.x) / den
        if t > 0 and -1e-6 <= s <= 1 + 1e-6:
            best = min(best, t)
    return d * best


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    stone, bronze, footing = lc.stone_pale(), lc.bronze_polished(), outdoor.stone()

    fx, fy, fz = p["foot"]
    lc.box(f"{n}_Foot", (-fx / 2, -fy / 2, 0), (fx / 2, fy / 2, fz), footing, col, root, uv_tile=2.0)

    bw, tw, T = p["base_w"], p["top_w"], p["thick"]
    z0 = fz - 0.02
    poly = [Vector((-bw / 2, z0)), Vector((bw / 2, z0)),
            Vector((tw / 2, p["h_right"] + fz)), Vector((-tw / 2, p["h_left"] + fz))]
    hx, hz, hr = p["hole"]
    hz += fz
    c = Vector((hx, hz))
    angs = {math.atan2(v.y - c.y, v.x - c.x) for v in poly}
    angs |= {2 * math.pi * k / p["ring_n"] - math.pi + 0.013 for k in range(p["ring_n"])}
    angs = sorted(angs)
    bm = bmesh.new()
    y0, y1 = -T / 2, T / 2
    outer = [c + _ray_hit(poly, c, a) for a in angs]
    inner = [c + Vector((math.cos(a), math.sin(a))) * hr for a in angs]
    V = {}
    for name, pts in (("o", outer), ("i", inner)):
        for side, y in (("f", y0), ("b", y1)):
            V[name, side] = [bm.verts.new((q.x, y, q.y)) for q in pts]
    m = len(angs)
    for k in range(m):
        k2 = (k + 1) % m
        # front annulus (-y), back annulus (+y), outer wall, hole wall
        bm.faces.new((V["o", "f"][k], V["o", "f"][k2], V["i", "f"][k2], V["i", "f"][k]))
        bm.faces.new((V["o", "b"][k2], V["o", "b"][k], V["i", "b"][k], V["i", "b"][k2]))
        bm.faces.new((V["o", "f"][k2], V["o", "f"][k], V["o", "b"][k], V["o", "b"][k2]))
        bm.faces.new((V["i", "f"][k], V["i", "f"][k2], V["i", "b"][k2], V["i", "b"][k]))
    lc.finish_solid(bm, 40)
    lc.refine(bm, 1.5)
    lc.finish("%s_Stone" % n, bm, col, root, stone, smooth=False)

    # bronze sleeve lining the opening, standing slightly proud of both faces
    sb = bmesh.new()
    s, r_in, r_out = p["sleeve"], hr - 0.045, hr + 0.07
    rings = []
    for k in range(p["ring_n"]):
        a = 2 * math.pi * k / p["ring_n"]
        ca, sa = math.cos(a), math.sin(a)
        prof = [(r_in, -(T / 2 + s)), (r_out, -(T / 2 + s)), (r_out, -(T / 2 - 0.02)), (r_in + 0.0, -(T / 2 + s))]
        prof = [(r_in, -(T / 2 + s)), (r_out, -(T / 2 + s)), (r_out, T / 2 + s), (r_in, T / 2 + s)]
        rings.append([(hx + r * ca, y, hz + r * sa) for r, y in prof])
    lc.sweep(sb, rings, loop=True)
    lc.finish_solid(sb, 40)
    lc.finish(f"{n}_Sleeve", sb, col, root, bronze, smooth=False)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
