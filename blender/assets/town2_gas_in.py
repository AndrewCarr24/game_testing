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
import math

V = None


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
    coolers(kit, q, rng)
    back_rooms(kit, p, q, rng)
    coffee_bar(kit, q, rng)
    fountain(kit, q, rng)
    for gx, kind in ((-12.5, "chips"), (-9.4, "snacks"), (-6.3, "auto")):
        gondola(kit, rng, gx, 6.4, 12.4, kind, f)
    cash_wrap(kit, p, q, rng)
    floor_things(kit, p, q, rng)
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
            kit.light("area", (x, y, c - 0.03), size=(0.6, 1.2), energy=34.0, color=(1.0, 0.97, 0.93))
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


# ------------------------------------------------------------------ the cooler wall
def coolers(kit, q, rng):
    """14 glass doors (y = 15.2) of a walk-in cooler across the north wall from the west wall to
    the restrooms; shelves of drinks behind each (emissive cards), the lit frost header above."""
    f, c = q["f"], q["c"]
    x0, x1, yd, yb = q["X0"], -4.6, 15.2, q["Y1"]
    n = 14
    dw = (x1 - x0) / n
    Bk = kit.p("black", "int", lmw=0.6)
    Gd = kit.p("green_dark", "int", lmw=0.7)
    Gl = kit.p("glass", "int")
    Sg = kit.p("signs", "int")
    Dr = kit.p("drinks", "int")
    Wh = kit.p("white", "int", lmw=0.4)
    # the box: the soffit / header over the doors, the kick plate, the side return
    Gd.box((x0, yd - 0.12, 2.28), (x1, yb, c), skip="Zx")
    Sg.panel(((x0 + x1) / 2, yd - 0.121, 2.52), "y", x1 - x0 - 0.2, 0.26, cell=kit.cell("signs", "frost"))
    Bk.box((x0, yd - 0.05, f), (x1, yd + 0.02, f + 0.2), skip="z")
    Gd.box((x1, yd - 0.12, f), (x1 + 0.1, yb, c), skip="z")
    kit.collide((x0, yd - 0.12, 0), (x1 + 0.1, yb, c))
    # inside the box: back, floor, ceiling (white, lit by its own strips)
    Wh.box((x0, yd + 0.05, f), (x1, yb, f + 0.01), skip="z")
    Wh.box((x0, yb - 0.02, f), (x1, yb, 2.28), skip="zZ")
    Wh.box((x0, yd + 0.05, 2.26), (x1, yb, 2.28), skip="Z")
    drinks = list(kit.cells["drinks"])
    order = ["water", "water2", "sport_b", "sport_r", "sport_y", "cola", "cola_can", "diet", "lemon", "orange", "soda_or",
             "tea", "ice_tea_can", "energy_k", "energy_s", "energy_w", "coffee_can", "protein", "milk", "choc", "juice", "cran",
             "kombucha", "seltzer", "yogurt", "cheese", "sand", "salad", "beer_a", "beer_b", "beer_c", "beer_d"]
    for k in range(n):
        a0, a1 = x0 + k * dw, x0 + (k + 1) * dw
        # mullion, the door's frame and glass, its handle
        Bk.box((a0 - 0.025, yd - 0.06, f + 0.2), (a0 + 0.025, yd + 0.03, 2.28), skip="")
        Gl.box((a0 + 0.045, yd - 0.015, f + 0.26), (a1 - 0.045, yd - 0.008, 2.2), skip="")
        for (b0, b1, z0, z1) in ((a0 + 0.025, a0 + 0.06, f + 0.2, 2.25), (a1 - 0.06, a1 - 0.025, f + 0.2, 2.25),
                                 (a0 + 0.025, a1 - 0.025, f + 0.2, f + 0.27), (a0 + 0.025, a1 - 0.025, 2.19, 2.25)):
            Bk.box((b0, yd - 0.04, z0), (b1, yd - 0.005, z1), skip="")
        hx = a1 - 0.1 if k % 2 == 0 else a0 + 0.1
        kit.p("steel", "int", lmw=0.15).box((hx - 0.012, yd - 0.09, 0.95), (hx + 0.012, yd - 0.06, 1.75))
        for z in (0.98, 1.72):
            kit.p("steel", "int", lmw=0.05).box((hx - 0.008, yd - 0.07, z - 0.01), (hx + 0.008, yd - 0.04, z + 0.01))
        # the LED strip on the mullion (inside)
        Sg.panel((a0 + 0.03, yd + 0.04, 1.25), "y", 0.02, 1.9, cell=kit.cell("signs", "strip"))
        # five shelves: wire shelf, front price strip, two rows of product (cards)
        cat = order[(k * 2) % len(order)]
        for j, z in enumerate((f + 0.3, f + 0.68, f + 1.06, f + 1.44, f + 1.82)):
            key = order[(k * 2 + j // 3) % len(order)] if j < 4 else order[(k * 2 + 1) % len(order)]
            cell = kit.cell("drinks", key)
            kit.p("lightgrey", "int", lmw=0.1).box((a0 + 0.03, yd + 0.06, z - 0.02), (a1 - 0.03, yd + 0.6, z))
            Dr.panel(((a0 + a1) / 2, yd + 0.11, z + 0.165), "y", dw - 0.07, 0.33, cell=cell)
            Dr.panel(((a0 + a1) / 2, yd + 0.45, z + 0.165), "y", dw - 0.07, 0.33, cell=cell)
        # its light (bake): the cooler's glow through the door into the store
        kit.light("area", ((a0 + a1) / 2, yd - 0.03, 1.25), size=(dw - 0.1, 1.9), energy=10.0, color=(0.96, 0.98, 1.0), rot=(-90, 0, 0))
    Bk.box((x1 - 0.025, yd - 0.06, f + 0.2), (x1 + 0.025, yd + 0.03, 2.28), skip="")


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


# ------------------------------------------------------------------ the coffee bar
def coffee_bar(kit, q, rng):
    """Along the west wall (faces +x): oak base cabinets, a quartz top, a white tile backsplash,
    an oak slat wall with three menu boards, the green soffit and its under-light; on the top
    three brewer stations, cup towers, lids, a cappuccino machine, condiments."""
    f, c, X0 = q["f"], q["c"], q["X0"]
    ya, yb = 4.3, 11.4
    d = 0.7
    O = kit.p("oak", "int", lmw=0.7)
    Bk = kit.p("black", "int", lmw=0.3)
    Qz = kit.p("cream", "int", lmw=0.7)
    O.box((X0, ya, f + 0.1), (X0 + d - 0.04, yb, f + 0.88), skip="xz")
    Bk.box((X0, ya, f), (X0 + d - 0.1, yb, f + 0.1), skip="xz")
    n = int((yb - ya) / 0.6)
    for k in range(1, n):
        y = ya + k * (yb - ya) / n
        Bk.box((X0 + d - 0.045, y - 0.003, f + 0.12), (X0 + d - 0.035, y + 0.003, f + 0.86))
    Qz.box((X0, ya - 0.02, f + 0.88), (X0 + d + 0.02, yb + 0.02, f + 0.92), bevel=0.008)
    kit.collide((X0, ya, 0), (X0 + d + 0.02, yb, f + 0.92))
    # backsplash and the slat wall
    kit.p("tile_wall", "int", lmw=0.6).box((X0, ya, f + 0.92), (X0 + 0.012, yb, f + 1.4), skip="x")
    for k in range(int((yb - ya) / 0.08)):
        y = ya + 0.02 + k * 0.08
        O.box((X0, y, f + 1.4), (X0 + 0.03, y + 0.06, 2.4), skip="xzZ")
    kit.p("green_dark", "int", lmw=0.6).box((X0, ya - 0.1, 2.4), (X0 + 0.55, yb + 0.1, c), skip="xZ")
    kit.p("signs", "int").panel((X0 + 0.551, (ya + yb) / 2, 2.4 - 0.001), "z", 0.1, yb - ya - 0.2, cell=kit.cell("signs", "led_warm"))
    kit.light("area", (X0 + 0.45, (ya + yb) / 2, 2.38), size=(0.12, yb - ya - 0.4), energy=26.0, color=(1.0, 0.9, 0.76))
    for k in range(3):
        y = ya + 1.2 + k * 2.35
        Bk.box((X0 + 0.03, y - 0.68, 1.62), (X0 + 0.06, y + 0.68, 2.36), bevel=0.005)
        kit.p("signs", "int").panel((X0 + 0.061, y, 1.99), "X", 1.3, 0.7, cell=kit.cell("signs", f"menu{k}"))
    top = f + 0.92
    # three brewer stations, each: a stainless brewer with two warming decanters, airpots beside
    St = kit.p("steel", "int", lmw=0.5)
    for k in range(3):
        y = ya + 0.9 + k * 2.35
        St.box((X0 + 0.05, y - 0.35, top), (X0 + 0.5, y + 0.35, top + 0.62), bevel=0.012)
        Bk.box((X0 + 0.5, y - 0.33, top + 0.5), (X0 + 0.52, y + 0.33, top + 0.6))
        for s in (-1, 1):
            # a decanter on its plate (dark glass, black handle)
            kit.p("glass_dark", "int").lathe([(0.0, 0.0), (0.075, 0.0), (0.085, 0.08), (0.06, 0.16), (0.045, 0.2), (0.0, 0.2)],
                                             c=(X0 + 0.42, y + s * 0.17), z=top + 0.04, seg=10)
            Bk.box((X0 + 0.36, y + s * 0.17 - 0.06, top), (X0 + 0.5, y + s * 0.17 + 0.06, top + 0.04))
        for j in range(2):
            yy = y + 0.55 + j * 0.24
            St.lathe([(0.0, 0.0), (0.09, 0.0), (0.09, 0.34), (0.06, 0.38), (0.0, 0.38)], c=(X0 + 0.3, yy), z=top, seg=12)
            Bk.box((X0 + 0.3, yy - 0.02, top + 0.32), (X0 + 0.44, yy + 0.02, top + 0.4))
    # cup towers (three sizes), the lid rack, sleeves, stir sticks, condiments
    for k in range(3):
        y = ya + 2.2 + k * 2.35
        for j, (r, n_) in enumerate(((0.045, 18), (0.052, 15), (0.06, 12))):
            yy = y + j * 0.15
            cups = [(r * 0.75, 0.0)] + [(r, 0.02 + 0.03 * i) for i in range(1, 2)] + [(r * 1.05, 0.03 * n_), (0.0, 0.03 * n_)]
            kit.p("cup_white", "int", lmw=0.3).lathe(cups, c=(X0 + 0.55, yy), z=top, seg=10)
        kit.p("black", "int", lmw=0.3).box((X0 + 0.08, y + 0.55, top), (X0 + 0.38, y + 0.95, top + 0.34), bevel=0.01)
        for j in range(4):
            kit.p("lid_black", "int", lmw=0.1).cyl((X0 + 0.22, y + 0.62 + j * 0.09), 0.04, top + 0.34, top + 0.42, seg=8)
        kit.p("tan", "int", lmw=0.2).box((X0 + 0.45, y + 0.6, top), (X0 + 0.6, y + 0.8, top + 0.12), bevel=0.01)
    # the cappuccino machine and the creamer fridge at the north end
    with kit.at((X0, yb - 0.55, top)):
        Bk.box((0.06, -0.3, 0.0), (0.52, 0.3, 0.7), bevel=0.02)
        St.box((0.4, -0.25, 0.25), (0.53, 0.25, 0.62), bevel=0.01)
        kit.p("signs", "int").panel((0.531, 0.0, 0.5), "X", 0.3, 0.12, cell=kit.cell("signs", "pos"))
        for j in range(3):
            St.cyl((0.46, -0.12 + j * 0.12), 0.012, 0.18, 0.26, seg=6)
    with kit.at((X0, ya + 0.35, top)):
        kit.p("white", "int", lmw=0.3).box((0.08, -0.25, 0.0), (0.55, 0.25, 0.45), bevel=0.02)
        kit.p("glass", "int").panel((0.552, 0.0, 0.24), "X", 0.42, 0.34)
        for j in range(3):
            kit.p("cup_white", "int", lmw=0.1).cyl((0.4, -0.15 + j * 0.15), 0.04, 0.05, 0.25, seg=8)


def fountain(kit, q, rng):
    """The fountain and the frozen-drink machine north of the coffee bar (west wall, faces +x)."""
    f, X0 = q["f"], q["X0"]
    ya, yb = 11.6, 14.6
    d = 0.75
    O = kit.p("oak", "int", lmw=0.6)
    O.box((X0, ya, f + 0.1), (X0 + d - 0.04, yb, f + 0.88), skip="xz")
    kit.p("black", "int", lmw=0.3).box((X0, ya, f), (X0 + d - 0.1, yb, f + 0.1), skip="xz")
    kit.p("cream", "int", lmw=0.6).box((X0, ya - 0.02, f + 0.88), (X0 + d + 0.02, yb + 0.02, f + 0.92), bevel=0.008)
    kit.collide((X0, ya, 0), (X0 + d + 0.02, yb, f + 0.92))
    top = f + 0.92
    St = kit.p("steel", "int", lmw=0.6)
    Bk = kit.p("black", "int", lmw=0.4)
    # fountain: a stainless tower, ten valves, the lit merchandiser over it, the drip tray
    St.box((X0 + 0.05, ya + 0.15, top), (X0 + 0.68, ya + 1.55, top + 1.0), bevel=0.015)
    Bk.box((X0 + 0.55, ya + 0.2, top + 0.0), (X0 + 0.72, ya + 1.5, top + 0.06))
    for k in range(10):
        y = ya + 0.27 + k * 0.125
        Bk.box((X0 + 0.66, y - 0.04, top + 0.42), (X0 + 0.72, y + 0.04, top + 0.6), bevel=0.005)
        kit.p("signs", "int").panel((X0 + 0.721, y, top + 0.66), "X", 0.08, 0.08, cell=kit.cell("signs", ["grades", "tickets"][k % 2]))
    Bk.box((X0 + 0.04, ya + 0.12, top + 1.0), (X0 + 0.7, ya + 1.58, top + 1.32), bevel=0.01)
    kit.p("signs", "int").panel((X0 + 0.701, ya + 0.85, top + 1.16), "X", 1.38, 0.28, cell=kit.cell("signs", "menu2"))
    # ice chute
    St.box((X0 + 0.6, ya + 0.75, top + 0.62), (X0 + 0.74, ya + 0.95, top + 0.8), bevel=0.01)
    # the frozen drink machine: two clear bowls of slush
    with kit.at((X0, ya + 2.25, top)):
        St.box((0.05, -0.45, 0.0), (0.65, 0.45, 0.38), bevel=0.015)
        for s, col in ((-1, "red"), (1, "blue")):
            kit.p(col, "int", lmw=0.3).lathe([(0.0, 0.0), (0.13, 0.0), (0.14, 0.25), (0.12, 0.35), (0.0, 0.36)], c=(0.38, s * 0.22), z=0.38, seg=12)
            kit.p("glass", "int").lathe([(0.15, 0.0), (0.16, 0.3), (0.14, 0.42), (0.0, 0.45)], c=(0.38, s * 0.22), z=0.38, seg=12, cap_top=False)
            Bk.box((0.6, s * 0.22 - 0.04, 0.2), (0.68, s * 0.22 + 0.04, 0.32))
        Bk.box((0.05, -0.45, 0.83), (0.62, 0.45, 1.0), bevel=0.01)
        kit.p("signs", "int").panel((0.621, 0.0, 0.915), "X", 0.85, 0.15, cell=kit.cell("signs", "frost"))


# ------------------------------------------------------------------ gondolas
GOODS = {
    "chips": [("bag", 0.21, 0.09, 0.3, 16)],
    "snacks": [("box", 0.17, 0.06, 0.24, 8), ("pouch", 0.15, 0.05, 0.21, 8), ("candy", 0.2, 0.12, 0.2, 8)],
    "auto": [("jug", 0.18, 0.12, 0.29, 8), ("box", 0.15, 0.08, 0.2, 8)],
}


def gondola(kit, rng, x, ya, yb, kind, f, h=1.45):
    """A double-sided gondola along y at x (0.95 deep): base deck, kick plates, the pegboard spine,
    four shelves a side with their price strips and goods, end caps."""
    W = kit.p("white", "int", lmw=0.6)
    L = kit.p("lightgrey", "int", lmw=0.5)
    Bk = kit.p("black", "int", lmw=0.3)
    hd = 0.475
    W.box((x - 0.03, ya, f), (x + 0.03, yb, f + h), skip="z")
    Bk.box((x - hd, ya, f), (x + hd, yb, f + 0.12), skip="z")
    W.box((x - 0.04, ya + 0.01, f + h), (x + 0.04, yb - 0.01, f + h + 0.03), bevel=0.01)
    kit.collide((x - hd, ya, 0), (x + hd, yb, f + h + 0.03))
    zs = [f + 0.12, f + 0.48, f + 0.84, f + 1.2]
    for s in (-1, 1):
        face = "X" if s > 0 else "x"
        for j, z in enumerate(zs):
            depth = 0.42 if j == 0 else 0.38 - 0.03 * j
            L.box((min(x, x + s * depth), ya, z - 0.025), (max(x, x + s * depth), yb, z), skip="")
            W.box((min(x + s * depth, x + s * (depth + 0.012)), ya, z - 0.045), (max(x + s * depth, x + s * (depth + 0.012)), yb, z + 0.01))
            # tags on the strip
            yy = ya + 0.2
            while yy < yb - 0.2:
                kit.p("safety" if rng.random() < 0.3 else "white", "int", lmw=0.05).box(
                    (min(x + s * (depth + 0.012), x + s * (depth + 0.016)), yy, z - 0.035), (max(x + s * (depth + 0.012), x + s * (depth + 0.016)), yy + 0.06, z - 0.005))
                yy += rng.uniform(0.35, 0.6)
            # goods: facings along the shelf
            grp = kit.group(0)
            Gd = kit.p("goods", "int", lmw=0.5, group=grp)
            spec = GOODS[kind]
            sp = spec[(j + (s > 0)) % len(spec)]
            name, gw, gd, gh, ncell = sp
            yy = ya + 0.03
            cell_i = rng.randrange(ncell)
            run = 0
            while yy + gw < yb - 0.03:
                if run <= 0:
                    cell_i = rng.randrange(ncell)
                    run = rng.randint(2, 5)
                run -= 1
                cell = kit.cell("goods", f"{name}{cell_i}")
                hh = gh * rng.uniform(0.92, 1.06)
                if name == "bag":
                    gw = rng.choice((0.19, 0.22, 0.25))
                    hh = gw * 1.35 * rng.uniform(0.95, 1.05)
                    if yy + gw >= yb - 0.03:
                        break
                rows = 3 if depth > 0.3 else 2
                # the front facing, and the rows behind it (only tops and the front are seen)
                fx = x + s * (depth - 0.01)
                bx = x + s * (depth - 0.01 - gd * rows)
                lo = (min(fx, bx), yy, z)
                hi = (max(fx, bx), yy + gw, z + hh)
                Gd.box(lo, hi, cell=cell, front=face, skip="z", bevel=0.02 if name == "bag" else 0.004)
                yy += gw + rng.uniform(0.004, 0.02)
        # the pegboard side of the spine
        W.box((min(x + s * 0.03, x + s * 0.035), ya, zs[0]), (max(x + s * 0.03, x + s * 0.035), yb, f + h), skip="zZ")
    # end caps: a display of cases at each end (water, chips)
    for e, ye in ((-1, ya), (1, yb)):
        W.box((x - hd, min(ye, ye + e * 0.45), f), (x + hd, max(ye, ye + e * 0.45), f + 0.12), skip="z")
        grp = kit.group(1)
        Gd = kit.p("goods", "int", lmw=0.5, group=grp)
        for j, z in enumerate((f + 0.12, f + 0.55, f + 0.98)):
            W.box((x - hd, min(ye, ye + e * 0.42), z - 0.02), (x + hd, max(ye, ye + e * 0.42), z))
            nn = 4
            for k in range(nn):
                gx0 = x - hd + 0.03 + k * (2 * hd - 0.06) / nn
                cell = kit.cell("goods", f"bag{rng.randrange(16)}" if j else f"box{rng.randrange(8)}")
                fy = ye + e * 0.4
                lo = (gx0, min(ye, fy), z)
                hi = (gx0 + (2 * hd - 0.06) / nn - 0.01, max(ye, fy), z + 0.3)
                Gd.box(lo, hi, cell=cell, front="Y" if e > 0 else "y", skip="z")
        kit.collide((x - hd, min(ye, ye + e * 0.45), 0), (x + hd, max(ye, ye + e * 0.45), f + 1.3))


# ------------------------------------------------------------------ the cash wrap
def cash_wrap(kit, p, q, rng):
    f, c, X1 = q["f"], q["c"], q["X1"]
    xa, xb, ya, yb = -0.6, 0.3, 4.2, 8.7
    top = f + 1.0
    O = kit.p("oak", "int", lmw=0.8)
    Bk = kit.p("black", "int", lmw=0.4)
    Qz = kit.p("cream", "int", lmw=0.8)
    # the counter: oak front (vertical boards), black kick, quartz top with an overhang
    O.box((xa, ya, f + 0.1), (xb, yb, top - 0.04), skip="z")
    Bk.box((xa + 0.06, ya + 0.06, f), (xb, yb - 0.06, f + 0.1), skip="z")
    for k in range(int((yb - ya) / 0.15)):
        y = ya + 0.075 + k * 0.15
        kit.p("wood_dark", "int", lmw=0.1).box((xa - 0.004, y - 0.004, f + 0.12), (xa, y + 0.004, top - 0.06))
    Qz.box((xa - 0.05, ya - 0.03, top - 0.04), (xb + 0.02, yb + 0.03, top), bevel=0.008)
    kit.collide((xa - 0.05, ya, 0), (xb, yb, top))
    # the register and the customer's display, the card reader
    with kit.at((-0.1, 6.3, top)):
        Bk.box((-0.15, -0.2, 0.0), (0.15, 0.2, 0.08), bevel=0.01)
        with kit.at((0.08, 0.0, 0.08), ry=-20):
            Bk.box((-0.02, -0.19, 0.0), (0.02, 0.19, 0.3), bevel=0.008)
            kit.p("signs", "int").panel((0.021, 0.0, 0.15), "X", 0.34, 0.25, cell=kit.cell("signs", "pos"))
        Bk.box((-0.45, -0.08, 0.0), (-0.33, 0.08, 0.05), bevel=0.01)
        with kit.at((-0.4, 0.0, 0.05), ry=25):
            Bk.box((-0.04, -0.06, 0.0), (0.0, 0.06, 0.14))
            kit.p("signs", "int").panel((-0.041, 0.0, 0.09), "x", 0.09, 0.07, cell=kit.cell("signs", "lotto_screen"))
        # a small impulse rack on the counter (lighters, mints)
        kit.p("goods", "int", lmw=0.3).box((-0.42, 0.3, 0.0), (-0.22, 0.55, 0.12), cell=kit.cell("goods", "candy3"), front="x")
    # the scratch-ticket case (lit, glass front) at the south end
    with kit.at((-0.15, 4.75, top)):
        Bk.box((-0.25, -0.4, 0.0), (0.25, 0.4, 0.06))
        for k in range(4):
            kit.p("signs", "int").panel((-0.2, -0.3 + k * 0.2, 0.18), "x", 0.17, 0.24, cell=kit.cell("signs", "tickets"))
        kit.p("glass", "int").box((-0.24, -0.39, 0.06), (0.24, 0.39, 0.34), skip="z")
    # the lottery terminal (north of the register)
    with kit.at((-0.05, 7.25, top), rot=180):
        Bk.box((-0.18, -0.15, 0.0), (0.18, 0.15, 0.12), bevel=0.01)
        with kit.at((0.0, 0.0, 0.12), ry=15):
            Bk.box((-0.02, -0.14, 0.0), (0.02, 0.14, 0.22))
            kit.p("signs", "int").panel((-0.021, 0.0, 0.11), "x", 0.25, 0.18, cell=kit.cell("signs", "lotto_screen"))
    # the roller grill under its sneeze guard (north end) with the bun warmer under it
    with kit.at((-0.2, 8.1, top)):
        St = kit.p("steel", "int", lmw=0.5)
        St.box((-0.35, -0.5, 0.0), (0.35, 0.5, 0.22), bevel=0.01)
        St.box((-0.34, -0.48, 0.22), (0.34, 0.48, 0.24))
        for k in range(10):
            yr = -0.42 + k * 0.093
            with kit.at((0.0, yr, 0.27), ry=90):
                kit.p("darksteel", "int", lmw=0.1).cyl((0, 0), 0.016, -0.3, 0.3, seg=8, caps="none")
            if k % 2 == 0 or rng.random() < 0.4:
                with kit.at((rng.uniform(-0.08, 0.08), yr + 0.0, 0.305), ry=90):
                    kit.p("sausage", "int", lmw=0.2).cyl((0, 0), 0.016, -0.08, 0.08, seg=8)
        kit.p("glass", "int").box((-0.38, -0.52, 0.46), (0.3, 0.52, 0.48), skip="")
        kit.p("glass", "int").box((-0.4, -0.52, 0.24), (-0.38, 0.52, 0.47), skip="")
        for s in (-1, 1):
            St.box((-0.4, s * 0.52 - 0.01, 0.0), (0.3, s * 0.52 + 0.01, 0.48))
        kit.light("area", (0.0, 0.0, 0.44), size=(0.5, 0.9), energy=6.0, color=(1.0, 0.75, 0.5))
    # the lottery jackpot sign over the counter (hung on rods, both faces)
    with kit.at((-0.25, 6.4, 2.65)):
        Bk.box((-0.04, -0.6, -0.18), (0.04, 0.6, 0.18), bevel=0.01)
        kit.p("signs", "int").panel((-0.041, 0.0, 0.0), "x", 1.1, 0.32, cell=kit.cell("signs", "lotto"))
        kit.p("signs", "int").panel((0.041, 0.0, 0.0), "X", 1.1, 0.32, cell=kit.cell("signs", "lotto"))
        for s in (-1, 1):
            kit.p("steel", "int", lmw=0.05).tube([(0, s * 0.5, 0.18), (0, s * 0.5, c - 2.65)], 0.006, sides=4, caps=False)
    # the impulse candy rack on the customer face
    grp = kit.group(0)
    for j, z in enumerate((f + 0.25, f + 0.5, f + 0.75)):
        kit.p("charcoal", "int", lmw=0.2).box((xa - 0.22, 4.4, z - 0.02), (xa, 7.4, z))
        yy = 4.45
        while yy < 7.3:
            kit.p("goods", "int", lmw=0.4, group=grp).box((xa - 0.2, yy, z), (xa - 0.02, yy + 0.18, z + 0.2), cell=kit.cell("goods", f"candy{rng.randrange(8)}"), front="x", skip="z")
            yy += 0.19
    kit.collide((xa - 0.22, 4.4, 0), (xa, 7.4, f + 0.95))
    # behind: the back counter, the tobacco wall, the monitor, the CB radio
    bx0 = X1 - 0.62
    kit.p("charcoal", "int", lmw=0.6).box((bx0, 3.6, f), (X1, 9.45, f + 0.86), skip="zX")
    Qz.box((bx0 - 0.02, 3.6, f + 0.86), (X1, 9.45, f + 0.9), bevel=0.006)
    kit.collide((bx0, 3.6, 0), (X1, 9.45, f + 0.9))
    for k in range(1, 6):
        y = 3.6 + k * (9.45 - 3.6) / 6
        Bk.box((bx0 - 0.004, y - 0.004, f + 0.1), (bx0, y + 0.004, f + 0.84))
    tw0, tw1 = 4.0, 8.6
    Bk.box((X1 - 0.3, tw0 - 0.05, f + 1.05), (X1, tw1 + 0.05, f + 2.55), skip="X")
    grp = kit.group(0)
    for r in range(6):
        z = f + 1.1 + r * 0.22
        for k in range(int((tw1 - tw0) / 0.5)):
            y = tw0 + 0.02 + k * 0.5
            kit.p("goods", "int", lmw=0.4, group=grp).box((X1 - 0.31, y, z), (X1 - 0.3, y + 0.48, z + 0.2), cell=kit.cell("goods", f"pack{(r * 3 + k) % 8}"), front="x")
    kit.p("signs", "int").panel((X1 - 0.31, (tw0 + tw1) / 2, f + 2.45), "x", tw1 - tw0 - 0.1, 0.08, cell=kit.cell("signs", "led"))
    kit.light("area", (X1 - 0.6, (tw0 + tw1) / 2, f + 2.3), size=(0.2, tw1 - tw0), energy=14.0, color=(1.0, 0.96, 0.9), rot=(0, 60, 0))
    # the security monitor on its arm over the back counter's north end, facing the store
    with kit.at((X1 - 0.12, 9.05, f + 1.75), rot=-90):
        kit.p("black", "int", lmw=0.2).box((-0.03, 0.0, 0.25), (0.03, 0.12, 0.31))
        monitor(kit, 0.72, 0.41)
    # the CB radio on the back counter: the set, its mic on a coiled cord, a power supply; a mug
    with kit.at((X1 - 0.3, 9.0, f + 0.9), rot=-90):
        R = kit.p("black", "int", lmw=0.3)
        R.box((-0.1, -0.12, 0.0), (0.1, 0.12, 0.06), bevel=0.006)
        kit.p("chrome", "int", lmw=0.1).box((-0.095, -0.121, 0.008), (0.095, -0.12, 0.052))
        kit.p("graphite", "int", lmw=0.2).box((0.14, -0.1, 0.0), (0.3, 0.08, 0.1), bevel=0.006)
        with kit.at((-0.16, -0.08, 0.0), rx=0):
            R.box((-0.025, -0.02, 0.0), (0.025, 0.02, 0.11), bevel=0.01)
        coil = [(-0.12 + 0.012 * math.cos(a * 1.3), -0.13 + 0.004 * a, 0.03 + 0.012 * math.sin(a * 1.3)) for a in range(14)]
        kit.p("black", "int", lmw=0.05).tube(coil, 0.004, sides=4)
        kit.p("black", "int", lmw=0.05).tube([(0.05, 0.12, 0.05), (0.08, 0.2, 0.3), (0.06, 0.22, 1.3)], 0.004, sides=4, caps=False)
        kit.p("cup_white", "int", lmw=0.1).lathe([(0.0, 0.0), (0.04, 0.0), (0.042, 0.1), (0.0, 0.1)], c=(0.25, 0.3), seg=10, cap_top=False)
    # the clerk's anti-fatigue mat
    kit.p("mat", "int", lmw=0.3).box((0.4, 4.0, f), (bx0 - 0.1, 8.8, f + 0.012), skip="z")
    kit.mark("clerk", (1.6, 6.4, f))


def floor_things(kit, p, q, rng):
    f = q["f"]
    # the walk-off mat inside the entry, the ATM, the ice cream chest, a stack of water cases, the
    # wet-floor sign
    d0, d1 = p["door"]
    kit.p("mat", "int", lmw=0.4).box((d0 - 0.3, q["Y0"], f), (d1 + 0.3, q["Y0"] + 1.6, f + 0.012), skip="z")
    with kit.at((-2.2, 13.13, f), rot=180):
        A = kit.p("charcoal", "int", lmw=0.6)
        A.box((-0.32, -0.3, 0.0), (0.32, 0.25, 1.45), bevel=0.02)
        kit.p("black", "int", lmw=0.3).box((-0.28, -0.34, 0.95), (0.28, -0.3, 1.35))
        kit.p("signs", "int").panel((0.0, -0.341, 1.15), "y", 0.3, 0.2, cell=kit.cell("signs", "atm"))
        kit.p("steel", "int", lmw=0.1).box((-0.25, -0.42, 0.85), (0.25, -0.3, 0.9))
        kit.collide((-0.32, -0.42, 0), (0.32, 0.25, 1.45))
    with kit.at((-3.2, 4.1, f)):
        W = kit.p("white", "int", lmw=0.6)
        W.box((-0.8, -0.32, 0.0), (0.8, 0.32, 0.82), bevel=0.02)
        kit.p("glass", "int").box((-0.76, -0.28, 0.82), (0.76, 0.28, 0.84), skip="z")
        grp = kit.group(2)
        for k in range(6):
            for j in range(2):
                kit.p("goods", "int", lmw=0.3, group=grp).box((-0.72 + k * 0.24, -0.24 + j * 0.25, 0.62), (-0.52 + k * 0.24, -0.04 + j * 0.25, 0.78),
                                                                cell=kit.cell("goods", f"box{rng.randrange(8)}"), front="Z")
        kit.light("area", (0.0, 0.0, 0.8), size=(1.4, 0.5), energy=3.0, color=(0.9, 0.95, 1.0))
        kit.collide((-0.8, -0.32, 0), (0.8, 0.32, 0.84))
    with kit.at((-4.3, 7.2, f)):
        for lvl in range(3):
            for k in range(2):
                for j in range(2):
                    kit.p("blue", "int", lmw=0.3).box((k * 0.42, j * 0.3, lvl * 0.25), (k * 0.42 + 0.4, j * 0.3 + 0.28, lvl * 0.25 + 0.24), bevel=0.02)
        kit.collide((0, 0, 0), (0.82, 0.58, 0.75))
    with kit.at((-14.2, 5.0, f), rot=30):
        Y = kit.p("safety", "int", lmw=0.3)
        with kit.at((0, 0, 0), rx=12):
            Y.box((-0.15, -0.015, 0.0), (0.15, 0.0, 0.62))
        with kit.at((0, 0.26, 0), rx=-12):
            Y.box((-0.15, 0.0, 0.0), (0.15, 0.015, 0.62))
