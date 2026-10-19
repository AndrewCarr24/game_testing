"""Art: 'blocks_umber', painterly block painting, 2 x 1.6 m, black floater frame (great_room E wall, north of the fireplace).
picture_frame variant (art_collection.PIECES); hangs on a wall, origin on the wall plane, faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "Art_BlocksUmber"
P = dict(name=NAME, variant="blocks_umber")


def build(**overrides):
    return picture_frame.build(**{**P, **overrides})
