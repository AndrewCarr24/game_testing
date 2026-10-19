"""Den media-wall credenza: low groups at both ends, clear of the screen."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_a_table  # noqa: E402

importlib.reload(decor_a_table)
common = decor_a_table.common

NAME = "DecorATableCredenza"
P = dict(decor_a_table.P, name=NAME, variant="credenza", seed=24, flat_books=True)


def build(**overrides):
    return decor_a_table.build(**{**P, **overrides})
