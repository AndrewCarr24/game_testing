"""Two sage foam yoga blocks, one on its side against the other, by a stretching mat.
Origin: centre of the pair's footprint."""
import importlib
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_kit as K  # noqa: E402

importlib.reload(K)

NAME = "DecorC_YogaBlocks"
P = dict(name=NAME, mat="sage")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, k = K.new_asset(n)
    a = k[p["mat"]]
    a.box((0.23, 0.15, 0.076), K.T(-0.06, 0.0, 0.038, rz=4), skip=("-z",), bevel=0.012, seg=2)
    a.box((0.23, 0.076, 0.15), K.T(0.08, 0.02, 0.075, rz=-8), skip=("-z",), bevel=0.012, seg=2)
    return K.done(k, n, col, root)
