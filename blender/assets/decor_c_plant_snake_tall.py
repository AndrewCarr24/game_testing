"""A taller snake plant in a bigger charcoal planter, for a room corner (about 1.5 m)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_plant_snake as base  # noqa: E402

importlib.reload(base)

NAME = "DecorC_PlantSnakeTall"
P = dict(base.P, name=NAME, seed=14, pot_r=0.2, pot_h=0.5, leaves=17, height=1.05, spread=0.12, )


def build(**overrides):
    return base.build(**{**P, **overrides})
