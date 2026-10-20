"""Roller blinds (see ix_blind). Kitchen north glass: nine 1.56 m bays, 4.2 m high, linen greige."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_blind  # noqa: E402

importlib.reload(ix_blind)
common = ix_blind.common

NAME = "IX_BlindKitchen"
P = dict(name=NAME, bays=9, bay_w=14 / 9, top=4.2, fabric="linen")


def build(**overrides):
    return ix_blind.build(**{**P, **overrides})
