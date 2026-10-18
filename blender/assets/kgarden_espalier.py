"""Espaliered fruit wall, 5 x 0.3 x 1.9 m: dark-metal posts every 2.5 m with four tensioned
wires, three tiers of horizontal bark cordons and clumps of leaves and blossom on them. Faces
-Y. Origin: floor centre. Units are metres."""
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

NAME = "KgardenEspalier"
P = dict(name=NAME, length=5.0, seed=5)


def build(**overrides):
    p = {**P, **overrides}
    rng = random.Random(p["seed"])
    B = kc.Builder(p["name"])
    metal = B.mat("Metal", outdoor.dark_metal())
    bark = B.mat("Bark", outdoor.bark())
    leaf = B.mat("Leaf", outdoor.foliage(), tile=1.5)
    leaf2 = B.mat("LeafDark", kc.leaf_dark())
    pink = B.mat("Blossom", kc.flat("Blossom", (0.6, 0.42, 0.44)))
    L = p["length"]
    for x in (-L / 2, 0, L / 2):
        B.box(metal, (x, 0, 0.95), (0.07, 0.07, 1.9), skip=("-z",))
    zs = (0.45, 0.9, 1.35, 1.8)
    for z in zs:
        B.bar(metal, (-L / 2, 0, z), (L / 2, 0, z), 0.012, 0.012)
    for z in zs[:3]:
        B.bar(bark, (-L / 2 + 0.2, -0.02, z), (L / 2 - 0.2, -0.02, z), 0.04, 0.04)
    B.bar(bark, (0, -0.02, 0.0), (0, -0.02, 1.35), 0.05, 0.05)
    for z in zs[:3]:
        for i in range(6):
            x = -L / 2 + 0.35 + i * (L - 0.7) / 5 + rng.uniform(-0.08, 0.08)
            B.dome(leaf if i % 3 else leaf2, (x, -0.02, z - 0.03), rng.uniform(0.24, 0.3), rng.uniform(0.15, 0.2), n=5, rng=rng, squash=0.7)
            if i % 4 == 1:
                B.dome(pink, (x + 0.1, -0.14, z + 0.08), 0.06, 0.05, n=4, rng=rng)
    return B.finish()
