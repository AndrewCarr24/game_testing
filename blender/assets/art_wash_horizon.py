"""Art: 'wash_horizon', watercolour on paper, 0.8 x 1 m, white box frame (primary_bedroom E wall, south of the bath door).
picture_frame variant (art_collection.PIECES); hangs on a wall, origin on the wall plane, faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "Art_WashHorizon"
P = dict(name=NAME, variant="wash_horizon")


def build(**overrides):
    return picture_frame.build(**{**P, **overrides})
