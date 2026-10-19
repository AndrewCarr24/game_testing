"""Three matte charcoal vessels (decor_c_ceramics, charcoal family)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_ceramics as base  # noqa: E402

importlib.reload(base)

NAME = "DecorC_CeramicsB"
P = dict(base.P, name=NAME, seed=4, family="charcoal")


def build(**overrides):
    return base.build(**{**P, **overrides})
