"""Raised kitchen-garden bed generator (the kgarden_bed_* assets are thin wrappers):
a 6 x 1.3 m planter, 0.5 m tall, teak or dark-metal sides with a flat rim, soil, and one of
several plantings (kind): "leaf" (rows of lettuce and red leaf), "brassica" (cabbages and
kale heads), "herb" (sage / rosemary / thyme mounds), "flower" (cut flowers), "beans"
(tall A-frame of dark-metal poles with climbing beans). Long axis along X; origin the
floor centre. Units are metres."""
import importlib
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kgarden_common as kc  # noqa: E402

importlib.reload(kc)
outdoor = kc.outdoor

NAME = "KgardenBed"

P = dict(
    name=NAME,
    kind="leaf",
    side="teak",          # "teak" | "metal"
    length=6.0,
    width=1.3,
    height=0.5,
    wall=0.07,
    soil_drop=0.07,
    seed=1,
)


def shell(B, key, L, W, t, H, zs, cell):
    """Bottomless ring: outer wall, rim, inner wall down to the soil (all counter-clockwise)."""
    ox, oy = L / 2, W / 2
    ix, iy = ox - t, oy - t
    outer = [(-ox, -oy), (ox, -oy), (ox, oy), (-ox, oy)]
    inner = [(-ix, -iy), (ix, -iy), (ix, iy), (-ix, iy)]
    for i in range(4):
        j = (i + 1) % 4
        (ax, ay), (bx, by) = outer[i], outer[j]
        B.quad(key, (ax, ay, 0), (bx, by, 0), (bx, by, H), (ax, ay, H), cell=cell)
        (cx, cy), (dx, dy) = inner[i], inner[j]
        B.quad(key, (ax, ay, H), (bx, by, H), (dx, dy, H), (cx, cy, H), cell=cell)
        B.quad(key, (cx, cy, H), (dx, dy, H), (dx, dy, zs), (cx, cy, zs), cell=cell)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rng = random.Random(p["seed"])
    B = kc.Builder(n)
    L, W, H, t = p["length"], p["width"], p["height"], p["wall"]
    zs = H - p["soil_drop"]
    if p["side"] == "teak":
        side = B.mat("Sides", outdoor.teak(), tile=0.5)
    else:
        side = B.mat("Sides", outdoor.dark_metal())
    soil = B.mat("Soil", outdoor.soil())
    shell(B, side, L, W, t, H, zs, cell=2.0)
    ix, iy = L / 2 - t, W / 2 - t
    B.quad(soil, (-ix, -iy, zs), (ix, -iy, zs), (ix, iy, zs), (-ix, iy, zs), cell=kc.CELL)
    kind = p["kind"]
    m = 0.32                                  # plants stop short of the bed ends
    x0, x1 = -ix + m, ix - m

    if kind == "leaf":
        green = B.mat("Lettuce", kc.leaf_light())
        red = B.mat("RedLeaf", kc.leaf_red())
        tex = B.mat("Foliage", outdoor.foliage(), tile=1.5)
        for k, (yy, key) in enumerate(((-0.36, green), (0.0, red), (0.36, tex))):
            B.ridge(key, (x0, yy, zs - 0.01), (x1, yy, zs - 0.01), 0.15 if key is not tex else 0.14,
                    0.17 if key is not tex else 0.14, 6, rng, lows=0.55, jitter=0.25)
    elif kind == "brassica":
        blue = B.mat("Kale", kc.leaf_blue())
        light = B.mat("Cabbage", kc.flat("Cabbage", (0.10, 0.19, 0.08)))
        for k, yy in enumerate((-0.3, 0.3)):
            for i in range(4):
                x = x0 + (x1 - x0) * (i + 0.5) / 4 + rng.uniform(-0.05, 0.05)
                big = (i + k) % 2 == 0
                B.dome(blue if big else light, (x, yy, zs - 0.01), rng.uniform(0.27, 0.31) if big else 0.24,
                       0.2 if big else 0.17, n=6, rng=rng, rot=rng.random())
    elif kind == "herb":
        sage = B.mat("Sage", kc.leaf_grey())
        rosemary = B.mat("Rosemary", kc.flat("Rosemary", (0.045, 0.085, 0.05)))
        purple = B.mat("Purple", kc.flat("PurpleSage", (0.07, 0.045, 0.08)))
        thyme = B.mat("Thyme", kc.flat("Thyme", (0.09, 0.14, 0.07)))
        keys = [sage, rosemary, purple, thyme, sage, rosemary]
        for i, key in enumerate(keys):
            x = x0 + (x1 - x0) * (i + 0.5) / len(keys)
            yy = rng.uniform(-0.12, 0.12)
            big = key in (rosemary, sage)
            B.dome(key, (x, yy, zs - 0.01), 0.3 if big else 0.25, 0.28 if big else 0.16, n=6, rng=rng, squash=0.95, rot=rng.random())
    elif kind == "flower":
        tex = B.mat("Foliage", outdoor.foliage(), tile=1.5)
        cols = [kc.flat("Dahlia_Rose", (0.42, 0.05, 0.14)), kc.flat("Dahlia_Apricot", (0.55, 0.20, 0.05)),
                kc.flat("Dahlia_Cream", (0.62, 0.55, 0.36)), kc.flat("Dahlia_Wine", (0.20, 0.015, 0.05))]
        bl = [B.mat(f"Bloom{i}", c) for i, c in enumerate(cols)]
        B.ridge(tex, (x0, -0.28, zs - 0.01), (x1, -0.28, zs - 0.01), 0.2, 0.45, 3, rng, lows=0.7)
        B.ridge(tex, (x0, 0.28, zs - 0.01), (x1, 0.28, zs - 0.01), 0.2, 0.4, 3, rng, lows=0.7)
        for k, yy in enumerate((-0.28, 0.28)):
            for i in range(3):
                x = x0 + (x1 - x0) * (i + rng.uniform(0.2, 0.8)) / 3
                B.dome(bl[(i + k * 2) % 4], (x, yy + rng.uniform(-0.04, 0.04), zs + 0.28 + rng.uniform(0, 0.14)),
                       0.1, 0.09, n=4, rng=rng)
    elif kind == "beans":
        metal = B.mat("Poles", outdoor.dark_metal())
        vine = B.mat("Vines", kc.flat("BeanLeaf", (0.035, 0.10, 0.022)))
        red = B.mat("Flower", kc.flat("BeanFlower", (0.5, 0.04, 0.02)))
        hgt = 2.45
        xs = [x0 + 0.1, (x0 + x1) / 2, x1 - 0.1]
        for x in xs:
            for sy in (-1, 1):
                B.bar(metal, (x, sy * 0.46, zs), (x, sy * 0.03, hgt), 0.03, 0.03)
        B.bar(metal, (xs[0], 0, hgt), (xs[-1], 0, hgt), 0.04, 0.04)
        # the vines: a clump of leaves climbing each half of the frame, gaps between
        for i, (a0, a1) in enumerate(((xs[0] + 0.05, xs[1] - 0.45), (xs[1] + 0.45, xs[2] - 0.05))):
            B.ridge(vine, (a0, 0, zs - 0.01), (a1, 0, zs - 0.01), 0.5, 1.75 + 0.1 * i, 4, rng, jitter=0.05, profile=[0.55, 0.93, 1.0, 0.93, 0.55])
        for i in range(3):
            sy = -1 if i % 2 else 1
            B.dome(red, (x0 + 0.8 + i * 1.8, sy * 0.3, zs + 0.9 + rng.uniform(-0.2, 0.4)), 0.05, 0.05, n=4, rng=rng)
    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    kc.report(root, parts)
