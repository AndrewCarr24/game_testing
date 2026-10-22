"""THE GAS STATION (town2_gas): Sourwood's canopy station and convenience store at the highway end
of Main Street (design/town/gas.md). Built, lightmapped and exported by blender/town/gas/make.py.

Frame: metres, origin at the lot's floor centre (z = 0 = the forecourt), front -Y (Main Street).
Footprint x -22..22, y -20..20 (the whole lot is paved here: the terrain under it is sunk).

  the road edge (y -20) -> two driveways, a planted strip, the monument price sign (east)
  the forecourt: a 24 x 11 m canopy (16 ft clear) over three pump islands, LED flat-lens fixtures
  the drive aisle -> the sidewalk and the store: 20 x 14 m, ledgestone base, light board-and-batten,
      a black storefront with a steel awning; inside: the coffee bar (west wall), the cooler wall
      (north), three gondolas, the cash wrap (east: lottery, the tobacco wall, the security
      monitor, a CB radio), restrooms and the stockroom (north-east), its back door open
  the side lot (east): parking, the air machine; the back lot: a dark van, doors open, by the
      stockroom door; the dumpster enclosure
"""
import importlib
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import town2_gas_kit as K  # noqa: E402
import town2_gas_mat as MT  # noqa: E402
import town2_gas_out as OUT  # noqa: E402
import town2_gas_in as IN  # noqa: E402

for m in (K, MT, OUT, IN):
    importlib.reload(m)

NAME = "Town2Gas"
P = dict(
    x0=-22.0, x1=22.0, y0=-20.0, y1=20.0,
    # the store: outside faces; the floor at the sidewalk's height
    sx0=-16.0, sx1=4.0, sy0=3.2, sy1=17.2, floor=0.15, ceil=3.35, parapet=5.2, wall=0.25, base_h=0.65,
    # the storefront: glass bays and the entry (x ranges), glass head
    bay_a=(-15.2, -8.8), entry=(-8.8, -4.4), door=(-7.8, -5.4), bay_b=(-4.4, 1.6), glass_top=3.0,
    back_door=(15.3, 16.3),
    # the canopy
    cx0=-15.0, cx1=9.0, cy0=-16.5, cy1=-5.5, cz=4.9, fascia=1.0,
    islands=(-11.0, -3.0, 5.0), island_y=-11.0, island_len=6.6,
    lod_distance=140,
)


def build(col, feeds=None, **over):
    p = dict(P, **over)
    mats, T = MT.materials(feeds)
    kit = K.Kit(NAME, mats, swatches=T["palette"], cells=dict(goods=T["goods"], drinks=T["drinks"], signs=T["signs"]))
    rng = random.Random(7)
    lot(kit, p, rng)
    canopy(kit, p)
    store_shell(kit, p, rng)
    IN.interior(kit, p, rng)
    yard(kit, p, rng)
    lod1(kit, p)
    kit.build(col)
    info = dict(footprint=[p["x0"], p["y0"], p["x1"], p["y1"]], height=p["parapet"], lod_distance=p["lod_distance"])
    return kit, info


# ------------------------------------------------------------------ the lot
def lot(kit, p, rng):
    A = kit.p("asphalt", "ext", lmw=0.3)
    C = kit.p("concrete", "ext", lmw=0.4)
    x0, x1, y0, y1 = p["x0"], p["x1"], p["y0"], p["y1"]
    # the forecourt slab under the canopy (concrete), the rest asphalt; the front strip's beds
    fx0, fx1, fy0, fy1 = p["cx0"] - 1.5, p["cx1"] + 1.5, p["cy0"] - 1.5, p["cy1"] + 1.4
    C.box((fx0, fy0, -0.1), (fx1, fy1, 0.0), skip="zxXyY")
    strip = y0 + 1.5                      # the planted strip along the road (beds between the driveways)
    drives = [(-22.0, -11.0), (2.0, 12.0)]
    # asphalt: everything but the forecourt and the beds (rectangles)
    for (a0, b0, a1, b1) in (
        (x0, strip, fx0, y1), (fx1, strip, x1, y1), (fx0, fy1, fx1, y1), (fx0, strip, fx1, fy0),
    ):
        A.box((a0, b0, -0.1), (a1, b1, 0.0), skip="zxXyY")
    for a0, a1 in drives:
        A.box((a0, y0, -0.1), (a1, strip, 0.0), skip="zxXyY")
    beds = [(-11.0, 2.0), (12.0, 22.0)]
    for a0, a1 in beds:
        sh = [(a0 + 0.8 + k * 1.3, y0 + 0.75, 0.42 + 0.08 * rng.random()) for k in range(int((a1 - a0 - 1.2) / 1.3))]
        if a0 > 10:
            sh = [s for s in sh if abs(s[0] - 17.5) > 2.0]
        OUT.bed(kit, rng, a0, y0, a1, strip, shrubs=sh)
    with kit.at((17.5, y0 + 0.75, 0.15)):
        OUT.monument_sign(kit)
    # the sidewalks: along the storefront, down the store's east side, the back stoop
    sw = [(p["sx0"] - 1.5, 1.0, p["sx1"] + 1.8, p["sy0"]), (p["sx1"], p["sy0"], p["sx1"] + 1.8, 9.6),
          (p["sx1"], p["back_door"][0] - 0.6, p["sx1"] + 1.6, p["back_door"][1] + 0.6)]
    for (a0, b0, a1, b1) in sw:
        C.box((a0, b0, 0), (a1, b1, p["floor"]), skip="z")
        kit.collide((a0, b0, 0), (a1, b1, p["floor"]))
    # the west bed along the store's side wall (boxwoods), and the strip behind
    OUT.bed(kit, rng, p["sx0"] - 1.5, p["sy0"], p["sx0"], p["sy1"],
            shrubs=[(p["sx0"] - 0.75, y, 0.5) for y in [4.2 + k * 1.45 for k in range(9)]])
    # paint: the parking stalls on the side lot (head-in to the east sidewalk), stop bars at the drives
    # (full density: at less, the 10 cm stripes were under a texel and bled dark)
    Wp = kit.p("paint_white_road", "ext", lmw=1.0)
    for k in range(5):
        y = -1.6 + k * 2.75
        Wp.box((p["sx1"] + 1.8, y - 0.05, 0.0), (p["sx1"] + 7.3, y + 0.05, 0.004), skip="zxXyY")
    for a0, a1 in drives:
        Wp.box((a0 + 0.5, y0 + 2.2, 0.0), (a0 + (a1 - a0) / 2 - 0.2, y0 + 2.6, 0.004), skip="zxXyY")
    # the forecourt's oil spots and tyre wear (dark, irregular, just above the slab)
    O = kit.p("stain", "ext", lmw=0.6)
    for x in p["islands"]:
        for s in (-1, 1):
            for k in range(2):
                cx, cy = x + s * 1.9 + rng.uniform(-0.3, 0.3), p["island_y"] + rng.uniform(-1.5, 1.5)
                blot(O, rng, cx, cy, rng.uniform(0.25, 0.5))
    O2 = kit.p("asphalt_patch", "ext", lmw=0.6)
    for k in range(5):
        blot(O2, rng, 8.3 + rng.uniform(-0.5, 0.5), 11.0 + k * 1.1, rng.uniform(0.3, 0.6))


def blot(brush, rng, cx, cy, r):
    n = 9
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        rr = r * (0.6 + 0.4 * rng.random())
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a) * 0.8, 0.003))
    brush.face(pts)


# ------------------------------------------------------------------ the canopy
def canopy(kit, p):
    W = kit.p("white", "ext", lmw=0.5)
    G = kit.p("signs", "ext")
    x0, x1, y0, y1, z, fz = p["cx0"], p["cx1"], p["cy0"], p["cy1"], p["cz"], p["fascia"]
    # the deck: underside (soffit panels), fascia, the top (low density: seen from the hill only)
    kit.p("white", "ext", lmw=0.15).box((x0, y0, z + fz - 0.05), (x1, y1, z + fz), skip="z")
    W.box((x0, y0, z), (x1, y1, z + 0.02), skip="Z")
    for (a, b, c, d) in ((x0, y0, x1, y0 + 0.08), (x0, y1 - 0.08, x1, y1), (x0, y0, x0 + 0.08, y1), (x1 - 0.08, y0, x1, y1)):
        W.box((a, b, z), (c, d, z + fz), bevel=0.02)
    # fascia panel seams, the green accent band all round, the pump mark front and back and at the ends
    D = kit.p("lightgrey", "ext", lmw=0.3)
    for k in range(1, 16):
        x = x0 + k * (x1 - x0) / 16
        D.box((x - 0.006, y0 - 0.004, z + 0.05), (x + 0.006, y0, z + fz - 0.05))
        D.box((x - 0.006, y1, z + 0.05), (x + 0.006, y1 + 0.004, z + fz - 0.05))
    bz = z + 0.2
    G.panel(((x0 + x1) / 2, y0 - 0.005, bz), "y", x1 - x0 - 0.1, 0.12, cell=kit.cell("signs", "band"))
    G.panel(((x0 + x1) / 2, y1 + 0.005, bz), "Y", x1 - x0 - 0.1, 0.12, cell=kit.cell("signs", "band"))
    G.panel((x0 - 0.005, (y0 + y1) / 2, bz), "x", y1 - y0 - 0.1, 0.12, cell=kit.cell("signs", "band"))
    G.panel((x1 + 0.005, (y0 + y1) / 2, bz), "X", y1 - y0 - 0.1, 0.12, cell=kit.cell("signs", "band"))
    for cx in (x0 + 2.0, x1 - 2.0):
        G.panel((cx, y0 - 0.006, z + 0.62), "y", 0.62, 0.62, cell=kit.cell("signs", "logo"))
    G.panel((x0 - 0.006, (y0 + y1) / 2, z + 0.62), "x", 0.62, 0.62, cell=kit.cell("signs", "logo"))
    G.panel((x1 + 0.006, (y0 + y1) / 2, z + 0.62), "X", 0.62, 0.62, cell=kit.cell("signs", "logo"))
    # LED flat-lens fixtures over the lanes and the islands (recessed, a dark trim ring)
    lanes = [x0 + 2.0, -7.0, 1.0, x1 - 2.0]
    xs = sorted(set(lanes + list(p["islands"])))
    cell = kit.cell("signs", "canopy_led")
    T = kit.p("graphite", "ext", lmw=0.1)
    for cx in xs:
        for cy in (y0 + 2.0, (y0 + y1) / 2, y1 - 2.0):
            T.box((cx - 0.36, cy - 0.36, z - 0.03), (cx + 0.36, cy + 0.36, z), skip="Z")
            G.panel((cx, cy, z - 0.037), "z", 0.62, 0.62, cell=cell)
            kit.light("area", (cx, cy, z - 0.05), size=(0.6, 0.6), energy=55.0, color=(1.0, 0.97, 0.92))
    # columns on the outer islands; the islands, dispensers and stands
    yi, L = p["island_y"], p["island_len"]
    for x in p["islands"]:
        with kit.at((x, yi, 0)):
            OUT.island(kit, L)
        with kit.at((x, yi, 0.15)):
            OUT.dispenser(kit, diesel=(x == p["islands"][-1]))
        with kit.at((x, yi + 2.0, 0.15)):
            OUT.island_stand(kit)
    for x in (p["islands"][0], p["islands"][-1]):
        for y in (yi - 2.55, yi + 2.55 + 0.4):
            with kit.at((x, y, 0.15), rot=0 if y < yi else 180):
                OUT.column(kit, z - 0.15)
    # security domes under the canopy
    for cx in (x0 + 0.6, x1 - 0.6):
        kit.p("black", "ext", lmw=0.1).lathe([(0.0, 0.0), (0.08, 0.0), (0.075, -0.05), (0.0, -0.08)], c=(cx, y1 - 0.6), z=z, seg=10)
    kit.mark("probe_ext", (-7.0, -11.0, 1.6))
    # the security cameras whose feeds the monitors show (make.py renders them)
    kit.mark("cam_pumps", (x1 - 0.6, y1 - 0.6, z - 0.15))
    kit.mark("cam_pumps_at", (-5.0, -12.5, 0.6))


# ------------------------------------------------------------------ the store's shell
def wall(kit, p, a0, a1, axis, c, inward, openings=(), ext="siding", base="stone", int_mat="offwhite", battens=True):
    """A straight exterior wall along `axis` (0: along x at y = c; 1: along y at x = c) from a0 to
    a1, its outside face at c, the inside `inward` (+1/-1) of it; openings: [(b0, b1, z0, z1)].
    Outer skin (ext: ledgestone base, board-and-batten above) + inner lining (int), split round the
    openings; colliders per piece; battens every 0.45 m on the boards."""
    t = p["wall"]
    zt = p["parapet"]
    bh = p["base_h"]
    pieces = slices(a0, a1, 0.0, zt, openings)
    for (b0, b1, z0, z1) in pieces:
        for zone, mat, d0, d1, zz0, zz1 in (("ext", base, 0, t * 0.5, z0, min(z1, bh)), ("ext", ext, 0, t * 0.5, max(z0, bh), z1),
                                            ("int", int_mat, t * 0.5, t, max(z0, p["floor"]), min(z1, p["ceil"] + 0.02))):
            if zz1 - zz0 < 1e-4:
                continue
            q0, q1 = sorted((c + inward * d0, c + inward * d1))
            lo, hi = ((b0, q0, zz0), (b1, q1, zz1)) if axis == 0 else ((q0, b0, zz0), (q1, b1, zz1))
            if zone == "ext":
                skip = ("Y" if inward > 0 else "y") if axis == 0 else ("X" if inward > 0 else "x")
                # (hidden: on the ground, stone under boards, under the coping)
                if zz0 <= 1e-3 or abs(zz0 - bh) < 1e-3:
                    skip += "z"
                if zz1 >= zt - 1e-3 or abs(zz1 - bh) < 1e-3:
                    skip += "Z"
            else:
                skip = ("y" if inward > 0 else "Y") if axis == 0 else ("x" if inward > 0 else "X")
                if zz0 <= p["floor"] + 1e-3:
                    skip += "z"
                if zz1 >= p["ceil"]:
                    skip += "Z"
            kit.p(mat, zone, lmw=0.7 if zone == "ext" else 1.0).box(lo, hi, skip=skip)
        q0, q1 = sorted((c, c + inward * t))
        kit.collide((b0, q0, z0), (b1, q1, z1)) if axis == 0 else kit.collide((q0, b0, z0), (q1, b1, z1))
    # the stone base's cast cap (a drip edge) and the battens, outside, round the openings
    Cc = kit.p("concrete", "ext", lmw=0.4)
    # (the battens share one lightmap chart per wall, projected on the wall: thin faces of their
    # own came out as dark, bled lines)
    Bt = kit.p("siding", "ext", lmw=0.7, group=kit.group(1 if axis == 0 else 0))
    o = -inward
    for (b0, b1, z0, z1) in slices(a0, a1, bh - 0.001, bh + 0.06, openings):
        q0, q1 = sorted((c + o * 0.035, c + inward * 0.02))
        Cc.box(*(((b0, q0, z0), (b1, q1, z1)) if axis == 0 else ((q0, b0, z0), (q1, b1, z1))), skip="")
    if battens:
        k0 = math.ceil((a0 + 0.2) / 0.45)
        k1 = math.floor((a1 - 0.2) / 0.45)
        for k in range(k0, k1 + 1):
            b = k * 0.45
            for (b0, b1, z0, z1) in slices(b - 0.03, b + 0.03, bh + 0.06, zt - 0.12, openings):
                if b1 - b0 < 0.059:
                    continue
                q0, q1 = sorted((c, c + o * 0.022))
                Bt.box(*(((b0, q0, z0), (b1, q1, z1)) if axis == 0 else ((q0, b0, z0), (q1, b1, z1))), skip="zZ" + (("Y" if inward > 0 else "y") if axis == 0 else ("X" if inward > 0 else "x")))


def slices(a0, a1, z0, z1, holes):
    """Rectangles covering [a0, a1] x [z0, z1] minus the holes (b0, b1, h0, h1)."""
    cuts = sorted({a0, a1} | {min(max(h[0], a0), a1) for h in holes} | {min(max(h[1], a0), a1) for h in holes})
    out = []
    for u0, u1 in zip(cuts, cuts[1:]):
        if u1 - u0 < 1e-6:
            continue
        hs = sorted([(max(h[2], z0), min(h[3], z1)) for h in holes if h[0] <= u0 + 1e-6 and h[1] >= u1 - 1e-6 and h[3] > z0 and h[2] < z1])
        z = z0
        for h0, h1 in hs:
            if h0 > z + 1e-6:
                out.append((u0, u1, z, h0))
            z = max(z, h1)
        if z < z1 - 1e-6:
            out.append((u0, u1, z, z1))
    return out


def store_shell(kit, p, rng):
    x0, x1, y0, y1, t = p["sx0"], p["sx1"], p["sy0"], p["sy1"], p["wall"]
    f, gt = p["floor"], p["glass_top"]
    ba, en, bb = p["bay_a"], p["entry"], p["bay_b"]
    sill = p["base_h"]
    front_holes = [(ba[0], ba[1], sill, gt), (en[0], en[1], f, gt), (bb[0], bb[1], sill, gt)]
    wall(kit, p, x0, x1, 0, y0, +1, openings=front_holes)
    wall(kit, p, x0, x1, 0, y1, -1)
    wall(kit, p, y0, y1, 1, x0, +1)
    bd = p["back_door"]
    wall(kit, p, y0, y1, 1, x1, -1, openings=[(bd[0], bd[1], f, 2.3)])
    # corner trims (black), the parapet's coping
    Bk = kit.p("black", "ext", lmw=0.3)
    for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        Bk.box((cx - 0.04, cy - 0.04, p["base_h"] + 0.06), (cx + 0.04, cy + 0.04, p["parapet"] - 0.1))
    zc = p["parapet"]
    for (a, b, c, d) in ((x0 - 0.05, y0 - 0.05, x1 + 0.05, y0 + t), (x0 - 0.05, y1 - t, x1 + 0.05, y1 + 0.05),
                         (x0 - 0.05, y0 + t, x0 + t, y1 - t), (x1 - t, y0 + t, x1 + 0.05, y1 - t)):
        Bk.box((a, b, zc - 0.12), (c, d, zc + 0.02), bevel=0.01)
    # the roof: membrane inside the parapet, the rooftop units
    kit.p("lightgrey", "ext", lmw=0.1).box((x0 + t, y0 + t, zc - 0.5), (x1 - t, y1 - t, zc - 0.45), skip="z")
    for (ux, uy) in ((-11.0, 11.5), (-3.5, 13.5)):
        with kit.at((ux, uy, zc - 0.45)):
            OUT.rooftop_unit(kit)
    # the storefront: glass, black aluminium frames, the entry's sliding doors parked open
    storefront(kit, p)
    # the steel awning over the sidewalk, its tie rods, downlights
    ax0, ax1, ay0 = ba[0] - 0.4, bb[1] + 0.4, y0 - 1.75
    az = 3.18
    Bk2 = kit.p("black", "ext", lmw=0.5)
    px0, px1 = p["entry"][0] - 0.35, p["entry"][1] + 0.35          # the entry's timber portico
    for (a0, a1) in ((ax0, px0), (px1, ax1)):
        Bk2.box((a0, ay0, az), (a1, y0, az + 0.06), skip="")
        Bk2.box((a0, ay0, az - 0.12), (a1, ay0 + 0.06, az + 0.14), bevel=0.01)
        for x in [a0 + 0.3 + k * (a1 - a0 - 0.6) / 2 for k in range(3)]:
            kit.p("black", "ext", lmw=0.1).tube([(x, ay0 + 0.05, az + 0.12), (x, y0 - 0.02, 4.35)], 0.012, sides=5)
            Bk2.box((x - 0.04, y0 - 0.02, 4.3), (x + 0.04, y0, 4.42))
    portico(kit, p, px0, px1, ay0 - 0.3)
    for x in (-13.0, -1.5):
        kit.p("signs", "ext").panel((x, ay0 + 0.85, az - 0.002), "z", 0.14, 0.14, cell=kit.cell("signs", "led_warm"))
        kit.light("spot", (x, ay0 + 0.85, az - 0.03), energy=40.0, color=(1.0, 0.86, 0.68), aim=(x, ay0 + 0.85, 0.0), angle=90, blend=0.7)
    # two gooseneck barn lights on the sign band
    for x in (-12.0, -1.2):
        gooseneck(kit, (x, y0, 4.6))
    # the east wall's service door (steel, propped open), its lamp, the meters; the back stoop
    service_door(kit, p)
    kit.mark("probe_int", (-7.0, 10.0, 1.7))
    kit.mark("cam_door", (-9.2, y0 + 0.5, 3.15))
    kit.mark("cam_door_at", (-6.0, 9.0, 0.6))
    kit.mark("cam_register", (x1 - 0.5, y0 + 0.5, 3.15))
    kit.mark("cam_register_at", (-0.5, 7.0, 0.9))
    kit.mark("cam_back", (x1 + 0.15, y1 - 0.2, 3.6))
    kit.mark("cam_back_at", (8.0, 12.5, 0.8))
    # (the back lot's camera on the wall: a small black bullet camera)
    with kit.at((x1 + 0.12, y1 - 0.2, 3.6)):
        kit.p("black", "ext", lmw=0.1).box((-0.05, -0.05, -0.04), (0.05, 0.05, 0.04))
        kit.p("lightgrey", "ext", lmw=0.1).box((0.03, -0.18, -0.04), (0.1, -0.02, 0.03))


def portico(kit, p, x0, x1, yf):
    """The entry's heavy-timber gable (the mountain-town touch, as on Blowing Rock's and Highlands'
    newer storefronts): two cedar posts on ledgestone piers, a beam, a king-post truss under a
    black standing-seam gable roof; its gable infilled with dark boards and the lit pump mark."""
    y0 = p["sy0"]
    S = kit.p("stone", "ext", lmw=0.8)
    C = kit.p("concrete", "ext", lmw=0.5)
    Wd = kit.p("wood_dark", "ext", lmw=0.8)
    R = kit.p("black", "ext", lmw=0.5)
    f = p["floor"]
    xm = (x0 + x1) / 2
    hw = (x1 - x0) / 2
    ze, zr = 3.55, 5.15                                       # eave and ridge
    for x in (x0 + 0.25, x1 - 0.25):
        S.box((x - 0.3, yf - 0.3 + 0.3, f), (x + 0.3, yf + 0.3 + 0.3, 0.95), skip="z")
        C.box((x - 0.34, yf - 0.04, 0.95), (x + 0.34, yf + 0.64, 1.01), bevel=0.01)
        Wd.box((x - 0.13, yf + 0.17, 1.01), (x + 0.13, yf + 0.43, ze - 0.3), bevel=0.012)
        # knee braces to the beam
        Wd.extrude([(x - 0.06, yf + 0.25, ze - 0.95), (x + 0.06, yf + 0.25, ze - 0.95), (x + (0.55 if x < xm else -0.55) + 0.06, yf + 0.25, ze - 0.3),
                    (x + (0.55 if x < xm else -0.55) - 0.06, yf + 0.25, ze - 0.3)][::1 if x < xm else -1], (0, 0.12, 0))
        kit.collide((x - 0.3, yf, 0), (x + 0.3, yf + 0.6, ze))
    Wd.box((x0, yf + 0.12, ze - 0.3), (x1, yf + 0.48, ze), bevel=0.015)               # the beam
    Wd.box((x0, y0 - 0.25, ze - 0.3), (x1, y0, ze), bevel=0.015)                      # the ledger at the wall
    # the truss in the gable face: rafters, the king post, the infill boards
    yt = yf + 0.2
    for s in (-1, 1):
        a = (xm + s * (hw + 0.25), yt, ze - 0.05)
        b = (xm, yt, zr)
        d = V2(a, b)
        n = (-d[1], d[0])
        Wd.extrude([(a[0] - 0.1 * n[0], yt, a[2] - 0.1 * n[1]), (b[0] - 0.1 * n[0], yt, b[2] - 0.1 * n[1]),
                    (b[0] + 0.1 * n[0], yt, b[2] + 0.1 * n[1]), (a[0] + 0.1 * n[0], yt, a[2] + 0.1 * n[1])][::-1 if s < 0 else 1], (0, 0.18, 0))
    Wd.box((xm - 0.1, yt, ze), (xm + 0.1, yt + 0.18, zr - 0.1))
    # infill (behind the truss): dark vertical boards in the triangle
    tri = [(xm - hw, yt + 0.19, ze), (xm + hw, yt + 0.19, ze), (xm, yt + 0.19, zr - 0.12)]
    kit.p("wood_dark", "ext", lmw=0.6).face([(x, y, z) for x, y, z in tri][::-1])
    kit.p("signs", "ext").panel((xm, yt + 0.17, ze + 0.55), "y", 0.78, 0.78, cell=kit.cell("signs", "logo"))
    kit.light("spot", (xm, yt - 0.6, ze - 0.2), energy=18.0, color=(1.0, 0.85, 0.66), aim=(xm, yt, ze + 0.6), angle=70, blend=0.6)
    # the roof: two standing-seam planes from the gable to the wall, the ridge cap
    yb = y0 + 0.05
    for s in (-1, 1):
        e = (xm + s * (hw + 0.45), ze - 0.18)
        r = (xm, zr + 0.12)
        quad = [(e[0], yf - 0.15, e[1]), (r[0], yf - 0.15, r[1]), (r[0], yb, r[1]), (e[0], yb, e[1])]
        if s > 0:
            quad = quad[::-1]
        R.face(quad)
        R.face([(x, y, z - 0.06) for x, y, z in quad[::-1]])
        for k in range(1, 9):
            t = k / 9
            xx, zz = e[0] + (r[0] - e[0]) * t, e[1] + (r[1] - e[1]) * t
            R.box((xx - 0.012, yf - 0.15, zz - 0.005), (xx + 0.012, yb, zz + 0.035))
    R.box((xm - 0.08, yf - 0.16, zr + 0.06), (xm + 0.08, yb, zr + 0.16), bevel=0.02)
    # downlight in the beam over the doors
    kit.p("signs", "ext").panel((xm, yf + 0.3, ze - 0.305), "z", 0.12, 0.12, cell=kit.cell("signs", "led_warm"))
    kit.light("spot", (xm, yf + 1.0, ze - 0.35), energy=40.0, color=(1.0, 0.86, 0.68), aim=(xm, yf + 1.0, 0.0), angle=90, blend=0.7)


def V2(a, b):
    dx, dz = b[0] - a[0], b[2] - a[2]
    L = math.hypot(dx, dz)
    return (dx / L, dz / L)


def gooseneck(kit, at):
    """A black barn light on a gooseneck arm, shining down the board-and-batten."""
    x, y, z = at
    B = kit.p("black", "ext", lmw=0.2)
    B.box((x - 0.07, y - 0.02, z - 0.07), (x + 0.07, y, z + 0.07))
    B.tube([(x, y - 0.02, z), (x, y - 0.25, z + 0.12), (x, y - 0.45, z + 0.05)], 0.015, sides=6)
    B.lathe([(0.0, 0.1), (0.04, 0.1), (0.06, 0.06), (0.2, -0.05), (0.19, -0.06)], c=(x, y - 0.48), z=z - 0.02, seg=14, cap_top=False)
    kit.p("signs", "ext").panel((x, y - 0.48, z - 0.065), "z", 0.22, 0.22, cell=kit.cell("signs", "led_warm"))
    kit.light("spot", (x, y - 0.48, z - 0.09), energy=25.0, color=(1.0, 0.85, 0.66), aim=(x, y - 0.1, z - 2.0), angle=110, blend=0.8)


def storefront(kit, p):
    """Black aluminium storefront: the two glass bays (sill at the stone base, a transom bar), the
    entry with fixed sidelites and a pair of sliding leaves parked open behind them, the header with
    the door operator."""
    y0, f, gt = p["sy0"], p["floor"], p["glass_top"]
    G = kit.p("glass", "ext")
    Bk = kit.p("black", "ext", lmw=0.5)
    gy = y0 + 0.07                       # the glass plane (in the wall's outer half)
    m = 0.05                             # frame member face width
    for (a0, a1) in (p["bay_a"], p["bay_b"]):
        G.box((a0, gy - 0.004, p["base_h"]), (a1, gy + 0.004, gt), skip="")
        n = max(2, round((a1 - a0) / 1.6))
        for k in range(n + 1):
            x = a0 + k * (a1 - a0) / n
            Bk.box((x - m, gy - 0.06, p["base_h"]), (x + m, gy + 0.06, gt), skip="")
        for z in (p["base_h"] + 0.03, 2.45, gt - 0.03):
            Bk.box((a0, gy - 0.06, z - m), (a1, gy + 0.06, z + m), skip="")
    e0, e1 = p["entry"]
    d0, d1 = p["door"]
    for (a0, a1) in ((e0, d0), (d1, e1)):
        G.box((a0, gy - 0.004, f + 0.12), (a1, gy + 0.004, 2.45), skip="")
        Bk.box((a0, gy - 0.06, f), (a1, gy + 0.06, f + 0.12), skip="")
        Bk.box((a0 - m, gy - 0.06, f), (a0 + m, gy + 0.06, gt), skip="")
        Bk.box((a1 - m, gy - 0.06, f), (a1 + m, gy + 0.06, gt), skip="")
    # the transom over the doors and the operator header
    G.box((e0, gy - 0.004, 2.55), (e1, gy + 0.004, gt), skip="")
    Bk.box((e0, gy - 0.07, 2.45), (e1, gy + 0.09, 2.6), bevel=0.01)
    Bk.box((e0, gy - 0.06, gt - m), (e1, gy + 0.06, gt + m), skip="")
    kit.p("graphite", "ext", lmw=0.2).box((-6.75, gy - 0.1, 2.38), (-6.45, gy - 0.07, 2.45))
    # the sliding leaves (open): behind each sidelite, a framed glass panel
    for (a0, a1), s in (((d0 - 1.2, d0), -1), ((d1, d1 + 1.2), 1)):
        yy = gy + 0.14
        G.box((a0 + 0.06, yy - 0.004, f + 0.12), (a1 - 0.06, yy + 0.004, 2.4), skip="")
        for (b0, b1, z0, z1) in ((a0, a0 + 0.06, f, 2.4), (a1 - 0.06, a1, f, 2.4), (a0, a1, f, f + 0.12), (a0, a1, 2.34, 2.4)):
            Bk.box((b0, yy - 0.03, z0), (b1, yy + 0.03, z1), skip="")
        kit.p("steel", "ext", lmw=0.1).box((a1 - 0.12 if s < 0 else a0 + 0.08, yy - 0.05, 0.9), (a1 - 0.08 if s < 0 else a0 + 0.12, yy - 0.03, 1.3))
    # the walk-off mat at the threshold (inside) and the threshold bar
    kit.p("steel", "ext", lmw=0.2).box((d0, y0, f), (d1, y0 + 0.25, f + 0.01))
    kit.collide((p["bay_a"][0], y0, 0), (p["bay_a"][1], y0 + 0.25, p["glass_top"]))
    kit.collide((p["bay_b"][0], y0, 0), (p["bay_b"][1], y0 + 0.25, p["glass_top"]))
    kit.collide((e0, y0, 0), (d0, y0 + 0.3, gt))
    kit.collide((d1, y0, 0), (e1, y0 + 0.3, gt))
    kit.collide((e0, y0, 2.4), (e1, y0 + 0.25, gt))


def service_door(kit, p):
    """The stockroom's steel back door on the east wall, propped open on a cinder block."""
    x1 = p["sx1"]
    a0, a1 = p["back_door"]
    f = p["floor"]
    D = kit.p("sage", "ext", lmw=0.5)
    Bk = kit.p("black", "ext", lmw=0.3)
    # frame
    for (b0, b1) in ((a0 - 0.06, a0), (a1, a1 + 0.06)):
        Bk.box((x1 - 0.02, b0, f), (x1 + 0.02, b1, 2.36))
    Bk.box((x1 - 0.02, a0 - 0.06, 2.3), (x1 + 0.02, a1 + 0.06, 2.36))
    # the leaf, hinged at a1, swung 75 degrees out (to +x)
    with kit.at((x1 + 0.02, a1, f), rot=-75):
        D.box((0.0, -(a1 - a0) + 0.01, 0.0), (0.05, 0.0, 2.12), bevel=0.01)
        kit.p("steel", "ext", lmw=0.1).box((0.05, -(a1 - a0) + 0.08, 0.95), (0.08, -(a1 - a0) + 0.2, 1.0))
    kit.collide((x1, a1 - 0.1, f), (x1 + 0.95, a1 + 0.3, 2.2))
    # the cinder block holding it
    kit.p("concrete_grey", "ext", lmw=0.2).box((x1 + 0.55, a0 + 0.25, f), (x1 + 0.95, a0 + 0.45, f + 0.2), bevel=0.01)
    # the wall pack over the door (on: the back lot's only light)
    kit.p("graphite", "ext", lmw=0.2).box((x1, (a0 + a1) / 2 - 0.15, 2.6), (x1 + 0.16, (a0 + a1) / 2 + 0.15, 2.85), bevel=0.02)
    kit.p("signs", "ext").panel((x1 + 0.161, (a0 + a1) / 2, 2.66), "X", 0.22, 0.1, cell=kit.cell("signs", "led_warm"))
    kit.light("spot", (x1 + 0.2, (a0 + a1) / 2, 2.62), energy=60.0, color=(1.0, 0.82, 0.6), aim=(x1 + 3.0, (a0 + a1) / 2, 0.0), angle=120, blend=0.8)
    # meters and the electrical panel, conduit up the wall
    G = kit.p("lightgrey", "ext", lmw=0.3)
    G.box((x1, 12.2, 1.1), (x1 + 0.2, 12.9, 1.9), bevel=0.01)
    G.box((x1, 13.2, 1.3), (x1 + 0.12, 13.5, 1.7), bevel=0.01)
    kit.p("steel", "ext", lmw=0.1).cyl((x1 + 0.15, 13.35), 0.1, 1.5, 1.52, seg=12)
    kit.p("steel", "ext", lmw=0.1).tube([(x1 + 0.05, 12.55, 1.9), (x1 + 0.05, 12.55, p["parapet"] - 0.2)], 0.02, sides=6)
    kit.collide((x1, 12.2, 0), (x1 + 0.2, 13.5, 1.9))


# ------------------------------------------------------------------ the yard round the store
def yard(kit, p, rng):
    y0, x1 = p["sy0"], p["sx1"]
    # on the front sidewalk: the ice merchandiser and the firewood west of the entry, a bench and a
    # trash can by the door, the propane cage in front of the solid east pier; bollards
    with kit.at((-14.2, 1.85, p["floor"])):
        OUT.ice_chest(kit)
    with kit.at((-12.2, 1.85, p["floor"])):
        OUT.firewood_rack(kit, rng)
    with kit.at((-3.0, 2.55, p["floor"]), rot=180):
        OUT.bench(kit)
    with kit.at((-9.35, 2.6, p["floor"])):
        OUT.trash_can(kit)
    with kit.at((2.8, 2.15, p["floor"])):
        OUT.propane_cage(kit, rng)
    for x in (-15.4, -11.0, -8.0, -5.0, -1.0, 1.4, 4.6):
        with kit.at((x, 1.3, p["floor"])):
            OUT.bollard(kit, 0.95, "black", 0.08)
    # the side lot: the air machine at the east edge
    with kit.at((19.6, 3.0, 0.0), rot=90):
        OUT.air_machine(kit)
    # the back lot: the dumpster enclosure, the van by the stockroom door (nose south, rear doors
    # open toward the door)
    with kit.at((17.7, 17.0, 0.0)):
        OUT.dumpster_enclosure(kit, rng)
    with kit.at((8.6, 13.4, 0.0), rot=-90):
        OUT.van(kit, rng)


# ------------------------------------------------------------------ the far version
def lod1(kit, p):
    """LOD1: the lot, the canopy, the islands' pumps, the store's box, its glass and sign; ~1k triangles."""
    Z = "lod1"
    A = kit.p("asphalt", Z)
    C = kit.p("concrete", Z)
    W = kit.p("white", Z)
    S = kit.p("stone", Z)
    Sd = kit.p("siding", Z)
    G = kit.p("glass_dark", Z)
    Sg = kit.p("signs", Z)
    A.box((p["x0"], p["y0"], -0.1), (p["x1"], p["y1"], 0.0), skip="zxXyY")
    C.box((p["cx0"] - 1.5, p["cy0"] - 1.5, -0.1), (p["cx1"] + 1.5, p["cy1"] + 1.4, 0.005), skip="zxXyY")
    W.box((p["cx0"], p["cy0"], p["cz"]), (p["cx1"], p["cy1"], p["cz"] + p["fascia"]))
    Sg.panel(((p["cx0"] + p["cx1"]) / 2, p["cy0"] - 0.01, p["cz"] + 0.2), "y", p["cx1"] - p["cx0"], 0.12, cell=kit.cell("signs", "band"))
    Sg.panel(((p["cx0"] + p["cx1"]) / 2, p["cy0"] + 0.01, p["cz"] - 0.01), "z", p["cx1"] - p["cx0"] - 1, p["cy1"] - p["cy0"] - 1, cell=kit.cell("signs", "led"))
    for x in (p["islands"][0], p["islands"][-1]):
        for y in (p["island_y"] - 2.55, p["island_y"] + 2.95):
            W.box((x - 0.3, y - 0.3, 0), (x + 0.3, y + 0.3, p["cz"]), skip="zZ")
    for x in p["islands"]:
        W.box((x - 0.3, p["island_y"] - 0.65, 0), (x + 0.3, p["island_y"] + 0.65, 2.3), skip="z")
    x0, x1, y0, y1 = p["sx0"], p["sx1"], p["sy0"], p["sy1"]
    S.box((x0, y0, 0), (x1, y1, p["base_h"]), skip="zZ")
    Sd.box((x0, y0, p["base_h"]), (x1, y1, p["parapet"]), skip="z")
    for (a0, a1) in (p["bay_a"], p["entry"], p["bay_b"]):
        G.panel(((a0 + a1) / 2, y0 - 0.01, (p["base_h"] + p["glass_top"]) / 2), "y", a1 - a0, p["glass_top"] - p["base_h"])
    kit.p("charcoal", Z).box((p["bay_a"][0] - 0.4, y0 - 1.75, 3.15), (p["bay_b"][1] + 0.4, y0, 3.3))
    kit.p("charcoal", Z).box((16.0, p["y0"] + 0.3, 0), (19.0, p["y0"] + 1.2, 3.3))
    Sg.panel((17.5, p["y0"] + 0.29, 1.55), "y", 2.4, 1.2, cell=kit.cell("signs", "price"))
