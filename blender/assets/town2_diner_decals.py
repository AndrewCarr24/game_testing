"""The diner's decal atlas (T_Town2_Diner_Decals, 512 px, numpy): the small printed and painted
surfaces on one texture and one material: the menu letterboard, the bulletin board's cork and
papers, the clock face, the wall boxes' title strips, the jukebox's selection panel, pie tops,
order tickets, an old photo, a flyer, griddle steel, patties and buns. Nothing on it is readable
text: letter strips are blank bars, papers carry grey scribble lines.

DECALS: region name -> (x0, y0, x1, y1) in pixels of the 512 square (y0 = the bottom row).
uv(name, u, v): the atlas UV of (u, v) in 0..1 inside a region.
"""
import math

import numpy as np

DECALS = {
    "menu": (0, 0, 256, 128),
    "cork": (256, 0, 384, 128),
    "paper0": (384, 0, 448, 64), "paper1": (448, 0, 512, 64), "paper2": (384, 64, 448, 128), "paper3": (448, 64, 512, 128),
    "clock": (0, 128, 128, 256),
    "wallbox": (128, 128, 256, 192),
    "grille": (128, 192, 256, 256),
    "juke": (256, 128, 512, 256),
    "pie0": (0, 256, 128, 384), "pie1": (128, 256, 256, 384), "pie2": (256, 256, 384, 384), "cake": (384, 256, 512, 384),
    "ticket": (0, 384, 64, 512),
    "photo": (64, 384, 192, 512),
    "flyer": (192, 384, 320, 512),
    "griddle": (320, 384, 384, 448),
    "plan": (320, 448, 448, 512),     # a pencil sketch of a floor plan on squared paper (the estate's)
    "patty": (448, 384, 512, 448), "bun": (448, 448, 512, 512),
}


def uv(name, u, v):
    x0, y0, x1, y1 = DECALS[name]
    # (half a texel in from the region's edge so filtering stays inside it)
    u = 0.01 + 0.98 * u
    v = 0.01 + 0.98 * v
    return ((x0 + (x1 - x0) * u) / 512, (y0 + (y1 - y0) * v) / 512)


def make(n=512):
    rng = np.random.default_rng(77)
    out = np.zeros((n, n, 3), np.float32)
    f = n / 512

    def reg(name):
        x0, y0, x1, y1 = DECALS[name]
        return slice(int(y0 * f), int(y1 * f)), slice(int(x0 * f), int(x1 * f))

    def grid(name):
        ys, xs = reg(name)
        h, w = ys.stop - ys.start, xs.stop - xs.start
        return np.meshgrid((np.arange(w) + 0.5) / w, (np.arange(h) + 0.5) / h)

    # menu letterboard: grooved black felt, rows of white letter strips, prices on the right
    ys, xs = reg("menu")
    u, v = grid("menu")
    m = np.ones(u.shape + (3,), np.float32) * 0.02
    m *= (1 + 0.6 * (np.sin(v * 128 * math.pi) > 0.6))[..., None]
    for row in range(11):
        vy = 0.08 + row * 0.082
        if row in (0, 6):
            hit = (np.abs(v - vy) < 0.03) & (u > 0.3) & (u < 0.7) & (np.sin(u * 300) > -0.2)
            m[hit] = np.array([0.85, 0.2, 0.15])
            continue
        x = 0.05
        while x < 0.8:
            ln = 0.03 + 0.08 * rng.random()
            hit = (u > x) & (u < min(x + ln, 0.8)) & (np.abs(v - vy) < 0.02) & (np.sin(u * 900) > -0.4)
            m[hit] = 0.85
            x += ln + 0.025
        hit = (u > 0.87) & (u < 0.94) & (np.abs(v - vy) < 0.02) & (np.sin(u * 900) > -0.4)
        m[hit] = 0.85
    out[ys, xs] = m
    # cork
    ys, xs = reg("cork")
    u, v = grid("cork")
    c = np.ones(u.shape + (3,), np.float32) * np.array([0.34, 0.20, 0.09], np.float32)
    out[ys, xs] = c * (0.75 + 0.5 * rng.random(u.shape + (1,)))
    # papers: white, yellow, pink, pale blue; faint scribble lines (not letters)
    for i, col in enumerate([(0.82, 0.81, 0.77), (0.85, 0.76, 0.35), (0.85, 0.55, 0.6), (0.55, 0.7, 0.85)]):
        ys, xs = reg(f"paper{i}")
        u, v = grid(f"paper{i}")
        pp = np.ones(u.shape + (3,), np.float32) * np.array(col, np.float32)
        for row in range(7):
            vy = 0.8 - row * 0.1
            ln = 0.35 + 0.45 * rng.random()
            hit = (np.abs(v - vy) < 0.014) & (u > 0.1) & (u < 0.1 + ln) & (np.sin(u * 140 + row) > -0.3)
            pp[hit] *= 0.45
        if i == 0:
            hit = (u > 0.15) & (u < 0.85) & (v > 0.05) & (v < 0.3)
            pp[hit] = (0.15 + 0.3 * rng.random((int(hit.sum()), 1))).astype(np.float32)
        out[ys, xs] = pp
    # clock: cream face, hour and minute ticks, no numerals; a chrome bezel; hands at ten to five
    ys, xs = reg("clock")
    u, v = grid("clock")
    x, y = u - 0.5, v - 0.5
    r = np.sqrt(x * x + y * y)
    a = np.arctan2(y, x)
    cl = np.ones(u.shape + (3,), np.float32) * np.array([0.8, 0.77, 0.68], np.float32)
    tick = (r > 0.36) & (r < 0.45) & (np.abs(((a / (2 * math.pi) * 12) % 1) - 0.5) > 0.47)
    mtick = (r > 0.42) & (r < 0.45) & (np.abs(((a / (2 * math.pi) * 60) % 1) - 0.5) > 0.44)
    cl[tick | mtick] = 0.03
    cl[r > 0.47] = np.array([0.6, 0.6, 0.62])
    cl[r < 0.025] = 0.03
    for ang, ln, wd in ((math.radians(90 - 145), 0.25, 0.02), (math.radians(90 - 300), 0.37, 0.012)):
        d = x * math.cos(ang) + y * math.sin(ang)
        q = np.abs(-x * math.sin(ang) + y * math.cos(ang))
        cl[(d > -0.03) & (d < ln) & (q < wd)] = 0.03
    out[ys, xs] = cl
    # wall box: two pages of title strips (cream tabs with red rules)
    ys, xs = reg("wallbox")
    u, v = grid("wallbox")
    wb = np.ones(u.shape + (3,), np.float32) * 0.05
    for side in (0, 1):
        for row in range(10):
            cy = 0.06 + row * 0.095
            hit = (np.abs(u - (0.26 + 0.48 * side)) < 0.2) & (np.abs(v - cy) < 0.04)
            wb[hit] = np.array([0.82, 0.78, 0.68])
            wb[hit & (np.abs(v - cy) < 0.006)] = np.array([0.6, 0.05, 0.04])
    out[ys, xs] = wb
    ys, xs = reg("grille")
    u, v = grid("grille")
    g = 0.25 + 0.15 * ((np.sin(u * 160) > 0) ^ (np.sin(v * 160) > 0))
    out[ys, xs] = (g[..., None] * np.array([0.6, 0.45, 0.3])).astype(np.float32)
    # jukebox panel: amber selection cards in rows on a dark ground
    ys, xs = reg("juke")
    u, v = grid("juke")
    jk = np.ones(u.shape + (3,), np.float32) * 0.06
    for row in range(8):
        for col in range(4):
            hit = (np.abs(u - (0.2 + col * 0.2)) < 0.085) & (np.abs(v - (0.12 + row * 0.105)) < 0.035)
            jk[hit] = np.array([0.85, 0.7, 0.45])
            jk[hit & (np.abs(v - (0.12 + row * 0.105)) < 0.007)] = np.array([0.5, 0.1, 0.05])
    out[ys, xs] = jk
    # pies from above: cherry lattice (a slice gone), coconut cream, lemon meringue; a layer cake
    for name, crust, fill, kind in (("pie0", (0.6, 0.38, 0.16), (0.32, 0.02, 0.03), "lattice"), ("pie1", (0.62, 0.42, 0.2), (0.82, 0.8, 0.72), "cream"),
                                    ("pie2", (0.62, 0.42, 0.2), (0.85, 0.72, 0.35), "meringue"), ("cake", (0.25, 0.12, 0.06), (0.78, 0.74, 0.68), "cake")):
        ys, xs = reg(name)
        u, v = grid(name)
        x, y = u - 0.5, v - 0.5
        r = np.sqrt(x * x + y * y)
        a = np.arctan2(y, x)
        pc = np.ones(u.shape + (3,), np.float32) * np.array([0.72, 0.72, 0.70], np.float32)
        top = np.ones(u.shape + (3,), np.float32) * np.array(fill, np.float32)
        if kind == "lattice":
            lat = (np.abs(((x + y) * 9) % 1 - 0.5) < 0.16) | (np.abs(((x - y) * 9) % 1 - 0.5) < 0.16)
            top[lat] = np.array(crust)
        elif kind == "meringue":
            top *= (0.8 + 0.3 * (np.sin(a * 14 + r * 40) * 0.5 + 0.5))[..., None]
            top[r < 0.3] *= np.array([1.05, 1.0, 0.9])
        elif kind == "cream":
            top *= (0.88 + 0.14 * rng.random(u.shape))[..., None]
        else:
            top *= (0.92 + 0.1 * np.sin(a * 24))[..., None]
        inner = r < 0.46
        pc[inner] = top[inner]
        rim = (r > 0.39) & (r < 0.46)
        if kind != "cake":
            pc[rim] = (np.array(crust, np.float32) * (0.85 + 0.3 * np.sin(a * 40) ** 2)[..., None])[rim]
        cuts = (np.abs(((a / (2 * math.pi)) * 8) % 1 - 0.5) > 0.485) & (r < 0.45)
        pc[cuts] *= 0.7
        if name == "pie0":
            wedge = (a > 0) & (a < 2 * math.pi / 8) & (r < 0.46)
            pc[wedge] = np.array([0.66, 0.66, 0.64])
        out[ys, xs] = pc
    ys, xs = reg("ticket")
    u, v = grid("ticket")
    tk = np.ones(u.shape + (3,), np.float32) * np.array([0.84, 0.83, 0.78], np.float32)
    for row in range(9):
        hit = (np.abs(v - (0.85 - row * 0.085)) < 0.01) & (u > 0.12) & (u < 0.3 + 0.55 * rng.random())
        tk[hit] *= 0.5
    tk[v > 0.93] = np.array([0.7, 0.2, 0.2])
    out[ys, xs] = tk
    # an old sepia photograph: a ridge line over a valley with a road; a white border
    ys, xs = reg("photo")
    u, v = grid("photo")
    ridge = 0.55 + 0.12 * np.sin(u * 7.0) + 0.05 * np.sin(u * 23 + 1)
    ph = np.where(v > ridge, 0.62 + 0.2 * v, 0.22 + 0.25 * v)
    ph = ph + 0.12 * ((np.abs(v - (0.2 + 0.6 * (u - 0.5) ** 2)) < 0.012) & (v < ridge))
    ph = ph * (0.92 + 0.08 * rng.random(u.shape))
    ph[(u < 0.06) | (u > 0.94) | (v < 0.06) | (v > 0.94)] = 0.85
    out[ys, xs] = (ph[..., None] * np.array([1.0, 0.9, 0.75])).astype(np.float32)
    ys, xs = reg("flyer")
    u, v = grid("flyer")
    fl = np.ones(u.shape + (3,), np.float32) * np.array([0.8, 0.79, 0.74], np.float32)
    fl[(u > 0.1) & (u < 0.9) & (v > 0.45) & (v < 0.88)] = np.array([0.25, 0.4, 0.3])
    for row in range(4):
        fl[(np.abs(v - (0.35 - row * 0.075)) < 0.02) & (u > 0.12) & (u < 0.88 - 0.2 * (row % 2))] = np.array([0.35, 0.35, 0.36])
    out[ys, xs] = fl
    ys, xs = reg("griddle")
    u, v = grid("griddle")
    gr = 0.05 + 0.04 * rng.random(u.shape) + 0.07 * np.exp(-((u - 0.4) ** 2 + (v - 0.5) ** 2) * 6)
    out[ys, xs] = (gr[..., None] * np.array([1.0, 0.9, 0.8])).astype(np.float32)
    # the sketch: the mansion's ground floor (blender/levels/plan.py ROOMS, copied: x -26..26,
    # y -20..20), the courtyard, the front door and a route drawn in red from the west lawn
    ys, xs = reg("plan")
    u, v = grid("plan")
    sk = np.ones(u.shape + (3,), np.float32) * np.array([0.8, 0.79, 0.72], np.float32)
    sk[(np.abs(((u * 24) % 1) - 0.5) > 0.47) | (np.abs(((v * 12) % 1) - 0.5) > 0.45)] *= 0.9
    rooms = [(-8, -20, 8, -10.5), (-13.5, -20, -8, -10.5), (8, -20, 13.5, -10.5), (-26, -20, -13.5, -10.5), (-26, -10.5, -13.5, 10.5),
             (-26, 10.5, -10, 20), (-10, 10.5, 8, 20), (8, 10.5, 13.5, 20), (13.5, 10.5, 26, 20), (13.5, 0, 26, 10.5), (13.5, -20, 26, 0),
             (-13.5, -10.5, 13.5, -7), (-13.5, 7, 13.5, 10.5), (-13.5, -7, -10, 7), (10, -7, 13.5, 7), (-10, -7, 10, 7)]
    def to_uv(x, y):
        return 0.08 + 0.84 * (x + 26) / 52, 0.1 + 0.8 * (y + 20) / 40
    lw = 0.006
    for x0, y0, x1, y1 in rooms:
        a0, b0 = to_uv(x0, y0)
        a1, b1 = to_uv(x1, y1)
        wob = 0.002 * np.sin(u * 90 + x0) + 0.002 * np.sin(v * 70 + y0)
        edge = (((np.abs(u - a0 + wob) < lw) | (np.abs(u - a1 + wob) < lw)) & (v > b0 - lw) & (v < b1 + lw)) | \
               (((np.abs(v - b0 + wob) < lw * 2) | (np.abs(v - b1 + wob) < lw * 2)) & (u > a0 - lw) & (u < a1 + lw))
        sk[edge] = np.array([0.22, 0.22, 0.24])
    # the route: across the west lawn to the great room's glass, an X on the stair hall
    pts = [(-40, 0), (-30, 2), (-26, 3), (-18, 3), (-12, -4), (0, -14)]
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        ua, va = to_uv(xa, ya)
        ub, vb = to_uv(xb, yb)
        t = np.clip(((u - ua) * (ub - ua) + (v - va) * (vb - va)) / ((ub - ua) ** 2 + (vb - va) ** 2 + 1e-9), 0, 1)
        d = np.sqrt((u - ua - t * (ub - ua)) ** 2 + ((v - va - t * (vb - va)) * 0.5) ** 2)
        sk[(d < 0.006) & (np.sin((u + v) * 200) > -0.5)] = np.array([0.6, 0.06, 0.04])
    ux, vx_ = to_uv(0, -14)
    cross = (np.abs(np.abs(u - ux) - np.abs(v - vx_) * 0.5) < 0.006) & (np.abs(u - ux) < 0.03)
    sk[cross] = np.array([0.6, 0.06, 0.04])
    out[ys, xs] = sk
    ys, xs = reg("patty")
    u, v = grid("patty")
    out[ys, xs] = (np.array([0.12, 0.05, 0.025]) * (0.6 + 0.8 * rng.random(u.shape + (1,)))).astype(np.float32)
    ys, xs = reg("bun")
    u, v = grid("bun")
    bn = np.ones(u.shape + (3,), np.float32) * np.array([0.55, 0.3, 0.1], np.float32)
    bn[rng.random(u.shape) > 0.985] = np.array([0.8, 0.75, 0.6])
    out[ys, xs] = bn
    return out
