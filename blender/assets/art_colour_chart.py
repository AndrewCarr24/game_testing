"""Art: 'colour_chart', watercolour on paper, 1 x 1.3 m, white box frame (ugallery_n, east).
picture_frame variant (art_collection.PIECES); hangs on a wall, origin on the wall plane, faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "Art_ColourChart"
P = dict(name=NAME, variant="colour_chart")


def build(**overrides):
    return picture_frame.build(**{**P, **overrides})
