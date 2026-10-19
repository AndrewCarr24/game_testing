"""Art: 'shoreline', photograph, 1.6 x 1 m, black-metal frame (primary_bath S wall over the daybed).
picture_frame variant (art_collection.PIECES); hangs on a wall, origin on the wall plane, faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "Art_Shoreline"
P = dict(name=NAME, variant="shoreline")


def build(**overrides):
    return picture_frame.build(**{**P, **overrides})
