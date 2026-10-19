"""Woven rope basket on the bath floor holding three rolled towels standing on end, with
two rope handles (wrappers change the weave and the cloths: decor_d_basket_guest
holds rolled throws). The basket collides (floor piece); the towels don't. Origin: floor."""
import importlib
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import decor_d_kit as kit  # noqa: E402

importlib.reload(kit)

NAME = "DecorD_Basket"
P = dict(name=NAME, radius=0.19, height=0.32, seed=2, weave="oat", cloths=("ivory", "oat", "ivory"), roll_r=0.052,
         roll_len=0.34)


def build(**overrides):
    p = {**P, **overrides}
    rng = random.Random(p["seed"])
    key = p["weave"] + "@Basket"
    B = kit.Builder(p["name"], collide=(key,))
    r, h = p["radius"], p["height"]
    fz = kit.basket(B, kit.at(), p["weave"], r=r, h=h, ribs=11, segs=14)
    for sx in (-1, 1):
        pts = [(sx * (r + 0.004), 0.05 * math.cos(math.pi * k / 6), h - 0.03 + 0.035 * math.sin(math.pi * k / 6)) for k in range(7)]
        pts = [(x + sx * 0.012 * math.sin(math.pi * k / 6), y, z) for k, (x, y, z) in enumerate(pts)]
        B.add(p["weave"], kit.tube(pts, 0.007, sides=6), kit.Matrix.Identity(4))
    rl = p["roll_r"]
    for i, cloth in enumerate(p["cloths"]):
        a = 2 * math.pi * i / 3 + 0.4
        rr = rl * 1.27
        lean = kit.Matrix.Rotation(math.radians(3.5), 4, kit.Vector((-math.sin(a), math.cos(a), 0)))
        M = kit.Matrix.Translation((rr * math.cos(a), rr * math.sin(a), fz)) @ lean
        kit.towel_roll(B, M, cloth, r=rl, L=p["roll_len"] - 0.03 * (i == 1), upright=True)
    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    print(NAME, kit.common.triangle_count(parts))
