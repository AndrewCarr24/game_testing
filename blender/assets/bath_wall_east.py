"""Primary bath east feature wall: dark book-matched marble slabs, 9.2 m (rot -90)."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bath_slab_wall  # noqa: E402

importlib.reload(bath_slab_wall)

NAME = "BathWallEast"
P = dict(name=NAME, tone="dark", runs=[(-4.6, 4.6, 0.0, 3.8)])


def build(**overrides):
    return bath_slab_wall.build(**{**P, **overrides})


if __name__ == "__main__":
    root, parts = build()
    print(NAME, len(parts))
