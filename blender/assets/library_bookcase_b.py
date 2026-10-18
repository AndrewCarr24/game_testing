"""Library bookcase, two bays, arrangement B (see library_bookcase)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import library_bookcase  # noqa: E402

importlib.reload(library_bookcase)
common = library_bookcase.common

NAME = "LibraryBookcaseB"
P = dict(name=NAME, seed=23, bays=2)


def build(**overrides):
    return library_bookcase.build(**{**P, **overrides})
