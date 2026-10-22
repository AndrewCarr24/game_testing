"""town_cottage_b: see town_house.py."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import town_house  # noqa: E402

importlib.reload(town_house)


def build(**overrides):
    return town_house.build(variant="cottage_b", **overrides)
