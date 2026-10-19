"""Coffee-table vignette: a stack of art books with a small bronze object on top, a candle
in a low holder and a little potted plant, composed on one half of a low table (about
0.5 x 0.45 m) so it can share a table with another object.

Origin: centre of the group on the table top (z = 0), front -Y. Everything is NoCollide.
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

NAME = "DecorBVignetteCoffee"

P = dict(name=NAME, seed=5, pages="candle", covers=("paper_white", "cloth_rust", "wool_greige"),
         sculpture="ring", pot="ceramic_charcoal", soil="soil", holder="ceramic_oat", plant=True, candle=True,
         bands=("paper_white",), wax="candle")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    a = K.Acc()
    z, L, W = K.book_stack(a, K.T(-0.06, 0.02, rz=8), rnd, 3, p["covers"], size=(0.33, 0.26), thick=(0.02, 0.03),
                           pages=p["pages"], bands=p["bands"])
    K.sculpture(a, K.T(-0.04, 0.02, z, rz=-20), p["sculpture"], s=0.85)
    if p["plant"]:
        K.herb_pot(a, K.T(0.19, 0.12), rnd, pot=p["pot"], soil=p["soil"], r=0.055, h=0.09, n=30, height=0.13,
                   leaf_len=0.045)
    if p["candle"]:
        K.candle(a, K.T(0.17, -0.12), h=0.07, r=0.03, holder=p["holder"], wax=p["wax"], style="cup")
    parts = a.finish(n, col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
