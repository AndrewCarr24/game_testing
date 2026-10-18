"""Low limestone bench wall with a teak seat plank, 0.45 m high, 0.5 m deep. Long axis
along X (symmetric; no front). Origin: floor centre. Used as a parapet seat along the
edge of the raised pool deck. Real geometry, long faces cut every 1.5 m."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pool_common as pc  # noqa: E402

importlib.reload(pc)
common = pc.common

NAME = "PoolBenchWall"

P = dict(name=NAME, length=8.0, depth=0.50, height=0.45, plank=0.05)


def build(**overrides):
    p = {**P, **overrides}
    b = pc.Builder(p["name"])
    stone, teak = pc.stone(), pc.teak()
    L, D, H, t = p["length"], p["depth"], p["height"], p["plank"]
    b.box(stone, (-L / 2, -D / 2, 0.0), (L / 2, D / 2, H - t), tile=2.0, step=1.5, skip=("-z", "+z"))
    b.box(teak, (-L / 2 - 0.01, -D / 2 - 0.015, H - t), (L / 2 + 0.01, D / 2 + 0.015, H), tile=0.5, step=1.5,
          skip=("-z",), grain=0)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    pc.report(root, parts)
