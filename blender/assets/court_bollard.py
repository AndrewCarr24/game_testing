"""Low landscape bollard light: a slim dark-metal square post with a glowing warm lens band
below a flat cap (outdoor.lamp(), emission kept in the baked grounds). 0.9 m tall.
Origin: floor centre."""
import importlib
import os
import sys

import bmesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import court_common as cc  # noqa: E402

importlib.reload(cc)
common, outdoor = cc.common, cc.outdoor

NAME = "CourtBollard"
P = dict(name=NAME, size=0.14, height=0.9, lens_z=(0.72, 0.82), cap=0.02)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root = cc.start(n)
    s = p["size"] / 2
    l0, l1 = p["lens_z"]
    H, c = p["height"], p["cap"]
    bm = bmesh.new()
    cc.box(bm, (-s, -s, 0), (s, s, l0), cell=4.0, top=False)
    cc.box(bm, (-s - c, -s - c, l1), (s + c, s + c, H), cell=4.0, bottom=True)
    cc.finish(f"{n}_Post", bm, outdoor.dark_metal(), col, root)
    bm = bmesh.new()
    cc.box(bm, (-s - 0.004, -s - 0.004, l0), (s + 0.004, s + 0.004, l1), cell=4.0, top=False)
    cc.finish(f"{n}_Lens", bm, outdoor.lamp(), col, root)
    parts = [o for o in root.children]
    return root, parts
