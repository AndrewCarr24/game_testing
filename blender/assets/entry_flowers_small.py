"""Smaller blossom arrangement (6 branches, shorter spray) for powder-room and cloakroom
surfaces: entry_flowers with fewer, shorter branches. Origin: centre of the vase underside."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entry_flowers  # noqa: E402

importlib.reload(entry_flowers)
common = entry_flowers.common

NAME = "EntryFlowersSmall"
P = dict(name=NAME, branches=6, spray=(0.38, 0.62), seed=9, vase_h=0.36)


def build(**overrides):
    return entry_flowers.build(**{**P, **overrides})
