"""Large square limestone planter (1.2 m, 0.8 m tall, with a cap) holding one big clipped
boxwood cloud and two smaller clipped balls. Origin: floor centre. Real geometry; the
foliage is the shared textured material (box_uv at 1.5 m)."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pool_common as pc  # noqa: E402

importlib.reload(pc)
common = pc.common

NAME = "PoolPlanter"

P = dict(name=NAME, size=1.2, height=0.78, small=True)


def build(**overrides):
    p = {**P, **overrides}
    b = pc.Builder(p["name"])
    stone, soil, leaf = pc.planter_stone(), pc.outdoor.soil(), pc.outdoor.foliage()
    s, H = p["size"], p["height"]
    h = s / 2
    b.box(stone, (-h, -h, 0.0), (h, h, H), skip=("-z", "+z"), step=1.5)
    b.box(stone, (-h - 0.03, -h - 0.03, H), (h + 0.03, h + 0.03, H + 0.05), skip=("-z", "+z"))
    # cap ring top + soil inside
    t, w = H + 0.05, 0.10
    b.hquad(stone, -h - 0.03, -h - 0.03, h + 0.03, -h + w, t)
    b.hquad(stone, -h - 0.03, h - w, h + 0.03, h + 0.03, t)
    b.hquad(stone, -h - 0.03, -h + w, -h + w, h - w, t)
    b.hquad(stone, h - w, -h + w, h + 0.03, h - w, t)
    b.hquad(soil, -h + w, -h + w, h - w, h - w, t - 0.12)
    b.vwall(soil, (-h + w, -h + w), (h - w, -h + w), t - 0.12, t, (0, 1), step=None)
    b.vwall(soil, (h - w, -h + w), (h - w, h - w), t - 0.12, t, (-1, 0), step=None)
    b.vwall(soil, (h - w, h - w), (-h + w, h - w), t - 0.12, t, (0, -1), step=None)
    b.vwall(soil, (-h + w, h - w), (-h + w, -h + w), t - 0.12, t, (1, 0), step=None)
    b.ball(leaf, (0.0, 0.0, t + 0.40), (0.50, 0.50, 0.46), seg=12, rings=7)
    if p["small"]:
        b.ball(leaf, (0.30, -0.26, t + 0.12), (0.24, 0.24, 0.22), seg=8, rings=5)
        b.ball(leaf, (-0.28, 0.28, t + 0.10), (0.20, 0.20, 0.18), seg=8, rings=5)
    return b.finish()


if __name__ == "__main__":
    root, parts = build()
    pc.report(root, parts)
