"""Garage-door opener: a tall graphite plate with a big round steel push button in a blue lit
ring (lit while the door is open) under a small garage mark (a roof over three panels).
A `switch` on signal "garage_door", starting off (closed). Mounted by the house door at
opener height (1.5 m, out of children's reach), on the other side of the door from the
light switch.

Wall-mounted like ix_switch: origin at the plate's back centre, front -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_switch  # noqa: E402

importlib.reload(ix_switch)
common = ix_switch.common
ix_common = ix_switch.ix_common

NAME = "IX_SwitchGarage"
_ICON = ix_common.chevron(0, 0.048, up=True, size=0.014, bar=0.0016, spread=28) + [
    (0, z, 0.016, 0.0016) for z in (0.040, 0.0355, 0.031)]
P = dict(name=NAME, signal="garage_door", state=False, prompt="Open garage door", promptActive="Close garage door",
         plate_size=(0.080, 0.130, 0.008), part="button", rocker_size=(0.038, 0.038, 0.008),
         paddle=("M_Switch_Button_Steel", (0.42, 0.42, 0.43)), ring=0.0245,
         plate_marks=_ICON, marks=("M_Switch_Marks_Light", (0.55, 0.54, 0.52)),
         led=("M_Switch_Locator_Garage", (0.35, 0.62, 1.0), 2.5))


def build(**overrides):
    return ix_switch.build(**{**P, **overrides})
