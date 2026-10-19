"""Primary bath vanity, left end: a small upright plant in a glossy white pot and a
pillar candle on a brass dish. Origin: on the counter, centre of the group."""
import importlib
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import decor_d_kit as kit  # noqa: E402

importlib.reload(kit)

NAME = "DecorD_VanityPlant"
P = dict(name=NAME, seed=8)


def build(**overrides):
    p = {**P, **overrides}
    rng = random.Random(p["seed"])
    B = kit.Builder(p["name"])
    kit.small_plant(B, kit.at(-0.02, 0.08, 0.0), rng, pot="ceramic", r=0.07, h=0.11, leaves=13, size=0.085,
                    kind="upright", leaf="bath_leaf", soil="bath_soil")
    kit.round_tray(B, kit.at(0.10, -0.08, 0.0), "brass", r=0.055, h=0.012, wall=0.003, base=0.003)
    kit.candle(B, kit.at(0.10, -0.08, 0.003), r=0.032, h=0.075, wax="paper")
    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    print(NAME, kit.common.triangle_count(parts))
