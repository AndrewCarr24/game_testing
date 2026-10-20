"""Roller blinds (see ix_blind). Primary bedroom north glass: eight 1.5 m bays, 3.8 m high, charcoal blackout."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_blind  # noqa: E402

importlib.reload(ix_blind)
common = ix_blind.common

NAME = "IX_BlindBedroom"
P = dict(name=NAME, bays=8, bay_w=1.5, top=3.8, fabric="blackout")


def build(**overrides):
    return ix_blind.build(**{**P, **overrides})
