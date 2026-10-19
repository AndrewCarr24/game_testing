"""Two big art books with a bronze split sphere on top (decor_c_books, another seed)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_books as base  # noqa: E402

importlib.reload(base)

NAME = "DecorC_BooksB"
P = dict(base.P, name=NAME, seed=7, n=2, top="sphere")


def build(**overrides):
    return base.build(**{**P, **overrides})
