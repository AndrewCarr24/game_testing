"""Hotel-style welcome at the foot of the guest bed: two folded linen bath towels and a
sage hand towel stacked on the bench, a cut eucalyptus sprig laid across the top.
Origin: centre of the stack's underside."""
import importlib
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import decor_d_kit as kit  # noqa: E402

importlib.reload(kit)

NAME = "DecorD_TowelsGuest"
P = dict(name=NAME, seed=6)


def build(**overrides):
    p = {**P, **overrides}
    rng = random.Random(p["seed"])
    B = kit.Builder(p["name"])
    z = kit.towel_stack(B, kit.at(), rng, ["linen", "linen", "sage"],
                        [(0.40, 0.27, 0.05), (0.395, 0.265, 0.046), (0.31, 0.2, 0.032)])
    kit.sprig(B, kit.at(0.01, -0.01, z - 0.002, 28), rng, n=9, L=0.24)
    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    print(NAME, kit.common.triangle_count(parts))
