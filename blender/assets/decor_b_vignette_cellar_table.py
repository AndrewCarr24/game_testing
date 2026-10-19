"""Coffee-table vignette for the cellar's leather nook: a stack of three vineyard atlases
(leather, white, smoked oak), a marble bowl of wine corks with a corkscrew beside it.
Origin: centre of the table top (z = 0), long axis X, front -Y. NoCollide."""
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

NAME = "DecorBVignetteCellarTable"

P = dict(name=NAME, seed=23, pages="label", covers=("leather", "paper_white", "oak_smoked"), bowl="marble",
         cork="wicker")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    a = K.Acc()
    zb, L, W = K.book_stack(a, K.T(-0.2, 0.0, rz=-8), rnd, 3, p["covers"], size=(0.34, 0.26), thick=(0.022, 0.035),
                            pages=p["pages"], bands=("label", "paper_white"))
    K.glasses(a, K.T(-0.2, -0.02, zb, rz=15))
    bx = 0.22
    K.vessel(a, p["bowl"], K.T(bx, 0.03), "bowl", 0.08, 0.12, segs=18, wall=0.008)
    for i in range(18):
        ang = i * 2.39996
        rr = 0.075 * math.sqrt((i + 0.5) / 18)
        zc = 0.025 + 0.012 * (i % 3) + (0.02 if i > 11 else 0.0)
        Mi = K.T(bx + rr * math.cos(ang), 0.03 + rr * math.sin(ang), zc, rz=rnd.uniform(0, 180), ry=90 + rnd.uniform(-25, 25))
        K.lathe(a, p["cork"], Mi @ K.T(z=-0.022), [(0.0, 0.0), (0.011, 0.0), (0.011, 0.044), (0.0, 0.044)], 6, sharp=50.0)
    # corkscrew (waiter's friend), lying flat
    K.box(a, "walnut", K.T(bx + 0.02, -0.15, 0.0, rz=-12), 0.115, 0.016, 0.011, bevel=0.003)
    K.tube(a, "steel", K.T(bx + 0.02, -0.15, 0.011, rz=-12), [(-0.03, 0.0, 0.0), (0.02, 0.012, 0.0)], 0.0018, sides=4)
    parts = a.finish(n, col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
