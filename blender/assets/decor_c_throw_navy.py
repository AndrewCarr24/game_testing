"""The throw in navy linen (for the oat sofa)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_throw as base  # noqa: E402

importlib.reload(base)

NAME = "DecorC_ThrowNavy"
P = dict(base.P, name=NAME, mat="navy", seed=8)


def build(**overrides):
    return base.build(**{**P, **overrides})
