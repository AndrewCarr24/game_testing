"""town_footbridge: see town_structures.py."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import town_structures  # noqa: E402

importlib.reload(town_structures)


def build(**overrides):
    return town_structures.build("footbridge", **overrides)
