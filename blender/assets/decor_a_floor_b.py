"""Branches in a floor vase, a second arrangement (another seed) so two rooms don't show the same one."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_a_floor  # noqa: E402

importlib.reload(decor_a_floor)
common = decor_a_floor.common

NAME = "DecorAFloorB"
P = dict(decor_a_floor.P, name=NAME, variant="branch_vase", seed=8)


def build(**overrides):
    return decor_a_floor.build(**{**P, **overrides})
