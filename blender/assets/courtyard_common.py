"""Shared building blocks for the courtyard_* assets (not an asset itself): textures
(limestone for stone furniture and coping, the courtyard floor's sandstone paving,
weathered teak, the foliage atlas: olive sprigs, golden grass, sedge, fern, maple, star
jasmine), materials and a few geometry helpers (bevelled pieces merged into one mesh,
lathes, leaf cards and bent leaf strips). Textures are generated with numpy only when
missing (the atlas: delete T_Courtyard_Foliage_BaseColor.png or call foliage(force=True)
after changing a cell painter)."""
import importlib
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

TEX = textures.TEX_DIR


# ----------------------------------------------------------------------------- textures

def _smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def limestone(n=1024, seed=41, force=False):
    """Honed limestone paving, one tile = 2 m: 1.0 x 0.5 m slabs in running bond,
    fine joints, soft clouding, tiny pits and the odd warm vein."""
    name = "T_Courtyard_Limestone_BaseColor"
    path = os.path.join(TEX, name + ".png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    u = (np.arange(n)[None, :] + 0.5) / n * 2.0 * np.ones((n, 1))      # metres
    v = (np.arange(n)[:, None] + 0.5) / n * 2.0 * np.ones((1, n))
    row = np.floor(v / 0.5).astype(int)
    shift = np.where(row % 2 == 1, 0.5, 0.0)
    su = u - shift
    col = np.floor(su / 1.0).astype(int)
    lu = su - col
    lv = v - row * 0.5
    du = np.minimum(lu, 1.0 - lu)
    dv = np.minimum(lv, 0.5 - lv)
    d = np.minimum(du, dv)
    joint = 1.0 - _smooth(0.0035, 0.0075, d)
    sid = (row * 7 + (col % 2) * 3 + (row % 2) * 5) % 16
    tone = rng.uniform(-1, 1, 16)[sid]
    cloud = textures._noise(n, 1.0, 1.0, 2.1, rng) * 0.5 + 0.5
    mid = textures._noise(n, 1.0, 1.0, 1.1, rng)
    fine = textures._noise(n, 1.0, 1.0, 0.25, rng)
    vein = textures._noise(n, 0.25, 1.0, 1.9, rng)
    veins = np.exp(-(np.sin(np.pi * (vein * 5.5 + v * 1.0))) ** 2 * 60.0) * 0.35
    pits = (textures._noise(n, 1.0, 1.0, 0.1, rng) > 0.5).astype(float)
    base = np.array([0.40, 0.31, 0.20])
    warm = np.array([0.43, 0.30, 0.17])
    lin = base * (0.90 + 0.12 * cloud[..., None]) * (1 + 0.05 * tone[..., None])
    lin = lin * (1 + 0.08 * mid[..., None] + 0.06 * fine[..., None])
    lin = lin * (1 - veins[..., None]) + warm * veins[..., None] * 0.9
    lin = lin * (1 - 0.22 * pits[..., None])
    lin = lin * (1 - 0.42 * joint[..., None]) + np.array([0.22, 0.2, 0.17]) * 0.42 * joint[..., None]
    return textures._save(name, textures._to_srgb(lin))


def paving(n=1024, seed=17, force=False):
    """Courtyard floor, one tile = 3 m: warm-grey sandstone flags (bluestone/Yorkstone
    type) in random-length courses with fine joints. This generated map sets the mean
    colour (the palette) and is the fallback; polyhaven_textures.py (GENERATE) replaces it
    with the large_grey_tiles scan in one warm grey. Courtyard floor only (the terrace and
    the stone furniture keep the limestone map)."""
    name = "T_Courtyard_Paving_BaseColor"
    path = os.path.join(TEX, name + ".png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    u = (np.arange(n)[None, :] + 0.5) / n * 3.0 * np.ones((n, 1))
    v = (np.arange(n)[:, None] + 0.5) / n * 3.0 * np.ones((1, n))
    rows = [0.0, 0.75, 1.35, 2.2, 3.0]
    tone = np.zeros((n, n))
    joint = np.zeros((n, n))
    for r0, r1 in zip(rows[:-1], rows[1:]):
        band = (v >= r0) & (v < r1)
        cuts = np.cumsum(rng.uniform(0.55, 1.05, 8))
        cuts = cuts[cuts < 3.0 - 0.4]
        edges = np.concatenate([[0.0], cuts, [3.0]])
        off = rng.uniform(0, 3.0)
        uu = (u + off) % 3.0
        for e0, e1 in zip(edges[:-1], edges[1:]):
            m = band & (uu >= e0) & (uu < e1)
            tone[m] = rng.uniform(-1, 1)
            d = np.minimum(np.minimum(uu - e0, e1 - uu), np.minimum(v - r0, r1 - v))
            joint = np.maximum(joint, m * (1.0 - _smooth(0.003, 0.007, d)))
    cloud = textures._noise(n, 1.0, 1.0, 2.0, rng)
    fine = textures._noise(n, 1.0, 1.0, 0.4, rng)
    base = np.array([0.205, 0.192, 0.172])
    lin = base * (1 + 0.07 * tone[..., None] + 0.08 * cloud[..., None] + 0.05 * fine[..., None])
    lin = lin * (1 - 0.5 * joint[..., None])
    return textures._save(name, textures._to_srgb(lin))


def teak(force=False):
    return textures.wood("T_Courtyard_Teak_BaseColor", dark=(0.060, 0.032, 0.015),
                         light=(0.180, 0.105, 0.050), rings=22, seed=29, force=force)


def _stamp_leaf(rgb, alpha, p0, ang, L, W, col, vein):
    """Paint one lanceolate leaf (base p0, direction ang, length L, max width W)."""
    h, w = alpha.shape
    d = np.array([math.cos(ang), math.sin(ang)])
    c = np.array(p0) + d * L * 0.5
    r = int(L * 0.5 + W + 4)
    x0, x1 = max(int(c[0]) - r, 0), min(int(c[0]) + r, w)
    y0, y1 = max(int(c[1]) - r, 0), min(int(c[1]) + r, h)
    if x1 <= x0 or y1 <= y0:
        return
    ys, xs = np.mgrid[y0:y1, x0:x1]
    rx, ry = xs + 0.5 - p0[0], ys + 0.5 - p0[1]
    uu = (rx * d[0] + ry * d[1]) / L
    vv = -rx * d[1] + ry * d[0]
    uc = np.clip(uu, 0.0, 1.0)
    hw = 0.5 * W * np.sin(np.pi * uc ** 0.7) ** 0.85
    a = np.clip((hw - np.abs(vv)) + 0.5, 0, 1) * ((uu >= -0.01) & (uu <= 1.01))
    shade = 1.0 + 0.18 * (np.abs(vv) / (hw + 1e-3) - 0.5) * (-1)
    midrib = np.exp(-(vv / 1.6) ** 2) * (uc < 0.97) * vein
    pix = np.array(col)[None, None, :] * shade[..., None] * (1 - midrib[..., None]) \
        + np.array(col)[None, None, :] * 1.7 * midrib[..., None]
    a3 = a[..., None]
    sl = (slice(y0, y1), slice(x0, x1))
    rgb[sl] = rgb[sl] * (1 - a3) + pix * a3
    alpha[sl] = np.maximum(alpha[sl], a)


def _draw_poly(rgb, alpha, pts, radii, cols):
    h, w = alpha.shape
    for (x, y), rad, col in zip(pts, radii, cols):
        r = int(rad + 2)
        x0, x1 = max(int(x) - r, 0), min(int(x) + r + 1, w)
        y0, y1 = max(int(y) - r, 0), min(int(y) + r + 1, h)
        if x1 <= x0 or y1 <= y0:
            continue
        ys, xs = np.mgrid[y0:y1, x0:x1]
        dist = np.hypot(xs + 0.5 - x, ys + 0.5 - y)
        a = np.clip(rad - dist + 0.5, 0, 1)[..., None]
        sl = (slice(y0, y1), slice(x0, x1))
        rgb[sl] = rgb[sl] * (1 - a) + np.array(col)[None, None, :] * a
        alpha[sl] = np.maximum(alpha[sl], a[..., 0])


def _sprig(rng, size, seed_tilt):
    """One olive sprig on a size x size cell: arched twig, paired lanceolate leaves,
    some showing the silver underside."""
    rgb = np.zeros((size, size, 3))
    alpha = np.zeros((size, size))
    green = np.array([0.085, 0.125, 0.05])
    silver = np.array([0.30, 0.34, 0.25])
    twig_col = (0.075, 0.055, 0.035)

    def twig(p0, ang, length, depth, leafL):
        pts, t = [], 0.0
        x, y = p0
        a = ang
        steps = int(length / 1.6)
        for k in range(steps):
            pts.append((x, y))
            a += (seed_tilt * 0.004 + rng.normal(0, 0.012)) * 0.4
            x += math.cos(a) * 1.6
            y += math.sin(a) * 1.6
        _draw_poly(rgb, alpha, pts, [max(1.4, 3.0 - depth * 1.0) * (1 - 0.5 * i / len(pts)) for i in range(len(pts))],
                   [twig_col] * len(pts))
        side = 1
        for i in range(20, len(pts), 28):
            px, py = pts[i]
            ta = math.atan2(pts[min(i + 1, len(pts) - 1)][1] - pts[i - 1][1],
                            pts[min(i + 1, len(pts) - 1)][0] - pts[i - 1][0])
            for sgn in (1, -1):
                la = ta + sgn * rng.uniform(0.7, 1.05)
                s = leafL * rng.uniform(0.85, 1.15) * (1 - 0.25 * i / len(pts))
                col = (silver if rng.random() < 0.38 else green) * rng.uniform(0.85, 1.2)
                _stamp_leaf(rgb, alpha, (px, py), la, s, s * rng.uniform(0.19, 0.25), col, 0.5)
        # terminal leaf
        px, py = pts[-1]
        ta = math.atan2(pts[-1][1] - pts[-4][1], pts[-1][0] - pts[-4][0])
        _stamp_leaf(rgb, alpha, (px, py), ta, leafL * 1.05, leafL * 0.22, green * 1.1, 0.5)
        return pts

    m = size * 0.5
    main = twig((m, size - 14), -math.pi / 2 + rng.uniform(-0.1, 0.1), size * 0.80, 0, size * 0.20)
    for frac, sg in ((0.35, 1), (0.55, -1), (0.75, 1)):
        i = int(len(main) * frac)
        a = -math.pi / 2 - sg * 0.75
        twig(main[i], a, size * 0.38 * (1.1 - frac * 0.5), 1, size * 0.17)
    # fill transparent pixels with the mean colour (no dark fringes when mip-mapped)
    mean = np.array([0.07, 0.11, 0.04])
    rgb = np.where(alpha[..., None] > 0.004, rgb, mean)
    return rgb, alpha


def _tuft(rng, size, blades, length, droop, base, tip, spread=0.95, w=1.0):
    rgb = np.zeros((size, size, 3))
    alpha = np.zeros((size, size))
    for _ in range(blades):
        ang = -math.pi / 2 + rng.normal(0, spread * 0.45)
        ang = max(min(ang, -math.pi / 2 + 1.2), -math.pi / 2 - 1.2)
        L = length * rng.uniform(0.55, 1.0) * (1 - 0.25 * abs(ang + math.pi / 2))
        x, y = size / 2 + rng.normal(0, 14 * w), size - 10 * w
        pts, rad, cols = [], [], []
        steps = int(L / 1.8)
        a = ang
        bend = droop * (1 if ang > -math.pi / 2 else -1) * rng.uniform(0.6, 1.4) / steps * 1.6
        tcol = np.array(tip) * rng.uniform(0.8, 1.2)
        for k in range(steps):
            t = k / steps
            pts.append((x, y))
            rad.append(max(1.3 if w == 1.0 else 0.95, (5.2 + rng.uniform(0, 0.8)) * w * (1 - t) ** 0.7))
            cols.append(np.array(base) * (1 - t) + tcol * t)
            a += bend * (0.3 + t)
            x += math.cos(a) * 1.8
            y += math.sin(a) * 1.8
        _draw_poly(rgb, alpha, pts, rad, cols)
    mean = np.array(base)
    rgb = np.where(alpha[..., None] > 0.004, rgb, mean)
    return rgb, alpha


def _fern(rng, size):
    """One fern frond, base at the bottom: a gently curved rachis with paired, forward-
    swept pinnae, longest a third of the way up, tapering to the tip."""
    rgb = np.zeros((size, size, 3))
    alpha = np.zeros((size, size))
    green = np.array([0.045, 0.115, 0.028])
    pts, x, y, a = [], size * 0.5, size - 6.0, -math.pi / 2 - 0.08
    steps = int(size * 0.94 / 1.5)
    for k in range(steps):
        pts.append((x, y))
        a += 0.0028 + rng.normal(0, 0.002)
        x += math.cos(a) * 1.5
        y += math.sin(a) * 1.5
    _draw_poly(rgb, alpha, pts, [1.6 * (1 - 0.6 * i / len(pts)) for i in range(len(pts))],
               [(0.05, 0.08, 0.03)] * len(pts))
    n = len(pts)
    for i in range(int(n * 0.08), n - 3, 6):
        t = i / n
        px, py = pts[i]
        ta = math.atan2(pts[i + 1][1] - pts[i - 1][1], pts[i + 1][0] - pts[i - 1][0])
        L = size * 0.27 * math.sin(math.pi * min(1.0, 0.22 + t * 0.9)) ** 0.8 + 4
        for sgn in (1, -1):
            col = green * rng.uniform(0.8, 1.25) * (1.0 + 0.35 * t)
            _stamp_leaf(rgb, alpha, (px, py), ta + sgn * rng.uniform(1.15, 1.35), L * rng.uniform(0.9, 1.05),
                        max(3.2, L * 0.17), col, 0.35)
    _stamp_leaf(rgb, alpha, pts[-1], a, size * 0.06, size * 0.02, green * 1.3, 0.3)
    rgb = np.where(alpha[..., None] > 0.004, rgb, green)
    return rgb, alpha


def _palmate(rgb, alpha, p0, ang, R, col):
    """Japanese maple leaf: seven slender lobes fanned from the petiole end."""
    for k, (da, f) in enumerate(((0, 1.0), (0.55, 0.92), (-0.55, 0.92), (1.1, 0.74), (-1.1, 0.74),
                                 (1.65, 0.48), (-1.65, 0.48))):
        _stamp_leaf(rgb, alpha, p0, ang + da, R * f, R * f * 0.30, col * (1.0 - 0.06 * k), 0.4)


def _maple(rng, size):
    """Japanese maple sprig: a slim red twig with alternate palmate leaves in reds, from
    crimson to copper (an acer turning in autumn); leaves face up and out."""
    rgb = np.zeros((size, size, 3))
    alpha = np.zeros((size, size))
    pal = [np.array(c) for c in ((0.36, 0.030, 0.018), (0.46, 0.060, 0.020), (0.52, 0.13, 0.025),
                                 (0.28, 0.035, 0.025), (0.40, 0.045, 0.022), (0.50, 0.20, 0.04))]

    def twig(p0, ang, length, width, depth):
        pts, x, y, a = [], p0[0], p0[1], ang
        for k in range(int(length / 1.5)):
            pts.append((x, y))
            a += rng.normal(0, 0.03)
            x += math.cos(a) * 1.5
            y += math.sin(a) * 1.5
        _draw_poly(rgb, alpha, pts, [max(0.8, width * (1 - 0.6 * i / len(pts))) for i in range(len(pts))],
                   [(0.16, 0.05, 0.03)] * len(pts))
        return pts

    main = twig((size * 0.5, size - 6), -math.pi / 2 + rng.uniform(-0.1, 0.1), size * 0.80, 2.0, 0)
    tips = [main]
    for frac, sg in ((0.15, 1), (0.3, -1), (0.48, 1), (0.64, -1), (0.8, 1)):
        i = int(len(main) * frac)
        tips.append(twig(main[i], -math.pi / 2 + sg * rng.uniform(0.75, 1.05), size * rng.uniform(0.30, 0.40), 1.3, 1))
    for pts in tips:
        for i in range(len(pts) // 3, len(pts), max(6, len(pts) // 4)):
            px, py = pts[i]
            a = -math.pi / 2 + rng.uniform(-1.1, 1.1)
            pet = rng.uniform(5, 9)
            q = (px + math.cos(a) * pet, py + math.sin(a) * pet)
            _draw_poly(rgb, alpha, [(px, py), q], [0.8, 0.7], [(0.2, 0.05, 0.03)] * 2)
            _palmate(rgb, alpha, q, a, size * rng.uniform(0.11, 0.145), pal[rng.integers(len(pal))] *
                     rng.uniform(0.85, 1.15))
        q = pts[-1]
        _palmate(rgb, alpha, q, math.atan2(q[1] - pts[-3][1], q[0] - pts[-3][0]), size * 0.12, pal[1])
    rgb = np.where(alpha[..., None] > 0.004, rgb, np.array([0.30, 0.06, 0.03]))
    return rgb, alpha


def _jasmine(rng, size):
    """Star jasmine strand (climbs a mast, trails over a bed's edge): a wiry stem with
    opposite pairs of glossy dark oval leaves and clusters of small white star flowers."""
    rgb = np.zeros((size, size, 3))
    alpha = np.zeros((size, size))
    leaf = np.array([0.028, 0.068, 0.022])
    flower = np.array([0.78, 0.75, 0.64])

    def strand(p0, ang, length, flowers):
        pts, x, y, a = [], p0[0], p0[1], ang
        for k in range(int(length / 1.5)):
            pts.append((x, y))
            a += 0.012 * math.sin(k * 0.05) + rng.normal(0, 0.015)
            x += math.cos(a) * 1.5
            y += math.sin(a) * 1.5
        _draw_poly(rgb, alpha, pts, [1.1] * len(pts), [(0.07, 0.06, 0.03)] * len(pts))
        for i in range(8, len(pts) - 2, 11):
            px, py = pts[i]
            ta = math.atan2(pts[i + 1][1] - pts[i - 1][1], pts[i + 1][0] - pts[i - 1][0])
            s = size * rng.uniform(0.10, 0.13) * (1 - 0.3 * i / len(pts))
            for sgn in (1, -1):
                _stamp_leaf(rgb, alpha, (px, py), ta + sgn * rng.uniform(0.75, 1.1), s, s * 0.46,
                            leaf * rng.uniform(0.8, 1.3), 0.45)
            if flowers and rng.random() < 0.28:
                for _ in range(rng.integers(2, 4)):
                    fx, fy = px + rng.normal(0, 6), py + rng.normal(0, 6)
                    r0 = rng.uniform(0, 1.3)
                    for k in range(5):
                        _stamp_leaf(rgb, alpha, (fx, fy), r0 + k * 2 * math.pi / 5, size * 0.03, size * 0.017,
                                    flower * rng.uniform(0.9, 1.1), 0.0)
        return pts

    main = strand((size * 0.5, size - 6), -math.pi / 2 + rng.uniform(-0.1, 0.1), size * 0.9, True)
    for frac, sg in ((0.12, 1), (0.25, -1), (0.42, 1), (0.58, -1), (0.72, 1)):
        strand(main[int(len(main) * frac)], -math.pi / 2 + sg * rng.uniform(0.55, 0.85), size * rng.uniform(0.36, 0.5),
               rng.random() < 0.7)
    rgb = np.where(alpha[..., None] > 0.004, rgb, leaf)
    return rgb, alpha


def foliage(n=1024, seed=53, force=False):
    """RGBA atlas: [olive sprig A | olive sprig B] (512 cells) over [golden grass (512) |
    four 256 cells: blue-green sedge, fern frond / maple sprig, star jasmine]."""
    name = "T_Courtyard_Foliage_BaseColor"
    path = os.path.join(TEX, name + ".png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(seed)
    half = n // 2
    q = n // 4
    rgb = np.zeros((n, n, 3))
    alpha = np.zeros((n, n))
    cells = [
        (0, 0, _sprig(rng, half, 1.0)),
        (0, half, _sprig(rng, half, -1.0)),
        (half, 0, _tuft(rng, half, 42, 420, 0.9, (0.05, 0.10, 0.03), (0.40, 0.36, 0.11), 0.7)),
        (half, half, _tuft(rng, q, 46, 225, 1.3, (0.03, 0.07, 0.045), (0.12, 0.22, 0.12), 0.8, w=0.6)),
        (half, half + q, _fern(rng, q)),
        (half + q, half, _maple(rng, q)),
        (half + q, half + q, _jasmine(rng, q)),
    ]
    for y0, x0, (c_rgb, c_a) in cells:
        # keep a margin so mip-mapping never bleeds one cell into the next
        c_a = c_a.copy()
        m = 4 if c_a.shape[0] > q else 3
        c_a[:m, :] = 0
        c_a[-m:, :] = 0
        c_a[:, :m] = 0
        c_a[:, -m:] = 0
        s = c_a.shape[0]
        rgb[y0:y0 + s, x0:x0 + s] = c_rgb
        alpha[y0:y0 + s, x0:x0 + s] = c_a
    srgb = textures._to_srgb(rgb)
    img = bpy.data.images.new(name, n, n, alpha=True)
    rgba = np.concatenate([srgb, alpha[..., None]], axis=2)
    img.pixels.foreach_set(rgba[::-1].astype(np.float32).ravel())
    img.alpha_mode = "STRAIGHT"
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    return path


# ----------------------------------------------------------------------------- materials

def limestone_mat():
    m = common.pbr_material("M_Courtyard_Limestone", (0.42, 0.36, 0.26), roughness=0.82)
    common.set_base_color_map(m, textures.load(limestone()))
    return m


def paving_mat():
    """Courtyard floor (shell finish): warm-grey sandstone flags, tile 3 m."""
    m = common.pbr_material("M_Courtyard_Paving", (0.205, 0.192, 0.172), roughness=0.86)
    common.set_base_color_map(m, textures.load(paving()))
    return m


def terracotta_mat():
    """Hand-thrown terracotta pots: warm, matt, slightly sun-bleached."""
    return common.pbr_material("M_Courtyard_Terracotta", (0.42, 0.165, 0.085), roughness=0.9)


def bulb_mat():
    """Festoon / candle glow: warm 2200 K filament bulbs (one material for every bulb)."""
    return materials.emissive("M_Courtyard_Bulb", (1.0, 0.70, 0.40), 9.0)


def black_mat():
    return materials.black_metal()


def teak_mat():
    m = common.pbr_material("M_Courtyard_Teak", (0.15, 0.08, 0.035), roughness=0.62, coat=0.0)
    common.set_base_color_map(m, textures.load(teak()))
    return m


def foliage_mat():
    """Leaf/grass cards: alpha-tested (exports as glTF alphaMode MASK) and double-sided."""
    m = common.pbr_material("M_Courtyard_Foliage", (0.1, 0.15, 0.05), roughness=0.7)
    img = textures.load(foliage())
    img.alpha_mode = "STRAIGHT"
    nodes, links = m.node_tree.nodes, m.node_tree.links
    bsdf = next(nd for nd in nodes if nd.type == "BSDF_PRINCIPLED")
    if not any(nd.type == "TEX_IMAGE" for nd in nodes):
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.location = (bsdf.location.x - 700, bsdf.location.y)
        rnd = nodes.new("ShaderNodeMath")
        rnd.operation = "ROUND"
        rnd.location = (bsdf.location.x - 350, bsdf.location.y - 250)
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        links.new(tex.outputs["Alpha"], rnd.inputs[0])
        links.new(rnd.outputs[0], bsdf.inputs["Alpha"])
    m.use_backface_culling = False
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "DITHERED"
    return m


def bark_mat():
    """Weathered grey-brown bark (the olive's; the maple and potted standards share it)."""
    return common.pbr_material("M_Courtyard_Bark", (0.165, 0.142, 0.112), roughness=0.92)


def soil_mat():
    return common.pbr_material("M_Courtyard_Soil", (0.045, 0.030, 0.022), roughness=0.98)


def boxwood_mat():
    return common.pbr_material("M_Courtyard_Boxwood", (0.038, 0.072, 0.028), roughness=0.85)


def water_mat():
    return common.pbr_material("M_Courtyard_Water", (0.010, 0.030, 0.036), roughness=0.02, metallic=0.35)


def ceramic_mat():
    return common.pbr_material("M_Courtyard_Ceramic", (0.62, 0.58, 0.50), roughness=0.35)


def sand_fabric():
    return materials.fabric("M_Fabric_Outdoor_Sand", (0.46, 0.405, 0.325), roughness=0.92)


def sage_fabric():
    return materials.fabric("M_Fabric_Outdoor_Sage", (0.16, 0.20, 0.12), roughness=0.92)


def clay_fabric():
    return materials.fabric("M_Fabric_Outdoor_Clay", (0.36, 0.15, 0.075), roughness=0.92)


# ----------------------------------------------------------------------------- geometry

def rbox(name, size, loc, mat, col, parent, bevel=0.004, uv_tile=0.5, seg=2, rot=None):
    """Bevelled box centred at loc with world-scale box UVs."""
    ob = common.mesh_object(name, common.box_bmesh(size), col, mat, parent, smooth=False)
    ob.location = loc
    if rot:
        ob.rotation_euler = rot
    if uv_tile:
        common.box_uv(ob, tile=uv_tile)
    if bevel:
        common.add_bevel(ob, bevel, segments=seg)
    return ob


def lathe(profile, segs, name, col, mat, parent, sharp=35.0, closed=False):
    """Revolve [(r, z), ...] about Z. Corners sharper than `sharp` degrees stay crisp."""
    bm = bmesh.new()
    rows = []
    for r, z in profile:
        if abs(r) < 1e-9:
            rows.append([bm.verts.new((0, 0, z))] * segs)
        else:
            rows.append([bm.verts.new((r * math.cos(2 * math.pi * s / segs),
                                       r * math.sin(2 * math.pi * s / segs), z)) for s in range(segs)])
    n = len(profile)
    for i in range(n if closed else n - 1):
        a, b = rows[i], rows[(i + 1) % n]
        for s in range(segs):
            t = (s + 1) % segs
            quad = []
            for vtx in (a[s], a[t], b[t], b[s]):
                if vtx not in quad:
                    quad.append(vtx)
            if len(quad) >= 3:
                bm.faces.new(quad)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for i, (r, z) in enumerate(profile):
        if abs(r) < 1e-9 or (not closed and i in (0, n - 1)):
            continue
        pr, nx = profile[(i - 1) % n], profile[(i + 1) % n]
        d1, d2 = (r - pr[0], z - pr[1]), (nx[0] - r, nx[1] - z)
        ang = math.degrees(abs(math.atan2(d1[0] * d2[1] - d1[1] * d2[0], d1[0] * d2[0] + d1[1] * d2[1])))
        if ang > sharp:
            for s in range(segs):
                e = bm.edges.get((rows[i][s], rows[i][(s + 1) % segs]))
                if e is not None and e.is_valid:
                    e.smooth = False
    return common.mesh_object(name, bm, col, mat, parent)


def round_uv(ob, tile=3.0):
    """World-scale UVs for a lathed object: u once round in whole tile multiples
    (seamless), v up the height; flat tops/bottoms use plan projection."""
    me = ob.data
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    rs = [math.hypot(v.co.x, v.co.y) for v in me.vertices]
    reps = max(1, round(2 * math.pi * max(rs) / tile))
    for poly in me.polygons:
        if abs(poly.normal.z) > 0.9:
            for li in poly.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                uv.data[li].uv = (co.x / tile + 0.37, co.y / tile + 0.11)
            continue
        angs = [math.atan2(me.vertices[me.loops[li].vertex_index].co.y,
                           me.vertices[me.loops[li].vertex_index].co.x) for li in poly.loop_indices]
        ref = angs[0]
        for k, li in enumerate(poly.loop_indices):
            a = angs[k]
            while a - ref > math.pi:
                a -= 2 * math.pi
            while a - ref < -math.pi:
                a += 2 * math.pi
            uv.data[li].uv = (a / (2 * math.pi) * reps, me.vertices[me.loops[li].vertex_index].co.z / tile)


# atlas cells: (u0, v0, size) in UV units; every cell is square, its plant's base at the bottom
CELLS = {"sprigA": (0.0, 0.5, 0.5), "sprigB": (0.5, 0.5, 0.5), "grassA": (0.0, 0.0, 0.5),
         "grassB": (0.5, 0.25, 0.25), "fern": (0.75, 0.25, 0.25),
         "maple": (0.5, 0.0, 0.25), "jasmine": (0.75, 0.0, 0.25)}


def add_card(bm, uvl, centre, right, up, cell, flip=False):
    """Quad from centre with half-extents `right` and `up` (vectors); atlas cell UVs."""
    c = Vector(centre)
    corners = [c - right - up, c + right - up, c + right + up, c - right + up]
    verts = [bm.verts.new(p) for p in corners]
    f = bm.faces.new(verts)
    u0, v0, s = CELLS[cell]
    uvs = [(u0, v0), (u0 + s, v0), (u0 + s, v0 + s), (u0, v0 + s)]
    if flip:
        uvs = [uvs[1], uvs[0], uvs[3], uvs[2]]
    for loop, uv in zip(f.loops, uvs):
        loop[uvl].uv = uv
    return f


def add_strip(bm, uvl, pts, half_w, cell, flip=False, widths=None):
    """A bent card: the cell's centre line follows pts (base first, 2+ points), half_w is
    the half-width vector (or one per point). Arching fern fronds, strands of jasmine
    climbing a mast or trailing over a bed's edge. 2 triangles per segment."""
    pts = [Vector(p) for p in pts]
    hw = half_w if isinstance(half_w, (list, tuple)) and len(half_w) == len(pts) and \
        not isinstance(half_w[0], (int, float)) else [Vector(half_w)] * len(pts)
    if widths:
        hw = [h * w for h, w in zip(hw, widths)]
    seg = [0.0]
    for a, b in zip(pts[:-1], pts[1:]):
        seg.append(seg[-1] + (b - a).length)
    u0, v0, s = CELLS[cell]
    ul, ur = (u0 + s, u0) if flip else (u0, u0 + s)
    rows = [(bm.verts.new(p - h), bm.verts.new(p + h)) for p, h in zip(pts, hw)]
    for i in range(len(pts) - 1):
        a, b = rows[i], rows[i + 1]
        f = bm.faces.new((a[0], a[1], b[1], b[0]))
        va, vb = v0 + s * seg[i] / seg[-1], v0 + s * seg[i + 1] / seg[-1]
        for loop, uv in zip(f.loops, ((ul, va), (ur, va), (ur, vb), (ul, vb))):
            loop[uvl].uv = uv
    return rows


def set_vertex_normals(me, normals_by_vertex):
    """Custom per-vertex normals (smooth, volumetric shading for foliage clumps)."""
    try:
        me.normals_split_custom_set_from_vertices([tuple(n) for n in normals_by_vertex])
    except Exception as e:  # noqa: BLE001
        print("custom normals unavailable:", e)


# ----------------------------------------------------------------------------- pieces

def piece(bm, uvl, size, matrix=None, bevel=0.003, tile=0.5, rng=None, skip=()):
    """Add one bevelled box (size, centred at the origin, then `matrix`) to bm, with its
    own box UVs (u along the piece's longest axis: wood grain follows each board, not the
    whole mesh) and a random texture offset. skip: faces to drop ("-z", "+y", ...), e.g.
    ones against the floor or hidden inside a joint. Lets one mesh (one collider box)
    hold several boards."""
    from mathutils import Matrix
    sx, sy, sz = size
    tmp = bmesh.new()
    bmesh.ops.create_cube(tmp, size=1.0)
    bmesh.ops.scale(tmp, vec=Vector(size), verts=tmp.verts)
    if bevel:
        bmesh.ops.bevel(tmp, geom=list(tmp.edges), offset=bevel, segments=1, affect="EDGES", profile=0.5,
                        clamp_overlap=True)
    order = sorted(range(3), key=lambda a: -size[a])
    du, dv = (rng.uniform(0, 1), rng.uniform(0, 1)) if rng else (0.0, 0.0)
    luv = tmp.loops.layers.uv.new("UVMap")
    drop = []
    for f in tmp.faces:
        nrm = f.normal
        na = max(range(3), key=lambda a: abs(nrm[a]))
        key = ("+" if nrm[na] > 0 else "-") + "xyz"[na]
        if key in skip and abs(nrm[na]) > 0.99:
            drop.append(f)
            continue
        a, b = [k for k in order if k != na][:2]
        for lp in f.loops:
            co = lp.vert.co
            lp[luv].uv = (co[a] / tile + du, co[b] / tile + dv)
    if drop:
        bmesh.ops.delete(tmp, geom=drop, context="FACES")
    m = matrix or Matrix.Identity(4)
    vmap = {}
    for v in tmp.verts:
        vmap[v] = bm.verts.new(m @ v.co)
    for f in tmp.faces:
        nf = bm.faces.new([vmap[v] for v in f.verts])
        for lp, lt in zip(nf.loops, f.loops):
            lp[uvl].uv = lt[luv].uv
    tmp.free()


def lathe_bm(bm, profile, segs, matrix=None, uvl=None, tile=0.5):
    """Revolve [(r, z), ...] about Z into an existing bmesh (cheap round parts: plates,
    candles, pots, bulbs), UVs u round / v up, smooth shading set by the caller."""
    from mathutils import Matrix
    m = matrix or Matrix.Identity(4)
    rows = []
    for r, z in profile:
        if abs(r) < 1e-9:
            rows.append([bm.verts.new(m @ Vector((0, 0, z)))] * segs)
        else:
            rows.append([bm.verts.new(m @ Vector((r * math.cos(2 * math.pi * s / segs),
                                                  r * math.sin(2 * math.pi * s / segs), z))) for s in range(segs)])
    faces = []
    for i in range(len(profile) - 1):
        a, b = rows[i], rows[i + 1]
        for s in range(segs):
            t = (s + 1) % segs
            quad = []
            for vtx in (a[s], a[t], b[t], b[s]):
                if vtx not in quad:
                    quad.append(vtx)
            if len(quad) >= 3:
                f = bm.faces.new(quad)
                faces.append(f)
                if uvl is not None:
                    for lp in f.loops:
                        co = lp.vert.co
                        lp[uvl].uv = (math.atan2(co.y - m.translation.y, co.x - m.translation.x) / (2 * math.pi) * 2,
                                      co.z / tile)
    return faces
