"""Raked pale gravel path, 1.8 m wide, set 2 cm proud of the lawn and held by black steel
edging. Runs along Y (length param), centred on the origin, so the end cells line up with
a neighbour placed a `length` further on. Bottom on the lawn. Metres."""
import importlib
import math
import os
import sys

import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import firepit_common as fc  # noqa: E402

importlib.reload(fc)
common, outdoor = fc.common, fc.outdoor

NAME = "FirepitPath"
P = dict(name=NAME, length=9.0, width=1.8, proud=0.02, edge_t=0.03, edge_h=0.05)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = fc.new_asset(n)
    L, W, z = p["length"], p["width"], p["proud"]
    nx = max(1, math.ceil(W / 1.0))
    ny = max(1, math.ceil(L / 1.5))
    bm = bmesh.new()
    vid = {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            vid[i, j] = bm.verts.new((-W / 2 + W * i / nx, -L / 2 + L * j / ny, z))
    for i in range(nx):
        for j in range(ny):
            bm.faces.new((vid[i, j], vid[i + 1, j], vid[i + 1, j + 1], vid[i, j + 1]))
    bm.normal_update()
    fc.orient_up(bm)
    fc.finish(bm, f"{n}_Gravel", col, root, outdoor.gravel(), uv_tile=2.0)
    et, eh = p["edge_t"], p["edge_h"]
    fc.merge_boxes(f"{n}_Edging",
                   [((et, L, eh), (sx * (W / 2 + et / 2), 0, eh / 2), (0, 0, 0), 0) for sx in (-1, 1)],
                   fc.edging(), col, root)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts
