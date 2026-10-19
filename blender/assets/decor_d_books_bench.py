"""Primary bedroom bench at the foot of the bed: two large art books with balanced stones (decor_d_books)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_d_books as base  # noqa: E402

importlib.reload(base)

NAME = "DecorD_Books_Bench"
P = dict(name=NAME, seed=14, n=2, palette="ink", topper="pebbles", sizes=[(0.31, 0.39), (0.27, 0.33)])


def build(**overrides):
    return base.build(**{**P, **overrides})
