"""Low path bollard, 0.7 m: dark-metal post with a warm glowing lens band under a cap.
Origin: floor centre. Units are metres."""
import importlib
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kgarden_common as kc  # noqa: E402

importlib.reload(kc)
outdoor = kc.outdoor

NAME = "KgardenBollard"
P = dict(name=NAME, height=0.7)


def build(**overrides):
    p = {**P, **overrides}
    B = kc.Builder(p["name"])
    metal = B.mat("Metal", outdoor.dark_metal())
    lamp = B.mat("Lamp", outdoor.lamp())
    h = p["height"]
    B.box(metal, (0, 0, (h - 0.2) / 2), (0.09, 0.09, h - 0.2), skip=("-z",))
    B.box(lamp, (0, 0, h - 0.1), (0.09, 0.09, 0.14), skip=("-z", "+z"))
    B.box(metal, (0, 0, h + 0.01), (0.13, 0.13, 0.03), skip=("-z",))
    return B.finish()
