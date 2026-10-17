"""An ordinary interior door: the keycard door without the reader."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import door  # noqa: E402

importlib.reload(door)
common = door.common

NAME = "DoorPlain"
P = dict(name=NAME, reader_enabled=False)


def build(**overrides):
    return door.build(**{**P, **overrides})
