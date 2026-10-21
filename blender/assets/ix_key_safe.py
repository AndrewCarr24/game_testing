"""Safe key (see ix_key): a pickup, item "key_safe"; it opens the office floor safe."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_key  # noqa: E402

importlib.reload(ix_key)
common = ix_key.common

NAME = "IX_KeySafe"
P = dict(name=NAME, item="key_safe", label="Safe key", metal="nickel", fob=(0.012, 0.012, 0.014), blade=0.044, double=True,
         bits=(0.003, 0.005, 0.0025, 0.0045, 0.0035))


def build(**overrides):
    return ix_key.build(**{**P, **overrides})
