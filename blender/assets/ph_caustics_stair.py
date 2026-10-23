"""The secret stair's east wall, opposite the pool's glass end: the cold blue-green light that comes
through the water and the window, moving (ph_caustics with a stair's size and colour)."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ph_caustics  # noqa: E402

importlib.reload(ph_caustics)

NAME = "PHCausticsStair"
P = dict(name=NAME, size=(5.4, 2.6), scale=1.9, strength=0.42, color=(0.42, 0.82, 0.86), stretch=1.3, seed=3.0)


def build(**overrides):
    return ph_caustics.build(**{**P, **overrides})


if __name__ == "__main__":
    root, parts = build()
    print(root.name, len(parts))
