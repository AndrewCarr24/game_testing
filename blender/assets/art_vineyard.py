"""Art: 'vineyard', photograph, 2.4 x 1.5 m, black-metal frame (wine_room S wall over the leather nook).
picture_frame variant (art_collection.PIECES); hangs on a wall, origin on the wall plane, faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "Art_Vineyard"
P = dict(name=NAME, variant="vineyard")


def build(**overrides):
    return picture_frame.build(**{**P, **overrides})
