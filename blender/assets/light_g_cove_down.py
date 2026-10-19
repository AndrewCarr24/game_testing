"""Cove ledge turned over: the lip hangs down and hides an LED aimed down the wall (a
valance wash). See light_g_cove."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import light_g_cove  # noqa: E402

importlib.reload(light_g_cove)
common = light_g_cove.common

NAME = "LightGCoveDown"
P = dict(name=NAME, up=False)


def build(**overrides):
    return light_g_cove.build(**{**P, **overrides})
