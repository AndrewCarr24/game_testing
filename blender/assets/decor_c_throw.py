"""A folded throw draped over a sofa or armchair arm: lying on the seat, up the inside of the
arm, over the top and hanging down the outside. The arm is centred on x = 0; the drape hangs
down the +x side; the origin is the bottom of that hanging edge, so place it at
z = hang (the hem's height above the floor). Defaults fit library_sofa / library_armchair
(arm top 0.62, seat 0.45)."""
import importlib
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_kit as K  # noqa: E402

importlib.reload(K)

NAME = "DecorC_Throw"
P = dict(name=NAME, seed=3, mat="oat", arm_w=0.2, arm_h=0.62, seat_h=0.45, hang=0.22, width=0.55)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, k = K.new_asset(n)
    K.throw_over_arm(k, K.T(), p["mat"], arm_w=p["arm_w"], arm_top=p["arm_h"] - p["hang"],
                     seat=p["seat_h"] - p["hang"], width=p["width"], rnd=random.Random(p["seed"]))
    bm = k[p["mat"]].bm
    zmin = min(v.co.z for v in bm.verts)          # the hem's lowest corner sits on z = 0
    for v in bm.verts:
        v.co.z -= zmin
    return K.done(k, n, col, root)
