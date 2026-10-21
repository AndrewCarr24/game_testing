"""Fiddle-leaf fig (Ficus lyrata) standard in a fluted limestone planter. Origin: floor centre.
About 0.60 x 0.58 x 2.0 m.

- Planter: a honed-limestone cylinder (T_LibraryPlant_Stone), fluted between a plain lip band
  and an eased foot, the inside visible down to a mounded bark-mulch top dressing.
- Trunk: a gently S-curved grey-brown stem with a root flare, encircled by the ring scars that
  fig stipules leave, forking near the top into three short shoots; each shoot ends in the
  pale green stipule sheath that wraps the next leaf.
- Leaves: real geometry (no alpha cards, so they batch and never alias): violin-shaped
  (pandurate) blades with a cordate base, a pinched waist and a broad rounded apex, cupped
  across, V'd along the midrib, wavy at the margin and drooping with age; on short petioles,
  spiralled up each shoot (137.5 deg), small, bright and upright at the tips, big, dark and
  hanging lower down. Two leaf variants (mature / young) and the bark and mulch share one
  1024 atlas (T_LibraryPlant_Atlas + _Normal) with painted venation: the pale midrib,
  ~8 pairs of looping laterals, secondary and tertiary veins, quilting between them.
Materials: M_LibraryPlant_Planter, M_LibraryPlant_Leaf (glossy, double-sided) and
M_LibraryPlant_Bark (trunk, shoots, mulch). Leaves and shoots are NoCollide; the planter and
trunk keep their colliders.

leaf_texture() / T_Library_Leaf / M_Library_Leaf are kept unchanged: the decor kits' small
plants use them."""
import importlib
import math
import os
import random
import sys

import bmesh
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import library_kit as kit  # noqa: E402
from library_kit import Mesh, common, materials, textures  # noqa: E402

importlib.reload(kit)

NAME = "LibraryPlant"

P = dict(name=NAME, seed=3, leaves=38, height=1.95, pot_r=0.23, pot_h=0.46,
         flutes=24, crown_r=0.31)


def leaf_texture(n=256, force=False):
    """The old small leaf map (T_Library_Leaf): kept for the decor kits' small plants."""
    path = os.path.join(textures.TEX_DIR, "T_Library_Leaf.png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(12)
    u = np.linspace(-1, 1, n)[None, :] * np.ones((n, 1))        # across the leaf
    v = np.linspace(0, 1, n)[:, None] * np.ones((1, n))         # along it (0 = base at the bottom row)
    base = np.array([0.018, 0.085, 0.022])
    light = np.array([0.06, 0.20, 0.05])
    rib = np.exp(-(u / 0.035) ** 2)
    veins = np.exp(-((((np.abs(u) * 9 - v * 6) % 1.0) - 0.5) / 0.07) ** 2) * (np.abs(u) < 0.95)
    mott = textures._noise(n, 1.0, 1.0, 1.4, rng) * 0.5 + 0.5
    t = np.clip(0.35 + 0.35 * mott + 0.25 * rib + 0.12 * veins - 0.25 * np.abs(u) ** 3, 0, 1)
    img = base + (light - base) * t[..., None]
    img[(rib > 0.4)] = img[(rib > 0.4)] * 0.6 + np.array([0.18, 0.28, 0.08]) * 0.4
    img *= (1 - 0.35 * v ** 4)[..., None]
    return textures._save("T_Library_Leaf", textures._to_srgb(np.clip(img, 0, 1)))


# ------------------------------------------------------------------ leaf shape
# One outline for every leaf (geometry and texture agree exactly); leaves differ by size,
# proportions and bending. Leaf space: x across (-1..1 = half the max width), b along
# (0 = petiole junction, 1 = apex). Rows of the leaf grid: 5 vertices each (a = -1..1).
COLS = (-1.0, -0.5, 0.0, 0.5, 1.0)
ROW_B = (0.11, 0.25, 0.40, 0.56, 0.71, 0.84, 0.94)
ROW_H = (0.48, 0.575, 0.575, 0.735, 0.945, 0.99, 0.82)
BASE_ROW = ((-0.30, 0.018), (-0.16, -0.028), (0.0, 0.012), (0.16, -0.028), (0.30, 0.018))   # shallow cordate lobes
TIP_ROW = ((-0.47, 0.984), (-0.24, 1.0), (0.0, 0.993), (0.24, 1.0), (0.47, 0.984))     # broad, faintly notched


def leaf_rows():
    """[(x, b) x 5] per row, base to apex."""
    rows = [BASE_ROW]
    for b, h in zip(ROW_B, ROW_H):
        rows.append(tuple((a * h, b) for a in COLS))
    rows.append(TIP_ROW)
    return rows


def outline():
    """Closed outline polygon in (x, b), right side up from the base, then left side down."""
    rows = leaf_rows()
    right = [rows[0][2], rows[0][3]] + [r[4] for r in rows] + [rows[-1][3], rows[-1][2]]
    left = [(-x, b) for x, b in reversed(right[1:-1])]
    return right + left


# atlas regions (u0, u1, v0, v1)
ATLAS_N = 1024
LEAF_REG = ((0.0, 400 / 1024, 0.0, 1.0), (400 / 1024, 800 / 1024, 0.0, 1.0))   # mature, young
BARK_REG = (816 / 1024, 1016 / 1024, 256 / 1024, 1.0)
SOIL_REG = (816 / 1024, 1016 / 1024, 24 / 1024, 224 / 1024)
LX, LB0, LB1 = 1.04, -0.07, 1.02          # leaf space covered by a leaf region
BARK_LEN = 1.5                            # metres of stem the bark strip covers (v)


def leaf_uv(reg, x, b, flip=False):
    u0, u1, v0, v1 = LEAF_REG[reg]
    xx = -x if flip else x
    return (u0 + (xx / LX * 0.5 + 0.5) * (u1 - u0), v0 + (b - LB0) / (LB1 - LB0) * (v1 - v0))


# ------------------------------------------------------------------ textures

def _pnoise(h, w, su, sv, beta, rng):
    """Periodic fractal noise (h x w) in [-1, 1]; larger su / sv -> longer features along u / v."""
    white = rng.standard_normal((h, w))
    ky = np.fft.fftfreq(h)[:, None] * h
    kx = np.fft.fftfreq(w)[None, :] * w
    k = np.sqrt((kx * su) ** 2 + (ky * sv) ** 2)
    k[0, 0] = 1.0
    spec = np.fft.fft2(white) / k ** beta
    spec[0, 0] = 0
    out = np.real(np.fft.ifft2(spec))
    return out / (np.abs(out).max() + 1e-9)


def _seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = np.clip(((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy + 1e-12), 0, 1)
    return np.hypot(px - ax - t * dx, py - ay - t * dy)


def _inside(px, py, poly):
    ins = np.zeros(px.shape, bool)
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        cond = (y0 > py) != (y1 > py)
        xi = x0 + (py - y0) * (x1 - x0) / (y1 - y0 + 1e-12)
        ins ^= cond & (px < xi)
    return ins


def _leaf_maps(h, w, young, rng):
    """Colour (h, w, 3, linear) and height (h, w) of one leaf region."""
    cols = (np.arange(w) + 0.5) / w
    rows = 1 - (np.arange(h) + 0.5) / h
    x = (cols[None, :] * 2 - 1) * LX * np.ones((h, 1))
    b = (LB0 + rows[:, None] * (LB1 - LB0)) * np.ones((1, w))
    ASP = 0.37                                    # half width / length of a typical leaf
    X, Y = x * ASP, b                             # physical (units of leaf length)
    poly = outline()
    inside = _inside(x, b, poly)
    d = np.full(x.shape, 9.0)
    for i in range(len(poly)):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % len(poly)]
        d = np.minimum(d, _seg_dist(X, Y, x0 * ASP, y0, x1 * ASP, y1))
    edge = np.where(inside, d, -d)                # signed distance to the margin (+ inside)
    Xa = np.abs(X)
    side = np.sign(x)

    # midrib: wide and pale at the base, fine at the apex
    mw = 0.0105 * (1 - np.clip(b, 0, 1)) ** 0.8 + 0.0022
    rib = np.exp(-(Xa / mw) ** 2 * 1.4) * (b < 0.985)
    rib_ch = np.exp(-(Xa / (mw * 2.6)) ** 2)     # the shallow channel the rib lies in

    # laterals: arcs leaving the rib at ~50 deg, curving apex-wards and looping near the margin
    g = 0.62 * Xa + 2.0 * Xa ** 2
    gp = 0.62 + 4.0 * Xa
    sp = 0.128
    off = np.where(side > 0, 0.03, 0.03 + sp * 0.45)
    phi = Y - g - off
    k = np.round(phi / sp)
    jit = np.sin(k * 2.7 + side * 1.3) * 0.014 + 0.006 * np.sin(Xa * 40 + k)
    dl = np.abs(phi - k * sp - jit) / np.sqrt(1 + gp ** 2)
    valid = (k >= 0) & (k <= 7) & (Y - g > 0.0)
    reach = np.clip(edge / 0.035, 0, 1)
    lw = 0.0042 * (1 - np.clip(Xa / 0.37, 0, 1)) ** 0.8 + 0.0013
    lat = np.exp(-(dl / lw) ** 2) * valid * reach * (b > 0.02) * (b < 0.97)
    # secondaries between them (finer, stop short of the margin)
    phi2 = phi - sp * 0.5
    k2 = np.round(phi2 / sp)
    d2 = np.abs(phi2 - k2 * sp) / np.sqrt(1 + gp ** 2)
    sec = np.exp(-(d2 / 0.0011) ** 2) * (k2 >= 0) * (k2 <= 8) * np.clip((Xa - 0.03) / 0.04, 0, 1) \
        * np.clip(edge / 0.06, 0, 1) * 0.22
    # intramarginal loop vein and the margin itself
    loop = np.exp(-((edge - 0.016) / 0.0022) ** 2) * (b > 0.05) * 0.6
    margin = np.exp(-(np.maximum(edge, 0) / 0.0035) ** 2)
    # tertiary network: ridges of band-passed noise
    n1 = _pnoise(h, w, 1.0, 1.0, 1.45, rng)
    n1 = n1 / (np.std(n1) + 1e-9)
    ter = np.exp(-(n1 / 0.18) ** 2) * 0.35 * np.clip(edge / 0.02, 0, 1)
    veins = np.clip(np.maximum.reduce([lat, sec, loop, ter * 0.6]), 0, 1)

    # quilting: the blade bulges between laterals
    fr = (phi / sp) - np.floor(phi / sp)
    quilt = np.sin(np.pi * fr) ** 1.5 * np.clip(Xa / 0.04, 0, 1) * np.clip(edge / 0.03, 0, 1)
    height = 0.55 * quilt - 0.9 * lat - 0.45 * sec - 0.5 * loop - 0.08 * ter + 0.5 * rib - 0.5 * rib_ch \
        - 0.3 * (1 - np.clip(edge / 0.012, 0, 1))
    height = np.where(inside, height, height * 0.2)

    mott = _pnoise(h, w, 1.0, 1.0, 1.6, rng)
    fine = _pnoise(h, w, 1.0, 1.0, 0.7, rng)
    if young:
        base = np.array([0.060, 0.155, 0.026])
        vein_c = np.array([0.14, 0.24, 0.05])
        rib_c = np.array([0.24, 0.32, 0.09])
        edge_c = np.array([0.11, 0.20, 0.04])
        vein_amt = 0.45
    else:
        base = np.array([0.013, 0.058, 0.010])
        vein_c = np.array([0.075, 0.13, 0.036])
        rib_c = np.array([0.20, 0.25, 0.085])
        edge_c = np.array([0.055, 0.10, 0.028])
        vein_amt = 0.7
    col = base * (1 + 0.16 * mott[..., None] + 0.05 * fine[..., None] + 0.12 * quilt[..., None])
    # warmer, lighter green towards the base and along the rib
    warm = np.clip(1 - b / 0.35, 0, 1)[..., None] * np.exp(-(Xa / 0.08) ** 2)[..., None]
    col = col * (1 - 0.35 * warm) + (base * 1.6 + np.array([0.01, 0.01, 0.0])) * 0.35 * warm
    col = col + (vein_c - col) * (veins * vein_amt)[..., None]
    col = col + (edge_c - col) * (margin * 0.45)[..., None]
    col = col + (rib_c - col) * np.clip(rib * 1.2, 0, 1)[..., None]
    col = np.where(inside[..., None], col, edge_c)
    return np.clip(col, 0, 1), height


def _bark_maps(h, w, rng):
    """Bark strip (periodic across u = round the stem): v runs along the stem."""
    v = 1 - (np.arange(h) + 0.5) / h                      # 0 = soil, 1 = BARK_LEN up
    z = (v * BARK_LEN)[:, None] * np.ones((1, w))
    streak = _pnoise(h, w, 0.25, 4.0, 1.3, rng)          # long along v
    blot = _pnoise(h, w, 1.0, 1.0, 1.7, rng)
    fine = _pnoise(h, w, 1.0, 1.0, 0.6, rng)
    lower = np.array([0.095, 0.080, 0.062])               # grey-brown, older
    upper = np.array([0.085, 0.070, 0.040])               # greener-brown, young wood
    t = np.clip((z - 0.55) / 0.8, 0, 1)[..., None]
    col = lower * (1 - t) + upper * t
    col = col * (1 + 0.10 * streak[..., None] + 0.12 * blot[..., None] + 0.06 * fine[..., None])
    height = 0.4 * streak + 0.15 * fine
    # stipule ring scars, closer together up the stem
    zr, ring_v = 0.06, []
    while zr < BARK_LEN:
        ring_v.append(zr)
        zr += 0.11 - 0.07 * min(zr / BARK_LEN, 1.0) + rng.uniform(-0.02, 0.02)
    u = (np.arange(w) + 0.5) / w
    for zr in ring_v:
        wob = 0.004 * np.sin(2 * np.pi * u + rng.uniform(0, 6.3)) + 0.002 * np.sin(4 * np.pi * u + rng.uniform(0, 6.3))
        dz = z - (zr + wob[None, :])
        ring = np.exp(-(dz / 0.0016) ** 2)
        lip = np.exp(-((dz - 0.0030) / 0.0022) ** 2)
        fade = 0.35 + 0.65 * min(zr / BARK_LEN, 1.0)        # old scars weather away down the trunk
        part = np.clip(0.6 + 0.8 * np.sin(2 * np.pi * u * rng.integers(1, 3) + rng.uniform(0, 6.3)), 0, 1)[None, :]
        col = col * (1 - 0.3 * fade * part * ring)[..., None] + np.array([0.16, 0.145, 0.115]) * (0.25 * fade * part * lip)[..., None]
        height += (0.6 * lip - 0.5 * ring) * fade * part
    # lenticels: small pale horizontal dashes
    for _ in range(520):
        cu, cz = rng.uniform(0, 1), rng.uniform(0, BARK_LEN)
        du = (u[None, :] - cu + 0.5) % 1.0 - 0.5
        m = np.exp(-((du / rng.uniform(0.008, 0.02)) ** 2 + ((z - cz) / 0.0011) ** 2))
        col = col + (np.array([0.17, 0.155, 0.125]) - col) * (m * 0.5)[..., None]
        height += 0.5 * m
    return np.clip(col, 0, 1), height


def _soil_maps(h, w, rng):
    """Bark-mulch top dressing over dark potting soil (planar, ~0.45 m across)."""
    col = np.array([0.028, 0.019, 0.012]) * (1 + 0.3 * _pnoise(h, w, 1, 1, 0.8, rng)[..., None])
    height = 0.2 * _pnoise(h, w, 1, 1, 1.0, rng)
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    for _ in range(620):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        a = rng.uniform(0, math.pi)
        ln, wd = rng.uniform(3, 9), rng.uniform(1.6, 4.0)
        dx, dy = xx - cx, yy - cy
        p = (dx * math.cos(a) + dy * math.sin(a)) / ln
        q = (-dx * math.sin(a) + dy * math.cos(a)) / wd
        th = np.arctan2(q, p)
        rr = np.hypot(p, q)
        lim = 1 + 0.28 * np.sin(3 * th + rng.uniform(0, 6.3)) + 0.16 * np.sin(5 * th + rng.uniform(0, 6.3))
        m = np.clip((lim - rr) * 3.0, 0, 1)
        if not m.any():
            continue
        kind = rng.random()
        if kind < 0.7:
            c = np.array([0.075, 0.042, 0.022]) * rng.uniform(0.55, 1.5)          # bark chip
        elif kind < 0.9:
            c = np.array([0.085, 0.075, 0.062]) * rng.uniform(0.7, 1.3)          # weathered, grey
        else:
            c = np.array([0.14, 0.085, 0.045]) * rng.uniform(0.8, 1.2)           # fresh, ginger
        grain = 1 + 0.18 * np.sin(q * 5 + rng.uniform(0, 6))
        hz = rng.uniform(0.5, 1.0)
        top = m * (hz > height - 0.1)
        col = col * (1 - top[..., None]) + (c * grain[..., None]) * top[..., None]
        height = np.maximum(height, m * hz)
    # crevices between chips
    col *= (0.55 + 0.45 * np.clip(height, 0, 1))[..., None]
    # a few pale perlite grains
    for _ in range(40):
        cx, cy, rr = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0.8, 1.6)
        m = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / rr ** 2))
        col = col + (np.array([0.45, 0.44, 0.40]) - col) * (m * 0.8)[..., None]
        height += 0.6 * m
    return np.clip(col, 0, 1), height


def _height_to_normal(hgt, px_u, px_v, strength):
    """Height (h, w) -> tangent-space normal (glTF / OpenGL). px_u, px_v: physical size of a pixel."""
    dx = (np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)) / (2 * px_u) * strength
    dy = (np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0)) / (2 * px_v) * strength   # rows run down = -v
    nrm = np.stack([-dx, dy, np.ones_like(hgt)], axis=-1)
    return nrm / np.linalg.norm(nrm, axis=-1, keepdims=True)


def atlas(force=False):
    """T_LibraryPlant_Atlas (+ _Normal): two leaves, the bark strip and the mulch."""
    cpath = os.path.join(textures.TEX_DIR, "T_LibraryPlant_Atlas.png")
    npath = os.path.join(textures.TEX_DIR, "T_LibraryPlant_Atlas_Normal.png")
    if os.path.exists(cpath) and os.path.exists(npath) and not force:
        return cpath, npath
    N = ATLAS_N
    rng = np.random.default_rng(41)
    col = np.zeros((N, N, 3))
    nrm = np.zeros((N, N, 3))
    nrm[...] = (0.0, 0.0, 1.0)
    col[...] = (0.05, 0.08, 0.03)

    def px(reg):
        u0, u1, v0, v1 = reg
        return (int(round((1 - v1) * N)), int(round((1 - v0) * N)), int(round(u0 * N)), int(round(u1 * N)))

    for i, reg in enumerate(LEAF_REG):
        r0, r1, c0, c1 = px(reg)
        c, hgt = _leaf_maps(r1 - r0, c1 - c0, young=(i == 1), rng=rng)
        col[r0:r1, c0:c1] = c
        L = 0.28                                  # a typical leaf, for the normal map's scale
        pu = 2 * LX * 0.33 * L / (c1 - c0)
        pv = (LB1 - LB0) * L / (r1 - r0)
        nrm[r0:r1, c0:c1] = _height_to_normal(hgt * 0.0011, pu, pv, 1.0)
    r0, r1, c0, c1 = px(BARK_REG)
    c, hgt = _bark_maps(r1 - r0, c1 - c0, rng)
    col[r0:r1, c0:c1] = c
    circ = 2 * math.pi * 0.016
    nrm[r0:r1, c0:c1] = _height_to_normal(hgt * 0.0004, circ / (c1 - c0), BARK_LEN / (r1 - r0), 1.0)
    # gutter above the soil: bark colour, so mip-maps don't bleed green into the stem
    col[r1:px(SOIL_REG)[0], c0:c1] = col[r1 - 1:r1, c0:c1]
    r0, r1, c0, c1 = px(SOIL_REG)
    c, hgt = _soil_maps(r1 - r0, c1 - c0, rng)
    col[r0:r1, c0:c1] = c
    nrm[r0:r1, c0:c1] = _height_to_normal(hgt * 0.004, 0.45 / (c1 - c0), 0.45 / (r1 - r0), 1.0)
    # right-hand gutter: repeat the strip's edges
    col[:, 1016:] = col[:, 1015:1016]
    col[:, 800:816] = col[:, 816:817]
    textures._save("T_LibraryPlant_Atlas", textures._to_srgb(col))
    textures._save("T_LibraryPlant_Atlas_Normal", nrm * 0.5 + 0.5, non_color=True)
    return cpath, npath


def stone_maps(n=1024, force=False):
    """Honed limestone for the planter, tileable, one tile = 0.5 m: soft clouding, faint
    bedding along u, shell specks and pin pores."""
    cpath = os.path.join(textures.TEX_DIR, "T_LibraryPlant_Stone.png")
    npath = os.path.join(textures.TEX_DIR, "T_LibraryPlant_Stone_Normal.png")
    if os.path.exists(cpath) and os.path.exists(npath) and not force:
        return cpath, npath
    rng = np.random.default_rng(57)
    cloud = textures._noise(n, 1.0, 1.0, 1.7, rng)
    bed = textures._noise(n, 6.0, 0.25, 1.2, rng)
    grain = textures._noise(n, 1.0, 1.0, 0.3, rng)
    base = np.array([0.47, 0.43, 0.36])
    col = base * (1 + 0.06 * cloud[..., None] + 0.035 * bed[..., None] + 0.03 * grain[..., None])
    height = 0.15 * grain
    # specks and pores (wrapping, tileable)
    for _ in range(900):
        cx, cy = rng.uniform(0, n), rng.uniform(0, n)
        rr = rng.uniform(0.6, 2.2)
        r0, c0 = int(cy) - 6, int(cx) - 6
        rs = np.arange(r0, r0 + 13) % n
        cs = np.arange(c0, c0 + 13) % n
        dy = (np.arange(r0, r0 + 13) + 0.5 - cy)[:, None]
        dx = (np.arange(c0, c0 + 13) + 0.5 - cx)[None, :]
        m = np.exp(-((dx ** 2 + dy ** 2) / rr ** 2))
        kind = rng.random()
        if kind < 0.55:            # pore: dark, sunken
            col[np.ix_(rs, cs)] *= (1 - 0.35 * m)[..., None]
            height[np.ix_(rs, cs)] -= 1.2 * m
        elif kind < 0.85:          # warm shell fragment
            col[np.ix_(rs, cs)] = col[np.ix_(rs, cs)] * (1 - 0.5 * m[..., None]) + np.array([0.40, 0.33, 0.24]) * 0.5 * m[..., None]
        else:                      # pale calcite
            col[np.ix_(rs, cs)] = col[np.ix_(rs, cs)] * (1 - 0.5 * m[..., None]) + np.array([0.62, 0.59, 0.53]) * 0.5 * m[..., None]
    px = 0.5 / n
    nrm = _height_to_normal(height * 0.00025, px, px, 1.0)
    textures._save("T_LibraryPlant_Stone", textures._to_srgb(np.clip(col, 0, 1)))
    textures._save("T_LibraryPlant_Stone_Normal", nrm * 0.5 + 0.5, non_color=True)
    return cpath, npath


def plant_materials():
    cpath, npath = atlas()
    spath, snpath = stone_maps()
    atlas_c = textures.load(cpath)
    atlas_n = textures.load(npath, non_color=True)
    stone = common.pbr_material("M_LibraryPlant_Planter", (1, 1, 1), roughness=0.78)
    common.set_base_color_map(stone, textures.load(spath))
    common.set_normal_map(stone, textures.load(snpath, non_color=True), 0.8)
    leaf = common.pbr_material("M_LibraryPlant_Leaf", (1, 1, 1), roughness=0.42)
    common.set_base_color_map(leaf, atlas_c)
    common.set_normal_map(leaf, atlas_n, 0.8)
    leaf.use_backface_culling = False
    bark = common.pbr_material("M_LibraryPlant_Bark", (1, 1, 1), roughness=0.85)
    common.set_base_color_map(bark, atlas_c)
    common.set_normal_map(bark, atlas_n, 1.0)
    return stone, leaf, bark


# ------------------------------------------------------------------ geometry helpers

def _frame(t, prev=None):
    """Perpendicular vector to t (parallel-transported from prev when given)."""
    if prev is not None:
        n = prev - t * prev.dot(t)
        if n.length > 1e-6:
            return n.normalized()
    a = Vector((1, 0, 0)) if abs(t.x) < 0.9 else Vector((0, 1, 0))
    return t.cross(a).normalized()


def tube(bm, uvl, pts, radii, sides, v_start=0.0, cap=None, bump=None):
    """Tapered tube along pts with bark-strip UVs (u round, v = arc length). cap: (length,
    (u, v)) closes the end in a cone (the stipule sheath at a shoot tip). Returns the rings."""
    u0, u1, v0, v1 = BARK_REG
    pts = [Vector(p) for p in pts]
    n = len(pts)
    tangents = []
    for i in range(n):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
        tangents.append((b - a).normalized())
    rings, s, nprev = [], v_start, None
    for i, (p, r) in enumerate(zip(pts, radii)):
        if i:
            s += (pts[i] - pts[i - 1]).length
        t = tangents[i]
        nv = _frame(t, nprev)
        nprev = nv
        bv = t.cross(nv)
        ring = []
        for k in range(sides + 1):
            ang = 2 * math.pi * k / sides
            rr = r * (1 + (bump(i, k % sides) if bump else 0.0))
            co = p + (nv * math.cos(ang) + bv * math.sin(ang)) * rr
            vert = bm.verts.new(co) if k < sides else ring[0][0]
            ring.append((vert, (u0 + (u1 - u0) * k / sides, v0 + (v1 - v0) * min(s / BARK_LEN, 0.999))))
        rings.append(ring)
    for i in range(n - 1):
        for k in range(sides):
            a, b, c, d = rings[i][k], rings[i][k + 1], rings[i + 1][k + 1], rings[i + 1][k]
            f = bm.faces.new((a[0], b[0], c[0], d[0]))
            for lp, uv in zip(f.loops, (a[1], b[1], c[1], d[1])):
                lp[uvl].uv = uv
    if cap:
        ln, uv = cap
        tip = bm.verts.new(pts[-1] + tangents[-1] * ln)
        for k in range(sides):
            f = bm.faces.new((rings[-1][k][0], rings[-1][k + 1][0], tip))
            for lp in f.loops:
                lp[uvl].uv = uv
    return rings


def _bend(p, curl, b):
    """Midrib position (along, up) and angle at b for a blade of unit length, start pitch p,
    bending down by `curl` radians over its length."""
    th = p - curl * b
    if abs(curl) < 1e-4:
        return b * math.cos(p), b * math.sin(p), th
    return (math.sin(p) - math.sin(th)) / curl, (math.cos(th) - math.cos(p)) / curl, th


def leaf_points(base, e1, e2, L, W, pitch, curl, roll, twist, cup, wave, phase):
    """World positions of the leaf grid (rows x 5) and its leaf-space (x, b)."""
    up = e1.cross(e2)
    half = W * 0.5
    out = []
    for row in leaf_rows():
        pr = []
        for j, (x, b) in enumerate(row):
            al, upc, th = _bend(pitch, curl, b)
            tng = e1 * math.cos(th) + up * math.sin(th)
            nrm = -e1 * math.sin(th) + up * math.cos(th)
            rl = roll + twist * b
            sd = e2 * math.cos(rl) + nrm * math.sin(rl)
            nn = nrm * math.cos(rl) - e2 * math.sin(rl)
            ax = abs(x)
            lift = half * (cup * ax ** 2 + 0.03 * ax)
            lift += L * wave * math.sin(2 * math.pi * (1.7 * b + phase + (0.37 if x > 0 else 0.0))) \
                * ax ** 1.5 * min(1.0, b / 0.3 if b > 0 else 0.0)
            co = base + (e1 * al + up * upc) * L + sd * (x * half) + nn * lift
            pr.append((co, x, b))
        out.append(pr)
    return out


def add_leaf(bm, uvl, grid, reg, flip):
    vs = [[bm.verts.new(co) for co, x, b in row] for row in grid]
    for r in range(len(grid) - 1):
        for c in range(4):
            quad = (vs[r][c], vs[r][c + 1], vs[r + 1][c + 1], vs[r + 1][c])
            xb = (grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c])
            f = bm.faces.new(quad)
            for lp, (co, x, b) in zip(f.loops, xb):
                lp[uvl].uv = leaf_uv(reg, x, b, flip)
    return vs


def petiole(bm, uvl, a, b, r0, r1, reg):
    """Three-sided stalk from the stem node a to the blade's base b (6 triangles)."""
    t = (b - a).normalized()
    nv = _frame(t)
    bv = t.cross(nv)
    rings = []
    for p, r in ((a, r0), (b, r1)):
        rings.append([bm.verts.new(p + (nv * math.cos(2 * math.pi * k / 3) + bv * math.sin(2 * math.pi * k / 3)) * r)
                      for k in range(3)])
    uvs = [leaf_uv(reg, 0.0, -0.03), leaf_uv(reg, 0.0, 0.03)]
    for k in range(3):
        k2 = (k + 1) % 3
        f = bm.faces.new((rings[0][k], rings[0][k2], rings[1][k2], rings[1][k]))
        for lp, uv in zip(f.loops, (uvs[0], uvs[0], uvs[1], uvs[1])):
            lp[uvl].uv = (uv[0] + (0.002 if lp.vert in (rings[0][k2], rings[1][k2]) else -0.002), uv[1])


def polyline_at(pts, s):
    """Point and tangent at arc length s along pts."""
    acc = 0.0
    for i in range(len(pts) - 1):
        seg = (pts[i + 1] - pts[i]).length
        if acc + seg >= s or i == len(pts) - 2:
            t = min(max((s - acc) / max(seg, 1e-9), 0.0), 1.0)
            return pts[i].lerp(pts[i + 1], t), (pts[i + 1] - pts[i]).normalized()
        acc += seg
    return pts[-1], (pts[-1] - pts[-2]).normalized()


def polyline_len(pts):
    return sum((pts[i + 1] - pts[i]).length for i in range(len(pts) - 1))


def radius_at(radii, pts, s):
    acc = 0.0
    for i in range(len(pts) - 1):
        seg = (pts[i + 1] - pts[i]).length
        if acc + seg >= s:
            t = (s - acc) / max(seg, 1e-9)
            return radii[i] * (1 - t) + radii[i + 1] * t
        acc += seg
    return radii[-1]


# ------------------------------------------------------------------ build

def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    rnd = random.Random(p["seed"])
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    stone, leaf_m, bark = plant_materials()

    R, PH, H = p["pot_r"], p["pot_h"], p["height"]

    # ---------------- planter: fluted limestone cylinder, open at the bottom
    F = int(p["flutes"])
    segs = 2 * F
    depth = 0.013
    prof = [(R * 0.955, 0.0, 0.0), (R * 0.985, 0.032, 1.0), (R * 1.03, PH - 0.058, 1.0),
            (R * 1.036, PH - 0.032, 0.0), (R * 1.032, PH - 0.007, 0.0), (R * 1.0, PH, 0.0),
            (R * 0.945, PH - 0.006, 0.0), (R * 0.925, PH - 0.08, 0.0)]
    pm = Mesh(0.5)
    bm, uvl = pm.bm, pm.uv
    rows = []
    for r, z, f in prof:
        ring = []
        for k in range(segs + 1):
            ang = 2 * math.pi * k / segs + math.pi / segs
            rr = r - depth * f * (k % 2)
            vert = bm.verts.new((rr * math.cos(ang), rr * math.sin(ang), z)) if k < segs else ring[0][0]
            ring.append((vert, 2 * math.pi * R * k / segs / 0.5))
        rows.append(ring)
    vacc = [0.0]
    for i in range(1, len(prof)):
        vacc.append(vacc[-1] + math.hypot(prof[i][0] - prof[i - 1][0], prof[i][1] - prof[i - 1][1]))
    for i in range(len(prof) - 1):
        for k in range(segs):
            a, b, c, d = rows[i][k], rows[i][k + 1], rows[i + 1][k + 1], rows[i + 1][k]
            fc = bm.faces.new((a[0], b[0], c[0], d[0]))
            for lp, (vv, uu), vz in zip(fc.loops, (a, b, c, d), (vacc[i], vacc[i], vacc[i + 1], vacc[i + 1])):
                lp[uvl].uv = (uu, vz / 0.5)
    # crisp ridges: the flutes' ridge edges are sharp, so each flute shades as a concave scallop
    for i in range(3):
        for k in range(0, segs, 2):
            e = bm.edges.get((rows[i][k][0], rows[i + 1][k][0]))
            if e:
                e.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    pot = pm.to_object(f"{n}_Planter", col, stone, root, smooth=True)

    # ---------------- trunk
    soil_z = PH - 0.05
    top_z = H - 0.11
    tz = [soil_z - 0.02, soil_z + 0.012, soil_z + 0.05, soil_z + 0.16]
    tz += [soil_z + 0.16 + (top_z - soil_z - 0.16) * i / 9 for i in range(1, 10)]
    trunk_pts = [Vector((0.011 * math.sin(2.1 * z + 0.4) - 0.004, 0.009 * math.sin(2.9 * z + 1.9), z)) for z in tz]
    rad = []
    for z in tz:
        h01 = (z - soil_z) / (top_z - soil_z)
        r = 0.0175 * (1 - h01) + 0.0065 * h01
        r += 0.010 * math.exp(-max(z - soil_z, 0) / 0.022)          # root flare
        rad.append(r)
    flare = lambda i, k: (0.22 * math.cos(k * 2.4 + 1.0) * (i < 2)) + 0.04 * math.sin(i * 1.7 + k * 0.9)
    tm = Mesh(0.5)
    tube(tm.bm, tm.uv, trunk_pts, rad, 8, 0.0, cap=(0.03, leaf_uv(1, 0.0, 0.02)), bump=flare)
    tm.to_object(f"{n}_Trunk", col, bark, root, smooth=True)

    # ---------------- shoots (branches): short, rising, curving up at the tips
    stems = []   # (pts, radii, s_from, s_to, leaves)
    br = Mesh(0.5)
    branch_specs = [(1.12, 35.0, 0.34, 34.0), (1.22, 160.0, 0.32, 31.0), (1.33, 275.0, 0.27, 28.0)]
    for bz, az, ln, ang in branch_specs:
        az = math.radians(az + rnd.uniform(-12, 12))
        a0, _ = polyline_at(trunk_pts, bz - soil_z + 0.02)
        d = Vector((math.cos(az), math.sin(az), 0))
        # integrate the curving direction
        pts = [a0 - d * 0.004]
        cur = pts[0].copy()
        for i in range(1, 6):
            t = i / 5
            tilt = math.radians(ang * (1 - 0.55 * t))
            step = d * math.sin(tilt) + Vector((0, 0, math.cos(tilt)))
            cur = cur + step * (ln / 5)
            pts.append(cur.copy())
        r0 = radius_at(rad, trunk_pts, bz - soil_z) * 0.62
        radii = [r0 * (1 - 0.55 * i / 5) for i in range(6)]
        tube(br.bm, br.uv, pts, radii, 6, 0.75, cap=(0.028, leaf_uv(1, 0.0, 0.02)))
        stems.append((pts, radii))
    br.to_object(f"{n}_Shoots_NoCollide", col, bark, root, smooth=True)

    # ---------------- leaves
    lm = Mesh(0.5)
    bm, uvl = lm.bm, lm.uv
    total = int(p["leaves"])
    lead_s0 = 1.36 - soil_z
    lead_len = polyline_len(trunk_pts)
    shoots = [(trunk_pts, rad, lead_s0, lead_len - 0.012)]
    for pts, radii in stems:
        L_ = polyline_len(pts)
        shoots.append((pts, radii, L_ * 0.32, L_ - 0.01))
    lower = (trunk_pts, rad, 0.98 - soil_z, 1.11 - soil_z)
    # how many per shoot (leader gets the most, three on the bare trunk below the fork)
    weights = [0.29, 0.22, 0.21, 0.19]
    n_lower = 3
    counts = [max(3, int(round((total - n_lower) * w))) for w in weights]
    counts[0] += (total - n_lower) - sum(counts)
    plan = [(shoots[i], counts[i], False) for i in range(4)] + [(lower, n_lower, True)]
    placed = []      # leaf centroids, to keep blades apart
    crown_r = p["crown_r"]
    phi0 = rnd.uniform(0, 6.28)
    for (pts, radii, sa, sb), cnt, is_lower in plan:
        phi = rnd.uniform(0, 6.28)
        for k in range(cnt):
            f = k / max(cnt - 1, 1)                          # 0 = oldest (lowest) .. 1 = tip
            if is_lower:
                f = 0.0
            s = sa + (sb - sa) * (1 - (1 - (k + 0.5) / cnt) ** 1.7)
            node, tng = polyline_at(pts, s)
            rr = radius_at(radii, pts, s)
            age = 1 - f                                      # 1 = old
            young = f > 0.82 and not is_lower
            L = (0.15 + 0.15 * min(age * 1.4, 1.0)) * rnd.uniform(0.9, 1.08)
            if is_lower:
                L = rnd.uniform(0.27, 0.31)
            W = L * rnd.uniform(0.68, 0.78)                  # full width
            best = None
            for attempt in range(7):
                ph = phi + rnd.uniform(-0.3, 0.3) * (1 + attempt * 0.5)
                radial = Vector((math.cos(ph), math.sin(ph), 0))
                radial = (radial - tng * radial.dot(tng)).normalized()
                lift = math.radians(70 if young else 45 + 10 * f)   # petiole angle up from radial
                pdir = (radial * math.cos(lift) + tng * math.sin(lift)).normalized()
                pl = (0.025 if young else 0.045) * rnd.uniform(0.85, 1.2)
                a = node + radial * rr * 0.6
                bpt = a + pdir * pl
                e1 = Vector((pdir.x, pdir.y, 0))
                if e1.length < 1e-4:
                    e1 = radial
                e1.normalize()
                e2 = Vector((0, 0, 1)).cross(e1).normalized()
                pitch = math.radians((55 + rnd.uniform(-8, 8)) if young else (26 - 34 * age ** 1.1 + rnd.uniform(-8, 8)))
                curl = (0.2 if young else 0.3 + 0.3 * age) * rnd.uniform(0.8, 1.25)
                roll = rnd.uniform(-0.3, 0.3)
                twist = rnd.uniform(-0.25, 0.25)
                cup = (0.45 if young else 0.2) * rnd.uniform(0.7, 1.3)
                wave = rnd.uniform(0.012, 0.024)
                wph = rnd.random()
                LL, WW = L, W
                for it in range(7):     # shrink, then lift it until it fits the crown footprint
                    grid = leaf_points(bpt, e1, e2, LL, WW, pitch, curl, roll, twist, cup, wave, wph)
                    rmax = max(math.hypot(co.x, co.y) for row in grid for co, _, _ in row)
                    if rmax <= crown_r:
                        break
                    if it < 2:
                        LL, WW = LL * 0.92, WW * 0.92
                    else:
                        pitch += math.radians(8)
                while rmax > crown_r and LL > 0.08:          # last resort: a smaller leaf
                    LL, WW = LL * 0.9, WW * 0.9
                    grid = leaf_points(bpt, e1, e2, LL, WW, pitch, curl, roll, twist, cup, wave, wph)
                    rmax = max(math.hypot(co.x, co.y) for row in grid for co, _, _ in row)
                cen = sum((co for row in grid for co, _, _ in row), Vector()) / sum(len(r) for r in grid)
                dmin = min([(cen - c).length for c in placed] or [1.0])
                score = dmin - max(rmax - crown_r, 0) * 10
                if best is None or score > best[0]:
                    best = (score, grid, a, bpt, cen)
            _, grid, a, bpt, cen = best
            placed.append(cen)
            reg = 1 if young else 0
            add_leaf(bm, uvl, grid, reg, flip=rnd.random() < 0.5)
            petiole(bm, uvl, a, bpt + (bpt - a).normalized() * 0.004, 0.0032 if not young else 0.0024,
                    0.0026 if not young else 0.002, reg)
            phi += math.radians(137.5)
    lm.to_object(f"{n}_Leaves_NoCollide", col, leaf_m, root, smooth=True)

    # ---------------- mulch: a low mound inside the rim, round the trunk
    sm = Mesh(0.5)
    bm, uvl = sm.bm, sm.uv
    su0, su1, sv0, sv1 = SOIL_REG
    rings_r = (0.028, 0.09, 0.16, R * 0.93)
    nseg = 20
    grid = []
    srnd = random.Random(p["seed"] + 7)
    for ri, rr in enumerate(rings_r):
        ring = []
        for k in range(nseg):
            ang = 2 * math.pi * (k + 0.5 * ri) / nseg
            x, y = rr * math.cos(ang), rr * math.sin(ang)
            z = soil_z + 0.016 * (1 - rr / (R * 0.93)) ** 1.5 + srnd.uniform(-0.003, 0.003) * (ri < 3)
            ring.append(bm.verts.new((x, y, z)))
        grid.append(ring)
    span = 2 * R * 0.95
    for ri in range(len(rings_r) - 1):
        for k in range(nseg):
            k2 = (k + 1) % nseg
            if ri % 2 == 0:
                tris = ((grid[ri][k], grid[ri + 1][k], grid[ri + 1][k2]), (grid[ri][k], grid[ri + 1][k2], grid[ri][k2]))
            else:
                tris = ((grid[ri][k], grid[ri + 1][k2], grid[ri][k2]), (grid[ri][k], grid[ri + 1][k], grid[ri + 1][k2]))
            for tri in tris:
                try:
                    fc = bm.faces.new(tri)
                except ValueError:
                    continue
                for lp in fc.loops:
                    co = lp.vert.co
                    lp[uvl].uv = (su0 + (co.x / span + 0.5) * (su1 - su0), sv0 + (co.y / span + 0.5) * (sv1 - sv0))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    for fc in bm.faces:
        if fc.normal.z < 0:
            fc.normal_flip()
    sm.to_object(f"{n}_Soil", col, bark, root, smooth=True)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
