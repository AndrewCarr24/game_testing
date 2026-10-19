"""Bath caddy across the freestanding tub: a walnut board resting on both rims (cleats
underneath keep it there), with a stone candle jar, a book laid open face-down and a
glass. Board along X (across the tub), origin: centre of its underside = rim height."""
import importlib
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import decor_d_kit as kit  # noqa: E402

importlib.reload(kit)

NAME = "DecorD_TubCaddy"
# rim_inner: the flat rim top's inner edge (from the tub's long axis) where the cleats sit. bath_tub's
# footprint is a superellipse, so it narrows away from mid-length: 0.356 at 0.33 m off centre.
P = dict(name=NAME, length=0.80, depth=0.21, thick=0.022, rim_inner=0.356, cleat=0.06)


def build(**overrides):
    p = {**P, **overrides}
    B = kit.Builder(p["name"])
    L, D, T = p["length"], p["depth"], p["thick"]
    B.add("walnut", kit.cbox((L, D, T), 0.003), kit.Matrix.Translation((0, 0, T / 2)))
    for sx in (-1, 1):
        x = sx * (p["rim_inner"] - 0.012)
        B.add("walnut", kit.cbox((0.018, p["cleat"], 0.016), 0.002, drop=("+z",)), kit.Matrix.Translation((x, 0, -0.008)))
    kit.candle_jar(B, kit.at(-0.22, 0.01, T), "bath_stone", r=0.04, h=0.08)
    kit.tent_book(B, kit.at(0.01, 0.0, T, 4), w=0.12, d=0.18, t=0.016, cover="ink")
    kit.wine_glass(B, kit.at(0.25, 0.02, T))
    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    print(NAME, kit.common.triangle_count(parts))
