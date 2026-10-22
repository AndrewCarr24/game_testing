"""town_suv: a suv (see town_vehicles.py)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import town_vehicles  # noqa: E402

importlib.reload(town_vehicles)


def build(**overrides):
    return town_vehicles.build("suv", module="town_suv", tint=(0.92, 0.92, 0.9), **overrides)
