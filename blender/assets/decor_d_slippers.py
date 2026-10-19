"""A pair of felt house slippers left by the bed, one a little turned: charcoal soles,
grey felt uppers, oat footbeds. Origin: between them on the floor (or rug), toes +Y."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import decor_d_kit as kit  # noqa: E402

importlib.reload(kit)

NAME = "DecorD_Slippers"
P = dict(name=NAME, upper="stone_fabric", footbed="oat")


def build(**overrides):
    p = {**P, **overrides}
    B = kit.Builder(p["name"])
    kit.slipper(B, kit.at(0.065, 0.0, 0.0, -4), side=1, upper=p["upper"], footbed=p["footbed"])
    kit.slipper(B, kit.at(-0.07, 0.025, 0.0, 9), side=-1, upper=p["upper"], footbed=p["footbed"])
    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    print(NAME, kit.common.triangle_count(parts))
