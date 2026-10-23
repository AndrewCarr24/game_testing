"""Textures for the gas station (town2_gas.py), all made here so the asset rebuilds from scratch:

- Poly Haven scans (CC0; downloaded once into build/town/gas/ph/), tiled to our tile size and
  tinted to the station's palette: brushed (broom-finish) concrete for the forecourt, clean
  asphalt for the drive lanes, rustic ledgestone for the store's base and the canopy columns,
  white oak veneer for the coffee bar and the cash wrap, polished terrazzo for the store floor
  (laid as 60 cm tiles with our own grout grid);
- painted in numpy: the paint palette (every flat-coloured part samples one swatch), the
  packaging atlas (chip bags, candy, boxes, pouches, jugs, cigarette packs: colour and shape, no
  words), the cooler shelf cards (rows of bottles and cans as seen through the glass), the
  emissive sign atlas (LED panels, price digits, pump screens, menu boards with pictures, the
  exit and restroom pictograms, the lottery and the security monitor) and the lay-in ceiling.

Everything is written to build/town/gas/tex/T_Town2_Gas_*.png and loaded as images of that name
(the glTF exporter writes them as assets/models/textures/T_Town2_Gas_*.webp).
"""
import json
import math
import os
import struct
import urllib.request
import zlib

import numpy as np

PROJECT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(PROJECT, "build", "town", "gas", "tex")
PH = os.path.join(PROJECT, "build", "town", "gas", "ph")
UA = {"User-Agent": "game_testing-town2-gas/1.0 (CC0 assets)"}


# ------------------------------------------------------------------ io
def to_lin(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def write_png(path, srgb):
    """srgb: (h, w, 3|4) floats 0..1, rows top-down."""
    img8 = np.round(np.clip(srgb, 0, 1) * 255).astype(np.uint8)
    h, w, c = img8.shape
    raw = b"".join(b"\x00" + img8[y].tobytes() for y in range(h))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6 if c == 4 else 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
    return path


def fetch(ph_id, res="2k"):
    folder = os.path.join(PH, ph_id)
    p = os.path.join(folder, f"{ph_id}_diff_{res}.jpg")
    if os.path.exists(p) and os.path.getsize(p) > 1000:
        return p
    with urllib.request.urlopen(urllib.request.Request(f"https://api.polyhaven.com/files/{ph_id}", headers=UA), timeout=60) as r:
        files = json.loads(r.read())
    url = files["Diffuse"][res]["jpg"]["url"]
    os.makedirs(folder, exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
        data = r.read()
    with open(p + ".part", "wb") as fh:
        fh.write(data)
    os.replace(p + ".part", p)
    return p


def load_px(path):
    """An image file's sRGB pixels (h, w, 3), rows top-down (through Blender's loader)."""
    import bpy
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, -1)[::-1, :, :3]
    bpy.data.images.remove(img)
    return px


def resize(px, w, h):
    """Area-average down / bilinear up."""
    H0, W0, _ = px.shape
    ys = (np.arange(h) + 0.5) * H0 / h - 0.5
    xs = (np.arange(w) + 0.5) * W0 / w - 0.5
    if H0 >= 2 * h and W0 >= 2 * w:
        # box filter by integer factors first
        fy, fx = H0 // h, W0 // w
        px = px[:h * fy, :w * fx].reshape(h, fy, w, fx, 3).mean(axis=(1, 3))
        return px
    y0 = np.clip(np.floor(ys).astype(int), 0, H0 - 1)
    x0 = np.clip(np.floor(xs).astype(int), 0, W0 - 1)
    y1, x1 = np.clip(y0 + 1, 0, H0 - 1), np.clip(x0 + 1, 0, W0 - 1)
    ty, tx = (ys - y0)[:, None, None], (xs - x0)[None, :, None]
    a = px[y0][:, x0] * (1 - tx) + px[y0][:, x1] * tx
    b = px[y1][:, x0] * (1 - tx) + px[y1][:, x1] * tx
    return a * (1 - ty) + b * ty


def scan(name, ph_id, size, mean_srgb=None, contrast=1.0, post=None):
    """A Poly Haven scan as one tile, colour-matched (linear per-channel gain) to mean_srgb, its
    detail scaled by contrast; post(lin) -> lin for joints / grout."""
    path = os.path.join(OUT, name + ".png")
    px = load_px(fetch(ph_id))
    px = resize(px, size, size)
    lin = to_lin(px)
    if mean_srgb is not None:
        m = lin.reshape(-1, 3).mean(axis=0)
        tgt = to_lin(np.array(mean_srgb, np.float32) / 255.0)
        lin = lin * (tgt / np.maximum(m, 1e-6))
        if contrast != 1.0:
            mu = lin.mean(axis=(0, 1), keepdims=True)
            lin = mu + (lin - mu) * contrast
    if post:
        lin = post(lin)
    write_png(path, to_srgb(lin))
    return path


# ------------------------------------------------------------------ drawing
class Canvas:
    """A linear-RGB canvas drawn with anti-aliased signed-distance shapes (pixel coords, y down)."""

    def __init__(self, w, h, col=(0, 0, 0)):
        self.w, self.h = w, h
        self.px = np.zeros((h, w, 3), np.float32) + to_lin(np.array(col, np.float32))
        self.Y, self.X = np.mgrid[0:h, 0:w].astype(np.float32) + 0.5

    def _blend(self, cov, col, alpha=1.0):
        a = (np.clip(cov, 0, 1) * alpha)[..., None]
        if callable(col):
            c = col(self.X, self.Y)
        else:
            c = to_lin(np.array(col, np.float32))
        self.px = self.px * (1 - a) + c * a

    def rect(self, x0, y0, x1, y1, col, r=0.0, alpha=1.0, feather=0.7):
        cx, cy, hx, hy = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
        dx = np.abs(self.X - cx) - hx + r
        dy = np.abs(self.Y - cy) - hy + r
        d = np.hypot(np.maximum(dx, 0), np.maximum(dy, 0)) + np.minimum(np.maximum(dx, dy), 0) - r
        self._blend(0.5 - d / feather, col, alpha)
        return d

    def ellipse(self, cx, cy, rx, ry, col, alpha=1.0, feather=0.7):
        d = (np.hypot((self.X - cx) / rx, (self.Y - cy) / ry) - 1) * min(rx, ry)
        self._blend(0.5 - d / feather, col, alpha)

    def ring(self, cx, cy, r, w, col, alpha=1.0):
        d = np.abs(np.hypot(self.X - cx, self.Y - cy) - r) - w / 2
        self._blend(0.5 - d / 0.7, col, alpha)

    def poly(self, pts, col, alpha=1.0):
        """A filled polygon (even-odd), AA by 4x4 supersampling of the edge band."""
        P = np.array(pts, np.float32)
        x0, y0 = np.floor(P.min(axis=0)).astype(int) - 1
        x1, y1 = np.ceil(P.max(axis=0)).astype(int) + 1
        x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, self.w), min(y1, self.h)
        if x1 <= x0 or y1 <= y0:
            return
        cov = np.zeros((y1 - y0, x1 - x0), np.float32)
        for sy in range(4):
            for sx in range(4):
                X = self.X[y0:y1, x0:x1] - 0.5 + (sx + 0.5) / 4
                Y = self.Y[y0:y1, x0:x1] - 0.5 + (sy + 0.5) / 4
                inside = np.zeros_like(X, bool)
                n = len(P)
                for i in range(n):
                    ax, ay = P[i]
                    bx, by = P[(i + 1) % n]
                    cond = ((ay > Y) != (by > Y)) & (X < (bx - ax) * (Y - ay) / (by - ay + 1e-9) + ax)
                    inside ^= cond
                cov += inside
        cov /= 16
        full = np.zeros((self.h, self.w), np.float32)
        full[y0:y1, x0:x1] = cov
        self._blend(full, col, alpha)

    def vgrad(self, x0, y0, x1, y1, c0, c1, alpha=1.0, r=0.0):
        """A vertical gradient (colours in 0..255 sRGB)."""
        c0, c1 = to_lin(np.array(c0, np.float32) / 255), to_lin(np.array(c1, np.float32) / 255)
        t = np.clip((self.Y - y0) / max(y1 - y0, 1e-6), 0, 1)[..., None]
        grad = c0 * (1 - t) + c1 * t
        self.rect(x0, y0, x1, y1, lambda X, Y: grad, r=r, alpha=alpha)

    def shade(self, x0, y0, x1, y1, k=0.35, horizontal=True, r=0.0, gloss=0.0):
        """A cylindrical / pillow shading over a region (multiplies): darker at the edges,
        a soft highlight off-centre."""
        if horizontal:
            t = np.clip((self.X - x0) / max(x1 - x0, 1e-6), 0, 1)
        else:
            t = np.clip((self.Y - y0) / max(y1 - y0, 1e-6), 0, 1)
        s = 1 - k * (2 * t - 1) ** 2
        hl = gloss * np.exp(-((t - 0.3) / 0.07) ** 2)
        inside = (self.X >= x0) & (self.X < x1) & (self.Y >= y0) & (self.Y < y1)
        m = np.where(inside, s, 1.0)[..., None]
        self.px = self.px * m + np.where(inside, hl, 0.0)[..., None]

    def noise(self, amt=0.03, seed=0):
        rng = np.random.default_rng(seed)
        self.px = self.px * (1 + (rng.random((self.h, self.w, 1)) - 0.5) * 2 * amt)

    def srgb(self):
        return to_srgb(self.px)


# seven-segment digits (for price signs and screens): segments a b c d e f g
SEG = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc", "7": "abc",
       "8": "abcdefg", "9": "abcdfg", "-": "g", " ": ""}


def digits(cv, s, x, y, h, col, w=None, gap=None, off=None):
    """Seven-segment digits, top-left at (x, y), height h."""
    w = w or h * 0.55
    t = h * 0.13
    gap = gap or h * 0.25
    for ch in s:
        if ch == ".":
            cv.rect(x - gap * 0.6, y + h - t, x - gap * 0.6 + t, y + h, col, r=t * 0.3)
            continue
        segs = SEG.get(ch, "")
        S = dict(a=(x + t * 0.6, y, x + w - t * 0.6, y + t), d=(x + t * 0.6, y + h - t, x + w - t * 0.6, y + h),
                 g=(x + t * 0.6, y + h / 2 - t / 2, x + w - t * 0.6, y + h / 2 + t / 2),
                 f=(x, y + t * 0.6, x + t, y + h / 2 - t * 0.4), b=(x + w - t, y + t * 0.6, x + w, y + h / 2 - t * 0.4),
                 e=(x, y + h / 2 + t * 0.4, x + t, y + h - t * 0.6), c=(x + w - t, y + h / 2 + t * 0.4, x + w, y + h - t * 0.6))
        for k, r_ in S.items():
            if off is not None and k not in segs:
                cv.rect(*r_, off, r=t * 0.3)
            if k in segs:
                cv.rect(*r_, col, r=t * 0.3)
        x += w + gap


# ------------------------------------------------------------------ atlases
class Atlas:
    """Named cells in a square atlas: name -> (u0, v0, u1, v1) in UV (v up)."""

    def __init__(self, name, w, h):
        self.name, self.w, self.h = name, w, h
        self.cells = {}

    def add(self, key, x0, y0, x1, y1, inset=2.0):
        # pixel rect (y down) -> uv rect (v up), inset to keep mip bleeding inside
        self.cells[key] = ((x0 + inset) / self.w, 1 - (y1 - inset) / self.h, (x1 - inset) / self.w, 1 - (y0 + inset) / self.h)

    def save(self, cv, out_w=None):
        """Writes the atlas, box-filtered down to out_w wide (drawn large, shipped small)."""
        px = cv.px
        if out_w and out_w < cv.w:
            f = cv.w // out_w
            h, w = cv.h // f, cv.w // f
            px = px[:h * f, :w * f].reshape(h, f, w, f, 3).mean(axis=(1, 3))
        path = write_png(os.path.join(OUT, self.name + ".png"), to_srgb(px))
        json.dump(self.cells, open(os.path.join(OUT, self.name + ".json"), "w"))
        return path


PALETTE = {
    # name: (sRGB 0..255, roughness)
    "white": ((236, 236, 232), 0.35), "offwhite": ((222, 218, 208), 0.6), "black": ((24, 25, 27), 0.45),
    "charcoal": ((52, 54, 56), 0.5), "graphite": ((78, 80, 82), 0.45), "grey": ((128, 130, 130), 0.5),
    "lightgrey": ((182, 184, 182), 0.5), "steel": ((200, 202, 204), 0.32), "darksteel": ((120, 122, 124), 0.38),
    "brushed": ((210, 212, 214), 0.42),
    "rubber": ((20, 20, 21), 0.8), "hose": ((30, 31, 33), 0.55), "green": ((38, 84, 64), 0.4),
    "green_dark": ((26, 56, 44), 0.45), "sage": ((120, 140, 118), 0.6), "red": ((176, 30, 28), 0.4),
    "yellow": ((228, 182, 28), 0.45), "safety": ((236, 196, 30), 0.5), "blue": ((34, 78, 148), 0.4),
    "propane_white": ((230, 230, 226), 0.4), "copper": ((150, 88, 50), 0.35), "cardboard": ((176, 138, 96), 0.85),
    "kraft": ((150, 116, 80), 0.85), "wood_dark": ((70, 50, 36), 0.6), "mulch": ((62, 42, 30), 0.95),
    "soil": ((58, 46, 36), 1.0), "leaf": ((52, 74, 38), 0.8), "leaf_light": ((86, 110, 52), 0.8),
    "grout": ((120, 116, 110), 0.9), "cream": ((236, 226, 202), 0.5), "brown": ((96, 62, 40), 0.5),
    "coffee": ((46, 28, 18), 0.3), "orange": ((222, 110, 30), 0.45), "tan": ((196, 170, 132), 0.6),
    "van": ((88, 90, 96), 0.3), "stain": ((126, 122, 116), 0.7), "van_trim": ((18, 18, 20), 0.6), "tyre": ((22, 22, 23), 0.85),
    "chrome": ((230, 232, 234), 0.12), "glass_dark": ((14, 16, 18), 0.1), "porcelain": ((242, 242, 240), 0.15),
    "tile_wall": ((206, 204, 198), 0.3), "partition": ((92, 96, 100), 0.35), "concrete_grey": ((150, 148, 142), 0.9),
    "asphalt_patch": ((70, 70, 72), 0.9), "oil": ((22, 22, 24), 0.6), "paint_white_road": ((222, 222, 214), 0.7),
    "paint_yellow_road": ((214, 170, 40), 0.7), "mat": ((40, 42, 44), 0.95), "foam": ((210, 206, 196), 0.8),
    "lid_black": ((30, 30, 32), 0.4), "cup_white": ((240, 238, 232), 0.5), "sausage": ((150, 72, 44), 0.35),
    "bun": ((206, 156, 96), 0.7), "mustard": ((214, 170, 40), 0.5),
}


METALS = ("steel", "chrome", "darksteel", "brushed")


def palette():
    """8 x 8 swatches of 32 px (256 x 256): name -> uv of its centre; plus a roughness map."""
    names = list(PALETTE)
    n = 8
    cv = Canvas(256, 256)
    rough = np.zeros((256, 256, 3), np.float32)
    uv = {}
    for i, k in enumerate(names):
        cx, cy = i % n, i // n
        col, r = PALETTE[k]
        cv.px[cy * 32:(cy + 1) * 32, cx * 32:(cx + 1) * 32] = to_lin(np.array(col, np.float32) / 255)
        # glTF metallicRoughness: G roughness, B metalness (stainless, chrome: true metals, lit
        # by the reflection panorama alone)
        rough[cy * 32:(cy + 1) * 32, cx * 32:(cx + 1) * 32] = (0.0, r, 1.0 if k in METALS else 0.0)
        uv[k] = ((cx + 0.5) / n, 1 - (cy + 0.5) / n)
    write_png(os.path.join(OUT, "T_Town2_Gas_Paint.png"), cv.srgb())
    write_png(os.path.join(OUT, "T_Town2_Gas_PaintRough.png"), rough)
    return uv


def _col(c):
    return tuple(np.array(c) / 255.0)


def mural(cv, x, y, w, h, rng):
    """The Blue Ridge from an overlook, as a wall mural: layered ridgelines fading into haze
    under a late sky, a stand of pines dark in the foreground."""
    cv.vgrad(x, y, x + w, y + h, (236, 196, 150), (150, 178, 206))
    X = np.arange(w, dtype=np.float32)
    layers = [((120, 150, 186), 0.35, 0.55), ((96, 124, 164), 0.45, 0.6), ((72, 96, 136), 0.55, 0.7), ((52, 70, 104), 0.66, 0.8), ((34, 46, 64), 0.8, 0.9)]
    for k, (col, base_, amp) in enumerate(layers):
        ph = rng.random(4) * 6.28
        ridge = base_ * h - amp * h * 0.22 * (0.6 * np.sin(X / w * 6.28 * (1.2 + k * 0.4) + ph[0]) + 0.3 * np.sin(X / w * 6.28 * (3.1 + k) + ph[1])
                                               + 0.15 * np.sin(X / w * 6.28 * (7.3 + 2 * k) + ph[2]))
        Ys = np.arange(h, dtype=np.float32)[:, None]
        cov = np.clip(Ys - ridge[None, :] + 0.5, 0, 1)
        c = to_lin(np.array(col, np.float32) / 255)
        cv.px[y:y + h, x:x + w] = cv.px[y:y + h, x:x + w] * (1 - cov[..., None]) + c * cov[..., None]
    for k in range(26):
        px_ = x + rng.random() * w
        hh = h * (0.2 + 0.25 * rng.random())
        cv.poly([(px_ - hh * 0.18, y + h), (px_, y + h - hh), (px_ + hh * 0.18, y + h)], (0.05, 0.07, 0.06))


def signs(feeds=None):
    """The emissive atlas (1024 x 1024): LED panels, the price sign, pump screens, menu boards,
    pictograms, the lottery, the monitor. feeds: an (h, w, 3) linear image (the security monitor's
    four camera views) pasted into the monitor cell."""
    A = Atlas("T_Town2_Gas_Signs", 1024, 1024)
    cv = Canvas(1024, 1024, (0, 0, 0))
    # LED whites (0..256 x 0..64): neutral, warm, cool, and the dim "back of a sign"
    for i, (k, c) in enumerate([("led", (255, 255, 252)), ("led_warm", (255, 226, 190)), ("led_cool", (236, 244, 255)), ("dim", (60, 60, 60))]):
        cv.rect(i * 64, 0, i * 64 + 64, 64, _col(c))
        A.add(k, i * 64, 0, i * 64 + 64, 64, inset=8)
    # LED flat-lens canopy fixture (256..384 x 0..128): a square lens, brighter centre, dark rim
    x, y = 256, 0
    cv.rect(x, y, x + 128, y + 128, (0.25, 0.25, 0.26))
    cv.rect(x + 10, y + 10, x + 118, y + 118, (0.92, 0.94, 0.96), r=6)
    cv.ellipse(x + 64, y + 64, 44, 44, (1, 1, 1), alpha=0.7)
    A.add("canopy_led", x, y, x + 128, y + 128)
    # 2 x 4 troffer (384..512 x 0..256 rotated as 128 x 256): a lens with the edge-lit frame
    x, y = 384, 0
    cv.rect(x, y, x + 128, y + 256, (0.55, 0.55, 0.56))
    cv.rect(x + 8, y + 8, x + 120, y + 248, (0.96, 0.97, 0.98), r=3)
    A.add("troffer", x, y, x + 128, y + 256)
    # price sign (512..1024 x 0..256): four lines of red/green seven-segment prices with grade tabs
    x, y = 512, 0
    cv.rect(x, y, x + 512, y + 256, (0.02, 0.02, 0.025))
    prices = ["3.29", "3.69", "3.99", "3.89"]
    tabs = [(40, 150, 70), (200, 40, 40), (40, 80, 170), (230, 190, 30)]
    for k, (pr, tb) in enumerate(zip(prices, tabs)):
        yy = y + 8 + k * 62
        cv.rect(x + 8, yy, x + 120, yy + 54, _col(tb), r=4)
        cv.rect(x + 20, yy + 18, x + 108, yy + 36, (0.98, 0.98, 0.95), r=3)        # (a white bar: no words)
        col = (1.0, 0.12, 0.06) if k != 3 else (0.2, 1.0, 0.3)
        digits(cv, pr, x + 150, yy + 4, 46, col, off=(0.08, 0.02, 0.02))
        digits(cv, "9", x + 430, yy + 4, 22, col)
    A.add("price", x, y, x + 512, y + 256)
    # pump screen (0..256 x 64..192): a lit LCD, total / gallons / price per gallon
    x, y = 0, 64
    cv.rect(x, y, x + 256, y + 128, (0.05, 0.07, 0.1))
    cv.rect(x + 8, y + 8, x + 248, y + 120, (0.55, 0.72, 0.8), r=3)
    digits(cv, "  0.00", x + 40, y + 16, 34, (0.05, 0.08, 0.1))
    digits(cv, "  0.000", x + 40, y + 62, 22, (0.05, 0.08, 0.1))
    digits(cv, "3.299", x + 90, y + 94, 16, (0.05, 0.08, 0.1))
    A.add("pump_screen", x, y, x + 256, y + 128)
    # pump media screen / card reader (256..384 x 128..256): a little video panel (a landscape)
    x, y = 256, 128
    cv.vgrad(x, y, x + 128, y + 128, (120, 170, 220), (240, 200, 150))
    cv.poly([(x, y + 90), (x + 40, y + 60), (x + 70, y + 80), (x + 110, y + 50), (x + 128, y + 70), (x + 128, y + 128), (x, y + 128)], (0.12, 0.25, 0.18))
    A.add("pump_media", x, y, x + 128, y + 128)
    # grade buttons (0..256 x 192..256): four lit coloured buttons
    x, y = 0, 192
    cv.rect(x, y, x + 256, y + 64, (0.04, 0.04, 0.04))
    for k, tb in enumerate(tabs):
        cv.rect(x + 8 + k * 62, y + 10, x + 58 + k * 62, y + 54, _col(tb), r=6)
        cv.rect(x + 20 + k * 62, y + 26, x + 46 + k * 62, y + 38, (1, 1, 1), r=3)
    A.add("grades", x, y, x + 256, y + 64)
    # brand-neutral canopy pictogram (0..256 x 256..512): a white fuel pump on the station green
    x, y = 0, 256
    cv.rect(x, y, x + 256, y + 256, _col((38, 110, 80)))
    cv.rect(x + 70, y + 50, x + 160, y + 210, (1, 1, 1), r=10)
    cv.rect(x + 86, y + 70, x + 144, y + 110, _col((38, 110, 80)), r=4)
    cv.rect(x + 160, y + 90, x + 186, y + 100, (1, 1, 1))
    cv.rect(x + 178, y + 90, x + 188, y + 180, (1, 1, 1), r=4)
    cv.rect(x + 54, y + 206, x + 176, y + 222, (1, 1, 1), r=3)
    A.add("logo", x, y, x + 256, y + 256)
    # the fascia's accent band (256..512 x 256..288): green light
    cv.rect(256, 256, 512, 288, _col((46, 160, 108)))
    A.add("band", 256, 256, 512, 288, inset=6)
    # exit (256..384 x 288..352): the green running man; restrooms (384..512 x 288..416)
    x, y = 256, 288
    cv.rect(x, y, x + 128, y + 64, _col((20, 170, 80)))
    cv.ellipse(x + 50, y + 14, 6, 6, (1, 1, 1))
    cv.poly([(x + 44, y + 22), (x + 56, y + 22), (x + 62, y + 40), (x + 72, y + 54), (x + 64, y + 56), (x + 54, y + 44), (x + 44, y + 56), (x + 36, y + 52), (x + 46, y + 38)], (1, 1, 1))
    cv.rect(x + 84, y + 14, x + 118, y + 54, (1, 1, 1))
    cv.rect(x + 88, y + 18, x + 114, y + 50, _col((20, 170, 80)))
    A.add("exit", x, y, x + 128, y + 64)
    x, y = 384, 288
    cv.rect(x, y, x + 128, y + 128, _col((30, 60, 120)))
    for k, cx in enumerate((x + 36, x + 92)):
        cv.ellipse(cx, y + 28, 9, 9, (1, 1, 1))
        if k == 0:
            cv.rect(cx - 12, y + 42, cx + 12, y + 80, (1, 1, 1), r=3)
            cv.rect(cx - 10, y + 78, cx - 2, y + 108, (1, 1, 1), r=2)
            cv.rect(cx + 2, y + 78, cx + 10, y + 108, (1, 1, 1), r=2)
        else:
            cv.poly([(cx - 6, y + 42), (cx + 6, y + 42), (cx + 18, y + 86), (cx - 18, y + 86)], (1, 1, 1))
            cv.rect(cx - 8, y + 84, cx - 2, y + 108, (1, 1, 1), r=2)
            cv.rect(cx + 2, y + 84, cx + 8, y + 108, (1, 1, 1), r=2)
    cv.rect(x + 63, y + 16, x + 65, y + 112, (1, 1, 1))
    A.add("restroom", x, y, x + 128, y + 128)
    # menu boards (0..768 x 512..704: three 256 x 192 panels): coffee, hot food, cold drinks
    for k in range(3):
        x, y = k * 256, 512
        cv.rect(x, y, x + 256, y + 192, (0.06, 0.06, 0.06))
        cv.vgrad(x + 6, y + 6, x + 250, y + 120, (40, 34, 30), (16, 14, 12))
        if k == 0:     # a steaming cup
            cv.rect(x + 90, y + 40, x + 166, y + 108, (0.95, 0.95, 0.93), r=6)
            cv.rect(x + 96, y + 60, x + 160, y + 82, _col((38, 110, 80)), r=3)
            cv.rect(x + 86, y + 32, x + 170, y + 44, (0.15, 0.15, 0.15), r=3)
            for j in range(3):
                cv.rect(x + 104 + j * 20, y + 12, x + 108 + j * 20, y + 28, (0.7, 0.7, 0.7), r=2)
        elif k == 1:   # hot dog + breakfast sandwich
            cv.rect(x + 40, y + 60, x + 150, y + 92, _col((206, 156, 96)), r=14)
            cv.rect(x + 34, y + 66, x + 156, y + 80, _col((170, 80, 50)), r=7)
            cv.poly([(x + 44, y + 70), (x + 60, y + 64), (x + 80, y + 72), (x + 100, y + 64), (x + 120, y + 72), (x + 140, y + 66)], _col((214, 170, 40)))
            cv.ellipse(x + 200, y + 72, 36, 22, _col((210, 160, 90)))
            cv.rect(x + 166, y + 68, x + 234, y + 76, _col((240, 200, 60)))
        else:          # a fountain cup with ice and a straw
            cv.poly([(x + 96, y + 30), (x + 160, y + 30), (x + 152, y + 112), (x + 104, y + 112)], _col((200, 40, 40)))
            cv.rect(x + 92, y + 24, x + 164, y + 32, (0.9, 0.9, 0.9), r=3)
            cv.rect(x + 132, y + 6, x + 138, y + 30, (0.95, 0.95, 0.95), r=2)
        for j in range(3):     # price rows (digits only)
            digits(cv, ["1.99", "2.49", "2.99"][j], x + 150, y + 128 + j * 20, 14, (0.95, 0.95, 0.9))
            cv.rect(x + 20, y + 132 + j * 20, x + 120, y + 138 + j * 20, (0.45, 0.45, 0.42), r=2)
        A.add(f"menu{k}", x, y, x + 256, y + 192)
    # lottery jackpot sign (768..1024 x 512..640): two jackpots
    x, y = 768, 512
    cv.rect(x, y, x + 256, y + 128, (0.03, 0.03, 0.06))
    cv.ellipse(x + 26, y + 32, 16, 16, _col((230, 40, 40)))
    cv.ellipse(x + 26, y + 92, 16, 16, _col((250, 200, 30)))
    digits(cv, "412", x + 60, y + 12, 40, (1.0, 0.85, 0.2))
    digits(cv, "86", x + 60, y + 72, 40, (1.0, 0.85, 0.2))
    A.add("lotto", x, y, x + 256, y + 128)
    # lottery terminal screen + ATM screen (768..1024 x 640..704)
    cv.vgrad(768, 640, 896, 704, (30, 90, 180), (10, 40, 100))
    cv.rect(780, 652, 884, 664, (0.9, 0.9, 0.9), r=2)
    A.add("lotto_screen", 768, 640, 896, 704)
    cv.vgrad(896, 640, 1024, 704, (40, 120, 90), (10, 50, 40))
    cv.rect(910, 656, 1010, 668, (0.9, 0.95, 0.9), r=2)
    A.add("atm", 896, 640, 1024, 704)
    # register / POS screens (768..1024 x 704..768)
    x, y = 768, 704
    cv.rect(x, y, x + 128, y + 64, (0.85, 0.88, 0.9))
    for j in range(3):
        for k in range(4):
            cv.rect(x + 6 + k * 30, y + 6 + j * 19, x + 32 + k * 30, y + 22 + j * 19, _col([(40, 110, 200), (40, 160, 90), (220, 140, 30)][j]), r=2)
    A.add("pos", x, y, x + 128, y + 64)
    # scratch-ticket case backlight (896..1024 x 704..768): a strip of bright tickets
    x, y = 896, 704
    tc = [(230, 40, 120), (40, 180, 220), (250, 200, 30), (60, 200, 90), (240, 90, 30), (150, 60, 200), (230, 230, 230), (40, 60, 200)]
    for k in range(8):
        cv.rect(x + k * 16, y, x + k * 16 + 15, y + 64, _col(tc[k]))
        cv.ellipse(x + k * 16 + 8, y + 20, 5, 5, (1, 0.95, 0.5))
    A.add("tickets", x, y, x + 128, y + 64)
    # the cooler's LED door strip (512..768 x 256..288) and the ice merchandiser's front (512..768 x 288..416)
    cv.rect(512, 256, 768, 288, (1, 1, 1))
    A.add("strip", 512, 256, 768, 288, inset=6)
    x, y = 512, 288
    cv.vgrad(x, y, x + 256, y + 128, (60, 150, 220), (20, 80, 170))
    # a snowflake pictogram
    for k in range(3):
        a = k * math.pi / 3
        cx, cy = x + 128, y + 64
        dx, dy = math.cos(a) * 46, math.sin(a) * 46
        cv.poly([(cx - dx - math.sin(a) * 4, cy - dy + math.cos(a) * 4), (cx + dx - math.sin(a) * 4, cy + dy + math.cos(a) * 4),
                 (cx + dx + math.sin(a) * 4, cy + dy - math.cos(a) * 4), (cx - dx + math.sin(a) * 4, cy - dy - math.cos(a) * 4)], (1, 1, 1))
    A.add("ice", x, y, x + 256, y + 128)
    # propane: a white flame pictogram on blue (768..896 x 256..384)
    x, y = 768, 256
    cv.rect(x, y, x + 128, y + 128, _col((30, 70, 150)))
    cv.poly([(x + 64, y + 14), (x + 92, y + 60), (x + 96, y + 90), (x + 64, y + 116), (x + 32, y + 90), (x + 38, y + 56), (x + 50, y + 70)], (1, 1, 1))
    cv.poly([(x + 64, y + 66), (x + 76, y + 88), (x + 64, y + 104), (x + 52, y + 88)], _col((30, 70, 150)))
    A.add("propane", x, y, x + 128, y + 128)
    # air pictogram (896..1024 x 256..384): a tyre
    x, y = 896, 256
    cv.rect(x, y, x + 128, y + 128, _col((38, 110, 80)))
    cv.ring(x + 64, y + 64, 36, 16, (1, 1, 1))
    cv.ring(x + 64, y + 64, 14, 6, (1, 1, 1))
    A.add("air", x, y, x + 128, y + 128)
    # the security monitor (0..512 x 768..1024): four camera feeds (rendered by make.py) or bars
    x, y = 0, 768
    cv.rect(x, y, x + 512, y + 256, (0.02, 0.02, 0.02))
    if feeds is not None:
        fh, fw, _ = feeds.shape
        cv.px[y:y + min(fh, 256), x:x + min(fw, 512)] = feeds[:256, :512]
    else:
        for k in range(4):
            cv.vgrad(x + (k % 2) * 256 + 2, y + (k // 2) * 128 + 2, x + (k % 2) * 256 + 254, y + (k // 2) * 128 + 126, (60, 70, 70), (20, 24, 24))
    A.add("cctv", x, y, x + 512, y + 256)
    # the beer cave / cooler header light box (512..1024 x 768..832): plain white with a frosty gradient
    cv.vgrad(512, 768, 1024, 832, (220, 240, 255), (150, 200, 240))
    A.add("frost", 512, 768, 1024, 832, inset=4)
    # OPEN-hours style plain lit panels: the window's coffee-cup neon (512..640 x 832..960)
    x, y = 512, 832
    cv.rect(x, y, x + 128, y + 128, (0, 0, 0))
    cv.ring(x + 56, y + 70, 30, 5, _col((255, 120, 60)))
    cv.ring(x + 96, y + 70, 12, 5, _col((255, 120, 60)))
    for j in range(3):
        cv.rect(x + 40 + j * 14, y + 18, x + 44 + j * 14, y + 34, _col((255, 220, 120)), r=2)
    A.add("neon_cup", x, y, x + 128, y + 128)
    A.save(cv, 512)
    return A


def ceiling():
    """A 2 x 2 ft (0.61 m) lay-in ceiling: one tile per texture (tile = 0.61 m), its white grid
    tee on two edges, a fine fissured face."""
    n = 128
    rng = np.random.default_rng(11)
    cv = Canvas(n, n, _col((226, 225, 220)))
    fine = rng.random((n, n, 1)).astype(np.float32)
    cv.px *= 0.94 + 0.08 * fine
    for _ in range(90):
        x, y = rng.random(2) * n
        cv.ellipse(x, y, 1.2, 0.8, _col((180, 178, 172)), alpha=0.5)
    cv.rect(0, 0, n, 3, _col((246, 246, 244)))
    cv.rect(0, 0, 3, n, _col((246, 246, 244)))
    cv.rect(0, 3, n, 4, _col((170, 170, 168)), alpha=0.6)
    cv.rect(3, 0, 4, n, _col((170, 170, 168)), alpha=0.6)
    return write_png(os.path.join(OUT, "T_Town2_Gas_Ceiling.png"), cv.srgb())


def siding():
    """Board-and-batten boards (painted, the battens are geometry): a faint grain and the
    board joints every 0.3 m under the battens; tile 1.2 m."""
    n = 256
    rng = np.random.default_rng(13)
    base = np.array([186, 178, 162], np.float32) / 255
    lin = np.zeros((n, n, 3), np.float32) + to_lin(base)
    g = rng.random((n // 8, n)).astype(np.float32)
    g = np.repeat(g, 8, axis=0).T
    lin *= 0.92 + 0.12 * g[..., None]
    lin *= (0.97 + 0.06 * rng.random((n, n, 1))).astype(np.float32)
    return write_png(os.path.join(OUT, "T_Town2_Gas_Siding.png"), to_srgb(lin))


def joints_concrete(lin, tile_px, every=1, w=2, dark=0.55):
    """Saw-cut joints along the tile's left and top edges (a slab per tile)."""
    out = lin.copy()
    out[:, :w] *= dark
    out[:w, :] *= dark
    return out


def grout_grid(cells, w=2, col=(0.38, 0.36, 0.33)):
    def f(lin):
        n = lin.shape[0]
        step = n // cells
        out = lin.copy()
        c = to_lin(np.array(col, np.float32) * 0 + np.array(col, np.float32))
        for k in range(cells):
            out[k * step:k * step + w, :] = out[k * step:k * step + w, :] * 0.3 + c * 0.7
            out[:, k * step:k * step + w] = out[:, k * step:k * step + w] * 0.3 + c * 0.7
        # a little tile-to-tile shade variation
        rng = np.random.default_rng(17)
        for a in range(cells):
            for b in range(cells):
                out[a * step + w:(a + 1) * step, b * step + w:(b + 1) * step] *= 0.97 + 0.06 * rng.random()
        return out
    return f


DECALS = {}     # filled by decals(): name -> uv rect


def floor_rough():
    """The store floor's metallicRoughness map (matches T_Town2_Gas_Floor: 60 cm tiles, two to a
    1.2 m tile): polished tile (G 0.12-0.3, smudged and worn where feet go), grout matte."""
    n = 256
    rng = np.random.default_rng(29)
    r = np.zeros((n, n), np.float32) + 0.07
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    for k in range(18):
        cx, cy, rad = rng.random() * n, rng.random() * n, rng.uniform(10, 60)
        r += rng.uniform(0.03, 0.14) * np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / rad ** 2))
    r += (rng.random((n, n)).astype(np.float32) - 0.5) * 0.04
    for g in (0, n // 2):
        r[g:g + 2, :] = 0.85
        r[:, g:g + 2] = 0.85
    img = np.stack([np.ones_like(r), np.clip(r, 0.05, 1.0), np.zeros_like(r)], axis=2)
    return write_png(os.path.join(OUT, "T_Town2_Gas_FloorRough.png"), img)


def decals():
    """Wear (alpha-blended black: they darken what's under them): door scuffs, gum, tyre marks,
    oil, dust, drip streaks, corner grime; a 4 x 4 atlas of 128 px cells (RGBA, black, alpha)."""
    n, S = 512, 128
    rng = np.random.default_rng(31)
    A = np.zeros((n, n), np.float32)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)

    def put(i, a, name):
        c, r = i % 4, i // 4
        A[r * S:(r + 1) * S, c * S:(c + 1) * S] = np.clip(a, 0, 1)
        DECALS[name] = ((c * S + 3) / n, 1 - ((r + 1) * S - 3) / n, ((c + 1) * S - 3) / n, 1 - (r * S + 3) / n)

    def soft(cx, cy, rx, ry, k=1.0):
        return np.exp(-(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)) * k
    edge = np.clip(np.minimum(np.minimum(xx, S - xx), np.minimum(yy, S - yy)) / 18, 0, 1)
    for i in range(4):                                     # foot-traffic scuffs: long soft smears
        a = np.zeros((S, S), np.float32)
        for _ in range(14):
            cx, cy = rng.uniform(20, 108), rng.uniform(20, 108)
            a += soft(cx, cy, rng.uniform(10, 40), rng.uniform(2, 8), rng.uniform(0.05, 0.13))
        put(i, a * edge, f"scuff{i}")
    a = np.zeros((S, S), np.float32)                       # gum: hard little dots
    for _ in range(22):
        cx, cy, rr = rng.uniform(8, 120), rng.uniform(8, 120), rng.uniform(1.2, 3.2)
        a = np.maximum(a, np.clip((rr - np.hypot(xx - cx, yy - cy)) * 1.2, 0, 1) * rng.uniform(0.45, 0.7))
    put(4, a, "gum")
    a = np.zeros((S, S), np.float32)                       # tyre marks: two soft arcs with tread
    for off in (-14, 14):
        d = np.abs(np.hypot(xx - 64, yy + 140) - 190 - off)
        a += np.exp(-(d / 5) ** 2) * (0.6 + 0.4 * np.sin(xx * 1.7)) * 0.28
    put(5, a * edge, "tyre")
    for i in range(3):                                     # oil: a soft stain with a darker rim
        a = np.zeros((S, S), np.float32)
        for _ in range(4):
            a += soft(64 + rng.uniform(-14, 14), 64 + rng.uniform(-14, 14), rng.uniform(18, 34), rng.uniform(14, 28), rng.uniform(0.15, 0.3))
        a += np.exp(-((np.hypot((xx - 64) / 1.2, yy - 64) - 36) / 5) ** 2) * 0.12
        put(6 + i, a * edge, f"oil{i}")
    put(9, (rng.random((S, S)).astype(np.float32) * 0.12 + 0.08) * edge, "dust")
    a = np.zeros((S, S), np.float32)                       # drip streaks (down a wall)
    for _ in range(9):
        cx = rng.uniform(10, 118)
        a += np.exp(-((xx - cx) / rng.uniform(1.5, 4)) ** 2) * np.clip(1 - yy / rng.uniform(60, 128), 0, 1) * rng.uniform(0.1, 0.3)
    put(10, a, "drip")
    put(11, np.clip(1 - yy / 50, 0, 1) ** 2 * 0.35 * edge, "grime")
    img = np.stack([np.zeros_like(A), np.zeros_like(A), np.zeros_like(A), A], axis=2)
    return write_png(os.path.join(OUT, "T_Town2_Gas_Decals.png"), img)


def frost():
    """The cooler doors' frost: white, faint over the glass, thicker in a feathered band at the
    bottom and the edges (RGBA, 128 x 256)."""
    w, h = 128, 256
    rng = np.random.default_rng(37)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nz = rng.random((h // 8, w // 8)).astype(np.float32)
    nz = np.kron(nz, np.ones((8, 8), np.float32))
    edge = np.minimum(xx, w - xx) / w
    bottom = (yy / h)
    a = 0.06 + 0.45 * np.clip((bottom - 0.82) / 0.18 + (nz - 0.5) * 0.5, 0, 1) + 0.25 * np.clip((0.08 - edge) / 0.08 + (nz - 0.5) * 0.6, 0, 1)
    img = np.stack([np.full_like(a, 0.93), np.full_like(a, 0.96), np.ones_like(a), np.clip(a, 0, 0.75)], axis=2)
    return write_png(os.path.join(OUT, "T_Town2_Gas_Frost.png"), img)


def build_all(feeds=None):
    """Make every texture; returns dict(paths, palette uv, atlases)."""
    os.makedirs(OUT, exist_ok=True)
    P = {}
    # (target mean colours, sRGB)
    P["concrete"] = scan("T_Town2_Gas_Concrete", "brushed_concrete_03", 512, (178, 174, 166), 0.9,
                         post=lambda l: joints_concrete(l, 512, w=2, dark=0.5))
    P["asphalt"] = scan("T_Town2_Gas_Asphalt", "clean_asphalt", 256, (104, 103, 101), 1.0)
    P["stone"] = scan("T_Town2_Gas_Stone", "rustic_stone_wall_02", 512, (156, 144, 126), 1.0)
    P["oak"] = scan("T_Town2_Gas_Oak", "white_oak_veneer", 256, (176, 140, 100), 1.0)
    P["floor"] = scan("T_Town2_Gas_Floor", "terrazzo_tiles", 512, (168, 164, 156), 0.55, post=grout_grid(2, w=1, col=(0.52, 0.50, 0.47)))
    P["ceiling"] = ceiling()
    P["siding"] = siding()
    uv = palette()
    P["paint"] = os.path.join(OUT, "T_Town2_Gas_Paint.png")
    P["paint_rough"] = os.path.join(OUT, "T_Town2_Gas_PaintRough.png")
    import town2_gas_pack
    P["goods"], goods = town2_gas_pack.save()
    S = signs(feeds)
    P["signs"] = os.path.join(OUT, S.name + ".png")
    P["floor_rough"] = floor_rough()
    P["decals"] = decals()
    P["frost"] = frost()
    return dict(paths=P, palette=uv, goods=goods, signs=S.cells, decals=DECALS)
