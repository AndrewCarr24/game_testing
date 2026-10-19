"""A pair of cognac loafers set down side by side (no collider)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_a_floor  # noqa: E402

importlib.reload(decor_a_floor)
common = decor_a_floor.common

NAME = "DecorAFloorShoes"
P = dict(decor_a_floor.P, name=NAME, variant="shoes")


def build(**overrides):
    return decor_a_floor.build(**{**P, **overrides})
