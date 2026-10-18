"""Circular mulched tree bed with a slim dark-metal edge, 2.2 m across, for the orchard
fruit trees. Origin: its centre on the lawn. Units are metres."""
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

NAME = "KgardenTreeBed"
P = dict(name=NAME, radius=1.1, n=14)


def build(**overrides):
    p = {**P, **overrides}
    B = kc.Builder(p["name"])
    mulch = B.mat("Mulch", kc.flat("Mulch", (0.085, 0.06, 0.04)))
    metal = B.mat("Edge", outdoor.dark_metal())
    r, n, h = p["radius"], p["n"], 0.04
    pts = [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    # disc: fan from the centre in two rings (keeps the triangles small enough for lighting)
    mid = [(x * 0.5, y * 0.5) for x, y in pts]
    for i in range(n):
        j = (i + 1) % n
        B.face(mulch, [(*mid[i], h), (*mid[j], h), (0, 0, h)] if False else [(0, 0, h), (*mid[i], h), (*mid[j], h)][::-1])
        B.face(mulch, [(*mid[i], h), (*pts[i], h), (*pts[j], h), (*mid[j], h)][::-1])
    # ring edge: outer wall and flat top
    r2 = r + 0.012
    for i in range(n):
        j = (i + 1) % n
        a = (r2 * math.cos(2 * math.pi * i / n), r2 * math.sin(2 * math.pi * i / n))
        b = (r2 * math.cos(2 * math.pi * j / n), r2 * math.sin(2 * math.pi * j / n))
        B.face(metal, [(*a, 0), (*b, 0), (*b, h + 0.02), (*a, h + 0.02)])
        B.face(metal, [(*a, h + 0.02), (*b, h + 0.02), (*pts[j], h + 0.02), (*pts[i], h + 0.02)])
    return B.finish()
