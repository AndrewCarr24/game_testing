"""Art: 'linen_check', woven textile, 0.85 x 1.1 m, white box frame (kitchen E wall, north of the opening).
picture_frame variant (art_collection.PIECES); hangs on a wall, origin on the wall plane, faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "Art_LinenCheck"
P = dict(name=NAME, variant="linen_check")


def build(**overrides):
    return picture_frame.build(**{**P, **overrides})
