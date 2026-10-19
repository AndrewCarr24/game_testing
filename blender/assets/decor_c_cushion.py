"""Scatter cushion standing on its edge and leaning back by `lean` degrees (front -y), with
a karate-chop dent. Origin: under its lowest point."""
import importlib
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_kit as K  # noqa: E402

importlib.reload(K)

NAME = "DecorC_Cushion"
P = dict(name=NAME, seed=1, mat="oat", w=0.5, h=0.5, t=0.21, lean=10.0, turn=0.0)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, k = K.new_asset(n)
    K.pillow(k, K.T(rz=p["turn"], rx=-p["lean"]), p["mat"], p["w"], p["h"], p["t"], rnd=random.Random(p["seed"]))
    bm = k[p["mat"]].bm
    zmin = min(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co.z -= zmin
    return K.done(k, n, col, root)
