"""town_pickup_grey: a pickup (see town_vehicles.py)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import town_vehicles  # noqa: E402

importlib.reload(town_vehicles)


def build(**overrides):
    return town_vehicles.build("pickup", module="town_pickup_grey", tint=(0.33, 0.34, 0.35), **overrides)
