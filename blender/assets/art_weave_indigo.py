"""Art: 'weave_indigo', woven textile, 1.4 x 1.8 m, unframed canvas (great_room N wall, west of the dining opening).
picture_frame variant (art_collection.PIECES); hangs on a wall, origin on the wall plane, faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "Art_WeaveIndigo"
P = dict(name=NAME, variant="weave_indigo")


def build(**overrides):
    return picture_frame.build(**{**P, **overrides})
