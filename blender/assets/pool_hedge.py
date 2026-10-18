"""Clipped yew hedge: a plain rectangular block of foliage with a crisp flat top, long
axis along X. Origin: floor centre. Long faces are cut every 1.5 m (baked lighting) and
the foliage material uses world-scale box UVs (1.5 m). Real geometry, no hidden faces."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pool_common as pc  # noqa: E402

importlib.reload(pc)
common = pc.common

NAME = "PoolHedge"

P = dict(name=NAME, length=11.0, thick=0.65, height=0.85)


def build(**overrides):
    p = {**P, **overrides}
    b = pc.Builder(p["name"])
    leaf = pc.outdoor.foliage()
    L, T, H = p["length"], p["thick"], p["height"]
    b.box(leaf, (-L / 2, -T / 2, 0.0), (L / 2, T / 2, H), tile=1.5, step=1.5, skip=("-z",))
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    pc.report(root, parts)
