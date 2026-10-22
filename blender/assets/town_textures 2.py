"""The town kit's one texture: T_Town_Atlas (2048, base colour), shared by every town_*.py
asset through a single material (plus an emissive twin for neon and lit signs). Not an asset.

The atlas is a grid of 256 px units. Each REGION holds one tileable surface (a 2x2 unit =
512 px region for walls and roofs, 1x1 for the rest), drawn at its inner size and padded
with an 8 px wrapped gutter so filtering never bleeds the neighbour in. Geometry repeats a
region by splitting faces at every tile boundary (town_common), so every face maps inside one
region. Special regions: WINDOWS (4 x 4 cells: what each window shows, frames painted in),
SIGNS (2 x 4 pictorial sign blanks, no lettering), PALETTE (8 x 8 flat swatches for trim,
paint, metal, neon and the far meshes, including each region's mean colour).

Surfaces come from Poly Haven CC0 scans (tiled at their real size, colour-matched, contrast
kept) or numpy designs times a scan's detail. Arrays are [row, col], row 0 = bottom (v = 0).
Regions are cached in build/town_atlas/<key>.npy; the atlas is re-assembled when missing.
Sources: assets/textures/town_polyhaven.json.
"""
import json
import os
import urllib.request

import bpy
import numpy as np

PROJECT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
TEX = os.path.join(PROJECT, "assets", "textures")
CACHE = os.path.join(PROJECT, "build", "polyhaven")
RCACHE = os.path.join(PROJECT, "build", "town_atlas")
MANIFEST = os.path.join(TEX, "town_polyhaven.json")
ATLAS = "T_Town_Atlas"
SIZE = 2048
UNIT = 256
GUT = 8
UA = {"User-Agent": "game_testing-texture-fetch/1.0 (Blender; CC0 assets)"}


# ------------------------------------------------------------------ io

def srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


_NOTES = {}


def fetch(ph_id):
    """The scan's 2k diffuse JPG (cached in build/polyhaven/) and its real width in metres."""
    os.makedirs(CACHE, exist_ok=True)
    meta = os.path.join(CACHE, f"{ph_id}.json")
    info_p = os.path.join(CACHE, f"{ph_id}.info.json")
    if not os.path.exists(meta):
        open(meta, "wb").write(_get(f"https://api.polyhaven.com/files/{ph_id}"))
    if not os.path.exists(info_p):
        open(info_p, "wb").write(_get(f"https://api.polyhaven.com/info/{ph_id}"))
    files, info = json.load(open(meta)), json.load(open(info_p))
    diff = files.get("Diffuse") or files.get("diffuse") or files.get("Color")
    url = diff["2k"]["jpg"]["url"]
    img = os.path.join(CACHE, f"{ph_id}_diff_2k.jpg")
    if not os.path.exists(img):
        open(img, "wb").write(_get(url))
    size_m = (info.get("dimensions") or [2000, 2000])[0] / 1000.0
    _NOTES[ph_id] = {"polyhaven": ph_id, "url": f"https://polyhaven.com/a/{ph_id}", "file": url,
                     "license": "CC0", "scan_metres": round(size_m, 3)}
    return img, size_m


def load_px(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[..., :3].copy()
    bpy.data.images.remove(img)
    return px


def resize(px, w, h):
    ih, iw, _ = px.shape
    img = bpy.data.images.new("_town_resize", iw, ih, alpha=False, float_buffer=True)
    img.pixels.foreach_set(np.concatenate([px, np.ones((ih, iw, 1), np.float32)], axis=2).astype(np.float32).ravel())
    img.scale(w, h)
    out = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[..., :3].copy()
    bpy.data.images.remove(img)
    return out


def save_png(path, lin):
    h, w, _ = lin.shape
    img = bpy.data.images.new("_town_save", w, h, alpha=False)
    rgba = np.concatenate([lin_to_srgb(lin), np.ones((h, w, 1))], axis=2)
    img.pixels.foreach_set(rgba.astype(np.float32).ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def scan_tile(ph_id, tile, n, rotate=False):
    """Linear rgb [n, n, 3] covering `tile` metres with the scan at about its real scale."""
    img, size_m = fetch(ph_id)
    px = load_px(img)
    if rotate:
        px = np.ascontiguousarray(np.rot90(px))
    k = max(1, round(tile / size_m))
    cell = resize(px, max(8, n // k), max(8, n // k))
    out = np.tile(cell, (k, k, 1))
    if out.shape[0] != n:
        out = resize(out, n, n)
    return srgb_to_lin(np.clip(out, 0, 1))


def lum(lin):
    return lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)


def detail(lin, contrast=1.0):
    L = lum(lin)
    return 1 + contrast * (L / max(float(L.mean()), 1e-5) - 1)


def matched(lin, mean, desat=0.0):
    if desat:
        lin = lin * (1 - desat) + lum(lin)[..., None] * desat
    cur = lin.reshape(-1, 3).mean(axis=0)
    return lin * (np.array(mean) / np.maximum(cur, 1e-4))


def noise(n, su, sv, beta, rng):
    """Periodic fractal noise in [-1, 1]; su/sv > 1 stretch features along u/v."""
    white = rng.standard_normal((n, n))
    kv = np.fft.fftfreq(n)[:, None] * n
    ku = np.fft.fftfreq(n)[None, :] * n
    k = np.sqrt((ku * su) ** 2 + (kv * sv) ** 2)
    k[0, 0] = 1.0
    spec = np.fft.fft2(white) / k ** beta
    spec[0, 0] = 0
    out = np.real(np.fft.ifft2(spec))
    return out / (np.abs(out).max() + 1e-9)


def grid(n, m=None):
    m = m or n
    return np.meshgrid((np.arange(n) + 0.5) / n, (np.arange(m) + 0.5) / m)


def smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ surface designs

def lap_siding(n, tile, paint, wear, seed, exposure=0.105, scan="weathered_plank_siding"):
    """Painted lap siding (courses along u), a scan's grain under the paint."""
    rng = np.random.default_rng(seed)
    boards = max(1, round(tile / exposure))
    wood = scan_tile(scan, tile, n)
    u, v = grid(n)
    b = np.floor(v * boards).astype(int)
    t = v * boards - b
    shade = (1.0 - 0.10 * t) * (1 - 0.45 * np.exp(-((1 - t) / 0.07) ** 2))
    shade *= np.where(t < 0.035, 0.62, 1.0)
    joints = rng.random(boards)
    jd = np.abs(((u - joints[b]) + 0.5) % 1.0 - 0.5)
    shade *= np.where(jd < 1.2 / n, 0.55, 1.0)
    tone = rng.uniform(-1, 1, boards)[b]
    m = noise(n, 2.5, 1.0, 1.6, rng) * 0.5 + 0.5 + 0.25 * (t < 0.12)
    bare = smooth(m, 1.0 - wear * 0.9, 1.0 - wear * 0.9 + 0.06)
    painted = np.array(paint) * (1 + 0.035 * tone)[..., None] * (detail(wood, 0.3) * 0.5 + 0.5)[..., None]
    lin = painted * (1 - bare[..., None]) + wood * 0.9 * bare[..., None]
    return lin * shade[..., None]


def board_batten(n, tile, paint, seed, batten=0.4, scan="white_planks_clean", grain=0.25):
    """Board-and-batten: vertical boards with 60 mm battens every `batten` m (along u)."""
    rng = np.random.default_rng(seed)
    wood = scan_tile(scan, tile, n)
    u, v = grid(n)
    k = max(1, round(tile / batten))
    t = (u * k) % 1.0
    bw = 0.06 / batten
    d = np.minimum(t, 1 - t)
    on = d < bw / 2
    shade = np.where(on, 1.06, 1.0)
    edge = np.abs(d - bw / 2) < 1.5 / n * k
    shade = np.where(edge & (t < 0.5), 0.55, shade)
    shade = np.where(edge & (t >= 0.5), 0.85, shade)
    shade = shade * (1 - 0.12 * np.exp(-((d - bw / 2) / (0.03 / batten)) ** 2) * (~on))
    tone = noise(n, 0.15, 3.0, 1.3, rng) * 0.5 + 0.5
    lin = np.array(paint) * detail(wood, grain)[..., None] * (0.95 + 0.08 * tone)[..., None] * shade[..., None]
    streak = smooth(noise(n, 0.08, 3.0, 1.2, rng), 0.2, 0.9)
    return lin * (1 - 0.10 * streak)[..., None]


def standing_seam(n, tile, colour, seed, pitch=0.45):
    """Standing-seam metal roof: seams along v every `pitch` m, light/shade per seam,
    faint oil-canning in the pans; a fine scan grain."""
    rng = np.random.default_rng(seed)
    u, v = grid(n)
    k = max(1, round(tile / pitch))
    t = (u * k) % 1.0
    shade = 1 + 1.4 * np.exp(-((t - 0.02) / 0.022) ** 2) - 0.55 * np.exp(-((t - 0.95) / 0.04) ** 2) + 0.08 * t
    can = noise(n, 0.3, 2.0, 1.6, rng)
    shade = shade * (1 + 0.06 * can * np.sin(np.pi * t))
    fine = scan_tile("metal_plate", tile, n)
    return np.array(colour) * shade[..., None] * detail(fine, 0.15)[..., None]


def shingles(n, tile, colour, seed):
    """Architectural (laminated) asphalt shingles: staggered tabs of random width, the
    dragon-tooth lower layer, granule speckle, lighter and darker shingles."""
    rng = np.random.default_rng(seed)
    u, v = grid(n)
    rows = max(1, round(tile / 0.143))
    r = np.floor(v * rows).astype(int)
    t = v * rows - r
    widths = rng.uniform(0.12, 0.33, (rows, 40)) / tile
    edges = np.cumsum(widths, axis=1)
    edges = edges / edges[:, -1:] * 1.0          # each row covers exactly one tile width
    off = rng.random(rows)
    uu = (u + off[r]) % 1.0
    tab = np.zeros_like(r)
    for j in range(39):
        tab += (uu > edges[r, j]).astype(int)
    tid = r * 41 + tab
    tone = rng.uniform(-1, 1, rows * 41 + 41)[tid]
    grit = noise(n, 1, 1, 0.2, rng)
    base = np.array(colour) * (1 + 0.22 * tone + 0.15 * grit)[..., None]
    drop = rng.uniform(0.25, 0.55, rows * 41 + 41)[tid]
    shade = 1 - 0.55 * np.exp(-(t / 0.07) ** 2)
    shade = shade * np.where(t < drop, 0.78, 1.0)
    jd = np.full(u.shape, 1.0)
    for j in range(39):
        jd = np.minimum(jd, np.abs(uu - edges[r, j]))
    shade = shade * np.where(jd < 1.0 / n, 0.5, 1.0)
    streak = smooth(noise(n, 0.05, 2.5, 1.3, rng), 0.2, 0.7)
    return base * shade[..., None] * (1 - 0.18 * streak)[..., None]


def checker(n, tile, a, b, k, seed, scan="old_linoleum_flooring_01"):
    rng = np.random.default_rng(seed)
    u, v = grid(n)
    c = (np.floor(u * k) + np.floor(v * k)) % 2
    d = detail(scan_tile(scan, tile, n), 0.2)
    lin = np.where(c[..., None] > 0.5, np.array(a), np.array(b)) * d[..., None]
    wear = smooth(noise(n, 1, 1, 1.8, rng), 0.2, 0.9)
    lin = lin * (1 - 0.2 * wear[..., None]) + 0.2 * wear[..., None] * np.array([0.18, 0.16, 0.13])
    uu, vv = (u * k) % 1, (v * k) % 1
    lin[(np.minimum(uu, 1 - uu) < 0.012) | (np.minimum(vv, 1 - vv) < 0.012)] *= 0.7
    return lin


def painted_block(n, tile, paint, seed):
    rng = np.random.default_rng(seed)
    d = detail(scan_tile("concrete_floor_02", tile, n), 0.5)
    u, v = grid(n)
    cols, rows = round(tile / 0.4), round(tile / 0.2)
    r = np.floor(v * rows).astype(int)
    uu = (u * cols + (r % 2) * 0.5) % 1.0
    vv = (v * rows) % 1.0
    joint = np.minimum(np.minimum(uu, 1 - uu) * 0.4, np.minimum(vv, 1 - vv) * 0.2)
    shade = 0.65 + 0.35 * smooth(joint, 0.002, 0.008)
    stain = smooth(noise(n, 0.15, 2.5, 1.4, rng), 0.0, 0.8)
    return np.array(paint) * d[..., None] * shade[..., None] * (1 - 0.15 * stain)[..., None]


# ------------------------------------------------------------------ windows

WINDOW_KINDS = [
    # white-frame double-hung (older homes, the church, brick fronts)
    "dh_curtain", "dh_blind", "dh_dark", "dh_lamp", "dh_lace", "dh_blind_low", "dh_venetian", "dh_tv",
    # black-frame modern (shops, the new mountain style)
    "bk_dark", "bk_shop", "bk_cafe", "bk_blinds", "bk_display", "bk_transom", "bk_office", "bk_video",
]


def _disk(u, v, cu, cv, r):
    return ((u - cu) ** 2 + (v - cv) ** 2) < r * r


def windows(n):
    """4 x 4 cells (cell 0 top-left): glass, what's behind it and the sash frame painted in."""
    rng = np.random.default_rng(3)
    k = 4
    c = n // k
    out = np.zeros((n, n, 3))
    u, v = grid(c)
    room = np.array([0.022, 0.020, 0.018])
    folds = 0.5 + 0.5 * np.sin(u * 2 * np.pi * 7 + 1.3 * np.sin(u * 13))
    for i, kind in enumerate(WINDOW_KINDS):
        img = np.ones((c, c, 3)) * room
        if kind == "dh_curtain":
            img = np.array([0.40, 0.33, 0.22]) * (0.55 + 0.45 * folds)[..., None]
            img[np.abs(u - 0.5) < 0.05] = room * 1.5
        elif kind in ("dh_blind", "dh_blind_low"):
            h = 0.48 if kind == "dh_blind" else 0.15
            img[v > h] = np.array([0.44, 0.40, 0.31])
            img[np.abs(v - h) < 0.015] = np.array([0.12, 0.10, 0.08])
        elif kind == "dh_dark":
            img = room + np.array([0.01, 0.012, 0.015]) * smooth(v, 0.2, 1)[..., None]
        elif kind == "dh_lamp":
            g = np.exp(-(((u - 0.32) / 0.25) ** 2 + ((v - 0.42) / 0.3) ** 2))
            img = room + np.array([0.70, 0.42, 0.17]) * g[..., None]
            img[(np.abs(u - 0.32) < 0.07) & (np.abs(v - 0.6) < 0.06)] = np.array([0.85, 0.66, 0.38])
            side = u > 0.7
            img[side] = (np.array([0.30, 0.22, 0.14]) * (0.6 + 0.4 * folds)[..., None])[side]
        elif kind == "dh_lace":
            pat = (np.sin(u * 90) * np.sin(v * 90) > 0.2) | (np.sin((u + v) * 45) > 0.85)
            img = room * 2 + np.array([0.34, 0.33, 0.29]) * pat[..., None] * 0.8
        elif kind == "dh_venetian":
            sl = 0.5 + 0.5 * np.sign(np.sin(v * 2 * np.pi * 22))
            img = np.array([0.40, 0.38, 0.33]) * (0.35 + 0.6 * sl)[..., None]
        elif kind == "dh_tv":
            g = np.exp(-(((u - 0.55) / 0.35) ** 2 + ((v - 0.4) / 0.35) ** 2))
            img = room + np.array([0.10, 0.17, 0.28]) * g[..., None]
        elif kind == "bk_dark":
            img = room * 1.2
        elif kind == "bk_shop":
            img = np.ones((c, c, 3)) * np.array([0.16, 0.14, 0.11])
            for sh in (0.2, 0.42, 0.64):
                img[np.abs(v - sh) < 0.012] = np.array([0.05, 0.04, 0.03])
                band = (v > sh + 0.012) & (v < sh + 0.17)
                col = rng.uniform(0.05, 0.5, (12, 3))
                idx = np.minimum(np.floor(u * 12).astype(int), 11)
                img[band] = col[idx[band]] * 0.7
            img[v > 0.9] = np.array([0.6, 0.55, 0.45])
        elif kind == "bk_cafe":
            img = np.ones((c, c, 3)) * np.array([0.10, 0.06, 0.035])
            for pu in (0.2, 0.5, 0.8):
                g = np.exp(-(((u - pu) / 0.08) ** 2 + ((v - 0.72) / 0.06) ** 2))
                img += np.array([0.9, 0.55, 0.22]) * g[..., None]
                img[(np.abs(u - pu) < 0.004) & (v > 0.75)] = 0.02
            img[v < 0.3] = np.array([0.16, 0.09, 0.05])
            img[np.abs(v - 0.3) < 0.01] = np.array([0.4, 0.3, 0.2])
        elif kind == "bk_blinds":
            sl = 0.5 + 0.5 * np.sign(np.sin(v * 2 * np.pi * 30))
            img = np.array([0.22, 0.21, 0.19]) * (0.5 + 0.5 * sl)[..., None]
        elif kind == "bk_display":
            img = np.ones((c, c, 3)) * np.array([0.13, 0.12, 0.10])
            img[(np.abs(u - 0.35) < 0.12) & (v > 0.35) & (v < 0.75)] = np.array([0.30, 0.08, 0.04])
            img[_disk(u, v, 0.35, 0.8, 0.04)] = np.array([0.05, 0.05, 0.05])
            img[(np.abs(u - 0.7) < 0.1) & (v > 0.1) & (v < 0.2)] = np.array([0.18, 0.10, 0.05])
            img[(np.abs(u - 0.82 + (v - 0.5) * 0.1) < 0.012) & (v > 0.15) & (v < 0.9)] = np.array([0.35, 0.25, 0.12])
            img[v < 0.08] = np.array([0.25, 0.2, 0.14])
        elif kind == "bk_transom":
            img = room * 1.5 + np.array([0.15, 0.18, 0.22]) * smooth(v, 0.4, 1.0)[..., None]
        elif kind == "bk_office":
            img = np.ones((c, c, 3)) * np.array([0.06, 0.06, 0.06])
            img[(v > 0.25) & (v < 0.3)] = np.array([0.12, 0.08, 0.05])
            img[(np.abs(u - 0.4) < 0.1) & (v > 0.32) & (v < 0.46)] = np.array([0.25, 0.35, 0.45])
            img[v > 0.92] = np.array([0.45, 0.45, 0.42])
        elif kind == "bk_video":
            img = np.ones((c, c, 3)) * np.array([0.08, 0.06, 0.08])
            for sh in (0.15, 0.35, 0.55):
                band = (v > sh) & (v < sh + 0.15)
                col = rng.uniform(0.03, 0.6, (24, 3)) * np.array([1.0, 0.7, 0.9])
                idx = np.minimum(np.floor(u * 24).astype(int), 23)
                img[band] = col[idx[band]]
            img[(np.abs(u - 0.75) < 0.12) & (v > 0.72) & (v < 0.94)] = np.array([0.5, 0.1, 0.25])
        refl = smooth(v, 0.45, 1.0) * 0.12 * (0.7 + 0.3 * noise(c, 0.3, 1, 1, rng))
        img = img * 0.85 + refl[..., None] * np.array([0.75, 0.8, 0.9])
        white = kind.startswith("dh")
        fc = np.array([0.56, 0.54, 0.48]) if white else np.array([0.02, 0.02, 0.022])
        fw = 0.05
        frame = (np.minimum(u, 1 - u) < fw) | (np.minimum(v, 1 - v) < fw)
        if white:
            frame |= np.abs(v - 0.5) < fw * 0.7
            frame |= np.abs(u - 0.5) < 0.012
        elif kind == "bk_transom":
            frame |= (np.abs(u - 1 / 3) < 0.012) | (np.abs(u - 2 / 3) < 0.012) | (np.abs(v - 0.5) < 0.012)
        img[frame] = fc
        inner = (np.minimum(u, 1 - u) < fw + 0.012) | (np.minimum(v, 1 - v) < fw + 0.012)
        img[inner & ~frame] *= 0.5
        r_, c_ = divmod(i, k)
        out[(k - 1 - r_) * c:(k - r_) * c, c_ * c:(c_ + 1) * c] = img
    return out


# ------------------------------------------------------------------ signs (pictorial, no lettering)

SIGN_KINDS = ["cafe", "burger", "outfitter", "video", "sheriff", "bar", "museum", "gas"]


def _seg(u, v, a, b, r):
    pa = np.stack([u - a[0], v - a[1]], -1)
    ba = np.array([b[0] - a[0], b[1] - a[1]])
    h = np.clip((pa @ ba) / (ba @ ba), 0, 1)
    return np.linalg.norm(pa - h[..., None] * ba, axis=-1) < r


def _poly(u, v, pts):
    inside = np.zeros_like(u, bool)
    for i in range(len(pts)):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
        inside ^= ((y0 > v) != (y1 > v)) & (u < (x1 - x0) * (v - y0) / (y1 - y0 + 1e-9) + x0)
    return inside


def signs(n):
    """2 x 4 cells (2:1, cell 0 top-left): clean modern sign blanks with a pictogram."""
    rng = np.random.default_rng(9)
    cw, ch = n // 2, n // 4
    out = np.zeros((n, n, 3))
    u, v = np.meshgrid((np.arange(cw) + 0.5) / cw * 2.0, (np.arange(ch) + 0.5) / ch)
    cells = {
        "cafe": ((0.03, 0.035, 0.03), (0.62, 0.55, 0.42)),
        "burger": ((0.55, 0.20, 0.03), (0.66, 0.60, 0.48)),
        "outfitter": ((0.06, 0.12, 0.09), (0.66, 0.58, 0.40)),
        "video": ((0.05, 0.03, 0.12), (0.65, 0.48, 0.05)),
        "sheriff": ((0.62, 0.58, 0.48), (0.30, 0.20, 0.04)),
        "bar": ((0.015, 0.012, 0.012), (0.55, 0.08, 0.05)),
        "museum": ((0.40, 0.36, 0.28), (0.06, 0.06, 0.06)),
        "gas": ((0.60, 0.60, 0.58), (0.06, 0.22, 0.40)),
    }
    for i, kind in enumerate(SIGN_KINDS):
        bg, fg = cells[kind]
        img = np.ones((ch, cw, 3)) * np.array(bg)
        m = np.zeros((ch, cw), bool)
        if kind == "cafe":
            m |= (np.abs(u - 1.0) < 0.2) & (v > 0.25) & (v < 0.6) & ~((np.abs(u - 1.0) < 0.15) & (v > 0.55))
            m |= _disk(u, v, 1.24, 0.43, 0.08) & ~_disk(u, v, 1.24, 0.43, 0.045)
            m |= (np.abs(u - 1.0) < 0.33) & (np.abs(v - 0.21) < 0.025)
            for dx in (-0.08, 0.02, 0.12):
                m |= (np.abs(u - 1.0 - dx - 0.03 * np.sin(v * 25)) < 0.014) & (v > 0.66) & (v < 0.86)
        elif kind == "burger":
            m |= ((((u - 1.0) / 0.34) ** 2 + ((v - 0.56) / 0.2) ** 2) < 1) & (v > 0.56)
            m |= (np.abs(u - 1.0) < 0.36) & (np.abs(v - 0.47) < 0.035)
            m |= (np.abs(u - 1.0) < 0.33) & (np.abs(v - 0.38) < 0.03)
            m |= (np.abs(u - 1.0) < 0.31) & (v > 0.22) & (v < 0.32)
        elif kind == "outfitter":
            m |= _poly(u, v, [(0.45, 0.4), (0.8, 0.82), (1.0, 0.6), (1.2, 0.86), (1.58, 0.4)])
            m &= ~_poly(u, v, [(0.72, 0.72), (0.8, 0.82), (0.88, 0.72)])
            for k_ in range(2):
                m |= (np.abs(v - 0.3 + 0.07 * k_ - 0.025 * np.sin(u * 16)) < 0.018) & (np.abs(u - 1.0) < 0.55)
        elif kind == "video":
            m |= (np.abs(u - 1.0) < 0.45) & (np.abs(v - 0.5) < 0.3)
            m &= ~(_disk(u, v, 0.78, 0.55, 0.1) | _disk(u, v, 1.22, 0.55, 0.1))
            m &= ~((np.abs(u - 1.0) < 0.3) & (np.abs(v - 0.3) < 0.05))
            m |= _disk(u, v, 0.78, 0.55, 0.04) | _disk(u, v, 1.22, 0.55, 0.04)
        elif kind == "sheriff":
            ang = np.arctan2(v - 0.5, u - 1.0)
            rr = np.hypot(u - 1.0, v - 0.5)
            m |= rr < 0.17 + 0.17 * np.maximum(0, np.cos(3 * (ang - np.pi / 2))) ** 4
            for a in np.arange(6) * np.pi / 3 + np.pi / 2:
                m |= _disk(u, v, 1.0 + 0.35 * np.cos(a), 0.5 + 0.35 * np.sin(a), 0.035)
            m &= ~(_disk(u, v, 1.0, 0.5, 0.07) & ~_disk(u, v, 1.0, 0.5, 0.045))
        elif kind == "bar":
            m |= _poly(u, v, [(0.7, 0.82), (1.3, 0.82), (1.0, 0.5)])
            m |= (np.abs(u - 1.0) < 0.018) & (v > 0.22) & (v < 0.52)
            m |= (np.abs(u - 1.0) < 0.16) & (np.abs(v - 0.2) < 0.022)
            m |= _disk(u, v, 1.13, 0.74, 0.04)
        elif kind == "museum":
            m |= _poly(u, v, [(0.6, 0.72), (1.4, 0.72), (1.0, 0.9)])
            for x in (0.7, 0.9, 1.1, 1.3):
                m |= (np.abs(u - x) < 0.035) & (v > 0.25) & (v < 0.68)
            m |= (np.abs(u - 1.0) < 0.42) & (np.abs(v - 0.2) < 0.04)
        elif kind == "gas":
            m |= (np.abs(u - 0.85) < 0.15) & (v > 0.15) & (v < 0.85) & ~((np.abs(u - 0.85) < 0.09) & (v > 0.55) & (v < 0.76))
            m |= _seg(u, v, (1.0, 0.7), (1.12, 0.62), 0.024) | _seg(u, v, (1.12, 0.62), (1.12, 0.3), 0.024)
            m |= _disk(u, v, 1.4, 0.38, 0.11) | _poly(u, v, [(1.31, 0.43), (1.49, 0.43), (1.4, 0.7)])
        img[m] = np.array(fg)
        border = (np.minimum(u, 2 - u) < 0.04) | (np.minimum(v, 1 - v) < 0.06)
        img[border] = np.array(fg) * 0.85
        img *= (0.95 + 0.05 * np.tile(noise(ch, 1, 1, 1.5, rng), (1, 2)))[..., None]
        r_, c_ = divmod(i, 2)
        out[(3 - r_) * ch:(4 - r_) * ch, c_ * cw:(c_ + 1) * cw] = img
    return out


# ------------------------------------------------------------------ flat palette

# 8 x 8 swatches (row-major from the top-left); the last row holds region means (far meshes)
SWATCHES = [
    ("trim", (0.58, 0.56, 0.50)), ("trim_black", (0.022, 0.022, 0.024)), ("trim_bronze", (0.06, 0.045, 0.03)),
    ("trim_red", (0.24, 0.05, 0.035)), ("trim_green", (0.045, 0.075, 0.05)), ("trim_brown", (0.11, 0.065, 0.04)),
    ("glass_dark", (0.012, 0.014, 0.017)), ("metal_galv", (0.33, 0.34, 0.34)),
    ("metal_dark", (0.03, 0.03, 0.032)), ("chrome", (0.62, 0.62, 0.62)), ("rubber", (0.012, 0.012, 0.013)),
    ("tar", (0.03, 0.03, 0.032)), ("soot", (0.015, 0.014, 0.013)), ("stone", (0.36, 0.34, 0.30)),
    ("door_red", (0.22, 0.035, 0.03)), ("door_green", (0.04, 0.10, 0.06)),
    ("door_wood", (0.13, 0.065, 0.03)), ("screen", (0.03, 0.032, 0.034)), ("vinyl_red", (0.30, 0.025, 0.025)),
    ("vinyl_black", (0.02, 0.018, 0.018)), ("felt", (0.02, 0.12, 0.05)), ("formica", (0.50, 0.47, 0.40)),
    ("brass", (0.40, 0.26, 0.08)), ("mirror", (0.30, 0.31, 0.32)),
    ("paint_white", (0.62, 0.61, 0.57)), ("paint_yellow", (0.62, 0.42, 0.03)), ("paint_blue", (0.04, 0.10, 0.25)),
    ("paint_red", (0.40, 0.03, 0.02)), ("paint_teal", (0.03, 0.22, 0.22)), ("paint_orange", (0.65, 0.20, 0.02)),
    ("plastic_white", (0.60, 0.60, 0.58)), ("ribbon", (0.70, 0.16, 0.02)),
    ("neon_red", (1.0, 0.10, 0.06)), ("neon_pink", (1.0, 0.15, 0.45)), ("neon_blue", (0.15, 0.35, 1.0)),
    ("neon_green", (0.2, 1.0, 0.35)), ("neon_amber", (1.0, 0.55, 0.12)), ("lamp", (1.0, 0.72, 0.42)),
    ("glow_cool", (0.75, 0.85, 1.0)), ("glow_white", (0.95, 0.93, 0.88)),
    ("bottle_green", (0.04, 0.12, 0.05)), ("bottle_amber", (0.25, 0.09, 0.015)), ("bottle_clear", (0.35, 0.38, 0.36)),
    ("paper", (0.62, 0.60, 0.53)), ("fabric_blue", (0.06, 0.08, 0.16)), ("fabric_tan", (0.30, 0.22, 0.13)),
    ("shade", (0.03, 0.028, 0.026)), ("window_lit", (0.55, 0.36, 0.16)),
    ("car_white", (0.58, 0.58, 0.56)), ("car_black", (0.015, 0.016, 0.018)), ("car_red", (0.30, 0.02, 0.02)),
    ("car_blue", (0.03, 0.06, 0.16)), ("car_silver", (0.35, 0.36, 0.37)), ("car_green", (0.03, 0.08, 0.05)),
    ("headlight", (0.70, 0.70, 0.66)), ("taillight", (0.35, 0.01, 0.01)),
]
PALETTE_N = 8
MEAN_KEYS = ["bb_white", "bb_charcoal", "lap_cream", "ledgestone", "fieldstone", "brick_red", "seam_black", "shingle"]


def palette(n):
    s = n // PALETTE_N
    out = np.zeros((n, n, 3))
    for i, (_, col) in enumerate(SWATCHES[:PALETTE_N * (PALETTE_N - 1)]):
        r_, c_ = divmod(i, PALETTE_N)
        out[(PALETTE_N - 1 - r_) * s:(PALETTE_N - r_) * s, c_ * s:(c_ + 1) * s] = col
    return out


def swatch_index(name):
    for i, (k, _) in enumerate(SWATCHES):
        if k == name:
            return i
    if name in MEAN_KEYS:
        return PALETTE_N * (PALETTE_N - 1) + MEAN_KEYS.index(name)
    raise KeyError(name)


# ------------------------------------------------------------------ the atlas layout

REGIONS = {}


def region(key, col, row, w, tile, kind="tile"):
    """Register a region: (col, row) of its top-left in 256 px units, w units square."""
    def deco(fn):
        REGIONS[key] = dict(col=col, row=row, w=w, tile=tile, fn=fn, kind=kind)
        return fn
    return deco


def _ribs(n, tile):
    u, _ = grid(n)
    k = round(tile / 0.068)
    t = (u * k) % 1.0
    return 0.75 + 0.45 * np.sin(2 * np.pi * t)


# 512 px surfaces (2 x 2 units)
region("bb_white", 0, 0, 2, 2.4)(lambda n: board_batten(n, 2.4, (0.60, 0.58, 0.52), 1))
region("bb_charcoal", 2, 0, 2, 2.4)(lambda n: board_batten(n, 2.4, (0.035, 0.036, 0.036), 2, grain=0.45))
region("lap_cream", 4, 0, 2, 2.1)(lambda n: lap_siding(n, 2.1, (0.60, 0.54, 0.38), 0.06, 3))
region("ledgestone", 6, 0, 2, 2.0)(lambda n: matched(scan_tile("rustic_stone_wall_02", 2.0, n), (0.20, 0.17, 0.13)))
region("fieldstone", 0, 2, 2, 2.5)(lambda n: matched(scan_tile("stone_wall", 2.5, n), (0.26, 0.23, 0.19), desat=0.2))
region("brick_red", 2, 2, 2, 1.5)(lambda n: matched(scan_tile("factory_brick", 1.5, n), (0.19, 0.08, 0.048)))
region("seam_black", 4, 2, 2, 1.8)(lambda n: standing_seam(n, 1.8, (0.028, 0.029, 0.03), 4))
region("shingle", 6, 2, 2, 2.0)(lambda n: shingles(n, 2.0, (0.07, 0.068, 0.066), 5))
region("cedar", 0, 4, 2, 2.0)(lambda n: matched(scan_tile("japanese_cedar_planks", 2.0, n), (0.20, 0.10, 0.05), desat=0.55))
region("windows", 2, 4, 2, 1.0, kind="cells")(lambda n: windows(n))
region("signs", 4, 4, 2, 1.0, kind="cells")(lambda n: signs(n))
region("woodfloor", 6, 4, 2, 2.0)(lambda n: matched(scan_tile("wood_floor_worn", 2.0, n), (0.16, 0.085, 0.04)))
# 256 px surfaces
region("concrete", 0, 6, 1, 3.0)(lambda n: matched(scan_tile("concrete_floor_02", 3.0, n), (0.30, 0.29, 0.27)))
region("asphalt", 1, 6, 1, 3.0)(lambda n: matched(scan_tile("asphalt_02", 3.0, n), (0.07, 0.068, 0.065)))
region("deck", 2, 6, 1, 2.0)(lambda n: matched(scan_tile("weathered_planks", 2.0, n, rotate=True), (0.19, 0.15, 0.11)))
region("plaster", 3, 6, 1, 2.0)(lambda n: matched(scan_tile("painted_plaster_wall", 2.0, n), (0.50, 0.47, 0.41)))
region("checker", 4, 6, 1, 1.0)(lambda n: checker(n, 1.0, (0.55, 0.53, 0.46), (0.03, 0.03, 0.032), 4, 6))
region("darkwood", 5, 6, 1, 1.5)(lambda n: matched(scan_tile("dark_wood", 2.0, n, rotate=True), (0.06, 0.025, 0.012)))
region("varnish", 6, 6, 1, 1.0)(lambda n: matched(scan_tile("wood_table_001", 1.5, n), (0.11, 0.045, 0.018)))
region("polished", 7, 6, 1, 3.0)(lambda n: matched(scan_tile("smooth_concrete_floor", 2.0, n), (0.24, 0.23, 0.215), desat=0.6))
region("brick_white", 0, 7, 1, 1.5)(lambda n: matched(scan_tile("whitewashed_brick", 2.0, n), (0.52, 0.50, 0.45)))
region("bb_sage", 1, 7, 1, 2.4)(lambda n: board_batten(n, 2.4, (0.20, 0.25, 0.20), 7))
region("seam_green", 2, 7, 1, 1.8)(lambda n: standing_seam(n, 1.8, (0.04, 0.075, 0.05), 8))
region("corrugated", 3, 7, 1, 2.24)(lambda n: matched(scan_tile("worn_corrugated_iron", 2.24, n), (0.30, 0.31, 0.31), desat=0.3)
                                    * _ribs(n, 2.24)[..., None])
region("block", 4, 7, 1, 2.0)(lambda n: painted_block(n, 2.0, (0.55, 0.53, 0.47), 9))
region("tile_floor", 5, 7, 1, 1.2)(lambda n: checker(n, 1.2, (0.42, 0.40, 0.35), (0.36, 0.34, 0.30), 4, 10, scan="square_tiles"))
region("lap_white", 6, 7, 1, 2.1)(lambda n: lap_siding(n, 2.1, (0.60, 0.58, 0.52), 0.04, 11))
region("palette", 7, 7, 1, 1.0, kind="palette")(lambda n: palette(n))


# ------------------------------------------------------------------ assembly

def _region_px(key, force=False):
    os.makedirs(RCACHE, exist_ok=True)
    p = os.path.join(RCACHE, key + ".npy")
    if os.path.exists(p) and not force:
        return np.load(p)
    R = REGIONS[key]
    n = R["w"] * UNIT - (2 * GUT if R["kind"] == "tile" else 0)
    lin = np.clip(R["fn"](n), 0, 1).astype(np.float32)
    np.save(p, lin)
    print(f"TOWN REGION {key} ({n}px, tile {R['tile']} m)")
    return lin


def atlas_path(force=(), rebuild=False):
    """Path of T_Town_Atlas.png, assembled (and any missing region generated) if needed."""
    path = os.path.join(TEX, ATLAS + ".png")
    missing = [k for k in REGIONS if k != "palette" and not os.path.exists(os.path.join(RCACHE, k + ".npy"))]
    if os.path.exists(path) and not missing and not force and not rebuild:
        return path
    img = np.zeros((SIZE, SIZE, 3), np.float32)
    means = {}
    for key, R in REGIONS.items():
        if key == "palette":
            continue
        lin = _region_px(key, force=key in force)
        means[key] = lin.reshape(-1, 3).mean(axis=0)
        _place(img, R, lin)
    pal = palette(UNIT)
    s = UNIT // PALETTE_N
    for i, k in enumerate(MEAN_KEYS):         # the bottom swatch row (row 7 from the top)
        pal[0:s, i * s:(i + 1) * s] = means[k]
    _place(img, REGIONS["palette"], pal)
    os.makedirs(TEX, exist_ok=True)
    save_png(path, img)
    old = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
    sources = {**old.get("sources", {}), **_NOTES}
    json.dump({"atlas": ATLAS, "size": SIZE, "unit": UNIT, "gutter": GUT,
               "regions": {k: {kk: vv for kk, vv in R.items() if kk != "fn"} for k, R in REGIONS.items()},
               "sources": sources}, open(MANIFEST, "w"), indent=1)
    print(f"TOWN ATLAS {path}")
    return path


def _place(img, R, lin):
    w = R["w"] * UNIT
    x0 = R["col"] * UNIT
    y0 = SIZE - (R["row"] + R["w"]) * UNIT
    if R["kind"] == "tile":
        lin = np.pad(lin, ((GUT, GUT), (GUT, GUT), (0, 0)), mode="wrap")
    img[y0:y0 + w, x0:x0 + w] = lin


def region_rect(key):
    """(u0, v0, du, dv) of a region's inner area in atlas UV (v up)."""
    R = REGIONS[key]
    w = R["w"] * UNIT
    g = GUT if R["kind"] == "tile" else 0
    x0 = R["col"] * UNIT + g
    y0 = SIZE - (R["row"] + R["w"]) * UNIT + g
    return x0 / SIZE, y0 / SIZE, (w - 2 * g) / SIZE, (w - 2 * g) / SIZE


def swatch_uv(name):
    i = swatch_index(name)
    r_, c_ = divmod(i, PALETTE_N)
    u0, v0, du, dv = region_rect("palette")
    return u0 + (c_ + 0.5) / PALETTE_N * du, v0 + (PALETTE_N - 1 - r_ + 0.5) / PALETTE_N * dv
