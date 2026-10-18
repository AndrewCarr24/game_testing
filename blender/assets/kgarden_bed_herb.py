""" (wrapper of kgarden_bed.py)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kgarden_bed  # noqa: E402

importlib.reload(kgarden_bed)
common = kgarden_bed.kc.common

NAME = "KgardenBedHerb"
P = dict(name=NAME, kind="herb", side="metal", seed=7)


def build(**overrides):
    return kgarden_bed.build(**{**P, **overrides})
