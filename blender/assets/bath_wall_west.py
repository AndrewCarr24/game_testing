"""Primary bath west wall, pale marble slabs with a gap for the door at y 1.2..2.3 (rot 90)."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bath_slab_wall  # noqa: E402

importlib.reload(bath_slab_wall)

NAME = "BathWallWest"
P = dict(name=NAME, tone="light", runs=[(-4.6, 1.2, 0.0, 3.8), (2.3, 4.6, 0.0, 3.8), (1.2, 2.3, 2.5, 3.8)])


def build(**overrides):
    return bath_slab_wall.build(**{**P, **overrides})


if __name__ == "__main__":
    root, parts = build()
    print(NAME, len(parts))
