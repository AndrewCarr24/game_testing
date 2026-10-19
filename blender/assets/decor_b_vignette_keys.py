"""Catch-all by the garage door: a walnut tray with a set of car keys and a house key, a pair
of sunglasses, and a little stack of post and a magazine beside it.
Origin: centre of the group (worktop z = 0), front -Y. NoCollide."""
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

NAME = "DecorBVignetteKeys"

P = dict(name=NAME, seed=41, tray="walnut", paper="paper_white", cover="linen_sage", fob="leather")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    a = K.Acc()
    K.tray(a, p["tray"], K.T(0.02, 0.06, rz=6), 0.26, 0.16, h=0.022, rim=0.008, floor=0.007, r=0.03)
    K.keys(a, K.T(-0.03, 0.06, 0.007, rz=20), rnd, metal="steel", fob=p["fob"])
    K.keys(a, K.T(0.07, 0.04, 0.007, rz=-50), rnd, metal="bronze", fob="black_metal")
    K.glasses(a, K.T(0.0, -0.12, rz=170), key="black_metal")
    # post: three envelopes and a magazine
    K.magazine(a, K.T(-0.30, -0.02, 0.0, rz=-9), p["cover"], p["paper"], size=(0.27, 0.21), t=0.006)
    for i in range(3):
        K.box(a, p["paper"], K.T(-0.30 + 0.01 * i, -0.01 - 0.008 * i, 0.006 + 0.0012 * i, rz=-9 + 6 * i), 0.22, 0.11,
              0.0012)
    parts = a.finish(n, col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
