"""Scatter cushion in navy linen."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_cushion as base  # noqa: E402

importlib.reload(base)

NAME = "DecorC_CushionNavy"
P = dict(base.P, name=NAME, mat="navy", seed=4)


def build(**overrides):
    return base.build(**{**P, **overrides})
