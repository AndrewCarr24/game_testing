"""The carafe tray in pale oak (gym)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_tray_carafe as base  # noqa: E402

importlib.reload(base)

NAME = "DecorC_TrayCarafeOak"
P = dict(base.P, name=NAME, tray="oak")


def build(**overrides):
    return base.build(**{**P, **overrides})
