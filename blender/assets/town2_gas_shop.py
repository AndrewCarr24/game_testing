"""The store's fixtures at full detail (town2_gas_in.interior() calls them): the cooler wall, the
gondolas, the coffee bar, the fountain, the cash wrap (POS, lottery, roller grill, impulse racks,
the tobacco wall, the security monitor, the CB radio) and the floor's odds and ends.

Products come from town2_gas_goods (real shapes on the packaging atlas); stainless and chrome are
metals (palette "brushed", "steel", "chrome": lit by the store's box-projected panorama), screens and
lit panels are the sign atlas, the cooler doors carry the frost texture.
"""
import math

import town2_gas_goods as GD


def _rb(kit, mat, zone="int", lmw=0.6):
    return kit.p(mat, zone, lmw=lmw)


def cord(kit, pts, r=0.004, zone="int"):
    kit.p("black", zone, lmw=0.05).tube(GD_smooth(pts), r, sides=5, caps=False)


def GD_smooth(pts):
    import town2_gas_out as OUT
    return OUT.smooth_path(pts, 3)


def knob(kit, x, y, z, facing="y", r=0.014, zone="int"):
    rot = {"y": 0, "x": -90, "X": 90, "Y": 180}[facing]
    with kit.at((x, y, z), rot=rot, rx=90):
        kit.p("black", zone, lmw=0.05).cyl((0, 0), r, 0.0, 0.018, seg=10)
        kit.p("chrome", zone, lmw=0.05).cyl((0, 0), r * 0.4, 0.018, 0.022, seg=6)


# ------------------------------------------------------------------ the cooler wall
COOLER_DOORS = [  # per door: shelf kinds bottom -> top
    ["case", "bottle", "bottle", "bottle", "bottle"],            # water and sports
    ["case", "bottle", "bottle", "bottle", "bottle"],
    ["case", "can", "bottle", "bottle", "bottle"],                # soda
    ["case", "can", "can", "bottle", "bottle"],
    ["tallcan", "tallcan", "tallcan", "tallcan", "can"],          # energy
    ["tallcan", "tallcan", "can", "can", "can"],
    ["carton", "jug", "carton", "carton", "bottle"],              # dairy and juice
    ["carton", "carton", "bottle", "bottle", "bottle"],
    ["bottle", "bottle", "bottle", "bottle", "bottle"],           # tea
    ["case", "case", "case", "can", "can"],                       # beer
    ["case", "case", "case", "can", "can"],
    ["case", "case", "tallcan", "can", "can"],
    ["jar", "carton", "box_s", "box_s", "carton"],                # grab-and-go
    ["case", "bottle", "bottle", "bottle", "bottle"],
]


def coolers(kit, q, rng):
    """14 glass doors (y = 15.2) of the walk-in cooler across the north wall: black frames, frosted
    glass, chrome handles, a heater strip; behind each door five wire shelves of real product (two
    rows deep), price rails, LED strips on the mullions; the lit frost header above."""
    f, c = q["f"], q["c"]
    x0, x1, yd, yb = q["X0"], -4.6, 15.2, q["Y1"]
    n = len(COOLER_DOORS)
    dw = (x1 - x0) / n
    Bk = _rb(kit, "black", lmw=0.6)
    Gd = _rb(kit, "green_dark", lmw=0.7)
    Sg = kit.p("signs", "int")
    Fr = kit.p("frost", "int")
    Wh = _rb(kit, "white", lmw=0.5)
    # the box: soffit / header, kick plate, side return, the inside (white, lit by its strips)
    Gd.box((x0, yd - 0.12, 2.28), (x1, yb, c), skip="Zx")
    Sg.panel(((x0 + x1) / 2, yd - 0.125, 2.52), "y", x1 - x0 - 0.2, 0.26, cell=kit.cell("signs", "frost"))
    Bk.box((x0, yd - 0.05, f), (x1, yd + 0.02, f + 0.2), skip="z", bevel=0.006)
    Gd.box((x1, yd - 0.12, f), (x1 + 0.1, yb, c), skip="z")
    kit.collide((x0, yd - 0.12, 0), (x1 + 0.1, yb, c))
    Wh.box((x0, yd + 0.05, f), (x1, yb, f + 0.01), skip="z")
    Wh.box((x0, yb - 0.02, f), (x1, yb, 2.28), skip="zZ")
    Wh.box((x0, yd + 0.05, 2.26), (x1, yb, 2.28), skip="Z")
    zs = [f + 0.26, f + 0.64, f + 1.02, f + 1.4, f + 1.78]
    for k in range(n):
        a0, a1 = x0 + k * dw, x0 + (k + 1) * dw
        # mullion with its LED strip (inside), the door's frame, frosted glass, the handle
        Bk.box((a0 - 0.025, yd - 0.06, f + 0.2), (a0 + 0.025, yd + 0.03, 2.28), skip="", bevel=0.004)
        Sg.panel((a0 + 0.027, yd + 0.035, 1.25), "X", 0.012, 1.9, cell=kit.cell("signs", "strip"))
        Fr.face([(a0 + 0.045, yd - 0.012, f + 0.26), (a1 - 0.045, yd - 0.012, f + 0.26), (a1 - 0.045, yd - 0.012, 2.2), (a0 + 0.045, yd - 0.012, 2.2)],
                [(0, 0), (1, 0), (1, 1), (0, 1)])
        for (b0, b1, z0, z1) in ((a0 + 0.025, a0 + 0.06, f + 0.2, 2.25), (a1 - 0.06, a1 - 0.025, f + 0.2, 2.25),
                                 (a0 + 0.025, a1 - 0.025, f + 0.2, f + 0.27), (a0 + 0.025, a1 - 0.025, 2.19, 2.25)):
            Bk.box((b0, yd - 0.04, z0), (b1, yd - 0.005, z1), skip="", bevel=0.003)
        hx = a1 - 0.1 if k % 2 == 0 else a0 + 0.1
        Ch = _rb(kit, "chrome", lmw=0.15)
        Ch.cyl((hx, yd - 0.075), 0.012, 0.95, 1.75, seg=10, caps="both")
        for z in (0.97, 1.73):
            with kit.at((hx, yd - 0.04, z), rx=90):
                Ch.cyl((0, 0), 0.008, 0.0, 0.035, seg=6, caps="none")
        # shelves: a wire deck on brackets, a price rail, two rows of product
        kinds = COOLER_DOORS[k]
        for j, z in enumerate(zs):
            L = _rb(kit, "lightgrey", lmw=0.15)
            L.box((a0 + 0.035, yd + 0.06, z - 0.018), (a1 - 0.035, yd + 0.6, z - 0.008))
            for b in range(1, 8):
                xx = a0 + 0.035 + b * (dw - 0.07) / 8
                L.box((xx - 0.002, yd + 0.06, z - 0.008), (xx + 0.002, yd + 0.6, z - 0.004))
            with kit.at((a0 + 0.04, yd + 0.065, z - 0.004)):
                GD.tag_rail(kit, dw - 0.08, 0.0, y=-0.004)
                kind = kinds[j]
                ks = [kind] if kind != "case" else ["case"]
                GD.row(kit, rng, dw - 0.08, 0.5, ks, group_axis=1, rows=2, gap=0.08, back_lod=True, slump=False)
        # (bake) the strips light the product; the glow spills through the door into the store
        kit.light("area", ((a0 + a1) / 2, yd + 0.02, 1.2), size=(dw - 0.12, 1.9), energy=9.0, color=(0.95, 0.98, 1.0), rot=(90, 0, 0))
        kit.light("area", ((a0 + a1) / 2, yd - 0.03, 1.25), size=(dw - 0.1, 1.9), energy=5.0, color=(0.94, 0.97, 1.0), rot=(-90, 0, 0))
    Bk.box((x1 - 0.025, yd - 0.06, f + 0.2), (x1 + 0.025, yd + 0.03, 2.28), skip="")


# ------------------------------------------------------------------ gondolas
SHELF_KINDS = {
    "chips": [["case"], ["bag_m", "bag_s"], ["bag_m"], ["bag_m", "box_c"]],
    "snacks": [["box_c", "jar"], ["candy", "pouch"], ["box_s", "pouch"], ["box_c"]],
    "auto": [["jug"], ["jug", "box_s"], ["can", "jar", "box_s"], ["box_c", "box_s"]],
}


def gondola(kit, rng, x, ya, yb, kind, f, h=1.45):
    """A double-sided gondola along y at x (0.95 deep): base decks, kick plates, uprights, the
    pegboard spine, four shelves a side with price rails and product, end caps of cases."""
    W = _rb(kit, "white", lmw=0.6)
    L = _rb(kit, "lightgrey", lmw=0.5)
    Bk = _rb(kit, "black", lmw=0.3)
    Dc = kit.p("decals", "int")
    hd = 0.475
    W.box((x - 0.03, ya, f), (x + 0.03, yb, f + h), skip="z")
    Bk.box((x - hd + 0.02, ya, f), (x + hd - 0.02, yb, f + 0.1), skip="z", bevel=0.004)
    n_up = max(2, round((yb - ya) / 1.2)) + 1
    for k in range(n_up):
        yy = ya + k * (yb - ya) / (n_up - 1)
        yy = min(max(yy, ya + 0.025), yb - 0.025)
        L.box((x - 0.05, yy - 0.025, f), (x + 0.05, yy + 0.025, f + h + 0.04), bevel=0.004)
    W.box((x - 0.04, ya + 0.01, f + h), (x + 0.04, yb - 0.01, f + h + 0.03), bevel=0.008)
    kit.collide((x - hd, ya, 0), (x + hd, yb, f + h + 0.04))
    zs = [f + 0.12, f + 0.48, f + 0.84, f + 1.2]
    for s in (-1, 1):
        for j, z in enumerate(zs):
            depth = 0.44 if j == 0 else 0.4 - 0.03 * j
            L.box((min(x, x + s * depth), ya + 0.03, z - 0.025), (max(x, x + s * depth), yb - 0.03, z), bevel=0.003)
            # product: the shelf frame (local +x along the shelf, front at -y facing out)
            if s > 0:
                at, rot = (x + depth, ya + 0.04, z), 90
            else:
                at, rot = (x - depth, yb - 0.04, z), -90
            with kit.at(at, rot=rot):
                GD.tag_rail(kit, yb - ya - 0.08, 0.0, y=-0.014)
                kinds = SHELF_KINDS[kind][j]
                GD.row(kit, rng, yb - ya - 0.08, depth - 0.05, kinds, group_axis=0, rows=3 if j < 3 else 1)
                if j == 3:
                    # dust on the top shelf's back (nobody reaches there)
                    Dc.face([(0.0, 0.25, 0.002), (yb - ya - 0.08, 0.25, 0.002), (yb - ya - 0.08, depth - 0.02, 0.002), (0.0, depth - 0.02, 0.002)],
                            _cellq(kit.cells["decals"]["dust"]))
        W.box((min(x + s * 0.03, x + s * 0.035), ya, zs[0]), (max(x + s * 0.03, x + s * 0.035), yb, f + h), skip="zZ")
    Dc.face([(x - 0.04, ya + 0.02, f + h + 0.032), (x + 0.04, ya + 0.02, f + h + 0.032), (x + 0.04, yb - 0.02, f + h + 0.032), (x - 0.04, yb - 0.02, f + h + 0.032)],
            _cellq(kit.cells["decals"]["dust"]))
    # end caps: a deck, two shelves of chips over a stack of water cases
    for e, ye in ((-1, ya), (1, yb)):
        W.box((x - hd, min(ye, ye + e * 0.46), f), (x + hd, max(ye, ye + e * 0.46), f + 0.1), skip="z", bevel=0.004)
        for z in (f + 0.95, f + 1.3):
            L.box((x - hd, min(ye, ye + e * 0.4), z - 0.02), (x + hd, max(ye, ye + e * 0.4), z), bevel=0.003)
        rot = 0 if e < 0 else 180
        x_from = x - hd + 0.02 if e < 0 else x + hd - 0.02
        for lvl in range(3):
            with kit.at((x_from, ye + e * 0.42, f + 0.1 + lvl * 0.13), rot=rot):
                GD.row(kit, rng, 2 * hd - 0.04, 0.4, ["case"], group_axis=1, rows=1, gap=0.0)
        for z in (f + 0.95, f + 1.3):
            with kit.at((x_from, ye + e * 0.38, z), rot=rot):
                GD.row(kit, rng, 2 * hd - 0.04, 0.34, ["bag_m"], group_axis=1, rows=2, gap=0.05)
                GD.tag_rail(kit, 2 * hd - 0.04, 0.0, y=-0.024)
        kit.collide((x - hd, min(ye, ye + e * 0.46), 0), (x + hd, max(ye, ye + e * 0.46), f + 1.3))


def _cellq(cell):
    u0, v0, u1, v1 = cell
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


# ------------------------------------------------------------------ the coffee bar
def brewer(kit, rng):
    """A twin-warmer commercial brewer (Bunn-like), its front facing +x: brushed stainless
    tower, the black brew funnels under the hood, two decanters on the warmers, the control strip."""
    St = _rb(kit, "brushed", lmw=0.6)
    Bk = _rb(kit, "black", lmw=0.4)
    St.box((0.05, -0.2, 0.0), (0.5, 0.2, 0.03), bevel=0.006)                     # base plate
    St.box((0.05, -0.2, 0.03), (0.24, 0.2, 0.62), bevel=0.01)                    # the tower
    St.box((0.05, -0.2, 0.62), (0.48, 0.2, 0.7), bevel=0.012)                    # the hood
    Bk.box((0.24, -0.19, 0.6), (0.47, 0.19, 0.62))
    kit.p("signs", "int").panel((0.481, 0.0, 0.66), "X", 0.3, 0.05, cell=kit.cell("signs", "pos"))
    for s in (-1, 1):
        yy = s * 0.095
        Bk.box((0.26, yy - 0.08, 0.5), (0.44, yy + 0.08, 0.6), bevel=0.012)      # the funnel
        Bk.box((0.44, yy - 0.015, 0.54), (0.52, yy + 0.015, 0.56), bevel=0.005)   # its handle
        Bk.cyl((0.36, yy), 0.075, 0.03, 0.037, seg=14)                           # the warmer
        # the decanter (glass, a black lid and handle; the second has an orange collar: decaf)
        kit.p("glass_dark", "int").lathe([(0.0, 0.0), (0.06, 0.0), (0.075, 0.03), (0.08, 0.08), (0.06, 0.15), (0.045, 0.17), (0.05, 0.19), (0.0, 0.19)],
                                         c=(0.36, yy), z=0.037, seg=12, cap_top=False)
        kit.p("black" if s < 0 else "orange", "int", lmw=0.1).cyl((0.36, yy), 0.052, 0.21, 0.235, seg=12)
        kit.p("black", "int", lmw=0.1).tube([(0.36, yy + 0.05 * s, 0.2), (0.36, yy + 0.1 * s, 0.17), (0.36, yy + 0.1 * s, 0.09), (0.36, yy + 0.065 * s, 0.07)], 0.009, sides=5)
    cord(kit, [(0.1, 0.15, 0.3), (0.06, 0.24, 0.15), (0.03, 0.3, 0.0)])


def airpot(kit):
    St = _rb(kit, "brushed", lmw=0.4)
    St.lathe([(0.0, 0.0), (0.085, 0.0), (0.09, 0.02), (0.09, 0.3), (0.075, 0.33), (0.0, 0.34)], seg=12, cap_top=False)
    kit.p("black", "int", lmw=0.1).lathe([(0.0, 0.34), (0.07, 0.34), (0.065, 0.38), (0.0, 0.39)], seg=10)
    kit.p("black", "int", lmw=0.1).box((0.0, -0.02, 0.38), (0.11, 0.02, 0.4), bevel=0.006)   # the pump lever
    kit.p("black", "int", lmw=0.1).tube([(0.085, 0.0, 0.31), (0.13, 0.0, 0.3), (0.14, 0.0, 0.26)], 0.012, sides=6)


def cup_tower(kit, r, n, key="cups"):
    """A stack of nested paper cups (rims every few cups; the cell's lines draw the rest)."""
    top = 0.08 + (n - 1) * 0.025
    prof = [(r * 0.72, 0.0)]
    for k in range(5):
        z = 0.08 + (top - 0.08) * k / 4
        prof += [(r * 0.98, z - 0.004), (r * 1.04, z)]
    prof += [(0.0, top + 0.002)]
    kit.p("goods", "int", lmw=0.3).lathe(prof, seg=10, cell=kit.cell("goods", key))


def coffee_bar(kit, q, rng):
    """Along the west wall (faces +x): oak base cabinets with pulls, a bevelled quartz top, a white
    subway-tile splash, the oak slat wall and three menu boards, the green soffit and its light;
    three brewers, airpots, cup towers, lid caddies, a cappuccino machine, a creamer fridge."""
    f, c, X0 = q["f"], q["c"], q["X0"]
    ya, yb = 4.3, 11.4
    d = 0.7
    O = _rb(kit, "oak", lmw=0.7)
    Bk = _rb(kit, "black", lmw=0.3)
    Qz = _rb(kit, "cream", lmw=0.7)
    Bk.box((X0, ya, f), (X0 + d - 0.1, yb, f + 0.1), skip="xz")
    n = int((yb - ya) / 0.6)
    Og = kit.p("oak", "int", lmw=0.8, group=kit.group(0))
    for k in range(n):
        y0, y1 = ya + k * (yb - ya) / n, ya + (k + 1) * (yb - ya) / n
        Og.box((X0, y0 + 0.003, f + 0.1), (X0 + d - 0.04, y1 - 0.003, f + 0.87), skip="xz", bevel=0.004)
        _rb(kit, "steel", lmw=0.1).box((X0 + d - 0.04, (y0 + y1) / 2 - 0.08, f + 0.76), (X0 + d - 0.02, (y0 + y1) / 2 + 0.08, f + 0.78), bevel=0.004)
    Qz.box((X0, ya - 0.02, f + 0.87), (X0 + d + 0.02, yb + 0.02, f + 0.91), bevel=0.01, seg=2)
    kit.collide((X0, ya, 0), (X0 + d + 0.02, yb, f + 0.91))
    top = f + 0.91
    # subway tile (white swatch with dark joints as thin boxes), the slat wall above
    kit.p("tile_wall", "int", lmw=0.6).box((X0, ya, top), (X0 + 0.012, yb, f + 1.42), skip="x")
    for k in range(1, 7):
        _rb(kit, "grout", lmw=0.05).box((X0 + 0.012, ya, top + k * 0.073 - 0.002), (X0 + 0.014, yb, top + k * 0.073))
    for k in range(int((yb - ya) / 0.08)):
        y = ya + 0.02 + k * 0.08
        O.box((X0, y, f + 1.42), (X0 + 0.03, y + 0.06, 2.4), skip="xzZ")
    kit.p("green_dark", "int", lmw=0.6).box((X0, ya - 0.1, 2.4), (X0 + 0.55, yb + 0.1, c), skip="xZ")
    kit.p("signs", "int").panel((X0 + 0.552, (ya + yb) / 2, 2.4 - 0.003), "z", 0.06, yb - ya - 0.2, cell=kit.cell("signs", "led_warm"))
    kit.light("area", (X0 + 0.45, (ya + yb) / 2, 2.38), size=(0.12, yb - ya - 0.4), energy=22.0, color=(1.0, 0.9, 0.76))
    for k in range(3):
        y = ya + 1.2 + k * 2.35
        Bk.box((X0 + 0.03, y - 0.68, 1.62), (X0 + 0.06, y + 0.68, 2.36), bevel=0.006)
        kit.p("signs", "int").panel((X0 + 0.063, y, 1.99), "X", 1.3, 0.7, cell=kit.cell("signs", f"menu{k}"))
    for k in range(3):
        y = ya + 0.85 + k * 2.35
        with kit.at((X0, y, top)):
            brewer(kit, rng)
        for j in range(2):
            with kit.at((X0 + 0.24, y + 0.5 + j * 0.24, top)):
                airpot(kit)
    # cups, lids, sleeves, the condiment caddy, a trash cutout
    for k in range(3):
        y = ya + 2.1 + k * 2.35
        for j, (r, n_) in enumerate(((0.042, 16), (0.048, 14), (0.055, 12))):
            with kit.at((X0 + 0.56, y + j * 0.14, top)):
                cup_tower(kit, r, n_)
        with kit.at((X0 + 0.08, y + 0.5, top)):
            Bk.box((0.0, 0.0, 0.0), (0.3, 0.42, 0.3), bevel=0.01)
            for a in range(2):
                for b in range(2):
                    kit.p("lid_black", "int", lmw=0.1).cyl((0.08 + a * 0.14, 0.11 + b * 0.2), 0.045, 0.3, 0.38, seg=10)
        with kit.at((X0 + 0.4, y + 0.62, top)):
            kit.p("black", "int", lmw=0.2).box((0.0, 0.0, 0.0), (0.2, 0.3, 0.06), bevel=0.006)
            for a in range(3):
                for b in range(4):
                    kit.p(["white", "safety", "blue", "red"][b], "int", lmw=0.05).box((0.02 + a * 0.06, 0.02 + b * 0.07, 0.01), (0.07 + a * 0.06, 0.08 + b * 0.07, 0.07))
        kit.p("black", "int", lmw=0.1).cyl((X0 + 0.5, y + 1.05), 0.07, top - 0.002, top + 0.004, seg=14, caps="top")
    # the cappuccino machine (black, a stainless face, four spouts, a grated drip tray, lit buttons)
    with kit.at((X0, yb - 0.55, top)):
        _rb(kit, "charcoal", lmw=0.5).box((0.06, -0.3, 0.0), (0.52, 0.3, 0.72), bevel=0.02, seg=2)
        St = _rb(kit, "brushed", lmw=0.4)
        St.box((0.5, -0.26, 0.28), (0.54, 0.26, 0.64), bevel=0.01)
        kit.p("signs", "int").panel((0.541, 0.0, 0.55), "X", 0.32, 0.1, cell=kit.cell("signs", "pos"))
        for j in range(4):
            St.cyl((0.47, -0.15 + j * 0.1), 0.012, 0.2, 0.28, seg=8)
        St.box((0.3, -0.26, 0.02), (0.56, 0.26, 0.05), bevel=0.004)
        for j in range(10):
            Bk.box((0.31, -0.24 + j * 0.05, 0.05), (0.55, -0.23 + j * 0.05, 0.052))
        cord(kit, [(0.08, 0.25, 0.3), (0.04, 0.33, 0.1), (0.02, 0.35, 0.0)])
    # the creamer fridge (glass door, little cartons)
    with kit.at((X0, ya + 0.35, top)):
        _rb(kit, "white", lmw=0.3).box((0.08, -0.25, 0.0), (0.55, 0.25, 0.45), bevel=0.012)
        kit.p("glass", "int").panel((0.553, 0.0, 0.24), "X", 0.42, 0.34)
        with kit.at((0.5, -0.2, 0.08), rot=90):
            GD.row(kit, rng, 0.4, 0.3, ["carton"], group_axis=0, rows=1, gap=0.0)
        kit.light("area", (0.4, 0.0, 0.4), size=(0.3, 0.3), energy=1.5, color=(0.95, 0.98, 1.0))


def fountain(kit, q, rng):
    """The fountain and the frozen-drink machine north of the coffee bar (west wall, faces +x)."""
    f, X0 = q["f"], q["X0"]
    ya, yb = 11.6, 14.6
    d = 0.75
    O = _rb(kit, "oak", lmw=0.6)
    O.box((X0, ya, f + 0.1), (X0 + d - 0.04, yb, f + 0.87), skip="xz", bevel=0.004)
    _rb(kit, "black", lmw=0.3).box((X0, ya, f), (X0 + d - 0.1, yb, f + 0.1), skip="xz")
    _rb(kit, "cream", lmw=0.6).box((X0, ya - 0.02, f + 0.87), (X0 + d + 0.02, yb + 0.02, f + 0.91), bevel=0.01, seg=2)
    kit.collide((X0, ya, 0), (X0 + d + 0.02, yb, f + 0.91))
    top = f + 0.91
    St = _rb(kit, "brushed", lmw=0.6)
    Bk = _rb(kit, "black", lmw=0.4)
    St.box((X0 + 0.05, ya + 0.15, top), (X0 + 0.66, ya + 1.55, top + 1.0), bevel=0.015, seg=2)
    St.box((X0 + 0.5, ya + 0.2, top), (X0 + 0.74, ya + 1.5, top + 0.03), bevel=0.006)
    for j in range(24):
        Bk.box((X0 + 0.52, ya + 0.22 + j * 0.053, top + 0.03), (X0 + 0.72, ya + 0.235 + j * 0.053, top + 0.032))
    for k in range(8):
        y = ya + 0.3 + k * 0.13
        St.box((X0 + 0.64, y - 0.04, top + 0.42), (X0 + 0.71, y + 0.04, top + 0.62), bevel=0.008)
        kit.p("black", "int", lmw=0.1).box((X0 + 0.7, y - 0.012, top + 0.34), (X0 + 0.73, y + 0.012, top + 0.44), bevel=0.004)
        kit.p("signs", "int").panel((X0 + 0.712, y, top + 0.56), "X", 0.06, 0.06, cell=kit.cell("signs", ["grades", "tickets"][k % 2]))
    Bk.box((X0 + 0.04, ya + 0.12, top + 1.0), (X0 + 0.7, ya + 1.58, top + 1.32), bevel=0.01)
    kit.p("signs", "int").panel((X0 + 0.703, ya + 0.85, top + 1.16), "X", 1.38, 0.28, cell=kit.cell("signs", "menu2"))
    St.box((X0 + 0.6, ya + 0.72, top + 0.62), (X0 + 0.74, ya + 0.98, top + 0.82), bevel=0.01)
    with kit.at((X0 + 0.58, ya + 1.75, top)):
        for j, r in enumerate((0.045, 0.052, 0.06)):
            with kit.at((0, j * 0.15, 0)):
                cup_tower(kit, r, 14, key="cups")
    with kit.at((X0, ya + 2.35, top)):
        St.box((0.05, -0.45, 0.0), (0.65, 0.45, 0.38), bevel=0.015, seg=2)
        for s, col in ((-1, "red"), (1, "blue")):
            kit.p(col, "int", lmw=0.3).lathe([(0.0, 0.0), (0.13, 0.0), (0.14, 0.25), (0.12, 0.35), (0.0, 0.36)], c=(0.38, s * 0.22), z=0.38, seg=14)
            kit.p("glass", "int").lathe([(0.15, 0.0), (0.16, 0.3), (0.14, 0.42), (0.0, 0.45)], c=(0.38, s * 0.22), z=0.38, seg=14, cap_top=False)
            Bk.box((0.6, s * 0.22 - 0.04, 0.2), (0.68, s * 0.22 + 0.04, 0.32), bevel=0.006)
        Bk.box((0.05, -0.45, 0.83), (0.62, 0.45, 1.0), bevel=0.01)
        kit.p("signs", "int").panel((0.623, 0.0, 0.915), "X", 0.85, 0.15, cell=kit.cell("signs", "frost"))
        cord(kit, [(0.1, 0.4, 0.2), (0.04, 0.48, 0.05), (0.02, 0.5, -0.0)])


# ------------------------------------------------------------------ the cash wrap
def pos_station(kit):
    """The register: a touch monitor on its stand (screen lit), the customer display, a receipt
    printer with its paper, the cash drawer under the top, the card terminal on a pole, cables to
    a grommet. Clerk on +x, customer on -x."""
    Bk = _rb(kit, "black", lmw=0.4)
    Gr = _rb(kit, "graphite", lmw=0.4)
    Bk.box((-0.1, -0.12, 0.0), (0.1, 0.12, 0.015), bevel=0.006)
    Bk.box((-0.02, -0.03, 0.015), (0.02, 0.03, 0.18), bevel=0.006)
    with kit.at((0.02, 0.0, 0.2), ry=-18):
        Bk.box((-0.025, -0.2, -0.02), (0.0, 0.2, 0.27), bevel=0.008)
        kit.p("signs", "int").panel((0.003, 0.0, 0.125), "X", 0.37, 0.25, cell=kit.cell("signs", "pos"))
    with kit.at((-0.06, 0.0, 0.16), ry=20):
        Bk.box((-0.015, -0.1, -0.01), (0.0, 0.1, 0.11), bevel=0.005)
        kit.p("signs", "int").panel((-0.018, 0.0, 0.05), "x", 0.17, 0.1, cell=kit.cell("signs", "lotto_screen"))
    with kit.at((0.05, 0.3, 0.0)):
        Gr.box((-0.08, -0.08, 0.0), (0.08, 0.08, 0.12), bevel=0.012)
        _rb(kit, "white", lmw=0.1).box((-0.04, -0.081, 0.08), (0.04, -0.079, 0.14))
    # the card terminal on its pole (customer side)
    with kit.at((-0.32, -0.25, 0.0)):
        _rb(kit, "chrome", lmw=0.1).cyl((0, 0), 0.012, 0.0, 0.14, seg=8)
        with kit.at((0, 0, 0.14), ry=35):
            Bk.box((-0.04, -0.045, 0.0), (0.0, 0.045, 0.16), bevel=0.008)
            kit.p("signs", "int").panel((-0.042, 0.0, 0.11), "x", 0.07, 0.06, cell=kit.cell("signs", "atm"))
            for r_ in range(3):
                for c_ in range(3):
                    Gr.box((-0.044, -0.03 + c_ * 0.022, 0.02 + r_ * 0.022), (-0.04, -0.012 + c_ * 0.022, 0.036 + r_ * 0.022))
    # cables into the grommet
    cord(kit, [(0.0, 0.0, 0.05), (0.08, 0.05, 0.01), (0.15, 0.1, 0.002)])
    cord(kit, [(0.05, 0.3, 0.05), (0.1, 0.2, 0.01), (0.15, 0.1, 0.002)])
    cord(kit, [(-0.32, -0.25, 0.02), (-0.1, -0.1, 0.004), (0.15, 0.1, 0.002)])
    Bk.cyl((0.15, 0.1), 0.03, 0.0, 0.004, seg=12, caps="top")


def roller_grill(kit, rng):
    """A ten-roller grill (brushed stainless, chrome rollers, hot dogs and taquitos), the control
    knobs, the drip pan, its sneeze guard; the bun warmer drawer under it. Faces -x."""
    St = _rb(kit, "brushed", lmw=0.5)
    Ch = _rb(kit, "chrome", lmw=0.1)
    St.box((-0.36, -0.5, 0.0), (0.34, 0.5, 0.18), bevel=0.012, seg=2)                 # bun warmer
    _rb(kit, "black", lmw=0.1).box((-0.365, -0.15, 0.08), (-0.35, 0.15, 0.1), bevel=0.004)
    kit.p("glass_dark", "int").panel((-0.362, 0.0, 0.12), "x", 0.4, 0.05)
    St.box((-0.36, -0.5, 0.18), (0.34, 0.5, 0.3), bevel=0.01)                          # the grill's body
    for j in range(2):
        knob(kit, -0.36, -0.35 + j * 0.7, 0.24, facing="x")
    for k in range(10):
        yr = -0.41 + k * 0.091
        with kit.at((0.0, yr, 0.33), ry=90):
            Ch.cyl((0, 0), 0.017, -0.3, 0.3, seg=10, caps="both")
        if rng.random() < 0.75:
            col = "sausage" if k < 6 else "bun"
            for j in range(2 if k < 6 else 3):
                xx = -0.15 + j * 0.2 + rng.uniform(-0.03, 0.03)
                with kit.at((xx, yr + 0.045, 0.36), ry=90):
                    L = 0.075 if k < 6 else 0.06
                    r = 0.014 if k < 6 else 0.012
                    kit.p(col, "int", lmw=0.15).lathe([(0.0, -L), (r * 0.7, -L + 0.004), (r, -L + 0.015), (r, L - 0.015), (r * 0.7, L - 0.004), (0.0, L)], seg=8)
    # the sneeze guard: a sloped glass lid on stainless posts
    G = kit.p("glass", "int")
    G.face([(-0.38, -0.52, 0.42), (-0.38, 0.52, 0.42), (0.22, 0.52, 0.56), (0.22, -0.52, 0.56)])
    G.face([(0.22, -0.52, 0.56), (0.22, 0.52, 0.56), (-0.38, 0.52, 0.42), (-0.38, -0.52, 0.42)])
    for s in (-1, 1):
        St.box((-0.39, s * 0.52 - 0.01, 0.3), (0.24, s * 0.52 + 0.01, 0.57), skip="")
    kit.light("area", (0.0, 0.0, 0.5), size=(0.5, 0.9), energy=5.0, color=(1.0, 0.72, 0.45))
    cord(kit, [(0.3, 0.45, 0.1), (0.4, 0.55, 0.02), (0.45, 0.6, 0.0)])


def wire_rack(kit, rng, w, levels, depth=0.22, zone="int"):
    """A chrome wire impulse rack (stepped tiers of product), faces -y, base at 0."""
    Ch = _rb(kit, "chrome", zone, lmw=0.1)
    for s in (-1, 1):
        Ch.tube([(s * w / 2, depth, 0.0), (s * w / 2, depth, 0.08 + levels * 0.11), (s * w / 2, 0.0, 0.05)], 0.004, sides=4, caps=False)
    for k in range(levels):
        z = 0.03 + k * 0.11
        y0 = depth * (1 - (k + 1) / (levels + 0.5))
        Ch.tube([(-w / 2, y0, z), (w / 2, y0, z)], 0.003, sides=4, caps=False)
        Ch.tube([(-w / 2, y0 + 0.06, z + 0.04), (w / 2, y0 + 0.06, z + 0.04)], 0.003, sides=4, caps=False)
        with kit.at((-w / 2, y0, z)):
            GD.row(kit, rng, w, 0.08, ["candy"], group_axis=1, rows=1, gap=0.0, slump=False)


def cash_wrap(kit, p, q, rng):
    f, c, X1 = q["f"], q["c"], q["X1"]
    xa, xb, ya, yb = -0.6, 0.3, 4.2, 8.7
    top = f + 1.0
    O = _rb(kit, "oak", lmw=0.8)
    Bk = _rb(kit, "black", lmw=0.4)
    Qz = _rb(kit, "cream", lmw=0.8)
    # the counter: oak boards (proud, bevelled), a black kick, a bevelled quartz top with an overhang
    O.box((xa + 0.01, ya, f + 0.1), (xb, yb, top - 0.04), skip="z")
    n = int((yb - ya) / 0.15)
    Og = kit.p("oak", "int", lmw=0.8, group=kit.group(0))
    for k in range(n):
        y0 = ya + k * (yb - ya) / n
        Og.box((xa - 0.006, y0 + 0.003, f + 0.11), (xa + 0.012, y0 + (yb - ya) / n - 0.003, top - 0.05), bevel=0.003, skip="X")
    Bk.box((xa + 0.06, ya + 0.06, f), (xb, yb - 0.06, f + 0.1), skip="z")
    Qz.box((xa - 0.06, ya - 0.03, top - 0.04), (xb + 0.02, yb + 0.03, top), bevel=0.01, seg=2)
    kit.collide((xa - 0.06, ya, 0), (xb, yb, top))
    with kit.at((-0.12, 6.3, top)):
        pos_station(kit)
    with kit.at((xb - 0.05, 6.3, top - 0.16)):
        _rb(kit, "graphite", lmw=0.3).box((-0.2, -0.22, 0.0), (0.0, 0.22, 0.11), bevel=0.006)    # cash drawer
    # the scratch-ticket case (lit, acrylic) at the south end
    with kit.at((-0.18, 4.75, top)):
        Bk.box((-0.25, -0.42, 0.0), (0.25, 0.42, 0.05), bevel=0.006)
        for k in range(4):
            kit.p("signs", "int").panel((-0.2, -0.31 + k * 0.205, 0.19), "x", 0.17, 0.26, cell=kit.cell("signs", "tickets"))
        kit.p("glass", "int").box((-0.24, -0.41, 0.05), (0.24, 0.41, 0.35), skip="z")
        _rb(kit, "chrome", lmw=0.1).box((-0.245, -0.415, 0.345), (0.245, 0.415, 0.355))
    # the lottery terminal, a stepped impulse rack, a lighter display
    with kit.at((-0.05, 7.2, top), rot=180):
        Bk.box((-0.18, -0.15, 0.0), (0.18, 0.15, 0.12), bevel=0.012)
        with kit.at((0.0, 0.0, 0.12), ry=15):
            Bk.box((-0.02, -0.14, 0.0), (0.02, 0.14, 0.22), bevel=0.006)
            kit.p("signs", "int").panel((-0.022, 0.0, 0.11), "x", 0.25, 0.18, cell=kit.cell("signs", "lotto_screen"))
        cord(kit, [(0.1, 0.1, 0.05), (0.2, 0.18, 0.004), (0.3, 0.2, 0.0)])
    with kit.at((-0.45, 5.55, top), rot=-90):
        wire_rack(kit, rng, 0.4, 3)
    with kit.at((-0.4, 7.55, top), rot=-90):
        GD.row(kit, rng, 0.2, 0.15, ["candy"], group_axis=0, rows=1, gap=0.0)
    with kit.at((-0.2, 8.15, top)):
        roller_grill(kit, rng)
    # the jackpot sign over the counter (hung on rods, both faces)
    with kit.at((-0.25, 6.4, 2.65)):
        Bk.box((-0.04, -0.6, -0.18), (0.04, 0.6, 0.18), bevel=0.012)
        kit.p("signs", "int").panel((-0.042, 0.0, 0.0), "x", 1.1, 0.32, cell=kit.cell("signs", "lotto"))
        kit.p("signs", "int").panel((0.042, 0.0, 0.0), "X", 1.1, 0.32, cell=kit.cell("signs", "lotto"))
        for s in (-1, 1):
            _rb(kit, "chrome", lmw=0.05).tube([(0, s * 0.5, 0.18), (0, s * 0.5, c - 2.65)], 0.005, sides=4, caps=False)
    # the impulse candy shelves on the customer face (three, with price rails)
    for j, z in enumerate((f + 0.22, f + 0.47, f + 0.72)):
        _rb(kit, "charcoal", lmw=0.2).box((xa - 0.24, 4.4, z - 0.02), (xa - 0.006, 7.4, z), bevel=0.003)
        with kit.at((xa - 0.24, 7.38, z), rot=-90):
            GD.row(kit, rng, 2.96, 0.2, ["candy", "box_s"] if j else ["candy"], group_axis=0, rows=1, gap=0.04)
            GD.tag_rail(kit, 2.96, 0.0, y=-0.004, h=0.03)
    kit.collide((xa - 0.24, 4.4, 0), (xa, 7.4, f + 0.95))
    # behind: the back counter (doors, pulls), the tobacco wall, the monitor, the CB radio
    bx0 = X1 - 0.62
    _rb(kit, "charcoal", lmw=0.6).box((bx0, 3.6, f), (X1, 9.45, f + 0.86), skip="zX")
    Qz.box((bx0 - 0.02, 3.6, f + 0.86), (X1, 9.45, f + 0.9), bevel=0.008)
    kit.collide((bx0, 3.6, 0), (X1, 9.45, f + 0.9))
    for k in range(6):
        y0 = 3.6 + k * (9.45 - 3.6) / 6
        Bk.box((bx0 - 0.004, y0 + 0.004, f + 0.1), (bx0, y0 + (9.45 - 3.6) / 6 - 0.004, f + 0.84))
        _rb(kit, "steel", lmw=0.05).box((bx0 - 0.025, y0 + 0.4, f + 0.7), (bx0 - 0.005, y0 + 0.56, f + 0.72), bevel=0.004)
    tw0, tw1 = 4.0, 8.6
    Bk.box((X1 - 0.29, tw0 - 0.05, f + 1.05), (X1, tw1 + 0.05, f + 2.55), skip="X", bevel=0.006)
    grp = kit.group(0)
    for r in range(6):
        z = f + 1.1 + r * 0.22
        _rb(kit, "charcoal", lmw=0.1).box((X1 - 0.32, tw0, z - 0.012), (X1 - 0.29, tw1, z))
        for k in range(int((tw1 - tw0) / 0.3)):
            y = tw0 + 0.02 + k * 0.3
            kit.p("goods", "int", lmw=0.4, group=grp).box((X1 - 0.31, y, z), (X1 - 0.3, y + 0.28, z + 0.19), cell=kit.cell("goods", f"pack{(r + k) % 4}"), front="x")
    kit.p("signs", "int").panel((X1 - 0.322, (tw0 + tw1) / 2, f + 2.45), "x", tw1 - tw0 - 0.1, 0.06, cell=kit.cell("signs", "led"))
    kit.light("area", (X1 - 0.6, (tw0 + tw1) / 2, f + 2.3), size=(0.2, tw1 - tw0), energy=12.0, color=(1.0, 0.96, 0.9), rot=(0, 60, 0))
    import town2_gas_in as IN
    with kit.at((X1 - 0.12, 9.05, f + 1.75), rot=-90):
        _rb(kit, "black", lmw=0.2).box((-0.03, 0.0, 0.25), (0.03, 0.12, 0.31))
        IN.monitor(kit, 0.72, 0.41)
    cord(kit, [(X1 - 0.1, 9.1, f + 1.95), (X1 - 0.05, 9.12, f + 1.4), (X1 - 0.05, 9.15, f + 0.9)])
    cb_radio(kit, (X1 - 0.3, 9.0, f + 0.9))
    kit.p("mat", "int", lmw=0.3).box((0.4, 4.0, f), (bx0 - 0.1, 8.8, f + 0.012), skip="z", bevel=0.004)
    kit.mark("clerk", (1.6, 6.4, f))


def cb_radio(kit, at):
    """The CB set on the back counter (faces -x, toward the clerk): a chrome-faced mobile rig with
    its dials and meter, the mic on its hook and coiled cord, a power supply, the coax up the wall."""
    with kit.at(at, rot=-90):
        R = _rb(kit, "black", lmw=0.3)
        R.box((-0.1, -0.12, 0.0), (0.1, 0.12, 0.06), bevel=0.006)
        _rb(kit, "chrome", lmw=0.1).box((-0.097, -0.122, 0.006), (0.097, -0.12, 0.054))
        for k in range(4):
            knob(kit, -0.07 + k * 0.045, -0.124, 0.03, facing="y", r=0.008)
        kit.p("signs", "int").panel((0.06, -0.1235, 0.035), "y", 0.04, 0.02, cell=kit.cell("signs", "led_warm"))
        _rb(kit, "graphite", lmw=0.2).box((0.14, -0.1, 0.0), (0.3, 0.08, 0.1), bevel=0.008)
        kit.p("signs", "int").panel((0.22, -0.101, 0.07), "y", 0.03, 0.012, cell=kit.cell("signs", "grades"))
        with kit.at((-0.16, -0.08, 0.0)):
            R.box((-0.028, -0.02, 0.0), (0.028, 0.02, 0.11), bevel=0.012)
        coil = [(-0.12 + 0.012 * math.cos(a * 1.3), -0.13 + 0.004 * a, 0.03 + 0.012 * math.sin(a * 1.3)) for a in range(16)]
        kit.p("black", "int", lmw=0.05).tube(coil, 0.004, sides=4)
        kit.p("black", "int", lmw=0.05).tube([(0.05, 0.12, 0.05), (0.08, 0.2, 0.3), (0.06, 0.22, 1.3)], 0.005, sides=4, caps=False)
        kit.p("cup_white", "int", lmw=0.1).lathe([(0.0, 0.0), (0.04, 0.0), (0.042, 0.1), (0.0, 0.1)], c=(0.25, 0.3), seg=10, cap_top=False)
        kit.p("cup_white", "int", lmw=0.1).tube([(0.29, 0.3, 0.075), (0.31, 0.3, 0.055), (0.29, 0.3, 0.025)], 0.006, sides=4)


# ------------------------------------------------------------------ the floor's odds and ends
def floor_things(kit, p, q, rng):
    f = q["f"]
    d0, d1 = p["door"]
    # the walk-off mat inside the entry: a rubber border round a charcoal pile field
    with kit.at(((d0 + d1) / 2, q["Y0"] + 0.85, f)):
        kit.p("black", "int", lmw=0.3).box((-1.5, -0.8, 0.0), (1.5, 0.8, 0.008), skip="z", bevel=0.004)
        kit.p("mat", "int", lmw=0.4).box((-1.42, -0.72, 0.0), (1.42, 0.72, 0.011), skip="z")
    # the ATM between the restroom doors
    with kit.at((-2.2, 13.13, f), rot=180):
        A = _rb(kit, "charcoal", lmw=0.6)
        A.box((-0.32, -0.3, 0.0), (0.32, 0.25, 1.45), bevel=0.025, seg=2)
        _rb(kit, "black", lmw=0.3).box((-0.28, -0.34, 0.95), (0.28, -0.3, 1.35), bevel=0.01)
        kit.p("signs", "int").panel((0.0, -0.342, 1.15), "y", 0.3, 0.2, cell=kit.cell("signs", "atm"))
        _rb(kit, "brushed", lmw=0.1).box((-0.25, -0.42, 0.85), (0.25, -0.3, 0.9), bevel=0.01)
        for r_ in range(4):
            for c_ in range(3):
                _rb(kit, "lightgrey", lmw=0.05).box((-0.1 + c_ * 0.04, -0.425 + r_ * 0.025, 0.9), (-0.07 + c_ * 0.04, -0.405 + r_ * 0.025, 0.905))
        kit.collide((-0.32, -0.42, 0), (0.32, 0.25, 1.45))
    # the ice-cream chest freezer under the window (sliding glass lids, product from above)
    with kit.at((-3.2, 4.1, f)):
        W = _rb(kit, "white", lmw=0.6)
        W.box((-0.8, -0.32, 0.0), (0.8, 0.32, 0.82), bevel=0.02, seg=2)
        Fr = kit.p("frost", "int")
        for k in (-1, 1):
            Fr.face([(k * 0.38 - 0.39, -0.29, 0.83 + 0.006 * (k > 0)), (k * 0.38 + 0.39, -0.29, 0.83 + 0.006 * (k > 0)),
                     (k * 0.38 + 0.39, 0.29, 0.83 + 0.006 * (k > 0)), (k * 0.38 - 0.39, 0.29, 0.83 + 0.006 * (k > 0))], [(0, 0), (1, 0), (1, 1), (0, 1)])
        grp = kit.group(2)
        for k in range(6):
            for j in range(2):
                kit.p("goods", "int", lmw=0.3, group=grp).box((-0.72 + k * 0.24, -0.24 + j * 0.25, 0.6), (-0.52 + k * 0.24, -0.04 + j * 0.25, 0.76),
                                                                cell=kit.cell("goods", f"box{rng.randrange(8)}"), front="Z", bevel=0.004)
        kit.light("area", (0.0, 0.0, 0.8), size=(1.4, 0.5), energy=2.0, color=(0.9, 0.95, 1.0))
        kit.collide((-0.8, -0.32, 0), (0.8, 0.32, 0.84))
    # a pallet-stack of water cases by the counter
    with kit.at((-4.3, 7.2, f)):
        for lvl in range(3):
            with kit.at((0.0, 0.0, lvl * 0.13)):
                GD.row(kit, rng, 0.82, 0.8, ["case"], group_axis=1, rows=2, gap=0.0)
        kit.collide((0, 0, 0), (0.82, 0.8, 0.4))
    # the wet-floor sign by the coffee bar
    with kit.at((-14.2, 5.0, f), rot=30):
        Y = _rb(kit, "safety", lmw=0.3)
        with kit.at((0, 0, 0), rx=12):
            Y.box((-0.15, -0.015, 0.0), (0.15, 0.0, 0.62), bevel=0.01)
        with kit.at((0, 0.26, 0), rx=-12):
            Y.box((-0.15, 0.0, 0.0), (0.15, 0.015, 0.62), bevel=0.01)
    # wear: scuffs fanning in from the door, gum, grime at the wall base by the entry
    Dc = kit.p("decals", "int")
    for k in range(7):
        cx, cy = (d0 + d1) / 2 + rng.uniform(-1.4, 1.4), q["Y0"] + 2.0 + k * 0.9 + rng.uniform(-0.2, 0.2)
        decal(Dc, kit, cx, cy, f + 0.003, rng.uniform(0.8, 1.6), rng.uniform(0.5, 1.0), rng.uniform(0, 180), f"scuff{rng.randrange(4)}")
    for (cx, cy) in ((-1.2, 6.4), (-2.0, 6.0), (-13.8, 8.0), (-14.0, 11.0)):          # at the counter, the coffee bar
        decal(Dc, kit, cx, cy, f + 0.003, 1.4, 0.9, rng.uniform(0, 180), f"scuff{rng.randrange(4)}")
    # grime along the wall base inside the entry (faces +y) and under the restroom doors' wall (-y)
    g = kit.cells["decals"]["grime"]
    u0, v0, u1, v1 = g
    for (cx, cy, w, s) in ((-11.8, q["Y0"] + 0.004, 5.6, 1), (-2.15, 13.33, 4.6, -1)):
        if s > 0:
            Dc.face([(cx + w / 2, cy, f), (cx - w / 2, cy, f), (cx - w / 2, cy, f + 0.3), (cx + w / 2, cy, f + 0.3)], [(u1, v1), (u0, v1), (u0, v0), (u1, v0)])
        else:
            Dc.face([(cx - w / 2, cy, f), (cx + w / 2, cy, f), (cx + w / 2, cy, f + 0.3), (cx - w / 2, cy, f + 0.3)], [(u0, v1), (u1, v1), (u1, v0), (u0, v0)])


def decal(Dc, kit, cx, cy, z, w, h, rot, key):
    """A floor (or ground) decal: a w x h rectangle at (cx, cy), turned rot degrees."""
    a = math.radians(rot)
    ca, sa = math.cos(a), math.sin(a)
    pts = [(cx + ca * u - sa * v, cy + sa * u + ca * v, z) for u, v in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]
    Dc.face(pts, _cellq(kit.cells["decals"][key]))
