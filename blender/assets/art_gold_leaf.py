"""Art: 'gold_leaf', gold-leaf panel, 0.7 x 0.7 m, black floater frame (powder S wall over the bench).
picture_frame variant (art_collection.PIECES); hangs on a wall, origin on the wall plane, faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "Art_GoldLeaf"
P = dict(name=NAME, variant="gold_leaf")


def build(**overrides):
    return picture_frame.build(**{**P, **overrides})
