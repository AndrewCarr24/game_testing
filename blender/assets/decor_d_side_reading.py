"""Reading-corner side table (guest_side_table, top r 0.26 at 0.50 m): a book left open,
an espresso cup on its saucer and folded reading glasses. Origin: the table top's centre."""
import importlib
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import decor_d_kit as kit  # noqa: E402

importlib.reload(kit)

NAME = "DecorD_SideReading"
P = dict(name=NAME)


def build(**overrides):
    p = {**P, **overrides}
    B = kit.Builder(p["name"])
    kit.open_book(B, kit.at(-0.03, 0.05, 0.0, 28), w=0.15, d=0.22, t=0.015, cover="sage", ribbon="terracotta")
    kit.cup_saucer(B, kit.at(0.14, -0.13, 0.0, 40) @ kit.Matrix.Scale(0.85, 4), "stoneware", "charcoal")
    kit.glasses(B, kit.at(-0.11, -0.14, 0.0, -35), "black")
    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    print(NAME, kit.common.triangle_count(parts))
