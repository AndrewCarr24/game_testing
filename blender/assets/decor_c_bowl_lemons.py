"""A wide ceramic bowl heaped with lemons. Origin: centre of the foot."""
import importlib
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_kit as K  # noqa: E402

importlib.reload(K)

NAME = "DecorC_BowlLemons"
P = dict(name=NAME, seed=2, mat="charcoal", radius=0.15, lemons=6)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, k = K.new_asset(n)
    K.lemon_bowl(k, K.T(), random.Random(p["seed"]), p["mat"], p["radius"], p["lemons"])
    return K.done(k, n, col, root)
