"""Dish rack for a sink drainer: a walnut slatted base with steel pegs, four white plates
standing up and two bowls leaning, a linen tea towel folded beside it.
Origin: centre of the rack (z = 0), plates along X, front -Y. NoCollide."""
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

NAME = "DecorBDishRack"

P = dict(name=NAME, seed=3, wood="walnut", pegs="steel", dishes="ceramic_white", towel="linen_stone")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    a = K.Acc()
    L, W = 0.36, 0.26
    for k in range(4):
        K.box(a, p["wood"], K.T(y=-W / 2 + 0.03 + k * (W - 0.06) / 3), L, 0.025, 0.012, bevel=0.002)
    K.box(a, p["wood"], K.T(x=-L / 2 + 0.01, z=0.012), 0.02, W, 0.012)
    K.box(a, p["wood"], K.T(x=L / 2 - 0.01, z=0.012), 0.02, W, 0.012)
    for i in range(5):
        x = -0.12 + i * 0.06
        for y in (-0.06, 0.06):
            K.tube(a, p["pegs"], K.T(), [(x, y, 0.012), (x, y, 0.09)], 0.0025, sides=4)
    for i in range(4):
        x = -0.096 + i * 0.048
        K.plate(a, K.T(x + 0.024, 0.0, 0.135, ry=90 - 8, rz=0) @ K.T(z=-0.006), p["dishes"], r=0.125, segs=16)
    for i in range(2):
        K.vessel(a, p["dishes"], K.T(0.14 + 0.02 * i, 0.03, 0.075, ry=-70), "bowl", 0.065, 0.075, segs=14, wall=0.005)
    parts = a.finish(n, col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
