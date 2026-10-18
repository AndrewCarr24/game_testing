"""9 m run of firepit_path (the three axial paths of the fire garden)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import firepit_path  # noqa: E402

importlib.reload(firepit_path)
common = firepit_path.common
NAME = "FirepitPathLong"
P = dict(name=NAME, length=9.0)


def build(**overrides):
    return firepit_path.build(**{**P, **overrides})
