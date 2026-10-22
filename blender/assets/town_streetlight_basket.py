"""town_streetlight_basket: the acorn lamp post with a flower-basket arm (town_props.py)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import town_props  # noqa: E402

importlib.reload(town_props)


def build(**overrides):
    root, parts = town_props.build("streetlight", module="town_streetlight_basket", basket=True, **overrides)
    return root, parts
