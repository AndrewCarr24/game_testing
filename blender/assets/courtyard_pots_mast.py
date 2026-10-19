"""Terracotta pot group round the foot of the festoon's free-standing mast (courtyard_pots,
variant mast): a big low pot centred on the mast, with a fern pot beside it."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import courtyard_pots  # noqa: E402

importlib.reload(courtyard_pots)
common = courtyard_pots.common

NAME = "CourtyardPotsMast"

P = dict(
    name=NAME,
    variant="mast",
    seed=5,
)


def build(**overrides):
    return courtyard_pots.build(**{**P, **overrides})


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
