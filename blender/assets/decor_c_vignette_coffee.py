"""Coffee-table vignette for the office's marble table (1.05 x 0.58 m, origin its centre on
the top): two big art books with folded reading glasses, a charcoal bowl of lemons."""
import importlib
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_kit as K  # noqa: E402

importlib.reload(K)

NAME = "DecorC_VignetteCoffee"
P = dict(name=NAME, seed=8, frames="black")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rnd = random.Random(p["seed"])
    col, root, k = K.new_asset(n)
    z, _ = K.book_stack(k, K.T(-0.2, 0.02, 0, rz=-7), rnd, n=2, w=(0.3, 0.34), d=(0.33, 0.37), t=(0.03, 0.045))
    K.reading_glasses(k, K.T(-0.18, -0.04, z, rz=20), p["frames"])
    K.lemon_bowl(k, K.T(0.26, 0.02, 0), rnd, "charcoal", r=0.13, n=5)
    return K.done(k, n, col, root)
