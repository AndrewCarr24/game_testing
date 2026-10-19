"""Art: 'wash_circles', watercolour on paper, 0.6 x 0.8 m, wood frame (guest_room S wall over the desk).
picture_frame variant (art_collection.PIECES); hangs on a wall, origin on the wall plane, faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "Art_WashCircles"
P = dict(name=NAME, variant="wash_circles")


def build(**overrides):
    return picture_frame.build(**{**P, **overrides})
