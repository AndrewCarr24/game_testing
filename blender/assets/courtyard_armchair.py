"""Outdoor lounge armchair: the courtyard sofa generator, one seat wide, one pillow."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import courtyard_sofa  # noqa: E402

importlib.reload(courtyard_sofa)
common = courtyard_sofa.common

NAME = "CourtyardArmchair"

P = dict(
    name=NAME,
    width=0.92,
    depth=0.92,
    seat_n=1,
    pillows=1,
)


def build(**overrides):
    return courtyard_sofa.build(**{**P, **overrides})


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
