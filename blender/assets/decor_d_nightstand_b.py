"""Primary bedroom nightstand vignette (carafe on a tray, two books): decor_d_nightstand, ink palette."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_d_nightstand as base  # noqa: E402

importlib.reload(base)

NAME = "DecorD_Nightstand_B"
P = dict(name=NAME, variant="carafe", width=0.55, palette="ink", seed=9)


def build(**overrides):
    return base.build(**{**P, **overrides})
