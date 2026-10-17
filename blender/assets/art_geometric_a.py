"""Hall artwork: picture_frame variant 'geometric_a'."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "Art_GeometricA"
P = dict(name=NAME, variant="geometric_a")


def build(**overrides):
    return picture_frame.build(**{**P, **overrides})
