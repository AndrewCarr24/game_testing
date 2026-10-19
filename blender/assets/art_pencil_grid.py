"""Art: 'pencil_grid', pencil-grid painting, 1.1 x 1.1 m, unframed canvas (great_room S wall, beside the tall canvas).
picture_frame variant (art_collection.PIECES); hangs on a wall, origin on the wall plane, faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "Art_PencilGrid"
P = dict(name=NAME, variant="pencil_grid")


def build(**overrides):
    return picture_frame.build(**{**P, **overrides})
