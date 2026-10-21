"""Locker key (see ix_key): a pickup, item "key_locker"; it opens the steel locker in the garage."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_key  # noqa: E402

importlib.reload(ix_key)
common = ix_key.common

NAME = "IX_KeyLocker"
P = dict(name=NAME, item="key_locker", label="Locker key", metal="steel", fob=(0.55, 0.12, 0.02), blade=0.030, bits=(0.004, 0.006, 0.003))


def build(**overrides):
    return ix_key.build(**{**P, **overrides})
