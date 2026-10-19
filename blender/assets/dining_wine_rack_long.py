"""Six-bay variant of the cellar racking (6 m run), for the long east wall."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dining_wine_rack  # noqa: E402

importlib.reload(dining_wine_rack)
common = dining_wine_rack.common

NAME = "DiningWineRackLong"
P = dict(name=NAME, bays=6, seed=8, bottle_segs=7, empty=0.10)


def build(**overrides):
    return dining_wine_rack.build(**{**P, **overrides})
