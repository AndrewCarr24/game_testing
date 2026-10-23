"""The diner's lot (town2_diner.py): asphalt off the highway with head-in stalls facing the car
(white stripes, concrete wheel stops, an accessible stall), stone-edged planters along the road
between the two driveways, the pylon sign at the road (neon DINER over a chaser arrow, OPEN in
blue), the roof sign on the car, the concrete walk with a bench, planters and a bike staple, the
service yard behind (a board-fenced dumpster enclosure, the grease bin), the parked cars
(town2_diner_cars.py)."""
import math

import lib.common as common
import town2_diner_geo as G

# single-stroke neon glyphs on a 0.6 x 1.0 cell (I is narrow): lists of polylines
GLYPHS = {
    "D": [[(0, 0), (0, 1), (0.32, 1), (0.6, 0.72), (0.6, 0.28), (0.32, 0), (0, 0)]],
    "I": [[(0.0, 1), (0.3, 1)], [(0.15, 1), (0.15, 0)], [(0.0, 0), (0.3, 0)]],
    "N": [[(0, 0), (0, 1), (0.6, 0), (0.6, 1)]],
    "E": [[(0.58, 1), (0, 1), (0, 0), (0.58, 0)], [(0, 0.52), (0.44, 0.52)]],
    "R": [[(0, 0), (0, 1), (0.44, 1), (0.6, 0.86), (0.6, 0.66), (0.44, 0.52), (0, 0.52)], [(0.3, 0.52), (0.6, 0)]],
    "O": [[(0.3, 0), (0.6, 0.2), (0.6, 0.8), (0.3, 1), (0, 0.8), (0, 0.2), (0.3, 0)]],
    "P": [[(0, 0), (0, 1), (0.44, 1), (0.6, 0.86), (0.6, 0.66), (0.44, 0.52), (0, 0.52)]],
    "A": [[(0, 0), (0.3, 1), (0.6, 0)], [(0.12, 0.4), (0.48, 0.4)]],
    "T": [[(0, 1), (0.6, 1)], [(0.3, 1), (0.3, 0)]],
}
WIDTH = {"I": 0.3}


def neon_word(k, M, word, x0, y, z0, h, tube, mat, gap=0.28, plane="xz", name="Neon", standoff=0.0):
    """A word in neon tube on a vertical plane facing -y (plane xz): x0 = the word's left, z0 its
    baseline, h the cap height. Returns the word's width."""
    x = x0
    for ch in word:
        w = WIDTH.get(ch, 0.6)
        for stroke in GLYPHS[ch]:
            pts = [(x + u * h, y - standoff, z0 + v * h) for u, v in stroke]
            closed = stroke[0] == stroke[-1] and len(stroke) > 3
            pts3 = common.fillet_polyline(pts[:-1] if closed else pts, h * 0.08, segments=4, closed=closed)
            if closed:
                pts3 = pts3 + [pts3[0]]
            k.add(name, G.tube([tuple(q) for q in pts3], tube, n=6), mat, tile=None)
        x += (w + gap) * h
    return x - x0 - gap * h


def word_width(word, h, gap=0.28):
    return sum((WIDTH.get(c, 0.6) + gap) * h for c in word) - gap * h


def build(k, M, p):
    sx, sy = p["site"]
    x0, x1, y0, y1 = -sx / 2, sx / 2, -sy / 2, sy / 2
    lz, wz = p["lot_z"], p["walk_z"]
    C = p["car"]
    A = p["annex"]
    RED, BLACK = p["red"], p["black"]
    wy0 = -2.2                 # the walk's front edge
    wx = 10.6                  # the walk's half length
    # ------------------------------------------------ asphalt (round the buildings, not under them)
    for lo, hi in (((x0, y0), (x1, wy0)), ((x0, wy0), (-wx, y1)), ((wx, wy0), (x1, y1)), ((-wx, C["yf"] + 0.4), (C["x0"] + 0.1, y1)),
                   ((C["x1"] - 0.1, C["yf"] + 0.4), (wx, y1)), ((C["x0"] + 0.1, A["y1"] - 0.05), (C["x1"] - 0.1, y1)),
                   ((C["x0"] + 0.1, C["yb"] - 0.05), (A["x0"] + 0.02, A["y1"])), ((A["x1"] - 0.02, C["yb"] - 0.05), (C["x1"] - 0.1, A["y1"]))):
        k.add("Site_Lot", G.box_lohi((lo[0], lo[1], -0.06), (hi[0], hi[1], lz)), M["asphalt"], tile=4.0, lm=0.3)
    # the walk along the car's front; a curb face, a ramp at the east end
    walk = [(-wx, wy0), (wx, wy0), (wx, C["yf"] + 0.4), (-wx, C["yf"] + 0.4)]
    k.add("Site_Walk", G.prism(walk, lz - 0.02, wz, bevel=0.012), M["concrete"], tile=2.0, lm=0.6)
    k.collider((-wx, wy0, 0.0), (wx, C["yf"] + 0.4, wz))
    for xj in [-wx + 1.5 * i for i in range(1, int(2 * wx / 1.5))]:
        k.add("Site_WalkJoint", G.box_lohi((xj - 0.006, wy0 + 0.02, wz - 0.002), (xj + 0.006, C["yf"] + 0.38, wz + 0.001)), M["paint"], tint=(0.2, 0.2, 0.2), tile=1.0, lm=0.2)
    # ------------------------------------------------ stalls: stripes, wheel stops, the accessible one
    sy0, sy1 = wy0 - 5.3, wy0
    xs = [-14.4 + 2.7 * i for i in range(5)] + [1.5 + 2.7 * i for i in range(6)]
    p["stalls"] = []
    for i, xa in enumerate(xs):
        if xa > 14.5:
            continue
        k.add("Site_Stripe", G.box_lohi((xa - 0.05, sy0, lz), (xa + 0.05, sy1 - 0.1, lz + 0.003)), M["paint"], tint=(0.75, 0.75, 0.72), tile=1.0, lm=0.2)
        if i not in (4,) and xa + 2.7 < 14.6:
            cxs = xa + 1.35
            p["stalls"].append((cxs, (sy0 + sy1) / 2))
            k.add("Site_WheelStop", G.box_lohi((cxs - 0.9, sy1 - 0.75, lz), (cxs + 0.9, sy1 - 0.6, lz + 0.11), bevel=0.02, seg=2), M["concrete"], tint=(0.75, 0.74, 0.7), tile=1.0, lm=0.4)
    # the accessible stall (east of the walkway): blue hatching and the pictogram
    ax = 1.5 + 1.35
    for j in range(5):
        k.add("Site_Hatch", G.box_lohi((ax + 1.4 + 0.0, sy0 + 0.5 + j * 0.9, lz), (ax + 1.5, sy0 + 0.9 + j * 0.9, lz + 0.003)), M["paint"], tint=(0.05, 0.15, 0.5), tile=1.0, lm=0.2)
    k.add("Site_Picto", G.cyl((ax, sy0 + 2.0, lz + 0.002), 0.45, 0.002, n=24), M["paint"], tint=(0.05, 0.15, 0.5), tile=1.0, lm=0.2)
    k.add("Site_PictoFig", G.cyl((ax, sy0 + 2.0, lz + 0.004), 0.28, 0.002, n=20), M["paint"], tint=(0.75, 0.75, 0.72), tile=1.0, lm=0.2)
    k.add("Site_PictoFig2", G.cyl((ax, sy0 + 2.0, lz + 0.006), 0.2, 0.002, n=20), M["paint"], tint=(0.05, 0.15, 0.5), tile=1.0, lm=0.2)
    # the walkway in the middle: a crosswalk of wide white bars from the drive aisle to the steps
    for j in range(6):
        yy = sy0 + 0.3 + j * 0.85
        k.add("Site_Zebra", G.box_lohi((-1.2, yy, lz), (1.2, yy + 0.45, lz + 0.003)), M["paint"], tint=(0.75, 0.75, 0.72), tile=1.0, lm=0.2)
    # ------------------------------------------------ the road edge: planters between the driveways
    for pa, pb in ((x0 + 0.2, -9.0), (-2.6, 2.6), (9.0, x1 - 0.2)):
        planter(k, M, p, pa, pb, y0 + 0.25, y0 + 1.55, 0.45)
    # driveway aprons: a strip of concrete where the lot meets the highway shoulder
    for da, db in ((-9.0, -2.6), (2.6, 9.0)):
        k.add("Site_Apron", G.box_lohi((da, y0, lz - 0.02), (db, y0 + 1.0, lz + 0.005)), M["concrete"], tile=2.0, lm=0.3)
    # ------------------------------------------------ the pylon sign by the west drive
    pylon(k, M, p, -12.0, y0 + 0.9)
    # ------------------------------------------------ the roof sign
    roof_sign(k, M, p)
    # ------------------------------------------------ the walk's furniture
    bench(k, M, p, 3.6, wy0 + 0.55)
    bench(k, M, p, -3.6, wy0 + 0.55)
    for xp in (-wx + 0.6, wx - 0.6):
        pot(k, M, p, xp, wy0 + 0.6, wz)
    for xs_ in (-7.6, -7.0):
        k.add("Site_BikeStaple", G.tube(common.fillet_polyline([(xs_, wy0 + 0.35, wz), (xs_, wy0 + 0.35, wz + 0.8), (xs_, wy0 + 1.05, wz + 0.8), (xs_, wy0 + 1.05, wz)], 0.15, 6, False), 0.024, n=8),
              M["paint"], tint=BLACK, tile=1.0, smooth=True, lm=0.4)
    # ------------------------------------------------ the service yard
    enclosure(k, M, p, 11.0, 14.6, A["y1"] + 0.6, y1 - 0.3)
    k.add("Yard_GreaseBin", G.box_lohi((9.6, A["y1"] + 1.2, lz), (10.5, A["y1"] + 1.9, lz + 1.0), bevel=0.03), M["paint"], tint=(0.08, 0.09, 0.1), tile=1.0, collide=True, lm=0.5)
    k.add("Yard_GreaseLid", G.box_lohi((9.58, A["y1"] + 1.18, lz + 1.0), (10.52, A["y1"] + 1.92, lz + 1.05), bevel=0.02), M["paint"], tint=(0.06, 0.07, 0.08), tile=1.0, lm=0.5)
    k.add("Yard_Bollard", G.cyl((9.1, A["y1"] + 0.12, lz + 0.55), 0.1, 1.1, n=12, bevel=0.03), M["paint"], tint=(0.6, 0.45, 0.03), tile=1.0, collide=True, smooth=True, lm=0.4)
    k.add("Yard_Bollard", G.cyl((-9.1, A["y1"] + 0.12, lz + 0.55), 0.1, 1.1, n=12, bevel=0.03), M["paint"], tint=(0.6, 0.45, 0.03), tile=1.0, collide=True, smooth=True, lm=0.4)
    # the yard light on the annex's east corner
    k.add("Yard_LightArm", G.box_lohi((A["x1"], A["y1"] - 0.6, 3.0), (A["x1"] + 0.5, A["y1"] - 0.5, 3.06)), M["paint"], tint=BLACK, tile=1.0, lm=0.3)
    k.add("Yard_LightHead", G.box_lohi((A["x1"] + 0.3, A["y1"] - 0.75, 2.92), (A["x1"] + 0.65, A["y1"] - 0.35, 3.0), bevel=0.01), M["paint"], tint=BLACK, tile=1.0, lm=0.3)
    k.add("Yard_LightLens", G.box_lohi((A["x1"] + 0.33, A["y1"] - 0.72, 2.915), (A["x1"] + 0.62, A["y1"] - 0.38, 2.92)), M["globe_cool"], tile=None, bake=False)
    k.light(kind="spot", loc=(A["x1"] + 0.48, A["y1"] - 0.55, 2.88), power=80.0, color=(1.0, 0.92, 0.8), dir=(0.1, 0.3, -1), cone=110, blend=0.6, radius=0.08)


def planter(k, M, p, xa, xb, ya, yb, h):
    """A fieldstone-edged planter: a cast stone cap, soil, mown grass and a row of low shrubs."""
    lz = p["lot_z"]
    t = 0.3
    for lo, hi in (((xa, ya, lz), (xb, ya + t, h)), ((xa, yb - t, lz), (xb, yb, h)), ((xa, ya + t, lz), (xa + t, yb - t, h)), ((xb - t, ya + t, lz), (xb, yb - t, h))):
        k.add("Planter_Wall", G.box_lohi(lo, hi), M["stone"], tile=2.0, lm=0.5)
        k.add("Planter_Cap", G.box_lohi((lo[0] - 0.02, lo[1] - 0.02, h), (hi[0] + 0.02, hi[1] + 0.02, h + 0.05), bevel=0.01), M["concrete"], tile=1.0, lm=0.4)
    k.collider((xa, ya, 0.0), (xb, yb, h + 0.05))
    k.add("Planter_Soil", G.box_lohi((xa + t, ya + t, lz), (xb - t, yb - t, h - 0.06)), M["paint"], tint=(0.06, 0.09, 0.03), tile=1.0, lm=0.4)
    n = max(2, int((xb - xa) / 0.9))
    rng = __import__("random").Random(int(xa * 10))
    for i in range(n):
        cx = xa + 0.55 + i * (xb - xa - 1.1) / max(1, n - 1)
        r = 0.32 + 0.1 * rng.random()
        bm = G.box_lohi((cx - r, (ya + yb) / 2 - r * 0.8, h - 0.06), (cx + r, (ya + yb) / 2 + r * 0.8, h + r * 1.2), bevel=r * 0.45, seg=2)
        k.add("Planter_Shrub", bm, M["paint"], tint=(0.05 + 0.03 * rng.random(), 0.11 + 0.04 * rng.random(), 0.035), tile=1.0, smooth=60, lm=0.6)


def pot(k, M, p, x, y, z):
    k.add("Pot", G.lathe([(0.001, 0.0), (0.26, 0.0), (0.3, 0.62), (0.32, 0.64), (0.32, 0.66), (0.001, 0.66)], c=(x, y, z), n=16), M["paint"], tint=(0.03, 0.03, 0.033), tile=1.0, smooth=True, lm=0.5)
    bm = G.box_lohi((x - 0.33, y - 0.33, z + 0.6), (x + 0.33, y + 0.33, z + 1.15), bevel=0.24, seg=3)
    k.add("Pot_Plant", bm, M["paint"], tint=(0.06, 0.13, 0.04), tile=1.0, smooth=60, lm=0.5)
    k.collider((x - 0.3, y - 0.3, 0.0), (x + 0.3, y + 0.3, z + 0.66))


def bench(k, M, p, x, y):
    """A bench on the walk: black steel frames, oak slats, its back to the car."""
    z = p["walk_z"]
    L = 1.8
    for s in (-1, 1):
        fx = x + s * (L / 2 - 0.15)
        frame = [(fx, y + 0.25, z), (fx, y + 0.22, z + 0.44), (fx, y - 0.25, z + 0.44), (fx, y - 0.25, z)]
        k.add("Bench_Frame", G.tube(common.fillet_polyline(frame, 0.04, 3, False), 0.022, n=6), M["paint"], tint=p["black"], tile=1.0, smooth=True, lm=0.4)
        k.add("Bench_Frame", G.tube([(fx, y + 0.21, z + 0.44), (fx, y + 0.29, z + 0.86)], 0.02, n=6), M["paint"], tint=p["black"], tile=1.0, smooth=True, lm=0.4)
    for j in range(4):
        yy = y - 0.22 + j * 0.13
        k.add("Bench_Slat", G.box_lohi((x - L / 2, yy, z + 0.44), (x + L / 2, yy + 0.1, z + 0.475), bevel=0.008), M["wood"], tile=0.5, lm=0.5)
    for j in range(2):
        zz = z + 0.6 + j * 0.15
        k.add("Bench_Slat", G.box_lohi((x - L / 2, y + 0.24 + j * 0.035, zz), (x + L / 2, y + 0.27 + j * 0.035, zz + 0.1), bevel=0.008), M["wood"], tile=0.5, lm=0.5)
    k.collider((x - L / 2, y - 0.27, 0.0), (x + L / 2, y + 0.3, z + 0.47))


def enclosure(k, M, p, xa, xb, ya, yb):
    """The dumpster enclosure: black board fence on steel posts, a pair of gates (one ajar), a
    green dumpster inside."""
    lz = p["lot_z"]
    h = 1.8
    for lo, hi in (((xa, yb - 0.08, lz), (xb, yb, h)), ((xa, ya, lz), (xa + 0.08, yb, h)), ((xb - 0.08, ya, lz), (xb, yb, h))):
        k.add("Fence", G.box_lohi(lo, hi), M["paint"], tint=p["black"], tile=1.0, lm=0.5, collide=True)
    k.add("Fence_Gate", G.box_lohi((xa + 0.1, ya - 0.04, lz + 0.05), ((xa + xb) / 2 - 0.02, ya + 0.02, h)), M["paint"], tint=p["black"], tile=1.0, lm=0.5, collide=True)
    gate = G.box_lohi((0, -0.03, lz + 0.05), ((xb - xa) / 2 - 0.12, 0.03, h))
    G.xform(gate, loc=(xb - 0.1, ya, 0), rz=math.radians(180 - 35))
    k.add("Fence_Gate", gate, M["paint"], tint=p["black"], tile=1.0, lm=0.5, collide=True)
    for xx in (xa + 0.04, xb - 0.04, (xa + xb) / 2):
        k.add("Fence_Post", G.box_lohi((xx - 0.05, ya - 0.05, lz), (xx + 0.05, ya + 0.05, h + 0.05)), M["paint"], tint=(0.02, 0.02, 0.02), tile=1.0, lm=0.4)
    dx0, dx1, dy0, dy1 = xa + 0.35, xb - 0.35, ya + 0.6, yb - 0.25
    k.add("Dumpster", G.box_lohi((dx0, dy0, lz + 0.15), (dx1, dy1, lz + 1.25), bevel=0.03), M["paint"], tint=(0.06, 0.16, 0.08), tile=1.0, lm=0.5, collide=True)
    k.add("Dumpster_Lid", G.box_lohi((dx0 - 0.02, dy0 - 0.02, lz + 1.25), (dx1 + 0.02, dy1 + 0.02, lz + 1.32), bevel=0.02), M["paint"], tint=(0.02, 0.02, 0.02), tile=1.0, lm=0.5)
    for xx in (dx0 + 0.2, dx1 - 0.2):
        k.add("Dumpster_Wheel", G.cyl((xx, dy0 + 0.2, lz + 0.08), 0.07, 0.06, n=10, axis="x"), M["paint"], tint=(0.03, 0.03, 0.03), tile=1.0, lm=0.3)


def pylon(k, M, p, x, y):
    """The road sign: two stainless posts on a stone base; a streamlined red-and-stainless cabinet
    with DINER in red neon, a chaser arrow pointing in, OPEN in blue under it."""
    lz = p["lot_z"]
    zb = 0.6
    k.add("Pylon_Base", G.box_lohi((x - 1.0, y - 0.4, lz), (x + 1.0, y + 0.4, zb), bevel=0.01), M["stone"], tile=2.0, collide=True, lm=0.5)
    k.add("Pylon_BaseCap", G.box_lohi((x - 1.04, y - 0.44, zb), (x + 1.04, y + 0.44, zb + 0.06), bevel=0.01), M["concrete"], tile=1.0, lm=0.4)
    for dx in (-0.6, 0.6):
        k.add("Pylon_Post", G.cyl((x + dx, y, zb + 2.0), 0.11, 4.0, n=16), M["steel"], tile=0.5, smooth=True, collide=True)
    # the cabinet: a rounded-end box (plan) 3.6 x 0.45, 1.3 tall, red enamel faces in a stainless band
    zc0, zc1 = 3.4, 4.75
    cab = G.rounded_rect(x - 1.85, y - 0.23, x + 1.85, y + 0.23, 0.22, 8)
    k.add("Pylon_Cab", G.prism(cab, zc0, zc1), M["paint"], tint=p["red"], tile=1.0, lm=0.6)
    k.add("Pylon_Band", G.path_sweep(cab + [cab[0]], [(0.0, zc0 - 0.02), (0.03, zc0), (0.03, zc0 + 0.12), (0.0, zc0 + 0.14)], closed=True), M["steel"], tile=0.5, uv_rot=True)
    k.add("Pylon_Band", G.path_sweep(cab + [cab[0]], [(0.0, zc1 - 0.14), (0.03, zc1 - 0.12), (0.03, zc1), (0.0, zc1 + 0.02)], closed=True), M["steel"], tile=0.5, uv_rot=True)
    k.add("Pylon_Cap", G.prism(G.rounded_rect(x - 1.95, y - 0.3, x + 1.95, y + 0.3, 0.28, 8), zc1, zc1 + 0.08), M["steel"], tile=0.5, lm=0.5)
    # DINER on both faces (front = -y, back = +y: mirrored by building it facing +y)
    h = 0.62
    w = word_width("DINER", h)
    neon_word(k, M, "DINER", x - w / 2, y - 0.24, zc0 + 0.33, h, 0.016, M["neon_red"], name="Pylon_Neon", standoff=0.03)
    # (the back face: the same word reversed so it reads from the far side)
    bx = x + w / 2
    for ch in "DINER":
        cw = WIDTH.get(ch, 0.6)
        for stroke in GLYPHS[ch]:
            pts = [(bx - u * h, y + 0.27, zc0 + 0.33 + v * h) for u, v in stroke]
            closed = stroke[0] == stroke[-1] and len(stroke) > 3
            pts3 = common.fillet_polyline(pts[:-1] if closed else pts, h * 0.08, segments=4, closed=closed)
            if closed:
                pts3 = pts3 + [pts3[0]]
            k.add("Pylon_Neon", G.tube([tuple(q) for q in pts3], 0.016, n=6), M["neon_red"], tile=None)
        bx -= (cw + 0.28) * h
    # the arrow under the cabinet: a stainless blade with a row of chaser bulbs, pointing at the lot
    za = 2.7
    arrow = [(x - 1.6, za - 0.18), (x + 0.9, za - 0.18), (x + 0.9, za - 0.38), (x + 1.65, za), (x + 0.9, za + 0.38), (x + 0.9, za + 0.18), (x - 1.6, za + 0.18)]
    bm = G.sweep([(a, b) for a, b in arrow][::-1], y - 0.07, y + 0.07, axis="y")
    k.add("Pylon_Arrow", bm, M["paint"], tint=(0.75, 0.72, 0.62), tile=1.0, lm=0.5)
    for i in range(10):
        bxx = x - 1.45 + i * 0.25
        for yy in (y - 0.08, y + 0.08):
            k.add("Pylon_Bulb", G.cyl((bxx, yy, za), 0.04, 0.03, n=8, axis="y"), M["globe"], tile=None, bake=True)
    # OPEN in blue on a small black panel over the arrow
    k.add("Pylon_OpenPanel", G.box_lohi((x - 0.75, y - 0.1, 2.98), (x + 0.75, y + 0.1, 3.36), bevel=0.02), M["paint"], tint=(0.02, 0.02, 0.022), tile=1.0, lm=0.5)
    ho = 0.26
    wo = word_width("OPEN", ho)
    neon_word(k, M, "OPEN", x - wo / 2, y - 0.1, 3.04, ho, 0.01, M["neon_blue"], name="Pylon_Open", standoff=0.02)


def roof_sign(k, M, p):
    """On the car's roof over the vestibule: a stainless-edged red board on two struts, DINER in
    red neon with a blue neon underline."""
    C = p["car"]
    fz = p["fz"]
    ze = C["ze"]
    yb = C["yf"] + 0.55
    zb0, zb1 = ze + 0.42, ze + 1.42
    xb = 3.2
    board = [(-xb, zb0), (xb, zb0), (xb, zb1 - 0.2), (xb - 0.2, zb1), (-xb + 0.2, zb1), (-xb, zb1 - 0.2)]
    k.add("RoofSign_Board", G.sweep(board, yb - 0.06, yb + 0.06, axis="y"), M["paint"], tint=p["red"], tile=1.0, lm=0.6)
    k.add("RoofSign_Edge", G.tube([(a, yb - 0.065, b) for a, b in board] + [(board[0][0], yb - 0.065, board[0][1])], 0.025, n=6), M["steel"], tile=0.5, lm=0.5)
    for xs in (-2.2, 2.2):
        k.add("RoofSign_Strut", G.box_lohi((xs - 0.05, yb - 0.05, ze - 0.1), (xs + 0.05, yb + 0.05, zb0)), M["steel"], tile=0.5, lm=0.4)
        k.add("RoofSign_Brace", G.tube([(xs, yb, zb0 - 0.05), (xs, yb + 0.9, ze + 0.25)], 0.025, n=6), M["steel"], tile=0.5, lm=0.3)
    h = 0.66
    w = word_width("DINER", h)
    neon_word(k, M, "DINER", -w / 2, yb - 0.07, zb0 + 0.2, h, 0.018, M["neon_red"], name="RoofSign_Neon", standoff=0.03)
    k.add("RoofSign_Line", G.tube([(-w / 2, yb - 0.1, zb0 + 0.11), (w / 2, yb - 0.1, zb0 + 0.11)], 0.014, n=6), M["neon_blue"], tile=None)
