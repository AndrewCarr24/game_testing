"""Fireplace switch: the same plate with one upright bar on the rocker, a `switch` on signal "fire" (renamed per placement: {"signal": "fire_<room>"}), starting on.

Wall-mounted like ix_switch: origin at the plate's back centre, front -Y, place at z = 1.1."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_switch  # noqa: E402

importlib.reload(ix_switch)
common = ix_switch.common

NAME = "IX_SwitchFire"
P = dict(name=NAME, signal="fire", state=True, prompt="Light the fire", promptActive="Put out the fire",
         glyphs=[(0, 0.0, 0.0016, 0.012)])


def build(**overrides):
    return ix_switch.build(**{**P, **overrides})
