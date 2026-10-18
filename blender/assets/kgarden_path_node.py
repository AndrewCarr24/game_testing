"""Gravel walk, 1.5 m x 1.5 m, no edge: the crossing of two walks (wrapper of kgarden_path.py)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kgarden_path  # noqa: E402

importlib.reload(kgarden_path)
common = kgarden_path.kc.common

NAME = "KgardenPathNode"
P = dict(name=NAME, length=1.5, width=1.5, edge=False)


def build(**overrides):
    return kgarden_path.build(**{**P, **overrides})
