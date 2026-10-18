"""Library armchair in cognac leather (library_armchair variant)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import library_armchair  # noqa: E402

importlib.reload(library_armchair)
common = library_armchair.common

NAME = "LibraryArmchairCognac"
P = dict(name=NAME, fabric="cognac")


def build(**overrides):
    return library_armchair.build(**{**P, **overrides})
