"""Art: 'sweep_terracotta', gestural ink / brush work, 1.3 x 1 m, unframed canvas (dining S wall, west segment).
picture_frame variant (art_collection.PIECES); hangs on a wall, origin on the wall plane, faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "Art_SweepTerracotta"
P = dict(name=NAME, variant="sweep_terracotta")


def build(**overrides):
    return picture_frame.build(**{**P, **overrides})
