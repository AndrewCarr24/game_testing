"""Console styling, variant c (marble tray with carafe, books + candle, tall vase)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_a_console  # noqa: E402

importlib.reload(decor_a_console)
common = decor_a_console.common

NAME = "DecorAConsoleC"
P = dict(decor_a_console.P, name=NAME, variant="c", seed=31)


def build(**overrides):
    return decor_a_console.build(**{**P, **overrides})
