"""Circular limestone fire terrace: a 10 m disc raised 0.2 m above the lawn, paved in 1 m
cells (so the baked light can show shadows), a vertical riser all round and a fine
black-steel inlay ring. Origin: centre, bottom on the lawn (z = 0). Units are metres."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import firepit_common as fc  # noqa: E402

importlib.reload(fc)
common, outdoor = fc.common, fc.outdoor

NAME = "FirepitTerrace"
P = dict(
    name=NAME,
    radius=5.0,
    height=0.20,
    cells=10,            # grid cells per side of the square that is mapped onto the disc
    inlay_r=3.55,        # radius of the black steel line set into the paving
    inlay_w=0.035,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = fc.new_asset(n)
    R, H, N = p["radius"], p["height"], p["cells"]

    # --- top: a square grid mapped onto the disc (all quads, no slivers)
    bm = bmesh.new()
    vid = {}
    for i in range(N + 1):
        for j in range(N + 1):
            u, v = -1 + 2 * i / N, -1 + 2 * j / N
            x = R * u * math.sqrt(1 - v * v / 2)
            y = R * v * math.sqrt(1 - u * u / 2)
            vid[i, j] = bm.verts.new((x, y, H))
    for i in range(N):
        for j in range(N):
            bm.faces.new((vid[i, j], vid[i + 1, j], vid[i + 1, j + 1], vid[i, j + 1]))
    bm.normal_update()
    fc.orient_up(bm)
    # --- riser: drop every boundary edge to the lawn
    bm.edges.ensure_lookup_table()
    for e in [e for e in bm.edges if len(e.link_faces) == 1]:
        a, b = e.verts
        a0 = bm.verts.new((a.co.x, a.co.y, 0.0))
        b0 = bm.verts.new((b.co.x, b.co.y, 0.0))
        f = bm.faces.new((a, b, b0, a0))
        mid = (a.co + b.co) / 2
        f.normal_update()
        if Vector((mid.x, mid.y, 0)).dot(f.normal) < 0:
            f.normal_flip()
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    fc.finish(bm, f"{n}_Paving", col, root, outdoor.stone(), uv_tile=2.0)

    # --- inlay line
    bm = bmesh.new()
    segs = 36
    r0, r1, z = p["inlay_r"] - p["inlay_w"] / 2, p["inlay_r"] + p["inlay_w"] / 2, H + 0.004
    ring = [(bm.verts.new((r0 * math.cos(t), r0 * math.sin(t), z)),
             bm.verts.new((r1 * math.cos(t), r1 * math.sin(t), z)))
            for t in (2 * math.pi * k / segs for k in range(segs))]
    for k in range(segs):
        a, b = ring[k], ring[(k + 1) % segs]
        bm.faces.new((a[0], a[1], b[1], b[0]))
    bm.normal_update()
    fc.orient_up(bm)
    fc.finish(bm, f"{n}_Inlay", col, root, fc.edging())

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts
