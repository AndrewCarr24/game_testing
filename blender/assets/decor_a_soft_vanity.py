"""Powder vanity: folded linen hand towels, a soap pump and a bud vase on a stone tray."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_a_soft  # noqa: E402

importlib.reload(decor_a_soft)
common = decor_a_soft.common

NAME = "DecorASoftVanity"
P = dict(decor_a_soft.P, name=NAME, variant="vanity")


def build(**overrides):
    return decor_a_soft.build(**{**P, **overrides})
