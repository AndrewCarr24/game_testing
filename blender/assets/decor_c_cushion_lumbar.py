"""Long lumbar cushion in oat linen."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_cushion as base  # noqa: E402

importlib.reload(base)

NAME = "DecorC_CushionLumbar"
P = dict(base.P, name=NAME, w=0.6, h=0.34, t=0.17, seed=6, lean=8.0)


def build(**overrides):
    return base.build(**{**P, **overrides})
