"""Raised planting bed, 4.2 x 1.6 m stadium, mounded soil held by black steel edging. The
planting assets go on top. Long axis along Y. Origin: centre, bottom on the lawn. Metres."""
import importlib
import math
import os
import sys

import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import firepit_common as fc  # noqa: E402

importlib.reload(fc)
common, outdoor = fc.common, fc.outdoor

NAME = "FirepitBed"
P = dict(name=NAME, length=4.2, width=1.6, soil_h=0.07, edge_h=0.10, end_steps=4)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = fc.new_asset(n)
    L, W, sh, eh, es = p["length"], p["width"], p["soil_h"], p["edge_h"], p["end_steps"]
    r = W / 2
    half = L / 2 - r
    pts = []
    for k in range(es + 1):                       # +Y end, east to west
        a = math.radians(0 + 180 * k / es)
        pts.append((r * math.cos(a), half + r * math.sin(a)))
    for k in range(es + 1):                       # -Y end, west to east
        a = math.radians(180 + 180 * k / es)
        pts.append((r * math.cos(a), -half + r * math.sin(a)))
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, sh)) for x, y in pts]
    bm.faces.new(vs)
    bm.normal_update()
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    fc.orient_up(bm)
    fc.finish(bm, f"{n}_Soil", col, root, outdoor.soil())
    bm = fc.wall_loop_bm(pts, 0.012, 0.0, eh)
    bm.normal_update()
    fc.fix_outward(bm)
    fc.finish(bm, f"{n}_Edging", col, root, fc.edging())
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts
