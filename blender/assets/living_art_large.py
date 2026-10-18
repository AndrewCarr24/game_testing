"""Large gallery-scale canvas for the great room: picture_frame with extra sizes."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "LivingArtLarge"
VARIANT = dict(size=(2.6, 1.7), border=0.12, art="colorfield_b", rough=0.8)
P = dict(name=NAME, variant="living_large")


def build(**overrides):
    picture_frame.VARIANTS["living_large"] = VARIANT      # (picture_frame is reloaded by other art modules)
    return picture_frame.build(**{**P, **overrides})
