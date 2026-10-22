"""town_car_blue: a car (see town_vehicles.py)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import town_vehicles  # noqa: E402

importlib.reload(town_vehicles)


def build(**overrides):
    return town_vehicles.build("car", module="town_car_blue", tint=(0.07, 0.13, 0.32), **overrides)
