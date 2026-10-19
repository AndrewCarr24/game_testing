"""Den side table: a tumbler and two small books beside the lamp."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_a_table  # noqa: E402

importlib.reload(decor_a_table)
common = decor_a_table.common

NAME = "DecorATableSideGlass"
P = dict(decor_a_table.P, name=NAME, variant="side_glass", seed=20, flat_books=True)


def build(**overrides):
    return decor_a_table.build(**{**P, **overrides})
