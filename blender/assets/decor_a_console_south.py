"""Console styling for the great room's south console (a vase already stands at its right end)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_a_console  # noqa: E402

importlib.reload(decor_a_console)
common = decor_a_console.common

NAME = "DecorAConsoleSouth"
P = dict(decor_a_console.P, name=NAME, variant="south", seed=51)


def build(**overrides):
    return decor_a_console.build(**{**P, **overrides})
