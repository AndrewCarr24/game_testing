"""A single glass door (see door_glass) for the kitchen's 1.56 m window bays (its 14 m glass wall is nine bays)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import door_glass  # noqa: E402

importlib.reload(door_glass)
common = door_glass.common

NAME = "DoorGlassWide"
P = dict(name=NAME, opening=(14.0 / 9.0, 3.0))


def build(**overrides):
    return door_glass.build(**{**P, **overrides})
