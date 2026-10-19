"""Gallery bench: solid walnut, a 60 mm top on two slab ends set well in, a low stretcher.
Collides. Origin: floor centre, long side along x."""
import importlib
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_kit as K  # noqa: E402

importlib.reload(K)

NAME = "DecorC_GalleryBench"
P = dict(name=NAME, width=1.6, depth=0.4, height=0.45)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, k = K.new_asset(n)
    K.gallery_bench(k, K.T(), p["width"], p["depth"], p["height"])
    return K.done(k, n, col, root, collide=("walnut",))
