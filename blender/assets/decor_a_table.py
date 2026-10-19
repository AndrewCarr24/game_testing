"""Styling for table tops (origin = the centre of the top surface, placed at its height; front -y).
Variants (`variant`), each for a surface in the entry wing / great room / den:

  round_entry     entry_round_table (r 0.75) round its centre flowers: art books with a stone
                  cairn, a black bowl with keys, a lidded walnut box
  round_powder    the powder room's round table round its blossom: books with a candle, a bronze dish
  coffee_round_a  living_coffee_round (r 0.56) with the vase at (0, 0.15): books + sphere, a bowl
  coffee_round_c  living_coffee_round, empty: marble tray with carafe and glasses, books + candle
  coffee_rect     coffee_table (1.05 x 0.58): fanned magazines, books + bowl, a coffee cup
  coffee_rect_b   coffee_table: an open book with reading glasses, a coffee cup, a small plant
  ottoman         living_ottoman (1.15 sq, crown 0.44): walnut tray with books and a candle
  ottoman_den     the den ottoman round its vase: a tray with a box and candle, a book stack
  side_cup        living_side_table under its lamp: coffee cup on a saucer at the edge
  side_glass      living_side_table under its lamp: a tumbler and two small books
  side_plant      living_side_table without a lamp: a small plant on two books
  credenza        the den media wall's credenza (4.9 m, origin at its centre): low groups at both ends

No colliders (everything is small).
"""
import importlib
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decor_a_kit as kit  # noqa: E402
from decor_a_kit import at  # noqa: E402

importlib.reload(kit)
common = kit.common

NAME = "DecorATable"

P = dict(name=NAME, variant="round_entry", seed=5, palette="neutral", flat_books=False, ceramic="glaze",
         accent="charcoal", base="", base_z=0.0)


def round_entry(B, rnd, p):
    z = kit.stack(B, at(0.40, -0.22, 0, 24), rnd, n=3, size=(0.38, 0.30), palette=p["palette"])
    kit.cairn(B, at(0.40, -0.23, z), rnd, keys=("charcoal", "stoneware", "charcoal"), r=0.06)
    kit.bowl(B, at(-0.38, -0.30, 0), "charcoal", r=0.12, h=0.05, foot=0.55)
    kit.keys(B, at(-0.37, -0.31, 0.012, 30))
    kit.walnut_box(B, at(0.18, 0.47, 0, -28), w=0.22, d=0.14, h=0.075)


def round_powder(B, rnd, p):
    z = kit.stack(B, at(0.36, -0.24, 0, 28), rnd, n=2, size=(0.32, 0.25), palette=p["palette"])
    kit.candle(B, at(0.36, -0.25, z), r=0.042, h=0.095, holder="stoneware")
    kit.bowl(B, at(-0.40, -0.20, 0), "bronze", r=0.11, h=0.035, foot=0.6, wall=0.003)


def coffee_round_a(B, rnd, p):
    z = kit.stack(B, at(-0.20, -0.20, 0, -18), rnd, n=3, size=(0.32, 0.25), palette=p["palette"])
    kit.sphere_on_block(B, at(-0.20, -0.21, z, 10), r=0.04, block=0.055)
    kit.bowl(B, at(0.25, -0.10, 0), p["accent"], r=0.13, h=0.055, foot=0.5)


def coffee_round_c(B, rnd, p):
    kit.tray(B, at(-0.14, 0.15, 0, 18), "marble", w=0.40, d=0.27, h=0.022)
    M = at(-0.14, 0.15, 0.006, 18)
    kit.carafe(B, M @ at(-0.09, 0.03, 0), h=0.24, r=0.055)
    kit.tumbler(B, M @ at(0.06, -0.05, 0))
    kit.tumbler(B, M @ at(0.11, 0.05, 0))
    z = kit.stack(B, at(0.20, -0.20, 0, 12), rnd, n=3, size=(0.30, 0.24), palette=p["palette"])
    kit.candle(B, at(0.21, -0.21, z), r=0.038, h=0.085, holder=p["accent"])


def coffee_rect(B, rnd, p):
    kit.fanned(B, at(-0.34, -0.06, 0, -12), rnd, n=3, palette="all")
    z = kit.stack(B, at(0.20, 0.07, 0, 6), rnd, n=2, size=(0.30, 0.24), palette=p["palette"])
    kit.bowl(B, at(0.21, 0.07, z), p["accent"], r=0.08, h=0.04, foot=0.55)
    kit.cup(B, at(0.33, -0.16, 0, 40), key=p["ceramic"])


def coffee_rect_b(B, rnd, p):
    kit.open_book(B, at(-0.18, 0.02, 0, 8), rnd, palette=p["palette"])
    kit.glasses(B, at(-0.12, -0.04, 0.016, -20))
    kit.cup(B, at(0.12, -0.15, 0, 120), key=p["ceramic"])
    kit.small_plant(B, at(0.34, 0.09, 0), rnd, pot=p["accent"], leaves=14, spread=0.14)


def ottoman(B, rnd, p):
    M = at(0.0, 0.0, 0, 8)
    kit.tray(B, M, "walnut", w=0.62, d=0.42, h=0.035, rim=0.01)
    z = kit.stack(B, M @ at(-0.12, 0.02, 0.006, -4), rnd, n=2, size=(0.32, 0.25), palette=p["palette"])
    kit.candle(B, M @ at(0.17, 0.08, 0.006), r=0.042, h=0.09, holder=p["accent"])
    kit.cairn(B, M @ at(-0.11, 0.02, 0.006 + z), rnd, keys=(p["accent"], p["ceramic"], p["accent"]), r=0.045)


def ottoman_den(B, rnd, p):
    M = at(0.30, 0.05, 0, 90)
    kit.tray(B, M, "walnut", w=0.40, d=0.27, h=0.03)
    kit.walnut_box(B, M @ at(-0.07, 0.0, 0.006, 4), w=0.16, d=0.11, h=0.06, key="oak")
    kit.candle(B, M @ at(0.11, 0.01, 0.006), r=0.036, h=0.08, holder=p["accent"])
    kit.stack(B, at(-0.32, -0.24, 0, -14), rnd, n=3, size=(0.31, 0.24), palette=p["palette"], flat=p["flat_books"])


def side_cup(B, rnd, p):
    kit.cup(B, at(0.13, -0.13, 0, -30), key=p["ceramic"])


def side_glass(B, rnd, p):
    # books tangential to the lamp's ceramic body (r 0.09), clear of it and inside the top (r 0.27)
    kit.stack(B, at(-0.13, -0.13, 0, 45), rnd, n=2, size=(0.17, 0.12), thick=(0.018, 0.03), palette=p["palette"],
              flat=p["flat_books"], shrink=0.95)
    kit.tumbler(B, at(0.15, -0.08, 0), r=0.036, h=0.085)


def side_plant(B, rnd, p):
    z = kit.stack(B, at(-0.02, -0.03, 0, 20), rnd, n=2, size=(0.24, 0.18), thick=(0.02, 0.035), palette=p["palette"],
                  flat=p["flat_books"])
    kit.small_plant(B, at(-0.01, -0.03, z), rnd, pot=p["ceramic"], pot_r=0.06, pot_h=0.085, leaves=16, spread=0.15)


def credenza(B, rnd, p):
    for side, x in ((-1, -1.95), (1, 1.95)):
        if side < 0:
            z = kit.stack(B, at(x - 0.08, 0.0, 0, 4), rnd, n=3, size=(0.34, 0.27), palette=p["palette"],
                          flat=p["flat_books"])
            kit.bowl(B, at(x + 0.28, 0.02, 0), p["accent"], r=0.12, h=0.06)
        else:
            kit.cairn(B, at(x - 0.25, 0.0, 0), rnd, keys=(p["accent"], p["ceramic"], p["accent"]), r=0.06)
            kit.vase(B, at(x + 0.05, 0.02, 0), p["ceramic"], "jar", h=0.24, r=0.085)
            kit.vase(B, at(x + 0.22, -0.04, 0), p["accent"], "bud", h=0.16, r=0.05)


RECIPES = {f.__name__: f for f in (round_entry, round_powder, coffee_round_a, coffee_round_c, coffee_rect, coffee_rect_b,
                                   ottoman, ottoman_den, side_cup, side_glass, side_plant, credenza)}


def build(**overrides):
    p = {**P, **overrides}
    rnd = random.Random(p["seed"])
    B = kit.Builder(p["name"])
    RECIPES[p["variant"]](B, rnd, p)
    if p["base"]:
        kit.with_base(B, p["base"], at(0, 0, -p["base_z"]))
    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
