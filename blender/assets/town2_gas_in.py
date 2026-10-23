"""The convenience store inside (town2_gas.py calls interior()): floor, the lay-in ceiling and its
troffers, the cooler wall, the coffee bar and the fountain, three gondolas of goods, the cash wrap
(register, lottery, the roller grill, the tobacco wall, the security monitor, a CB radio), the
restrooms and the stockroom.

References: a small-format Wawa / Sheetz (the coffee bar as a wall of brewers, cup towers and lids
under a menu board; the roller grill on the counter; terrazzo-look tile, a lay-in ceiling with 2 x 4
LED troffers), Buc-ee's for the scale and glow of the cooler wall (here 14 doors), and the small
independents' cash wrap: an oak front with a quartz top, the scratch-ticket case, the jackpot sign
hung over it, the cigarette wall behind.
"""
import importlib
import math

import town2_gas_goods as GD
import town2_gas_shop as SH

importlib.reload(GD)
importlib.reload(SH)


def interior(kit, p, rng):
    t = p["wall"]
    X0, X1, Y0, Y1 = p["sx0"] + t, p["sx1"] - t, p["sy0"] + t, p["sy1"] - t
    f, c = p["floor"], p["ceil"]
    q = dict(X0=X0, X1=X1, Y0=Y0, Y1=Y1, f=f, c=c)
    # floor (terrazzo-look tile), the black rubber base round the walls, the ceiling
    kit.p("floor", "int", lmw=0.9).box((X0, Y0, 0.0), (X1, Y1, f), skip="zxXyY")
    kit.p("floor", "int", lmw=0.5).box((p["door"][0], p["sy0"], 0.0), (p["door"][1], Y0, f), skip="zxXyY")
    base(kit, [((X0, Y0), (X1, Y0)), ((X0, Y1), (-4.6, Y1)), ((X0, Y0), (X0, Y1))], f)
    kit.p("ceiling", "int", lmw=0.6).box((X0, Y0, c), (X1, Y1, c + 0.02), skip="Z")
    kit.collide((p["sx0"], p["sy0"], 0), (p["sx1"], p["sy1"], f))
    ceiling_fixtures(kit, q, rng)
    SH.coolers(kit, q, rng)
    back_rooms(kit, p, q, rng)
    SH.coffee_bar(kit, q, rng)
    SH.fountain(kit, q, rng)
    for gx, kind in ((-12.5, "chips"), (-9.4, "snacks"), (-6.3, "auto")):
        SH.gondola(kit, rng, gx, 6.4, 12.4, kind, f)
    SH.cash_wrap(kit, p, q, rng)
    SH.floor_things(kit, p, q, rng)
    kit.mark("cctv_register", (2.6, 4.2, 2.9))


def base(kit, runs, f, h=0.1):
    B = kit.p("black", "int", lmw=0.3)
    for (a, b) in runs:
        (ax, ay), (bx, by) = a, b
        if abs(ay - by) < 1e-6:
            s = 1 if ay < 10 else -1
            B.box((min(ax, bx), ay if s > 0 else ay - 0.012, f), (max(ax, bx), ay + 0.012 if s > 0 else ay, f + h), skip="z")
        else:
            B.box((ax, min(ay, by), f), (ax + 0.012, max(ay, by), f + h), skip="z")


# ------------------------------------------------------------------ ceiling
def ceiling_fixtures(kit, q, rng):
    c = q["c"]
    G = kit.p("signs", "int")
    T = kit.p("lightgrey", "int", lmw=0.1)
    cell = kit.cell("signs", "troffer")
    for x in (-13.6, -10.9, -7.8, -4.7, -1.9):
        for y in (5.0, 8.4, 11.8):
            if x > -3 and y > 9:
                continue
            T.box((x - 0.33, y - 0.63, c - 0.012), (x + 0.33, y + 0.63, c), skip="Z")
            G.panel((x, y, c - 0.013), "z", 0.6, 1.2, cell=cell)
            kit.light("area", (x, y, c - 0.03), size=(0.6, 1.2), energy=30.0, color=(1.0, 0.97, 0.93), spread=110)
    # supply diffusers, smoke detectors, speakers, the camera domes, the convex mirror
    W = kit.p("white", "int", lmw=0.15)
    D = kit.p("graphite", "int", lmw=0.1)
    for (x, y) in ((-12.2, 6.7), (-6.2, 6.7), (-12.2, 10.1), (-6.2, 10.1), (-1.0, 6.7)):
        W.box((x - 0.3, y - 0.3, c - 0.02), (x + 0.3, y + 0.3, c), skip="Z")
        for k in range(3):
            d = 0.08 + k * 0.08
            D.box((x - d, y - d, c - 0.021), (x + d, y - d + 0.012, c - 0.02))
            D.box((x - d, y + d - 0.012, c - 0.021), (x + d, y + d, c - 0.02))
    for (x, y) in ((-9.4, 4.6), (-3.2, 11.0)):
        W.cyl((x, y), 0.07, c - 0.04, c, seg=12, caps="bottom")
    for (x, y) in ((-14.4, 13.8), (-4.0, 5.2), (1.6, 8.6)):
        kit.p("black", "int", lmw=0.1).lathe([(0.0, 0.0), (0.09, 0.0), (0.085, -0.06), (0.0, -0.09)], c=(x, y), z=c, seg=12)
    # the convex mirror in the corner by the coolers
    with kit.at((-15.6, 14.9, 2.6), rot=-45):
        with kit.at((0, 0, 0), rx=-90):
            kit.p("chrome", "int", lmw=0.1).lathe([(0.0, 0.08), (0.12, 0.065), (0.2, 0.03), (0.23, 0.0)][::-1], seg=16, cap_top=False)


# ------------------------------------------------------------------ restrooms, stockroom
def partition(kit, a0, a1, axis, c, f, h, holes=(), mat="offwhite", mat2=None, t=0.12):
    """An interior partition (both faces lit), holes (b0, b1, z0, z1)."""
    import town2_gas as TG
    for (b0, b1, z0, z1) in TG.slices(a0, a1, f, h, holes):
        lo, hi = ((b0, c - t / 2, z0), (b1, c + t / 2, z1)) if axis == 0 else ((c - t / 2, b0, z0), (c + t / 2, b1, z1))
        kit.p(mat, "int", lmw=0.8).box(lo, hi, skip=("z" if z0 <= f + 1e-3 else "") + ("Z" if z1 >= h - 1e-3 else ""))
        kit.collide(lo, hi)


def door_leaf(kit, hinge, width, f, rot, mat="oak", h=2.13, t=0.045):
    """A door leaf hinged at `hinge` (x, y), closed along +x, turned rot degrees; lever handle."""
    with kit.at((hinge[0], hinge[1], f), rot=rot):
        kit.p(mat, "int", lmw=0.6).box((0.0, -t / 2, 0.0), (width, t / 2, h), bevel=0.006)
        S = kit.p("steel", "int", lmw=0.1)
        for s in (-1, 1):
            S.box((width - 0.1, s * t / 2, 1.0), (width - 0.08, s * (t / 2 + 0.05), 1.03))
            S.box((width - 0.2, s * (t / 2 + 0.04), 1.0), (width - 0.08, s * (t / 2 + 0.06), 1.03))
        kit.collide((0.0, -t / 2, 0.0), (width, t / 2, h))


def back_rooms(kit, p, q, rng):
    f, c = q["f"], q["c"]
    X1, Y1 = q["X1"], q["Y1"]
    yw = 13.4
    dM, dW = (-3.85, -2.95), (-1.45, -0.55)
    partition(kit, -4.6, 0.36, 0, yw, f, c, holes=[(*dM, f, 2.15), (*dW, f, 2.15)])
    # the Blue Ridge mural over the restroom doors (the store's one picture: no words)
    kit.p("goods", "int", lmw=0.8).panel((-2.15, yw - 0.065, 2.82), "y", 4.8, 1.0, cell=kit.cell("goods", "mural"))
    partition(kit, yw, Y1, 1, -2.15, f, c)
    partition(kit, 9.6, Y1, 1, 0.3, f, c)
    sd = (1.2, 2.1)
    partition(kit, 0.3, X1, 0, 9.6, f, c, holes=[(*sd, f, 2.15)])
    # door frames (black), leaves ajar (inward), the restroom pictograms, the exit sign
    Bk = kit.p("black", "int", lmw=0.3)
    for (a0, a1) in (dM, dW):
        for b in (a0, a1):
            Bk.box((b - 0.03, yw - 0.075, f), (b + 0.03, yw + 0.075, 2.18))
        Bk.box((a0 - 0.03, yw - 0.075, 2.15), (a1 + 0.03, yw + 0.075, 2.21))
        door_leaf(kit, (a1, yw + 0.06), a1 - a0 - 0.01, f, 180 - 70)
        kit.p("signs", "int").panel(((a0 + a1) / 2 + 0.7 * (1 if a0 < -2 else -1), yw - 0.061, 1.55), "y", 0.22, 0.22, cell=kit.cell("signs", "restroom"))
    for b in sd:
        Bk.box((b - 0.03, 9.6 - 0.075, f), (b + 0.03, 9.6 + 0.075, 2.18))
    Bk.box((sd[0] - 0.03, 9.6 - 0.075, 2.15), (sd[1] + 0.03, 9.6 + 0.075, 2.21))
    door_leaf(kit, (sd[1], 9.6 + 0.06), sd[1] - sd[0] - 0.01, f, 180 - 60, mat="sage")
    kit.p("signs", "int").panel((-6.6, q["Y0"] + 0.01, 2.75), "Y", 0.36, 0.18, cell=kit.cell("signs", "exit"))
    kit.p("signs", "int").panel((X1 - 0.01, 15.8, 2.5), "x", 0.36, 0.18, cell=kit.cell("signs", "exit"))
    # the two restrooms
    for (rx0, rx1), door in (((-4.6, -2.15), dM), ((-2.15, 0.3), dW)):
        restroom(kit, rx0 + 0.06, rx1 - 0.06, yw + 0.06, Y1, f, c, rng, mirror_x=(rx0 > -3))
    # the stockroom
    stockroom(kit, p, 0.36, X1, 9.66, Y1, f, c, rng)


def restroom(kit, x0, x1, y0, y1, f, c, rng, mirror_x=False):
    """Single-occupancy: tile wainscot, a wall-hung toilet... (floor-mount), a basin, a mirror, grab
    bars, a hand dryer, paper towels, a bin, a baby changing station."""
    Tl = kit.p("tile_wall", "int", lmw=0.6)
    P = kit.p("porcelain", "int", lmw=0.6)
    S = kit.p("steel", "int", lmw=0.3)
    # wainscot on three walls (a thin skin), the grout lines as a dark band at the top
    for (a, b, cc, d) in ((x0, y1 - 0.012, x1, y1), (x0, y0 + 0.06, x0 + 0.012, y1), (x1 - 0.012, y0 + 0.06, x1, y1)):
        Tl.box((a, b, f), (cc, d, f + 1.25), skip="z")
    kit.p("charcoal", "int", lmw=0.2).box((x0, y1 - 0.016, f + 1.25), (x1, y1, f + 1.29))
    xm = (x0 + x1) / 2
    # toilet against the back wall
    tx = x0 + 0.48 if not mirror_x else x1 - 0.48
    P.box((tx - 0.22, y1 - 0.22, f + 0.42), (tx + 0.22, y1 - 0.02, f + 0.8), bevel=0.02)
    P.lathe([(0.0, 0.0), (0.12, 0.0), (0.14, 0.2), (0.19, 0.38), (0.17, 0.42), (0.0, 0.42)], c=(tx, y1 - 0.48), z=f, seg=14)
    kit.p("white", "int", lmw=0.2).lathe([(0.0, 0.0), (0.2, 0.0), (0.21, 0.025), (0.0, 0.025)], c=(tx, y1 - 0.5), z=f + 0.42, seg=14)
    kit.collide((tx - 0.22, y1 - 0.7, f), (tx + 0.22, y1, f + 0.8))
    # grab bars
    gx = x0 + 0.03 if not mirror_x else x1 - 0.03
    S.tube([(gx, y1 - 1.2, f + 0.85), (gx, y1 - 0.15, f + 0.85)], 0.018, sides=6)
    S.tube([(tx - 0.45, y1 - 0.04, f + 0.85), (tx + 0.45, y1 - 0.04, f + 0.85)], 0.018, sides=6)
    # basin on the side wall opposite, mirror over it
    bx = x1 - 0.03 if not mirror_x else x0 + 0.03
    sgn = -1 if not mirror_x else 1
    by = y0 + 0.9
    with kit.at((bx, by, f)):
        P.box((min(0, sgn * 0.5), -0.28, 0.7), (max(0, sgn * 0.5), 0.28, 0.86), bevel=0.03)
        S.tube([(sgn * 0.05, 0.0, 0.86), (sgn * 0.05, 0.0, 1.02), (sgn * 0.22, 0.0, 1.0)], 0.014, sides=6)
        kit.p("chrome", "int", lmw=0.3).box((min(0, sgn * 0.012), -0.3, 1.05), (max(0, sgn * 0.012), 0.3, 1.85))
        # hand dryer and towel dispenser, the bin
        kit.p("lightgrey", "int", lmw=0.2).box((min(0, sgn * 0.18), 0.55, 1.1), (max(0, sgn * 0.18), 0.85, 1.4), bevel=0.03)
        kit.p("graphite", "int", lmw=0.2).box((min(0, sgn * 0.12), 0.45, f + 0.0), (max(0, sgn * 0.42), 0.75, 0.6), bevel=0.02)
    kit.collide((min(bx, bx + sgn * 0.5), by - 0.3, f), (max(bx, bx + sgn * 0.5), by + 0.3, f + 0.86))
    # baby changing station (folded) on the back wall
    cxs = x1 - 0.55 if not mirror_x else x0 + 0.55
    kit.p("lightgrey", "int", lmw=0.2).box((cxs - 0.4, y1 - 0.1, f + 0.9), (cxs + 0.4, y1 - 0.01, f + 1.45), bevel=0.02)
    # light
    kit.light("area", (xm, (y0 + y1) / 2, c - 0.03), size=(0.6, 0.6), energy=16.0, color=(1.0, 0.97, 0.93))
    kit.p("signs", "int").panel((xm, (y0 + y1) / 2, c - 0.005), "z", 0.6, 0.6, cell=kit.cell("signs", "led"))


def stockroom(kit, p, x0, x1, y0, y1, f, c, rng):
    """Steel shelving of cased stock, a mop sink and bucket, a hand truck, a desk with the store's
    second monitor; one bare troffer; the back door (east wall) stands open on the back lot."""
    St = kit.p("graphite", "int", lmw=0.4)
    Gc = kit.group(0)
    # a run of shelving along the west wall (x0) facing +x
    for k in range(2):
        ys = y0 + 0.3 + k * 1.9
        for yy in (ys, ys + 1.8):
            for xx in (x0 + 0.02, x0 + 0.6):
                St.box((xx, yy - 0.02, f), (xx + 0.03, yy + 0.02, f + 2.1))
        for z in (f + 0.15, f + 0.8, f + 1.45, f + 2.05):
            St.box((x0 + 0.02, ys, z), (x0 + 0.63, ys + 1.8, z + 0.03))
            yy = ys + 0.05
            while yy < ys + 1.7:
                d = rng.uniform(0.3, 0.55)
                h = rng.uniform(0.22, 0.5)
                w = rng.uniform(0.28, 0.42)
                if yy + w > ys + 1.75:
                    break
                cell = kit.cell("goods", "cardboard" if rng.random() < 0.6 else "cardboard2")
                kit.p("goods", "int", lmw=0.5, group=Gc).box((x0 + 0.62 - d, yy, z + 0.03), (x0 + 0.62, yy + w, z + 0.03 + min(h, 0.6)), cell=cell, front="X")
                yy += w + 0.02
        kit.collide((x0, ys, f), (x0 + 0.65, ys + 1.8, f + 2.1))
    # the mop sink in the north-east corner, the yellow bucket
    kit.p("concrete_grey", "int", lmw=0.4).box((x1 - 0.7, y1 - 0.7, f), (x1, y1, f + 0.3), bevel=0.02)
    kit.p("steel", "int", lmw=0.1).tube([(x1 - 0.02, y1 - 0.35, f + 0.9), (x1 - 0.2, y1 - 0.35, f + 0.9), (x1 - 0.2, y1 - 0.35, f + 0.8)], 0.015, sides=6)
    kit.p("safety", "int", lmw=0.3).lathe([(0.0, 0.0), (0.18, 0.0), (0.2, 0.32), (0.0, 0.32)], c=(x1 - 1.0, y1 - 0.5), z=f, seg=12)
    kit.p("tan", "int", lmw=0.1).tube([(x1 - 1.0, y1 - 0.5, f + 0.2), (x1 - 0.9, y1 - 0.45, f + 1.4)], 0.012, sides=5)
    kit.collide((x1 - 0.7, y1 - 0.7, f), (x1, y1, f + 0.3))
    # the desk under the window-less south wall, its chair and the monitor (the same four feeds)
    D = kit.p("charcoal", "int", lmw=0.5)
    D.box((x1 - 1.5, y0 + 0.05, f + 0.72), (x1 - 0.05, y0 + 0.75, f + 0.76))
    for (xx, yy) in ((x1 - 1.45, y0 + 0.1), (x1 - 0.1, y0 + 0.1), (x1 - 1.45, y0 + 0.7), (x1 - 0.1, y0 + 0.7)):
        D.box((xx - 0.025, yy - 0.025, f), (xx + 0.025, yy + 0.025, f + 0.72))
    kit.collide((x1 - 1.5, y0 + 0.05, f), (x1 - 0.05, y0 + 0.75, f + 0.76))
    with kit.at((x1 - 0.8, y0 + 0.3, f + 0.76), rot=180):
        monitor(kit, 0.5, 0.3)
    # a stack of the same black plastic crates as in the van, by the back door
    for k in range(3):
        kit.p("black", "int", lmw=0.3).box((x1 - 0.7, y1 - 2.6, f + k * 0.31), (x1 - 0.15, y1 - 2.05, f + 0.3 + k * 0.31), bevel=0.01)
    kit.collide((x1 - 0.7, y1 - 2.6, f), (x1 - 0.15, y1 - 2.05, f + 0.93))
    # a hand truck leaning on the wall
    with kit.at((x0 + 0.95, y1 - 0.3, f), rx=-12):
        kit.p("red", "int", lmw=0.2).tube([(-0.2, 0, 0.05), (-0.2, 0, 1.3), (0.2, 0, 1.3), (0.2, 0, 0.05)], 0.015, sides=6, caps=False)
        kit.p("steel", "int", lmw=0.1).box((-0.22, -0.2, 0.0), (0.22, 0.0, 0.02))
    # light
    kit.light("area", ((x0 + x1) / 2, (y0 + y1) / 2, c - 0.03), size=(0.6, 1.2), energy=22.0, color=(1.0, 0.98, 0.95))
    kit.p("signs", "int").panel(((x0 + x1) / 2, (y0 + y1) / 2, c - 0.005), "z", 0.6, 1.2, cell=kit.cell("signs", "troffer"))


def monitor(kit, w, h, zone="int"):
    """A flat monitor on a foot (faces -y): the security feeds (four cameras)."""
    B = kit.p("black", zone, lmw=0.3)
    B.box((-0.1, -0.08, 0.0), (0.1, 0.08, 0.015))
    B.box((-0.02, 0.0, 0.0), (0.02, 0.03, 0.12 + h / 2))
    B.box((-w / 2 - 0.015, -0.03, 0.12), (w / 2 + 0.015, 0.0, 0.12 + h + 0.015), bevel=0.004)
    kit.p("signs", zone).panel((0, -0.031, 0.12 + h / 2 + 0.008), "y", w, h, cell=kit.cell("signs", "cctv"))


