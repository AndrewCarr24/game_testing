"""Kitchen island vignette (the free east end of the marble island): three potted herbs on
a walnut tray, two cookbooks with a marble mortar and pestle on top, and a tall white jug
of cut olive branches as the focal height.

Origin: centre of the group on the worktop (z = 0), long axis X, front -Y (the island's
working side). About 1.3 x 0.45 m. NoCollide.
"""
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

NAME = "DecorBVignetteIsland"

P = dict(name=NAME, seed=4, pages="paper_white", covers=("linen_oat", "wool_charcoal"), pots=("ceramic_white",
         "ceramic_charcoal", "ceramic_white"), soil="coffee", jug="ceramic_white", twig="leaf")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    a = K.Acc()
    # herbs on a tray, west part of the group
    K.tray(a, "walnut", K.T(-0.42, 0.04, rz=3), 0.46, 0.18, h=0.025, rim=0.008, floor=0.007, r=0.02)
    for i, (dx, kind, hh) in enumerate(((-0.14, "basil", 0.13), (0.0, "grass", 0.16), (0.14, "basil", 0.10))):
        K.herb_pot(a, K.T(-0.42 + dx, 0.04, 0.007, rz=40 * i), rnd, pot=p["pots"][i], soil=p["soil"], r=0.05, h=0.085,
                   n=22 if kind == "basil" else 30, height=hh, leaf_len=0.04, kind=kind)
    # cookbooks + mortar
    z, L, W = K.book_stack(a, K.T(0.12, -0.04, rz=-6), rnd, 2, p["covers"], size=(0.27, 0.21), thick=(0.025, 0.035),
                           pages=p["pages"], bands=("paper_white",))
    K.mortar(a, K.T(0.10, -0.05, z))
    # tall jug with olive branches, at the back
    K.vessel(a, p["jug"], K.T(0.48, 0.08), "beaker", 0.27, 0.07, segs=16, wall=0.006)
    K.sprigs(a, K.T(0.48, 0.08, 0.265), rnd, twig=p["twig"], n=6, h=0.36, spread=0.22, leaves=11, leaf_len=0.06,
             leaf_w=0.016)
    parts = a.finish(n, col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
