"""Floor plant: a bird of paradise (Strelitzia nicolai) in a lathed charcoal planter, big
paddle leaves folded along the midrib on upright stems. The planter may collide; the
leaves don't. Origin: floor centre."""
import importlib
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common  # noqa: E402
import decor_b_kit as K  # noqa: E402

importlib.reload(common)
importlib.reload(K)

NAME = "DecorBPlantFloor"

P = dict(name=NAME, seed=7, pot="ceramic_charcoal", soil="coffee", pot_r=0.24, pot_h=0.44, leaves=11, height=1.85)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    a = K.Acc()
    K.plant_paddle(a, K.T(), rnd, pot=p["pot"], soil=p["soil"], pot_r=p["pot_r"], pot_h=p["pot_h"],
                   leaves=p["leaves"], height=p["height"])
    parts = a.finish(n, col, root, collide=(p["pot"],))
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
