"""decor_b_plant_floor in a terracotta pot with dark soil (mudroom), a different seed."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import decor_b_plant_floor as base  # noqa: E402

importlib.reload(base)

NAME = "DecorBPlantFloorB"
P = dict(base.P, name=NAME, seed=19, pot="terracotta", soil="soil", height=1.7, leaves=10)


def build(**overrides):
    return base.build(**{**P, **overrides})
