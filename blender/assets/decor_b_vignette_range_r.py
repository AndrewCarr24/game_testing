"""Counter vignette on the other side of the range: a marble tray with a smoked-glass oil
bottle, a charcoal cruet, a walnut pepper mill and a salt cellar, and a pot of rosemary.

Origin: centre of the counter section (worktop z = 0), front -Y, back at y = +0.30.
NoCollide.
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

NAME = "DecorBVignetteRangeR"

P = dict(name=NAME, seed=9, tray="marble", glass="glass_smoke", cruet="ceramic_charcoal", pot="ceramic_white",
         soil="coffee")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    a = K.Acc()
    K.tray(a, p["tray"], K.T(-0.08, 0.12, rz=-2), 0.40, 0.20, h=0.02, rim=0.012, floor=0.01, r=0.02)
    K.bottle(a, K.T(-0.20, 0.15, 0.01), key=p["glass"], h=0.29, r=0.032, label="paper_white", cap="walnut", kind="oil")
    K.vessel(a, p["cruet"], K.T(-0.10, 0.10, 0.01), "bottle", 0.17, 0.038, segs=12, wall=0.004)
    K.mill(a, K.T(0.0, 0.16, 0.01))
    K.salt_cellar(a, K.T(0.06, 0.07, 0.01), r=0.038)
    K.herb_pot(a, K.T(0.24, 0.10), rnd, pot=p["pot"], soil=p["soil"], r=0.06, h=0.10, n=30, height=0.15, kind="grass")
    parts = a.finish(n, col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
