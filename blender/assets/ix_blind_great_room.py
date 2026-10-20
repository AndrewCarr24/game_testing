"""Roller blinds (see ix_blind). Great room west glass: four of its eleven 1.45 m bays per run (place two runs, either side of the breakable middle bays 4-6), 8.4 m high, linen greige."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_blind  # noqa: E402

importlib.reload(ix_blind)
common = ix_blind.common

NAME = "IX_BlindGreatRoom"
P = dict(name=NAME, bays=4, bay_w=16 / 11, top=8.4, fabric="linen")


def build(**overrides):
    return ix_blind.build(**{**P, **overrides})
