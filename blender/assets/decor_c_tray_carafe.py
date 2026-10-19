"""A tray with a smoked-glass carafe and two tumblers (one turned down on its rim would be
fussier; both upright). Origin: centre of the tray's underside."""
import importlib
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_kit as K  # noqa: E402

importlib.reload(K)

NAME = "DecorC_TrayCarafe"
P = dict(name=NAME, tray="walnut", size=(0.40, 0.25))


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, k = K.new_asset(n)
    w, d = p["size"]
    t = K.tray(k, K.T(), w, d, p["tray"])
    K.carafe(k, K.T(-w * 0.22, 0.01, t))
    K.tumbler(k, K.T(w * 0.12, 0.045, t))
    K.tumbler(k, K.T(w * 0.27, -0.04, t))
    return K.done(k, n, col, root)
