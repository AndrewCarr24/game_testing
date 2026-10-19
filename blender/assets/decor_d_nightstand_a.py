"""Primary bedroom nightstand vignette (books, glasses, bud vase): decor_d_nightstand, ink palette."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_d_nightstand as base  # noqa: E402

importlib.reload(base)

NAME = "DecorD_Nightstand_A"
P = dict(name=NAME, variant="books", width=0.55, palette="ink", seed=4, flip=True, bud="marble")


def build(**overrides):
    return base.build(**{**P, **overrides})
