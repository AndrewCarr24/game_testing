"""Gym towels: a stack of three folded towels with two rolled ones beside it, in oat linen.
Origin: centre of the group's footprint."""
import importlib
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_kit as K  # noqa: E402

importlib.reload(K)

NAME = "DecorC_Towels"
P = dict(name=NAME, seed=2, mat="linen")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rnd = random.Random(p["seed"])
    col, root, k = K.new_asset(n)
    z = 0.0
    for i in range(3):
        t = 0.034 + rnd.uniform(-0.003, 0.004)
        K.folded_towel(k, K.T(-0.1 + rnd.uniform(-0.006, 0.006), rnd.uniform(-0.006, 0.006), z, rz=rnd.uniform(-3, 3)),
                       p["mat"], w=0.3, d=0.22, t=t)
        z += t - 0.002
    K.rolled_towel(k, K.T(0.13, -0.055, 0, rz=90), p["mat"], L=0.24, r=0.048)
    K.rolled_towel(k, K.T(0.13, 0.05, 0, rz=93), p["mat"], L=0.24, r=0.048)
    return K.done(k, n, col, root)
