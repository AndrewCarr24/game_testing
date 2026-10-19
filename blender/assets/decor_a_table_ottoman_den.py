"""Den ottoman (round its vase): a tray with box and candle, a book stack."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_a_table  # noqa: E402

importlib.reload(decor_a_table)
common = decor_a_table.common

NAME = "DecorATableOttomanDen"
P = dict(decor_a_table.P, name=NAME, variant="ottoman_den", seed=18, flat_books=True)


def build(**overrides):
    return decor_a_table.build(**{**P, **overrides})
