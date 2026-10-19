"""Cloakroom south bench: two stacked hat boxes and a folded throw."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_a_soft  # noqa: E402

importlib.reload(decor_a_soft)
common = decor_a_soft.common

NAME = "DecorASoftBenchHatboxes"
P = dict(decor_a_soft.P, name=NAME, variant="bench_hatboxes")


def build(**overrides):
    return decor_a_soft.build(**{**P, **overrides})
