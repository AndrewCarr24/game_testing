"""Scullery counter vignette (the butcher-block run under the copper pans): a big walnut
board with a sourdough boule and a baguette, a linen cloth, a stoneware crock of wooden
spoons, a stack of white bowls, and a wicker basket of lemons.

Origin: centre of the counter (z = 0 on the top), long axis X, front -Y, back at y = +0.24.
About 2.4 m long. NoCollide.
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

NAME = "DecorBVignetteBread"

P = dict(name=NAME, seed=14, board="walnut", crust="crust", flour="flour", linen="linen_stone", crock="ceramic_charcoal",
         bowls="ceramic_white", basket="wicker", fruit="lemon")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    a = K.Acc()
    # bread board, left of centre
    K.board(a, K.T(-0.55, 0.02, rz=3), p["board"], L=0.56, W=0.34, t=0.03)
    K.boule(a, K.T(-0.66, 0.04, 0.03), key=p["crust"], flour=p["flour"], r=0.10, h=0.09)
    K.baguette(a, K.T(-0.45, 0.06, 0.03, rz=-14), key=p["crust"], L=0.50, r=0.032)
    K.knife(a, K.T(-0.55, -0.12, 0.03, rz=4), handle="walnut", L=0.30)
    K.towel_stack(a, K.T(-0.98, -0.02, rz=-6), p["linen"], n=2, size=(0.26, 0.18), t=0.022)
    # crock of spoons and the bowls between the open shelves (clear of the shelf above)
    K.crock(a, K.T(0.50, 0.10), rnd, key=p["crock"], wood="oak_smoked", h=0.18, r=0.065, n=5)
    for i in range(3):
        K.vessel(a, p["bowls"], K.T(0.70, -0.04, i * 0.032, rz=17 * i), "bowl", 0.07, 0.085 - 0.012 * i, segs=14,
                 wall=0.005)
    # basket of lemons, right
    K.vessel(a, p["basket"], K.T(0.98, 0.0), "dish", 0.09, 0.15, segs=18, wall=0.008)
    pts = [(0.98 + 0.065 * math.cos(k * 1.26), 0.065 * math.sin(k * 1.26), 0.012) for k in range(5)]
    pts += [(0.98 + 0.02, 0.01, 0.05), (0.95, -0.03, 0.05)]
    K.lemons(a, K.T(), rnd, p["fruit"], pts, r=0.031)
    parts = a.finish(n, col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
