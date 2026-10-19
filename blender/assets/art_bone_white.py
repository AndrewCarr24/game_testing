"""Art: 'bone_white', monochrome painting, 0.8 x 0.8 m, unframed canvas (guest_room N wall over the dresser).
picture_frame variant (art_collection.PIECES); hangs on a wall, origin on the wall plane, faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "Art_BoneWhite"
P = dict(name=NAME, variant="bone_white")


def build(**overrides):
    return picture_frame.build(**{**P, **overrides})
