"""Den bar console: decanters and tumblers on a leather tray, an ice bucket, books + candle."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_a_console  # noqa: E402

importlib.reload(decor_a_console)
common = decor_a_console.common

NAME = "DecorAConsoleBar"
P = dict(decor_a_console.P, name=NAME, variant="bar", seed=81, flat_books=True)


def build(**overrides):
    return decor_a_console.build(**{**P, **overrides})
