"""Great room coffee table: marble tray with carafe and glasses, books + candle."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_a_table  # noqa: E402

importlib.reload(decor_a_table)
common = decor_a_table.common

NAME = "DecorATableCoffeeRoundC"
P = dict(decor_a_table.P, name=NAME, variant="coffee_round_c", seed=14)


def build(**overrides):
    return decor_a_table.build(**{**P, **overrides})
