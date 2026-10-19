"""A walnut bread board with a floured sourdough boule, a bread knife and a folded linen
napkin, for a kitchen counter. Origin: centre of the board's footprint (z = 0), handle
to +X, front -Y. NoCollide."""
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

NAME = "DecorBBreadBoard"

P = dict(name=NAME, seed=2, board="walnut", crust="crust", flour="flour", linen="linen_oat", baguette=False)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    a = K.Acc()
    K.board(a, K.T(rz=-4), p["board"], L=0.44, W=0.30, t=0.025)
    K.boule(a, K.T(-0.05, 0.02, 0.025), key=p["crust"], flour=p["flour"])
    K.knife(a, K.T(0.05, -0.11, 0.025, rz=8), handle="walnut", L=0.30)
    if p["baguette"]:
        K.baguette(a, K.T(0.08, 0.10, 0.025, rz=-12), key=p["crust"], L=0.48)
    K.towel_stack(a, K.T(0.34, 0.14, 0.0, rz=10), p["linen"], n=1, size=(0.20, 0.14), t=0.02)
    parts = a.finish(n, col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
