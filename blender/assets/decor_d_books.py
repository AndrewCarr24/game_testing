"""Stack of large cloth-bound art books lying flat, the top one carrying a small object
(balanced stones, a bronze ring or nothing). `seed` reshuffles sizes, cloth colours and
the slight turn of each book; `palette` picks the room's cloth colours (decor_d_kit).
Wrappers: decor_d_books_b / _c. Origin: centre of the bottom book's underside."""
import importlib
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import decor_d_kit as kit  # noqa: E402

importlib.reload(kit)

NAME = "DecorD_Books"
P = dict(name=NAME, seed=1, n=3, palette="ink", topper="pebbles", sizes=None)


def build(**overrides):
    p = {**P, **overrides}
    rng = random.Random(p["seed"])
    pal = kit.PALETTES[p["palette"]]
    B = kit.Builder(p["name"])
    z = kit.book_stack(B, kit.at(), rng, p["n"], pal["covers"], sizes=p["sizes"])
    if p["topper"] == "pebbles":
        kit.pebbles(B, kit.at(0.03, 0.0, z), pal["vessels"][1], rng=rng, r=0.045)
    elif p["topper"] == "ring":
        kit.ring_sculpture(B, kit.at(0.03, 0.0, z, 8), pal["metal"], R=0.055, r=0.009, base_key=pal["vessels"][0])
    elif p["topper"] == "bowl":
        kit.bowl(B, kit.at(0.02, 0.0, z), pal["vessels"][0], r=0.07, h=0.035)
    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    print(NAME, kit.common.triangle_count(parts))
