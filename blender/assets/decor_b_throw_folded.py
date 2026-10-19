"""A folded wool throw for the end of a bench or window seat, its loose end dropping over
the front edge. Origin: centre of the throw's footprint on the seat (z = 0), front -Y.
NoCollide."""
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

NAME = "DecorBThrowFolded"

P = dict(name=NAME, seed=1, cloth="wool_charcoal", size=(0.46, 0.34), t=0.07, drape=0.22)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    a = K.Acc()
    K.throw_folded(a, K.T(rz=0), p["cloth"], size=p["size"], t=p["t"], drape=p["drape"])
    parts = a.finish(n, col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
