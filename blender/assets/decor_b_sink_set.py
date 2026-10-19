"""By the sink: a white ceramic soap pump and a wooden dish brush on a small marble dish.
Origin: centre of the dish (z = 0 on the worktop), front -Y. NoCollide."""
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

NAME = "DecorBSinkSet"

P = dict(name=NAME, seed=1, dish="marble", soap="ceramic_white", bristle="flour")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    a = K.Acc()
    K.slab(a, p["dish"], K.T(rz=8), 0.20, 0.11, 0.012, r=0.03)
    K.soap_pump(a, K.T(-0.05, 0.0, 0.012), key=p["soap"])
    K.brush(a, K.T(-0.01, -0.01, 0.012, rz=-25), bristle=p["bristle"], L=0.20)
    parts = a.finish(n, col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
