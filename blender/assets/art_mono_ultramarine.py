"""Art: 'mono_ultramarine', monochrome painting, 1.4 x 1.8 m, unframed canvas (great_room N wall, east of the dining opening).
picture_frame variant (art_collection.PIECES); hangs on a wall, origin on the wall plane, faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "Art_MonoUltramarine"
P = dict(name=NAME, variant="mono_ultramarine")


def build(**overrides):
    return picture_frame.build(**{**P, **overrides})
