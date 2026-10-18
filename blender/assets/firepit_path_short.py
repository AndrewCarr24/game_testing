"""4.5 m run of firepit_path (the east link toward the pool deck)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import firepit_path  # noqa: E402

importlib.reload(firepit_path)
common = firepit_path.common
NAME = "FirepitPathShort"
P = dict(name=NAME, length=4.5)


def build(**overrides):
    return firepit_path.build(**{**P, **overrides})
