"""A small potted plant for a desk or shelf: arching stems with broad leaves (pilea habit) in
a glazed cylinder. Origin: centre of the pot's foot."""
import importlib
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_kit as K  # noqa: E402

importlib.reload(K)

NAME = "DecorC_PlantDesk"
P = dict(name=NAME, seed=3, pot="glaze", pot_r=0.07, pot_h=0.085, leaves=22, height=0.25, spread=0.15)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, k = K.new_asset(n)
    z = K.pot(k, K.T(), p["pot"], p["pot_r"], p["pot_h"], "cylinder")
    K.leafy_plant(k, K.T(), random.Random(p["seed"]), p["leaves"], p["height"], p["spread"], z0=z)
    return K.done(k, n, col, root)
