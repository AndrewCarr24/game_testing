"""Open bronze ring on a low stone plinth: a thick polished band, 5 m across, standing on
its edge and leaning back a few degrees. The band swells towards the base and thins to
its two ends, which overlap in depth across a gap near the top, so the ring reads as one
continuous gesture rather than a closed hoop. Origin: floor centre of the plinth; the
ring faces -Y (seen as a circle from the south side of the lawn)."""
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

NAME = "LawnSculptureRing"

P = dict(
    name=NAME,
    radius=2.75,        # centre line radius (m)
    thick=0.36,         # radial thickness of the band
    depth_max=1.15,     # band depth (front to back) at the base
    depth_min=0.42,     # ... at the ends
    arc_start=64.0,     # arc runs CCW from here (degrees, 0 = +x, 90 = up) ...
    arc_end=-244.0,     # ... clockwise round the bottom to here (a 308 degree arc)
    drift=0.5,         # ends sit +-drift apart in depth (a shallow spiral)
    lean=7.0,           # tilt back, degrees
    segments=56,
    plinth=(4.0, 1.6, 0.26),
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    bronze, stone = lc.bronze_polished(), outdoor.stone()

    px, py, ph = p["plinth"]
    lc.box(f"{n}_Plinth", (-px / 2, -py / 2, 0), (px / 2, py / 2, ph), stone, col, root, uv_tile=2.0)

    R, t = p["radius"], p["thick"]
    a0, a1 = math.radians(p["arc_start"]), math.radians(p["arc_end"])
    bm = bmesh.new()
    rings = []
    N = p["segments"]
    for i in range(N + 1):
        s = i / N
        phi = a0 + (a1 - a0) * s
        # depth: full at the base (phi = -90 deg), tapering towards both ends
        d = p["depth_min"] + (p["depth_max"] - p["depth_min"]) * math.sin(math.pi * s) ** 0.8
        yc = -p["drift"] + 2 * p["drift"] * s
        er = Vector((math.cos(phi), 0, math.sin(phi)))
        c = er * R + Vector((0, yc, 0))
        y = Vector((0, 1, 0))
        ring = [c + er * (t / 2) - y * (d / 2), c + er * (t / 2) + y * (d / 2),
                c - er * (t / 2) + y * (d / 2), c - er * (t / 2) - y * (d / 2)]
        rings.append(ring)
    lc.sweep(bm, rings, cap=True)
    lc.finish_solid(bm)
    # stand it on the plinth: lowest point of the band touches z = plinth top - 0.05 (set in)
    lean = Matrix.Rotation(math.radians(-p["lean"]), 4, "X")
    bm.transform(lean)
    low = min(v.co.z for v in bm.verts)
    bmesh.ops.translate(bm, vec=(0, 0, ph - 0.04 - low), verts=bm.verts)
    lc.finish(f"{n}_Band", bm, col, root, bronze, smooth=True)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
