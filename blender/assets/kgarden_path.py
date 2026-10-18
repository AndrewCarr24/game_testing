"""Raked gravel path with a slim dark-metal edge on both sides (the kgarden_path_* assets
are thin wrappers). Long axis along X, origin the centre of the path on the lawn. The gravel
is 3.5 cm proud of the lawn and cut into cells of 1.5 m or less. Units are metres."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kgarden_common as kc  # noqa: E402

importlib.reload(kc)
outdoor = kc.outdoor

NAME = "KgardenPath"

P = dict(name=NAME, length=20.0, width=1.8, rise=0.035, edge=True)


def build(**overrides):
    p = {**P, **overrides}
    B = kc.Builder(p["name"])
    gravel = B.mat("Gravel", outdoor.gravel(), tile=2.0)
    metal = B.mat("Edge", outdoor.dark_metal())
    L, W, h = p["length"], p["width"], p["rise"]
    B.box(gravel, (0, 0, h / 2), (L, W, h), cell=kc.CELL, cell_on=("+z",), skip=("-z",))
    if p["edge"]:
        for sy in (-1, 1):
            B.box(metal, (0, sy * (W / 2 + 0.006), 0.03), (L, 0.012, 0.062), skip=("-z", "-x", "+x"))
    return B.finish()
