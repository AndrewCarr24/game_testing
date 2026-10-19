"""A big woven floor basket with two rolled throws standing in it (oat wool and clay linen),
leather handles. The basket may collide. Origin: floor centre."""
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

NAME = "DecorBBasketBlankets"

P = dict(name=NAME, seed=2, basket="wicker", throws=("wool_oat", "linen_clay"))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    a = K.Acc()
    b = K.Acc()
    K.basket(b, K.T(), p["basket"], r=0.21, h=0.36, rim="leather")
    K.rolled_throw(a, K.T(-0.05, 0.03, 0.30, ry=-72, rz=20), p["throws"][0], L=0.56, r=0.075)
    K.rolled_throw(a, K.T(0.07, -0.04, 0.26, ry=-80, rz=-30), p["throws"][1], L=0.5, r=0.065)
    parts = b.finish(n, col, root, collide=(p["basket"],))
    parts += a.finish(n + "Throws", col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
