"""The other leaf of a pair of glass doors (see door_glass): hung on the +X jamb."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import door_glass  # noqa: E402

importlib.reload(door_glass)
common = door_glass.common

NAME = "DoorGlassR"
P = dict(name=NAME, hinge="right")


def build(**overrides):
    return door_glass.build(**{**P, **overrides})
