"""Tasting-table vignette: a walnut cheese board with two wedges and a round, a bunch of red
grapes and a cheese knife, and a short stack of wine books with a bronze candlestick.
Origin: centre of the group (table top z = 0), long axis X, front -Y. NoCollide."""
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

NAME = "DecorBVignetteCheese"

P = dict(name=NAME, seed=17, board="walnut", cheese="label", grapes="wine", pages="label",
         covers=("leather", "paper_white", "oak_smoked"), holder="bronze", wax="label")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    a = K.Acc()
    bx = -0.12
    K.board(a, K.T(bx, 0.0, rz=-3), p["board"], L=0.40, W=0.26, t=0.022)
    z = 0.022
    for (x, y, rz, s) in ((bx - 0.10, 0.04, 20, 1.0), (bx - 0.02, -0.06, -40, 0.8)):
        # wedge: a triangular prism, rind on the round back
        import bmesh
        bm = bmesh.new()
        r_, h_ = 0.09 * s, 0.045 * s
        pts = [(0.0, 0.0)] + [(r_ * math.cos(math.radians(a_)), r_ * math.sin(math.radians(a_))) for a_ in (-18, 0, 18)]
        lo = [bm.verts.new((px, py, 0)) for px, py in pts]
        hi = [bm.verts.new((px, py, h_)) for px, py in pts]
        bm.faces.new(list(reversed(lo)))
        bm.faces.new(hi)
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
        a.emit(p["cheese"], bm, K.T(x, y, z, rz=rz), smooth=False)
    K.lathe(a, "paper_white", K.T(bx + 0.11, 0.05, z), [(0.0, 0.0), (0.05, 0.0), (0.054, 0.012), (0.054, 0.026),
                                                       (0.05, 0.034), (0.0, 0.034)], 16)
    K.grapes(a, K.T(bx + 0.08, -0.07, z, rz=-20), rnd, p["grapes"], n=16, r=0.0095, spread=0.06, stem="oak_smoked")
    K.knife(a, K.T(bx - 0.02, -0.15, 0.0, rz=6), handle="walnut", L=0.20)
    zb, L, W = K.book_stack(a, K.T(0.38, 0.02, rz=7), rnd, 2, p["covers"], size=(0.28, 0.22), thick=(0.025, 0.035),
                            pages=p["pages"], bands=("label",))
    K.candle(a, K.T(0.40, 0.03, zb), h=0.16, r=0.011, holder=p["holder"], wax=p["wax"], style="stick")
    parts = a.finish(n, col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
