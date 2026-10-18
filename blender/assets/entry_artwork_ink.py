"""Powder-room painting: a 1.3 x 1.8 m ink-wash enso with a gold-leaf panel (entry_artwork,
style 'ink'). Origin: centre of the picture on the wall plane; faces -Y."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entry_artwork  # noqa: E402

importlib.reload(entry_artwork)
common = entry_artwork.common

NAME = "EntryArtworkInk"
P = dict(name=NAME, style="ink", size=(1.3, 1.8), tex="T_Entry_Art_Ink", seed=57, backer_inset=0.10)


def build(**overrides):
    return entry_artwork.build(**{**P, **overrides})
