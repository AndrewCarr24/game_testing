"""Office desk vignette (origin = the desk's centre on its top, 2.0 x 0.9 m; the sitter is on
+y, the banker's lamp at (-0.7, -0.2)): a closed laptop on the leather pad, a notebook with a
pen on it, a coffee mug, and on the far corner a short stack of books beside a small potted
plant. Everything stays on the top, clear of the drawer below the +y edge."""
import importlib
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_kit as K  # noqa: E402

importlib.reload(K)

NAME = "DecorC_VignetteDesk"
P = dict(name=NAME, seed=6)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rnd = random.Random(p["seed"])
    col, root, k = K.new_asset(n)
    pad = 0.003
    K.laptop(k, K.T(0.02, 0.16, pad, rz=184))
    K.notebook(k, K.T(0.44, 0.2, pad, rz=-6), rnd)
    K.pen(k, K.T(0.45, 0.2, pad + 0.0176, rz=70))
    K.mug(k, K.T(-0.36, 0.26, 0, rz=30))
    z, _ = K.book_stack(k, K.T(0.36, -0.22, 0, rz=8), rnd, n=3, w=(0.2, 0.25), d=(0.24, 0.29), t=(0.02, 0.034))
    zt = K.pot(k, K.T(0.83, -0.2, 0), "glaze", 0.065, 0.08, "cylinder", seed=2)
    K.leafy_plant(k, K.T(0.83, -0.2, 0), rnd, 18, 0.22, 0.13, z0=zt)
    return K.done(k, n, col, root)
