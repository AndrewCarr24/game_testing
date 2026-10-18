"""Primary bath north wall: pale book-matched marble slabs, 9.7 m (place on the wall face, rot 0)."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bath_slab_wall  # noqa: E402

importlib.reload(bath_slab_wall)

NAME = "BathWallNorth"
P = dict(name=NAME, tone="light", runs=[(-4.85, 4.85, 0.0, 3.8)])


def build(**overrides):
    return bath_slab_wall.build(**{**P, **overrides})


if __name__ == "__main__":
    root, parts = build()
    print(NAME, len(parts))
