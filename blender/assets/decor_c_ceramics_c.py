"""Cream bottle and moon vase with a low charcoal cylinder (decor_c_ceramics, pale family)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_ceramics as base  # noqa: E402

importlib.reload(base)

NAME = "DecorC_CeramicsC"
P = dict(base.P, name=NAME, seed=9, family="pale")


def build(**overrides):
    return base.build(**{**P, **overrides})
