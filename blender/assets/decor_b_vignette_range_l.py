"""Counter vignette beside the range: two walnut boards leaning against the backsplash, a
white crock of wooden spoons and spatulas in front of them, a marble salt cellar.

Origin: centre of the counter section (z = 0 on the worktop), front -Y; the back of the
group is at y = +0.30 (the splashback). About 0.8 x 0.6 m. NoCollide.
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

NAME = "DecorBVignetteRangeL"

P = dict(name=NAME, seed=6, back=0.30, crock="ceramic_white", wood="oak_smoked", boards="walnut")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    a = K.Acc()
    b = p["back"]
    # leaning boards: bottom edge on the worktop, top edge against the splashback
    for dx, L, W, ang in ((-0.12, 0.46, 0.30, 12), (0.10, 0.36, 0.24, 15)):
        th = math.radians(ang)
        M = K.T(dx, b - W * math.sin(th), 0.0, rx=90 - ang) @ K.T(0.0, W / 2, 0.0)
        K.board(a, M, p["boards"], L=L, W=W, t=0.022, handle=False)
    K.crock(a, K.T(-0.02, 0.10), rnd, key=p["crock"], wood=p["wood"], h=0.16, r=0.058)
    K.salt_cellar(a, K.T(0.24, -0.02))
    parts = a.finish(n, col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
