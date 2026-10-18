"""Small petanque court: a 12 x 4 m bed of raked gravel (1.5 m cells) framed by teak
sleepers. Long axis X. Origin: centre, bottom on the lawn. Metres."""
import importlib
import math
import os
import sys

import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import firepit_common as fc  # noqa: E402

importlib.reload(fc)
common, outdoor = fc.common, fc.outdoor

NAME = "FirepitCourt"
P = dict(name=NAME, length=12.0, width=4.0, sleeper_w=0.16, sleeper_h=0.12, gravel_z=0.03)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = fc.new_asset(n)
    L, W, sw, sh, gz = p["length"], p["width"], p["sleeper_w"], p["sleeper_h"], p["gravel_z"]
    nx, ny = math.ceil(L / 1.5), math.ceil(W / 1.5)
    bm = bmesh.new()
    vid = {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            vid[i, j] = bm.verts.new((-L / 2 + L * i / nx, -W / 2 + W * j / ny, gz))
    for i in range(nx):
        for j in range(ny):
            bm.faces.new((vid[i, j], vid[i + 1, j], vid[i + 1, j + 1], vid[i, j + 1]))
    bm.normal_update()
    fc.orient_up(bm)
    fc.finish(bm, f"{n}_Gravel", col, root, outdoor.gravel(), uv_tile=2.0)
    ow, od = L + 2 * sw, W + 2 * sw
    fc.merge_boxes(f"{n}_Sleepers", [
        ((ow, sw, sh), (0, -W / 2 - sw / 2, sh / 2), (0, 0, 0), 0),
        ((ow, sw, sh), (0, W / 2 + sw / 2, sh / 2), (0, 0, 0), 0),
        ((sw, W, sh), (-L / 2 - sw / 2, 0, sh / 2), (0, 0, 0), 0),
        ((sw, W, sh), (L / 2 + sw / 2, 0, sh / 2), (0, 0, 0), 0)], outdoor.teak(), col, root, uv_tile=0.5)
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts
