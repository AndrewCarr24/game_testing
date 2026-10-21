"""Cellar key (see ix_key): a pickup, item "key_cellar"; it opens the wine room's climate cabinet."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_key  # noqa: E402

importlib.reload(ix_key)
common = ix_key.common

NAME = "IX_KeyCellar"
P = dict(name=NAME, item="key_cellar", label="Cellar key", metal="bronze", fob=(0.13, 0.012, 0.016), bow=(0.030, 0.026))


def build(**overrides):
    return ix_key.build(**{**P, **overrides})
