"""Courtyard raised bed along the west glass (the courtyard_bed generator); back row
kept clear for the festoon mast and the maple standing in it (local x = court y)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import courtyard_bed  # noqa: E402

importlib.reload(courtyard_bed)
common = courtyard_bed.common

NAME = "CourtyardBedWest"

P = dict(
    name=NAME,
    length=11.5,
    seed=2,
    clear=((-3.15, -2.05), (1.35, 2.65)),
)


def build(**overrides):
    return courtyard_bed.build(**{**P, **overrides})


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
