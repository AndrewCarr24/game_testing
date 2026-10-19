"""The oat throw sized for a library armchair's narrower arm (0.17 m, seat 0.44)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_throw as base  # noqa: E402

importlib.reload(base)

NAME = "DecorC_ThrowChair"
P = dict(base.P, name=NAME, seed=11, arm_w=0.17, seat_h=0.44, width=0.5)


def build(**overrides):
    return base.build(**{**P, **overrides})
