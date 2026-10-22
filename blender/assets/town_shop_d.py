"""town_shop variant "d" (see town_shop.py)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import town_shop  # noqa: E402

importlib.reload(town_shop)


def build(**overrides):
    return town_shop.build(variant="d", **overrides)
