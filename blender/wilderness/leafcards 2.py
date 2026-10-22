"""Twig-card baker (vegetation.md gap #3): composes leaves, needles, fronds and flowers onto procedural
twigs, renders each twig flat (ortho camera looking down -Z, Eevee emission passes) and packs the
renders into shared RGBA leaf atlases with a matching tangent-space normal atlas.

Pieces:
  outlines   species leaf silhouettes as 2D polygons (tulip, lobed oaks, palmate maple, leaflets, ...),
             corner-preserving Chaikin smoothing, normalised to x in [-0.5, 0.5], y in [0, 1] (base -> tip)
  leaf_tex   outline -> RGBA texture: species colour, procedural veins, fine grain taken from a Poly Haven
             leaf scan (island_tree_02, CC0) as a high-pass multiplier, darker margin, base->tip gradient
  Card       a scene description: stems (tapered tubes) + leaves (bent quads textured by a leaf_tex)
  render     albedo (tex x per-leaf tint, soft alpha) and normal (geometric, folded to face the camera)
             emission renders to linear EXR, un-premultiplied and colour-dilated
  atlas      shelf-packed; each card -> rect (x0, y0, x1, y1, side, base) in 1/8-atlas units, y down
             (the format trees.card_rects reads), plus its real size in metres and its mean colour

Cards are cached per card in build/wilderness/veg/src_prep/cards/<name>_<hash>.npz (the hash covers the
card's definition and this file's CARD_VERSION), atlases in src_prep/T_Veg_<Atlas>_Leaf{,_N}.png +
<atlas>.json. Changing one card re-renders only that card.
"""
import hashlib
import inspect
import json
import math
import os
import random

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
PREP = os.path.join(PROJECT, "build", "wilderness", "veg", "src_prep")
CARD_CACHE = os.path.join(PREP, "cards")
CARD_VERSION = 3
Z = Vector((0, 0, 1))


# =============================================================================================
# colour helpers
def srgb_to_lin(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(np.asarray(c, np.float32), 0, None)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def hexlin(h):
    h = h.lstrip("#")
    return srgb_to_lin([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def lin_hex(c):
    s = np.clip(lin_to_srgb(c), 0, 1)
    return "#" + "".join(f"{int(round(v * 255)):02X}" for v in s[:3])


# =============================================================================================
# outlines
def chaikin(pts, sharp, iters=3):
    """Closed-polygon Chaikin corner cutting that keeps the vertices flagged sharp (lobe tips, teeth)."""
    for _ in range(iters):
        out, osharp = [], []
        n = len(pts)
        for i in range(n):
            p, q = np.array(pts[i]), np.array(pts[(i + 1) % n])
            if sharp[i]:
                out.append(tuple(p))
                osharp.append(True)
                if not sharp[(i + 1) % n]:
                    out.append(tuple(0.25 * p + 0.75 * q))
                    osharp.append(False)
                continue
            out.append(tuple(0.75 * p + 0.25 * q))
            osharp.append(False)
            if not sharp[(i + 1) % n]:
                out.append(tuple(0.25 * p + 0.75 * q))
                osharp.append(False)
        pts, sharp = out, osharp
    return pts


def mirror(half):
    """half: [(x >= 0, y, sharp)] from the base (x = 0) to the tip (x = 0) along the right margin ->
    closed outline (right side up, left side down)."""
    right = list(half)
    left = [(-x, y, s) for x, y, s in reversed(half[1:-1])]
    pts = right + left
    return [(x, y) for x, y, _ in pts], [s for _, _, s in pts]


def normalise(pts):
    """Fit an outline to y in [0, 1] (base at y = 0), x centred; returns (pts, aspect W/L)."""
    a = np.array(pts, np.float32)
    y0, y1 = a[:, 1].min(), a[:, 1].max()
    L = y1 - y0
    a[:, 1] = (a[:, 1] - y0) / L
    a[:, 0] = a[:, 0] / L
    W = a[:, 0].max() - a[:, 0].min()
    cx = (a[:, 0].max() + a[:, 0].min()) / 2
    a[:, 0] = (a[:, 0] - cx) / W              # x in [-0.5, 0.5] of the texture
    return a, float(W)


def envelope_half(w_fn, n=24, teeth=0, tooth_depth=0.0, tooth_fwd=0.0, tip_sharp=True, y0=0.0, round_teeth=False):
    """Half outline from a half-width function w(y), optional serration (teeth per side)."""
    half = [(0.0, y0, True)]
    m = max(n, teeth * 2)
    for i in range(1, m):
        y = i / m
        w = w_fn(y)
        if teeth:
            k = i % 2
            if k == 1:
                half.append((w, min(1, y + tooth_fwd), not round_teeth))
            else:
                half.append((w * (1 - tooth_depth), y, False))
        else:
            half.append((w, y, False))
    half.append((0.0, 1.0, tip_sharp))
    return half


def _sx(pts, k):
    return [(x * k, y) for x, y in pts]


# width : length of each outline (real leaves: Sargent / USFS silvics descriptions)
ASPECT = dict(red_oak=0.62, white_oak=0.6, chestnut_oak=0.46, leaflet_serrate=0.34, leaflet_obovate=0.44,
              rhodo=0.27, laurel=0.34, catawba=0.46, doghobble=0.34, cinn_pinna=0.24)


def outline(kind):
    """Leaf outlines by name -> (pts (N, 2) normalised, aspect)."""
    pts, aspect = _outline(kind)
    return pts, aspect


def _outline(kind):
    if kind == "tulip":
        # Liriodendron: four lobes, truncate notched apex, broad truncate base, nearly square
        half = [(0.0, 0.05, True), (0.1, 0.0, False), (0.26, 0.03, False), (0.42, 0.13, False), (0.53, 0.27, True),
                (0.43, 0.35, False), (0.33, 0.46, False), (0.37, 0.56, False), (0.46, 0.67, False), (0.55, 0.79, True),
                (0.4, 0.88, False), (0.24, 0.98, True), (0.12, 0.93, False), (0.0, 0.85, True)]
        p, s = mirror(half)
        return normalise(chaikin(p, s))
    if kind == "red_oak":
        # Quercus rubra: 7-11 bristle-tipped pointed lobes, sinuses about half-way to the midrib
        half = [(0.0, 0.0, True), (0.07, 0.04, False), (0.13, 0.1, False), (0.3, 0.2, True), (0.27, 0.23, True),
                (0.13, 0.3, False), (0.16, 0.36, False), (0.42, 0.42, True), (0.36, 0.45, True), (0.4, 0.5, True),
                (0.18, 0.53, False), (0.2, 0.59, False), (0.4, 0.66, True), (0.34, 0.68, True), (0.36, 0.72, True),
                (0.16, 0.75, False), (0.18, 0.8, False), (0.27, 0.86, True), (0.12, 0.89, False), (0.1, 0.93, False),
                (0.0, 1.0, True)]
        p, s = mirror(half)
        return normalise(chaikin(_sx(p, ASPECT[kind] / 0.96), s, 3))
    if kind == "white_oak":
        # Quercus alba: 7-9 rounded finger lobes, sinuses of varying depth, tapered base
        half = [(0.0, 0.0, True), (0.05, 0.05, False), (0.13, 0.12, False), (0.17, 0.17, False), (0.12, 0.22, False),
                (0.08, 0.26, False), (0.24, 0.31, False), (0.33, 0.37, False), (0.26, 0.43, False), (0.1, 0.46, False),
                (0.3, 0.52, False), (0.42, 0.58, False), (0.34, 0.65, False), (0.14, 0.67, False), (0.26, 0.73, False),
                (0.33, 0.79, False), (0.24, 0.84, False), (0.12, 0.86, False), (0.18, 0.92, False), (0.1, 0.98, False),
                (0.0, 1.0, False)]
        p, s = mirror(half)
        return normalise(chaikin(_sx(p, ASPECT[kind] / 0.84), s, 4))
    if kind == "chestnut_oak":
        # Quercus montana: obovate, wavy round-toothed (crenate) margin, widest above the middle
        half = envelope_half(lambda y: 0.5 * math.sin(math.pi * min(1, y ** 0.82)) ** 0.75 * (0.6 + 0.4 * y),
                             teeth=11, tooth_depth=0.13, round_teeth=True, tip_sharp=False)
        p, s = mirror(half)
        return normalise(chaikin(_sx(p, ASPECT[kind]), s, 3))
    if kind == "maple":
        # Acer saccharum: palmate, 5 lobes, few large blunt-pointed teeth, U-shaped sinuses
        c = (0.0, 0.33)

        def P(a, r, sh):
            a = math.radians(a)
            return (c[0] + r * math.cos(a), c[1] + r * math.sin(a), sh)
        half = [(0.0, 0.3, True), P(-70, 0.12, False), P(-45, 0.3, False), P(-30, 0.42, True), P(-18, 0.4, False),
                P(-8, 0.44, True), P(6, 0.34, False), P(14, 0.3, False), P(22, 0.36, False), P(27, 0.52, True),
                P(31, 0.48, False), P(38, 0.63, True), P(45, 0.52, False), P(51, 0.55, True), P(60, 0.36, False),
                P(68, 0.32, False), P(74, 0.4, False), P(77, 0.52, True), P(81, 0.5, False), P(86, 0.66, True),
                (0.0, 1.0, True)]
        p, s = mirror(half)
        return normalise(chaikin(p, s, 3))
    if kind == "leaflet_serrate":       # buckeye / hickory leaflet: elliptic-lanceolate, finely serrate
        half = envelope_half(lambda y: 0.5 * math.sin(math.pi * y ** 0.9) ** 0.85, teeth=16, tooth_depth=0.06,
                             tooth_fwd=0.012)
        p, s = mirror(half)
        return normalise(chaikin(_sx(p, ASPECT[kind]), s, 2))
    if kind == "leaflet_obovate":       # hickory terminal leaflet: obovate, serrate, acuminate
        half = envelope_half(lambda y: 0.5 * math.sin(math.pi * y ** 0.7) ** 0.9, teeth=16, tooth_depth=0.06,
                             tooth_fwd=0.012)
        p, s = mirror(half)
        return normalise(chaikin(_sx(p, ASPECT[kind]), s, 2))
    if kind == "rhodo":                 # rosebay: long elliptic-oblong, entire, revolute margin
        half = envelope_half(lambda y: 0.5 * math.sin(math.pi * y ** 0.95) ** 0.6, n=20)
        p, s = mirror(half)
        return normalise(chaikin(_sx(p, ASPECT[kind]), s, 3))
    if kind == "laurel":                # Kalmia: elliptic, pointed at both ends
        half = envelope_half(lambda y: 0.5 * math.sin(math.pi * y) ** 0.95, n=20)
        p, s = mirror(half)
        return normalise(chaikin(_sx(p, ASPECT[kind]), s, 3))
    if kind == "catawba":               # oval-elliptic, rounded base, blunt tip
        half = envelope_half(lambda y: 0.5 * math.sin(math.pi * (0.06 + 0.9 * y)) ** 0.5, n=20, tip_sharp=False)
        p, s = mirror(half)
        return normalise(chaikin(_sx(p, ASPECT[kind]), s, 3))
    if kind == "doghobble":             # Leucothoe: ovate-lanceolate, long acuminate tip, fine teeth
        half = envelope_half(lambda y: 0.5 * math.sin(math.pi * y ** 0.55) ** 0.9 * (1 - 0.25 * y), teeth=14,
                             tooth_depth=0.05, tooth_fwd=0.01)
        p, s = mirror(half)
        return normalise(chaikin(_sx(p, ASPECT[kind]), s, 2))
    if kind == "xmas_pinna":            # Polystichum: falcate lanceolate pinna with an upper auricle ("stocking")
        pts = [(0.0, 0.0), (0.2, 0.06), (0.3, 0.25), (0.3, 0.5), (0.24, 0.72), (0.14, 0.9), (0.02, 1.0),
               (-0.06, 0.93), (-0.16, 0.75), (-0.2, 0.5), (-0.2, 0.3), (-0.3, 0.24), (-0.44, 0.17), (-0.36, 0.08),
               (-0.12, 0.04)]
        sharp = [True, False, False, False, False, False, True, False, False, False, False, False, True, False, False]
        return normalise(chaikin(pts, sharp, 3))
    if kind == "cinn_pinna":            # Osmundastrum: linear-lanceolate pinna cut into rounded lobes
        half = envelope_half(lambda y: 0.5 * (math.sin(math.pi * y ** 0.8) ** 0.5), teeth=12, tooth_depth=0.45,
                             round_teeth=True)
        p, s = mirror(half)
        return normalise(chaikin(_sx(p, ASPECT[kind]), s, 3))
    if kind == "needle":                # flat hemlock needle, rounded tip
        half = [(0.0, 0.0, True), (0.35, 0.03, False), (0.5, 0.15, False), (0.5, 0.88, False), (0.35, 0.98, False),
                (0.0, 1.0, False)]
        p, s = mirror(half)
        a, _ = normalise(chaikin(p, s, 2))
        return a, 0.11
    if kind == "strip":                 # a thin tapered strip (pine needle, sporangia stalk, bark strip)
        half = [(0.0, 0.0, True), (0.5, 0.02, False), (0.5, 0.9, False), (0.0, 1.0, True)]
        p, s = mirror(half)
        a, _ = normalise(p)
        return a, 0.03
    if kind == "bark_strip":            # shagbark plate: long, curling, ragged ends
        pts = [(0.0, 0.0), (0.3, 0.02), (0.5, 0.1), (0.46, 0.5), (0.5, 0.86), (0.28, 1.0), (0.1, 0.94),
               (-0.2, 1.0), (-0.5, 0.88), (-0.44, 0.45), (-0.5, 0.08), (-0.24, 0.03)]
        sharp = [False, False, True, False, True, True, False, True, True, False, True, False]
        a, _ = normalise(chaikin(pts, sharp, 2))
        return a, 0.16
    if kind in ("floret5", "floret_cup"):
        n = 72
        k = 0.24 if kind == "floret5" else 0.1
        pts = []
        for i in range(n):
            t = 2 * math.pi * i / n
            r = 0.5 * (1 - k + k * math.cos(5 * t)) ** 0.6
            pts.append((r * math.sin(t), 0.5 + r * math.cos(t)))
        return normalise(pts)
    if kind == "bud":
        half = envelope_half(lambda y: 0.5 * math.sin(math.pi * y ** 1.4) ** 0.7, n=16)
        p, s = mirror(half)
        a, _ = normalise(chaikin(p, s, 2))
        return a, 0.55
    if kind == "round":
        n = 40
        pts = [(0.5 * math.sin(2 * math.pi * i / n), 0.5 + 0.5 * math.cos(2 * math.pi * i / n)) for i in range(n)]
        return normalise(pts)
    raise KeyError(kind)


def raster(pts, W, H, ss=3):
    """Coverage (H, W) of a closed polygon in texture units (x in [-0.5, 0.5], y in [0, 1] up)."""
    xs = (np.arange(W * ss) + 0.5) / (W * ss) - 0.5
    ys = 1 - (np.arange(H * ss) + 0.5) / (H * ss)
    X, Y = np.meshgrid(xs, ys)
    inside = np.zeros(X.shape, bool)
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        if y1 == y2:
            continue
        cond = (y1 > Y) != (y2 > Y)
        xint = x1 + (Y - y1) * (x2 - x1) / (y2 - y1)
        inside ^= cond & (X < xint)
    return inside.reshape(H, ss, W, ss).mean((1, 3)).astype(np.float32)


# =============================================================================================
# leaf textures
_scan_detail = None


def scan_detail():
    """High-pass luminance of a scanned leaf's interior (island_tree_02, CC0): veins + grain, mean 1."""
    global _scan_detail
    if _scan_detail is not None:
        return _scan_detail
    import veg_sources
    im = bpy.data.images.load(veg_sources.path("island_tree_02", "leaves_diff"), check_existing=False)
    w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, im.channels)[::-1]     # row 0 = top
    bpy.data.images.remove(im)
    # the first leaf in the atlas (top-left), its central interior
    crop = a[int(h * 0.05):int(h * 0.38), int(w * 0.03):int(w * 0.15), :3]
    hh, ww = crop.shape[:2]
    crop = crop[int(hh * 0.2):int(hh * 0.8), int(ww * 0.28):int(ww * 0.72)]
    L = srgb_to_lin(crop) @ np.array([0.3, 0.6, 0.1], np.float32)
    k = 9
    pad = np.pad(L, k, mode="reflect")
    c = pad.cumsum(0).cumsum(1)
    blur = (c[2 * k:, 2 * k:] - c[:-2 * k, 2 * k:] - c[2 * k:, :-2 * k] + c[:-2 * k, :-2 * k]) / (2 * k) ** 2
    d = L[:blur.shape[0], :blur.shape[1]] / np.maximum(blur, 1e-3)
    _scan_detail = np.clip(d, 0.6, 1.4).astype(np.float32)
    return _scan_detail


def _resample(img, W, H):
    h, w = img.shape[:2]
    ys = np.clip(((np.arange(H) + 0.5) / H * h).astype(int), 0, h - 1)
    xs = np.clip(((np.arange(W) + 0.5) / W * w).astype(int), 0, w - 1)
    return img[ys][:, xs]


def leaf_tex(shape, colour, W=192, H=None, veins="pinnate", vein_k=0.12, grain=0.5, margin_k=0.12,
             tip_k=0.08, vein_colour=None, seed=1, spots=None, ring=None, centre=None, lateral=0.6):
    """RGBA (H, W, 4) linear, alpha = coverage. colour / vein_colour: sRGB hex."""
    pts, aspect = outline(shape)
    if H is None:
        H = W
    if W is None or W == H:
        W = max(8, int(round(H * min(1.0, aspect))))
    cov = raster(pts, W, H)
    xs = (np.arange(W) + 0.5) / W - 0.5
    ys = 1 - (np.arange(H) + 0.5) / H
    X, Y = np.meshgrid(xs, ys)
    base = hexlin(colour)
    vc = hexlin(vein_colour) if vein_colour else base * np.array([1.25, 1.22, 0.9], np.float32)
    rgb = np.ones((H, W, 3), np.float32) * base
    m = np.zeros((H, W), np.float32)
    xa = X * aspect                                   # isotropic leaf units
    if veins == "pinnate":
        m = np.maximum(m, np.exp(-(X / 0.035) ** 2) * (Y < 0.97))
        for k in range(1, 9):
            y0 = k / 9.0 * 0.92
            for side in (-1, 1):
                ang = math.radians(48)
                dx, dy = side * math.cos(ang), math.sin(ang)
                px, py = xa, Y - y0
                t = px * dx + py * dy
                d = np.abs(px * dy - py * dx)
                m = np.maximum(m, lateral * np.exp(-(d / 0.012) ** 2) * (t > 0) * (side * X > 0))
    elif veins == "palmate":
        cy = 0.3
        for ang in (90, 52, 15, -25, 128, 165, 205):
            a = math.radians(ang)
            dx, dy = math.cos(a), math.sin(a)
            px, py = xa, Y - cy
            t = px * dx + py * dy
            d = np.abs(px * dy - py * dx)
            m = np.maximum(m, (1.0 if ang == 90 else 0.75) * np.exp(-(d / 0.016) ** 2) * (t > 0))
    elif veins == "midrib":
        m = np.exp(-(X / 0.05) ** 2) * (Y < 0.95)
    elif veins == "parallel":
        m = 0.5 * (0.5 + 0.5 * np.cos(X * 40))
    rgb = rgb * (1 - vein_k * m[..., None]) + vc * (vein_k * m[..., None]) * 1.6 if veins else rgb
    # grain from the scan, a slight base->tip gradient, darker margin
    if grain > 0:
        det = _resample(scan_detail(), W, H)
        rgb *= (1 + grain * (det - 1))[..., None]
    rgb *= (1 - tip_k + 2 * tip_k * Y)[..., None]
    if margin_k > 0:
        edge = np.clip(cov, 0, 1)
        k = 3
        pad = np.pad(edge, k, mode="edge")
        c = pad.cumsum(0).cumsum(1)
        blur = (c[2 * k:, 2 * k:] - c[:-2 * k, 2 * k:] - c[2 * k:, :-2 * k] + c[:-2 * k, :-2 * k]) / (2 * k) ** 2
        blur = blur[:H, :W]
        rgb *= (1 - margin_k * np.clip(1 - blur, 0, 1) * 2)[..., None]
    R = np.sqrt(X ** 2 + (Y - 0.5) ** 2)
    if ring:                                          # flowers: (colour, r0, r1) band
        col, r0, r1 = ring
        band = np.clip(1 - np.abs(R - (r0 + r1) / 2) / ((r1 - r0) / 2 + 1e-4), 0, 1) ** 0.7
        rgb = rgb * (1 - band[..., None]) + hexlin(col) * band[..., None]
    if centre:                                        # flowers: (colour, r)
        col, r0 = centre
        cm = np.clip(1 - R / r0, 0, 1) ** 0.6
        rgb = rgb * (1 - cm[..., None]) + hexlin(col) * cm[..., None]
    if spots:                                         # flowers: (colour, count, r_pos, size, sector)
        col, n, rp, sz, sector = spots
        rr = random.Random(seed)
        for i in range(n):
            a = (2 * math.pi * i / n) if sector is None else math.radians(sector[0] + (sector[1] - sector[0]) * rr.random())
            r = rp * (1 if sector is None else rr.uniform(0.4, 1.0))
            sx, sy = r * math.sin(a), 0.5 + r * math.cos(a)
            d = np.sqrt((X - sx) ** 2 + (Y - sy) ** 2)
            sm = np.clip(1 - d / sz, 0, 1) ** 0.5
            rgb = rgb * (1 - sm[..., None]) + hexlin(col) * sm[..., None]
    return np.dstack([np.clip(rgb, 0, 4), cov]).astype(np.float32), aspect


def strip_tex(colour, colour2=None, W=8, H=128):
    """Plain tapered strip (needles, stalks): colour base -> colour2 tip."""
    pts, aspect = outline("strip")
    cov = raster(pts, W, H, ss=4)
    t = (1 - (np.arange(H) + 0.5) / H)[:, None, None]
    c0, c1 = hexlin(colour), hexlin(colour2 or colour)
    rgb = c0 * (1 - t) + c1 * t
    rgb = np.broadcast_to(rgb, (H, W, 3))
    return np.dstack([rgb, cov]).astype(np.float32), aspect


def scan_tex(src, key_d, key_a, rect, colour_mul=(1, 1, 1)):
    """A region (x0, y0, x1, y1 in 0..1, y down) of a Poly Haven atlas (diffuse + separate alpha)."""
    import veg_sources
    out = []
    for key in (key_d, key_a):
        im = bpy.data.images.load(veg_sources.path(src, key), check_existing=False)
        w, h = im.size
        a = np.array(im.pixels[:], np.float32).reshape(h, w, im.channels)[::-1]
        bpy.data.images.remove(im)
        x0, y0, x1, y1 = rect
        out.append(a[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)])
    d, a = out
    rgb = srgb_to_lin(d[..., :3]) * np.array(colour_mul, np.float32)
    hh, ww = rgb.shape[:2]
    return np.dstack([rgb, a[..., 0]]).astype(np.float32), ww / hh


# =============================================================================================
# card scene description
class Card:
    """stems: (pts, radii, sRGB hex); leaves: dicts (tex, base, dir, L, tint, fold, droop, roll, lift);
    size: (w, h) metres of the render window, x in [-w/2, w/2], y in [0, h] (stem base at (0, 0))."""

    def __init__(self, size, px, seed=1):
        self.size, self.px = size, px
        self.stems, self.leaves = [], []
        self.rng = random.Random(seed)
        self.opaque_bg = None                       # tiles: sRGB hex background (alpha 1)
        self.wrap = False                            # tiles: leaves wrap around the window

    def stem(self, pts, r0, r1, colour):
        n = len(pts)
        self.stems.append(([Vector(p) for p in pts], [r0 + (r1 - r0) * i / max(1, n - 1) for i in range(n)], colour))

    def leaf(self, tex, base, d, L, tint=1.0, fold=0.12, droop=0.1, roll=0.0, lift=0.0, hue=0.0):
        self.leaves.append(dict(tex=tex, base=Vector(base), dir=Vector(d).normalized(), L=L, tint=tint,
                                fold=fold, droop=droop, roll=roll, lift=lift, hue=hue))


def curve(start, d, length, bend=0.0, n=8, wob=0.0, rng=None, lift=0.0):
    """Polyline from start along d (XY) bending by `bend` radians over its length."""
    p = Vector(start)
    d = Vector((d[0], d[1], 0)).normalized()
    pts = [p.copy()]
    for i in range(n):
        a = bend / n + (rng.uniform(-wob, wob) if rng and wob else 0.0)
        d = Matrix.Rotation(a, 3, Z) @ d
        p = p + d * (length / n) + Z * (lift / n)
        pts.append(p.copy())
    return pts


def at(pts, f):
    """Point and XY tangent at fraction f of a polyline."""
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + (b - a).length)
    s = f * cum[-1]
    for i in range(len(pts) - 1):
        if cum[i + 1] >= s or i == len(pts) - 2:
            t = (s - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
            d = pts[i + 1] - pts[i]
            return pts[i].lerp(pts[i + 1], min(max(t, 0), 1)), Vector((d.x, d.y, 0)).normalized()
    return pts[-1], Vector((0, 1, 0))


def rot(v, deg):
    return Matrix.Rotation(math.radians(deg), 3, Z) @ Vector(v)


# =============================================================================================
# rendering
def _engine(scene):
    for name in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = name
            return
        except TypeError:
            pass


def _np_image(name, arr):
    """float RGBA array (row 0 = top) -> a float Blender image (linear)."""
    h, w = arr.shape[:2]
    im = bpy.data.images.get(name)
    if im is not None:
        bpy.data.images.remove(im)
    im = bpy.data.images.new(name, w, h, alpha=True, float_buffer=True)
    im.pixels.foreach_set(np.ascontiguousarray(arr[::-1], np.float32).ravel())
    im.pack()
    return im


def _mat(name, img, mode, opaque=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for nd in list(nt.nodes):
        nt.nodes.remove(nd)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    tint = nt.nodes.new("ShaderNodeAttribute")
    tint.attribute_name = "tint"
    if mode == "albedo":
        if img is not None:
            tx = nt.nodes.new("ShaderNodeTexImage")
            tx.image = img
            tx.interpolation = "Cubic"
            mul = nt.nodes.new("ShaderNodeMix")
            mul.data_type = "RGBA"
            mul.blend_type = "MULTIPLY"
            mul.inputs["Factor"].default_value = 1.0
            nt.links.new(tx.outputs["Color"], mul.inputs[6])
            nt.links.new(tint.outputs["Color"], mul.inputs[7])
            nt.links.new(mul.outputs[2], em.inputs["Color"])
        else:
            nt.links.new(tint.outputs["Color"], em.inputs["Color"])
    else:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        sg = nt.nodes.new("ShaderNodeMath")
        sg.operation = "SIGN"
        vm = nt.nodes.new("ShaderNodeVectorMath")
        vm.operation = "SCALE"
        enc = nt.nodes.new("ShaderNodeVectorMath")
        enc.operation = "MULTIPLY_ADD"
        enc.inputs[1].default_value = (0.5, 0.5, 0.5)
        enc.inputs[2].default_value = (0.5, 0.5, 0.5)
        nt.links.new(geo.outputs["Normal"], sep.inputs[0])
        nt.links.new(sep.outputs[2], sg.inputs[0])
        nt.links.new(geo.outputs["Normal"], vm.inputs[0])
        nt.links.new(sg.outputs[0], vm.inputs["Scale"])
        nt.links.new(vm.outputs[0], enc.inputs[0])
        nt.links.new(enc.outputs[0], em.inputs["Color"])
        if img is not None:
            tx = nt.nodes.new("ShaderNodeTexImage")
            tx.image = img
            tx.interpolation = "Cubic"
    if img is not None and not opaque:
        nt.links.new(tx.outputs["Alpha"], mix.inputs[0])
    else:
        mix.inputs[0].default_value = 1.0
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    try:
        m.surface_render_method = "DITHERED"
    except (AttributeError, TypeError):
        pass
    m.use_backface_culling = False
    return m


def _scene():
    sc = bpy.data.scenes.get("CardBake")
    if sc is None:
        sc = bpy.data.scenes.new("CardBake")
    for ob in list(sc.collection.objects):
        bpy.data.objects.remove(ob)
    _engine(sc)
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "OPEN_EXR"
    sc.render.image_settings.color_depth = "32"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.resolution_percentage = 100
    try:
        sc.view_settings.view_transform = "Standard"
    except TypeError:
        pass
    try:
        sc.eevee.taa_render_samples = 24
    except AttributeError:
        pass
    w = bpy.data.worlds.get("CardWorld") or bpy.data.worlds.new("CardWorld")
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Strength"].default_value = 0.0
    sc.world = w
    return sc


def _load_exr(path):
    im = bpy.data.images.load(path, check_existing=False)
    w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, 4)[::-1]
    bpy.data.images.remove(im)
    return a


def _tube_mesh(stems):
    co, faces, cols = [], [], []
    sides = 6
    for pts, rad, colour in stems:
        c = list(hexlin(colour)) + [1.0]
        n = len(pts)
        if n < 2:
            continue
        rings = []
        prev = None
        for i in range(n):
            t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
            if prev is None:
                a = Vector((1, 0, 0)) if abs(t.x) < 0.9 else Vector((0, 1, 0))
                prev = t.cross(a).normalized()
            nrm = (prev - t * prev.dot(t)).normalized()
            prev = nrm
            b = t.cross(nrm)
            ring = []
            for j in range(sides):
                ang = 2 * math.pi * j / sides
                co.append(tuple(pts[i] + (nrm * math.cos(ang) + b * math.sin(ang)) * rad[i]))
                cols.append(c)
                ring.append(len(co) - 1)
            rings.append(ring)
        for i in range(n - 1):
            for j in range(sides):
                faces.append((rings[i][j], rings[i][(j + 1) % sides], rings[i + 1][(j + 1) % sides], rings[i + 1][j]))
    return co, faces, cols


def _leaf_mesh(leaves, aspects, wrap=None):
    co, faces, uvs, cols = [], [], [], []
    nu, nv = 3, 4
    for lf in leaves:
        L = lf["L"]
        Wd = L * aspects[lf["tex"]]
        d = lf["dir"]
        a = d.cross(Z)
        a = a.normalized() if a.length > 1e-6 else Vector((1, 0, 0))
        a = Matrix.Rotation(lf["roll"], 3, d) @ a
        nrm = a.cross(d).normalized()
        if nrm.z < 0:
            nrm = -nrm
        tint = lf["tint"]
        if isinstance(tint, (int, float)):
            tint = (tint, tint, tint)
        c = [tint[0] * (1 + lf["hue"]), tint[1], tint[2] * (1 - lf["hue"]), 1.0]
        offsets = [Vector((0, 0, 0))]
        if wrap:
            offsets = [Vector((dx, dy, 0)) for dx in (-wrap[0], 0, wrap[0]) for dy in (-wrap[1], 0, wrap[1])]
        for off in offsets:
            base_i = len(co)
            for j in range(nv + 1):
                v = j / nv
                for i in range(nu + 1):
                    u = i / nu - 0.5
                    p = lf["base"] + off + d * (v * L) + a * (u * Wd) + nrm * (lf["fold"] * abs(u) * Wd) \
                        - Z * (lf["droop"] * v * v * L) + Z * lf["lift"]
                    co.append(tuple(p))
                    uvs.append((u + 0.5, v))
                    cols.append(c)
            for j in range(nv):
                for i in range(nu):
                    k = base_i + j * (nu + 1) + i
                    faces.append((k, k + 1, k + nu + 2, k + nu + 1))
    return co, faces, uvs, cols


def _object(sc, name, co, faces, cols, uvs=None, mats=()):
    me = bpy.data.meshes.new(name)
    me.from_pydata(co, [], faces)
    if uvs is not None:
        me.uv_layers.new(name="UVMap")
        loop_uv = [uvs[vi] for f in faces for vi in f]
        me.uv_layers[0].data.foreach_set("uv", np.array(loop_uv, np.float32).ravel())
    at = me.color_attributes.new("tint", "FLOAT_COLOR", "POINT")
    at.data.foreach_set("color", np.array(cols, np.float32).ravel())
    for m in mats:
        me.materials.append(m)
    me.update()
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    return ob


def render_card(card, textures):
    """card: Card; textures: {tex: (rgba array, aspect)} -> (rgba linear un-premultiplied, normal 0..1)."""
    sc = _scene()
    W, H = card.size
    pw, ph = card.px
    sc.render.resolution_x, sc.render.resolution_y = pw, ph
    cam = bpy.data.objects.new("CardCam", bpy.data.cameras.new("CardCam"))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = max(W, H)
    cam.data.clip_start = 0.01
    cam.data.clip_end = 50
    cam.location = (0, H / 2, 10)
    cam.rotation_euler = (0, 0, 0)
    sc.collection.objects.link(cam)
    sc.camera = cam
    used = sorted({lf["tex"] for lf in card.leaves})
    imgs = {t: _np_image(f"card_{t}", textures[t][0]) for t in used}
    aspects = {t: textures[t][1] for t in used}
    objs = []
    mats = {}
    for t in used:
        for mode in ("albedo", "normal"):
            mats[(t, mode)] = _mat(f"cm_{t}_{mode}", imgs[t], mode)
    for mode in ("albedo", "normal"):
        mats[("stem", mode)] = _mat(f"cm_stem_{mode}", None, mode)
    if card.stems:
        co, faces, cols = _tube_mesh(card.stems)
        ob = _object(sc, "stems", co, faces, cols, mats=[mats[("stem", "albedo")]])
        objs.append((ob, "stem"))
    wrap = (W, H) if card.wrap else None
    for t in used:
        lv = [lf for lf in card.leaves if lf["tex"] == t]
        co, faces, uvs, cols = _leaf_mesh(lv, aspects, wrap)
        ob = _object(sc, f"leaves_{t}", co, faces, cols, uvs, mats=[mats[(t, "albedo")]])
        objs.append((ob, t))
    tmp = os.path.join(PREP, "_card_tmp.exr")
    res = {}
    for mode in ("albedo", "normal"):
        for ob, t in objs:
            ob.data.materials[0] = mats[(t, mode)]
        sc.render.filepath = tmp
        bpy.ops.render.render(write_still=True, scene=sc.name)
        res[mode] = _load_exr(tmp)
    os.remove(tmp)
    for ob, _ in objs:
        me = ob.data
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(me)
    for m in mats.values():
        bpy.data.materials.remove(m)
    for im in imgs.values():
        bpy.data.images.remove(im)
    bpy.data.objects.remove(cam)
    alb, nor = res["albedo"], res["normal"]
    a = alb[..., 3]
    rgb = alb[..., :3] / np.maximum(a[..., None], 1e-4)
    n = nor[..., :3] / np.maximum(nor[..., 3:4], 1e-4)
    if card.opaque_bg:
        bg = hexlin(card.opaque_bg)
        rgb = alb[..., :3] + bg * (1 - a[..., None])
        n = nor[..., :3] + np.array([0.5, 0.5, 1.0], np.float32) * (1 - nor[..., 3:4])
        a = np.ones_like(a)
    return np.dstack([rgb, a]).astype(np.float32), n.astype(np.float32)


# =============================================================================================
# atlas packing
def dilate(rgb, mask, iters=12):
    rgb = rgb.copy()
    valid = mask.copy()
    for _ in range(iters):
        acc = np.zeros_like(rgb)
        cnt = np.zeros(mask.shape, np.float32)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            v = np.roll(np.roll(valid, dy, 0), dx, 1)
            acc += np.roll(np.roll(rgb, dy, 0), dx, 1) * v[..., None]
            cnt += v
        grow = (~valid) & (cnt > 0)
        if not grow.any():
            break
        rgb[grow] = acc[grow] / cnt[grow][:, None]
        valid |= grow
    if (~valid).any() and valid.any():
        rgb[~valid] = rgb[valid].mean(0)
    return rgb


def _hash(obj):
    return hashlib.sha1(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:10]


def pack(sizes, S, pad=6):
    """Shelf packing: sizes {name: (w, h)} -> {name: (x, y)} (pixels, y down) in an S x S atlas."""
    order = sorted(sizes, key=lambda k: (-sizes[k][1], -sizes[k][0]))
    pos, x, y, shelf = {}, pad, pad, 0
    for k in order:
        w, h = sizes[k]
        if x + w + pad > S:
            x, y = pad, y + shelf + pad
            shelf = 0
        if y + h + pad > S:
            raise RuntimeError(f"atlas overflow at {k}: {sizes}")
        pos[k] = (x, y)
        x += w + pad
        shelf = max(shelf, h)
    return pos


def _save_png(arr, path, colorspace, size=None):
    """arr row 0 = top, values already encoded (sRGB or data)."""
    h, w = arr.shape[:2]
    im = bpy.data.images.new(os.path.basename(path), w, h, alpha=True)
    im.colorspace_settings.name = colorspace
    im.pixels.foreach_set(np.ascontiguousarray(arr[::-1], np.float32).ravel())
    if size and size != w:
        im.scale(size, size)
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)


def build_atlas(atlas_id, spec, force=False):
    """spec: dict(size, nor_size, textures={tex: fn() -> (rgba, aspect)}, cards={name: fn(textures) -> Card},
    tiles=[names of opaque cards]). Returns the atlas info: png paths, rects, sizes, mean colours."""
    os.makedirs(CARD_CACHE, exist_ok=True)
    tag = "".join(p.title() for p in atlas_id.split("_"))
    path = os.path.join(PREP, f"T_Veg_{tag}_Leaf.png")
    npath = os.path.join(PREP, f"T_Veg_{tag}_Leaf_N.png")
    jpath = os.path.join(PREP, f"{atlas_id}.json")
    src = {k: inspect.getsource(f) for k, f in spec["cards"].items()}
    tsrc = {k: inspect.getsource(f[0]) + repr(f[1:]) for k, f in spec["textures"].items()}
    lib_v = [CARD_VERSION, _hash(open(os.path.abspath(__file__)).read())]
    key = _hash([lib_v, spec["size"], spec["nor_size"], src, tsrc, inspect.getsource(build_atlas)])
    if not force and os.path.exists(jpath) and os.path.exists(path):
        info = json.load(open(jpath))
        if info.get("hash") == key:
            return info
    textures = {}

    def tex(name):
        if name not in textures:
            fn = spec["textures"][name]
            textures[name] = fn[0](*fn[1:])
        return textures[name]
    # card resolution: the largest scale (in 5% steps) at which the (uncropped) cards still pack
    S = spec["size"]
    cards0 = {k: f() for k, f in spec["cards"].items()}
    scale = 1.0
    for sc_try in [1.8 - 0.05 * i for i in range(17)]:
        try:
            pack({k: (int(c.px[0] * sc_try * 0.82), int(c.px[1] * sc_try * 0.9)) for k, c in cards0.items()
                  if not c.opaque_bg}, S)
            scale = sc_try
            break
        except RuntimeError:
            continue
    renders = {}
    for name, fn in spec["cards"].items():
        card = fn()
        if not card.opaque_bg:
            card.px = (int(round(card.px[0] * scale)), int(round(card.px[1] * scale)))
        need = sorted({lf["tex"] for lf in card.leaves})
        ck = _hash([lib_v, src[name], {t: tsrc[t] for t in need}, card.px])
        cpath = os.path.join(CARD_CACHE, f"{atlas_id}__{name}_{ck}.npz")
        if os.path.exists(cpath) and not force:
            z = np.load(cpath)
            renders[name] = (z["rgba"].astype(np.float32), z["nor"].astype(np.float32), card)
            continue
        rgba, nor = render_card(card, {t: tex(t) for t in need})
        np.savez_compressed(cpath, rgba=rgba.astype(np.float16), nor=nor.astype(np.float16))
        renders[name] = (rgba, nor, card)
    # tiles: opaque, seamlessly repeating textures of their own (shell meshes, moss mats)
    tiles = {}
    for name in [k for k, v in renders.items() if v[2].opaque_bg]:
        rgba, nor, card = renders.pop(name)
        ttag = "".join(p.title() for p in name.split("_"))
        tp = os.path.join(PREP, f"T_Veg_{ttag}_Tile.png")
        tnp = os.path.join(PREP, f"T_Veg_{ttag}_Tile_N.png")
        _save_png(np.dstack([np.clip(lin_to_srgb(rgba[..., :3]), 0, 1), np.ones(rgba.shape[:2], np.float32)]), tp, "sRGB")
        _save_png(np.dstack([nor, np.ones(rgba.shape[:2], np.float32)]), tnp, "Non-Color")
        tiles[name] = dict(albedo=os.path.basename(tp), normal=os.path.basename(tnp), size_m=list(card.size),
                           px=[rgba.shape[1], rgba.shape[0]], mean_srgb=lin_hex(rgba[..., :3].mean((0, 1))))
    crops = {}
    for name, (rgba, nor, card) in list(renders.items()):
        a = rgba[..., 3] > 0.03
        h, w = a.shape
        ys, xs = np.where(a.any(1))[0], np.where(a.any(0))[0]
        m = 3
        x0, x1 = max(0, xs[0] - m), min(w, xs[-1] + 1 + m)
        y0 = max(0, ys[0] - m)
        y1 = h                                       # the stem base sits on the bottom edge: keep it
        renders[name] = (rgba[y0:y1, x0:x1], nor[y0:y1, x0:x1], card)
        mpp = card.size[0] / w
        crops[name] = dict(base_px=w / 2 - x0, size_m=[(x1 - x0) * mpp, (y1 - y0) * mpp])
    sizes = {k: (v[0].shape[1], v[0].shape[0]) for k, v in renders.items()}
    pos = pack(sizes, S)
    atlas = np.zeros((S, S, 4), np.float32)
    natlas = np.zeros((S, S, 3), np.float32)
    natlas[:] = (0.5, 0.5, 1.0)
    rects, meta = {}, {}
    pad = 6
    for name, (rgba, nor, card) in renders.items():
        x, y = pos[name]
        h, w = rgba.shape[:2]
        mask = rgba[..., 3] > 0.02
        # colour-dilate the card into its padding so mips and bilinear taps don't pick up black
        big = np.zeros((h + 2 * pad, w + 2 * pad, 3), np.float32)
        bmask = np.zeros((h + 2 * pad, w + 2 * pad), bool)
        big[pad:pad + h, pad:pad + w] = rgba[..., :3]
        bmask[pad:pad + h, pad:pad + w] = mask
        big = dilate(big, bmask, iters=pad + 16)
        y0, x0 = y - pad, x - pad
        atlas[y0:y0 + h + 2 * pad, x0:x0 + w + 2 * pad, :3] = big
        atlas[y:y + h, x:x + w, 3] = rgba[..., 3]
        nn = np.where(mask[..., None], nor, np.array([0.5, 0.5, 1.0], np.float32))
        natlas[y:y + h, x:x + w] = nn
        wgt = rgba[..., 3:4]
        mean = (rgba[..., :3] * wgt).sum((0, 1)) / max(float(wgt.sum()), 1e-3)
        g = S / 8.0
        rects[name] = [x / g, y / g, (x + w) / g, (y + h) / g, "b", (x + crops[name]["base_px"]) / g]
        meta[name] = dict(size_m=[round(v, 4) for v in crops[name]["size_m"]], px=[w, h], mean_srgb=lin_hex(mean),
                          coverage=round(float(rgba[..., 3].mean()), 3))
    # whole-atlas fill between cards: average colour (cheap), the dilated pads already cover the edges
    empty = atlas[..., :3].sum(2) == 0
    if empty.any():
        atlas[empty, :3] = atlas[~empty, :3].mean(0)
    rgb = lin_to_srgb(atlas[..., :3])
    _save_png(np.dstack([np.clip(rgb, 0, 1), atlas[..., 3]]), path, "sRGB")
    _save_png(np.dstack([natlas, np.ones((S, S), np.float32)]), npath, "Non-Color", spec["nor_size"])
    info = dict(hash=key, atlas=os.path.basename(path), normal=os.path.basename(npath), size=S,
                nor_size=spec["nor_size"], rects=rects, cards=meta, tiles=tiles)
    with open(jpath + ".part", "w") as fh:
        json.dump(info, fh, indent=1)
    os.replace(jpath + ".part", jpath)
    return info
