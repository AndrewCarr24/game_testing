"""Multi-stem olive tree in a plaster planter (living_plant, kind="olive")."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import living_plant  # noqa: E402

importlib.reload(living_plant)

NAME = "LivingPlantOlive"
P = dict(name=NAME, kind="olive", seed=5, planter_r=0.38, planter_h=0.55, trunk_h=2.5, leaf_count=600,
         leaf_len=0.12, leaf_w=0.036)


def build(**overrides):
    return living_plant.build(**{**P, **overrides})
