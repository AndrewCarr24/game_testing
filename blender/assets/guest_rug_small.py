"""Small guest-room rug for the reading corner: guest_rug at 2.2 x 1.7 m."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guest_rug  # noqa: E402

importlib.reload(guest_rug)
common = guest_rug.common

NAME = "GuestRugSmall"
P = dict(name=NAME, size=(2.4, 1.9), line_inset=0.12)


def build(**overrides):
    return guest_rug.build(**{**P, **overrides})
