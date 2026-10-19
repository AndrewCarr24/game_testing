"""Art: 'cyanotype_umbel', cyanotype, 0.6 x 0.8 m, wood frame (office W wall over the credenza, north of the pair).
picture_frame variant (art_collection.PIECES); hangs on a wall, origin on the wall plane, faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "Art_CyanotypeUmbel"
P = dict(name=NAME, variant="cyanotype_umbel")


def build(**overrides):
    return picture_frame.build(**{**P, **overrides})
