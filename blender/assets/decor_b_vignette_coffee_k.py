"""decor_b_vignette_coffee in the kitchen's palette (white pages, linen / charcoal / cognac
covers, a white candle, coffee-dark soil), for the lounge nook's coffee table."""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import decor_b_vignette_coffee as base  # noqa: E402

importlib.reload(base)

NAME = "DecorBVignetteCoffeeK"
P = dict(base.P, name=NAME, seed=8, pages="paper_white", covers=("linen_oat", "wool_charcoal", "leather"),
         sculpture="sphere", soil="coffee", holder="ceramic_white", wax="paper_white", bands=("paper_white",))


def build(**overrides):
    return base.build(**{**P, **overrides})
