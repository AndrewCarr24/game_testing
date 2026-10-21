"""Steel security locker for the garage (gun-safe style, see ix_safe): 0.92 x 0.5 x 1.85 m,
graphite powder coat on a black plinth, one full-height door with a chrome bar handle, a
brass key cylinder and vent slots, three shelves inside. The door is an interactable
(`rotate`, "Open locker"); the level locks it ({"lock": "key_locker"}) and attaches what it
holds to `IX_GunLocker_Inside` (the middle shelf, ~1 m up)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ix_safe  # noqa: E402

importlib.reload(ix_safe)
common = ix_safe.common

NAME = "IX_GunLocker"
P = dict(name=NAME, style="locker", size=(0.92, 0.50, 1.85), wall=0.025, door_t=0.04, plinth=0.06,
         shelves=(0.52, 1.0, 1.45), inside_z=1.0, open_angle=-105,
         prompt="Open locker", prompt_active="Close locker",
         body=("M_Locker_Graphite", (0.040, 0.044, 0.047), 0.5, 0.6),
         lining=("M_Locker_Inner", (0.11, 0.115, 0.12), 0.7, 0.0))


def build(**overrides):
    return ix_safe.build(**{**P, **overrides})
