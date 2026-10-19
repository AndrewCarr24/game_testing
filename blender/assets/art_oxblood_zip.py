"""Art: 'oxblood_zip', monochrome painting, 0.75 x 0.95 m, black floater frame (wine_room S wall, pair (west)).
picture_frame variant (art_collection.PIECES); hangs on a wall, origin on the wall plane, faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "Art_OxbloodZip"
P = dict(name=NAME, variant="oxblood_zip")


def build(**overrides):
    return picture_frame.build(**{**P, **overrides})
