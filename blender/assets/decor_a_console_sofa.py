"""Console styling behind the great room sofa, between its two lamps."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_a_console  # noqa: E402

importlib.reload(decor_a_console)
common = decor_a_console.common

NAME = "DecorAConsoleSofa"
P = dict(decor_a_console.P, name=NAME, variant="sofa", seed=61, shelf_items=False)


def build(**overrides):
    return decor_a_console.build(**{**P, **overrides})
