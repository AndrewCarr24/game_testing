"""Teak garden bench on dark-metal sled legs, 1.8 x 0.5 x 0.8 m (seat 0.45, slatted back),
front faces -Y. Origin: floor centre. Units are metres."""
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

NAME = "KgardenBench"
P = dict(name=NAME, length=1.8)


def build(**overrides):
    p = {**P, **overrides}
    B = kc.Builder(p["name"])
    teak = B.mat("Teak", outdoor.teak(), tile=0.5)
    metal = B.mat("Legs", outdoor.dark_metal())
    L = p["length"]
    for i, y in enumerate((-0.15, 0.0, 0.15)):
        B.box(teak, (0, y, 0.43), (L, 0.095, 0.04), skip=("-z",))
    for sx in (-1, 1):
        x = sx * (L / 2 - 0.2)
        B.bar(metal, (x, -0.2, 0.0125), (x, 0.2, 0.0125), 0.04, 0.025)
        B.bar(metal, (x, -0.2, 0.0), (x, -0.2, 0.41), 0.04, 0.04)
        B.bar(metal, (x, 0.2, 0.0), (x, 0.26, 0.78), 0.04, 0.04)
    for z in (0.58, 0.72):
        B.box(teak, (0, 0.22 + (z - 0.43) * 0.18, z), (L - 0.2, 0.03, 0.08), skip=("-z",))
    return B.finish()
