"""Three-seat sofa in navy linen: library_sofa (three seat and back cushions)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import library_armchair  # noqa: E402

importlib.reload(library_armchair)
common = library_armchair.common

NAME = "LibrarySofaNavy"
P = dict(name=NAME, fabric="navy", width=2.3, depth=0.95, seats=3, seat_h=0.45, arm_w=0.2)


def build(**overrides):
    return library_armchair.build(**{**P, **overrides})
