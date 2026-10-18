"""Variant (other seed) of multistem for the estate planting; same look, different silhouette."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plant_tree  # noqa: E402

importlib.reload(plant_tree)
common = plant_tree.common

NAME = "PlantTreeMultistemB"
P = dict(name=NAME, kind="multistem", seed=13)


def build(**overrides):
    return plant_tree.build(**{**P, **overrides})
