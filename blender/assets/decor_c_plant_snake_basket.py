"""Snake plant in a woven basket (gym)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_plant_snake as base  # noqa: E402

importlib.reload(base)

NAME = "DecorC_PlantSnakeBasket"
P = dict(base.P, name=NAME, seed=9, pot="wicker", pot_kind="basket", pot_r=0.19, pot_h=0.34, height=0.8, dress="soil")


def build(**overrides):
    return base.build(**{**P, **overrides})
