"""town_van: a van (see town_vehicles.py)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import town_vehicles  # noqa: E402

importlib.reload(town_vehicles)


def build(**overrides):
    return town_vehicles.build("van", module="town_van", tint=(0.035, 0.037, 0.04), **overrides)
