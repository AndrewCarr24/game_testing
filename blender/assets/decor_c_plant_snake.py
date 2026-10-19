"""Floor plant: a snake plant (sansevieria) in a tapered stoneware planter. Sword leaves in
a loose fan. The planter collides; the leaves don't. Origin: centre of the planter's foot."""
import importlib
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_kit as K  # noqa: E402

importlib.reload(K)

NAME = "DecorC_PlantSnake"
P = dict(name=NAME, seed=5, pot="charcoal", pot_kind="tall", pot_r=0.17, pot_h=0.42, leaves=13, height=0.8,
         spread=0.09, dress="charcoal")


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col, root, k = K.new_asset(n)
    rnd = random.Random(p["seed"])
    if p["pot_kind"] == "basket":
        K.basket(k, K.T(), p["pot"], r=p["pot_r"], h=p["pot_h"])
        z = p["pot_h"] - 0.03
        K.top_dressing(k, K.T(), p["pot_r"] - 0.012, z, p["dress"], rnd, segs=16)
    else:
        z = K.pot(k, K.T(), p["pot"], p["pot_r"], p["pot_h"], p["pot_kind"], segs=18, dress=p["dress"])
    K.snake_plant(k, K.T(), rnd, p["leaves"], p["height"], p["spread"], z0=z - 0.01)
    return K.done(k, n, col, root, collide=(p["pot"],))
