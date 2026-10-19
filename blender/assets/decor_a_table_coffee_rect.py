"""Entry nook coffee table: fanned magazines, books + bowl, a stoneware cup."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_a_table  # noqa: E402

importlib.reload(decor_a_table)
common = decor_a_table.common

NAME = "DecorATableCoffeeRect"
P = dict(decor_a_table.P, name=NAME, variant="coffee_rect", seed=15, ceramic="stoneware")


def build(**overrides):
    return decor_a_table.build(**{**P, **overrides})
