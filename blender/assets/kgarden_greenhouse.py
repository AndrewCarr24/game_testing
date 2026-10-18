"""Gabled glasshouse, 6 x 12 m: limestone plinth, slim dark-metal frame (posts, rafters,
glazing bars, gutters, downpipes), glass roof and walls, a glazed door in the front (-Y)
gable with a stone step and paved apron, paved floor, two teak potting benches with pots and
seedling trays, and tomatoes / vines trained up the aisle. Origin: floor centre of the
building (the apron lies in front, towards -Y). Units are metres."""
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

NAME = "KgardenGreenhouse"

P = dict(
    name=NAME,
    width=6.0,
    length=12.0,
    plinth_h=0.6,
    plinth_t=0.22,
    eaves=2.45,
    ridge=4.1,
    bays=5,
    seed=11,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rng = random.Random(p["seed"])
    B = kc.Builder(n)
    metal = B.mat("Frame", outdoor.dark_metal())
    glass = B.mat("Glass", outdoor.glass())
    stone = B.mat("Stone", outdoor.stone(), tile=2.0)
    teak = B.mat("Teak", outdoor.teak(), tile=0.5)
    leaf = B.mat("Leaf", outdoor.foliage(), tile=1.5)
    leaf2 = B.mat("LeafDark", kc.leaf_dark())
    leaf3 = B.mat("LeafBlue", kc.leaf_light())
    pot = B.mat("Pot", kc.terracotta())
    fruit = B.mat("Fruit", kc.flat("Tomato", (0.45, 0.03, 0.02)))
    soil = B.mat("Soil", outdoor.soil())
    bronze = B.mat("Bronze", outdoor.bronze())

    W, L = p["width"], p["length"]
    hw, hl = W / 2, L / 2
    ph, pt = p["plinth_h"], p["plinth_t"]
    ez, rz = p["eaves"], p["ridge"]
    px = hw - 0.11                     # frame line, centred on the plinth wall
    door = 0.55                        # half door opening
    C = kc.CELL

    # --- floor and plinth -------------------------------------------------
    B.box(stone, (0, 0, 0.025), (W - 2 * pt + 0.02, L - 2 * pt + 0.02, 0.05), cell=C, skip=("-z", "-x", "+x", "-y", "+y"))
    # long walls
    for sx in (-1, 1):
        B.box(stone, (sx * (hw - pt / 2), 0, ph / 2), (pt, L, ph), cell=C, skip=("-z",))
    # gable walls (front has the door opening)
    B.box(stone, (0, hl - pt / 2, ph / 2), (W - 2 * pt, pt, ph), cell=C, skip=("-z", "-x", "+x"))
    for sx in (-1, 1):
        xc = sx * (door + (hw - pt - door) / 2)
        B.box(stone, (xc, -hl + pt / 2, ph / 2), (hw - pt - door, pt, ph), cell=C, skip=("-z", "-x", "+x"))
    # door sill, step and paved apron
    B.box(stone, (0, -hl + pt / 2, 0.04), (2 * door, pt, 0.08), skip=("-z",))
    B.box(stone, (0, -hl - 0.22, 0.045), (1.5, 0.44, 0.09), cell=None, skip=("-z",))
    B.box(stone, (0, -hl - 1.35, 0.02), (3.0, 1.9, 0.04), cell=1.6, skip=("-z",))

    # --- frame ------------------------------------------------------------
    ys = [(-hl + 0.11) + i * (L - 0.22) / p["bays"] for i in range(p["bays"] + 1)]
    mids = [(ys[i] + ys[i + 1]) / 2 for i in range(p["bays"])]
    for y in ys:
        for sx in (-1, 1):
            B.bar(metal, (sx * px, y, ph), (sx * px, y, ez), 0.07, 0.07)
            B.bar(metal, (sx * px, y, ez), (0, y, rz), 0.06, 0.09)
    for sx in (-1, 1):
        # eaves gutter, rail, transom, purlin
        B.box(metal, (sx * (hw + 0.02), 0, ez + 0.03), (0.13, L + 0.1, 0.1), skip=("-z",))
        B.bar(metal, (sx * px, -hl + 0.11, 1.55), (sx * px, hl - 0.11, 1.55), 0.045, 0.045)
    B.bar(metal, (0, -hl + 0.11, rz), (0, hl - 0.11, rz), 0.08, 0.12)
    B.box(metal, (0, 0, rz + 0.075), (0.2, L - 0.1, 0.03))

    # --- glass --------------------------------------------------------------
    for sx in (-1, 1):
        for i in range(p["bays"]):
            y0, y1 = ys[i], ys[i + 1]
            # wall pane (outward normal along sx)
            if sx > 0:
                B.quad(glass, (px, y0, ph), (px, y1, ph), (px, y1, ez), (px, y0, ez))
                B.quad(glass, (px, y1, ez), (px, y0, ez), (0, y0, rz), (0, y1, rz))
            else:
                B.quad(glass, (-px, y1, ph), (-px, y0, ph), (-px, y0, ez), (-px, y1, ez))
                B.quad(glass, (-px, y0, ez), (-px, y1, ez), (0, y1, rz), (0, y0, rz))
    # gables
    y_f, y_b = -hl + 0.11, hl - 0.11
    B.tri(glass, (-px, y_b, ez), (px, y_b, ez), (0, y_b, rz))
    B.quad(glass, (-px, y_b, ph), (px, y_b, ph), (px, y_b, ez), (-px, y_b, ez))
    B.tri(glass, (px, y_f, ez), (-px, y_f, ez), (0, y_f, rz))
    # front: side lights either side of the door, fanlight above it
    B.quad(glass, (-door, y_f, ph), (-px, y_f, ph), (-px, y_f, ez), (-door, y_f, ez))
    B.quad(glass, (px, y_f, ph), (door, y_f, ph), (door, y_f, ez), (px, y_f, ez))
    B.quad(glass, (door, y_f, 2.2), (-door, y_f, 2.2), (-door, y_f, ez), (door, y_f, ez))

    # gable framing: king post at the back, mullions, door frame and leaf
    for y, f in ((y_b, 1), (y_f, -1)):
        for x in (-1.5, 1.5):
            ztop = ez + (rz - ez) * (1 - abs(x) / px)
            B.bar(metal, (x, y, ph), (x, y, ztop), 0.04, 0.05)
        B.bar(metal, (-px, y, 1.55), (px, y, 1.55), 0.045, 0.045)
    B.bar(metal, (0, y_b, ph), (0, y_b, rz), 0.04, 0.05)
    for sx in (-1, 1):
        B.bar(metal, (sx * door, y_f - 0.01, 0.08), (sx * door, y_f - 0.01, ez), 0.07, 0.09)
    B.bar(metal, (-door, y_f - 0.01, 2.2), (door, y_f - 0.01, 2.2), 0.05, 0.07)
    # door leaf: frame + glass + pull handle
    dy = y_f - 0.05
    for sx in (-1, 1):
        B.bar(metal, (sx * (door - 0.05), dy, 0.09), (sx * (door - 0.05), dy, 2.15), 0.06, 0.05)
    B.bar(metal, (-door + 0.05, dy, 0.1), (door - 0.05, dy, 0.1), 0.05, 0.05)
    B.bar(metal, (-door + 0.05, dy, 2.12), (door - 0.05, dy, 2.12), 0.05, 0.05)
    B.bar(metal, (-door + 0.05, dy, 1.1), (door - 0.05, dy, 1.1), 0.035, 0.04)
    B.quad(glass, (-door + 0.05, dy, 0.1), (door - 0.05, dy, 0.1), (door - 0.05, dy, 2.12), (-door + 0.05, dy, 2.12))

    # --- inside: potting benches, pots, trays, tomatoes ---------------------------
    by = 0.0
    bench_h, bench_w = 0.85, 0.7
    bx = hw - pt - 0.15 - bench_w / 2
    y0b, y1b = -hl + 0.9, hl - 0.6
    for sx in (-1, 1):
        B.box(teak, (sx * bx, (y0b + y1b) / 2, bench_h - 0.025), (bench_w, y1b - y0b, 0.05), cell=4.0, skip=("-z",))
        for yy in (y0b + 0.15, (y0b + y1b) / 2, y1b - 0.15):
            for dx in (-1, 1):
                B.bar(metal, (sx * bx + dx * (bench_w / 2 - 0.05), yy, 0.05), (sx * bx + dx * (bench_w / 2 - 0.05), yy, bench_h - 0.05), 0.045, 0.045)
    # pots and seedling trays on the benches
    pots = [(-1, 1.0), (-1, 4.4), (1, -3.2), (1, 3.3)]
    for k, (sx, yy) in enumerate(pots):
        r = rng.uniform(0.11, 0.16)
        h = r * 1.5
        B.cyl(pot, (sx * bx + rng.uniform(-0.12, 0.12), yy, bench_h), r, h, n=6, r_top=r * 1.18)
        if k % 2 == 0:
            B.dome(leaf3 if k % 4 == 0 else leaf2, (sx * bx, yy, bench_h + h), r * 1.5, rng.uniform(0.18, 0.3), n=5, rng=rng)
    for k, yy in enumerate((-2.6, 1.2)):
        sx = -1 if k < 1 else 1
        B.box(teak if k % 2 else metal, (sx * bx, yy, bench_h + 0.03), (0.5, 0.36, 0.06), skip=("-z",))
        B.box(leaf2 if k % 2 else leaf3, (sx * bx, yy, bench_h + 0.065), (0.46, 0.32, 0.04), skip=("-z", "-x", "+x", "-y", "+y"))
    # tomatoes / vines up strings in the aisle, trained as tall lumpy columns
    for k, yy in enumerate((-2.6, 3.4)):
        xx = rng.uniform(-0.15, 0.15)
        B.cyl(pot, (xx, yy, 0.0), 0.2, 0.3, n=6, r_top=0.25)
        zc = 0.3
        for lvl in range(3):
            r = 0.3 - lvl * 0.03
            B.dome(leaf2 if lvl % 2 else leaf, (xx, yy, zc), r + 0.05, 0.4, n=5, rng=rng)
            zc += 0.42
        B.bar(metal, (xx, yy, 0.3), (xx, yy, ez), 0.015, 0.015)

    root, parts = B.finish()
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    kc.report(root, parts)
