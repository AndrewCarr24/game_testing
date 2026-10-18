"""Second mudroom locker wall: the same lockers in a different arrangement (three
wider bays, the other coat colours), so the room does not repeat itself."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import garage_lockers  # noqa: E402

importlib.reload(garage_lockers)
common = garage_lockers.common

NAME = "GarageLockersB"
P = dict(name=NAME, bays=3, bay_w=1.25, palette=1, coats=(1, 0, 1))


def build(**overrides):
    return garage_lockers.build(**{**P, **overrides})
