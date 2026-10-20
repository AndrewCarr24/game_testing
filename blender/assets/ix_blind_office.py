"""Roller blinds (see ix_blind). Office north glass: eight 1.44 m bays, 3.8 m high, charcoal blackout (glare-free screens)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_blind  # noqa: E402

importlib.reload(ix_blind)
common = ix_blind.common

NAME = "IX_BlindOffice"
P = dict(name=NAME, bays=8, bay_w=11.5 / 8, top=3.8, fabric="blackout")


def build(**overrides):
    return ix_blind.build(**{**P, **overrides})
