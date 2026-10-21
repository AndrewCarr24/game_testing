"""Fireplace switch: a round bronze plate with a black gas-valve knob (a grip bar across a
round skirt) that turns a quarter, a flame mark above it and an orange locator LED below,
so it can't be mistaken for a light switch. A `switch` on signal "fire" (renamed per
placement: {"signal": "fire_<room>"}), starting on. Mounted on the fireplace surround.

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
         plate="bronze", plate_shape="round", plate_size=(0.092, 0.092, 0.008),
         part="knob", rocker_size=(0.036, 0.036, 0.012),
         plate_marks=[(0, 0.033, 0.0062, 0.0062, 45)],
         marks=("M_Switch_Marks_Dark", (0.02, 0.018, 0.016)),
         led=("M_Switch_Locator_Fire", (1.0, 0.36, 0.08), 2.5), led_at=(0, -0.034))


def build(**overrides):
    return ix_switch.build(**{**P, **overrides})
