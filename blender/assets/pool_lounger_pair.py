"""A pair of teak pool loungers with a stone drum side table between them. The loungers'
foot ends face -Y (rotate 180 to face the pool to the north). Origin: floor centre of the
pair. Built from pool_lounger.lounger(), real geometry."""
import importlib
import os
import sys

from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pool_common as pc  # noqa: E402
import pool_lounger as pl  # noqa: E402

importlib.reload(pc)
importlib.reload(pl)
common = pc.common

NAME = "PoolLoungerPair"

P = dict(
    name=NAME,
    gap=0.46,            # between the two frames
    table_r=0.19,
    table_h=0.42,
    table_y=0.12,
    second_towel=False,
)


def side_table(b, x, y, r, h):
    stone = pc.planter_stone()
    b.cyl(stone, (x, y), r, 0.0, h - 0.03, seg=12, caps=("+z",), tile=1.0)
    b.cyl(stone, (x, y), r + 0.02, h - 0.03, h, seg=12, caps=("+z",), tile=1.0)


def build(**overrides):
    p = {**P, **overrides}
    b = pc.Builder(p["name"])
    lp = dict(pl.P)
    dx = lp["width"] / 2 + p["gap"] / 2
    for k, sx in enumerate((-1, 1)):
        b.push(Matrix.Translation((sx * dx, 0, 0)))
        pl.lounger(b, {**lp, "towel": lp["towel"] and (k == 0 or p["second_towel"])})
        b.pop()
    side_table(b, 0.0, p["table_y"], p["table_r"], p["table_h"])
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    pc.report(root, parts)
