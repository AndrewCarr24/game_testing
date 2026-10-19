"""Three medium books with a bronze catch-all dish (decor_c_books, another seed)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_books as base  # noqa: E402

importlib.reload(base)

NAME = "DecorC_BooksD"
P = dict(base.P, name=NAME, seed=21, n=3, top="dish", size="medium")


def build(**overrides):
    return base.build(**{**P, **overrides})
