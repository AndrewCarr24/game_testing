"""A woven floor basket of rolled towels for the gym. Collides (it's big enough to bump).
Origin: centre of the foot."""
import importlib
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_kit as K  # noqa: E402

importlib.reload(K)

NAME = "DecorC_TowelBasket"
P = dict(name=NAME, seed=4, r=0.2, h=0.3)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rnd = random.Random(p["seed"])
    col, root, k = K.new_asset(n)
    r, h = p["r"], p["h"]
    K.basket(k, K.T(), "wicker", r=r, h=h)
    rr = 0.05
    # rolls standing upright, packed in, tops above the rim at varied heights
    spots = [(0.0, 0.0), (0.1, 0.0), (-0.1, 0.0), (0.05, 0.087), (-0.05, 0.087), (0.05, -0.087), (-0.05, -0.087)]
    for x, y in spots:
        L = h + rnd.uniform(-0.02, 0.06)
        K.rolled_towel(k, K.T(x, y, 0.026, rz=rnd.uniform(0, 360)), "linen", L=L, r=rr, upright=True)
    return K.done(k, n, col, root, collide=("wicker",))
