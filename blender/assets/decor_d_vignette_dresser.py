"""Guest dresser vignette (guest_dresser 1.6 x 0.46 at 0.80 m; the smoked-glass vase
stands at its left end, local x -0.7): two cloth books turned off-axis with a small
terracotta bowl on them, and a pale-oak tray with a carafe and two tumblers at the right.
Origin: the dresser top's centre, front -Y."""
import importlib
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import decor_d_kit as kit  # noqa: E402

importlib.reload(kit)

NAME = "DecorD_Vignette_Dresser"
P = dict(name=NAME, seed=5)


def build(**overrides):
    p = {**P, **overrides}
    rng = random.Random(p["seed"])
    B = kit.Builder(p["name"])
    z = kit.book_stack(B, kit.at(-0.16, 0.02, 0.0, -9), rng, 2, ["sage", "linen"],
                       sizes=[(0.28, 0.34), (0.24, 0.30)], thick=(0.03, 0.04), spin=3, fixed=True)
    kit.bowl(B, kit.at(-0.15, 0.03, z), "terracotta", r=0.075, h=0.04, segs=18)
    tx = 0.42
    b = kit.tray(B, kit.at(tx, 0.03, 0.0, 4), "oak_light", w=0.36, d=0.20, h=0.024, r=0.025, wall=0.007, base=0.007)
    kit.carafe(B, kit.at(tx - 0.08, 0.05, b), tumbler=False)
    kit.tumbler(B, kit.at(tx + 0.04, 0.0, b), r=0.032, h=0.085)
    kit.tumbler(B, kit.at(tx + 0.11, 0.06, b), r=0.032, h=0.085)
    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    print(NAME, kit.common.triangle_count(parts))
