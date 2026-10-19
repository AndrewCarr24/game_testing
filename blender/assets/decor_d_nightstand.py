"""Bedside vignette for a nightstand whose lamp stands at its centre (origin = the lamp's
foot, on the top; the nightstand's width runs along X, front -Y). Either side of the lamp
base, under the shade: variant "books" = two novels with folded reading glasses on top
and a bud vase with a cut olive stem opposite; variant "carafe" = a water carafe with its tumbler on a small
round tray and two books opposite. `width` = the nightstand top, `palette` the room's.
Wrappers: decor_d_nightstand_a/_b (primary bedroom), _guest_a/_guest_b (guest room)."""
import importlib
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import decor_d_kit as kit  # noqa: E402

importlib.reload(kit)

NAME = "DecorD_Nightstand"
P = dict(name=NAME, variant="books", width=0.55, palette="ink", seed=4, flip=False, bud=None)

NOVELS = [(0.155, 0.235), (0.145, 0.22), (0.16, 0.24), (0.135, 0.205)]


def build(**overrides):
    p = {**P, **overrides}
    rng = random.Random(p["seed"])
    pal = kit.PALETTES[p["palette"]]
    B = kit.Builder(p["name"])
    s = -1 if p["flip"] else 1
    x = s * min(0.18, p["width"] / 2 - 0.085)        # centre of each side's group
    if p["variant"] == "books":
        z = kit.book_stack(B, kit.at(x, 0.0, 0.0, rng.uniform(-4, 4)), rng, 2, pal["novels"], sizes=NOVELS[:2],
                           thick=(0.022, 0.034), spin=3, spines="side" if s > 0 else "outside", fixed=True)
        kit.glasses(B, kit.at(x + 0.005, -0.03, z, -12 + rng.uniform(-5, 5)), pal["frame"])
        h = kit.vessel(B, kit.at(-x, 0.04, 0.0), p["bud"] or pal["vessels"][0], "bud", h=0.15, r=0.042, segs=14)
        # the lamp shade (r 0.178) starts 0.36 above the top: the stem leans out from under it
        kit.stem_sprig(B, kit.at(-x, 0.04, h), rng, h=0.25, leaves=9, lean=24.0, azim=0.0 if -x > 0 else 180.0)
    else:
        b = kit.round_tray(B, kit.at(-x, 0.0, 0.0), pal["metal"], r=0.075, h=0.014, wall=0.004, base=0.004)
        kit.carafe(B, kit.at(-x, 0.0, b))
        kit.book_stack(B, kit.at(x, 0.01, 0.0, rng.uniform(-4, 4)), rng, 2, pal["novels"][::-1], sizes=NOVELS[2:],
                       thick=(0.02, 0.03), spin=3, spines="outside" if s > 0 else "side", fixed=True)
    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    print(NAME, kit.common.triangle_count(parts))
