"""Primary bath vanity, right end: three folded hand towels (ivory, oat, ivory) and a
stone candle jar with a brass lid. Origin: on the counter, centre of the group."""
import importlib
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import decor_d_kit as kit  # noqa: E402

importlib.reload(kit)

NAME = "DecorD_VanityTowels"
P = dict(name=NAME, seed=3)


def build(**overrides):
    p = {**P, **overrides}
    rng = random.Random(p["seed"])
    B = kit.Builder(p["name"])
    kit.towel_stack(B, kit.at(0.05, -0.02, 0.0, 90), rng, ["ivory", "oat", "ivory"],
                    [(0.29, 0.19, 0.034), (0.28, 0.185, 0.032), (0.275, 0.18, 0.03)])
    kit.candle_jar(B, kit.at(-0.13, 0.11, 0.0), "bath_stone", r=0.042, h=0.085, lid="brass")
    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    print(NAME, kit.common.triangle_count(parts))
