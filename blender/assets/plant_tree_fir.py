"""Tall sparse fir, 12 m, layered drooping tiers (wrapper of plant_tree.py)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plant_tree  # noqa: E402

importlib.reload(plant_tree)
common = plant_tree.common

NAME = "PlantTreeFir"
P = dict(name=NAME, kind="fir", seed=8)


def build(**overrides):
    return plant_tree.build(**{**P, **overrides})
