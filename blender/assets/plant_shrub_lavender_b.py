"""Variant (other seed) of lavender for the estate planting; same look, different silhouette."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plant_shrub  # noqa: E402

importlib.reload(plant_shrub)
common = plant_shrub.common

NAME = "PlantShrubLavenderB"
P = dict(name=NAME, kind="lavender", seed=22)


def build(**overrides):
    return plant_shrub.build(**{**P, **overrides})
