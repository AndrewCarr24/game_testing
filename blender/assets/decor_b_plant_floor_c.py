"""decor_b_plant_floor in a graphite planter (garage), taller, another seed."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import decor_b_plant_floor as base  # noqa: E402

importlib.reload(base)

NAME = "DecorBPlantFloorC"
P = dict(base.P, name=NAME, seed=27, pot="graphite", soil="graphite_dark", height=2.0, leaves=12, pot_r=0.27,
         pot_h=0.5)


def build(**overrides):
    return base.build(**{**P, **overrides})
