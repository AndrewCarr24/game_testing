"""The small things (town2_diner.py): table sets on every booth table and along the counter
(chrome napkin dispenser, glass salt and pepper with chrome caps, a sugar pourer, red and yellow
squeeze bottles, a menu card), what the last customers left (cups, a plate, a folded newspaper),
and the turn (design/town/brief.md "The turn": environmental only):
  - the booth nearest the door, east side, where you can see the whole lot: four coffee cups, a
    scanner radio, a sketch of a floor plan on squared paper (the estate's ground floor, a red
    route over the west lawn to the great room's glass) under a plate; under the table two black
    duffel bags, one open on zip ties and a coil of rope; a long hard case on the bench and a white
    hard mask (the invaders') half out of the bag;
  - the waitress's stool, at the counter's east end, turned to face the front door; the wall
    phone's handset off the hook and laid on the counter by the register, its cord stretched;
  - on the kitchen shelf by the pass, a charging dock with four handheld radios."""
import math

import lib.common as common
import town2_diner_geo as G


def build(k, M, p):
    fz = p["fz"]
    tables = p["tables"]
    cahoots = tables[4]                     # the first booth east of the vestibule
    for i, (tx, ty) in enumerate(tables):
        zt = fz + 0.765
        table_set(k, M, p, tx + 0.18, 0.86, zt)
        if i == 4:
            continue
        if i in (1, 6):
            cup(k, M, p, tx - 0.18, ty + 0.15, zt)
            cup(k, M, p, tx + 0.14, ty + 0.3, zt)
        if i == 2:
            plate_left(k, M, p, tx - 0.1, ty + 0.2, zt)
        menu_card(k, M, p, tx - 0.05, 0.82, zt)
    # along the counter: a set every fourth stool, cups where someone just sat
    zc = fz + 0.98
    stools = p["stools"]
    for j, (sx, sy) in enumerate(stools):
        if j % 4 == 1:
            table_set(k, M, p, sx + 0.35, 3.55, zc)
        if j in (3, 9, 10):
            cup(k, M, p, sx, 3.4, zc)
    newspaper(k, M, p, stools[6][0] - 0.2, 3.45, zc)

    # ---------------------------------------------------- the booth by the door
    tx, ty = cahoots
    zt = fz + 0.765
    for dx, dy in ((-0.2, 0.0), (0.2, 0.05), (-0.18, 0.4), (0.22, 0.45)):
        cup(k, M, p, tx + dx, ty + dy, zt)
    # the sketch, weighted by a plate
    a = math.radians(8)
    w, h = 0.36, 0.18
    cx, cy = tx + 0.0, ty + 0.25
    pts = [(cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a), zt + 0.002) for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]
    k.add("Turn_Sketch", G.decal(*pts, "plan"), M["decal"], tile=None)
    k.add("Turn_Pencil", G.tube([(cx + 0.12, cy - 0.12, zt + 0.006), (cx + 0.27, cy - 0.06, zt + 0.006)], 0.0045, n=6), M["paint"], tint=(0.7, 0.5, 0.05), tile=1.0, lm=0.2)
    # a scanner radio (black, a stubby antenna, an amber display)
    rx, ry = tx + 0.22, ty - 0.22
    k.add("Turn_Scanner", G.box_lohi((rx - 0.1, ry - 0.06, zt), (rx + 0.1, ry + 0.06, zt + 0.055), bevel=0.01), M["paint"], tint=(0.02, 0.02, 0.022), tile=1.0)
    k.add("Turn_ScannerFace", G.box_lohi((rx - 0.07, ry + 0.06, zt + 0.02), (rx + 0.0, ry + 0.062, zt + 0.045)), M["globe"], tile=None, bake=False)
    k.add("Turn_ScannerAnt", G.cyl((rx + 0.07, ry - 0.03, zt + 0.12), 0.006, 0.13, n=6), M["paint"], tint=(0.02, 0.02, 0.02), tile=1.0, lm=0.2)
    # under the table: two black duffels, one open on zip ties and a rope coil
    y0 = p["car"]["yi0"]
    duffel(k, M, p, tx - 0.15, y0 + 0.45, 0.0, open_=False)
    duffel(k, M, p, tx + 0.18, y0 + 0.72, 0.5, open_=True)
    # a long hard case on the east bench, a white hard mask on top of it
    bx = tx + 0.62
    k.add("Turn_Case", G.box_lohi((bx - 0.16, y0 + 0.08, fz + 0.47), (bx + 0.14, y0 + 1.1, fz + 0.56), bevel=0.015, seg=2), M["paint"], tint=(0.03, 0.03, 0.03), tile=1.0)
    for yy in (y0 + 0.3, y0 + 0.85):
        k.add("Turn_CaseLatch", G.box_lohi((bx - 0.17, yy - 0.03, fz + 0.5), (bx - 0.155, yy + 0.03, fz + 0.53)), M["chrome"], tile=0.5)
    mask(k, M, p, bx, y0 + 0.62, fz + 0.56)

    # ---------------------------------------------------- the waitress's stool, the phone
    C = p["car"]
    wx, wy = 6.35, 3.05
    k.add("Turn_Stool", G.lathe([(0.001, 0.0), (0.19, 0.0), (0.12, 0.035), (0.045, 0.11)], c=(wx, wy, fz), n=20), M["chrome"], tile=0.5, smooth=True)
    k.add("Turn_StoolPost", G.cyl((wx, wy, fz + 0.36), 0.04, 0.52, n=12, cap=False), M["chrome"], tile=0.5, smooth=True)
    k.add("Turn_StoolSeat", G.lathe([(0.2, 0.0), (0.205, 0.02), (0.2, 0.05), (0.17, 0.075), (0.08, 0.088), (0.001, 0.09)], c=(wx, wy, fz + 0.7), n=24),
          M["paint"], tint=p["vinyl"], tile=1.0, smooth=True)
    k.add("Turn_StoolBand", G.lathe([(0.2, 0.0), (0.205, 0.005), (0.205, 0.045), (0.2, 0.05)], c=(wx, wy, fz + 0.65), n=24), M["chrome"], tile=0.5, smooth=True)
    k.collider((wx - 0.2, wy - 0.2, fz), (wx + 0.2, wy + 0.2, fz + 0.79))
    # her cardigan over the seat, a cup of coffee on the counter's end with lipstick on it
    k.add("Turn_Cardigan", G.box_lohi((wx - 0.18, wy - 0.05, fz + 0.79), (wx + 0.16, wy + 0.2, fz + 0.82), bevel=0.012, seg=2), M["paint"], tint=(0.35, 0.32, 0.28), tile=1.0, smooth=True)
    k.add("Turn_CardiganSleeve", G.tube([(wx + 0.1, wy + 0.18, fz + 0.8), (wx + 0.2, wy + 0.28, fz + 0.6), (wx + 0.22, wy + 0.3, fz + 0.4)], 0.04, n=8), M["paint"], tint=(0.35, 0.32, 0.28), tile=1.0, smooth=True)
    zc = fz + 0.98
    cup(k, M, p, 5.62, 3.34, zc, lip=True)
    # the wall phone by the kitchen door, the handset off the hook on the counter
    px, py, pz = p["kitchen_door"][0] - 0.25, C["yi1"] - 0.02, fz + 1.45
    k.add("Phone_Base", G.box_lohi((px - 0.08, py - 0.08, pz - 0.12), (px + 0.08, py, pz + 0.12), bevel=0.015, seg=2), M["paint"], tint=(0.6, 0.56, 0.46), tile=1.0)
    k.add("Phone_Hook", G.box_lohi((px - 0.03, py - 0.11, pz + 0.04), (px + 0.03, py - 0.08, pz + 0.1)), M["paint"], tint=(0.6, 0.56, 0.46), tile=1.0, lm=0.3)
    for i in range(3):
        for j in range(4):
            k.add("Phone_Key", G.box_lohi((px - 0.04 + i * 0.03, py - 0.085, pz - 0.08 + j * 0.03), (px - 0.02 + i * 0.03, py - 0.08, pz - 0.06 + j * 0.03)), M["paint"], tint=(0.8, 0.78, 0.7), tile=1.0, lm=0.2)
    hx, hy = 5.95, 3.7
    k.add("Phone_Handset", G.tube([(hx - 0.1, hy, zc + 0.03), (hx - 0.06, hy + 0.01, zc + 0.015), (hx + 0.06, hy + 0.01, zc + 0.015), (hx + 0.1, hy, zc + 0.03)], 0.022, n=8), M["paint"],
          tint=(0.6, 0.56, 0.46), tile=1.0, smooth=True)
    # the cord: a coil stretched from the base down, round the counter's end, to the handset
    cord = []
    path = [(px, py - 0.05, pz - 0.12), (px - 0.3, py - 0.4, fz + 1.0), (6.1, 4.2, zc + 0.02), (hx + 0.1, hy, zc + 0.02)]
    for (xa, ya, za), (xb, yb, zb) in zip(path, path[1:]):
        n = int(math.dist((xa, ya, za), (xb, yb, zb)) / 0.012)
        for t in range(n):
            f = t / n
            ang = t * 1.1
            cord.append((xa + (xb - xa) * f + 0.008 * math.cos(ang), ya + (yb - ya) * f + 0.008 * math.sin(ang), za + (zb - za) * f - 0.05 * math.sin(math.pi * f)))
    k.add("Phone_Cord", G.tube(cord, 0.0035, n=4, cap=False), M["paint"], tint=(0.6, 0.56, 0.46), tile=1.0, lm=0.15)

    # ---------------------------------------------------- the radios on the kitchen shelf
    yb = C["yb"]
    sx, sy, sz = 1.7, yb + 0.12, p["pass_z"][0] + 0.34
    k.add("Radio_Dock", G.box_lohi((sx - 0.22, sy - 0.07, sz), (sx + 0.22, sy + 0.07, sz + 0.05), bevel=0.01), M["paint"], tint=(0.03, 0.03, 0.03), tile=1.0)
    for i in range(4):
        rx = sx - 0.165 + i * 0.11
        k.add("Radio", G.box_lohi((rx - 0.03, sy - 0.02, sz + 0.03), (rx + 0.03, sy + 0.03, sz + 0.2), bevel=0.008), M["paint"], tint=(0.025, 0.025, 0.028), tile=1.0)
        k.add("Radio_Ant", G.cyl((rx + 0.015, sy, sz + 0.26), 0.006, 0.12, n=6), M["paint"], tint=(0.02, 0.02, 0.02), tile=1.0, lm=0.2)
        k.add("Radio_Led", G.box_lohi((rx - 0.01, sy - 0.025, sz + 0.035), (rx + 0.0, sy - 0.02, sz + 0.045)), M["neon_red"] if i else M["globe_cool"], tile=None, bake=False)


# ------------------------------------------------------------------ pieces

def table_set(k, M, p, x, y, z):
    """Napkin dispenser, salt and pepper, sugar pourer, ketchup and mustard."""
    k.add("Set_Napkins", G.box_lohi((x - 0.06, y - 0.05, z), (x + 0.06, y + 0.05, z + 0.12), bevel=0.012, seg=2), M["chrome"], tile=0.5)
    k.add("Set_NapkinsPaper", G.box_lohi((x - 0.045, y - 0.051, z + 0.03), (x + 0.045, y + 0.051, z + 0.1)), M["paint"], tint=(0.85, 0.84, 0.8), tile=1.0, lm=0.2)
    for j, (dx, fill) in enumerate(((0.1, (0.85, 0.84, 0.8)), (0.15, (0.12, 0.1, 0.09)))):
        k.add("Set_Shaker", G.lathe([(0.001, 0.0), (0.02, 0.0), (0.022, 0.05), (0.018, 0.065), (0.001, 0.066)], c=(x + dx, y, z), n=8), M["glass"], tile=None, bake=False, smooth=True)
        k.add("Set_ShakerFill", G.cyl((x + dx, y, z + 0.022), 0.017, 0.04, n=8), M["paint"], tint=fill, tile=1.0, lm=0.2)
        k.add("Set_ShakerCap", G.lathe([(0.018, 0.0), (0.019, 0.015), (0.012, 0.025), (0.001, 0.027)], c=(x + dx, y, z + 0.063), n=8), M["chrome"], tile=0.5, smooth=True)
    k.add("Set_Sugar", G.lathe([(0.001, 0.0), (0.033, 0.0), (0.035, 0.09), (0.03, 0.1), (0.001, 0.1)], c=(x - 0.11, y, z), n=10), M["glass"], tile=None, bake=False, smooth=True)
    k.add("Set_SugarFill", G.cyl((x - 0.11, y, z + 0.03), 0.03, 0.06, n=10), M["paint"], tint=(0.85, 0.84, 0.8), tile=1.0, lm=0.2)
    k.add("Set_SugarTop", G.lathe([(0.032, 0.0), (0.033, 0.02), (0.012, 0.045), (0.006, 0.06), (0.001, 0.06)], c=(x - 0.11, y, z + 0.1), n=10), M["chrome"], tile=0.5, smooth=True)
    for j, col in enumerate(((0.45, 0.02, 0.02), (0.75, 0.55, 0.03))):
        bx = x - 0.18 - j * 0.06
        k.add("Set_Bottle", G.lathe([(0.001, 0.0), (0.026, 0.0), (0.028, 0.14), (0.018, 0.17), (0.006, 0.2), (0.001, 0.21)], c=(bx, y, z), n=10), M["paint"], tint=col, tile=1.0, smooth=True, lm=0.3)


def cup(k, M, p, x, y, z, lip=False):
    k.add("Saucer", G.lathe([(0.001, 0.0), (0.06, 0.0), (0.075, 0.012), (0.07, 0.014), (0.001, 0.006)], c=(x, y, z), n=14), M["paint"], tint=(0.8, 0.78, 0.72), tile=1.0, smooth=True, lm=0.25)
    k.add("Cup", G.lathe([(0.001, 0.006), (0.03, 0.006), (0.042, 0.03), (0.045, 0.08), (0.04, 0.08), (0.038, 0.03), (0.001, 0.012)], c=(x, y, z), n=14), M["paint"], tint=(0.8, 0.78, 0.72), tile=1.0, smooth=True, lm=0.25)
    k.add("Cup_Coffee", G.cyl((x, y, z + 0.06), 0.038, 0.004, n=12), M["paint"], tint=(0.05, 0.02, 0.008), tile=1.0, lm=0.2)
    k.add("Cup_Handle", G.tube([(x + 0.044, y, z + 0.07), (x + 0.065, y, z + 0.06), (x + 0.044, y, z + 0.035)], 0.006, n=6), M["paint"], tint=(0.8, 0.78, 0.72), tile=1.0, lm=0.2)
    if lip:
        k.add("Cup_Lipstick", G.box_lohi((x - 0.044, y - 0.012, z + 0.074), (x - 0.04, y + 0.012, z + 0.08)), M["paint"], tint=(0.5, 0.02, 0.04), tile=1.0, lm=0.2)


def plate_left(k, M, p, x, y, z):
    k.add("Plate", G.lathe([(0.001, 0.0), (0.1, 0.0), (0.13, 0.018), (0.125, 0.02), (0.1, 0.006), (0.001, 0.006)], c=(x, y, z), n=18), M["paint"], tint=(0.8, 0.78, 0.72), tile=1.0, smooth=True, lm=0.3)
    k.add("Plate_Crumbs", G.box_lohi((x - 0.04, y - 0.02, z + 0.006), (x + 0.03, y + 0.03, z + 0.009)), M["paint"], tint=(0.5, 0.3, 0.12), tile=1.0, lm=0.2)
    k.add("Fork", G.box_lohi((x + 0.03, y - 0.09, z + 0.012), (x + 0.045, y + 0.08, z + 0.016)), M["chrome"], tile=0.5, lm=0.2)


def menu_card(k, M, p, x, y, z):
    """A laminated menu, folded in a tent behind the napkins (blank laminate: no text)."""
    a = math.radians(70)
    w = 0.2
    h = 0.24
    k.add("Menu_Card", G.quad((x - w / 2, y, z), (x + w / 2, y, z), (x + w / 2, y + h * math.cos(a), z + h * math.sin(a)), (x - w / 2, y + h * math.cos(a), z + h * math.sin(a))),
          M["paint"], tint=(0.45, 0.04, 0.03), tile=1.0, lm=0.3)


def newspaper(k, M, p, x, y, z):
    """A folded newspaper on the counter (grey columns; the masthead a black bar: unreadable)."""
    k.add("Paper", G.box_lohi((x - 0.17, y - 0.14, z), (x + 0.17, y + 0.14, z + 0.012), bevel=0.003), M["paint"], tint=(0.65, 0.64, 0.6), tile=1.0, lm=0.3)
    k.add("Paper_Masthead", G.box_lohi((x - 0.15, y + 0.08, z + 0.012), (x + 0.15, y + 0.12, z + 0.013)), M["paint"], tint=(0.05, 0.05, 0.05), tile=1.0, lm=0.2)
    for i in range(4):
        k.add("Paper_Col", G.box_lohi((x - 0.15 + i * 0.077, y - 0.12, z + 0.012), (x - 0.085 + i * 0.077, y + 0.06, z + 0.013)), M["paint"], tint=(0.5, 0.5, 0.48), tile=1.0, lm=0.2)


def duffel(k, M, p, x, y, rot, open_=False):
    fz = p["fz"]
    bm = G.box_lohi((-0.32, -0.16, 0.0), (0.32, 0.16, 0.3), bevel=0.11, seg=3)
    G.xform(bm, loc=(x, y, fz), rz=rot)
    k.add("Turn_Duffel", bm, M["paint"], tint=(0.018, 0.018, 0.02), tile=1.0, smooth=50)
    # the carry handles: a loop over the top, lying slack
    strap = [(x + 0.2 * math.cos(rot) * s, y + 0.2 * math.sin(rot) * s, fz + 0.3 + (0.1 if abs(s) < 1 else 0.0)) for s in (-1, -0.5, 0, 0.5, 1)]
    k.add("Turn_DuffelStrap", G.tube(common.fillet_polyline(strap, 0.05, 4, False), 0.012, n=6), M["paint"], tint=(0.025, 0.025, 0.028), tile=1.0, smooth=True, lm=0.2)
    if open_:
        # the zip pulled back: a bundle of white zip ties and a coil of rope inside the mouth
        for i in range(6):
            a = rot + 0.3 * i
            k.add("Turn_ZipTie", G.box_lohi((x - 0.12 + 0.02 * i, y - 0.04, fz + 0.29), (x + 0.1 + 0.02 * i, y - 0.03, fz + 0.3)), M["paint"], tint=(0.85, 0.85, 0.82), tile=1.0, lm=0.2)
        coil = [(x + 0.08 + 0.07 * math.cos(t * 0.35), y + 0.03 + 0.07 * math.sin(t * 0.35), fz + 0.27 + 0.004 * t) for t in range(60)]
        k.add("Turn_Rope", G.tube(coil, 0.009, n=5, cap=False), M["paint"], tint=(0.55, 0.45, 0.25), tile=1.0, lm=0.2)


def mask(k, M, p, x, y, z):
    """A white hard mask (the invaders'): a shallow shell, eye holes, lying face up."""
    import bmesh
    bm = bmesh.new()
    nu, nv = 10, 8
    rows = []
    for i in range(nv + 1):
        t = i / nv                      # chin (0) to brow (1) along y
        row = []
        for j in range(nu + 1):
            s = j / nu * 2 - 1          # left to right
            w = 0.085 * math.sqrt(max(0.0, 1 - (2 * t - 1) ** 2 * 0.6))
            px = s * w
            py = (t - 0.5) * 0.22
            pz = 0.055 * (1 - s * s) * (0.7 + 0.3 * math.sin(math.pi * t)) + 0.01
            row.append(bm.verts.new((x + px, y + py, z + pz)))
        rows.append(row)
    for i in range(nv):
        for j in range(nu):
            bm.faces.new([rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]])
    k.add("Turn_Mask", bm, M["paint"], tint=(0.82, 0.82, 0.8), tile=1.0, smooth=60)
    for s in (-1, 1):
        k.add("Turn_MaskEye", G.box_lohi((x + s * 0.035 - 0.018, y + 0.03, z + 0.058), (x + s * 0.035 + 0.018, y + 0.045, z + 0.066)), M["paint"], tint=(0.01, 0.01, 0.01), tile=1.0, lm=0.2)
