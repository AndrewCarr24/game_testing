"""Potting shed, 4.2 x 3.0 m: weathered-teak board cladding on a low concrete slab, a dark
metal mono-pitch roof with deep overhang (higher at the front, which faces -Y), a glazed
double door and a window in dark-metal frames, a gutter with downpipe into a galvanised
water butt, and a potting bench with pots visible through the glass. Origin: floor centre.
Units are metres."""
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

NAME = "KgardenShed"

P = dict(
    name=NAME,
    width=4.2,
    depth=3.0,
    wall=0.12,
    h_front=2.7,
    h_back=2.3,
    slab=0.12,
    seed=4,
)


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rng = random.Random(p["seed"])
    B = kc.Builder(n)
    teak = B.mat("Teak", outdoor.teak(), tile=0.5)
    metal = B.mat("Metal", outdoor.dark_metal())
    glass = B.mat("Glass", outdoor.glass())
    conc = B.mat("Slab", outdoor.concrete())
    stone = B.mat("Stone", outdoor.stone(), tile=2.0)
    pot = B.mat("Pot", kc.terracotta())
    leaf = B.mat("Leaf", kc.leaf_light())
    butt = B.mat("Butt", kc.galvanised())
    C = kc.CELL

    W, D, t = p["width"], p["depth"], p["wall"]
    hw, hd = W / 2, D / 2
    z0 = p["slab"]
    hf, hb = p["h_front"], p["h_back"]

    # slab and a stone step at the door
    B.box(conc, (0, 0, z0 / 2), (W + 0.4, D + 0.4, z0), cell=C, cell_on=("+z",), skip=("-z",))
    B.box(stone, (1.15, -hd - 0.45, 0.04), (1.6, 0.6, 0.08), skip=("-z",))

    # --- walls ---------------------------------------------------------------
    def wall_box(x0, x1, za, zb):
        B.box(teak, ((x0 + x1) / 2, -hd + t / 2, (za + zb) / 2), (x1 - x0, t, zb - za), cell=C, skip=("-z", "+z"))
    dx0, dx1 = 0.5, 1.8          # door opening
    wx0, wx1 = -1.8, -0.5        # window opening
    wz0, wz1 = 0.95, 2.0
    dz = 2.15
    top = z0 + hf
    base = z0
    wall_box(-hw, wx0, base, top)
    wall_box(wx0, wx1, base, base + wz0)
    wall_box(wx0, wx1, base + wz1, top)
    wall_box(wx1, dx0, base, top)
    wall_box(dx1, hw, base, top)
    wall_box(dx0, dx1, base + dz, top)
    # back wall
    B.box(teak, (0, hd - t / 2, z0 + hb / 2), (W - 2 * t, t, hb), cell=C, skip=("-z", "+z", "-x", "+x"))
    # side walls: trapezoids, thickness t
    for sx in (-1, 1):
        xo, xi = sx * hw, sx * (hw - t)
        if sx > 0:
            B.quad(teak, (xo, -hd, z0), (xo, hd, z0), (xo, hd, z0 + hb), (xo, -hd, z0 + hf), cell=C)
            B.quad(teak, (xi, hd, z0), (xi, -hd, z0), (xi, -hd, z0 + hf), (xi, hd, z0 + hb), cell=C)
        else:
            B.quad(teak, (xo, hd, z0), (xo, -hd, z0), (xo, -hd, z0 + hf), (xo, hd, z0 + hb), cell=C)
            B.quad(teak, (xi, -hd, z0), (xi, hd, z0), (xi, hd, z0 + hb), (xi, -hd, z0 + hf), cell=C)

    # --- door and window --------------------------------------------------------
    yf = -hd - 0.02
    fb = 0.06                                  # frame bar section
    # door: jambs, head, mid rail, centre meeting stile, glass
    for x in (dx0 + 0.03, dx1 - 0.03):
        B.bar(metal, (x, yf, base), (x, yf, base + dz), fb, 0.07)
    B.bar(metal, (dx0, yf, base + dz - 0.03), (dx1, yf, base + dz - 0.03), 0.07, 0.07)
    B.bar(metal, ((dx0 + dx1) / 2, yf, base), ((dx0 + dx1) / 2, yf, base + dz), 0.05, 0.07)
    B.bar(metal, (dx0, yf, base + 0.9), (dx1, yf, base + 0.9), 0.05, 0.05)
    B.bar(metal, (dx0, yf, base + 0.03), (dx1, yf, base + 0.03), 0.07, 0.07)
    B.quad(glass, (dx0, yf + 0.01, base), (dx1, yf + 0.01, base), (dx1, yf + 0.01, base + dz), (dx0, yf + 0.01, base + dz))
    # window: frame and one mullion
    for x in (wx0 + 0.03, wx1 - 0.03):
        B.bar(metal, (x, yf, base + wz0), (x, yf, base + wz1), fb, 0.07)
    for z in (base + wz0 + 0.03, base + wz1 - 0.03):
        B.bar(metal, (wx0, yf, z), (wx1, yf, z), 0.07, 0.07)
    B.bar(metal, ((wx0 + wx1) / 2, yf, base + wz0), ((wx0 + wx1) / 2, yf, base + wz1), 0.04, 0.06)
    B.quad(glass, (wx0, yf + 0.01, base + wz0), (wx1, yf + 0.01, base + wz0), (wx1, yf + 0.01, base + wz1), (wx0, yf + 0.01, base + wz1))
    # door pulls
    for x in (dx0 + 0.18, dx1 - 0.18):
        B.bar(metal, (x, yf - 0.04, base + 0.9), (x, yf - 0.04, base + 1.3), 0.025, 0.025)

    # --- roof --------------------------------------------------------------------
    ang = math.degrees(math.atan2(hf - hb, D))
    over_f, over_s, over_b = 0.45, 0.3, 0.3
    roof_len = (D + over_f + over_b) / math.cos(math.radians(ang))
    zc = z0 + (hf + hb) / 2 + 0.07 + (over_f - over_b) / 2 * math.tan(math.radians(ang)) * 0
    B.box(metal, (0, (over_b - over_f) / 2, zc), (W + 2 * over_s, roof_len, 0.1), rot=(-ang, 0, 0), cell=C, cell_on=("+z",))
    # fascia / gutter on the low (back) edge
    gz = zc - 0.5 * roof_len * math.sin(math.radians(ang)) * 1.0
    B.box(metal, (0, hd + over_b - 0.05, z0 + hb - 0.02), (W + 2 * over_s, 0.1, 0.1), skip=("-z",))

    # downpipe and water butt at the back-east corner
    bx = hw + 0.32
    B.bar(metal, (hw + 0.1, hd + over_b - 0.1, z0 + 0.62), (hw + 0.1, hd + over_b - 0.1, z0 + hb - 0.05), 0.08, 0.08)
    B.bar(metal, (hw + 0.1, hd + over_b - 0.1, z0 + 0.62), (bx, hd + 0.4, z0 + 0.82), 0.07, 0.07)
    B.cyl(butt, (bx, hd + 0.4, z0), 0.34, 0.8, n=10)
    B.cyl(metal, (bx, hd + 0.4, z0 + 0.8), 0.36, 0.03, n=10)

    # --- inside: potting bench along the back wall, pots, trays ------------------------
    bz = z0 + 0.88
    B.box(teak, (0, hd - t - 0.3, bz - 0.03), (3.4, 0.55, 0.06), cell=3.0, skip=("-z",))
    for x in (-1.6, 1.6):
        B.bar(metal, (x, hd - t - 0.3, z0), (x, hd - t - 0.3, bz - 0.06), 0.5, 0.05)
    for i, x in enumerate((-0.6, 0.6)):
        r = 0.11
        B.cyl(pot, (x, hd - t - 0.3, bz), r, r * 1.4, n=5, r_top=r * 1.2)
        B.dome(leaf, (x, hd - t - 0.3, bz + r * 1.4), r * 1.4, 0.2, n=4, rng=rng)

    return B.finish()


if __name__ == "__main__":
    root, parts = build()
    kc.report(root, parts)
