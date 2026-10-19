"""Art: 'target', hard-edge painting, 1.2 x 1.2 m, unframed canvas (gym W wall).
picture_frame variant (art_collection.PIECES); hangs on a wall, origin on the wall plane, faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "Art_Target"
P = dict(name=NAME, variant="target")


def build(**overrides):
    return picture_frame.build(**{**P, **overrides})
