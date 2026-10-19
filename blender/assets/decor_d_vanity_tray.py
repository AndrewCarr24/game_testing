"""Primary bath vanity, between the basins: a walnut tray with a charcoal soap pump, a
stone bottle and a bar of soap. Origin: centre of the tray's underside on the counter."""
import importlib
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import decor_d_kit as kit  # noqa: E402

importlib.reload(kit)

NAME = "DecorD_VanityTray"
P = dict(name=NAME)


def build(**overrides):
    p = {**P, **overrides}
    B = kit.Builder(p["name"])
    b = kit.tray(B, kit.at(0, 0, 0, 0), "walnut", w=0.30, d=0.15, h=0.02, r=0.02, wall=0.006, base=0.006)
    kit.pump_bottle(B, kit.at(-0.075, 0.012, b, 200), "charcoal", "brass", r=0.031, h=0.15)
    kit.vessel(B, kit.at(0.01, 0.022, b), "bath_stone", "flask", h=0.11, r=0.03, segs=14)
    kit.soap(B, kit.at(0.085, -0.012, b, 12), "paper", w=0.08, d=0.05, h=0.022)
    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    print(NAME, kit.common.triangle_count(parts))
