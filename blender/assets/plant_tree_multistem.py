"""Multi-stem birch-like tree, 7 m, light green crown (wrapper of plant_tree.py)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plant_tree  # noqa: E402

importlib.reload(plant_tree)
common = plant_tree.common

NAME = "PlantTreeMultistem"
P = dict(name=NAME, kind="multistem", seed=4)


def build(**overrides):
    return plant_tree.build(**{**P, **overrides})
