"""Terracotta pot group for either side of the courtyard doorway (courtyard_pots,
variant door): a long-tom with a little multi-stemmed standard, grass, a bowl of jasmine."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import courtyard_pots  # noqa: E402

importlib.reload(courtyard_pots)
common = courtyard_pots.common

NAME = "CourtyardPotsDoor"

P = dict(
    name=NAME,
    variant="door",
    seed=6,
)


def build(**overrides):
    return courtyard_pots.build(**{**P, **overrides})


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
