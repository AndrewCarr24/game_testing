"""A smaller oat scatter cushion for an armchair (0.42 m)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_cushion as base  # noqa: E402

importlib.reload(base)

NAME = "DecorC_CushionSmall"
P = dict(base.P, name=NAME, w=0.42, h=0.42, t=0.18, seed=9, lean=9.0)


def build(**overrides):
    return base.build(**{**P, **overrides})
