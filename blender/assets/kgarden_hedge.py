"""Clipped yew hedge, 6 m long, 0.6 m thick, 0.95 m tall, with slightly chamfered shoulders
(the garden's low enclosure). Long axis along X, origin the floor centre; the ends are
capped. Units are metres."""
import importlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kgarden_common as kc  # noqa: E402

importlib.reload(kc)
outdoor = kc.outdoor

NAME = "KgardenHedge"
P = dict(name=NAME, length=6.0, thick=0.6, height=0.95, chamfer=0.04)


def build(**overrides):
    p = {**P, **overrides}
    B = kc.Builder(p["name"])
    leaf = B.mat("Yew", outdoor.foliage(), tile=1.5)
    L, T, H, c = p["length"], p["thick"], p["height"], p["chamfer"]
    hy = T / 2
    # profile in (y, z), counter-clockwise looking along +X (so extrusion normals face outward)
    prof = [(-hy, 0), (hy, 0), (hy, H - 0.12), (hy - c, H), (-hy + c, H), (-hy, H - 0.12)]
    for i in range(1, 5):          # skip the bottom edge (0 -> 1)
        a, b = prof[i], prof[(i + 1) % len(prof)]
        B.quad(leaf, (-L / 2, a[0], a[1]), (L / 2, a[0], a[1]), (L / 2, b[0], b[1]), (-L / 2, b[0], b[1]), cell=kc.CELL)
    # the two vertical sides: i = 1 -> 2 (east face, +Y) and 5 -> 0 (-Y)
    a, b = prof[5], prof[0]
    B.quad(leaf, (-L / 2, a[0], a[1]), (L / 2, a[0], a[1]), (L / 2, b[0], b[1]), (-L / 2, b[0], b[1]), cell=kc.CELL)
    a, b = prof[1], prof[2]
    B.quad(leaf, (-L / 2, a[0], a[1]), (L / 2, a[0], a[1]), (L / 2, b[0], b[1]), (-L / 2, b[0], b[1]), cell=kc.CELL)
    # end caps
    B.face(leaf, [(-L / 2, y, z) for y, z in prof][::-1])
    B.face(leaf, [(L / 2, y, z) for y, z in prof])
    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    kc.report(root, parts)
