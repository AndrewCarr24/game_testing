"""Three ceramic vessels of varied height in a loose triangle: glossy cream glaze and matte
charcoal (shared M_Ceramic_Glaze / M_Ceramic_Charcoal). family: mixed | glaze | charcoal |
pale. Origin: centre of the group's footprint, on the surface."""
import importlib
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_kit as K  # noqa: E402

importlib.reload(K)

NAME = "DecorC_Ceramics"
P = dict(name=NAME, seed=1, family="mixed")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, k = K.new_asset(n)
    K.ceramic_trio(k, K.T(), random.Random(p["seed"]), p["family"])
    return K.done(k, n, col, root)
