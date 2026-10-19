"""Sideboard vignette (dining room, the bare south sideboard): a family of three ceramics
(a tall charcoal ovoid with cut olive branches, a matt white bottle vase, a small oat bud
vase), a stack of three art books with a bronze sphere on a marble block, and a walnut tray
with a smoked-glass carafe and two tumblers.

Sits on a 2.5 x 0.52 m top: origin at the centre of the surface (z = 0), long axis X,
front -Y (the back towards the wall). Everything is NoCollide.
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

NAME = "DecorBVignetteSideboard"

P = dict(
    name=NAME,
    seed=3,
    pages="candle",                                          # cream page blocks (already in the room)
    covers=("paper_white", "cloth_rust", "wool_greige", "linen_oat"),
    tall="ceramic_charcoal", mid="paper_white", small="ceramic_oat",
    tray="walnut", glass="glass_smoke",
    sculpture="sphere",
    bands=("paper_white", "wool_greige"),                    # printed title strips on some spines
    mirror=False,                                            # swap the ends
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    a = K.Acc()
    sx = -1 if p["mirror"] else 1

    # ceramics, left end: varied heights, the tall one at the back
    K.vessel(a, p["tall"], K.T(sx * -0.90, 0.05), "ovoid", 0.36, 0.105, segs=18, wall=0.007)
    K.sprigs(a, K.T(sx * -0.90, 0.05, 0.355), rnd, n=5, h=0.42, spread=0.22, leaves=10)
    K.vessel(a, p["mid"], K.T(sx * -0.70, -0.07), "bottle", 0.25, 0.068, segs=16, wall=0.005)
    K.vessel(a, p["small"], K.T(sx * -0.79, -0.15), "bud", 0.12, 0.05, segs=14, wall=0.004)

    # book stack + sculpture, centre-right of centre
    z, L, W = K.book_stack(a, K.T(sx * 0.05, 0.0, rz=sx * 3), rnd, 3, p["covers"], size=(0.34, 0.26),
                           thick=(0.022, 0.034), pages=p["pages"], bands=p["bands"])
    K.sculpture(a, K.T(sx * 0.06, -0.01, z, rz=12), p["sculpture"])

    # tray with carafe and tumblers, right end
    tx = sx * 0.78
    K.tray(a, p["tray"], K.T(tx, 0.0, rz=-sx * 4), 0.44, 0.27, h=0.03, rim=0.01, floor=0.008)
    K.carafe(a, K.T(tx + 0.09, 0.04, 0.008), p["glass"], h=0.25, r=0.058)
    K.tumbler(a, K.T(tx - 0.10, -0.03, 0.008), p["glass"])
    K.tumbler(a, K.T(tx - 0.02, -0.07, 0.008), p["glass"])

    parts = a.finish(n, col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
