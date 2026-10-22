"""town_crate_stack: see town_props.py."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import town_props  # noqa: E402

importlib.reload(town_props)


def build(**overrides):
    return town_props.build("crate_stack", **overrides)
