"""Art: 'calligraphy', gestural ink / brush work, 1.1 x 0.85 m, white box frame (office S wall, east of the door).
picture_frame variant (art_collection.PIECES); hangs on a wall, origin on the wall plane, faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "Art_Calligraphy"
P = dict(name=NAME, variant="calligraphy")


def build(**overrides):
    return picture_frame.build(**{**P, **overrides})
