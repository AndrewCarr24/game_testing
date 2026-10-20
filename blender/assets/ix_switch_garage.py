"""Garage-door switch: the same plate with three bars on the rocker (a panel door), a `switch` on signal "garage_door", starting off (closed).

Wall-mounted like ix_switch: origin at the plate's back centre, front -Y, place at z = 1.1."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_switch  # noqa: E402

importlib.reload(ix_switch)
common = ix_switch.common

NAME = "IX_SwitchGarage"
P = dict(name=NAME, signal="garage_door", state=False, prompt="Open garage door", promptActive="Close garage door",
         glyphs=[(0, 0.0, 0.016, 0.0016), (0, 0.006, 0.016, 0.0016), (0, -0.006, 0.016, 0.0016)])


def build(**overrides):
    return ix_switch.build(**{**P, **overrides})
