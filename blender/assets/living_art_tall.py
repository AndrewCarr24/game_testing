"""Art: 'kline_bars', gestural ink / brush work, 1.5 x 2.3 m, unframed canvas (great_room S wall, west).
picture_frame variant (art_collection.PIECES); hangs on a wall, origin on the wall plane, faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import picture_frame  # noqa: E402

importlib.reload(picture_frame)
common = picture_frame.common

NAME = "LivingArtTall"
P = dict(name=NAME, variant="kline_bars")


def build(**overrides):
    return picture_frame.build(**{**P, **overrides})
