"""Outdoor flat-weave jute rug under the courtyard dining table (the courtyard_rug
generator, larger: the table and its ten chairs stand on it, chairs pulled out included)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import courtyard_rug  # noqa: E402

importlib.reload(courtyard_rug)
common = courtyard_rug.common

NAME = "CourtyardRugDining"

P = dict(
    name=NAME,
    size=(5.8, 3.5),
    border=0.24,
)


def build(**overrides):
    return courtyard_rug.build(**{**P, **overrides})


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
