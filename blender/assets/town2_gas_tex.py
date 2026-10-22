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
    "lightgrey": ((182, 184, 182), 0.5), "steel": ((150, 152, 154), 0.3), "darksteel": ((92, 94, 96), 0.35),
    "rubber": ((20, 20, 21), 0.8), "hose": ((30, 31, 33), 0.55), "green": ((38, 84, 64), 0.4),
    "green_dark": ((26, 56, 44), 0.45), "sage": ((120, 140, 118), 0.6), "red": ((176, 30, 28), 0.4),
    "yellow": ((228, 182, 28), 0.45), "safety": ((236, 196, 30), 0.5), "blue": ((34, 78, 148), 0.4),
    "propane_white": ((230, 230, 226), 0.4), "copper": ((150, 88, 50), 0.35), "cardboard": ((176, 138, 96), 0.85),
    "kraft": ((150, 116, 80), 0.85), "wood_dark": ((70, 50, 36), 0.6), "mulch": ((62, 42, 30), 0.95),
    "soil": ((58, 46, 36), 1.0), "leaf": ((52, 74, 38), 0.8), "leaf_light": ((86, 110, 52), 0.8),
    "grout": ((120, 116, 110), 0.9), "cream": ((236, 226, 202), 0.5), "brown": ((96, 62, 40), 0.5),
    "coffee": ((46, 28, 18), 0.3), "orange": ((222, 110, 30), 0.45), "tan": ((196, 170, 132), 0.6),
    "van": ((34, 36, 40), 0.35), "van_trim": ((18, 18, 20), 0.6), "tyre": ((22, 22, 23), 0.85),
    "chrome": ((196, 198, 200), 0.2), "glass_dark": ((14, 16, 18), 0.1), "porcelain": ((242, 242, 240), 0.15),
    "tile_wall": ((206, 204, 198), 0.3), "partition": ((92, 96, 100), 0.35), "concrete_grey": ((150, 148, 142), 0.9),
    "asphalt_patch": ((40, 40, 42), 0.9), "oil": ((22, 22, 24), 0.6), "paint_white_road": ((222, 222, 214), 0.7),
    "paint_yellow_road": ((214, 170, 40), 0.7), "mat": ((40, 42, 44), 0.95), "foam": ((210, 206, 196), 0.8),
    "lid_black": ((30, 30, 32), 0.4), "cup_white": ((240, 238, 232), 0.5), "sausage": ((150, 72, 44), 0.35),
    "bun": ((206, 156, 96), 0.7), "mustard": ((214, 170, 40), 0.5),
}


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
        rough[cy * 32:(cy + 1) * 32, cx * 32:(cx + 1) * 32] = (0.0, r, 0.0)   # glTF metallicRoughness: G
        uv[k] = ((cx + 0.5) / n, 1 - (cy + 0.5) / n)
    write_png(os.path.join(OUT, "T_Town2_Gas_Paint.png"), cv.srgb())
    write_png(os.path.join(OUT, "T_Town2_Gas_PaintRough.png"), rough)
    return uv


def _col(c):
    return tuple(np.array(c) / 255.0)


def goods():
    """The packaging atlas: 8 x 8 cells of 128 px; returns the Atlas (cells by kind_index)."""
    A = Atlas("T_Town2_Gas_Goods", 1024, 1024)
    cv = Canvas(1024, 1024, (0.2, 0.2, 0.2))
    rng = np.random.default_rng(42)
    S = 128
    bag_cols = [(206, 36, 34), (236, 186, 30), (30, 92, 176), (40, 140, 70), (120, 40, 140), (236, 110, 30), (24, 24, 26), (200, 200, 196),
                (180, 30, 90), (30, 160, 180), (150, 190, 40), (220, 70, 50), (70, 50, 40), (40, 60, 120), (238, 214, 60), (190, 40, 40)]
    for i in range(16):                       # rows 0-1: chip bags
        x, y = (i % 8) * S, (i // 8) * S
        c = _col(bag_cols[i])
        cv.rect(x, y, x + S, y + S, (0.12, 0.12, 0.12))
        cv.rect(x + 6, y + 4, x + S - 6, y + S - 2, c, r=10)
        cv.rect(x + 6, y + 4, x + S - 6, y + 16, tuple(np.array(c) * 0.7), r=4)     # crimp
        cv.rect(x + 6, y + S - 14, x + S - 6, y + S - 2, tuple(np.array(c) * 0.7), r=4)
        acc = _col(bag_cols[(i * 5 + 3) % 16])
        cv.ellipse(x + S / 2, y + S * 0.42, S * 0.3, S * 0.2, (0.95, 0.93, 0.88))
        cv.ellipse(x + S / 2, y + S * 0.42, S * 0.24, S * 0.14, acc)
        # the chips in the window
        cv.ellipse(x + S * 0.5, y + S * 0.76, S * 0.2, S * 0.09, (0.86, 0.66, 0.30))
        cv.ellipse(x + S * 0.42, y + S * 0.72, S * 0.12, S * 0.07, (0.92, 0.74, 0.36))
        cv.rect(x + 14, y + S * 0.6, x + S - 14, y + S * 0.63, (0.97, 0.97, 0.95), r=2)
        cv.shade(x + 6, y, x + S - 6, y + S, k=0.45, gloss=0.08)
        A.add(f"bag{i}", x, y, x + S, y + S)
    candy = [(120, 60, 30), (200, 30, 40), (240, 200, 40), (30, 60, 140), (90, 40, 20), (230, 120, 30), (250, 250, 245), (40, 120, 60)]
    for i in range(8):                        # row 2: candy display boxes (a row of bars)
        x, y = i * S, 2 * S
        cv.rect(x, y, x + S, y + S, (0.35, 0.3, 0.25))
        for k in range(4):
            c = _col(candy[(i + k * 3) % 8])
            yy = y + 8 + k * 30
            cv.rect(x + 6, yy, x + S - 6, yy + 26, c, r=3)
            cv.rect(x + 30, yy + 8, x + S - 30, yy + 18, tuple(1 - np.array(c) * 0.6), r=4)
            cv.shade(x + 6, yy, x + S - 6, yy + 26, k=0.5, horizontal=False, gloss=0.1)
        A.add(f"candy{i}", x, y, x + S, y + S)
    boxc = [(200, 40, 40), (40, 90, 170), (240, 200, 60), (120, 70, 40), (60, 140, 80), (230, 230, 225), (170, 40, 120), (240, 140, 40)]
    for i in range(8):                        # row 3: boxes (cookies, crackers, pastries, medicine)
        x, y = i * S, 3 * S
        c = _col(boxc[i])
        cv.rect(x, y, x + S, y + S, c)
        cv.rect(x + 12, y + 50, x + S - 12, y + S - 14, (0.96, 0.95, 0.9), r=8)
        cv.ellipse(x + S / 2, y + 84, 26, 20, _col(candy[i]))
        cv.rect(x + 10, y + 14, x + S - 10, y + 36, tuple(np.array(c) * 0.6), r=4)
        A.add(f"box{i}", x, y, x + S, y + S)
    for i in range(8):                        # row 4: pouches (jerky, nuts, trail mix): kraft + window
        x, y = i * S, 4 * S
        base = _col([(150, 116, 80), (40, 40, 42), (160, 40, 30), (40, 80, 50), (150, 116, 80), (210, 190, 150), (60, 40, 30), (30, 50, 90)][i])
        cv.rect(x, y, x + S, y + S, (0.15, 0.15, 0.15))
        cv.rect(x + 10, y + 6, x + S - 10, y + S - 4, base, r=8)
        cv.rect(x + 28, y + 50, x + S - 28, y + S - 20, (0.55, 0.32, 0.18) if i % 2 == 0 else (0.62, 0.48, 0.30), r=12)
        cv.rect(x + 18, y + 18, x + S - 18, y + 38, (0.94, 0.9, 0.8), r=4)
        cv.shade(x + 10, y, x + S - 10, y + S, k=0.4, gloss=0.05)
        A.add(f"pouch{i}", x, y, x + S, y + S)
    jug = [(30, 60, 150), (20, 20, 22), (230, 190, 30), (40, 130, 200), (200, 40, 30), (240, 240, 236), (60, 120, 60), (80, 80, 84)]
    for i in range(8):                        # row 5: jugs and bottles (oil, washer fluid, coolant, cleaners)
        x, y = i * S, 5 * S
        c = _col(jug[i])
        cv.rect(x, y, x + S, y + S, (0.2, 0.2, 0.2))
        cv.rect(x + 18, y + 26, x + S - 18, y + S - 4, c, r=14)
        cv.rect(x + 52, y + 6, x + 76, y + 30, tuple(np.array(c) * 0.8), r=4)
        cv.rect(x + 26, y + 60, x + S - 26, y + 104, (0.95, 0.95, 0.92), r=4)
        cv.rect(x + 30, y + 66, x + S - 30, y + 76, _col(jug[(i + 3) % 8]), r=2)
        cv.shade(x + 18, y, x + S - 18, y + S, k=0.5, gloss=0.1)
        A.add(f"jug{i}", x, y, x + S, y + S)
    for i in range(8):                        # row 6: cigarette and tobacco packs (a grid of packs per cell)
        x, y = i * S, 6 * S
        cv.rect(x, y, x + S, y + S, (0.1, 0.1, 0.1))
        tones = [(250, 250, 248), (200, 30, 36), (230, 200, 120), (40, 60, 120), (30, 30, 30), (90, 140, 80), (160, 120, 60), (110, 110, 120)]
        for r_ in range(2):
            for k in range(4):
                c = _col(tones[(i + k + r_ * 2) % 8])
                px0, py0 = x + 4 + k * 31, y + 4 + r_ * 62
                cv.rect(px0, py0, px0 + 28, py0 + 58, c, r=2)
                cv.rect(px0, py0 + 34, px0 + 28, py0 + 58, (0.95, 0.95, 0.93), r=1)      # the warning panel (no words)
                cv.rect(px0 + 6, py0 + 8, px0 + 22, py0 + 20, _col(tones[(i + k + 5) % 8]), r=6)
        A.add(f"pack{i}", x, y, x + S, y + S)
    misc = ["cups", "lids", "ice_panel", "coffeebag", "cardboard", "cardboard2", "tickets", "propane_panel"]
    for i, k in enumerate(misc):              # row 7
        x, y = i * S, 7 * S
        if k == "cups":
            cv.rect(x, y, x + S, y + S, (0.94, 0.93, 0.9))
            for j in range(6):
                cv.rect(x + 8, y + 8 + j * 20, x + S - 8, y + 12 + j * 20, (0.75, 0.72, 0.68))
            cv.rect(x + 30, y + 50, x + S - 30, y + 80, (0.15, 0.35, 0.28), r=6)
        elif k == "lids":
            cv.rect(x, y, x + S, y + S, (0.12, 0.12, 0.13))
            for j in range(10):
                cv.rect(x, y + j * 13, x + S, y + j * 13 + 3, (0.25, 0.25, 0.26))
        elif k == "ice_panel":       # the ice merchandiser's printed door: blue, a white snowflake
            cv.vgrad(x, y, x + S, y + S, (70, 160, 225), (24, 84, 170))
            cx, cy = x + S / 2, y + S / 2
            for j in range(3):
                a = j * math.pi / 3
                dx, dy, nx, ny = math.cos(a) * 44, math.sin(a) * 44, -math.sin(a) * 4, math.cos(a) * 4
                cv.poly([(cx - dx + nx, cy - dy + ny), (cx + dx + nx, cy + dy + ny), (cx + dx - nx, cy + dy - ny), (cx - dx - nx, cy - dy - ny)], (1, 1, 1))
            cv.ellipse(cx, cy, 8, 8, (1, 1, 1))
        elif k == "coffeebag":
            cv.rect(x, y, x + S, y + S, (0.12, 0.08, 0.06))
            cv.rect(x + 14, y + 10, x + S - 14, y + S - 6, (0.2, 0.13, 0.09), r=6)
            cv.ellipse(x + S / 2, y + 60, 24, 24, (0.85, 0.72, 0.45))
            cv.ellipse(x + S / 2, y + 60, 14, 18, (0.25, 0.15, 0.1))
        elif k.startswith("cardboard"):
            cv.rect(x, y, x + S, y + S, (0.69, 0.54, 0.37) if k == "cardboard" else (0.62, 0.48, 0.33))
            cv.rect(x, y + S / 2 - 3, x + S, y + S / 2 + 3, (0.8, 0.72, 0.55))           # tape
            cv.rect(x + 12, y + 80, x + 60, y + 110, (0.95, 0.95, 0.93), r=2)             # shipping label
            cv.rect(x + 16, y + 86, x + 50, y + 90, (0.2, 0.2, 0.2))
            cv.rect(x + 16, y + 96, x + 44, y + 100, (0.2, 0.2, 0.2))
        elif k == "tickets":
            cv.rect(x, y, x + S, y + S, (0.1, 0.1, 0.1))
            tc = [(230, 40, 120), (40, 180, 220), (250, 200, 30), (60, 200, 90), (240, 90, 30), (150, 60, 200)]
            for j in range(6):
                cv.rect(x + 4 + (j % 3) * 41, y + 4 + (j // 3) * 62, x + 40 + (j % 3) * 41, y + 62 + (j // 3) * 62, _col(tc[j]), r=3)
                cv.ellipse(x + 22 + (j % 3) * 41, y + 26 + (j // 3) * 62, 10, 10, (0.98, 0.9, 0.3))
        elif k == "propane_panel":   # the exchange cage's sign: a white flame on blue
            cv.rect(x, y, x + S, y + S, _col((30, 70, 150)))
            cv.poly([(x + 64, y + 14), (x + 92, y + 60), (x + 96, y + 90), (x + 64, y + 116), (x + 32, y + 90), (x + 38, y + 56), (x + 50, y + 70)], (1, 1, 1))
            cv.poly([(x + 64, y + 66), (x + 76, y + 88), (x + 64, y + 104), (x + 52, y + 88)], _col((30, 70, 150)))
        A.add(k, x, y, x + S, y + S)
    cv.noise(0.02, seed=3)
    A.save(cv, 512)
    return A


def drinks():
    """Cooler shelf cards: 4 x 8 cells of 256 x 128 px, a shelf's front row as seen through the
    door (bottles / cans on a lit white back, the shelf's price strip under them)."""
    A = Atlas("T_Town2_Gas_Drinks", 1024, 1024)
    cv = Canvas(1024, 1024, (0.6, 0.6, 0.6))
    W, Hc = 256, 128
    kinds = [
        ("water", (200, 225, 240), (40, 110, 200), 8, "bottle"), ("cola", (60, 26, 16), (200, 30, 30), 8, "bottle"),
        ("lemon", (190, 230, 150), (40, 150, 60), 8, "bottle"), ("orange", (240, 140, 30), (240, 240, 240), 8, "bottle"),
        ("sport_b", (60, 120, 230), (240, 240, 240), 7, "sport"), ("sport_r", (220, 40, 50), (240, 240, 240), 7, "sport"),
        ("sport_y", (220, 230, 60), (30, 30, 30), 7, "sport"), ("tea", (170, 90, 30), (240, 220, 160), 8, "bottle"),
        ("energy_k", (24, 24, 26), (120, 220, 60), 10, "can"), ("energy_s", (190, 192, 196), (30, 60, 160), 10, "can"),
        ("energy_w", (240, 240, 238), (230, 60, 140), 10, "can"), ("seltzer", (230, 236, 240), (90, 170, 210), 10, "can"),
        ("milk", (246, 246, 244), (40, 90, 170), 4, "jug"), ("choc", (120, 70, 40), (240, 240, 240), 6, "carton"),
        ("juice", (240, 150, 30), (40, 140, 60), 6, "bottle"), ("cran", (150, 20, 40), (240, 240, 240), 6, "bottle"),
        ("beer_a", (190, 150, 60), (30, 40, 90), 3, "case"), ("beer_b", (30, 70, 40), (230, 220, 200), 3, "case"),
        ("beer_c", (200, 40, 40), (240, 240, 240), 3, "case"), ("beer_d", (240, 240, 236), (40, 60, 130), 3, "case"),
        ("coffee_can", (60, 40, 30), (230, 200, 150), 10, "can"), ("protein", (240, 240, 240), (60, 60, 64), 8, "carton"),
        ("cola_can", (200, 30, 30), (240, 240, 240), 10, "can"), ("diet", (200, 200, 205), (200, 30, 30), 10, "can"),
        ("water2", (210, 230, 245), (30, 140, 120), 6, "big"), ("kombucha", (200, 160, 100), (30, 30, 30), 8, "bottle"),
        ("ice_tea_can", (230, 200, 90), (40, 80, 50), 10, "can"), ("soda_or", (240, 120, 20), (30, 30, 30), 8, "bottle"),
        ("sand", (230, 220, 200), (150, 50, 40), 4, "sandwich"), ("salad", (110, 160, 70), (240, 240, 236), 4, "sandwich"),
        ("yogurt", (240, 240, 236), (200, 60, 90), 8, "cup"), ("cheese", (240, 200, 90), (200, 40, 40), 6, "cup"),
    ]
    for i, (key, liquid, label, n, shape) in enumerate(kinds):
        x, y = (i % 4) * W, (i // 4) * Hc
        cv.vgrad(x, y, x + W, y + Hc, (236, 238, 240), (196, 200, 204))      # the lit white back
        cv.rect(x, y + Hc - 14, x + W, y + Hc, (0.94, 0.94, 0.92))             # price strip
        for k in range(6):
            cv.rect(x + 8 + k * 42, y + Hc - 12, x + 30 + k * 42, y + Hc - 3, (0.98, 0.85, 0.2) if k % 3 == 0 else (0.92, 0.92, 0.9), r=1)
        bw = (W - 8) / n
        top = y + 6
        for k in range(n):
            bx = x + 4 + k * bw
            L, Lb = _col(liquid), _col(label)
            if shape == "bottle" or shape == "sport":
                cv.rect(bx + bw * 0.2, top + 26, bx + bw * 0.8, y + Hc - 16, L, r=bw * 0.18)
                cv.rect(bx + bw * 0.36, top + 8, bx + bw * 0.64, top + 30, L, r=4)
                cv.rect(bx + bw * 0.34, top + 2, bx + bw * 0.66, top + 10, Lb if shape == "sport" else (0.9, 0.9, 0.9) if key == "water" else Lb, r=2)
                cv.rect(bx + bw * 0.2, top + 52, bx + bw * 0.8, top + 82, Lb, r=2)
                cv.rect(bx + bw * 0.3, top + 60, bx + bw * 0.7, top + 72, L, r=3)
                cv.shade(bx + bw * 0.2, top, bx + bw * 0.8, y + Hc - 16, k=0.55, gloss=0.25)
            elif shape == "can":
                cv.rect(bx + bw * 0.12, top + 24, bx + bw * 0.88, y + Hc - 16, L, r=3)
                cv.rect(bx + bw * 0.12, top + 50, bx + bw * 0.88, top + 70, Lb, r=1)
                cv.rect(bx + bw * 0.16, top + 20, bx + bw * 0.84, top + 26, (0.75, 0.76, 0.78), r=2)
                cv.shade(bx + bw * 0.12, top, bx + bw * 0.88, y + Hc - 16, k=0.5, gloss=0.3)
            elif shape in ("jug", "big"):
                cv.rect(bx + bw * 0.1, top + 22, bx + bw * 0.9, y + Hc - 16, L, r=10)
                cv.rect(bx + bw * 0.4, top + 6, bx + bw * 0.6, top + 24, Lb, r=3)
                cv.rect(bx + bw * 0.15, top + 50, bx + bw * 0.85, top + 80, Lb, r=3)
                cv.shade(bx + bw * 0.1, top, bx + bw * 0.9, y + Hc - 16, k=0.4, gloss=0.15)
            elif shape == "carton":
                cv.rect(bx + bw * 0.12, top + 30, bx + bw * 0.88, y + Hc - 16, L, r=2)
                cv.poly([(bx + bw * 0.12, top + 30), (bx + bw * 0.5, top + 16), (bx + bw * 0.88, top + 30)], L)
                cv.rect(bx + bw * 0.2, top + 54, bx + bw * 0.8, top + 84, Lb, r=3)
                cv.shade(bx + bw * 0.12, top, bx + bw * 0.88, y + Hc - 16, k=0.3)
            elif shape == "case":
                cv.rect(bx + 2, top + 30, bx + bw - 2, y + Hc - 16, L, r=2)
                cv.rect(bx + 8, top + 50, bx + bw - 8, top + 76, Lb, r=3)
                cv.rect(bx + 2, top + 30, bx + bw - 2, top + 38, tuple(np.array(L) * 0.7))
                cv.shade(bx + 2, top, bx + bw - 2, y + Hc - 16, k=0.2)
            elif shape == "sandwich":
                cv.poly([(bx + 4, y + Hc - 16), (bx + bw - 4, y + Hc - 16), (bx + bw - 4, top + 40)], (0.9, 0.92, 0.94))
                cv.poly([(bx + 10, y + Hc - 20), (bx + bw - 10, y + Hc - 20), (bx + bw - 10, top + 52)], L)
                cv.rect(bx + 10, y + Hc - 40, bx + bw - 10, y + Hc - 30, Lb, r=2)
            elif shape == "cup":
                cv.rect(bx + bw * 0.15, top + 60, bx + bw * 0.85, y + Hc - 16, L, r=6)
                cv.rect(bx + bw * 0.12, top + 56, bx + bw * 0.88, top + 64, Lb, r=2)
                cv.rect(bx + bw * 0.15, top + 70, bx + bw * 0.85, top + 84, Lb, r=2)
        A.add(key, x, y, x + W, y + Hc)
    cv.noise(0.015, seed=5)
    A.save(cv, 512)
    return A


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
    cv.rect(256, 256, 512, 288, _col((60, 190, 130)))
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


def build_all(feeds=None):
    """Make every texture; returns dict(paths, palette uv, atlases)."""
    os.makedirs(OUT, exist_ok=True)
    P = {}
    # (target mean colours, sRGB)
    P["concrete"] = scan("T_Town2_Gas_Concrete", "brushed_concrete_03", 512, (178, 174, 166), 0.9,
                         post=lambda l: joints_concrete(l, 512, w=2, dark=0.5))
    P["asphalt"] = scan("T_Town2_Gas_Asphalt", "clean_asphalt", 512, (88, 87, 86), 1.0)
    P["stone"] = scan("T_Town2_Gas_Stone", "rustic_stone_wall_02", 512, (156, 144, 126), 1.0)
    P["oak"] = scan("T_Town2_Gas_Oak", "white_oak_veneer", 256, (176, 140, 100), 1.0)
    P["floor"] = scan("T_Town2_Gas_Floor", "terrazzo_tiles", 512, (184, 180, 172), 0.55, post=grout_grid(2, w=1, col=(0.52, 0.50, 0.47)))
    P["ceiling"] = ceiling()
    P["siding"] = siding()
    uv = palette()
    P["paint"] = os.path.join(OUT, "T_Town2_Gas_Paint.png")
    P["paint_rough"] = os.path.join(OUT, "T_Town2_Gas_PaintRough.png")
    G = goods()
    D = drinks()
    S = signs(feeds)
    for k, a in (("goods", G), ("drinks", D), ("signs", S)):
        P[k] = os.path.join(OUT, a.name + ".png")
    return dict(paths=P, palette=uv, goods=G.cells, drinks=D.cells, signs=S.cells)
