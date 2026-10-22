"""The kitchen (town2_diner.py, in the annex): the cook line facing the pass-through (a six-burner
range, the flat-top griddle on a refrigerated chef base, a charbroiler, two fryers, a dump
station), its stainless hood with baffle filters, the cold prep table under the pass, the back
of house (three-compartment sink, dish machine and table, wire shelving with dry goods, a prep
table), the reach-ins, the ice machine, staff lockers. The walk-in's box and door are the annex's.
"""
import math

import town2_diner_geo as G


def build(k, M, p):
    A = p["annex"]
    fz = p["fz"]
    cz = A["cz"]
    ly = A["line_y"]                         # the hood wall's south face
    y0 = ly - 0.8                            # the line's front edge
    BLACK = p["black"]

    # ------------------------------------------------ the line
    range6(k, M, p, -2.9, -1.9, y0, ly)
    griddle(k, M, p, -1.85, -0.65, y0, ly)
    broiler(k, M, p, -0.6, 0.3, y0, ly)
    fryer(k, M, p, 0.35, 0.75, y0, ly)
    fryer(k, M, p, 0.77, 1.17, y0, ly)
    dump(k, M, p, 1.22, 2.0, y0, ly)
    worktable(k, M, p, 2.05, 3.85, y0, ly, shelf=True)
    k.collider((-2.9, y0, fz), (3.85, ly, fz + 0.92))
    # the hood: a stainless canopy over the hot line, baffle filters, two lights
    hx0, hx1 = -3.0, 2.1
    hz0 = cz - 0.62
    k.add("Hood_Box", G.box_lohi((hx0, ly - 1.1, hz0), (hx1, ly, cz), bevel=0.008), M["steel"], tile=0.5)
    k.add("Hood_Lip", G.box_lohi((hx0 - 0.01, ly - 1.12, hz0 - 0.03), (hx1 + 0.01, ly - 1.08, hz0 + 0.04)), M["steel"], tile=0.5)
    nf = 8
    for i in range(nf):
        fx0 = hx0 + 0.08 + i * (hx1 - hx0 - 0.16) / nf
        fx1 = fx0 + (hx1 - hx0 - 0.16) / nf - 0.02
        for j in range(5):
            zz = hz0 + 0.12 + j * 0.08
            k.add("Hood_Baffle", G.box_lohi((fx0, ly - 0.32 - 0.04 * j, zz), (fx1, ly - 0.2 - 0.04 * j, zz + 0.05)), M["steel"], tile=0.5, lm=0.4)
    k.add("Hood_Under", G.box_lohi((hx0 + 0.02, ly - 1.06, hz0 + 0.01), (hx1 - 0.02, ly - 0.02, hz0 + 0.02)), M["paint"], tint=(0.05, 0.05, 0.05), tile=1.0, lm=0.5)
    for lx in (-1.6, 0.6):
        k.add("Hood_Light", G.box_lohi((lx - 0.18, ly - 0.75, hz0 + 0.0), (lx + 0.18, ly - 0.6, hz0 + 0.012)), M["globe_cool"], tile=None, bake=False)
        k.light(kind="area", loc=(lx, ly - 0.68, hz0 - 0.02), size=(0.36, 0.15), power=40.0, color=(1.0, 0.93, 0.82), dir=(0, 0, -1))
    # the fire-suppression nozzles and pipe under the hood
    k.add("Hood_Pipe", G.tube([(hx0 + 0.1, ly - 0.5, hz0 + 0.04), (hx1 - 0.1, ly - 0.5, hz0 + 0.04)], 0.012, n=6), M["chrome"], tile=0.5, lm=0.3)

    # ------------------------------------------------ the cold prep table under the pass
    pa, pb = p["pass"]
    yb = p["car"]["yb"]
    cold(k, M, p, pa - 1.0, pb + 1.2, yb, yb + 0.7)
    k.collider((pa - 1.0, yb, fz), (pb + 1.2, yb + 0.7, fz + 0.92))
    # the pass shelf's upper tier (kitchen side) with plates waiting
    k.add("Pass_Tier", G.box_lohi((pa, yb + 0.05, p["pass_z"][0] + 0.32), (pb, yb + 0.32, p["pass_z"][0] + 0.34)), M["steel"], tile=0.5)
    for j, px in enumerate((-0.8, -0.25, 0.4)):
        plate(k, M, p, px, yb + 0.15, p["pass_z"][0], food=("burger", "pie", "eggs")[j])

    # ------------------------------------------------ back of house
    iy1 = A["iy1"]
    sink3(k, M, p, -2.85, -0.85, iy1 - 0.7, iy1)
    k.collider((-2.85, iy1 - 0.7, fz), (-0.85, iy1, fz + 0.92))
    dishmachine(k, M, p, -0.8, -0.1, iy1 - 0.7, iy1)
    worktable(k, M, p, -0.05, 1.0, iy1 - 0.7, iy1, shelf=True, splash=True)
    k.collider((-0.8, iy1 - 0.7, fz), (1.0, iy1, fz + 1.6))
    worktable(k, M, p, 2.35, 4.6, iy1 - 0.75, iy1, shelf=True, splash=True)
    k.collider((2.35, iy1 - 0.75, fz), (4.6, iy1, fz + 0.92))
    k.add("Prep_Mixer", G.box_lohi((3.6, iy1 - 0.5, fz + 0.92), (3.95, iy1 - 0.15, fz + 1.0), bevel=0.02), M["paint"], tint=(0.75, 0.74, 0.7), tile=1.0)
    k.add("Prep_MixerCol", G.box_lohi((3.7, iy1 - 0.25, fz + 1.0), (3.85, iy1 - 0.12, fz + 1.45), bevel=0.02), M["paint"], tint=(0.75, 0.74, 0.7), tile=1.0)
    k.add("Prep_MixerHead", G.box_lohi((3.62, iy1 - 0.55, fz + 1.38), (3.92, iy1 - 0.12, fz + 1.55), bevel=0.04, seg=2), M["paint"], tint=(0.75, 0.74, 0.7), tile=1.0, smooth=True)
    k.add("Prep_Bowl", G.lathe([(0.001, 0.0), (0.1, 0.0), (0.15, 0.2), (0.14, 0.2), (0.001, 0.01)], c=(3.77, iy1 - 0.4, fz + 1.05), n=14), M["chrome"], tile=0.5, smooth=True)
    for j in range(3):
        k.add("Prep_Tub", G.box_lohi((2.5 + j * 0.32, iy1 - 0.55, fz + 0.92), (2.78 + j * 0.32, iy1 - 0.25, fz + 1.08), bevel=0.01), M["paint"], tint=(0.75, 0.75, 0.73), tile=1.0, lm=0.4)
    # wire shelving along the hood wall's back, with dry goods
    shelving(k, M, p, -2.9, 3.6, ly + 0.15, ly + 0.6)
    k.collider((-2.9, ly + 0.15, fz), (3.6, ly + 0.6, fz + 1.9))
    # the east side: two reach-ins, the ice machine, lockers, the waitress pickup shelf
    ix1 = A["ix1"]
    reachin(k, M, p, ix1 - 0.82, ix1, 5.7, 6.45)
    reachin(k, M, p, ix1 - 0.82, ix1, 6.5, 7.25)
    k.collider((ix1 - 0.82, 5.7, fz), (ix1, 7.25, fz + 2.05))
    icemachine(k, M, p, 4.25, 5.05, 5.45, 6.2)
    k.collider((4.25, 5.45, fz), (5.05, 6.2, fz + 1.75))
    lockers(k, M, p, ix1 - 0.45, ix1, 7.45, 8.45)
    k.collider((ix1 - 0.45, 7.45, fz), (ix1, 8.45, fz + 1.85))
    # a mop sink and bucket by the back door; a fire extinguisher; a first-aid box
    k.add("MopSink", G.box_lohi((1.0 + 0.05, iy1 - 0.55, fz), (1.0 + 0.0 + 0.1, iy1, fz + 0.25)), M["steel"], tile=0.5)
    k.add("Bucket", G.lathe([(0.001, 0.0), (0.16, 0.0), (0.18, 0.32), (0.17, 0.32), (0.001, 0.01)], c=(2.65, 8.9, fz), n=12), M["paint"], tint=(0.6, 0.45, 0.05), tile=1.0, lm=0.4)
    k.add("Extinguisher", G.cyl((-2.95, 7.0, fz + 0.75), 0.08, 0.5, n=12, bevel=0.02), M["paint"], tint=(0.5, 0.02, 0.02), tile=1.0, smooth=True)
    k.add("Extinguisher_Head", G.box_lohi((-2.99, 6.97, fz + 1.0), (-2.91, 7.03, fz + 1.1)), M["paint"], tint=BLACK, tile=1.0)


# ------------------------------------------------------------------ equipment pieces

def _base(k, M, p, x0, x1, y0, y1, h, name, doors=1, knobs=0):
    fz = p["fz"]
    k.add(f"{name}_Body", G.box_lohi((x0, y0 + 0.02, fz + 0.15), (x1, y1, fz + h)), M["steel"], tile=0.5)
    k.add(f"{name}_Front", G.box_lohi((x0, y0, fz + 0.18), (x1, y0 + 0.02, fz + h - 0.14), bevel=0.004), M["steel"], tile=0.5)
    for lx in (x0 + 0.06, x1 - 0.06):
        for ly_ in (y0 + 0.08, y1 - 0.08):
            k.add(f"{name}_Leg", G.cyl((lx, ly_, fz + 0.075), 0.025, 0.15, n=8), M["chrome"], tile=0.5, lm=0.3)
    # control panel strip with knobs
    k.add(f"{name}_Panel", G.box_lohi((x0, y0 - 0.03, fz + h - 0.14), (x1, y0 + 0.02, fz + h - 0.02), bevel=0.005), M["steel"], tile=0.5)
    for i in range(knobs):
        kx = x0 + (i + 0.5) * (x1 - x0) / knobs
        k.add(f"{name}_Knob", G.cyl((kx, y0 - 0.05, fz + h - 0.08), 0.025, 0.04, n=10, axis="y", bevel=0.006), M["paint"], tint=(0.02, 0.02, 0.02), tile=1.0, lm=0.3)
    for i in range(doors):
        d0 = x0 + i * (x1 - x0) / doors + 0.03
        d1 = x0 + (i + 1) * (x1 - x0) / doors - 0.03
        k.add(f"{name}_Handle", G.box_lohi((d0 + 0.05, y0 - 0.03, fz + h - 0.24), (d1 - 0.05, y0 - 0.005, fz + h - 0.21), bevel=0.006), M["chrome"], tile=0.5)


def range6(k, M, p, x0, x1, y0, y1):
    fz = p["fz"]
    h = 0.9
    _base(k, M, p, x0, x1, y0, y1, h, "Range", doors=1, knobs=6)
    k.add("Range_Top", G.box_lohi((x0, y0, fz + h), (x1, y1, fz + h + 0.03)), M["steel"], tile=0.5)
    for i in range(3):
        for j in range(2):
            cx, cy = x0 + 0.17 + i * 0.33, y0 + 0.22 + j * 0.35
            k.add("Range_Grate", G.box_lohi((cx - 0.15, cy - 0.15, fz + h + 0.03), (cx + 0.15, cy - 0.13, fz + h + 0.06)), M["paint"], tint=(0.02, 0.02, 0.02), tile=1.0, lm=0.3)
            k.add("Range_Grate", G.box_lohi((cx - 0.15, cy + 0.13, fz + h + 0.03), (cx + 0.15, cy + 0.15, fz + h + 0.06)), M["paint"], tint=(0.02, 0.02, 0.02), tile=1.0, lm=0.3)
            k.add("Range_Grate", G.box_lohi((cx - 0.01, cy - 0.15, fz + h + 0.03), (cx + 0.01, cy + 0.15, fz + h + 0.06)), M["paint"], tint=(0.02, 0.02, 0.02), tile=1.0, lm=0.3)
            k.add("Range_Burner", G.cyl((cx, cy, fz + h + 0.04), 0.06, 0.02, n=10), M["paint"], tint=(0.03, 0.03, 0.03), tile=1.0, lm=0.3)
    k.add("Range_Back", G.box_lohi((x0, y1 - 0.08, fz + h + 0.03), (x1, y1, fz + h + 0.5)), M["steel"], tile=0.5)
    k.add("Range_Shelf", G.box_lohi((x0, y1 - 0.3, fz + h + 0.42), (x1, y1, fz + h + 0.45)), M["steel"], tile=0.5)
    # a stockpot and a sauté pan
    k.add("Stockpot", G.lathe([(0.001, 0.0), (0.16, 0.0), (0.16, 0.3), (0.15, 0.3), (0.001, 0.29)], c=(x0 + 0.17, y0 + 0.57, fz + h + 0.06), n=14), M["chrome"], tile=0.5, smooth=True)
    k.add("Pan", G.lathe([(0.001, 0.0), (0.11, 0.0), (0.13, 0.05), (0.12, 0.05), (0.001, 0.01)], c=(x0 + 0.5, y0 + 0.22, fz + h + 0.06), n=14), M["paint"], tint=(0.06, 0.06, 0.06), tile=1.0, smooth=True, lm=0.4)
    k.add("Pan_Handle", G.box_lohi((x0 + 0.5 - 0.015, y0 - 0.12, fz + h + 0.1), (x0 + 0.5 + 0.015, y0 + 0.1, fz + h + 0.115)), M["paint"], tint=(0.06, 0.06, 0.06), tile=1.0, lm=0.3)


def griddle(k, M, p, x0, x1, y0, y1):
    """The flat-top on a two-drawer refrigerated chef base: seasoned plate, grease trough, splash."""
    fz = p["fz"]
    h = 0.62
    _base(k, M, p, x0, x1, y0, y1, h, "ChefBase", doors=2, knobs=0)
    zt = fz + h
    k.add("Griddle_Body", G.box_lohi((x0, y0 + 0.04, zt), (x1, y1, zt + 0.24)), M["steel"], tile=0.5)
    for i in range(4):
        k.add("Griddle_Knob", G.cyl((x0 + 0.15 + i * 0.3, y0 + 0.02, zt + 0.12), 0.025, 0.04, n=10, axis="y"), M["paint"], tint=(0.02, 0.02, 0.02), tile=1.0, lm=0.3)
    zp = zt + 0.24
    k.add("Griddle_Plate", G.decal((x0 + 0.03, y0 + 0.1, zp + 0.012), (x1 - 0.03, y0 + 0.1, zp + 0.012), (x1 - 0.03, y1 - 0.1, zp + 0.012), (x0 + 0.03, y1 - 0.1, zp + 0.012), "griddle"),
          M["decal"], tile=None)
    k.add("Griddle_PlateEdge", G.box_lohi((x0 + 0.02, y0 + 0.09, zp), (x1 - 0.02, y1 - 0.09, zp + 0.011)), M["paint"], tint=(0.04, 0.04, 0.04), tile=1.0, lm=0.5)
    k.add("Griddle_Trough", G.box_lohi((x0, y0 + 0.04, zp - 0.02), (x1, y0 + 0.1, zp + 0.01)), M["steel"], tile=0.5)
    for xs in (x0, x1 - 0.02):
        k.add("Griddle_Side", G.box_lohi((xs, y0 + 0.1, zp), (xs + 0.02, y1, zp + 0.12)), M["steel"], tile=0.5)
    k.add("Griddle_Splash", G.box_lohi((x0, y1 - 0.09, zp), (x1, y1, zp + 0.25)), M["steel"], tile=0.5)
    # on the plate: patties, a bun pair toasting, the press
    for i, (px, py) in enumerate(((x0 + 0.3, y0 + 0.35), (x0 + 0.5, y0 + 0.45), (x0 + 0.28, y0 + 0.58))):
        k.add("Griddle_Patty", G.decal_disc((px, py, zp + 0.026), 0.055, "patty", n=12), M["decal"], tile=None, lm=0.4)
        k.add("Griddle_PattySide", G.cyl((px, py, zp + 0.019), 0.055, 0.014, n=12, cap=False), M["paint"], tint=(0.1, 0.045, 0.02), tile=1.0, lm=0.3)
    for i in range(2):
        k.add("Griddle_Bun", G.decal_disc((x1 - 0.35 + i * 0.14, y0 + 0.5, zp + 0.035), 0.055, "bun", n=12), M["decal"], tile=None, lm=0.4)
        k.add("Griddle_BunSide", G.cyl((x1 - 0.35 + i * 0.14, y0 + 0.5, zp + 0.024), 0.055, 0.022, n=12, cap=False), M["paint"], tint=(0.55, 0.32, 0.12), tile=1.0, lm=0.3)
    k.add("Griddle_Spatula", G.box_lohi((x1 - 0.2, y0 + 0.15, zp + 0.013), (x1 - 0.08, y0 + 0.25, zp + 0.016)), M["steel"], tile=0.5, lm=0.3)
    k.add("Griddle_SpatHandle", G.box_lohi((x1 - 0.16, y0 - 0.05, zp + 0.02), (x1 - 0.12, y0 + 0.15, zp + 0.04), bevel=0.006), M["paint"], tint=(0.04, 0.03, 0.02), tile=1.0, lm=0.3)


def broiler(k, M, p, x0, x1, y0, y1):
    fz = p["fz"]
    h = 0.62
    _base(k, M, p, x0, x1, y0, y1, h, "BroilerStand", doors=1)
    zt = fz + h
    k.add("Broiler_Body", G.box_lohi((x0, y0 + 0.04, zt), (x1, y1, zt + 0.3)), M["steel"], tile=0.5)
    for i in range(14):
        gx = x0 + 0.05 + i * (x1 - x0 - 0.1) / 13
        k.add("Broiler_Grate", G.box_lohi((gx - 0.012, y0 + 0.1, zt + 0.3), (gx + 0.012, y1 - 0.1, zt + 0.32)), M["paint"], tint=(0.03, 0.03, 0.03), tile=1.0, lm=0.3)
    k.add("Broiler_Coals", G.box_lohi((x0 + 0.04, y0 + 0.1, zt + 0.26), (x1 - 0.04, y1 - 0.1, zt + 0.27)), M["neon_red"], tile=None, bake=True)
    k.add("Broiler_Splash", G.box_lohi((x0, y1 - 0.09, zt + 0.3), (x1, y1, zt + 0.55)), M["steel"], tile=0.5)
    for i in range(3):
        k.add("Broiler_Knob", G.cyl((x0 + 0.15 + i * 0.3, y0 + 0.02, zt + 0.15), 0.025, 0.04, n=10, axis="y"), M["paint"], tint=(0.02, 0.02, 0.02), tile=1.0, lm=0.3)


def fryer(k, M, p, x0, x1, y0, y1):
    fz = p["fz"]
    h = 0.88
    _base(k, M, p, x0, x1, y0, y1, h, "Fryer", doors=1)
    zt = fz + h
    k.add("Fryer_Top", G.box_lohi((x0, y0, zt), (x1, y1, zt + 0.03)), M["steel"], tile=0.5)
    k.add("Fryer_Oil", G.box_lohi((x0 + 0.05, y0 + 0.08, zt - 0.06), (x1 - 0.05, y1 - 0.15, zt + 0.032)), M["paint"], tint=(0.2, 0.12, 0.03), tile=1.0, lm=0.5)
    k.add("Fryer_Flue", G.box_lohi((x0 + 0.02, y1 - 0.14, zt + 0.03), (x1 - 0.02, y1, zt + 0.32)), M["steel"], tile=0.5)
    # a basket hanging on the flue, a basket down in the oil
    for j, (zb, yy) in enumerate(((zt + 0.08, y1 - 0.4), (zt - 0.02, y0 + 0.3))):
        k.add("Fryer_Basket", G.box_lohi((x0 + 0.07, yy - 0.14, zb), (x1 - 0.07, yy + 0.14, zb + 0.14)), M["chrome"], tint=(0.5, 0.5, 0.5), tile=0.5, lm=0.4)
        k.add("Fryer_BasketHandle", G.box_lohi(((x0 + x1) / 2 - 0.012, yy - 0.5, zb + 0.12), ((x0 + x1) / 2 + 0.012, yy - 0.14, zb + 0.15), bevel=0.005), M["paint"], tint=(0.6, 0.05, 0.04), tile=1.0, lm=0.3)


def dump(k, M, p, x0, x1, y0, y1):
    """The fry dump station: a perforated pan under a heat lamp, a scoop."""
    fz = p["fz"]
    h = 0.88
    _base(k, M, p, x0, x1, y0, y1, h, "Dump", doors=1)
    zt = fz + h
    k.add("Dump_Top", G.box_lohi((x0, y0, zt), (x1, y1, zt + 0.03)), M["steel"], tile=0.5)
    k.add("Dump_Pan", G.box_lohi((x0 + 0.06, y0 + 0.1, zt - 0.05), (x1 - 0.06, y1 - 0.12, zt + 0.031)), M["paint"], tint=(0.7, 0.55, 0.25), tile=1.0, lm=0.4)
    k.add("Dump_Lamp", G.box_lohi((x0 + 0.05, y0 + 0.2, zt + 0.55), (x1 - 0.05, y0 + 0.45, zt + 0.62), bevel=0.01), M["steel"], tile=0.5)
    k.add("Dump_LampGlow", G.box_lohi((x0 + 0.08, y0 + 0.24, zt + 0.545), (x1 - 0.08, y0 + 0.41, zt + 0.55)), M["neon_red"], tile=None, bake=False)
    k.add("Dump_LampPost", G.box_lohi((x0 + 0.05, y1 - 0.06, zt), (x0 + 0.09, y1 - 0.02, zt + 0.62)), M["steel"], tile=0.5)
    k.light(kind="area", loc=((x0 + x1) / 2, y0 + 0.33, zt + 0.53), size=(x1 - x0 - 0.2, 0.15), power=12.0, color=(1.0, 0.45, 0.2), dir=(0, 0, -1))


def worktable(k, M, p, x0, x1, y0, y1, shelf=True, splash=False):
    fz = p["fz"]
    zt = fz + 0.9
    k.add("Table_Steel", G.box_lohi((x0, y0, zt - 0.04), (x1, y1, zt), bevel=0.006), M["steel"], tile=0.5)
    if splash:
        k.add("Table_Splash", G.box_lohi((x0, y1 - 0.03, zt), (x1, y1, zt + 0.12)), M["steel"], tile=0.5)
    for lx in (x0 + 0.04, x1 - 0.04):
        for ly in (y0 + 0.04, y1 - 0.04):
            k.add("Table_SteelLeg", G.cyl((lx, ly, fz + 0.45), 0.02, 0.86, n=8), M["chrome"], tile=0.5, lm=0.3)
    if shelf:
        k.add("Table_UnderShelf", G.box_lohi((x0 + 0.02, y0 + 0.02, fz + 0.2), (x1 - 0.02, y1 - 0.02, fz + 0.22)), M["steel"], tile=0.5)
        # stock on the undershelf: a few boxes and tubs
        for i in range(int((x1 - x0) / 0.45)):
            bx = x0 + 0.1 + i * 0.45
            k.add("Stock_Box", G.box_lohi((bx, y0 + 0.08, fz + 0.22), (bx + 0.36, y1 - 0.1, fz + 0.22 + 0.18 + 0.06 * (i % 2))), M["paint"], tint=(0.42, 0.3, 0.17), tile=1.0, lm=0.3)


def cold(k, M, p, x0, x1, y0, y1):
    """The refrigerated sandwich unit: a pan rail of inserts with toppings, a cutting board, doors."""
    fz = p["fz"]
    h = 0.88
    zt = fz + h
    # (its doors face the cook, +y; its back is against the car's back wall)
    k.add("Cold_Body", G.box_lohi((x0, y0, fz + 0.12), (x1, y1 - 0.02, zt)), M["steel"], tile=0.5)
    k.add("Cold_Kick", G.box_lohi((x0 + 0.04, y0, fz), (x1 - 0.04, y1 - 0.06, fz + 0.12)), M["paint"], tint=p["black"], tile=1.0)
    nd = 3
    for i in range(nd):
        d0 = x0 + i * (x1 - x0) / nd + 0.03
        d1 = x0 + (i + 1) * (x1 - x0) / nd - 0.03
        k.add("Cold_Door", G.box_lohi((d0, y1 - 0.02, fz + 0.16), (d1, y1, zt - 0.06), bevel=0.004), M["steel"], tile=0.5)
        k.add("Cold_Handle", G.box_lohi((d0 + 0.05, y1, zt - 0.16), (d1 - 0.05, y1 + 0.025, zt - 0.13), bevel=0.006), M["chrome"], tile=0.5)
    k.add("Cold_Top", G.box_lohi((x0, y0, zt), (x1, y1, zt + 0.03)), M["steel"], tile=0.5)
    k.add("Cold_Board", G.box_lohi((x0 + 0.05, y1 - 0.3, zt + 0.03), (x1 - 0.05, y1 - 0.02, zt + 0.045)), M["paint"], tint=(0.7, 0.68, 0.6), tile=1.0)
    cols = [(0.35, 0.05, 0.03), (0.55, 0.45, 0.1), (0.15, 0.3, 0.08), (0.65, 0.6, 0.45), (0.6, 0.1, 0.05), (0.7, 0.65, 0.5), (0.12, 0.2, 0.05), (0.62, 0.5, 0.2)]
    n = int((x1 - x0 - 0.1) / 0.18)
    for i in range(n):
        px = x0 + 0.08 + i * 0.18
        k.add("Cold_Pan", G.box_lohi((px, y0 + 0.06, zt + 0.0), (px + 0.16, y0 + 0.32, zt + 0.04)), M["steel"], tile=0.5, lm=0.4)
        k.add("Cold_Food", G.box_lohi((px + 0.01, y0 + 0.07, zt + 0.02), (px + 0.15, y0 + 0.31, zt + 0.035)), M["paint"], tint=cols[i % len(cols)], tile=1.0, lm=0.3)


def plate(k, M, p, x, y, z, food="burger"):
    k.add("Plate", G.lathe([(0.001, 0.0), (0.1, 0.0), (0.13, 0.018), (0.125, 0.02), (0.1, 0.006), (0.001, 0.006)], c=(x, y, z), n=18), M["paint"], tint=(0.8, 0.78, 0.72), tile=1.0, smooth=True, lm=0.3)
    if food == "burger":
        k.add("Food_Bun", G.lathe([(0.001, 0.0), (0.055, 0.0), (0.058, 0.025), (0.045, 0.045), (0.001, 0.05)], c=(x - 0.02, y, z + 0.05), n=12), M["paint"], tint=(0.55, 0.3, 0.1), tile=1.0, smooth=True, lm=0.3)
        k.add("Food_Patty", G.cyl((x - 0.02, y, z + 0.04), 0.057, 0.018, n=12), M["paint"], tint=(0.12, 0.05, 0.025), tile=1.0, lm=0.3)
        k.add("Food_Bun", G.cyl((x - 0.02, y, z + 0.018), 0.055, 0.024, n=12), M["paint"], tint=(0.6, 0.38, 0.15), tile=1.0, lm=0.3)
        for i in range(9):
            a = i * 0.7
            k.add("Food_Fry", G.box_lohi((x + 0.05 + 0.02 * math.cos(a), y - 0.05 + i * 0.012, z + 0.008), (x + 0.11, y - 0.04 + i * 0.012, z + 0.018)), M["paint"], tint=(0.75, 0.52, 0.18), tile=1.0, lm=0.2)
    elif food == "pie":
        k.add("Food_Slice", G.prism([(x, y), (x + 0.1, y - 0.035), (x + 0.1, y + 0.035)], z + 0.006, z + 0.05), M["paint"], tint=(0.32, 0.03, 0.03), tile=1.0, lm=0.3)
    else:
        k.add("Food_Egg", G.cyl((x - 0.03, y, z + 0.008), 0.045, 0.006, n=12), M["paint"], tint=(0.85, 0.84, 0.8), tile=1.0, lm=0.3)
        k.add("Food_Yolk", G.lathe([(0.001, 0.0), (0.018, 0.0), (0.012, 0.01), (0.001, 0.012)], c=(x - 0.03, y, z + 0.011), n=10), M["paint"], tint=(0.85, 0.5, 0.05), tile=1.0, lm=0.2)
        k.add("Food_Toast", G.box_lohi((x + 0.02, y - 0.05, z + 0.006), (x + 0.1, y + 0.05, z + 0.02), bevel=0.005), M["paint"], tint=(0.55, 0.33, 0.12), tile=1.0, lm=0.2)


def sink3(k, M, p, x0, x1, y0, y1):
    fz = p["fz"]
    zt = fz + 0.92
    k.add("Sink_Body", G.box_lohi((x0, y0, zt - 0.32), (x1, y1, zt)), M["steel"], tile=0.5)
    for i in range(3):
        bx0 = x0 + 0.45 + i * 0.4
        k.add("Sink_Basin", G.box_lohi((bx0, y0 + 0.08, zt - 0.3), (bx0 + 0.36, y1 - 0.12, zt + 0.001)), M["paint"], tint=(0.25, 0.25, 0.26), tile=1.0, lm=0.5)
    k.add("Sink_Splash", G.box_lohi((x0, y1 - 0.05, zt), (x1, y1, zt + 0.25)), M["steel"], tile=0.5)
    for lx in (x0 + 0.04, x1 - 0.04):
        for ly in (y0 + 0.04, y1 - 0.04):
            k.add("Sink_Leg", G.cyl((lx, ly, fz + 0.3), 0.02, 0.6, n=8), M["chrome"], tile=0.5, lm=0.3)
    for i in range(2):
        fx = x0 + 0.85 + i * 0.6
        k.add("Sink_Faucet", G.tube([(fx, y1 - 0.06, zt + 0.15), (fx, y1 - 0.3, zt + 0.15), (fx, y1 - 0.3, zt + 0.08)], 0.015, n=8), M["chrome"], tile=0.5, smooth=True)
    k.add("Sink_Sprayer", G.tube([(x0 + 0.2, y1 - 0.08, zt), (x0 + 0.2, y1 - 0.08, zt + 0.9), (x0 + 0.2, y1 - 0.35, zt + 0.7)], 0.012, n=6), M["chrome"], tile=0.5, smooth=True)


def dishmachine(k, M, p, x0, x1, y0, y1):
    fz = p["fz"]
    k.add("Dish_Base", G.box_lohi((x0, y0, fz), (x1, y1, fz + 0.85)), M["steel"], tile=0.5)
    k.add("Dish_Hood", G.box_lohi((x0 + 0.02, y0 + 0.02, fz + 0.85), (x1 - 0.02, y1 - 0.02, fz + 1.55), bevel=0.02), M["steel"], tile=0.5)
    k.add("Dish_Handle", G.box_lohi((x0 + 0.1, y0 - 0.04, fz + 1.5), (x1 - 0.1, y0 + 0.02, fz + 1.53), bevel=0.008), M["chrome"], tile=0.5)
    k.add("Dish_Panel", G.box_lohi((x0 + 0.15, y0 - 0.005, fz + 0.65), (x1 - 0.15, y0, fz + 0.75)), M["paint"], tint=(0.03, 0.03, 0.03), tile=1.0, lm=0.3)


def shelving(k, M, p, x0, x1, y0, y1):
    """Wire shelving (chrome posts, four tiers) with dry goods: cans, sacks, boxes, jugs."""
    fz = p["fz"]
    n = int((x1 - x0) / 1.2)
    rng = __import__("random").Random(5)
    for i in range(n + 1):
        px = x0 + i * (x1 - x0) / n
        for py in (y0 + 0.02, y1 - 0.02):
            k.add("Shelf_Post", G.cyl((px, py, fz + 0.95), 0.012, 1.9, n=6), M["chrome"], tile=0.5, lm=0.2)
    for t in range(4):
        zt = fz + 0.15 + t * 0.55
        k.add("Shelf_Tier", G.box_lohi((x0, y0, zt), (x1, y1, zt + 0.02)), M["chrome"], tint=(0.6, 0.6, 0.6), tile=0.5, lm=0.4)
        x = x0 + 0.05
        while x < x1 - 0.3:
            kind = rng.random()
            if kind < 0.35:      # a row of #10 cans
                for c in range(3):
                    k.add("Stock_Can", G.cyl((x + 0.08 + c * 0.16, (y0 + y1) / 2, zt + 0.1), 0.077, 0.18, n=8), M["paint"],
                          tint=rng.choice([(0.6, 0.1, 0.05), (0.7, 0.6, 0.2), (0.15, 0.3, 0.12), (0.7, 0.68, 0.6)]), tile=1.0, lm=0.2)
                x += 0.5
            elif kind < 0.6:     # a sack of flour or sugar
                k.add("Stock_Sack", G.box_lohi((x, y0 + 0.04, zt + 0.02), (x + 0.42, y1 - 0.04, zt + 0.16), bevel=0.05, seg=2), M["paint"], tint=(0.72, 0.68, 0.58), tile=1.0, smooth=True, lm=0.2)
                x += 0.46
            elif kind < 0.85:    # cases
                hh = 0.2 + 0.15 * rng.random()
                k.add("Stock_Box", G.box_lohi((x, y0 + 0.03, zt + 0.02), (x + 0.38, y1 - 0.03, zt + 0.02 + hh)), M["paint"], tint=rng.choice([(0.42, 0.3, 0.17), (0.5, 0.38, 0.22), (0.7, 0.68, 0.62)]), tile=1.0, lm=0.2)
                x += 0.42
            else:                # jugs of oil
                for c in range(2):
                    k.add("Stock_Jug", G.box_lohi((x + c * 0.17, y0 + 0.08, zt + 0.02), (x + c * 0.17 + 0.15, y1 - 0.08, zt + 0.3), bevel=0.02), M["paint"], tint=(0.75, 0.62, 0.2), tile=1.0, lm=0.2)
                x += 0.36


def reachin(k, M, p, x0, x1, y0, y1):
    """A one-door stainless reach-in refrigerator against the east wall (its door faces -x)."""
    fz = p["fz"]
    k.add("Reach_Body", G.box_lohi((x0, y0, fz + 0.12), (x1, y1, fz + 2.0)), M["steel"], tile=0.5)
    k.add("Reach_Door", G.box_lohi((x0 - 0.03, y0 + 0.02, fz + 0.2), (x0, y1 - 0.02, fz + 1.8), bevel=0.006), M["steel"], tile=0.5)
    k.add("Reach_Handle", G.box_lohi((x0 - 0.06, y1 - 0.08, fz + 0.9), (x0 - 0.03, y1 - 0.05, fz + 1.4), bevel=0.006), M["chrome"], tile=0.5)
    k.add("Reach_Grille", G.box_lohi((x0 - 0.005, y0 + 0.02, fz + 1.83), (x0, y1 - 0.02, fz + 1.97)), M["paint"], tint=(0.05, 0.05, 0.05), tile=1.0, lm=0.4)
    k.add("Reach_Display", G.box_lohi((x0 - 0.006, y0 + 0.3, fz + 1.88), (x0 - 0.001, y0 + 0.42, fz + 1.92)), M["neon_red"], tile=None, bake=False)
    for ly in (y0 + 0.08, y1 - 0.08):
        k.add("Reach_Caster", G.cyl((x0 + 0.1, ly, fz + 0.06), 0.04, 0.12, n=8), M["paint"], tint=(0.04, 0.04, 0.04), tile=1.0, lm=0.3)


def icemachine(k, M, p, x0, x1, y0, y1):
    fz = p["fz"]
    k.add("Ice_Bin", G.box_lohi((x0, y0, fz + 0.1), (x1, y1, fz + 1.0), bevel=0.01), M["steel"], tile=0.5)
    k.add("Ice_Door", G.box_lohi((x0 + 0.08, y1, fz + 0.75), (x1 - 0.08, y1 + 0.03, fz + 0.95), bevel=0.01), M["steel"], tile=0.5)
    k.add("Ice_Head", G.box_lohi((x0, y0, fz + 1.0), (x1, y1, fz + 1.72), bevel=0.01), M["steel"], tile=0.5)
    k.add("Ice_Vent", G.box_lohi((x0 + 0.1, y1, fz + 1.15), (x1 - 0.1, y1 + 0.005, fz + 1.55)), M["paint"], tint=(0.05, 0.05, 0.05), tile=1.0, lm=0.4)


def lockers(k, M, p, x0, x1, y0, y1):
    """Four staff lockers (sage green) against the east wall, an apron on a hook, a jacket."""
    fz = p["fz"]
    n = 4
    for i in range(n):
        ya, yb = y0 + i * (y1 - y0) / n, y0 + (i + 1) * (y1 - y0) / n
        k.add("Locker", G.box_lohi((x0, ya + 0.005, fz + 0.1), (x1, yb - 0.005, fz + 1.85), bevel=0.004), M["paint"], tint=(0.2, 0.27, 0.22), tile=1.0)
        for zz in (fz + 1.6, fz + 1.65, fz + 1.7, fz + 0.3, fz + 0.35):
            k.add("Locker_Vent", G.box_lohi((x0 - 0.002, ya + 0.06, zz), (x0, yb - 0.06, zz + 0.015)), M["paint"], tint=(0.03, 0.03, 0.03), tile=1.0, lm=0.2)
        k.add("Locker_Latch", G.box_lohi((x0 - 0.03, yb - 0.06, fz + 0.95), (x0, yb - 0.03, fz + 1.1)), M["chrome"], tile=0.5)
    k.add("Locker_Base", G.box_lohi((x0 + 0.03, y0, fz), (x1, y1, fz + 0.1)), M["paint"], tint=p["black"], tile=1.0)
