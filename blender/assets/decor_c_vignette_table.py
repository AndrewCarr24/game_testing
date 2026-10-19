"""Library reading-table vignette (origin = the table's centre on its top, 3.2 x 1.2 m with
banker's lamps at (-0.9, +0.12) and (+0.9, -0.12)): a stack of three folios with a bronze
split sphere in the middle, an open book with gold-rimmed reading glasses at the south
centre place, a cognac leather notebook and pen at the north, a coffee mug left by a reader, and two books
at the east end."""
import importlib
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_kit as K  # noqa: E402

importlib.reload(K)

NAME = "DecorC_VignetteTable"
P = dict(name=NAME, seed=4)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rnd = random.Random(p["seed"])
    col, root, k = K.new_asset(n)
    z, _ = K.book_stack(k, K.T(-0.22, 0.14, 0, rz=7), rnd, n=3, w=(0.29, 0.36), d=(0.3, 0.37), t=(0.03, 0.05))
    K.sculpture(k, K.T(-0.2, 0.13, z), "sphere", mat="bronze")
    K.open_book(k, K.T(0.04, -0.3, 0, rz=-4), rnd, w=0.19, d=0.26)
    K.reading_glasses(k, K.T(0.33, -0.36, 0, rz=-75), "bronze", folded=False)
    K.notebook(k, K.T(0.48, 0.3, 0, rz=-9), rnd, cover="cognac")
    K.pen(k, K.T(0.62, 0.27, 0, rz=80))
    K.mug(k, K.T(-0.52, -0.33, 0, rz=200))
    K.book_stack(k, K.T(1.28, 0.22, 0, rz=-12), rnd, n=2, w=(0.2, 0.24), d=(0.24, 0.28), t=(0.025, 0.04))
    return K.done(k, n, col, root)
