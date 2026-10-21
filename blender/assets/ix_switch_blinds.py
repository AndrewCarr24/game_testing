"""Blinds switch: reads as a different control from the light switch across the room: a tall
bronze plate (the light switch is a small graphite square) with an ivory rocker between an
up and a down chevron printed on the plate, and a cool white locator LED (lit while the
blinds are down). A `switch` on signal "blinds" (renamed per room: {"signal": "blinds_<room>"}),
starting off (blinds up). Placed by the glass it drives, never beside the light switch.

Wall-mounted like ix_switch: origin at the plate's back centre, front -Y, place at z = 1.1."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_switch  # noqa: E402

importlib.reload(ix_switch)
common = ix_switch.common
ix_common = ix_switch.ix_common

NAME = "IX_SwitchBlinds"
P = dict(name=NAME, signal="blinds", state=False, prompt="Lower blinds", promptActive="Raise blinds",
         plate="bronze", plate_size=(0.074, 0.136, 0.008), rocker_size=(0.040, 0.060, 0.007),
         paddle=("M_Switch_Rocker_Ivory", (0.62, 0.58, 0.50)),
         plate_marks=ix_common.chevron(0, 0.047, up=True) + ix_common.chevron(0, -0.047, up=False),
         marks=("M_Switch_Marks_Dark", (0.02, 0.018, 0.016)),
         led=("M_Switch_Locator_Blinds", (0.55, 0.78, 1.0), 2.5), led_at=(0, -0.059))


def build(**overrides):
    return ix_switch.build(**{**P, **overrides})
