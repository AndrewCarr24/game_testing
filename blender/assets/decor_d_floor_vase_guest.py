"""Guest room: a terracotta floor vase of olive branches flanking the dresser (decor_d_floor_vase)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_d_floor_vase as base  # noqa: E402

importlib.reload(base)

NAME = "DecorD_FloorVase_Guest"
P = dict(name=NAME, seed=9, height=0.52, radius=0.155, glaze="terracotta", spray=0.8, leaves=180)


def build(**overrides):
    return base.build(**{**P, **overrides})
