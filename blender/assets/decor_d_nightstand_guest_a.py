"""Guest room nightstand vignette (books, glasses, bud vase): decor_d_nightstand, sage palette."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_d_nightstand as base  # noqa: E402

importlib.reload(base)

NAME = "DecorD_Nightstand_Guest_A"
P = dict(name=NAME, variant="books", width=0.50, palette="sage", seed=21, flip=True)


def build(**overrides):
    return base.build(**{**P, **overrides})
