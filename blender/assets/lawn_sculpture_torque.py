"""Torqued steel walls: two tall, gently S-curved plates of dark weathered steel that lean
and twist as they rise, so the passage between them narrows towards the top. After the
big torqued-plate sculptures of landscape art; abstract, 4.2 m high, about 6.5 m long.
Origin: floor centre; the walls run along X."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lawn_common as lc  # noqa: E402

importlib.reload(lc)
common, outdoor = lc.common, lc.outdoor

NAME = "LawnSculptureTorque"

P = dict(
    name=NAME,
    length=7.4,
    height=4.8,
    thick=0.10,
    gap=2.4,           # distance between the two walls at the foot (m)
    narrow=0.45,       # the gap shrinks by this fraction at the top
    bow=1.0,           # amplitude of the S curve in plan
    lean=1.5,          # how far the top is shifted sideways
    twist=12.0,        # degrees the top is turned relative to the foot
    stations=12,
    levels=4,
)


def _wall(n, p, side, col, root, mat):
    """One plate of the pair. side = +1 / -1: which side of the shared S-curved centre line."""
    L, H, t = p["length"], p["height"], p["thick"]
    N, M = p["stations"], p["levels"]
    rings = []
    for i in range(N + 1):
        u = i / N
        x = L * (u - 0.5)
        y = p["bow"] * math.sin(2 * math.pi * (u - 0.5))
        dy = p["bow"] * 2 * math.pi / L * math.cos(2 * math.pi * (u - 0.5))
        tan = Vector((1, dy, 0)).normalized()
        nor = Vector((-tan.y, tan.x, 0))
        side_a, side_b = [], []
        for j in range(M + 1):
            v = j / M
            ease = v * v * (3 - 2 * v) * 0.4 + v * 0.6
            half = p["gap"] / 2 * (1 - p["narrow"] * ease)      # the passage closes towards the top
            pt = Vector((x, y, 0)) + nor * (side * half)
            pt.y += p["lean"] * ease
            pt = Matrix.Rotation(math.radians(p["twist"]) * ease, 3, "Z") @ pt
            tn = Matrix.Rotation(math.radians(p["twist"]) * ease, 3, "Z") @ nor
            z = Vector((0, 0, H * v))
            side_a.append(pt + tn * (t / 2) + z)
            side_b.append(pt - tn * (t / 2) + z)
        rings.append(side_a + side_b[::-1])
    bm = bmesh.new()
    lc.sweep(bm, rings, cap=True)
    lc.finish_solid(bm, 60)
    return lc.finish(f"{n}_Wall{'A' if side > 0 else 'B'}", bm, col, root, mat, smooth=True)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    mat = lc.steel_weathered()
    _wall(n, p, +1, col, root, mat)
    _wall(n, p, -1, col, root, mat)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
