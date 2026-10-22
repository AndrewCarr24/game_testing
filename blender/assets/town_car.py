"""town_car: a car (see town_vehicles.py)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import town_vehicles  # noqa: E402

importlib.reload(town_vehicles)


def build(**overrides):
    return town_vehicles.build("car", module="town_car", tint=(0.62, 0.63, 0.65), **overrides)
