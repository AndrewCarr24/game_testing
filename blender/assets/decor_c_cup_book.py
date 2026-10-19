"""Side-table life: an espresso cup on its saucer, two books with folded reading glasses on
top. Fits a 0.26 m-radius side table. Origin: the table's centre."""
import importlib
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_kit as K  # noqa: E402

importlib.reload(K)

NAME = "DecorC_CupBook"
P = dict(name=NAME, seed=5, frames="bronze")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rnd = random.Random(p["seed"])
    col, root, k = K.new_asset(n)
    z, _ = K.book_stack(k, K.T(-0.03, 0.03, 0, rz=-18), rnd, n=2, w=(0.17, 0.2), d=(0.21, 0.24), t=(0.02, 0.032))
    K.reading_glasses(k, K.T(-0.04, 0.02, z, rz=-30), p["frames"])
    K.cup_saucer(k, K.T(0.12, -0.1, 0, rz=150))
    return K.done(k, n, col, root)
