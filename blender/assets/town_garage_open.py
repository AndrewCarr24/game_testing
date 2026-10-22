"""town_garage_open: see town_small.py."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import town_small  # noqa: E402

importlib.reload(town_small)


def build(**overrides):
    return town_small.build("garage_open", **overrides)
