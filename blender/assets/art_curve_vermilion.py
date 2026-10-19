"""Art: 'curve_vermilion', hard-edge painting, 2 x 1.6 m, unframed canvas (great_room E wall, south of the fireplace).
picture_frame variant (art_collection.PIECES); hangs on a wall, origin on the wall plane, faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "Art_CurveVermilion"
P = dict(name=NAME, variant="curve_vermilion")


def build(**overrides):
    return picture_frame.build(**{**P, **overrides})
