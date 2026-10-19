"""Breakfast-table vignette: a white bowl of green apples and lemons at one end, and at one
place a cup of coffee on its saucer, an open book and a pair of reading glasses. The middle
of the table (|x| < 0.2) stays clear for the glass vase that lives there.

Origin: centre of the table top (z = 0), long axis X, front -Y. NoCollide.
"""
import importlib
import math
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

NAME = "DecorBVignetteBreakfast"

P = dict(name=NAME, seed=12, bowl="ceramic_white", fruit=("lime", "lemon"), cup="ceramic_white",
         pages="paper_white", cover="linen_oat")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    a = K.Acc()
    # fruit bowl, east end
    fx = 0.66
    K.vessel(a, p["bowl"], K.T(fx, 0.06), "bowl", 0.10, 0.15, segs=18, wall=0.006)
    pts = [(fx + 0.05 * math.cos(k * 2.1), 0.06 + 0.05 * math.sin(k * 2.1), 0.012 + (0.01 if k < 3 else 0.055))
           for k in range(5)]
    K.apples(a, K.T(), rnd, p["fruit"][0], pts[:4], r=0.034, stem="oak_smoked")
    K.lemons(a, K.T(), rnd, p["fruit"][1], [(fx + 0.01, 0.06, 0.06), (fx - 0.06, 0.1, 0.045)], r=0.03)
    # a place: cup, open book, glasses (west, at the south chair)
    K.cup_saucer(a, K.T(-0.52, -0.32), p["cup"])
    K.open_book(a, K.T(-0.78, -0.27, rz=8), p["cover"], p["pages"], L=0.22, W=0.15, t=0.02)
    K.glasses(a, K.T(-0.58, -0.12, rz=-30))
    parts = a.finish(n, col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
