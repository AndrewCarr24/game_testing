"""Three bud vases for a long dining table (one stem each: an olive sprig, a leafy branch,
a single twig), in oat, matt white and charcoal glazes of different heights.

Origin: centre of the group on the table top (z = 0), spread along X. NoCollide.
"""
import importlib
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common  # noqa: E402
import decor_b_kit as K  # noqa: E402

importlib.reload(common)
importlib.reload(K)

NAME = "DecorBTableBuds"

P = dict(name=NAME, seed=21, glazes=("ceramic_oat", "paper_white", "ceramic_charcoal"))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    a = K.Acc()
    for (x, y, h, r, kind), g in zip(((-0.11, 0.02, 0.16, 0.042, "bud"), (0.0, -0.03, 0.22, 0.045, "flask"),
                                      (0.12, 0.03, 0.12, 0.05, "bud")), p["glazes"]):
        K.vessel(a, g, K.T(x, y), kind, h, r, segs=12, wall=0.004)
        K.sprigs(a, K.T(x, y, h - 0.005), rnd, n=1 if h < 0.2 else 2, h=h * 1.3, spread=0.08, leaves=7,
                 leaf_len=0.045, leaf_w=0.02)
    parts = a.finish(n, col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
