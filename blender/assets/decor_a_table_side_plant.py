"""Side table without a lamp: a small plant on two books."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_a_table  # noqa: E402

importlib.reload(decor_a_table)
common = decor_a_table.common

NAME = "DecorATableSidePlant"
P = dict(decor_a_table.P, name=NAME, variant="side_plant", seed=22)


def build(**overrides):
    return decor_a_table.build(**{**P, **overrides})
