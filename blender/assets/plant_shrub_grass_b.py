"""Variant (other seed) of grass for the estate planting; same look, different silhouette."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plant_shrub  # noqa: E402

importlib.reload(plant_shrub)
common = plant_shrub.common

NAME = "PlantShrubGrassB"
P = dict(name=NAME, kind="grass", seed=21)


def build(**overrides):
    return plant_shrub.build(**{**P, **overrides})
