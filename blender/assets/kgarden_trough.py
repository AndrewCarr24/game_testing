"""Limestone water trough on a plinth with a stone tap pillar and bronze spout, for the
greenhouse door, 1.7 x 0.6 m, 0.55 m tall; the tap pillar stands at the +X end.
Origin: floor centre of the trough. Units are metres."""
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

NAME = "KgardenTrough"
P = dict(name=NAME, length=1.7, width=0.6, height=0.55, wall=0.09)


def build(**overrides):
    p = {**P, **overrides}
    B = kc.Builder(p["name"])
    stone = B.mat("Stone", outdoor.stone(), tile=2.0)
    water = B.mat("Water", outdoor.water())
    bronze = B.mat("Bronze", outdoor.bronze())
    L, W, H, t = p["length"], p["width"], p["height"], p["wall"]
    # ring walls (bottomless) with the water just below the rim
    zw = H - 0.07
    ox, oy, ix, iy = L / 2, W / 2, L / 2 - t, W / 2 - t
    outer = [(-ox, -oy), (ox, -oy), (ox, oy), (-ox, oy)]
    inner = [(-ix, -iy), (ix, -iy), (ix, iy), (-ix, iy)]
    for i in range(4):
        j = (i + 1) % 4
        (ax, ay), (bx, by) = outer[i], outer[j]
        (cx, cy), (dx, dy) = inner[i], inner[j]
        B.quad(stone, (ax, ay, 0), (bx, by, 0), (bx, by, H), (ax, ay, H))
        B.quad(stone, (ax, ay, H), (bx, by, H), (dx, dy, H), (cx, cy, H))
        B.quad(stone, (cx, cy, H), (dx, dy, H), (dx, dy, zw - 0.05), (cx, cy, zw - 0.05))
    B.quad(stone, (-ix, -iy, zw - 0.05), (ix, -iy, zw - 0.05), (ix, iy, zw - 0.05), (-ix, iy, zw - 0.05))
    B.quad(water, (-ix, -iy, zw), (ix, -iy, zw), (ix, iy, zw), (-ix, iy, zw))
    # tap pillar at the east end
    px = ox + 0.28
    B.box(stone, (px, 0, 0.45), (0.26, 0.26, 0.9), cell=None, skip=("-z",))
    B.box(stone, (px, 0, 0.92), (0.32, 0.32, 0.04), skip=("-z",))
    B.bar(bronze, (px - 0.13, 0, 0.7), (px - 0.36, 0, 0.7), 0.035, 0.035, cap=True)
    B.bar(bronze, (px - 0.36, 0, 0.7), (px - 0.36, 0, 0.62), 0.035, 0.035, cap=True)
    return B.finish()
