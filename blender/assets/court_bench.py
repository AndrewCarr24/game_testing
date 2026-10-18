"""Monolithic limestone bench with a teak seat plank: 2.6 x 0.5 m, 0.46 m high, on a recessed
dark shadow gap. Meant for the fountain plaza. Origin: floor centre; the seat faces -Y."""
import importlib
import os
import sys

import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import court_common as cc  # noqa: E402

importlib.reload(cc)
common, outdoor = cc.common, cc.outdoor

NAME = "CourtBench"
P = dict(name=NAME, length=2.6, depth=0.5, height=0.46, seat_t=0.05, gap=0.06, inset=0.05)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = cc.start(n)
    hl, hd, H, st, g, i = p["length"] / 2, p["depth"] / 2, p["height"], p["seat_t"], p["gap"], p["inset"]
    bm = bmesh.new()
    cc.box(bm, (-hl, -hd, g), (hl, hd, H - st), cell=4.0, top=False, bottom=True)
    cc.finish(f"{n}_Stone", bm, outdoor.stone(), col, root, uv_tile=2.0)
    bm = bmesh.new()
    cc.box(bm, (-hl - 0.01, -hd - 0.01, H - st), (hl + 0.01, hd + 0.01, H), cell=4.0, bottom=True)
    cc.finish(f"{n}_Seat", bm, outdoor.teak(), col, root, uv_tile=0.5)
    bm = bmesh.new()
    cc.box(bm, (-hl + i, -hd + i, 0), (hl - i, hd - i, g + 0.01), cell=4.0, top=False)
    cc.finish(f"{n}_Base", bm, outdoor.dark_metal(), col, root)
    parts = [o for o in root.children]
    return root, parts
