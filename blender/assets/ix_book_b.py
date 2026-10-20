"""Hardback book, oxblood cloth (see ix_book): a throwable lure."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_book  # noqa: E402

importlib.reload(ix_book)
common = ix_book.common

NAME = "IX_BookB"
P = dict(name=NAME, size=(0.215, 0.145, 0.026), cloth="M_Book_Cloth_Oxblood", color=(0.16, 0.025, 0.02))


def build(**overrides):
    return ix_book.build(**{**P, **overrides})
