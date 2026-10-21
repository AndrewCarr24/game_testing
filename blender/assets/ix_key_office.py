"""Office key (see ix_key): a pickup, item "key_office"; it opens the office door (upper gallery, north)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_key  # noqa: E402

importlib.reload(ix_key)
common = ix_key.common

NAME = "IX_KeyOffice"
P = dict(name=NAME, item="key_office", label="Office key", metal="brass", fob=(0.20, 0.075, 0.03))


def build(**overrides):
    return ix_key.build(**{**P, **overrides})
