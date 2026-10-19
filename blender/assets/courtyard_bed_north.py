"""Courtyard raised bed along the north glass (the courtyard_bed generator), full width;
back-row planting kept clear where the maple on the doorway axis and two festoon masts
stand in it (local x)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import courtyard_bed  # noqa: E402

importlib.reload(courtyard_bed)
common = courtyard_bed.common

NAME = "CourtyardBedNorth"

P = dict(
    name=NAME,
    length=19.9,
    seed=1,
    clear=((-9.95, -8.5), (-0.75, 0.75), (1.25, 2.35)),
)


def build(**overrides):
    return courtyard_bed.build(**{**P, **overrides})


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
