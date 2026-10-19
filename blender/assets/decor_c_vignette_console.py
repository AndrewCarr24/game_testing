"""Console / credenza vignette (origin = centre of the top, 1.1 m clear between two lamps):
two large books with a bronze dish on top at the left, a trio of ceramics at the right."""
import importlib
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_kit as K  # noqa: E402

importlib.reload(K)

NAME = "DecorC_VignetteConsole"
P = dict(name=NAME, seed=10, family="mixed", gap=0.56)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rnd = random.Random(p["seed"])
    col, root, k = K.new_asset(n)
    g = p["gap"] / 2
    z, _ = K.book_stack(k, K.T(-g, 0.0, 0, rz=-5), rnd, n=2, w=(0.28, 0.33), d=(0.3, 0.35), t=(0.03, 0.045))
    K.candle_dish(k, K.T(-g + 0.02, -0.01, z))
    K.ceramic_trio(k, K.T(g, 0.04, 0), rnd, p["family"], scale=1.15)
    return K.done(k, n, col, root)
