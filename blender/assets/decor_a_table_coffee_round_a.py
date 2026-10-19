"""Great room coffee table (with its vase): books + bronze sphere, a bowl."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_a_table  # noqa: E402

importlib.reload(decor_a_table)
common = decor_a_table.common

NAME = "DecorATableCoffeeRoundA"
P = dict(decor_a_table.P, name=NAME, variant="coffee_round_a", seed=13)


def build(**overrides):
    return decor_a_table.build(**{**P, **overrides})
