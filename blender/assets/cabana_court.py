"""The bathhouse's garden court: a 14.6 x 11 m limestone slab 12 cm above the lawn, east of the
building (off the fire bath's door), carrying the outdoor kitchen and the dining pergola
(cabana_paving's slab at the court's size). Origin: the slab's centre at lawn level."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cabana_paving  # noqa: E402

importlib.reload(cabana_paving)

NAME = "CabanaCourt"
P = dict(name=NAME, size=(14.6, 11.0), height=0.12)


def build(**overrides):
    return cabana_paving.build(**{**P, **overrides})


if __name__ == "__main__":
    root, parts = build()
    print(root.name, len(parts))
