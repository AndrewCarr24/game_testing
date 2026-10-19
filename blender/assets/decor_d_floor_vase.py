"""Tall charcoal floor vase with cut olive branches: a stylist's corner piece where a
plant would crowd. The vase body collides (it stands on the floor); the branches don't.
Origin: floor centre; the branches lean out toward -Y (front) and the sides, not
backward into a wall (`arc`)."""
import importlib
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import decor_d_kit as kit  # noqa: E402

importlib.reload(kit)

NAME = "DecorD_FloorVase"
P = dict(name=NAME, seed=5, height=0.58, radius=0.17, glaze="charcoal", spray=0.85, leaves=200, arc=(-90, 230))


def build(**overrides):
    p = {**P, **overrides}
    rng = random.Random(p["seed"])
    key = p["glaze"] + "@Body"
    B = kit.Builder(p["name"], collide=(key,))
    h = kit.vessel(B, kit.at(), key, "ovoid", h=p["height"], r=p["radius"], segs=18)
    kit.branch_spray(B, kit.at(), rng, n=5, height=p["spray"], spread=0.5, leaves=p["leaves"], z0=h - 0.01, twigs=3,
                     arc=p["arc"])
    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    print(NAME, kit.common.triangle_count(parts))
