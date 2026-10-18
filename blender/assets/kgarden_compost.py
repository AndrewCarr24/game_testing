"""Three-bay compost store of teak slats on dark-metal posts, 3.6 x 1.2 x 1.1 m, open
front (-Y) with horizontal slats removable in the middle bay; compost heaps inside.
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

NAME = "KgardenCompost"
P = dict(name=NAME, seed=3)


def build(**overrides):
    p = {**P, **overrides}
    rng = random.Random(p["seed"])
    B = kc.Builder(p["name"])
    teak = B.mat("Teak", outdoor.teak(), tile=0.5)
    metal = B.mat("Posts", outdoor.dark_metal())
    soil = B.mat("Compost", kc.flat("Compost", (0.035, 0.025, 0.018)))
    mulch = B.mat("Mulch", kc.flat("Mulch", (0.09, 0.06, 0.035)))
    L, D, H = 3.6, 1.2, 1.1
    bays = 3
    bw = L / bays
    xs = [-L / 2 + i * bw for i in range(bays + 1)]
    for x in (-L / 2, L / 2):
        for y in (-D / 2, D / 2):
            B.box(metal, (x, y, H / 2), (0.07, 0.07, H), skip=("-z",))
    # back wall slats, solid divider boards, front slats (4 high in the end bays only)
    for k in range(4):
        z = 0.11 + k * 0.23
        B.box(teak, (0, D / 2, z), (L, 0.03, 0.2), skip=("-z", "+z"))
        for bi in (0, 2):
            B.box(teak, (xs[bi] + bw / 2, -D / 2, z), (bw - 0.08, 0.03, 0.2), skip=("-z", "+z"))
    for x in xs[1:-1]:
        B.box(teak, (x, 0, 0.5), (0.03, D - 0.04, 1.0), skip=("-z", "+z", "-y", "+y"))
    for x in (-L / 2 + 0.02, L / 2 - 0.02):
        B.box(teak, (x, 0, 0.5), (0.03, D - 0.04, 1.0), skip=("-z", "+z", "-y", "+y"))
    # compost: dark heap, mulch heap, empty bay with a little
    B.dome(soil, (xs[0] + bw / 2, 0.02, 0.0), 0.55, 0.75, n=7, rng=rng, squash=0.85)
    B.dome(mulch, (xs[2] + bw / 2, 0.02, 0.0), 0.5, 0.55, n=7, rng=rng, squash=0.85)
    B.dome(soil, (xs[1] + bw / 2, 0.1, 0.0), 0.35, 0.22, n=6, rng=rng)
    return B.finish()
