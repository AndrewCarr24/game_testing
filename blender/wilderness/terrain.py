"""Wilderness terrain generator (concept-agnostic spike): authored large forms + fractal detail,
fluvial / droplet / thermal erosion, hydrology (lakes, rivers, banks), gameplay sculpting hooks,
masks, previews and engine-ready data. Pure numpy (no scipy, no PIL, no bpy), so it runs in
Blender's bundled Python without Blender itself:

  PY=/Applications/Blender.app/Contents/Resources/5.0/python/bin/python3.11
  $PY blender/wilderness/terrain.py [--name demo] [--quick] [--set key=value ...] [--set erosion.droplets.per_cell=0.5]

then the meshes, glTF chunks and renders (one headless Blender, takes a "level" run slot):

  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
      --python blender/wilderness/terrain_blender.py -- demo

Everything is driven by the P dict below (reproducible: same P + seed = same terrain, bit for
bit). A concept overrides P (build(**overrides) or a dict merged in), it doesn't edit outputs.

Coordinates: Blender metres, z up, +y north, origin at the terrain centre. Arrays are [row, col]
= [y, x] with row 0 at the SOUTH edge (y0); every image / binary written to disk has row 0 at
the NORTH edge (image convention, and = the smallest three.js z, since three z = -blender y).

Stage order (each stage sees the previous one's result):
  1 macro      control shapes (ridges, valleys, basins, plateaus, optional guide image) + tilt
  2 detail     domain-warped fBm (lowlands) + ridged multifractal (mountains, masked by ridges)
  3 fluvial    stream-power incision on a 4x coarser grid (dendritic valleys), upsampled delta
  4 droplets   particle hydraulic erosion, all droplets of a batch advanced together (vectorised)
  5 thermal    talus relaxation (scree slopes, removes droplet spikes)
  6 cliffs     gameplay hook: sheer edge along a spline (after erosion so it stays crisp)
  7 hydrology  priority-flood fill, D8 flow accumulation, lakes (filled basins, flat level),
               rivers carved along flow with width ~ sqrt(area), banks, beaches
  8 hooks      pads (flatten a disc) and corridors (path spline: grade-limited, flattened)
  9 fords      river channels re-cut through corridors that cross them (ford=True)
 10 masks      on the final surface: slope, altitude, flow, wetness, curvature, aspect,
               distance-to-path, rivers, lakes, sediment; previews; "Bake" light/colour
"""
import heapq
import json
import math
import os
import struct
import sys
import time
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT_ROOT = os.path.join(PROJECT, "build", "wilderness")

# ---------------------------------------------------------------------------------- parameters
P = dict(
    name="demo",
    seed=7,
    size=1536.0,            # m, square, centred on the origin
    cell=1.5,               # m between height samples (1025 x 1025 at the defaults)
    base=0.0,               # m, height before shapes (the south entry sits near 0)
    tilt=(0.0, 0.045),      # m per m (east, north): the land rises away from the estate
    # Large forms. Polylines are Catmull-Rom splines through the points; per-point attributes
    # (height or depth, width = full base width) are interpolated along them.
    shapes=[
        dict(kind="ridge", name="north_range", sharp=1.0, points=[
            (-860, 700, 200, 860), (-430, 760, 250, 900), (-170, 720, 170, 760),
            (20, 700, 50, 520), (230, 730, 190, 760), (520, 780, 260, 900), (880, 700, 210, 860)]),
        dict(kind="ridge", name="west_spur", points=[
            (-480, 720, 210, 700), (-660, 360, 150, 620), (-740, -40, 110, 560), (-820, -480, 70, 520)]),
        dict(kind="ridge", name="east_spur", points=[
            (560, 760, 220, 700), (680, 300, 150, 620), (760, -140, 100, 560), (820, -520, 60, 520)]),
        dict(kind="valley", name="main_valley", points=[
            (130, 430, 20, 140), (70, 210, 30, 170), (-90, 10, 28, 200),
            (-330, -330, 26, 170), (-460, -600, 24, 160), (-560, -820, 20, 150)]),
        dict(kind="basin", name="lake_basin", center=(-215, -110), radius=(190, 125), angle=25, depth=30),
        dict(kind="plateau", name="mesa", center=(390, -380), radius=(190, 140), angle=-15,
             height=55, edge=0.3),
    ],
    guide=None,             # optional sketch: path to a grey PNG (8-bit, any size) or .npy over the
    guide_height=0.0,       #   terrain square, white = +guide_height m (bilinear, added to the macro)
    shape_jitter=35.0,      # m: noise added to every shape's distance field (no geometric contours)
    detail=dict(
        warp=70.0, warp_wavelength=650.0,                       # domain warp (m)
        low_amp=22.0, low_wavelength=420.0, low_octaves=9,      # rolling lowland fBm
        high_amp=80.0, high_wavelength=340.0, high_octaves=8,  # ridged multifractal on ridges
        mountain=(0.05, 0.6),                                   # ridge height fraction -> 0..1 mask
    ),
    erosion=dict(
        fluvial=dict(on=True, factor=4, iters=50, k=0.02, m=0.5, diffusion=0.15),
        droplets=dict(on=True, scales=(1,), scale_share=(1.0,),  # grid factor(s) and droplet share
                      per_cell=0.15, batch=65536, lifetime=56, inertia=0.25,
                      capacity=4.0, min_slope=0.02, erode=0.3, deposit=0.25, evaporate=0.02,
                      gravity=9.81, radius=2, max_step=0.35),
        thermal=dict(on=True, talus_deg=38.0, iters=40, rate=0.45),
    ),
    hydro=dict(
        eps=1e-4,                     # m per cell of the epsilon fill (routing across flats)
        river_area=1.2e5,             # m² of catchment where a stream becomes a carved river
        width_k=8.0, width=(3.0, 14.0),   # width = width_k * sqrt(area km²), clamped (m)
        depth_k=0.12, depth0=0.5,     # channel depth = depth0 + depth_k * width (m)
        bank_drop=0.3,                # water this far below the surrounding ground (m)
        bank_w=8.0, bank_deg=12.0,    # banks: graded at bank_deg over bank_w beside the channel
        lake_min_area=2500.0, lake_min_depth=1.5, freeboard=0.3,  # lake = filled basin
        beach_w=10.0, beach_deg=5.0, shelf_deg=9.0,
    ),
    # Gameplay hooks (applied after erosion; authoritative). side=+1 raises the right-hand side
    # of the cliff polyline's direction of travel.
    cliffs=[dict(name="mesa_west", points=[(225, -520), (200, -390), (215, -260)], height=18.0,
                 side=+1, edge=2.0, back=20.0, end_fade=40.0, jitter=2.5, talus_deg=38.0)],
    # River steps (waterfalls): after erosion, before cliffs, everything downstream of a lip on
    # a channel-following band is lowered by `height` (taper across (1-t²)² over width/2, faded
    # out over `fade` m at the far end), so erosion can't smooth the step away and the cliff hook's
    # 2° trench fill can't ramp it. An optional plunge pool (disc, (1-(r/R)²)² profile) is dug
    # after the cliffs, so hydrology turns it into a lake. points run downstream from the lip.
    knicks=[],              # dict(name, points, height, width, lip, fade, pool=dict(center, radius, depth))
    pads=[dict(name="gate", center=(20, -748), radius=24, falloff=14),
          dict(name="camp", center=(25, 120), radius=20, falloff=12),
          dict(name="overlook", center=(300, -380), radius=13, falloff=8),
          dict(name="pass", center=(25, 660), radius=16, falloff=10)],
    paths=[dict(name="trail", width=4.0, shoulder=6.0, max_grade=0.14, smooth=40.0, ford=True, switchbacks=True,
                bank_deg=34.0, cut_deg=50.0, reach=140.0, points=[(20, -768), (-20, -690), (-75, -570), (-10, -450), (60, -330), (5, -60),
                                       (25, 120), (170, 250), (-60, 360), (120, 470), (-20, 570), (25, 660)])],
    # rock_deg: slope band (deg) where the albedo turns to rock (plus noise and convexity);
    # cliff_rock: rock on the faces the cliff hook cut (masks/cliff.png)
    masks=dict(path_range=80.0, water_range=40.0, curv_sigma=(2.0, 8.0), rock_deg=(36.0, 48.0), cliff_rock=1.0),
    # light for the vertex-colour "Bake" stand-in and the renders (mansion.py LOOKS["golden"])
    look=dict(sun_dir=(0.94, 0.12, -0.32), sun_strength=6.0, sun_color=(1.0, 0.70, 0.45),
              sky=(0.42, 0.52, 0.72), sky_strength=0.85),
    palette=dict(           # linear albedo
        grass=(0.075, 0.115, 0.035), dry=(0.20, 0.17, 0.08), alpine=(0.16, 0.15, 0.10),
        rock=(0.22, 0.20, 0.18), scree=(0.30, 0.28, 0.25), dirt=(0.24, 0.17, 0.10),
        gravel=(0.34, 0.31, 0.26), mud=(0.09, 0.07, 0.05), forest=(0.035, 0.06, 0.025)),
    # holes: rects (x0, y0, x1, y1, height, blend m) held flat in the backdrop (e.g. an estate lawn
    # that lies outside the square); rock_deg: the backdrop's rock slope band
    backdrop=dict(extent=4608.0, cell=12.0, frame_height=110.0, frame_wavelength=900.0, blend=320.0,
                  holes=[], rock_deg=(28.0, 40.0)),
    chunks=8,               # per side (Blender phase); 1024 / 8 = 128 cells per chunk
    lods=(1, 2, 4, 8),      # LOD steps in cells (1.5 / 3 / 6 / 12 m)
)


def merged(base, overrides):
    """Deep-merge overrides (dicts merge, everything else replaces)."""
    out = dict(base)
    for k, v in overrides.items():
        out[k] = merged(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


# --------------------------------------------------------------------------------- PNG I/O
def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = np.abs(p - a), np.abs(p - b), np.abs(p - c)
    return np.where((pa <= pb) & (pa <= pc), a, np.where(pb <= pc, b, c))


def write_png(path, arr, flip=True, paeth=False):
    """uint8 (h,w) / (h,w,3) / (h,w,4) or uint16 (h,w). flip: array row 0 = south -> image bottom."""
    arr = np.ascontiguousarray(arr[::-1] if flip else arr)
    h, w = arr.shape[:2]
    ch = 1 if arr.ndim == 2 else arr.shape[2]
    depth = 16 if arr.dtype == np.uint16 else 8
    data = (arr.astype(">u2") if depth == 16 else arr.astype(np.uint8)).reshape(h, -1)
    raw = np.ascontiguousarray(data).view(np.uint8).reshape(h, -1).astype(np.int16)
    bpp = ch * depth // 8
    a = np.zeros_like(raw); a[:, bpp:] = raw[:, :-bpp]
    b = np.zeros_like(raw); b[1:] = raw[:-1]
    c = np.zeros_like(raw); c[1:, bpp:] = raw[:-1, :-bpp]
    if paeth:
        filt, ft = ((raw - _paeth(a, b, c)) % 256).astype(np.uint8), 4
    else:                                   # Up: decodes as one cumsum (read_png_fast)
        filt, ft = ((raw - b) % 256).astype(np.uint8), 2
    body = np.concatenate([np.full((h, 1), ft, np.uint8), filt], axis=1).tobytes()

    def chunk(tag, payload):
        return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
    color = {1: 0, 2: 4, 3: 2, 4: 6}[ch]
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, depth, color, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(body, 9)) + chunk(b"IEND", b""))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(png)
    return len(png)


def read_png(path):
    """Small 8/16-bit, non-interlaced PNG -> float array in 0..1 (grey; colour images averaged).
    Image row 0 (top) = north; returned with row 0 = south. For sketch guides, not big images."""
    with open(path, "rb") as fh:
        blob = fh.read()
    pos, idat, hdr = 8, b"", None
    while pos < len(blob):
        n, tag = struct.unpack(">I4s", blob[pos:pos + 8])
        payload = blob[pos + 8:pos + 8 + n]
        if tag == b"IHDR":
            hdr = struct.unpack(">IIBBBBB", payload)
        elif tag == b"IDAT":
            idat += payload
        pos += 12 + n
    w, h, depth, color, _, _, interlace = hdr
    assert interlace == 0 and color in (0, 2, 4, 6), "guide PNG: grey/RGB(A), non-interlaced"
    ch = {0: 1, 2: 3, 4: 2, 6: 4}[color]
    bpp = max(1, ch * depth // 8)
    raw = np.frombuffer(zlib.decompress(idat), np.uint8).reshape(h, 1 + w * ch * depth // 8)
    out = np.zeros((h, raw.shape[1] - 1), np.int32)
    for y in range(h):
        f, row = raw[y, 0], raw[y, 1:].astype(np.int32)
        up = out[y - 1] if y else np.zeros_like(row)
        if f == 0:
            cur = row
        elif f == 2:
            cur = (row + up) % 256
        else:
            cur = row.copy()
            for x in range(len(cur)):
                left = cur[x - bpp] if x >= bpp else 0
                ul = up[x - bpp] if x >= bpp else 0
                pred = {1: left, 3: (left + up[x]) // 2, 4: int(_paeth(np.int32(left), up[x], np.int32(ul)))}[int(f)]
                cur[x] = (row[x] + pred) % 256
        out[y] = cur
    if depth == 16:
        px = (out[:, 0::2] * 256 + out[:, 1::2]).reshape(h, w, ch) / 65535.0
    else:
        px = out.reshape(h, w, ch) / 255.0
    grey = px[..., :min(ch, 3) if ch != 2 else 1].mean(axis=2)
    return grey[::-1]


def read_png_fast(path):
    """Our own PNGs (Paeth rows, as write_png makes them) -> uint8/uint16 array, image row order.
    Vectorised per row; for previews and checks."""
    with open(path, "rb") as fh:
        blob = fh.read()
    pos, idat = 8, b""
    while pos < len(blob):
        n, tag = struct.unpack(">I4s", blob[pos:pos + 8])
        if tag == b"IHDR":
            w, h, depth, color = struct.unpack(">IIBB", blob[pos + 8:pos + 18])
        elif tag == b"IDAT":
            idat += blob[pos + 8:pos + 8 + n]
        pos += 12 + n
    ch = {0: 1, 2: 3, 4: 2, 6: 4}[color]
    bpp = ch * depth // 8
    raw = np.frombuffer(zlib.decompress(idat), np.uint8).reshape(h, -1)
    if (raw[:, 0] == 2).all():
        out = (np.cumsum(raw[:, 1:].astype(np.int64), axis=0) % 256).astype(np.int32)
        if depth == 16:
            return (out[:, 0::2] * 256 + out[:, 1::2]).astype(np.uint16).reshape(h, w, ch).squeeze()
        return out.astype(np.uint8).reshape(h, w, ch).squeeze()
    out = np.zeros((h, raw.shape[1] - 1), np.int32)
    prev = np.zeros(raw.shape[1] - 1, np.int32)
    for y in range(h):
        f, row = raw[y, 0], raw[y, 1:].astype(np.int32)
        if f == 0:
            cur = row
        elif f == 2:
            cur = (row + prev) % 256
        else:   # Sub / Average / Paeth: sequential across pixels, vectorised across rows' pixels' channels
            cur = np.zeros_like(row)
            for x0 in range(0, len(row), bpp):
                sl = slice(x0, x0 + bpp)
                a = cur[x0 - bpp:x0] if x0 else np.zeros(bpp, np.int32)
                c = prev[x0 - bpp:x0] if x0 else np.zeros(bpp, np.int32)
                b = prev[sl]
                pred = a if f == 1 else (a + b) // 2 if f == 3 else _paeth(a, b, c)
                cur[sl] = (row[sl] + pred) % 256
        out[y] = cur
        prev = cur
    if depth == 16:
        return (out[:, 0::2] * 256 + out[:, 1::2]).astype(np.uint16).reshape(h, w, ch).squeeze()
    return out.astype(np.uint8).reshape(h, w, ch).squeeze()


# --------------------------------------------------------------------------------- basics
class Grid:
    """Regular grid of nx x ny samples, spacing cell, first sample at (x0, y0)."""
    def __init__(self, x0, y0, cell, nx, ny):
        self.x0, self.y0, self.cell, self.nx, self.ny = x0, y0, cell, nx, ny

    def xy(self):
        x = self.x0 + np.arange(self.nx) * self.cell
        y = self.y0 + np.arange(self.ny) * self.cell
        return np.meshgrid(x, y)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def blur(a, sigma):
    """Gaussian-ish blur (3 box passes per axis, cumsum, edge-clamped); sigma in cells."""
    if sigma <= 0:
        return a
    r = max(1, int(round(math.sqrt(12 * sigma * sigma / 3 + 1) / 2)))
    out = a.astype(np.float64)
    for axis in (0, 1):
        for _ in range(3):
            pad = [(0, 0), (0, 0)]
            pad[axis] = (r + 1, r)
            c = np.cumsum(np.pad(out, pad, mode="edge"), axis=axis)
            hi = np.take(c, np.arange(2 * r + 1, c.shape[axis]), axis=axis)
            lo = np.take(c, np.arange(0, c.shape[axis] - 2 * r - 1), axis=axis)
            out = (hi - lo) / (2 * r + 1)
    return out


def sample(H, grid, x, y):
    """Bilinear height at world points (clamped to the grid)."""
    u = np.clip((np.asarray(x) - grid.x0) / grid.cell, 0, grid.nx - 1.000001)
    v = np.clip((np.asarray(y) - grid.y0) / grid.cell, 0, grid.ny - 1.000001)
    i, j = np.floor(u).astype(np.int64), np.floor(v).astype(np.int64)
    fu, fv = u - i, v - j
    return (H[j, i] * (1 - fu) * (1 - fv) + H[j, i + 1] * fu * (1 - fv)
            + H[j + 1, i] * (1 - fu) * fv + H[j + 1, i + 1] * fu * fv)


def height_at(H, grid, x, y):
    """Exact height of the LOD0 mesh (and the collider) at world (x, y): each cell is split along
    its (i, j)-(i+1, j+1) diagonal, the same triangulation the chunks use."""
    u = np.clip((np.asarray(x, float) - grid.x0) / grid.cell, 0, grid.nx - 1.000001)
    v = np.clip((np.asarray(y, float) - grid.y0) / grid.cell, 0, grid.ny - 1.000001)
    i, j = np.floor(u).astype(np.int64), np.floor(v).astype(np.int64)
    fu, fv = u - i, v - j
    a, b, c, d = H[j, i], H[j, i + 1], H[j + 1, i + 1], H[j + 1, i]
    return np.where(fu >= fv, a + (b - a) * fu + (c - b) * fv, a + (c - d) * fu + (d - a) * fv)


def shift(a, dy, dx, fill=None):
    """a shifted so out[j, i] = a[j + dy, i + dx] (edge-clamped, or `fill`)."""
    ny, nx = a.shape
    if fill is None:
        jj = np.clip(np.arange(ny) + dy, 0, ny - 1)
        ii = np.clip(np.arange(nx) + dx, 0, nx - 1)
        return a[jj][:, ii]
    out = np.full_like(a, fill)
    ys, yd = slice(max(dy, 0), ny + min(dy, 0)), slice(max(-dy, 0), ny + min(-dy, 0))
    xs, xd = slice(max(dx, 0), nx + min(dx, 0)), slice(max(-dx, 0), nx + min(-dx, 0))
    out[yd, xd] = a[ys, xs]
    return out


N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


# --------------------------------------------------------------------------------- noise
class Noise:
    """2-D gradient (Perlin) noise evaluated at arbitrary world points, so the fine field and
    the coarse backdrop share the same function and meet without a seam."""
    def __init__(self, seed):
        rng = np.random.default_rng(seed)
        perm = rng.permutation(256)
        self.perm = np.concatenate([perm, perm]).astype(np.int64)
        ang = rng.uniform(0, 2 * np.pi, 256)
        self.gx, self.gy = np.cos(ang), np.sin(ang)
        self.offsets = rng.uniform(-1000, 1000, (32, 2))

    def perlin(self, x, y):
        xf, yf = np.floor(x), np.floor(y)
        fx, fy = x - xf, y - yf
        xi, yi = xf.astype(np.int64) & 255, yf.astype(np.int64) & 255
        xj, yj = (xi + 1) & 255, (yi + 1) & 255
        p, gx, gy = self.perm, self.gx, self.gy

        def g(ix, iy, dx, dy):
            h = p[p[ix] + iy]
            return gx[h] * dx + gy[h] * dy
        u = fx * fx * fx * (fx * (fx * 6 - 15) + 10)
        v = fy * fy * fy * (fy * (fy * 6 - 15) + 10)
        n0 = g(xi, yi, fx, fy) * (1 - u) + g(xj, yi, fx - 1, fy) * u
        n1 = g(xi, yj, fx, fy - 1) * (1 - u) + g(xj, yj, fx - 1, fy - 1) * u
        return (n0 * (1 - v) + n1 * v) * 1.41

    def _oct(self, X, Y, k, freq):
        a = 0.6 + 1.618 * k                      # rotate every octave: no lattice alignment
        ca, sa = math.cos(a), math.sin(a)
        ox, oy = self.offsets[k % 32]
        return (X * ca - Y * sa) * freq + ox, (X * sa + Y * ca) * freq + oy

    def fbm(self, X, Y, wavelength, octaves, gain=0.5, lac=2.0):
        out, amp, freq, norm = np.zeros_like(X), 1.0, 1.0 / wavelength, 0.0
        for k in range(octaves):
            u, v = self._oct(X, Y, k, freq)
            out += amp * self.perlin(u, v)
            norm += amp
            amp *= gain
            freq *= lac
        return out / norm

    def ridged(self, X, Y, wavelength, octaves, gain=0.5, lac=2.0):
        """Musgrave ridged multifractal, 0..~1: sharp crests, eroded-looking valleys."""
        out, amp, freq, weight, norm = np.zeros_like(X), 1.0, 1.0 / wavelength, np.ones_like(X), 0.0
        for k in range(octaves):
            u, v = self._oct(X, Y, k + 11, freq)
            s = (1.0 - np.abs(self.perlin(u, v))) ** 2
            s *= weight
            weight = np.clip(s * 2.0, 0, 1)
            out += amp * s
            norm += amp
            amp *= gain
            freq *= lac
        return out / norm


# --------------------------------------------------------------------------------- splines
def spline(points, step):
    """Catmull-Rom through points (n, k) (x, y, attributes...), resampled ~every `step` m."""
    pts = np.asarray(points, float)
    if len(pts) < 3:
        n = max(2, int(np.hypot(*(pts[-1, :2] - pts[0, :2])) / step) + 1)
        t = np.linspace(0, 1, n)[:, None]
        return pts[0] * (1 - t) + pts[-1] * t
    ext = np.vstack([2 * pts[0] - pts[1], pts, 2 * pts[-1] - pts[-2]])
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        n = max(2, int(np.hypot(*(p2[:2] - p1[:2])) / step))
        t = np.linspace(0, 1, n, endpoint=False)[:, None]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1:])
    return np.vstack(out)


def poly_field(grid, pts, radius):
    """Distance from every sample within `radius` of the polyline pts (n, k) to it.
    Returns d (inf beyond radius), attrs (ny, nx, k-2) at the nearest point, s (arc length there),
    side (+1 right / -1 left of the direction of travel)."""
    ny, nx, k = grid.ny, grid.nx, pts.shape[1]
    d = np.full((ny, nx), np.inf)
    attrs = np.zeros((ny, nx, max(k - 2, 1)))
    s_at = np.zeros((ny, nx))
    side = np.zeros((ny, nx))
    seg = np.hypot(*(pts[1:, :2] - pts[:-1, :2]).T)
    cum = np.concatenate([[0], np.cumsum(seg)])
    for a, b, L, s0 in zip(pts[:-1], pts[1:], seg, cum[:-1]):
        lo, hi = np.minimum(a[:2], b[:2]) - radius, np.maximum(a[:2], b[:2]) + radius
        i0, i1 = max(0, int((lo[0] - grid.x0) / grid.cell)), min(nx, int((hi[0] - grid.x0) / grid.cell) + 2)
        j0, j1 = max(0, int((lo[1] - grid.y0) / grid.cell)), min(ny, int((hi[1] - grid.y0) / grid.cell) + 2)
        if i0 >= i1 or j0 >= j1 or L < 1e-9:
            continue
        X = (grid.x0 + np.arange(i0, i1) * grid.cell)[None, :]
        Y = (grid.y0 + np.arange(j0, j1) * grid.cell)[:, None]
        ab = b[:2] - a[:2]
        t = np.clip(((X - a[0]) * ab[0] + (Y - a[1]) * ab[1]) / (L * L), 0, 1)
        dist = np.hypot(a[0] + t * ab[0] - X, a[1] + t * ab[1] - Y)
        sub = d[j0:j1, i0:i1]
        better = (dist < sub) & (dist <= radius)
        if not better.any():
            continue
        sub[better] = dist[better]
        if k > 2:
            attrs[j0:j1, i0:i1][better] = (a[2:] + t[..., None] * (b[2:] - a[2:]))[better]
        s_at[j0:j1, i0:i1][better] = (s0 + t * L)[better]
        cross = ab[0] * (Y - a[1]) - ab[1] * (X - a[0])
        side[j0:j1, i0:i1][better] = np.where(cross > 0, -1.0, 1.0)[better]
    return d, attrs, s_at, side


def ellipse_t(X, Y, center, radius, angle):
    a = math.radians(angle)
    dx, dy = X - center[0], Y - center[1]
    u = (dx * math.cos(a) + dy * math.sin(a)) / radius[0]
    v = (-dx * math.sin(a) + dy * math.cos(a)) / radius[1]
    return np.sqrt(u * u + v * v)


# --------------------------------------------------------------------------------- 1-2 forms
def macro(p, grid, noise):
    """Authored large forms + tilt + fractal detail. Returns (height, mountain mask)."""
    X, Y = grid.xy()
    jitter = p["shape_jitter"] * noise.fbm(X, Y, 260.0, 4)
    H = p["base"] + p["tilt"][0] * X + p["tilt"][1] * (Y + p["size"] / 2)
    ridges = np.zeros_like(X)
    peak = 1e-6
    for sh in p["shapes"]:
        if sh["kind"] in ("ridge", "valley"):
            pts = spline(sh["points"], 15.0)
            r = pts[:, 3].max() / 2 + abs(p["shape_jitter"]) + 5
            d, at, _, _ = poly_field(grid, pts, r)
            t = np.clip((d + jitter) / (at[..., 1] / 2 + 1e-6), 0, 1)
            prof = np.where(np.isfinite(d), (1 - t * t) ** 2, 0.0) * at[..., 0]
            if sh["kind"] == "ridge":
                prof = prof ** sh.get("sharp", 1.0) / at[..., 0].clip(1e-6) ** (sh.get("sharp", 1.0) - 1)
                ridges = np.maximum(ridges, prof)
                peak = max(peak, pts[:, 2].max())
            else:
                H -= prof
        elif sh["kind"] == "basin":
            t = np.clip(ellipse_t(X, Y, sh["center"], sh["radius"], sh.get("angle", 0)) + jitter / max(sh["radius"]), 0, 1)
            H -= sh["depth"] * (1 - t * t) ** 2
        elif sh["kind"] == "plateau":
            t = ellipse_t(X, Y, sh["center"], sh["radius"], sh.get("angle", 0)) + jitter / max(sh["radius"])
            e = sh.get("edge", 0.3)
            H += sh["height"] * (1 - smoothstep(1 - e, 1 + e * 0.5, t))
    H += ridges
    if p.get("guide"):
        g = np.load(p["guide"]) if p["guide"].endswith(".npy") else read_png(p["guide"])
        gg = Grid(-p["size"] / 2, -p["size"] / 2, p["size"] / (g.shape[1] - 1), g.shape[1], g.shape[0])
        H += p["guide_height"] * sample(g, gg, X, Y)
    dp = p["detail"]
    m = smoothstep(dp["mountain"][0], dp["mountain"][1], ridges / peak)
    wx = dp["warp"] * noise.fbm(X + 311, Y - 97, dp["warp_wavelength"], 4)
    wy = dp["warp"] * noise.fbm(X - 523, Y + 211, dp["warp_wavelength"], 4)
    Xw, Yw = X + wx, Y + wy
    H += dp["low_amp"] * noise.fbm(Xw, Yw, dp["low_wavelength"], dp["low_octaves"]) * (1 - 0.5 * m)
    H += dp["high_amp"] * (noise.ridged(Xw, Yw, dp["high_wavelength"], dp["high_octaves"]) - 0.35) * m
    return H, m


# --------------------------------------------------------------------------------- hydrology core
def priority_flood(Z, eps):
    """Epsilon priority-flood (Barnes et al. 2014): the lowest surface >= Z that drains to the
    border, with every filled cell eps above the one it drains to (so D8 routes across lakes)."""
    ny, nx = Z.shape
    W = np.pad(Z.astype(np.float64), 1, constant_values=-np.inf)
    nxp = nx + 2
    closed = np.zeros(W.shape, np.bool_)
    closed[0, :] = closed[-1, :] = closed[:, 0] = closed[:, -1] = True
    border = np.zeros((ny, nx), np.bool_)
    border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
    jj, ii = np.nonzero(border)
    idx = (jj + 1) * nxp + ii + 1
    closed.ravel()[idx] = True
    w = W.ravel().tolist()
    cl = bytearray(closed.ravel().tobytes())
    heap = [(w[i], i) for i in idx.tolist()]
    heapq.heapify(heap)
    offs = [dy * nxp + dx for dy, dx in N8]
    pop, push = heapq.heappop, heapq.heappush
    while heap:
        h, i = pop(heap)
        for o in offs:
            j = i + o
            if cl[j]:
                continue
            cl[j] = 1
            hj = w[j]
            if hj <= h:
                hj = h + eps
                w[j] = hj
            push(heap, (hj, j))
    return np.array(w).reshape(ny + 2, nxp)[1:-1, 1:-1]


def d8(W, cell):
    """Steepest-descent receiver (flat index; itself at outlets) and its distance."""
    ny, nx = W.shape
    best = np.zeros_like(W)
    rec = np.arange(W.size).reshape(ny, nx)
    dist = np.full_like(W, cell)
    jj, ii = np.mgrid[0:ny, 0:nx]
    for dy, dx in N8:
        L = cell * math.hypot(dy, dx)
        s = (W - shift(W, dy, dx, fill=np.inf)) / L
        better = s > best
        best = np.where(better, s, best)
        rec = np.where(better, (jj + dy) * nx + ii + dx, rec)
        dist = np.where(better, L, dist)
    return rec.ravel(), dist.ravel()


def accumulate(W, rec, extra=None):
    """Cells draining through each cell (D8), in height-descending order. `extra`: {flat index:
    cells} added where a river enters from outside the grid (hydro.inflows)."""
    order = np.argsort(-W.ravel(), kind="stable").tolist()
    acc = [1.0] * W.size
    for k, v in (extra or {}).items():
        acc[k] += v
    r = rec.tolist()
    for i in order:
        j = r[i]
        if j != i:
            acc[j] += acc[i]
    return np.array(acc).reshape(W.shape)


def nearest_seed(mask):
    """Jump-flood: for every cell, (row, col) of the nearest True cell of mask and the distance
    in cells (inf when mask is empty)."""
    ny, nx = mask.shape
    jj, ii = np.mgrid[0:ny, 0:nx].astype(np.int32)
    sy = np.where(mask, jj, -1).astype(np.int32)
    sx = np.where(mask, ii, -1).astype(np.int32)
    big = np.float32(3e9)
    best = np.where(mask, 0, big).astype(np.float32)
    k = 1 << int(math.ceil(math.log2(max(nx, ny))))
    steps = []
    while k >= 1:
        k //= 2
        if k:
            steps.append(k)
    for k in steps + [1]:
        for dy, dx in N8:
            cy = shift(sy, dy * k, dx * k, fill=-1)
            cx = shift(sx, dy * k, dx * k, fill=-1)
            d2 = ((jj - cy).astype(np.float32) ** 2 + (ii - cx).astype(np.float32) ** 2)
            better = (cy >= 0) & (d2 < best)
            best = np.where(better, d2, best)
            sy = np.where(better, cy, sy)
            sx = np.where(better, cx, sx)
    return sy, sx, np.where(best >= big, np.inf, np.sqrt(best))


def label(mask):
    """Connected components (8-neighbour) of mask: label = smallest flat index in the component,
    -1 outside. Min-propagation with pointer jumping (vectorised)."""
    n = mask.size
    lab = np.where(mask.ravel(), np.arange(n), n).reshape(mask.shape)
    while True:
        new = lab
        for dy, dx in N8:
            new = np.minimum(new, np.where(mask, shift(lab, dy, dx, fill=n), n))
        flat = new.ravel()
        m = flat < n
        flat[m] = flat[flat[m]]
        flat[m] = flat[flat[m]]
        if np.array_equal(new, lab):
            break
        lab = new
    return np.where(mask, lab, -1)


# --------------------------------------------------------------------------------- 3-5 erosion
def fluvial(H, cell, q):
    """Stream-power incision (Braun & Willett 2013 implicit scheme, n = 1) + hillslope diffusion on
    a coarser grid; returns the fine-grid delta. Carves dendritic valley networks that droplets
    alone can't (they only see ~60 m)."""
    f = q["factor"]
    Z = H[::f, ::f].copy()
    Z0 = Z.copy()
    c = cell * f
    for it in range(q["iters"]):
        W = priority_flood(Z, 1e-4)
        rec, dist = d8(W, c)
        A = accumulate(W, rec).ravel() * c * c
        F = (q["k"] * A ** q["m"] / dist).tolist()
        z = W.ravel().tolist()
        r = rec.tolist()
        for i in np.argsort(W.ravel(), kind="stable").tolist():
            j = r[i]
            if j != i:
                z[i] = (z[i] + F[i] * z[j]) / (1 + F[i])
        Zn = np.array(z).reshape(Z.shape)
        lake = W > Z + 1e-3                     # filled basins keep their beds (lakes later)
        Zn = np.where(lake, Z, Zn)
        lap = (shift(Zn, 1, 0) + shift(Zn, -1, 0) + shift(Zn, 0, 1) + shift(Zn, 0, -1) - 4 * Zn)
        Z = Zn + q["diffusion"] * 0.25 * lap
    D = Z - Z0
    return upsample(D, f, H.shape)


def upsample(a, f, shape):
    ny, nx = shape
    yc, xc = np.arange(a.shape[0]) * f, np.arange(a.shape[1]) * f
    rows = np.array([np.interp(np.arange(nx), xc, r) for r in a])
    return np.array([np.interp(np.arange(ny), yc, col) for col in rows.T]).T


def droplets(H, cell, q, rng):
    """Particle hydraulic erosion (Beyer 2015 / Lague), a batch of droplets advanced together:
    each step every droplet samples the bilinear height + gradient, turns with inertia, moves one
    cell, erodes (radius brush) or deposits (bilinear) by its sediment capacity. Heights in m.
    Returns (new heights, deposition field: >0 deposited, <0 eroded)."""
    ny, nx = H.shape
    h = H.ravel().astype(np.float64).copy()
    h0 = h.copy()
    r = q["radius"]
    oy, ox = np.mgrid[-r:r + 1, -r:r + 1]
    wgt = np.maximum(0, r + 0.5 - np.hypot(ox, oy))
    keep = wgt > 0
    oy, ox, wgt = oy[keep], ox[keep], wgt[keep] / wgt[keep].sum()
    total = int(q["per_cell"] * nx * ny)
    nb = max(1, total // q["batch"])
    inertia, cap_k, min_slope = q["inertia"], q["capacity"], q["min_slope"] * cell
    for b in range(nb):
        n = q["batch"]
        px = rng.uniform(r, nx - 1 - r, n)
        py = rng.uniform(r, ny - 1 - r, n)
        dx = np.zeros(n); dy = np.zeros(n)
        speed = np.ones(n); water = np.ones(n); sed = np.zeros(n)
        alive = np.ones(n, bool)
        for step in range(q["lifetime"]):
            ix = px.astype(np.int64); iy = py.astype(np.int64)
            fx = px - ix; fy = py - iy
            i00 = iy * nx + ix
            h00, h10, h01, h11 = h[i00], h[i00 + 1], h[i00 + nx], h[i00 + nx + 1]
            gx = (h10 - h00) * (1 - fy) + (h11 - h01) * fy
            gy = (h01 - h00) * (1 - fx) + (h11 - h10) * fx
            hc = h00 * (1 - fx) * (1 - fy) + h10 * fx * (1 - fy) + h01 * (1 - fx) * fy + h11 * fx * fy
            dx = dx * inertia - gx * (1 - inertia)
            dy = dy * inertia - gy * (1 - inertia)
            L = np.hypot(dx, dy)
            still = L < 1e-9
            if still.any():
                a = rng.uniform(0, 2 * np.pi, still.sum())
                dx[still], dy[still], L[still] = np.cos(a), np.sin(a), 1.0
            dx /= L; dy /= L
            nxp, nyp = px + dx, py + dy
            alive &= (nxp >= r) & (nxp < nx - 1 - r) & (nyp >= r) & (nyp < ny - 1 - r)
            if not alive.any():
                break
            nxp = np.where(alive, nxp, px); nyp = np.where(alive, nyp, py)
            jx = nxp.astype(np.int64); jy = nyp.astype(np.int64)
            gxf, gyf = nxp - jx, nyp - jy
            j00 = jy * nx + jx
            hn = (h[j00] * (1 - gxf) * (1 - gyf) + h[j00 + 1] * gxf * (1 - gyf)
                  + h[j00 + nx] * (1 - gxf) * gyf + h[j00 + nx + 1] * gxf * gyf)
            dh = np.where(alive, hn - hc, 0.0)
            cap = np.maximum(-dh, min_slope) * speed * water * cap_k
            dep_mask = alive & ((sed > cap) | (dh > 0))
            amt_dep = np.where(dep_mask, np.where(dh > 0, np.minimum(dh, sed), (sed - cap) * q["deposit"]), 0.0)
            amt_ero = np.where(alive & ~dep_mask,
                               np.minimum(np.minimum((cap - sed) * q["erode"], -dh), q["max_step"]), 0.0)
            amt_ero = np.maximum(amt_ero, 0.0)
            delta = np.zeros(h.size)
            if dep_mask.any():
                for di, wi in ((0, (1 - fx) * (1 - fy)), (1, fx * (1 - fy)), (nx, (1 - fx) * fy), (nx + 1, fx * fy)):
                    delta += np.bincount(i00 + di, weights=amt_dep * wi, minlength=h.size)
            e = amt_ero > 0
            if e.any():
                cen = (iy[e] * nx + ix[e])
                idx = (cen[:, None] + (oy * nx + ox)[None, :]).ravel()
                delta -= np.bincount(idx, weights=(amt_ero[e][:, None] * wgt[None, :]).ravel(), minlength=h.size)
            h += delta
            sed += amt_ero - amt_dep
            speed = np.sqrt(np.clip(speed * speed - dh * q["gravity"] / cell, 0, 400.0))
            water *= 1 - q["evaporate"]
            px, py = nxp, nyp
    return h.reshape(ny, nx), (h - h0).reshape(ny, nx)


def thermal(H, cell, q):
    """Talus relaxation: material above the talus angle slides to lower neighbours."""
    H = H.copy()
    tan = math.tan(math.radians(q["talus_deg"]))
    T = [tan * cell * math.hypot(dy, dx) for dy, dx in N8]
    for _ in range(q["iters"]):
        ex = [np.maximum(0, H - shift(H, dy, dx) - t) for (dy, dx), t in zip(N8, T)]
        tot = sum(ex)
        mx = np.max(ex, axis=0)
        move = q["rate"] * 0.5 * mx
        frac = np.where(tot > 0, move / np.where(tot > 0, tot, 1), 0)
        out = np.zeros_like(H)
        H = H - move
        for (dy, dx), e in zip(N8, ex):
            out += shift(e * frac, -dy, -dx, fill=0.0)
        H += out
    return H


# --------------------------------------------------------------------------------- 6 cliffs
def apply_cliffs(H, grid, p, noise):
    """Carve a cliff edge along a spline: the edge height is the terrain along the line (smoothed);
    on the high side the ground is kept at least that high, on the low side it drops `height` m
    across `edge` m; below the face the natural ground is lowered by an amount that runs out over
    `runout` m (default 3 x height: the talus apron), never below a talus slope (talus_deg) falling
    from the foot. Ragged by noise, faded at the ends. (The old run-out rose from the foot at the
    talus angle: on a hillside, whose ground keeps falling, that dug a trench the apron fill then
    flooded into a flat disc.)"""
    X, Y = grid.xy()
    out = []
    cliff_mask = np.zeros(H.shape)
    for c in p["cliffs"]:
        pts = spline(c["points"], 3.0)
        ht = sample(H, grid, pts[:, 0], pts[:, 1])
        k = 8
        for _ in range(3):
            ht = np.convolve(np.pad(ht, k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), "valid")
        tal = math.tan(math.radians(c.get("talus_deg", 38.0)))
        R = c.get("runout", 3.0 * c["height"])
        reach = max(c["edge"] + R + c["jitter"] * 2 + 5, c["back"])
        d, at, s, side = poly_field(grid, np.column_stack([pts, ht]), reach)
        total = np.hypot(*(pts[1:, :2] - pts[:-1, :2]).T).sum()
        fin = np.isfinite(d)
        dd = np.where(fin, d, reach)
        sd = dd * side * c["side"] + c["jitter"] * noise.fbm(X, Y, 14.0, 3)  # >0 high side
        top = at[..., 0]
        ends = smoothstep(0, c["end_fade"], s) * smoothstep(0, c["end_fade"], total - s)
        hgt = c["height"] * ends
        low = np.maximum(-sd, 0)
        face = top - hgt * smoothstep(-0.5, c["edge"], low)
        strata = 0.6 * np.sin(face * 1.7) * smoothstep(0.2, 0.8, (top - face) / np.maximum(hgt, 1e-3)) * (hgt > 1)
        beyond = np.maximum(low - c["edge"], 0)
        apron = np.maximum(H - hgt * np.clip(1 - beyond / R, 0, 1) ** 2, top - hgt - beyond * tal)
        Hlow = np.where(low < c["edge"], face + strata, apron)
        Hn = np.where(sd < 0, np.minimum(H, Hlow), np.maximum(H, top - sd * 0.08))
        # (x ends: beyond the line's ends the nearest point is an end point, and without the fade
        # the high-side clamp raised a flat half-disc shelf there and the low side cut a cone)
        w = fin * (1 - smoothstep(reach * 0.8, reach, dd)) * ends
        cliff_mask = np.maximum(cliff_mask, fin * ends * (sd < 0) * (low < c["edge"] + c["jitter"] + 1.5)
                                * smoothstep(0.5, 2.0, H - Hn))
        H = H + (Hn - H) * w
        # the cut must not leave a closed trench at the foot: fill it like a talus apron
        jj, ii = np.nonzero(w > 0)
        if len(jj):
            m = int(40 / grid.cell)
            j0, j1 = max(0, jj.min() - m), min(H.shape[0], jj.max() + m + 1)
            i0, i1 = max(0, ii.min() - m), min(H.shape[1], ii.max() + m + 1)
            win = H[j0:j1, i0:i1]
            filled = priority_flood(win, 0.05)       # ~2 degree apron, drains to the spill
            near = blur((w[j0:j1, i0:i1] > 0).astype(float), 3) > 0.01
            H[j0:j1, i0:i1] = np.where(near, filled, win)
        out.append(dict(name=c["name"], height=c["height"], length=round(float(total), 1)))
    return H, out, cliff_mask


def apply_knicks(H, grid, p):
    """River steps: lower a channel-following band below a lip (see P["knicks"])."""
    out = []
    for k in p.get("knicks", []):
        pts = spline(k["points"], 3.0)
        d, _, s, _ = poly_field(grid, pts, k["width"] / 2)
        fin = np.isfinite(d)
        t = np.clip(np.where(fin, d, 1e9) / (k["width"] / 2), 0, 1)
        across = (1 - t * t) ** 2
        total = np.hypot(*(pts[1:, :2] - pts[:-1, :2]).T).sum()
        along = smoothstep(0, k["lip"], s) * (1 - smoothstep(total - k["fade"], total, s))
        H = H - k["height"] * across * along * fin
        lip = pts[0]
        out.append(dict(name=k["name"], height=k["height"], lip=[round(float(lip[0]), 1), round(float(lip[1]), 1)],
                        length=round(float(total), 1)))
    return H, out


def apply_pools(H, grid, p):
    """Plunge pools of the knicks (after the cliffs, so hydrology fills them into lakes)."""
    X, Y = grid.xy()
    for k in p.get("knicks", []):
        pool = k.get("pool")
        if pool:
            c, r = pool["center"], pool["radius"]
            tt = np.clip(np.hypot(X - c[0], Y - c[1]) / r, 0, 1)
            H = H - pool["depth"] * (1 - tt * tt) ** 2
    return H


# --------------------------------------------------------------------------------- 7 hydrology
def hydrology(H, grid, p, timings):
    q, cell = p["hydro"], grid.cell
    t = time.perf_counter()
    W = priority_flood(H, q["eps"])
    timings["hydro_fill"] = time.perf_counter() - t
    t = time.perf_counter()
    rec, _ = d8(W, cell)
    # inflows: a river entering the square from a catchment outside it (dict(x, y, r, area m²)):
    # its area joins the flow at the lowest filled cell within r of (x, y)
    extra, inflow_info = {}, []
    if q.get("inflows"):
        X, Y = grid.xy()
        for f in q["inflows"]:
            near = np.hypot(X - f["x"], Y - f["y"]) < f["r"]
            k = int(np.argmin(np.where(near, W, np.inf)))
            extra[k] = extra.get(k, 0.0) + f["area"] / (cell * cell)
            inflow_info.append(dict(name=f.get("name", "inflow"), x=round(float(X.ravel()[k]), 1), y=round(float(Y.ravel()[k]), 1),
                                    z=round(float(W.ravel()[k]), 2), area_km2=round(f["area"] / 1e6, 1)))
    acc = accumulate(W, rec, extra)
    timings["hydro_flow"] = time.perf_counter() - t
    t = time.perf_counter()
    A = acc * cell * cell
    # lakes: filled basins deep and big enough; the level sits `freeboard` under the spill
    comp = label(W - H > 0.05)
    lakes, lake_level = [], np.full(H.shape, np.nan)
    ids = np.unique(comp[comp >= 0])
    flat_comp, flat_W, flat_dep = comp.ravel(), W.ravel(), (W - H).ravel()
    order = np.argsort(flat_comp)
    sc = flat_comp[order]
    starts = np.searchsorted(sc, ids)
    ends = np.searchsorted(sc, ids, side="right")
    for cid, a, b in zip(ids, starts, ends):
        cells = order[a:b]
        if (b - a) * cell * cell < q["lake_min_area"] or flat_dep[cells].max() < q["lake_min_depth"]:
            continue
        level = float(flat_W[cells].min()) - q["freeboard"]
        lake_level.ravel()[cells] = level
        lakes.append(dict(level=round(level, 2), cells=int(b - a)))
    in_lake = np.isfinite(lake_level) & (H < lake_level)
    # rivers along the flow network
    seeds = (A >= q["river_area"]) & ~np.isfinite(lake_level)
    width = np.clip(q["width_k"] * np.sqrt(A / 1e6), *q["width"])
    depth = q["depth0"] + q["depth_k"] * width
    sy, sx, dcell = nearest_seed(seeds)
    mq = q.get("meander")
    if mq:
        # meanders: the D8 network runs in straight 45-degree runs. The channel is carved in warped
        # coordinates instead (a smooth displacement field, `amp` m over `wavelength` m), so the bed
        # swings from bank to bank and its width breathes; the displacement fades to zero at the
        # `protect` discs (x, y, r, fade: falls, plunge pool, fords), where authored features sit
        # on the D8 line. Off by default (hydro.meander = None): other levels are unchanged.
        X, Y = grid.xy()
        nzm = Noise(mq.get("seed", 5))
        wx = mq["amp"] * nzm.fbm(X, Y, mq["wavelength"], 2)
        wy = mq["amp"] * nzm.fbm(X + 517.0, Y - 313.0, mq["wavelength"], 2)
        fade = np.ones_like(X)
        for px, py, r, f in mq.get("protect", []):
            fade *= smoothstep(r, r + f, np.hypot(X - px, Y - py))
        wx, wy = wx * fade, wy * fade
        fin = np.isfinite(dcell)
        dw = sample(np.where(fin, dcell, 1e6), grid, X + wx, Y + wy)
        ii = np.clip(np.round((X + wx - grid.x0) / cell), 0, grid.nx - 1).astype(np.int64)
        jj = np.clip(np.round((Y + wy - grid.y0) / cell), 0, grid.ny - 1).astype(np.int64)
        sy, sx = sy[jj, ii], sx[jj, ii]
        dcell = np.where(fin[jj, ii] & (dw < 1e5), dw, np.inf)
    has = np.isfinite(dcell)
    sy, sx = np.where(has, sy, 0), np.where(has, sx, 0)
    d = dcell * cell
    hw = width[sy, sx] / 2
    ground = W[sy, sx]
    level = ground - q["bank_drop"]
    bed = level - depth[sy, sx]
    inner = np.clip(d / np.maximum(hw, 1e-6), 0, 1)
    T = np.where(d <= hw, bed + (ground - bed) * inner ** 2,
                 ground + (d - hw) * math.tan(math.radians(q["bank_deg"])))
    blend = 1 - smoothstep(hw + q["bank_w"] * 0.5, hw + q["bank_w"], d)
    carve = has & (d < hw + q["bank_w"])
    Hn = np.where(carve, H + (np.minimum(H, T) - H) * blend, H)
    # banks: soften the band beside the channel (not the bed)
    band = carve & (d > hw)
    Hb = blur(Hn, 1.5)
    Hn = np.where(band, Hn + (np.minimum(Hb, Hn) - Hn) * blend, Hn)
    # floodplain and gravel bars (hydro.floodplain = dict(width, rise, max_above, min_width)): beside
    # a big channel, ground that sits only a little above the water is levelled into a gently rising
    # bench (bars on the insides of bends, the flats where the valley opens); steep banks keep theirs
    fq = q.get("floodplain")
    bars = np.zeros(H.shape, bool)
    if fq:
        big = has & (hw * 2 >= fq.get("min_width", 15.0))
        above = Hn - level
        fpw = fq["width"] * np.clip(hw / 15.0, 0.5, 1.2)
        zone = big & (d > hw * 0.8) & (d < hw + fpw) & (above < fq["max_above"])
        target = level + 0.35 + (d - hw).clip(0) * fq["rise"]
        wgt = (1 - smoothstep(hw + fpw * 0.6, hw + fpw, d)) * (1 - smoothstep(fq["max_above"] * 0.6, fq["max_above"], above))
        Hn = np.where(zone, Hn + (np.minimum(Hn, target) - Hn) * wgt, Hn)
        bars = zone & (wgt > 0.3)
    channel_T = np.where(has & (d < hw), T, np.inf)          # kept for fords
    river_level = np.where(has & (d < hw + cell), level, np.nan)
    m = np.isfinite(river_level)
    num = blur(np.where(m, river_level, 0), 2.0)
    den = blur(m.astype(float), 2.0)
    river_level = np.where(m, num / np.maximum(den, 1e-6), np.nan)
    # lake shores: shelf under the water, beach above it
    if lakes:
        lake_mask = np.isfinite(lake_level) & (Hn < lake_level)
        lv = np.where(np.isfinite(lake_level), lake_level, 0)
        ly, lx, dout = nearest_seed(lake_mask)
        dout = dout * cell
        lev_near = np.where(np.isfinite(dout), lv[np.where(np.isfinite(dout), ly, 0), np.where(np.isfinite(dout), lx, 0)], 0)
        beach = np.isfinite(dout) & (dout > 0) & (dout < q["beach_w"]) & (Hn - lev_near < 3.0)
        target = lev_near + 0.05 + dout * math.tan(math.radians(q["beach_deg"]))
        wb = 1 - smoothstep(q["beach_w"] * 0.5, q["beach_w"], dout)
        Hn = np.where(beach, Hn + (np.minimum(Hn, target) - Hn) * wb, Hn)
        _, _, din = nearest_seed(~lake_mask)
        din = din * cell
        shelf = lake_mask & (din < 15)
        Hn = np.where(shelf, np.minimum(Hn, lv - 0.15 - din * math.tan(math.radians(q["shelf_deg"]))), Hn)
    timings["hydro_carve"] = time.perf_counter() - t
    rivers_mask = has & (d < hw)
    info = dict(lakes=lakes, river_cells=int(seeds.sum()), inflows=inflow_info, bar_cells=int(bars.sum()),
                river_length_m=round(float(seeds.sum() * cell * 1.2), 0),
                max_width=round(float(width[seeds].max()) if seeds.any() else 0, 1))
    return Hn, dict(W=W, acc=acc, lake_level=lake_level, river_level=river_level, bars=bars,
                    channel_T=channel_T, rivers=rivers_mask, river_d=d, river_hw=hw, info=info)


# --------------------------------------------------------------------------------- 8 hooks
def bank_clamp(H, target, d, core, bank_deg, shoulder, cut_deg=50.0):
    """Delta that pulls H onto `target` inside `core` and clamps it to banks beyond: fills no
    steeper than bank_deg, cuts no steeper than cut_deg; rounded over `shoulder` m."""
    e = np.maximum(d - core, 0)
    clamped = np.clip(H, target - e * math.tan(math.radians(bank_deg)), target + e * math.tan(math.radians(cut_deg)))
    delta = np.where(np.isfinite(d), clamped - H, 0)
    soft = blur(delta, max(0.5, shoulder / 6 / 1.5))
    return delta + (soft - delta) * smoothstep(core, core + shoulder * 0.5, d)


def apply_pads(H, grid, p):
    """Flatten a disc (radius) or a rectangle (half=(hx, hy)) at its median height (or `height`).
    Fills / cuts run out at bank_deg / cut_deg, but only within `reach` m of the pad's centre
    (default radius + 2 falloff + 20 m), faded over its last 15%: without a reach a pad on a summit
    propped up every slope steeper than bank_deg for hundreds of metres around it."""
    X, Y = grid.xy()
    out = []
    for pad in p["pads"]:
        cx, cy = pad["center"]
        if pad.get("half"):
            hx, hy = pad["half"]
            ex, ey = np.abs(X - cx) - hx, np.abs(Y - cy) - hy
            d = np.hypot(np.maximum(ex, 0), np.maximum(ey, 0))     # 0 inside the rectangle
            core, size = 0.0, max(hx, hy)
        else:
            d = np.hypot(X - cx, Y - cy)
            core = size = pad["radius"]
        reach = pad.get("reach", size + 2 * pad["falloff"] + 20.0)
        inside = d <= core
        hgt = pad.get("height")
        if hgt is None:
            hgt = float(np.median(H[inside]))
        dist = np.hypot(X - cx, Y - cy) if pad.get("half") is None else d + size
        dd = np.where(dist <= reach, d, np.inf)
        delta = bank_clamp(H, hgt, dd, core, pad.get("bank_deg", 33.0), pad["falloff"], pad.get("cut_deg", 50.0))
        H = H + delta * (1 - smoothstep(reach * 0.85, reach, dist))
        out.append(dict(name=pad["name"], center=list(pad["center"]), radius=pad.get("radius"), half=pad.get("half"),
                        reach=round(reach, 1), height=round(hgt, 2)))
    return H, out


def corridor(H, grid, pts, hp, core, bank_deg, reach, shoulder, cut_deg=50.0):
    """Height change that puts a corridor in: within `core` of the path the ground is the path
    height, beyond it the ground is clamped between the lower / upper envelopes of banks at
    bank_deg rising and falling from EVERY path point (so stacked switchback legs cut and fill
    consistently); where two legs' envelopes conflict the nearer leg wins. Rounded by a blur."""
    tanb, tanc = math.tan(math.radians(bank_deg)), math.tan(math.radians(cut_deg))
    q = np.column_stack([pts, hp])
    q = q[::max(1, int(4.0 / grid.cell))]
    if not np.allclose(q[-1], np.column_stack([pts, hp])[-1]):
        q = np.vstack([q, np.column_stack([pts, hp])[-1:]])
    ny, nx = H.shape
    U, L = np.full(H.shape, np.inf), np.full(H.shape, -np.inf)
    dmin, near_h = np.full(H.shape, np.inf), np.zeros(H.shape)
    for a, b in zip(q[:-1], q[1:]):
        lo, hi = np.minimum(a[:2], b[:2]) - reach, np.maximum(a[:2], b[:2]) + reach
        i0, i1 = max(0, int((lo[0] - grid.x0) / grid.cell)), min(nx, int((hi[0] - grid.x0) / grid.cell) + 2)
        j0, j1 = max(0, int((lo[1] - grid.y0) / grid.cell)), min(ny, int((hi[1] - grid.y0) / grid.cell) + 2)
        if i0 >= i1 or j0 >= j1:
            continue
        X = (grid.x0 + np.arange(i0, i1) * grid.cell)[None, :]
        Y = (grid.y0 + np.arange(j0, j1) * grid.cell)[:, None]
        ab = b[:2] - a[:2]
        L2 = max(float(ab @ ab), 1e-9)
        t = np.clip(((X - a[0]) * ab[0] + (Y - a[1]) * ab[1]) / L2, 0, 1)
        dist = np.hypot(a[0] + t * ab[0] - X, a[1] + t * ab[1] - Y)
        h = a[2] + t * (b[2] - a[2])
        e = np.maximum(dist - core, 0)
        ok = dist <= reach
        sl = (slice(j0, j1), slice(i0, i1))
        U[sl] = np.minimum(U[sl], np.where(ok, h + e * tanc, np.inf))
        L[sl] = np.maximum(L[sl], np.where(ok, h - e * tanb, -np.inf))
        nearer = dist < dmin[sl]
        dmin[sl] = np.where(nearer, dist, dmin[sl])
        near_h[sl] = np.where(nearer, h, near_h[sl])
    e = np.maximum(dmin - core, 0)
    conflict = L > U
    Z = np.where(conflict, np.clip(H, near_h - e * tanb, near_h + e * tanc), np.clip(H, L, U))
    Z = np.where(np.isfinite(dmin), Z, H)
    raw = Z - H
    # round the bank shoulders, but keep the walking surface (core) exact
    soft = blur(raw, max(0.5, shoulder / 6 / grid.cell))
    k = smoothstep(core, core + shoulder * 0.5, np.where(np.isfinite(dmin), dmin, 1e9))
    delta = raw + (soft - raw) * k
    return delta * (1 - smoothstep(reach * 0.85, reach, np.where(np.isfinite(dmin), dmin, reach)))


def path_profile(H, grid, points, path, water=None):
    """The corridor's height profile along a path: the spline through `points` (every cell), the
    terrain under it (h), box-smoothed over `smooth` m (hs), then grade-limited by forward and
    backward Lipschitz passes, averaged (hp: |dh/ds| <= max_grade)."""
    pts = spline([(x, y) for x, y in points], grid.cell)
    seg = np.hypot(*(pts[1:, :2] - pts[:-1, :2]).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    h = sample(H, grid, pts[:, 0], pts[:, 1])
    k = max(1, int(path["smooth"] / grid.cell / 2))
    if path.get("river_offset") is not None and water is not None:
        # a riverside road / rail grade: graded off the nearest river's water level (+ offset), not
        # the bumpy bank, so it cuts through the spurs and fills across the side gullies
        hw = sample(water, grid, pts[:, 0], pts[:, 1]) + path["river_offset"]
        hs = hw.copy()
        for _ in range(3):
            pad = np.pad(hs, k * 3, mode="edge")
            c = np.cumsum(np.concatenate([[0], pad]))
            hs = (c[6 * k + 1:] - c[:-6 * k - 1]) / (6 * k + 1)
        g = path["max_grade"]
        fw, bw = hs.copy(), hs.copy()
        for i in range(1, len(hs)):
            fw[i] = np.clip(fw[i], fw[i - 1] - g * seg[i - 1], fw[i - 1] + g * seg[i - 1])
        if path.get("grade_from") == "start":
            # (graded on from the start only: where the river drops faster than the grade, e.g. into a
            # gorge, the road holds its line on the valley side above it)
            return pts, seg, s, h, hs, fw
        for i in range(len(hs) - 2, -1, -1):
            bw[i] = np.clip(bw[i], bw[i + 1] - g * seg[i], bw[i + 1] + g * seg[i])
        return pts, seg, s, h, hs, (fw + bw) / 2
    hs = h.copy()
    for _ in range(3):
        pad = np.pad(hs, k, mode="edge")
        c = np.cumsum(np.concatenate([[0], pad]))
        hs = (c[2 * k + 1:] - c[:-2 * k - 1]) / (2 * k + 1)
    g = path["max_grade"]
    fw, bw = hs.copy(), hs.copy()
    for i in range(1, len(hs)):
        fw[i] = np.clip(fw[i], fw[i - 1] - g * seg[i - 1], fw[i - 1] + g * seg[i - 1])
    for i in range(len(hs) - 2, -1, -1):
        bw[i] = np.clip(bw[i], bw[i + 1] - g * seg[i], bw[i + 1] + g * seg[i])
    hp = (fw + bw) / 2
    return pts, seg, s, h, hs, hp


def _simplify(P, tol):
    """Douglas-Peucker on a polyline (n, 2)."""
    keep = np.zeros(len(P), bool); keep[[0, -1]] = True
    stack = [(0, len(P) - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        ab = P[b] - P[a]; L = np.hypot(*ab) + 1e-9
        d = np.abs(ab[0] * (P[a + 1:b, 1] - P[a, 1]) - ab[1] * (P[a + 1:b, 0] - P[a, 0])) / L
        k = int(np.argmax(d))
        if d[k] > tol:
            keep[a + 1 + k] = True
            stack += [(a, a + 1 + k), (a + 1 + k, b)]
    return P[keep]


# 32 headings: every lattice step (dx, dy) with max(|dx|, |dy|) <= 3 and gcd 1 (at most 18 deg
# apart). On 35-45 deg slopes a 20% trail runs only 12-18 deg off the contour, which 16 headings
# often can't hit.
_DIRS = sorted({(dx // math.gcd(dx, dy), dy // math.gcd(dx, dy)) for dx in range(-3, 4) for dy in range(-3, 4)
                if (dx or dy)}, key=lambda d: math.atan2(d[1], d[0]))


def route_switchbacks(Hb, grid, A, B, g, half_width, avoid=None, rc=3.0, turn_m=40.0, end_m=15.0, end_grade=2.5):
    """Shortest trail from A to B whose every step is no steeper than g, inside a band of
    half_width m around the line A-B: A* over (cell, heading) on an rc-metre lattice with 16
    headings; cost = length + turn_m x (1 - cos turn) (so a hairpin costs 2 turn_m: as few as the
    band allows) + a penalty on `avoid` cells (water). Where the straight line is too steep this
    is a switchback stack along the contours, on any shape of ground (draws, spurs, cliff ends).
    Within end_m of A and B steps may be end_grade x steeper (a creek bank, a pad's edge).
    Returns ((n, 2) polyline, hairpins) or None."""
    A, B = np.asarray(A, float), np.asarray(B, float)
    L = float(np.hypot(*(B - A)))
    axis = (B - A) / max(L, 1e-9)
    perp = np.array([-axis[1], axis[0]])
    m = half_width + 10.0
    x0, x1 = min(A[0], B[0]) - m, max(A[0], B[0]) + m
    y0, y1 = min(A[1], B[1]) - m, max(A[1], B[1]) + m
    nx, ny = int((x1 - x0) / rc) + 2, int((y1 - y0) / rc) + 2
    X = x0 + np.arange(nx) * rc
    Y = y0 + np.arange(ny) * rc
    XX, YY = np.meshgrid(X, Y)
    Z = sample(Hb, grid, XX, YY)
    rel_x, rel_y = XX - A[0], YY - A[1]
    along = rel_x * axis[0] + rel_y * axis[1]
    lat = rel_x * perp[0] + rel_y * perp[1]
    band = (np.abs(lat) <= half_width) & (along >= -half_width * 0.5) & (along <= L + half_width * 0.5)
    pen = np.zeros(Z.shape)
    if avoid is not None:
        pen = np.where(sample(avoid.astype(float), grid, XX, YY) > 0.3, 25.0, 0.0)
    band &= (XX > grid.x0 + 3) & (XX < grid.x0 + (grid.nx - 1) * grid.cell - 3)
    band &= (YY > grid.y0 + 3) & (YY < grid.y0 + (grid.ny - 1) * grid.cell - 3)
    sa = (int(round((A[1] - y0) / rc)), int(round((A[0] - x0) / rc)))
    sb = (int(round((B[1] - y0) / rc)), int(round((B[0] - x0) / rc)))
    band[sa] = band[sb] = True
    near_end = (np.hypot(XX - A[0], YY - A[1]) < end_m) | (np.hypot(XX - B[0], YY - B[1]) < end_m)
    gl = np.where(near_end, g * end_grade, g).tolist()
    dirs = [(dy, dx, rc * math.hypot(dx, dy), math.atan2(dy, dx)) for dx, dy in _DIRS]
    mids = [[(round(dy * t / max(abs(dx), abs(dy))), round(dx * t / max(abs(dx), abs(dy))))
             for t in range(1, max(abs(dx), abs(dy)))] for dx, dy in _DIRS]
    cosd = np.array([[math.cos(a[3] - b[3]) for b in dirs] for a in dirs])
    zl, bl, pl = Z.tolist(), band.tolist(), pen.tolist()
    hB = zl[sb[0]][sb[1]]
    nd = len(dirs)
    INF = float("inf")
    best = {}
    heap = []
    for k in range(nd):
        st = (sa[0], sa[1], k)
        best[st] = 0.0
        heap.append((0.0, 0.0, st, None))
    came = {}
    goal = None
    pops = 0
    while heap:
        f, cost, st, parent = heapq.heappop(heap)
        if best.get(st, INF) < cost - 1e-9:
            continue
        if st in came:
            continue
        came[st] = parent
        pops += 1
        if pops > 600000:
            break
        j, i, k = st
        if (j, i) == sb:
            goal = st
            break
        hz = zl[j][i]
        gj = gl[j][i]
        for k2, (dy, dx, Lm, _) in enumerate(dirs):
            j2, i2 = j + dy, i + dx
            if j2 < 0 or i2 < 0 or j2 >= ny or i2 >= nx or not bl[j2][i2]:
                continue
            h2 = zl[j2][i2]
            gg = max(gj, gl[j2][i2])
            if abs(h2 - hz) > gg * Lm:
                continue
            bad = False                               # long steps: the cells passed (no jumping a ledge)
            for (mj, mi) in mids[k2]:
                if abs(zl[j + mj][i + mi] - hz) > gg * Lm * 0.85 or not bl[j + mj][i + mi]:
                    bad = True
                    break
            if bad:
                continue
            c2 = cost + Lm + turn_m * (1.0 - cosd[k][k2]) + pl[j2][i2]
            st2 = (j2, i2, k2)
            if c2 < best.get(st2, INF) - 1e-9:
                best[st2] = c2
                dist = math.hypot((sb[0] - j2) * rc, (sb[1] - i2) * rc)
                hh = max(dist, abs(hB - h2) / g)
                heapq.heappush(heap, (c2 + hh, c2, st2, st))
    if goal is None:
        route_switchbacks.fail = f"no route within {half_width:.0f} m of the line ({pops} states)"
        return None
    cells, st = [], goal
    while st is not None:
        cells.append(st)
        st = came[st]
    cells.reverse()
    line = np.array([(X[i], Y[j]) for j, i, _ in cells])
    line[0], line[-1] = A, B
    heads = [k for _, _, k in cells[1:]]
    hairpins = sum(1 for a, b in zip(heads[:-1], heads[1:]) if cosd[a][b] < -0.3)
    # (hairpins counted as heading reversals between consecutive steps; a turn spread over a few
    # steps is counted by the drift of the lateral direction instead)
    latv = (line - A) @ perp
    flips = int(np.sum(np.abs(np.diff(np.sign(np.diff(latv[::3])))) > 1))
    return line, max(hairpins, flips)


def _excess_window(hs, s, g):
    """The stretch of a profile that climbs (or drops) furthest beyond what grade g allows:
    max over i <= j of |hs[j] - hs[i]| - g (s[j] - s[i]). Returns (excess m, i, j)."""
    best = (0.0, 0, 0)
    for sign in (1.0, -1.0):
        f = sign * hs - g * s
        m, am = np.inf, 0
        e = np.zeros(len(f)); arg = np.zeros(len(f), np.int64)
        for k in range(len(f)):                  # running minimum and where it is
            if f[k] < m:
                m, am = f[k], k
            e[k], arg[k] = f[k] - m, am
        j = int(np.argmax(e))
        if e[j] > best[0]:
            best = (float(e[j]), int(arg[j]), j)
    return best


def plan_switchbacks(H, grid, path, max_cut=3.0, half_width=50.0, max_sections=10, blur_m=12.0, avoid=None):
    """Where the ground climbs (or drops) faster than max_grade allows by more than max_cut m
    over some stretch (_excess_window), replace that stretch of the authored polyline by a
    switchback stack traced along the contours (trace_switchbacks), and repeat. The corridor
    then follows the ground instead of cutting or filling it. Returns (points, report)."""
    pts0 = [tuple(q[:2]) for q in path["points"]]
    Hb = blur(H, blur_m / grid.cell / 1.5)
    g = path["max_grade"]
    report = []
    for _ in range(max_sections):
        pts, seg, s, h, hs, hp = path_profile(H, grid, pts0, path)
        E, i0, i1 = _excess_window(hs, s, g)
        if E <= max_cut:
            break
        m = int(10.0 / grid.cell)
        i0, i1 = max(0, i0 - m), min(len(s) - 1, i1 + m)
        A, B = pts[i0, :2], pts[i1, :2]
        rec = dict(excess_m=round(E, 1), section=[[round(float(v), 1) for v in A], [round(float(v), 1) for v in B]],
                   rise_m=round(float(hs[i1] - hs[i0]), 1), length_m=round(float(s[i1] - s[i0]), 1))
        tr = None
        for wmul in (1.0, 1.6, 2.5):
            tr = route_switchbacks(Hb, grid, A, B, g * 0.92, half_width * wmul, avoid)
            if tr is not None:
                rec["half_width_m"] = half_width * wmul
                break
        if tr is None:
            report.append(dict(rec, result="no route: " + getattr(route_switchbacks, "fail", "?")))
            break
        line, legs = tr
        line = _simplify(line, 1.0)
        cs = np.array([s[int(np.argmin(np.hypot(pts[:, 0] - q[0], pts[:, 1] - q[1])))] for q in pts0])
        new = ([q for q, c in zip(pts0, cs) if c < s[i0] - 1.0] + [tuple(q) for q in line]
               + [q for q, c in zip(pts0, cs) if c > s[i1] + 1.0])
        _, _, s1, _, hs1, _ = path_profile(H, grid, new, path)
        E1 = _excess_window(hs1, s1, g)[0]
        report.append(dict(rec, hairpins=legs, traced_m=round(float(np.hypot(*np.diff(line, axis=0).T).sum()), 1),
                           excess_after_m=round(E1, 1)))
        if E1 >= E - 0.25:
            report[-1]["result"] = "no gain"
            break
        pts0 = new
    return pts0, report


def apply_paths(H, grid, p, avoid=None, water=None):
    """Corridor: the path's height profile is the terrain along it, smoothed and grade-limited
    (|dh/ds| <= max_grade), then the terrain is pulled onto it: flat across `width`, banks at most
    bank_deg steep (cuts and fills), shoulder minimum. With `switchbacks` (a dict: max_cut,
    half_width; or True) climbs too steep for max_grade get switchback legs along the contours
    first (plan_switchbacks), so the corridor follows the ground instead of cutting / filling it."""
    out, dist, routed = [], np.full(H.shape, np.inf), {}
    for path in p["paths"]:
        points, sb = path["points"], []
        if path.get("switchbacks"):
            o = path["switchbacks"] if isinstance(path["switchbacks"], dict) else {}
            points, sb = plan_switchbacks(H, grid, path, avoid=avoid, **o)
        routed[path["name"]] = [list(map(float, q[:2])) for q in points]
        pts, seg, s, h, hs, hp = path_profile(H, grid, points, path, water)
        dz = np.abs(hp - h)
        dz_max = float(dz.max())
        kmax = int(np.argmax(dz))
        core = path["width"] / 2
        H = H + corridor(H, grid, pts, hp, core, path["bank_deg"], path.get("reach", 140.0), path["shoulder"],
                         path.get("cut_deg", 50.0))
        d, _, _, _ = poly_field(grid, pts, p["masks"]["path_range"])
        dist = np.minimum(dist, d)
        grade = np.abs(np.diff(hp)) / np.maximum(seg, 1e-6)
        out.append(dict(name=path["name"], length_m=round(float(s[-1]), 1),
                        max_grade=round(float(grade.max()), 3), max_cut_fill_m=round(dz_max, 2),
                        max_cut_fill_at=[round(float(pts[kmax, 0]), 1), round(float(pts[kmax, 1]), 1), round(float(s[kmax]), 1)],
                        cut_fill_p95_m=round(float(np.percentile(dz, 95)), 2),
                        rise_m=round(float(hp.max() - hp.min()), 1), switchbacks=sb))
    return H, out, dist, routed


# --------------------------------------------------------------------------------- 10 masks / light
def normals(H, cell):
    gy, gx = np.gradient(H, cell)
    n = np.dstack([-gx, -gy, np.ones_like(H)])
    return n / np.linalg.norm(n, axis=2, keepdims=True), gx, gy


def masks(H, grid, hyd, sed, path_d, p):
    cell = grid.cell
    n, gx, gy = normals(H, cell)
    slope = np.degrees(np.arccos(np.clip(n[..., 2], -1, 1)))
    lo, hi = float(H.min()), float(H.max())
    altitude = (H - lo) / (hi - lo)
    la = np.log(hyd["acc"])
    flow = blur(la / la.max(), 0.7)
    flow = np.where(np.isfinite(hyd["lake_level"]) & (H < hyd["lake_level"]), 1.0, flow)
    twi = np.log(hyd["acc"] * cell / np.maximum(np.tan(np.radians(slope)), 1e-3))
    twi = blur(twi, 2.0)
    tlo, thi = np.percentile(twi, [2, 99.5])
    wet = np.clip((twi - tlo) / (thi - tlo), 0, 1)
    water = hyd["rivers"] | (np.isfinite(hyd["lake_level"]) & (H < hyd["lake_level"]))
    _, _, dw = nearest_seed(water)
    near = 1 - np.clip(dw * cell / p["masks"]["water_range"], 0, 1)
    wetness = np.maximum(wet, near ** 1.5)
    curv = np.zeros_like(H)
    for sg in p["masks"]["curv_sigma"]:
        b = blur(H, sg / cell * 1.5)
        lap = (shift(b, 1, 0) + shift(b, -1, 0) + shift(b, 0, 1) + shift(b, 0, -1) - 4 * b) / cell ** 2
        sc = np.percentile(np.abs(lap), 98) + 1e-9
        curv += np.clip(-lap / sc, -1, 1) / len(p["masks"]["curv_sigma"])
    curvature = 0.5 + 0.5 * curv                    # >0.5 ridge / convex, <0.5 gully / concave
    aspect = (np.degrees(np.arctan2(-gx, -gy)) + 360) % 360   # downslope bearing, 0 = north
    pr = p["masks"]["path_range"]
    path = np.clip(np.where(np.isfinite(path_d), path_d, pr) / pr, 0, 1)
    rivers = hyd["rivers"].astype(float)
    lakes = (np.isfinite(hyd["lake_level"]) & (H < hyd["lake_level"])).astype(float)
    s = np.clip(sed, 0, None)
    sediment = np.clip(blur(s, 1.0) / (np.percentile(s[s > 0], 98) + 1e-9 if (s > 0).any() else 1), 0, 1)
    return dict(slope=slope, altitude=altitude, flow=flow, wetness=wetness, curvature=curvature,
                aspect=aspect, path=path, rivers=rivers, lakes=lakes, sediment=sediment, normal=n)


def light(H, cell, look, x_extent_hint=None):
    """Numpy stand-in for the bake: sun (Lambert x heightfield shadow, soft) + sky (horizon-based
    visibility from 12 directions). Returns linear RGB light."""
    n, _, _ = normals(H, cell)
    sd = np.asarray(look["sun_dir"], float)
    L = -sd / np.linalg.norm(sd)
    ny, nx = H.shape
    jj, ii = np.mgrid[0:ny, 0:nx].astype(np.float64)
    g = Grid(0, 0, 1, nx, ny)
    hor = math.hypot(L[0], L[1])
    tan_e = L[2] / max(hor, 1e-6)
    vis = np.ones_like(H)
    dists = np.geomspace(1.0, 600.0 / cell, 40)
    for s in dists:
        hs = sample(H, g, ii + L[0] / hor * s, jj + L[1] / hor * s)
        ray = H + tan_e * s * cell
        vis = np.minimum(vis, np.clip(0.5 + (ray - hs) / (0.03 * s * cell + 0.3), 0, 1))
    sun = np.clip((n * L).sum(axis=2), 0, 1) * vis
    sky = np.zeros_like(H)
    dirs = 12
    for k in range(dirs):
        a = 2 * np.pi * (k + 0.5) / dirs
        cx, cy = math.cos(a), math.sin(a)
        tmax = np.zeros_like(H)
        for s in np.geomspace(1.5, 250.0 / cell, 12):
            tmax = np.maximum(tmax, (sample(H, g, ii + cx * s, jj + cy * s) - H) / (s * cell))
        sky += 1 - np.sin(np.arctan(tmax))
    sky = sky / dirs * (0.5 + 0.5 * n[..., 2])
    rgb = (np.asarray(look["sun_color"]) * look["sun_strength"] / math.pi * sun[..., None]
           + np.asarray(look["sky"]) * look["sky_strength"] * sky[..., None])
    return rgb, vis, sky


def albedo(M, p, noise, grid):
    pal = {k: np.asarray(v) for k, v in p["palette"].items()}
    X, Y = grid.xy()
    n1 = noise.fbm(X + 77, Y - 41, 60.0, 4)
    n2 = noise.fbm(X - 19, Y + 63, 9.0, 3)
    wet = np.clip(M["wetness"] + 0.25 * n1, 0, 1)[..., None]
    col = pal["dry"] * (1 - wet) + pal["grass"] * wet
    alp = smoothstep(0.62, 0.85, M["altitude"] + 0.08 * n1)[..., None]
    col = col * (1 - alp) + pal["alpine"] * alp
    scree = (smoothstep(0.15, 0.6, M["sediment"]) * smoothstep(18, 30, M["slope"]))[..., None]
    col = col * (1 - scree) + pal["scree"] * scree
    r0, r1 = p["masks"].get("rock_deg", (36.0, 48.0))       # (a forested old mountain wants ~(48, 58))
    rock = smoothstep(r0, r1, M["slope"] + 6 * n2 + 10 * (M["curvature"] - 0.5))
    rock = np.maximum(rock, M["cliff"] * p["masks"].get("cliff_rock", 1.0))[..., None]   # cut cliff faces
    col = col * (1 - rock) + pal["rock"] * rock
    bank = np.clip(M["_near_water"] * (0.8 + 0.4 * n2), 0, 1)[..., None]   # gravel / sand banks
    col = col * (1 - bank) + pal["gravel"] * bank
    wb = np.maximum(M["rivers"], M["lakes"])[..., None]
    col = col * (1 - wb) + pal["mud"] * wb
    pth = (1 - smoothstep(0.02, 0.05, M["path"] + 0.01 * n2))[..., None]
    col = col * (1 - pth) + pal["dirt"] * pth
    return col * (0.85 + 0.3 * (0.5 + 0.5 * n2))[..., None]


# --------------------------------------------------------------------------------- backdrop
def backdrop(p, H, grid, noise):
    """Coarse ring out to backdrop.extent: same macro function, bigger framing hills toward the
    edge, and the fine field's border offset blended in so the seam is exact."""
    q = p["backdrop"]
    n = int(round(q["extent"] / q["cell"])) + 1
    g = Grid(-q["extent"] / 2, -q["extent"] / 2, q["cell"], n, n)
    Hb, _ = macro(p, g, noise)
    X, Y = g.xy()
    half = p["size"] / 2
    cheb = np.maximum(np.abs(X), np.abs(Y))
    frame = smoothstep(half, q["extent"] / 2 * 0.85, cheb)
    Hb += q["frame_height"] * frame * (0.55 + 0.45 * noise.ridged(X, Y, q["frame_wavelength"], 5))
    # the same erosion at the coarse spacing, so distant ridges read as eroded too
    er = p["erosion"]
    if er["fluvial"]["on"]:
        Hb = Hb + fluvial(Hb, g.cell, dict(er["fluvial"], factor=1, iters=25))
    if er["thermal"]["on"]:
        Hb = thermal(Hb, g.cell, dict(er["thermal"], iters=15))
    # inner square: the fine heights at the coarse spacing (exact on shared vertices)
    step = int(round(q["cell"] / grid.cell))
    k0 = int(round((-half - g.x0) / q["cell"]))
    k1 = k0 + (grid.nx - 1) // step + 1
    inner = H[::step, ::step]
    Hb_in = Hb[k0:k1, k0:k1].copy()
    off = np.zeros_like(Hb)
    cx = np.clip(np.arange(n), k0, k1 - 1) - k0
    cy = cx
    edge_off = inner - Hb_in
    low = blur(edge_off, 6)                 # long-range: only the smooth part of the mismatch
    dout = np.maximum(cheb - half, 0)
    Hb = Hb + (low[np.ix_(cy, cx)] * (1 - smoothstep(0, q["blend"], dout))
               + (edge_off - low)[np.ix_(cy, cx)] * (1 - smoothstep(0, 3 * q["cell"], dout)))
    Hb[k0:k1, k0:k1] = inner
    # flat holes (outside the fine square only: inside it the fine field, and its pads, rule)
    outside = np.ones(Hb.shape, bool); outside[k0:k1, k0:k1] = False
    for x0, y0, x1, y1, hh, bl in q.get("holes", []):
        ex, ey = np.maximum(np.maximum(x0 - X, X - x1), 0), np.maximum(np.maximum(y0 - Y, Y - y1), 0)
        wgt = (1 - smoothstep(0, max(bl, 1e-3), np.hypot(ex, ey))) * outside
        Hb = Hb + (hh - Hb) * wgt
    return Hb, g, (k0, k1)


# --------------------------------------------------------------------------------- driver
def build(**overrides):
    p = merged(P, overrides)
    timings = {}
    T0 = time.perf_counter()
    rng = np.random.default_rng(p["seed"])
    noise = Noise(p["seed"])
    n = int(round(p["size"] / p["cell"])) + 1
    grid = Grid(-p["size"] / 2, -p["size"] / 2, p["cell"], n, n)
    out_dir = os.path.join(OUT_ROOT, p["name"])
    os.makedirs(os.path.join(out_dir, "masks"), exist_ok=True)

    def tick(name, t):
        timings[name] = round(time.perf_counter() - t, 2)
        print(f"  {name:14s} {timings[name]:7.2f} s", flush=True)

    print(f"terrain {p['name']}: {n} x {n} samples, {p['cell']} m, {p['size']} m square")
    t = time.perf_counter()
    H, mountain = macro(p, grid, noise)
    H_macro = H.copy()
    tick("macro+detail", t)
    er = p["erosion"]
    sed = np.zeros_like(H)
    if er["fluvial"]["on"]:
        t = time.perf_counter()
        H = H + fluvial(H, grid.cell, er["fluvial"])
        tick("fluvial", t)
    if er["droplets"]["on"]:
        q = er["droplets"]
        for f, share in zip(q.get("scales", (1,)), q.get("scale_share", (1.0,))):
            t = time.perf_counter()
            qs = dict(q, per_cell=q["per_cell"] * share)
            if f == 1:
                H, s1 = droplets(H, grid.cell, qs, rng)
                sed += s1
            else:            # coarse pass: gullies hundreds of metres long; delta upsampled
                Hc, dc = droplets(H[::f, ::f], grid.cell * f, qs, rng)
                H = H + upsample(dc, f, H.shape)
                sed += upsample(dc, f, H.shape)
            tick(f"droplets_x{f}", t)
    if er["thermal"]["on"]:
        t = time.perf_counter()
        Hth = thermal(H, grid.cell, er["thermal"])
        sed += np.clip(Hth - H, 0, None)
        H = Hth
        tick("thermal", t)
    t = time.perf_counter()
    H, knicks = apply_knicks(H, grid, p)
    H, cliffs, cliff_mask = apply_cliffs(H, grid, p, noise)
    H = apply_pools(H, grid, p)
    tick("cliffs", t)
    t = time.perf_counter()
    H, hyd = hydrology(H, grid, p, {})
    tick("hydrology", t)
    t = time.perf_counter()
    H, pads = apply_pads(H, grid, p)
    water_near = None
    if any(pp.get("river_offset") is not None for pp in p["paths"]):
        # the nearest river's water level everywhere (for riverside roads)
        # (big channels only: side creeks crossing the road would put bumps in its grade)
        rm = np.isfinite(hyd["river_level"]) & (hyd["river_hw"] * 2 >= 12.0)
        wy, wx, _ = nearest_seed(rm)
        water_near = np.where(rm.any(), np.nan_to_num(hyd["river_level"])[np.maximum(wy, 0), np.maximum(wx, 0)], H)
    H, paths, path_d, routed = apply_paths(H, grid, p, avoid=hyd["rivers"] | (np.isfinite(hyd["lake_level"]) & (H < hyd["lake_level"])),
                                           water=water_near)
    # fords: corridors don't dam rivers
    # where a river crosses a corridor: a ford (channel re-cut through the path) when the
    # overlap is short; a river running ALONG the path is reported (the path wins there)
    fords, overlaps = [], []
    pw = max(pp["width"] for pp in p["paths"]) / 2 + 1
    chan = np.isfinite(hyd["channel_T"])
    crossing = chan & (path_d < pw + 6)
    recut = np.zeros(H.shape, bool)
    if crossing.any():
        lab = label(crossing)
        X, Y = grid.xy()
        for cid in np.unique(lab[lab >= 0]):
            m = lab == cid
            ext = math.hypot(np.ptp(X[m]), np.ptp(Y[m]))
            wid = float(hyd["river_hw"][m].max() * 2)
            rec = dict(x=round(float(X[m].mean()), 1), y=round(float(Y[m].mean()), 1), width_m=round(wid, 1),
                       extent_m=round(ext, 1))
            if ext <= 3 * (wid + 2 * pw) + 12:
                fords.append(rec)
                recut |= m
            else:
                overlaps.append(rec)
    if any(pp.get("ford", True) for pp in p["paths"]) and recut.any():
        near = blur(recut.astype(float), 2) > 0.02
        H = np.where(near & chan, np.minimum(H, hyd["channel_T"]), H)
    tick("hooks", t)
    t = time.perf_counter()
    M = masks(H, grid, hyd, sed, path_d, p)
    M["cliff"] = np.clip(blur(cliff_mask, 0.7), 0, 1)
    M["bars"] = hyd["bars"].astype(float)                    # gravel bars / floodplain (hydro.floodplain)
    water_any = (M["rivers"] > 0) | (M["lakes"] > 0)
    _, _, dwc = nearest_seed(water_any)
    M["_near_water"] = 1 - smoothstep(0, 6.0 / grid.cell, dwc)
    tick("masks", t)
    t = time.perf_counter()
    rgb, sunvis, skyvis = light(H, grid.cell, p["look"])
    alb = albedo(M, p, noise, grid)
    bake = alb * rgb
    scale = float(np.percentile(bake.max(axis=2), 99.5)) or 1.0
    bake_n = np.clip(bake / scale, 0, 1)
    tick("light", t)
    t = time.perf_counter()
    Hb, gb, (k0, k1) = backdrop(p, H, grid, noise)
    rgb_b, _, _ = light(Hb, gb.cell, p["look"])
    nb, _, _ = normals(Hb, gb.cell)
    slope_b = np.degrees(np.arccos(nb[..., 2]))
    Xb, Yb = gb.xy()
    pal = p["palette"]
    nzb = noise.fbm(Xb, Yb, 140.0, 4)
    wood = smoothstep(-0.15, 0.25, nzb)[..., None]               # distant forest / meadow mosaic
    meadow = np.asarray(pal["dry"]) * 0.5 + np.asarray(pal["grass"]) * 0.5
    alb_b = meadow * (1 - wood) + np.asarray(pal.get("forest", (0.035, 0.06, 0.025))) * wood
    rk = smoothstep(*p["backdrop"].get("rock_deg", (28.0, 40.0)), slope_b)[..., None]
    alb_b = alb_b * (1 - rk) + np.asarray(pal["rock"]) * rk
    # meet the fine albedo at the seam (sampled at the nearest border point), fade over `blend`
    half = p["size"] / 2
    st = int(round(gb.cell / grid.cell))
    edge_alb = alb[::st, ::st]
    edge_low = np.dstack([blur(edge_alb[..., c], 6) for c in range(3)])
    ci = np.clip(np.arange(gb.nx), k0, k1 - 1) - k0
    dout = np.maximum(np.maximum(np.abs(Xb), np.abs(Yb)) - half, 0)
    w_long = (1 - smoothstep(0, p["backdrop"]["blend"] * 0.5, dout))[..., None]
    w_short = (1 - smoothstep(0, 3 * gb.cell, dout))[..., None]
    alb_b = (alb_b * (1 - w_long) + edge_low[np.ix_(ci, ci)] * w_long
             + (edge_alb - edge_low)[np.ix_(ci, ci)] * w_short)
    alb_b[k0:k1, k0:k1] = edge_alb
    bake_b = np.clip(alb_b * rgb_b / scale, 0, 1)
    tick("backdrop", t)
    timings["generate_total"] = round(time.perf_counter() - T0, 2)

    # ------------------------------------------------------------------ write
    t = time.perf_counter()
    files = {}
    lo, hi = float(H.min()), float(H.max())
    q16 = np.round((H - lo) / (hi - lo) * 65535).astype(np.uint16)
    files["height16.png"] = write_png(os.path.join(out_dir, "height16.png"), q16)
    # collider: raw little-endian uint16, row 0 = north (= three.js min z), same quantisation
    with open(os.path.join(out_dir, "collider_u16.bin"), "wb") as fh:
        fh.write(np.ascontiguousarray(q16[::-1]).astype("<u2").tobytes())
    files["collider_u16.bin"] = os.path.getsize(os.path.join(out_dir, "collider_u16.bin"))
    files["collider_u16.bin.gz"] = len(zlib.compress(open(os.path.join(out_dir, "collider_u16.bin"), "rb").read(), 9))
    u8 = lambda a: np.round(np.clip(a, 0, 1) * 255).astype(np.uint8)
    mask_imgs = dict(slope=M["slope"] / 90, altitude=M["altitude"], flow=M["flow"], wetness=M["wetness"],
                     curvature=M["curvature"], aspect=M["aspect"] / 360, path=M["path"],
                     rivers=blur(M["rivers"], 0.7), lakes=M["lakes"], sediment=M["sediment"], cliff=M["cliff"],
                     **({"bars": M["bars"]} if "bars" in M else {}))
    for k, a in mask_imgs.items():
        files[f"masks/{k}.png"] = write_png(os.path.join(out_dir, "masks", f"{k}.png"), u8(a))
    splat = np.dstack([u8(M["slope"] / 90), u8(M["wetness"]), u8(M["curvature"]), u8(M["sediment"])])
    files["masks/splat_rgba.png"] = write_png(os.path.join(out_dir, "masks", "splat_rgba.png"), splat)
    srgb = lambda c: np.where(c <= 0.0031308, c * 12.92, 1.055 * np.clip(c, 0, None) ** (1 / 2.4) - 0.055)
    files["albedo.png"] = write_png(os.path.join(out_dir, "albedo.png"), u8(srgb(np.clip(alb, 0, 1))))
    files["bake.png"] = write_png(os.path.join(out_dir, "bake.png"), u8(srgb(bake_n)))
    relief = relief_image(H, grid, M, hyd, p)
    files["relief.png"] = write_png(os.path.join(out_dir, "relief.png"), relief)
    before_after = np.concatenate([relief_image(H_macro, grid, None, None, p), relief], axis=1)
    files["relief_macro_vs_final.png"] = write_png(os.path.join(out_dir, "relief_macro_vs_final.png"),
                                                   before_after[::2, ::2])
    np.savez_compressed(os.path.join(out_dir, "terrain.npz"),
                        H=H.astype(np.float32), bake=(bake_n * 65535).astype(np.uint16),
                        river_level=hyd["river_level"].astype(np.float32),
                        lake_level=hyd["lake_level"].astype(np.float32),
                        Hb=Hb.astype(np.float32), bake_b=(bake_b * 65535).astype(np.uint16),
                        albedo_b=(np.clip(alb_b, 0, 1) * 65535).astype(np.uint16))
    tick("write", t)
    stats = dict(
        name=p["name"], seed=p["seed"], samples=[n, n], cell_m=p["cell"], size_m=p["size"],
        height=dict(min=round(lo, 2), max=round(hi, 2)),
        erosion=dict(droplet_eroded_m3=round(float(-np.clip(sed, None, 0).sum() * grid.cell ** 2), 0),
                     deposited_m3=round(float(np.clip(sed, 0, None).sum() * grid.cell ** 2), 0),
                     mean_abs_change_m=round(float(np.abs(H - H_macro).mean()), 2)),
        walk=dict(slope_deg_p50=round(float(np.percentile(M["slope"], 50)), 1),
                  slope_deg_p90=round(float(np.percentile(M["slope"], 90)), 1),
                  walkable_pct_lt_35deg=round(float((M["slope"] < 35).mean() * 100), 1),
                  paths=[path_walk(H, grid, dict(pp, points=routed[pp["name"]])) for pp in p["paths"]]),
        routed_paths=routed, hydrology=hyd["info"], knicks=knicks, cliffs=cliffs, pads=pads, paths=paths, fords=fords, river_along_path=overlaps,
        light_scale=round(scale, 5), timings_s=timings, files_bytes=files,
        grid=dict(x0=grid.x0, y0=grid.y0, cell=grid.cell, nx=n, ny=n),
        collider=dict(file="collider_u16.bin", dtype="uint16 little-endian", rows="north to south",
                      height_min=lo, height_max=hi, scale=(hi - lo) / 65535,
                      three_origin=[grid.x0, -(grid.y0 + (n - 1) * grid.cell)],
                      triangulation="cell (i,j)-(i+1,j+1) diagonal in Blender coords; see terrain.height_at"),
        backdrop=dict(samples=[gb.nx, gb.ny], cell=gb.cell, extent=p["backdrop"]["extent"], inner=[k0, k1]),
        chunks=p["chunks"], lods=list(p["lods"]), look=p["look"],
    )
    with open(os.path.join(out_dir, "stats.json"), "w") as fh:
        json.dump(stats, fh, indent=1)
    print(f"  total {timings['generate_total']:.1f} s generate; height {lo:.1f}..{hi:.1f} m; "
          f"{len(hyd['info']['lakes'])} lakes, {hyd['info']['river_cells']} river cells, fords {len(fords)}")
    return stats


def path_walk(H, grid, path):
    """Along-grade and cross-slope of the final surface (exact mesh heights) on a path."""
    pts = spline(path["points"], 0.5)
    h = height_at(H, grid, pts[:, 0], pts[:, 1])
    seg = np.hypot(*np.diff(pts[:, :2], axis=0).T)
    grade = np.abs(np.diff(h)) / np.maximum(seg, 1e-6)
    t = np.diff(pts[:, :2], axis=0) / np.maximum(seg, 1e-6)[:, None]
    nrm = np.column_stack([-t[:, 1], t[:, 0]])
    c, o = pts[:-1, :2], path["width"] / 2 * 0.75
    hl = height_at(H, grid, c[:, 0] + nrm[:, 0] * o, c[:, 1] + nrm[:, 1] * o)
    hr = height_at(H, grid, c[:, 0] - nrm[:, 0] * o, c[:, 1] - nrm[:, 1] * o)
    cross = np.degrees(np.arctan(np.abs(hl - hr) / (2 * o)))
    return dict(name=path["name"], grade_p50=round(float(np.percentile(grade, 50)), 3),
                grade_p99=round(float(np.percentile(grade, 99)), 3), grade_max=round(float(grade.max()), 3),
                cross_deg_p50=round(float(np.percentile(cross, 50)), 1),
                cross_deg_p99=round(float(np.percentile(cross, 99)), 1), cross_deg_max=round(float(cross.max()), 1))


def relief_image(H, grid, M, hyd, p):
    """Shaded relief preview: hypsometric tint x multi-directional hillshade, water, path."""
    n, _, _ = normals(H, grid.cell)
    shade = np.zeros(H.shape)
    for az, w in ((315, 0.5), (270, 0.2), (0, 0.2), (225, 0.1)):
        a, e = math.radians(az), math.radians(40)
        L = np.array([math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)])
        shade += w * np.clip((n * L).sum(axis=2), 0, 1)
    shade = (shade / shade.max()) ** 1.6
    t = (H - H.min()) / (H.max() - H.min())
    stops = np.array([[0.0, 0.33, 0.45, 0.25], [0.25, 0.55, 0.60, 0.33], [0.5, 0.70, 0.62, 0.42],
                      [0.75, 0.62, 0.52, 0.42], [1.0, 0.92, 0.90, 0.88]])
    tint = np.dstack([np.interp(t, stops[:, 0], stops[:, c]) for c in (1, 2, 3)])
    img = tint * (0.12 + 1.0 * shade[..., None])
    if M is not None:
        water = np.maximum(M["lakes"], M["rivers"])[..., None]
        img = img * (1 - water) + np.array([0.20, 0.38, 0.62]) * water * (0.7 + 0.3 * shade[..., None])
        pth = (1 - smoothstep(0.02, 0.04, M["path"]))[..., None]
        img = img * (1 - pth) + np.array([0.85, 0.30, 0.15]) * pth
        X, Y = grid.xy()
        for pad in p["pads"]:
            if pad.get("half"):
                ex = np.abs(X - pad["center"][0]) - pad["half"][0]; ey = np.abs(Y - pad["center"][1]) - pad["half"][1]
                ring = np.abs(np.maximum(ex, ey)) < grid.cell
            else:
                ring = np.abs(np.hypot(X - pad["center"][0], Y - pad["center"][1]) - pad["radius"]) < grid.cell
            img[ring] = (1.0, 0.9, 0.2)
    return np.round(np.clip(img, 0, 1) * 255).astype(np.uint8)


def _parse(argv):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default=None)
    ap.add_argument("--quick", action="store_true", help="3 m cells (4x faster) for iteration")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override, dotted for nested dicts, value parsed as JSON")
    a = ap.parse_args(argv)
    ov = {}
    if a.name:
        ov["name"] = a.name
    if a.quick:
        ov["cell"] = 3.0
        ov.setdefault("name", (a.name or P["name"]) + "_quick")
    for pair in a.set:
        k, v = pair.split("=", 1)
        try:
            v = json.loads(v)
        except ValueError:
            pass
        node = ov
        keys = k.split(".")
        for kk in keys[:-1]:
            node = node.setdefault(kk, {})
        node[keys[-1]] = v
    return ov


if __name__ == "__main__":
    build(**_parse(sys.argv[1:]))
