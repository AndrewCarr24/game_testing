"""Round coffee-table vignette (primary bedroom sitting area, living_coffee_round: top r
0.56 at 0.36 m): three large art books turned off-axis with a bronze ring on a marble
block on top, a pair of vases (tall charcoal bottle, low marble-white globe) and a low
matte stoneware bowl toward the sofa. Origin: the table's centre, on its top."""
import importlib
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import decor_d_kit as kit  # noqa: E402

importlib.reload(kit)

NAME = "DecorD_Vignette_Coffee"
P = dict(name=NAME, seed=7, palette="ink")


def build(**overrides):
    p = {**P, **overrides}
    rng = random.Random(p["seed"])
    pal = kit.PALETTES[p["palette"]]
    B = kit.Builder(p["name"])
    z = kit.book_stack(B, kit.at(-0.16, 0.10, 0.0, 18), rng, 3, ["ink", "oat", "stone_fabric"],
                       sizes=[(0.31, 0.39), (0.28, 0.34), (0.24, 0.30)], thick=(0.028, 0.042), spin=4, fixed=True)
    kit.ring_sculpture(B, kit.at(-0.15, 0.10, z, 24), pal["metal"], R=0.06, r=0.010, base_key="marble")
    kit.vessel(B, kit.at(0.25, 0.17, 0.0), "charcoal", "bottle", h=0.34, r=0.075, segs=16)
    kit.vessel(B, kit.at(0.35, 0.00, 0.0), "marble", "globe", h=0.17, r=0.085, segs=16)
    kit.bowl(B, kit.at(0.10, -0.26, 0.0), "stoneware", r=0.13, h=0.055, segs=20)
    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    print(NAME, kit.common.triangle_count(parts))
