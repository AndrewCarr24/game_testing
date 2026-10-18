"""Teak pool lounger: two rails on four legs, a hinged reclined back, sand mattress in two
parts and a folded towel. Foot end toward -Y (it faces -Y like a chair), head end at +Y.
Origin: floor centre. ~190 triangles; lounger() draws one into any Builder (the pair
and the in-water variant reuse it). Real geometry only (no modifiers)."""
import importlib
import math
import os
import sys

from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pool_common as pc  # noqa: E402

importlib.reload(pc)
common = pc.common

NAME = "PoolLounger"

P = dict(
    name=NAME,
    width=0.74,
    foot=-1.0,
    hinge=0.05,
    frame_z=0.34,        # top of the rails
    back_deg=38.0,
    back_len=1.10,
    towel=True,
)


def lounger(b, p, teak=None, sand=None, towel=None):
    """Draw one lounger into builder b (current transform applies)."""
    teak = teak or pc.teak()
    sand = sand or pc.sand()
    towel = towel or pc.towel()
    W, y_foot, hinge, fz = p["width"], p["foot"], p["hinge"], p["frame_z"]
    a = math.radians(p["back_deg"])
    bl = p["back_len"]
    rt, rh = 0.05, 0.065
    xr = W / 2 - rt / 2
    leg = 0.05
    # side rails of the flat part, legs under them
    for sx in (-1, 1):
        b.box(teak, (sx * xr - rt / 2, y_foot, fz - rh), (sx * xr + rt / 2, hinge + 0.03, fz), tile=0.5,
              skip=("-z",), grain=1)
        for ly in (y_foot + 0.07, hinge - 0.04):
            b.box(teak, (sx * xr - leg / 2, ly - leg / 2, 0), (sx * xr + leg / 2, ly + leg / 2, fz - rh),
                  tile=0.5, skip=("-z", "+z"), grain=2)
    # foot slat (the end of the deck seen from the front)
    b.box(teak, (-xr, y_foot, fz - 0.03), (xr, y_foot + 0.07, fz), tile=0.5, skip=("-z", "+y", "-x", "+x"), grain=0)
    # back frame: rails in a frame rotated about the hinge
    b.push(Matrix.Translation((0, hinge, fz)) @ Matrix.Rotation(a, 4, "X"))
    for sx in (-1, 1):
        b.box(teak, (sx * xr - rt / 2, 0.0, -rh), (sx * xr + rt / 2, bl, 0.0), tile=0.5, skip=("-y",), grain=1)
    b.box(teak, (-xr, bl - 0.06, -0.03), (xr, bl, 0.0), tile=0.5, skip=("-y", "-x", "+x", "+z"), grain=0)
    # back mattress
    mt = 0.09
    b.chamfer_box(sand, (-W / 2 + 0.045, 0.02, 0.0), (W / 2 - 0.045, bl - 0.03, mt), r=0.022)
    b.pop()
    # prop strut: from under the back to the floor behind the hinge
    top_y = hinge + 0.62 * math.cos(a)
    top_z = fz + 0.62 * math.sin(a) - 0.05
    bot_y, bot_z = hinge + 0.10, 0.02
    ln = math.hypot(top_y - bot_y, top_z - bot_z)
    ang = math.atan2(top_y - bot_y, top_z - bot_z)       # tilt of the strut from vertical
    b.push(Matrix.Translation((0, (top_y + bot_y) / 2, (top_z + bot_z) / 2)) @ Matrix.Rotation(-ang, 4, "X"))
    b.box(teak, (-0.025, -0.022, -ln / 2), (0.025, 0.022, ln / 2), tile=0.5, skip=("+z", "-z"), grain=2)
    b.pop()
    # seat mattress
    b.chamfer_box(sand, (-W / 2 + 0.045, y_foot + 0.03, fz), (W / 2 - 0.045, hinge - 0.005, fz + 0.09), r=0.022)
    if p["towel"] and towel is not None:
        b.chamfer_box(towel, (-0.22, y_foot + 0.42, fz + 0.09), (0.22, y_foot + 0.72, fz + 0.125), r=0.008)


def build(**overrides):
    p = {**P, **overrides}
    b = pc.Builder(p["name"])
    lounger(b, p)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    pc.report(root, parts)
