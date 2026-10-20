"""Blinds switch: the same plate with two bars on the rocker (up / down), a `switch` on signal "blinds" (renamed per room: {"signal": "blinds_<room>"}), starting off (blinds up).

Wall-mounted like ix_switch: origin at the plate's back centre, front -Y, place at z = 1.1."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_switch  # noqa: E402

importlib.reload(ix_switch)
common = ix_switch.common

NAME = "IX_SwitchBlinds"
P = dict(name=NAME, signal="blinds", state=False, prompt="Lower blinds", promptActive="Raise blinds",
         glyphs=[(0, 0.012, 0.010, 0.0016), (0, -0.012, 0.010, 0.0016)])


def build(**overrides):
    return ix_switch.build(**{**P, **overrides})
