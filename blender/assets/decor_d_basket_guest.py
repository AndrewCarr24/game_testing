"""Guest reading corner: a woven seagrass-toned basket of rolled sage throws by the armchairs (decor_d_basket)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_d_basket as base  # noqa: E402

importlib.reload(base)

NAME = "DecorD_Basket_Guest"
P = dict(name=NAME, radius=0.22, height=0.36, weave="oak_light", cloths=("sage", "linen", "sage_light"), roll_r=0.065, roll_len=0.46, seed=4)


def build(**overrides):
    return base.build(**{**P, **overrides})
