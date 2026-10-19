"""Guest writing-desk vignette (guest_desk 1.45 x 0.68 at 0.74 m, placed at the desk's
centre with its rotation; the lamp stands at local (+0.45, +0.11)): two books with a
small pilea in a terracotta pot on them (back left), a sage notebook and a pen in front
of the chair, a mug of coffee toward the lamp. Origin: desk top centre, sitter at -Y."""
import importlib
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import decor_d_kit as kit  # noqa: E402

importlib.reload(kit)

NAME = "DecorD_Vignette_GuestDesk"
P = dict(name=NAME, seed=12)


def build(**overrides):
    p = {**P, **overrides}
    rng = random.Random(p["seed"])
    B = kit.Builder(p["name"])
    z = kit.book_stack(B, kit.at(-0.40, 0.12, 0.0, 7), rng, 2, ["linen", "stoneware"],
                       sizes=[(0.25, 0.31), (0.22, 0.28)], thick=(0.028, 0.036), spin=3, fixed=True)
    kit.small_plant(B, kit.at(-0.41, 0.13, z), rng, pot="terracotta", r=0.06, h=0.08, leaves=12, size=0.07)
    kit.notebook(B, kit.at(-0.02, -0.10, 0.0, 95), w=0.15, d=0.21, t=0.013, cover="sage")
    kit.pen(B, kit.at(0.12, -0.12, 0.0, 80), "bronze")
    kit.mug(B, kit.at(0.24, 0.02, 0.0, 30), "stoneware", r=0.04, h=0.092)
    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    print(NAME, kit.common.triangle_count(parts))
