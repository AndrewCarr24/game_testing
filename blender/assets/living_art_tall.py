"""Tall portrait canvas for the great room's wall flanks (picture_frame, larger)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "LivingArtTall"
VARIANT = dict(size=(1.5, 2.3), border=0.12, art="geometric_a", rough=0.78)
P = dict(name=NAME, variant="living_tall")


def build(**overrides):
    picture_frame.VARIANTS["living_tall"] = VARIANT      # (picture_frame is reloaded by other art modules)
    return picture_frame.build(**{**P, **overrides})
