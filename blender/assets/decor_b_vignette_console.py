"""Console vignette for the dining room's west sideboard, either side of the smoked-glass
vase between the two lamps: on one side two art books with a stack of three pebbles, on the
other a low charcoal footed dish and a bronze candlestick.

Origin: centre of the sideboard top (z = 0), long axis X, front -Y. The middle (|x| < 0.15)
and the lamp positions (x = +-0.85) stay clear. Everything is NoCollide.
"""
import importlib
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

NAME = "DecorBVignetteConsole"

P = dict(name=NAME, seed=11, pages="candle", covers=("paper_white", "cloth_rust", "linen_oat"),
         dish="ceramic_charcoal", pebbles="ceramic_oat", holder="bronze")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    a = K.Acc()
    z, L, W = K.book_stack(a, K.T(0.42, 0.0, rz=-5), rnd, 2, p["covers"], size=(0.31, 0.24), thick=(0.024, 0.032),
                           pages=p["pages"], bands=("paper_white",))
    K.sculpture(a, K.T(0.40, -0.02, z), "pebbles", key=p["pebbles"])
    K.vessel(a, p["dish"], K.T(-0.40, 0.02), "dish", 0.075, 0.13, segs=18, wall=0.008)
    K.candle(a, K.T(-0.56, -0.10), h=0.17, r=0.011, holder=p["holder"], style="stick")
    parts = a.finish(n, col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
