"""Styling for a living_console (2.3 x 0.42 m walnut console, top 0.82 m, open shelf at 0.255 m):
a composed vignette on the top (books, ceramics, a focal object, odd groups of varied height)
and a few large books / a box on the lower shelf. Placed at the console's own position and
rotation (origin = the console's floor centre, front -y). Variants (`variant`):

  a      ceramics pair left, a book stack with a bronze sphere, a walnut bowl right
  b      books + stone cairn left, a low black bowl, a ceramic trio right
  c      tray with carafe and glasses left, books + candle, a tall vase right
  d      a bronze ring on its stone, books, two vases, a lidded box
  south  for the console that already carries a vase at its right end (x +0.7)
  sofa   behind the sofa, between its two lamps (x -0.45..0.45 only)
  bar    den bar: decanter and tumblers on a tray (a vase already stands at x -0.6)

Every part is small: no colliders.
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

NAME = "DecorAConsole"

P = dict(name=NAME, variant="a", seed=11, top=0.82, shelf=0.255, palette="neutral", flat_books=False,
         ceramic="glaze", accent="charcoal", shelf_items=True, base="")


def _shelf(B, rnd, p, xs=(-0.62, 0.48), box_on=1):
    z = p["shelf"]
    for i, x in enumerate(xs):
        top = kit.stack(B, at(x, 0.0, z, rnd.uniform(-3, 3)), rnd, n=rnd.choice((2, 3)), size=(0.36, 0.28),
                        thick=(0.03, 0.05), palette=p["palette"], flat=p["flat_books"], jitter=2.5)
        if i == box_on:
            kit.walnut_box(B, at(x + 0.02, -0.01, z + top, 8), w=0.2, d=0.13, h=0.07)


def recipe_a(B, rnd, p):
    t, cer, acc = p["top"], p["ceramic"], p["accent"]
    kit.vase(B, at(-0.8, 0.04, t), acc, "bottle", h=0.50, r=0.095)
    kit.vase(B, at(-0.58, -0.04, t), cer, "ovoid", h=0.27, r=0.095)
    z = kit.stack(B, at(0.26, 0.0, t, -4), rnd, n=3, size=(0.38, 0.29), palette=p["palette"], flat=p["flat_books"])
    kit.sphere_on_block(B, at(0.28, -0.01, t + z, 12), r=0.045, block=0.06)
    kit.bowl(B, at(0.80, 0.02, t), acc, r=0.17, h=0.07)


def recipe_b(B, rnd, p):
    t, cer, acc = p["top"], p["ceramic"], p["accent"]
    z = kit.stack(B, at(-0.68, 0.0, t, 5), rnd, n=2, size=(0.32, 0.25), palette=p["palette"], flat=p["flat_books"])
    kit.cairn(B, at(-0.66, -0.01, t + z), rnd, keys=(acc, cer, acc), r=0.055)
    kit.bowl(B, at(0.02, 0.0, t), acc, r=0.17, h=0.06, foot=0.5)
    kit.vase(B, at(0.56, 0.05, t), cer, "bottle", h=0.38, r=0.075)
    kit.vase(B, at(0.74, -0.03, t), acc, "jar", h=0.22, r=0.08)
    kit.vase(B, at(0.88, 0.07, t), cer, "bud", h=0.16, r=0.05)


def recipe_c(B, rnd, p):
    t, cer, acc = p["top"], p["ceramic"], p["accent"]
    kit.tray(B, at(-0.6, 0.0, t, 0), "marble", w=0.42, d=0.28, h=0.025)
    kit.carafe(B, at(-0.7, 0.02, t + 0.006))
    kit.tumbler(B, at(-0.53, -0.05, t + 0.006))
    kit.tumbler(B, at(-0.48, 0.06, t + 0.006))
    z = kit.stack(B, at(0.18, 0.0, t, 3), rnd, n=3, size=(0.3, 0.24), palette=p["palette"], flat=p["flat_books"])
    kit.candle(B, at(0.2, -0.02, t + z), r=0.04, h=0.09, holder=acc)
    kit.vase(B, at(0.78, 0.03, t), cer, "flask", h=0.42, r=0.08)


def recipe_d(B, rnd, p):
    t, cer, acc = p["top"], p["ceramic"], p["accent"]
    kit.vase(B, at(-0.86, 0.03, t), cer, "cylinder", h=0.34, r=0.06)
    kit.vase(B, at(-0.7, -0.03, t), acc, "ovoid", h=0.2, r=0.075)
    z = kit.stack(B, at(-0.12, 0.0, t, -3), rnd, n=2, size=(0.36, 0.28), palette=p["palette"], flat=p["flat_books"])
    kit.ring_sculpture(B, at(-0.12, 0.0, t + z, 4), R=0.085, key="bronze")
    kit.walnut_box(B, at(0.62, -0.02, t, -6), w=0.24, d=0.15, h=0.08)


def recipe_south(B, rnd, p):
    t, cer, acc = p["top"], p["ceramic"], p["accent"]
    z = kit.stack(B, at(-0.62, 0.0, t, 4), rnd, n=3, size=(0.34, 0.26), palette=p["palette"], flat=p["flat_books"])
    kit.cairn(B, at(-0.62, -0.01, t + z), rnd, keys=(acc, cer, acc), r=0.05)
    kit.vase(B, at(0.02, 0.04, t), acc, "bottle", h=0.34, r=0.07)
    kit.vase(B, at(0.18, -0.03, t), cer, "jar", h=0.18, r=0.07)


def recipe_sofa(B, rnd, p):
    t, cer, acc = p["top"], p["ceramic"], p["accent"]
    z = kit.stack(B, at(-0.2, 0.0, t, -3), rnd, n=3, size=(0.3, 0.24), palette=p["palette"], flat=p["flat_books"])
    kit.candle(B, at(-0.2, 0.0, t + z), r=0.038, h=0.085, holder=acc)
    kit.bowl(B, at(0.2, 0.0, t), "walnut", r=0.13, h=0.06)


def recipe_bar(B, rnd, p):
    t, acc = p["top"], p["accent"]
    kit.tray(B, at(0.42, 0.0, t, 0), "leather", w=0.46, d=0.3, h=0.03)
    kit.decanter(B, at(0.32, 0.03, t + 0.006))
    kit.decanter(B, at(0.48, 0.06, t + 0.006), h=0.18, r=0.05)
    kit.tumbler(B, at(0.52, -0.07, t + 0.006), r=0.04, h=0.085)
    kit.tumbler(B, at(0.6, 0.0, t + 0.006), r=0.04, h=0.085)
    kit.bowl(B, at(0.92, 0.0, t), "bronze", r=0.09, h=0.1, foot=0.7, wall=0.004)      # ice bucket
    z = kit.stack(B, at(-0.12, 0.0, t, 5), rnd, n=3, size=(0.3, 0.23), palette=p["palette"], flat=p["flat_books"])
    kit.candle(B, at(-0.1, 0.0, t + z), r=0.036, h=0.08, holder=acc)


RECIPES = dict(a=recipe_a, b=recipe_b, c=recipe_c, d=recipe_d, south=recipe_south, sofa=recipe_sofa, bar=recipe_bar)


def build(**overrides):
    p = {**P, **overrides}
    rnd = random.Random(p["seed"])
    B = kit.Builder(p["name"])
    RECIPES[p["variant"]](B, rnd, p)
    if p["shelf_items"]:
        _shelf(B, rnd, p, box_on=0 if p["variant"] in ("b", "c") else 1)
    if p["base"]:
        kit.with_base(B, p["base"])
    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
