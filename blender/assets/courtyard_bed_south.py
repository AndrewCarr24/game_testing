"""Courtyard raised bed along the south glass, one each side of the doorway (the
courtyard_bed generator)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import courtyard_bed  # noqa: E402

importlib.reload(courtyard_bed)
common = courtyard_bed.common

NAME = "CourtyardBedSouth"

P = dict(
    name=NAME,
    length=7.55,
    seed=3,
)


def build(**overrides):
    return courtyard_bed.build(**{**P, **overrides})


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
