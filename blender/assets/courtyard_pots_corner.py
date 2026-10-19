"""Terracotta pot group standing free in the courtyard (courtyard_pots, variant corner):
a big rolled-rim pot of fern, a long-tom of golden grass and a small clipped boxwood."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import courtyard_pots  # noqa: E402

importlib.reload(courtyard_pots)
common = courtyard_pots.common

NAME = "CourtyardPotsCorner"

P = dict(
    name=NAME,
    variant="corner",
    seed=8,
)


def build(**overrides):
    return courtyard_pots.build(**{**P, **overrides})


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
