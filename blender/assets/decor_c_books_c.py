"""Four medium books with stacked charcoal pebbles (decor_c_books, another seed)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_books as base  # noqa: E402

importlib.reload(base)

NAME = "DecorC_BooksC"
P = dict(base.P, name=NAME, seed=12, n=4, top="pebbles", top_mat="charcoal", size="medium")


def build(**overrides):
    return base.build(**{**P, **overrides})
