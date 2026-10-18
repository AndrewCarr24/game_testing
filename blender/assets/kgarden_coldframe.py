"""Cold frame: teak box 1.2 x 0.8 m (0.35 m at the back, 0.2 m at the front) with a
dark-metal glazed lid propped open at the front. Origin: floor centre; the lid hinges at the
back (+Y) and opens towards -Y. Units are metres."""
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

NAME = "KgardenColdframe"
P = dict(name=NAME, seed=2)


def build(**overrides):
    p = {**P, **overrides}
    rng = random.Random(p["seed"])
    B = kc.Builder(p["name"])
    teak = B.mat("Teak", outdoor.teak(), tile=0.5)
    metal = B.mat("Frame", outdoor.dark_metal())
    glass = B.mat("Glass", outdoor.glass())
    soil = B.mat("Soil", outdoor.soil())
    leaf = B.mat("Leaf", kc.leaf_light())
    L, D, hb, hf, t = 1.2, 0.8, 0.35, 0.2, 0.035
    zs = 0.16
    # sloped side panels (trapezoids) and front / back boards
    for sx in (-1, 1):
        x0, x1 = sx * L / 2, sx * (L / 2 - t)
        if sx > 0:
            B.quad(teak, (x0, -D / 2, 0), (x0, D / 2, 0), (x0, D / 2, hb), (x0, -D / 2, hf))
            B.quad(teak, (x1, D / 2, 0), (x1, -D / 2, 0), (x1, -D / 2, hf), (x1, D / 2, hb))
            B.quad(teak, (x1, -D / 2, hf), (x1, D / 2, hb), (x0, D / 2, hb), (x0, -D / 2, hf))
        else:
            B.quad(teak, (x0, D / 2, 0), (x0, -D / 2, 0), (x0, -D / 2, hf), (x0, D / 2, hb))
            B.quad(teak, (x1, -D / 2, 0), (x1, D / 2, 0), (x1, D / 2, hb), (x1, -D / 2, hf))
            B.quad(teak, (x0, -D / 2, hf), (x0, D / 2, hb), (x1, D / 2, hb), (x1, -D / 2, hf))
    B.box(teak, (0, D / 2 - t / 2, hb / 2), (L - 2 * t, t, hb), skip=("-z", "+z", "-x", "+x"))
    B.box(teak, (0, -D / 2 + t / 2, hf / 2), (L - 2 * t, t, hf), skip=("-z", "+z", "-x", "+x"))
    B.quad(soil, (-L / 2 + t, -D / 2 + t, zs), (L / 2 - t, -D / 2 + t, zs), (L / 2 - t, D / 2 - t, zs), (-L / 2 + t, D / 2 - t, zs))
    for i in range(7):
        B.dome(leaf, (-L / 2 + 0.2 + i * 0.133, rng.uniform(-0.15, 0.15), zs), 0.07, 0.07, n=5, rng=rng)
    # lid: hinged at the back top edge, propped open ~50 deg
    ang = math.radians(50)
    hy, hz = D / 2, hb
    ly, lz = -D * math.cos(ang), D * math.sin(ang)
    a = (-L / 2, hy, hz)
    b = (L / 2, hy, hz)
    c = (L / 2, hy + ly, hz + lz)
    d = (-L / 2, hy + ly, hz + lz)
    B.quad(glass, a, b, c, d)
    for pa, pb in ((a, d), (b, c)):
        B.bar(metal, pa, pb, 0.04, 0.04)
    B.bar(metal, d, c, 0.04, 0.04)
    B.bar(metal, a, b, 0.04, 0.04)
    B.bar(metal, (0, hy + ly * 0.92, hz + lz * 0.92), (0, -D / 2 + 0.05, hf), 0.025, 0.025)  # prop stay
    return B.finish()
