"""Two pale wooden wine crates stacked in a corner: a closed one below, an open one on top
with six bottles standing in it (green and black glass, cream labels, foil caps). The lower
crate may collide (it's knee-high); the rest is NoCollide. Origin: floor centre."""
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

NAME = "DecorBWineCrates"

P = dict(name=NAME, seed=31, wood="oak_light", label="label")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    a = K.Acc()
    L, W, H = 0.52, 0.36, 0.22
    low = K.Acc()
    K.crate(low, K.T(), p["wood"], L=L, W=W, H=H, lid=True, label=None)
    K.crate(a, K.T(0.015, -0.01, H + 0.012, rz=4), p["wood"], L=L, W=W, H=H, label=p["label"])
    K.box(a, p["label"], K.T(y=-W / 2 - 0.0006, z=H * 0.3), L * 0.4, 0.001, H * 0.4)
    for i in range(6):
        x = -0.16 + (i % 3) * 0.16 + 0.015
        y = -0.08 + (i // 3) * 0.16 - 0.01
        key = "bottle_green" if (i * 7) % 3 else "bottle_black"
        K.bottle(a, K.T(x, y, H + 0.024, rz=rnd.uniform(0, 360)), key=key, h=0.30, r=0.037, label=p["label"],
                 cap="bronze" if i % 2 else "wine")
    parts = low.finish(n + "Low", col, root, collide=(p["wood"],))
    parts += a.finish(n, col, root)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
