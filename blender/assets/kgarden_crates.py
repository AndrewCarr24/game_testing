"""Two stacked teak harvest crates with produce (tomatoes, squash, lettuce), 0.5 x 0.4 x 0.5 m. Origin: floor centre. Units are metres."""
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

NAME = "KgardenCrates"
P = dict(name=NAME, seed=8)


def build(**overrides):
    p = {**P, **overrides}
    rng = random.Random(p["seed"])
    B = kc.Builder(p["name"])
    teak = B.mat("Teak", outdoor.teak(), tile=0.5)
    green = B.mat("Lettuce", kc.leaf_light())
    red = B.mat("Tomato", kc.flat("Tomato", (0.45, 0.03, 0.02)))
    orange = B.mat("Squash", kc.flat("Squash", (0.55, 0.16, 0.02)))
    dark = B.mat("Kale", kc.leaf_blue())

    def crate(cx, cy, z, rot, produce):
        w, d, h, t = 0.46, 0.34, 0.24, 0.025
        c, s = math.cos(rot), math.sin(rot)

        def at(x, y):
            return (cx + x * c - y * s, cy + x * s + y * c)
        # four wall boxes via the builder with a rotation, plus a bottom
        B.box(teak, (cx, cy, z + 0.02), (w, d, 0.03), rot=(0, 0, math.degrees(rot)), skip=("-z",))
        for (dx, dy, sx, sy) in ((0, -d / 2 + t / 2, w, t), (0, d / 2 - t / 2, w, t), (-w / 2 + t / 2, 0, t, d - 2 * t), (w / 2 - t / 2, 0, t, d - 2 * t)):
            px, py = at(dx, dy)
            B.box(teak, (px, py, z + h / 2), (sx, sy, h), rot=(0, 0, math.degrees(rot)), skip=("-z",))
        for i in range(3):
            px, py = at(-0.14 + i * 0.14 + rng.uniform(-0.02, 0.02), rng.uniform(-0.05, 0.05))
            B.dome(produce[i % len(produce)], (px, py, z + 0.06), 0.085, 0.12, n=4, rng=rng)
    crate(0, 0, 0, 0.0, [red, orange])
    crate(0.02, 0.0, 0.25, math.radians(5), [green, dark])
    return B.finish()
