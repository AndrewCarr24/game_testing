"""Art: 'still_life', hard-edge painting, 0.8 x 1 m, unframed canvas (kitchen W wall, north of the opening).
picture_frame variant (art_collection.PIECES); hangs on a wall, origin on the wall plane, faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "Art_StillLife"
P = dict(name=NAME, variant="still_life")


def build(**overrides):
    return picture_frame.build(**{**P, **overrides})
