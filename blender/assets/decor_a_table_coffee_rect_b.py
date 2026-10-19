"""Great room window-lounge coffee table: open book with reading glasses, a cup, a small plant."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_a_table  # noqa: E402

importlib.reload(decor_a_table)
common = decor_a_table.common

NAME = "DecorATableCoffeeRectB"
P = dict(decor_a_table.P, name=NAME, variant="coffee_rect_b", seed=16)


def build(**overrides):
    return decor_a_table.build(**{**P, **overrides})
