"""Freestanding outdoor shower: a teak backing panel on a limestone plinth, a bronze riser
pipe with a rain head, a hand shower and a foot tap. The panel faces -Y. Origin: floor
centre of the plinth. Real geometry (~100 triangles)."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pool_common as pc  # noqa: E402

importlib.reload(pc)
common = pc.common

NAME = "PoolShower"

P = dict(name=NAME, width=0.9, height=2.15)


def build(**overrides):
    p = {**P, **overrides}
    b = pc.Builder(p["name"])
    teak, bronze = pc.teak(), pc.outdoor.bronze()
    stone = pc.planter_stone()
    W, H = p["width"], p["height"]
    h = W / 2
    # plinth (a shallow drain slab in front) and panel
    b.box(stone, (-h - 0.1, -0.45, 0.0), (h + 0.1, 0.18, 0.05), skip=("-z",), tile=1.0)
    b.box(teak, (-h, 0.0, 0.05), (h, 0.06, H), tile=0.5, skip=("-z", "+y"), grain=2)
    # riser pipe and rain head
    b.box(bronze, (-0.02, -0.06, 0.05), (0.02, -0.02, H - 0.1), skip=("-z", "+y"))
    b.box(bronze, (-0.02, -0.28, H - 0.14), (0.02, -0.02, H - 0.10), skip=("-z", "+y"))
    b.cyl(bronze, (0.0, -0.26), 0.13, H - 0.17, H - 0.14, seg=12, caps=("+z", "-z"))
    # hand shower on a bracket and a foot tap
    b.box(bronze, (0.22, -0.04, 1.15), (0.26, -0.01, 1.30), skip=("+y",))
    b.box(bronze, (-0.02, -0.12, 0.28), (0.02, -0.02, 0.32), skip=("+y",))
    b.box(bronze, (-0.02, -0.12, 0.05), (0.02, -0.08, 0.32), skip=("-z", "+y"))
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    pc.report(root, parts)
