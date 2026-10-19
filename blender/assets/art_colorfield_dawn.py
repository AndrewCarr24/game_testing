"""Art: 'colorfield_dawn', soft colour-field canvas, 1.9 x 1.1 m, unframed canvas (primary_bedroom W wall over the bed).
picture_frame variant (art_collection.PIECES); hangs on a wall, origin on the wall plane, faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "Art_ColorfieldDawn"
P = dict(name=NAME, variant="colorfield_dawn")


def build(**overrides):
    return picture_frame.build(**{**P, **overrides})
