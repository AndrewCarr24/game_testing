"""Round smoked-oak coffee table on a bronze pedestal (living_side_table, scaled up)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import living_side_table  # noqa: E402

importlib.reload(living_side_table)

NAME = "LivingCoffeeRound"
P = dict(name=NAME, top_r=0.56, top_t=0.05, height=0.36, top="oak", foot_r=0.34, neck_r=0.15)


def build(**overrides):
    return living_side_table.build(**{**P, **overrides})
