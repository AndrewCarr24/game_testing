"""Workshop counter vignette for the showroom garage: a graphite caddy of detailing kit (two
spray bottles, a polish tin, folded cloths), a stack of three motoring books with a bronze
ring on top, a coffee mug, and a small potted plant.
Origin: centre of the counter (z = 0 on the worktop), long axis X, front -Y. NoCollide."""
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

NAME = "DecorBVignetteGarage"

P = dict(name=NAME, seed=51, pages="paper", covers=("accent", "white_lacquer", "graphite", "garage_leather"),
         caddy="graphite", bottles="white_lacquer", heads="accent", cloth="garage_leather", mug="white_lacquer",
         pot="graphite", soil="graphite_dark")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    a = K.Acc()
    # caddy with kit, left
    cx = -0.85
    K.tray(a, p["caddy"], K.T(cx, 0.05), 0.40, 0.22, h=0.08, rim=0.01, floor=0.01, r=0.015)
    K.box(a, p["caddy"], K.T(cx, 0.05, 0.08), 0.012, 0.18, 0.12)
    K.box(a, p["caddy"], K.T(cx, 0.05, 0.19), 0.04, 0.10, 0.02, bevel=0.004)
    K.spray_bottle(a, K.T(cx - 0.12, 0.08, 0.01, rz=170), body=p["bottles"], head=p["heads"], h=0.22)
    K.spray_bottle(a, K.T(cx - 0.05, 0.02, 0.01, rz=200), body=p["bottles"], head="graphite_dark", h=0.20)
    K.lathe(a, "aluminium", K.T(cx + 0.10, 0.09, 0.01), [(0.0, 0.0), (0.045, 0.0), (0.045, 0.05), (0.0, 0.05)], 16)
    K.towel_stack(a, K.T(cx + 0.11, -0.01, 0.01, rz=4), p["cloth"], n=2, size=(0.15, 0.10), t=0.018)
    # books + ring
    zb, L, W = K.book_stack(a, K.T(-0.15, 0.0, rz=-5), rnd, 3, p["covers"], size=(0.32, 0.25), thick=(0.02, 0.032),
                            pages=p["pages"], bands=("white_lacquer", "accent"))
    K.sculpture(a, K.T(-0.14, 0.0, zb, rz=10), "ring", key="bronze", base="graphite_dark", s=0.8)
    K.mug(a, K.T(0.22, -0.10, rz=-40), key=p["mug"], coffee="graphite_dark")
    # small plant at the back right
    K.herb_pot(a, K.T(0.62, 0.10), rnd, pot=p["pot"], soil=p["soil"], r=0.075, h=0.13, n=24, height=0.30, kind="grass")
    parts = a.finish(n, col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
