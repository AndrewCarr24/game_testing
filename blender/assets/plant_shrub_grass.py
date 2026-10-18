"""Ornamental grass clump, straw colour (wrapper of plant_shrub.py)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plant_shrub  # noqa: E402

importlib.reload(plant_shrub)
common = plant_shrub.common

NAME = "PlantShrubGrass"
P = dict(name=NAME, kind="grass", seed=3)


def build(**overrides):
    return plant_shrub.build(**{**P, **overrides})
