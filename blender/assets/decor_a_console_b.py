"""Console styling, variant b (books + cairn, black bowl, ceramic trio)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_a_console  # noqa: E402

importlib.reload(decor_a_console)
common = decor_a_console.common

NAME = "DecorAConsoleB"
P = dict(decor_a_console.P, name=NAME, variant="b", seed=21)


def build(**overrides):
    return decor_a_console.build(**{**P, **overrides})
