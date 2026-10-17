"""Reading chair for the bedroom: the lounge chair in the bedroom palette
(ink leather, bronze frame, smoked-oak-dark arm caps stay walnut)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lounge_chair  # noqa: E402

importlib.reload(lounge_chair)
common = lounge_chair.common

NAME = "BedroomChair"
P = dict(name=NAME, leather_name="M_Leather_Ink", leather=(0.012, 0.016, 0.028), frame="bronze")


def build(**overrides):
    return lounge_chair.build(**{**P, **overrides})
