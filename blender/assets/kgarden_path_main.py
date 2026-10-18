"""Gravel walk, 8.75 m x 1.5 m, dark-metal edged (wrapper of kgarden_path.py)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kgarden_path  # noqa: E402

importlib.reload(kgarden_path)
common = kgarden_path.kc.common

NAME = "KgardenPathMain"
P = dict(name=NAME, length=8.75, width=1.5, edge=True)


def build(**overrides):
    return kgarden_path.build(**{**P, **overrides})
