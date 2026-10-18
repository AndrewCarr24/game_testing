"""Three-bay variant of the cellar racking (3 m run)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dining_wine_rack  # noqa: E402

importlib.reload(dining_wine_rack)
common = dining_wine_rack.common

NAME = "DiningWineRackShort"
P = dict(name=NAME, bays=3, seed=14)


def build(**overrides):
    return dining_wine_rack.build(**{**P, **overrides})
