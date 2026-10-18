"""Full-length mirror (0.8 x 2.2 m): entry_mirror with shape='tall'."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entry_mirror  # noqa: E402

importlib.reload(entry_mirror)
common = entry_mirror.common

NAME = "EntryMirrorTall"
P = dict(name=NAME, shape="tall")


def build(**overrides):
    return entry_mirror.build(**{**P, **overrides})
