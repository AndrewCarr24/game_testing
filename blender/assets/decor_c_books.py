"""A stack of art books lying flat (spine-atlas covers, largest at the bottom), optionally
with an object on top: a bronze ring on a walnut block, a split sphere, pebbles, a bronze
dish, a small bowl. `seed` changes sizes, colours and turns; decor_c_books_b/_c wrap it.
Origin: centre of the underside."""
import importlib
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_c_kit as K  # noqa: E402

importlib.reload(K)

NAME = "DecorC_Books"
P = dict(name=NAME, seed=1, n=3, top="ring", top_mat="bronze", size="large", turn=4.0)

SIZES = {"large": dict(w=(0.25, 0.34), d=(0.29, 0.37), t=(0.024, 0.048)),
         "medium": dict(w=(0.19, 0.25), d=(0.23, 0.29), t=(0.018, 0.036))}


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rnd = random.Random(p["seed"])
    col, root, k = K.new_asset(n)
    z, (tw, td, _) = K.book_stack(k, K.T(), rnd, n=p["n"], turn=p["turn"], **SIZES[p["size"]])
    top = p["top"]
    at = K.T(rnd.uniform(-0.03, 0.03), rnd.uniform(-0.03, 0.03), z, rz=rnd.uniform(-20, 20))
    if top in ("ring", "sphere", "pebbles"):
        K.sculpture(k, at, top, mat=p["top_mat"])
    elif top == "dish":
        K.candle_dish(k, at, p["top_mat"])
    elif top == "bowl":
        K.bowl(k, at, p["top_mat"], r=0.07, h=0.045, foot=0.5)
    elif top == "glasses":
        K.reading_glasses(k, at)
    return K.done(k, n, col, root)


if __name__ == "__main__":
    build()
