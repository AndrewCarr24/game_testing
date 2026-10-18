"""Entrance canopy for the motor court: a thin flat white-render roof slab, 12 x 5 m,
cantilevered out from the glass front (its back edge meets the facade, y = -20 in the world)
and carried at the front by two slender dark-metal blade columns, with a teak soffit and a
row of small warm downlights. Placed on the stone terrace at world (0, -22.5), z 0.06.

Origin: the middle of the footprint on the terrace. Front (south) is -Y, the glass wall is +Y.
"""
import importlib
import math
import os
import sys

import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import court_common as cc  # noqa: E402

importlib.reload(cc)
common, outdoor = cc.common, cc.outdoor

NAME = "CourtCanopy"

P = dict(
    name=NAME,
    width=12.0,
    depth=5.0,
    soffit_z=3.2,           # underside of the roof above the terrace
    slab_t=0.26,
    col_x=3.9,              # column centre lines (+/-)
    col_y_in=0.9,           # columns this far behind the front edge
    col_size=(0.16, 0.42),  # section: x (thin, seen from the court) by y
    light_cols=5,
    light_rows=(1.0, 3.0),  # downlight rows, metres behind the front edge
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = cc.start(n)
    W, D = p["width"], p["depth"]
    z0, t = p["soffit_z"], p["slab_t"]
    x0, x1, y0, y1 = -W / 2, W / 2, -D / 2, D / 2

    # white render slab: top, underside, front and side faces (no back face: it meets the facade)
    bm = bmesh.new()
    cc.box(bm, (x0, y0, z0), (x1, y1, z0 + t), bottom=True, sides="sew")
    cc.finish(f"{n}_Slab", bm, outdoor.render_white(), col, root)

    # teak soffit, a 1 cm proud panel inset from the edges (the slab shows as a render reveal)
    bm = bmesh.new()
    inset = 0.14
    cc.panel(bm, (x0 + inset, y0 + inset, z0 - 0.012), (0, D - 2 * inset, 0), (W - 2 * inset, 0, 0))
    cc.finish(f"{n}_Soffit", bm, outdoor.teak(), col, root, uv_tile=0.5)

    # columns
    bm = bmesh.new()
    cx, cy = p["col_size"]
    for sx in (-1, 1):
        x = sx * p["col_x"]
        y = y0 + p["col_y_in"]
        cc.box(bm, (x - cx / 2, y - cy / 2, 0), (x + cx / 2, y + cy / 2, z0 - 0.012), cell=4.0, top=False)
        # base plate
        cc.box(bm, (x - cx / 2 - 0.05, y - cy / 2 - 0.05, 0), (x + cx / 2 + 0.05, y + cy / 2 + 0.05, 0.03), cell=4.0)
    cc.finish(f"{n}_Columns", bm, outdoor.dark_metal(), col, root)

    # downlights (glowing discs in the soffit)
    bm = bmesh.new()
    nl = p["light_cols"]
    for k in range(nl):
        x = x0 + W * (k + 0.5) / nl
        for row in p["light_rows"]:
            y = y0 + row
            ring = [bm.verts.new((x + 0.08 * math.cos(a), y + 0.08 * math.sin(a), z0 - 0.02))
                    for a in [2 * math.pi * i / 8 for i in range(8)]]
            bm.faces.new(ring[::-1])
    cc.finish(f"{n}_Lights", bm, outdoor.lamp(), col, root)

    parts = [o for o in root.children]
    return root, parts
