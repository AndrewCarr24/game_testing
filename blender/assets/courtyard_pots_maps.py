"""Texture maps for courtyard_pots (a helper, not an asset): two texture sets.

T_CourtyardPots_Clay_BaseColor / _Normal (1024): two terracotta pot "skins", each a full-width
band (u wraps round the pot, any whole number of times), v running along the pot's lathe profile
from the foot, up the outside, over the rolled rim, down the inside and across the soil to the
centre (so a pot and its soil are one mesh, one material). The fine clay detail (speckle, lime
spots, firing mottle) and its relief come from the Poly Haven planter_pot_clay scan's outer
wall (CC0), high-passed and tiled; the structure is procedural: a damp foot with moss and algae,
firing flashes and sun-bleached patches, lime (salt) bloom as a tide line under the rim with
drips, a worn rim with chipped edges, a dark soil-stained inside, then the top dressing (skin A:
bark mulch; skin B: grit with moss). Skin A is a warm, younger orange pot; skin B an older,
paler, salt-bloomed one.

T_CourtyardPots_Foliage_BaseColor (1024 RGBA, alpha-tested): plant cards composed from Poly
Haven scans (CC0): fern_02 fronds; star jasmine strands built from periwinkle_plant leaves and
flowers (recoloured to jasmine's dark glossy green and cream-white stars); olive sprigs from
shrub_02's lanceolate leaves (grey-green, silver undersides); box sprigs and a dense box-leaf
mat from shrub_04 / periwinkle leaves; painted golden-grass and blue sedge tufts.

Maps are generated only when missing (bump VERSION or delete them after changing a painter).
Without network on the first build the scans fall back to procedural-only detail."""
import json
import math
import os
import sys
import urllib.request

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import textures  # noqa: E402

PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
SCANS = os.path.join(PROJECT, "build", "polyhaven", "maps")
TEX = textures.TEX_DIR
UA = {"User-Agent": "game_testing-map-fetch/1.0 (CC0 assets)"}

CLAY = "T_CourtyardPots_Clay"
LEAF = "T_CourtyardPots_Foliage"

# ------------------------------------------------------------------ clay skin layout
N = 1024
SKIN_H = 512                  # rows per skin (two skins: Blender v 0..0.5 = A, 0.5..1 = B)
PAD = 4                       # rows of padding at each end of a skin
U_M = 0.82                    # metres of circumference per texture width (the scan's period)
V_M = 1.05                    # nominal profile length (foot to soil centre) a skin is painted for
# profile keypoints (fraction of the skin): foot, neck (rim starts), rim apex, inner lip, soil
# meets the wall, centre
P_FOOT, P_NECK, P_APEX, P_LIP, P_WALL = 0.02, 0.60, 0.69, 0.745, 0.79


def skin_v(skin, p):
    """Blender v for profile fraction p on skin 0 (A) / 1 (B)."""
    return skin * 0.5 + (PAD + p * (SKIN_H - 2 * PAD)) / N


# ------------------------------------------------------------------ scans

def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def scan_map(ph_id, key, ext="jpg"):
    """One 1k map of a Poly Haven asset (key: Diffuse, Alpha, nor_gl), downloaded once."""
    os.makedirs(SCANS, exist_ok=True)
    path = os.path.join(SCANS, f"{ph_id}_{key}_1k.{ext}")
    if not os.path.exists(path):
        files = json.loads(_get(f"https://api.polyhaven.com/files/{ph_id}"))
        data = _get(files[key]["1k"][ext]["url"])
        with open(path + ".tmp", "wb") as f:
            f.write(data)
        os.replace(path + ".tmp", path)
    return path


def _read(path):
    """Image -> float array, rows top-down, raw stored values (sRGB-encoded for colour maps)."""
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    a = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)[::-1].copy()


def _lin(s):
    s = np.clip(s, 0, 1)
    return np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)


def _blur(a, sx, sy):
    """Periodic gaussian blur (sigma in pixels along columns / rows)."""
    h, w = a.shape[:2]
    ky = np.fft.fftfreq(h)[:, None]
    kx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2 * np.pi ** 2 * ((kx * sx) ** 2 + (ky * sy) ** 2))
    if a.ndim == 3:
        g = g[..., None]
    return np.real(np.fft.ifft2(np.fft.fft2(a, axes=(0, 1)) * g, axes=(0, 1)))


def _noise(h, w, su, sv, beta, rng):
    """Periodic fractal noise in [-1, 1] on an h x w grid; su / sv > 1 stretch features."""
    white = rng.standard_normal((h, w))
    ky = np.fft.fftfreq(h)[:, None] * h
    kx = np.fft.fftfreq(w)[None, :] * w
    k = np.sqrt((kx * su) ** 2 + (ky * sv) ** 2)
    k[0, 0] = 1.0
    spec = np.fft.fft2(white) / k ** beta
    spec[0, 0] = 0
    out = np.real(np.fft.ifft2(spec))
    return out / (np.abs(out).max() + 1e-9)


def _ss(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def _save_png(name, rgb, alpha=None):
    path = os.path.join(TEX, name + ".png")
    h, w, _ = rgb.shape
    img = bpy.data.images.new(name + "_tmp", w, h, alpha=alpha is not None)
    a = np.ones((h, w, 1)) if alpha is None else alpha[..., None]
    img.pixels.foreach_set(np.concatenate([rgb, a], axis=2)[::-1].astype(np.float32).ravel())
    if alpha is not None:
        img.alpha_mode = "STRAIGHT"
    img.filepath_raw = path + ".tmp.png"
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    os.replace(path + ".tmp.png", path)
    return path


# ------------------------------------------------------------------ clay

def _scan_band():
    """The planter_pot_clay scan's outer wall: (lin rgb, slope_x, slope_y) for rows going UP
    the pot, period = the texture width (0.82 m of circumference), ~0.2 m tall."""
    try:
        d = _read(scan_map("planter_pot_clay", "Diffuse"))
        n = _read(scan_map("planter_pot_clay", "nor_gl"))
    except Exception as e:  # noqa: BLE001  (offline first build: procedural only)
        print("courtyard_pots_maps: clay scan unavailable:", e)
        return None
    if d.shape[1] != N:
        return None
    rows = slice(720, 1001)            # outer wall, image rows (row 1004 = the foot, 717 = the rim)
    rgb = _lin(d[rows, :, :3])[::-1]   # bottom-up
    nn = n[rows, :, :3][::-1] * 2 - 1
    sx = nn[..., 0] / np.maximum(nn[..., 2], 0.3)
    sy = nn[..., 1] / np.maximum(nn[..., 2], 0.3)
    # high-pass the colour: keep speckle, lime spots and the firing mottle under ~2 cm, as a ratio
    lo = _blur(rgb, 18, 18)
    ratio = np.clip(rgb / np.maximum(lo, 1e-3), 0.45, 1.9)
    sx = sx - _blur(sx, 30, 30)
    sy = sy - _blur(sy, 30, 30)
    return ratio, sx, sy


def _tile_band(band, rows_per_m, rng):
    """Resample the scan band onto a skin (SKIN_H x N): physical scale kept, mirrored tiles up
    the profile with a random sideways shift per tile, cross-faded at the joins."""
    ratio, sx, sy = band
    bh = ratio.shape[0]
    arc = (np.arange(SKIN_H) + 0.5 - PAD) / (SKIN_H - 2 * PAD) * V_M        # metres up the profile
    t = arc * rows_per_m / bh                                               # in band heights
    shifts = rng.integers(0, N, 64)
    out_r = np.zeros((SKIN_H, N, 3))
    out_x = np.zeros((SKIN_H, N))
    out_y = np.zeros((SKIN_H, N))
    cols = np.arange(N)
    for i, ti in enumerate(t):
        k = int(math.floor(ti))
        f = ti - k
        acc_w, acc_r, acc_x, acc_y = 0.0, 0.0, 0.0, 0.0
        for kk, w in ((k, 1.0), (k - 1, max(0.0, 0.18 - f) / 0.18 * 0.5), (k + 1, max(0.0, f - 0.82) / 0.18 * 0.5)):
            if w <= 0:
                continue
            ff = ti - kk
            mir = (kk % 2) == 1
            row = (1 - ff) if mir else ff
            row = int(np.clip(row * (bh - 1), 0, bh - 1))
            c = (cols + shifts[kk % 64]) % N
            acc_r = acc_r + w * ratio[row, c]
            acc_x = acc_x + w * sx[row, c]
            acc_y = acc_y + w * sy[row, c] * (-1 if mir else 1)
            acc_w += w
        out_r[i], out_x[i], out_y[i] = acc_r / acc_w, acc_x / acc_w, acc_y / acc_w
    return out_r, out_x, out_y


def _chips(h, w, n, size, aspect, cols, rng, height, hmap, rgb, mask_rows=None, round_=False):
    """Scatter n small rotated ellipses (bark chips / grit), u-periodic; size in rows."""
    for _ in range(n):
        cy = rng.uniform(mask_rows[0], mask_rows[1]) if mask_rows else rng.uniform(0, h)
        cx = rng.uniform(0, w)
        ry = size * rng.uniform(0.5, 1.3)
        rx = ry * aspect * (1.0 if round_ else rng.uniform(1.2, 2.6))
        ang = rng.uniform(0, math.pi)
        r = int(max(rx, ry) + 2)
        y0, y1 = max(int(cy) - r, 0), min(int(cy) + r + 1, h)
        if y1 <= y0:
            continue
        ys, xs = np.mgrid[y0:y1, int(cx) - r:int(cx) + r + 1]
        dx, dy = xs + 0.5 - cx, ys + 0.5 - cy
        # (the ellipse rotates in a space where rows and columns are equally scaled)
        ex, ey = dx / aspect, dy
        c, s = math.cos(ang), math.sin(ang)
        qa = (ex * c + ey * s) / (rx / aspect)
        qb = (-ex * s + ey * c) / ry
        d = qa * qa + qb * qb
        m = np.clip((1.0 - d) * 3.0, 0, 1)
        if not m.any():
            continue
        xs = xs % w
        col = np.array(cols[rng.integers(len(cols))]) * rng.uniform(0.75, 1.25)
        shade = (1.0 - 0.35 * np.clip(qa * 0.7 + qb * 0.5, -1, 1))[..., None]   # lit from one side
        rgb[ys, xs] = rgb[ys, xs] * (1 - m[..., None]) + col * shade * m[..., None]
        hmap[ys, xs] = np.maximum(hmap[ys, xs], height * np.sqrt(np.clip(1 - d, 0, 1)) * m)


def _skin(rng, band, kind):
    """One pot skin: (lin rgb, height m, extra slopes) on SKIN_H x N, row 0 = the foot."""
    h, w = SKIN_H, N
    p = ((np.arange(h) + 0.5 - PAD) / (h - 2 * PAD))[:, None] * np.ones((1, w))
    x = np.ones((h, 1)) * (np.arange(w)[None, :] + 0.5) / w
    # px per metre: u 1249, v ~490: noise stretched 2.55x along u keeps features round on the pot
    an = (w / U_M) / ((h - 2 * PAD) / V_M)

    def nz(beta, scale=1.0):
        return _noise(h, w, an * scale, scale, beta, rng)

    old = kind == "B"
    body = np.array((0.39, 0.155, 0.080)) if not old else np.array((0.37, 0.180, 0.115))
    pale = np.array((0.48, 0.27, 0.16)) if not old else np.array((0.47, 0.32, 0.24))
    dark = np.array((0.27, 0.095, 0.050))
    n_big, n_mid, n_fine = nz(2.3), nz(1.6), nz(0.9)
    rgb = body * (1 + 0.16 * n_big + 0.07 * n_mid)[..., None]
    bleach = _ss(0.05, 0.55, nz(2.1) + 0.25 * (p - 0.3)) * (0.55 if old else 0.35)
    rgb = rgb * (1 - bleach[..., None]) + pale * (1 + 0.06 * n_mid)[..., None] * bleach[..., None]
    flash = _ss(0.20, 0.60, nz(2.0)) * 0.55
    rgb = rgb * (1 - flash[..., None]) + dark * flash[..., None]
    sx = np.zeros((h, w))
    sy = np.zeros((h, w))
    if band is not None:
        ratio, bsx, bsy = band
        wall = (p < P_LIP).astype(float)[..., None]
        rgb = rgb * (1 + (ratio ** 0.9 - 1) * (0.55 + 0.45 * wall))
        sx += bsx * 0.8 * wall[..., 0]
        sy += bsy * 0.8 * wall[..., 0]
    else:
        rgb = rgb * (1 + 0.08 * n_fine)[..., None]

    side = np.cos(2 * np.pi * (x - rng.uniform(0, 1)))         # the shaded, mossy side
    # damp foot: water wicks up from the floor, darker, with a soft tide mark
    edge = 0.11 + 0.04 * nz(1.7) + 0.025 * side
    damp = 1 - _ss(edge - 0.02, edge + 0.015, p)
    tide = np.exp(-((p - edge - 0.012) / 0.006) ** 2) * 0.5
    rgb = rgb * (1 - 0.50 * damp[..., None]) * (1 + 0.12 * tide[..., None])
    # moss and algae climbing from the foot, more on one side; algae film higher up on old pots
    m = nz(1.25) * 0.8 + 0.35 * side + nz(0.8) * 0.25
    moss = _ss(0.10, 0.45, m - (p - P_FOOT) / (0.10 if old else 0.06)) * (p < P_NECK) * _ss(-0.6, 0.0, n_fine)
    moss_col = np.array((0.030, 0.042, 0.012)) * (1 + 0.9 * _ss(-0.3, 0.7, n_fine))[..., None] \
        + np.array((0.035, 0.035, 0.006)) * _ss(0.2, 0.8, nz(1.0))[..., None]
    rgb = rgb * (1 - moss[..., None]) + moss_col * moss[..., None]
    algae = _ss(0.0, 0.6, nz(1.9) + 0.6 * side) * (1 - _ss(0.15, 0.45, p)) * (0.45 if old else 0.18)
    rgb = rgb * (1 - algae[..., None]) + np.array((0.15, 0.15, 0.085)) * algae[..., None]

    # lime bloom: a blotchy tide line under the rim, drips running down, a dusting on the rim
    n_salt = nz(1.5)
    band_m = _ss(0.22 if old else 0.30, 0.50, p + 0.08 * nz(1.8)) * (1 - _ss(P_NECK - 0.005, P_NECK + 0.015, p))
    drip_n = _noise(h, w, an * 0.35, 3.0, 1.4, rng)               # long along the profile
    drips = _ss(0.25, 0.65, drip_n) * _ss(0.12, 0.50, p) * (p < P_NECK)
    rim_salt = _ss(0.0, 0.5, nz(1.2)) * ((p >= P_NECK) & (p < P_LIP)) * (0.9 if old else 0.6)
    amount = 1.0 if old else 0.75
    salt = np.clip(_ss(-0.30 if old else -0.10, 0.35, n_salt + 0.35 * n_fine) * band_m + drips * 0.6 + rim_salt, 0, 1)
    salt = salt * amount * _ss(-0.5, 0.2, n_fine * 0.7 + 0.3)
    salt_col = np.array((0.62, 0.59, 0.52)) * (0.90 + 0.14 * n_fine)[..., None]
    rgb = rgb * (1 - 0.85 * salt[..., None]) + salt_col * 0.85 * salt[..., None]

    # rim: dry and worn, chipped at the apex (fresh clay shows); grime in the neck under it
    rim = ((p >= P_NECK) & (p < P_LIP)).astype(float)
    lum = rgb.mean(axis=2, keepdims=True)
    rgb = rgb * (1 - 0.12 * rim[..., None]) + (lum * 0.12 + rgb * 0.06) * rim[..., None]
    chips = _ss(0.55, 0.75, nz(0.7)) * np.exp(-((p - P_APEX) / 0.018) ** 2)
    rgb = rgb * (1 - chips[..., None]) + np.array((0.52, 0.25, 0.13)) * chips[..., None]
    neck = np.exp(-((p - P_NECK) / 0.010) ** 2) * 0.25
    rgb = rgb * (1 - neck[..., None])

    # inside: damp, soil-stained, darkest where the soil meets it
    ins = _ss(P_APEX + 0.01, P_LIP + 0.01, p)
    inside_col = np.array((0.17, 0.08, 0.048)) * (1 + 0.15 * n_mid + 0.1 * n_fine)[..., None] \
        * (1 - 0.45 * _ss(P_LIP, P_WALL, p))[..., None]
    rgb = rgb * (1 - ins[..., None]) + inside_col * ins[..., None]

    # height: throwing rings (stronger inside), clay grain, lime crust, moss cushion, rim chips
    arc = p * V_M
    rings = np.sin(2 * np.pi * arc / 0.021 + 1.5 * nz(2.0)) * (0.6 + 0.4 * nz(2.2))
    hmap = (0.00030 * (p < P_NECK) + 0.00055 * ((p >= P_LIP) & (p < P_WALL))) * rings
    hmap = hmap + 0.00012 * n_fine + 0.00025 * salt * nz(0.6) + 0.0010 * moss * (0.6 + 0.4 * n_fine)
    hmap = hmap - 0.0012 * chips

    # top dressing on the soil (rows from P_WALL to the centre)
    r0 = int(PAD + P_WALL * (h - 2 * PAD)) - 2
    soil = _ss(P_WALL - 0.004, P_WALL + 0.006, p)
    srgb = np.zeros((h, w, 3))
    if not old:            # bark mulch on dark compost
        srgb[:] = np.array((0.040, 0.028, 0.020))[None, None, :] * (1 + 0.4 * n_fine)[..., None]
        shm = np.zeros((h, w))
        _chips(h, w, 1300, 4.0, an, [(0.13, 0.065, 0.035), (0.10, 0.055, 0.032), (0.17, 0.10, 0.06),
                                      (0.07, 0.045, 0.03)], rng, 0.004, shm, srgb, (r0, h))
    else:                  # grey-brown grit with cushions of moss
        srgb[:] = np.array((0.06, 0.05, 0.04))[None, None, :] * (1 + 0.3 * n_fine)[..., None]
        shm = np.zeros((h, w))
        _chips(h, w, 2200, 2.4, an, [(0.24, 0.22, 0.19), (0.18, 0.16, 0.13), (0.30, 0.27, 0.22),
                                      (0.14, 0.12, 0.10)], rng, 0.0025, shm, srgb, (r0, h), round_=True)
        mo = _ss(0.1, 0.45, nz(1.3)) * (p > P_WALL)
        srgb = srgb * (1 - mo[..., None]) + moss_col * 1.3 * mo[..., None]
        shm = shm + 0.0015 * mo
    srgb = srgb * (1 - 0.35 * np.exp(-((p - P_WALL) / 0.012) ** 2))[..., None]   # shade at the wall
    rgb = rgb * (1 - soil[..., None]) + srgb * soil[..., None]
    hmap = hmap * (1 - soil) + shm * soil
    return np.clip(rgb, 0, 1), hmap, sx * (1 - soil), sy * (1 - soil)


VERSION = 10


STAMP = os.path.join(PROJECT, "build", "courtyard_pots_maps.version")


def _fresh(names):
    """The maps exist and were painted by this VERSION (stamped once both sets are written)."""
    try:
        with open(STAMP) as f:
            ok = f.read().strip() == str(VERSION)
    except OSError:
        ok = False
    return ok and all(os.path.exists(os.path.join(TEX, n + ".png")) for n in names)


def _stamp():
    os.makedirs(os.path.dirname(STAMP), exist_ok=True)
    with open(STAMP, "w") as f:
        f.write(str(VERSION))


def clay(force=False):
    """-> (base colour path, normal path)."""
    names = [CLAY + "_BaseColor", CLAY + "_Normal"]
    if _fresh(names) and not force:
        return tuple(os.path.join(TEX, n + ".png") for n in names)
    rng = np.random.default_rng(71)
    band = _scan_band()
    rgb = np.zeros((N, N, 3))
    nrm = np.zeros((N, N, 3))
    du = U_M / N
    dv = V_M / (SKIN_H - 2 * PAD)
    for skin, kind in ((0, "A"), (1, "B")):
        tb = _tile_band(band, 287 / 0.2, rng) if band is not None else None
        c, hm, sx, sy = _skin(rng, tb, kind)
        gx = (np.roll(hm, -1, axis=1) - np.roll(hm, 1, axis=1)) / (2 * du) + sx
        gy = np.gradient(hm, dv, axis=0) + sy
        n = np.stack([-gx, -gy, np.ones_like(gx)], axis=2)
        n /= np.linalg.norm(n, axis=2, keepdims=True)
        # skin rows bottom-up (p up) -> image rows top-down; skin 0 is the bottom half
        r0 = N - (skin + 1) * SKIN_H
        rgb[r0:r0 + SKIN_H] = c[::-1]
        nrm[r0:r0 + SKIN_H] = (n * 0.5 + 0.5)[::-1]
    _save_png(names[0], textures._to_srgb(rgb))
    _save_png(names[1], nrm)
    return tuple(os.path.join(TEX, n + ".png") for n in names)


# ------------------------------------------------------------------ foliage atlas
# cells in pixels (x0, y0, w, h), image rows top-down; a plant's base is at the cell's bottom
CELLS_PX = {
    "frondA": (0, 0, 128, 1024), "frondB": (128, 0, 128, 1024), "frondC": (256, 0, 128, 1024),
    "jasmineA": (384, 0, 160, 1024), "jasmineB": (544, 0, 160, 1024),
    "grass": (704, 0, 160, 512), "sedge": (864, 0, 160, 512),
    "oliveA": (704, 512, 160, 256), "oliveB": (864, 512, 160, 256),
    "boxSprig": (704, 768, 160, 256), "boxMat": (864, 768, 160, 256),
}


def cell_uv(name):
    """(u0, v0, du, dv) of a cell in Blender UV space (v0 = the cell's bottom = the plant base)."""
    x0, y0, w, h = CELLS_PX[name]
    return x0 / N, 1 - (y0 + h) / N, w / N, h / N


class Sprite:
    def __init__(self, rgb, a, base, tip, hw, tip_hw=None, leaf=False):
        """base/tip: the sprite's axis in the scan (pixels); hw: half-width of the mask round it
        (tapering to tip_hw at the tip; leaf: an almond-shaped mask, narrow at both ends)."""
        self.rgb = rgb
        self.base, self.tip, self.hw = np.array(base, float), np.array(tip, float), hw
        h, w = a.shape
        x0 = int(max(0, min(base[0], tip[0]) - hw - 4))
        x1 = int(min(w, max(base[0], tip[0]) + hw + 4))
        y0 = int(max(0, min(base[1], tip[1]) - hw - 4))
        y1 = int(min(h, max(base[1], tip[1]) + hw + 4))
        ys, xs = np.mgrid[y0:y1, x0:x1]
        ax = self.tip - self.base
        L2 = float(ax @ ax)
        t = np.clip(((xs + 0.5 - base[0]) * ax[0] + (ys + 0.5 - base[1]) * ax[1]) / L2, -0.06, 1.06)
        d = np.hypot(xs + 0.5 - (base[0] + t * ax[0]), ys + 0.5 - (base[1] + t * ax[1]))
        if leaf:
            lim = hw * np.maximum(0.22, np.sin(np.pi * np.clip(t, 0, 1)) ** 0.55)
        else:
            lim = hw + ((tip_hw if tip_hw is not None else hw) - hw) * np.clip(t, 0, 1)
        m = np.zeros((h, w))
        m[y0:y1, x0:x1] = np.clip(lim - d, 0, 1)
        # erode the scan's alpha by ~1 px: its edge texels are dark (the cut-out's outline)
        sub = a[y0:y1, x0:x1]
        er = sub.copy()
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            er = np.minimum(er, np.roll(np.roll(sub, dy, 0), dx, 1))
        ae = np.zeros((h, w))
        ae[y0:y1, x0:x1] = np.clip((er - 0.25) / 0.5, 0, 1)
        self.a = ae * m
        sel = self.a > 0.5
        self.mean = rgb[sel].mean(axis=0) if sel.any() else np.array((0.1, 0.1, 0.1))
        self.lum = float(self.mean @ LUM)


LUM = np.array((0.2126, 0.7152, 0.0722))


def _sample(img, sx, sy):
    h, w = img.shape[:2]
    x = np.clip(sx - 0.5, 0, w - 1.001)
    y = np.clip(sy - 0.5, 0, h - 1.001)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = x - x0, y - y0
    if img.ndim == 3:
        fx, fy = fx[..., None], fy[..., None]
    a = img[y0, x0] * (1 - fx) + img[y0, x0 + 1] * fx
    b = img[y0 + 1, x0] * (1 - fx) + img[y0 + 1, x0 + 1] * fx
    return a * (1 - fy) + b * fy


def stamp(rgb, alpha, spr, base, tip, width=1.0, colour=None, flip=False, clip=None, wrap=False):
    """Composite a sprite so its base->tip axis lands on base->tip here (similarity transform,
    across-axis scaled by `width`). colour: a function lin_rgb -> lin_rgb (recolour)."""
    sb, st = spr.base, spr.tip
    db, dt = np.array(base, float), np.array(tip, float)
    sa, da = st - sb, dt - db
    Ls, Ld = np.linalg.norm(sa), np.linalg.norm(da)
    if Ld < 1:
        return
    s = Ld / Ls
    us, ud = sa / Ls, da / Ld
    ps, pd = np.array((-us[1], us[0])), np.array((-ud[1], ud[0]))
    if flip:
        ps = -ps
    hwd = spr.hw * s * width + 2
    corners = [db + ud * t * Ld + pd * q for t in (-0.1, 1.1) for q in (-hwd, hwd)]
    cx0, cy0, cw, ch = clip if clip else (0, 0, alpha.shape[1], alpha.shape[0])
    xs_ = [c[0] for c in corners]
    ys_ = [c[1] for c in corners]
    x0, x1 = int(math.floor(min(xs_))), int(math.ceil(max(xs_))) + 1
    y0, y1 = int(math.floor(min(ys_))), int(math.ceil(max(ys_))) + 1
    if not wrap:
        x0, x1 = max(x0, cx0), min(x1, cx0 + cw)
    y0, y1 = max(y0, cy0), min(y1, cy0 + ch)
    if x1 <= x0 or y1 <= y0:
        return
    ys, xs = np.mgrid[y0:y1, x0:x1]
    rx, ry = xs + 0.5 - db[0], ys + 0.5 - db[1]
    along = (rx * ud[0] + ry * ud[1]) / s
    perp = (rx * pd[0] + ry * pd[1]) / (s * width)
    sx = sb[0] + us[0] * along + ps[0] * perp
    sy = sb[1] + us[1] * along + ps[1] * perp
    inside = (sx >= 0) & (sy >= 0) & (sx < spr.a.shape[1]) & (sy < spr.a.shape[0])
    a = _sample(spr.a, sx, sy) * inside
    if not a.any():
        return
    c = _sample(spr.rgb, sx, sy)
    if colour is not None:
        c = colour(c)
    if wrap:
        xs = cx0 + (xs - cx0) % cw
    a3 = a[..., None]
    rgb[ys, xs] = rgb[ys, xs] * (1 - a3) + c * a3
    alpha[ys, xs] = np.maximum(alpha[ys, xs], a)


def _gain(spr, target, jitter=1.0, sat=1.0, keep=0.3):
    """Recolour a scan sprite to a target mean colour: mostly the target hue scaled by the
    sprite's own luminance (veins, sheen, blemishes keep their light and dark), plus `keep`
    of its own colour shifted to the target (some natural hue variation, no false colours)."""
    tgt = np.array(target) * jitter
    g = tgt / np.maximum(spr.mean, 1e-4)
    tl = float(tgt @ LUM)

    def f(c):
        rel = (c @ LUM)[..., None] / max(spr.lum, 1e-4)
        out = tgt * rel * (1 - keep) + np.clip(c * g, 0, tl * 4) * keep
        if sat != 1.0:
            lum = (out @ LUM)[..., None]
            out = lum + (out - lum) * sat
        return np.clip(out, 0, 1)
    return f


def _flower_col(spr, cream=(0.70, 0.68, 0.57)):
    m = spr.mean.mean()

    def f(c):
        lum = c.mean(axis=-1, keepdims=True) / max(m, 1e-4)
        out = np.array(cream) * np.clip(0.62 + 0.38 * lum, 0.45, 1.15)
        eye = np.clip((c[..., 1:2] - c[..., 0:1]) * 6, 0, 1)        # the green-yellow centre
        return out * (1 - eye) + np.array((0.55, 0.50, 0.12)) * eye
    return f


def _sprites():
    """Scan sprites: (kind -> [Sprite]); None where a scan can't be had."""
    out = {}
    try:
        d = _lin(_read(scan_map("fern_02", "Diffuse"))[..., :3])
        a = _read(scan_map("fern_02", "Alpha", "png"))[..., 0]
        out["frond"] = [Sprite(d, a, (172, 968), (180, 112), 86, 24), Sprite(d, a, (390, 772), (378, 26), 80, 22),
                        Sprite(d, a, (814, 915), (797, 110), 76, 22)]
    except Exception as e:  # noqa: BLE001
        print("courtyard_pots_maps: fern scan unavailable:", e)
    try:
        d = _lin(_read(scan_map("periwinkle_plant", "Diffuse"))[..., :3])
        a = np.clip((d.max(axis=2) - 0.004) * 60, 0, 1)            # leaves on black
        out["leaf"] = [Sprite(d, a, (332, 972), (618, 832), 78, leaf=True), Sprite(d, a, (625, 985), (893, 832), 78, leaf=True),
                       Sprite(d, a, (567, 727), (760, 690), 52, leaf=True), Sprite(d, a, (213, 153), (375, 165), 46, leaf=True),
                       Sprite(d, a, (603, 88), (767, 112), 44, leaf=True), Sprite(d, a, (772, 297), (588, 318), 52, leaf=True),
                       Sprite(d, a, (157, 415), (242, 238), 52, leaf=True)]
        out["flower"] = [Sprite(d, a, (414, 498), (414, 246), 128), Sprite(d, a, (900, 792), (900, 612), 92)]
    except Exception as e:  # noqa: BLE001
        print("courtyard_pots_maps: periwinkle scan unavailable:", e)
    try:
        d = _lin(_read(scan_map("shrub_02", "Diffuse"))[..., :3])
        a = _read(scan_map("shrub_02", "Alpha", "png"))[..., 0]
        out["lance"] = [Sprite(d, a, (272, 868), (240, 300), 76, leaf=True), Sprite(d, a, (585, 858), (578, 328), 62, leaf=True),
                        Sprite(d, a, (790, 838), (757, 420), 56, leaf=True), Sprite(d, a, (942, 835), (893, 420), 56, leaf=True),
                        Sprite(d, a, (408, 808), (378, 440), 46, leaf=True)]
    except Exception as e:  # noqa: BLE001
        print("courtyard_pots_maps: shrub_02 scan unavailable:", e)
    try:
        d = _lin(_read(scan_map("shrub_04", "Diffuse"))[..., :3])
        a = _read(scan_map("shrub_04", "Alpha", "png"))[..., 0]
        out["oval"] = [Sprite(d, a, (140, 325), (215, 105), 52, leaf=True), Sprite(d, a, (585, 330), (565, 80), 52, leaf=True),
                       Sprite(d, a, (685, 590), (655, 400), 46, leaf=True), Sprite(d, a, (300, 935), (290, 660), 52, leaf=True),
                       Sprite(d, a, (460, 945), (430, 720), 46, leaf=True), Sprite(d, a, (625, 895), (600, 705), 46, leaf=True)]
    except Exception as e:  # noqa: BLE001
        print("courtyard_pots_maps: shrub_04 scan unavailable:", e)
    return out


def _line(rgb, alpha, pts, r0, r1, col, clip):
    """A tapering stem along pts (pixel coords)."""
    x0c, y0c, wc, hc = clip
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        rad = r0 + (r1 - r0) * i / max(n - 1, 1)
        r = int(rad + 2)
        xa, xb = max(int(x) - r, x0c), min(int(x) + r + 1, x0c + wc)
        ya, yb = max(int(y) - r, y0c), min(int(y) + r + 1, y0c + hc)
        if xb <= xa or yb <= ya:
            continue
        ys, xs = np.mgrid[ya:yb, xa:xb]
        a = np.clip(rad - np.hypot(xs + 0.5 - x, ys + 0.5 - y) + 0.5, 0, 1)
        sh = (1 - 0.3 * np.clip((xs + 0.5 - x) / max(rad, 0.5), -1, 1))[..., None]
        rgb[ys, xs] = rgb[ys, xs] * (1 - a[..., None]) + np.array(col) * sh * a[..., None]
        alpha[ys, xs] = np.maximum(alpha[ys, xs], a)


def _path(rng, p0, ang, length, step=1.5, wobble=0.012, bend=0.0):
    pts, x, y, a = [], p0[0], p0[1], ang
    for k in range(int(length / step)):
        pts.append((x, y))
        a += bend + rng.normal(0, wobble)
        x += math.cos(a) * step
        y += math.sin(a) * step
    return pts


def _blades(rgb, alpha, rng, cell, n, base_col, tip_col, width, droop, spread):
    """A fan of grass blades from the cell's bottom centre (painted: tapering, keeled blades
    with a lighter midrib, darker toward the crown, each bowing outward by up to `droop` rad)."""
    x0, y0, w, h = cell
    for _ in range(n):
        ang = -math.pi / 2 + rng.normal(0, spread)
        ang = max(min(ang, -math.pi / 2 + 0.42), -math.pi / 2 - 0.42)
        L = h * rng.uniform(0.55, 0.96) * (1 - 0.3 * abs(ang + math.pi / 2))
        x, y = x0 + w / 2 + rng.normal(0, w * 0.05), y0 + h - 6
        side = 1 if ang > -math.pi / 2 else -1
        steps = int(L / 1.6)
        bend = droop * side * rng.uniform(0.5, 1.3) / steps
        tcol = np.array(tip_col) * rng.uniform(0.8, 1.2)
        bcol = np.array(base_col) * rng.uniform(0.85, 1.15)
        wd = width * rng.uniform(0.75, 1.25)
        a = ang
        for i in range(steps):
            t = i / steps
            rad = max(0.9, wd * (1 - t) ** 0.8)
            r = int(rad + 2)
            xa, xb = max(int(x) - r, x0), min(int(x) + r + 1, x0 + w)
            ya, yb = max(int(y) - r, y0), min(int(y) + r + 1, y0 + h)
            if xb > xa and yb > ya:
                ys, xs = np.mgrid[ya:yb, xa:xb]
                dd = np.hypot(xs + 0.5 - x, ys + 0.5 - y)
                al = np.clip(rad - dd + 0.5, 0, 1)
                col = bcol * (1 - t) ** 1.3 + tcol * (1 - (1 - t) ** 1.3)
                rib = np.exp(-(dd / max(rad * 0.35, 0.5)) ** 2) * 0.22
                pix = col * (1 + rib[..., None]) * (1 - 0.22 * (dd / (rad + 0.5))[..., None])
                rgb[ys, xs] = rgb[ys, xs] * (1 - al[..., None]) + pix * al[..., None]
                alpha[ys, xs] = np.maximum(alpha[ys, xs], al)
            a += bend * (0.4 + 1.2 * t)
            x += math.cos(a) * 1.6
            y += math.sin(a) * 1.6


def foliage(force=False):
    name = LEAF + "_BaseColor"
    path = os.path.join(TEX, name + ".png")
    if _fresh([name]) and not force:
        return path
    rng = np.random.default_rng(83)
    S = _sprites()
    rgb = np.zeros((N, N, 3))
    alpha = np.zeros((N, N))
    means = {}

    # fern fronds: the scan's fronds, squeezed across (the cards are wider than the cells)
    fern_t = (0.075, 0.165, 0.030)
    for k, cname in enumerate(("frondA", "frondB", "frondC")):
        cell = CELLS_PX[cname]
        x0, y0, w, h = cell
        if "frond" in S:
            spr = S["frond"][k]
            L = np.linalg.norm(spr.tip - spr.base)
            s = (h - 10) / L
            width = (w / 2 - 3) / (spr.hw * s)
            stamp(rgb, alpha, spr, (x0 + w / 2, y0 + h - 4), (x0 + w / 2, y0 + 6), width,
                  _gain(spr, fern_t, rng.uniform(0.92, 1.08)), clip=cell)
        means[cname] = fern_t

    # star jasmine strands: a wiry stem with side shoots, opposite pairs of glossy oval leaves
    # (smaller toward the tips), clusters of cream-white stars at the shoot tips
    jas_t = (0.060, 0.120, 0.030)
    for cname in ("jasmineA", "jasmineB"):
        cell = CELLS_PX[cname]
        x0, y0, w, h = cell
        stem = _path(rng, (x0 + w / 2, y0 + h - 4), -math.pi / 2, h - 16, 1.5, 0.010)
        stem = [(x0 + w / 2 + (x - x0 - w / 2) * 0.5 + 9 * math.sin(i * 0.016), y) for i, (x, y) in enumerate(stem)]
        shoots = [stem]
        for frac in (0.22, 0.42, 0.62):
            i0 = int(len(stem) * frac)
            sg = 1 if rng.random() < 0.5 else -1
            shoots.append(_path(rng, stem[i0], -math.pi / 2 + sg * rng.uniform(0.28, 0.40), h * rng.uniform(0.16, 0.24),
                                1.5, 0.012, -sg * 0.002))
        for k, pts in enumerate(shoots):
            _line(rgb, alpha, pts, 2.2 if k == 0 else 1.5, 0.9, (0.10, 0.075, 0.035), cell)
        tips = []
        if "leaf" in S:
            for k, pts in enumerate(shoots):
                i = 26 if k == 0 else 14
                while i < len(pts) - 6:
                    t = i / len(pts)
                    px, py = pts[i]
                    qx, qy = pts[min(i + 2, len(pts) - 1)]
                    ta = math.atan2(qy - py, qx - px)
                    L = rng.uniform(56, 80) * (1 - 0.40 * t) * (1.0 if k == 0 else 0.85)
                    for sg in (1, -1):
                        la = ta + sg * rng.uniform(0.65, 1.15)
                        spr = S["leaf"][rng.integers(len(S["leaf"]))]
                        tip = (px + math.cos(la) * L, py + math.sin(la) * L)
                        stamp(rgb, alpha, spr, (px, py), tip, rng.uniform(0.85, 1.0),
                              _gain(spr, jas_t, rng.uniform(0.75, 1.25), 0.85), flip=rng.random() < 0.5, clip=cell)
                    i += int(rng.uniform(26, 36) * (1 - 0.3 * t))
                # young leaves at the tip
                px, py = pts[-1]
                ta = math.atan2(pts[-1][1] - pts[-4][1], pts[-1][0] - pts[-4][0])
                for sg in (1, -1):
                    spr = S["leaf"][rng.integers(len(S["leaf"]))]
                    la = ta + sg * 0.4
                    stamp(rgb, alpha, spr, (px, py), (px + math.cos(la) * 30, py + math.sin(la) * 30), 0.9,
                          _gain(spr, (0.09, 0.17, 0.04)), clip=cell)
                tips.append(pts[-1])
                tips.append(pts[int(len(pts) * 0.7)])
        if "flower" in S:
            for k, (px, py) in enumerate(tips):
                if rng.random() < 0.5:
                    continue
                for _ in range(rng.integers(3, 6)):
                    fx, fy = px + rng.normal(0, 11), py + rng.normal(0, 11) + 6
                    spr = S["flower"][rng.integers(len(S["flower"]))]
                    r = rng.uniform(10, 14)
                    a = rng.uniform(0, 2 * math.pi)
                    stamp(rgb, alpha, spr, (fx - math.cos(a) * r, fy - math.sin(a) * r),
                          (fx + math.cos(a) * r, fy + math.sin(a) * r), 1.0, _flower_col(spr), clip=cell)
        means[cname] = jas_t

    # grasses: golden fountain grass, blue-green sedge
    _blades(rgb, alpha, rng, CELLS_PX["grass"], 14, (0.08, 0.13, 0.03), (0.26, 0.30, 0.07), 5.0, 0.30, 0.22)
    _blades(rgb, alpha, rng, CELLS_PX["grass"], 26, (0.12, 0.16, 0.035), (0.46, 0.41, 0.11), 6.0, 0.30, 0.21)
    _blades(rgb, alpha, rng, CELLS_PX["sedge"], 60, (0.05, 0.10, 0.065), (0.17, 0.27, 0.18), 2.6, 0.5, 0.24)
    means["grass"] = (0.22, 0.21, 0.06)
    means["sedge"] = (0.09, 0.15, 0.10)

    # olive-like sprigs: a twig with alternate lanceolate leaves, grey-green / silver beneath
    for cname, silver in (("oliveA", 0.22), ("oliveB", 0.42)):
        cell = CELLS_PX[cname]
        x0, y0, w, h = cell
        twig = _path(rng, (x0 + w / 2, y0 + h - 4), -math.pi / 2 + rng.uniform(-0.1, 0.1), h * 0.86, 1.5, 0.02)
        _line(rgb, alpha, twig, 2.0, 0.8, (0.16, 0.13, 0.10), cell)
        side_twigs = []
        for frac, sg in ((0.22, 1), (0.40, -1), (0.58, 1), (0.74, -1)):
            i = int(len(twig) * frac)
            side_twigs.append(_path(rng, twig[i], -math.pi / 2 + sg * rng.uniform(0.6, 0.9), h * 0.36 * (1.1 - frac * 0.6),
                                    1.5, 0.02))
            _line(rgb, alpha, side_twigs[-1], 1.4, 0.7, (0.16, 0.13, 0.10), cell)
        if "lance" in S:
            for pts in [twig] + side_twigs:
                sg = 1
                for i in range(8, len(pts) - 2, 8):
                    px, py = pts[i]
                    qx, qy = pts[min(i + 2, len(pts) - 1)]
                    ta = math.atan2(qy - py, qx - px)
                    la = ta + sg * rng.uniform(0.45, 0.8)
                    sg = -sg
                    L = rng.uniform(50, 64) * (1 - 0.3 * i / len(pts))
                    spr = S["lance"][rng.integers(len(S["lance"]))]
                    col = (0.22, 0.24, 0.16) if rng.random() < silver else (0.10, 0.125, 0.06)
                    stamp(rgb, alpha, spr, (px, py), (px + math.cos(la) * L, py + math.sin(la) * L),
                          rng.uniform(0.85, 1.0), _gain(spr, col, rng.uniform(0.85, 1.15), 0.8),
                          flip=rng.random() < 0.5, clip=cell)
                px, py = pts[-1]
                spr = S["lance"][0]
                stamp(rgb, alpha, spr, (px, py + 3), (px, py - 40), 0.7, _gain(spr, (0.12, 0.14, 0.07)), clip=cell)
        means[cname] = (0.16, 0.18, 0.12)

    # box: a sprig of small glossy leaves; a dense opaque leaf mat for the clipped ball's core
    box_t = (0.058, 0.110, 0.026)
    new_t = (0.12, 0.17, 0.04)
    small = S.get("oval") or S.get("leaf")
    cell = CELLS_PX["boxSprig"]
    x0, y0, w, h = cell
    for k in range(5):
        ang = -math.pi / 2 + (k - 2) * 0.32 + rng.uniform(-0.1, 0.1)
        tw = _path(rng, (x0 + w / 2 + (k - 2) * 6, y0 + h - 4), ang, h * rng.uniform(0.6, 0.9), 1.5, 0.03)
        _line(rgb, alpha, tw, 1.2, 0.6, (0.12, 0.10, 0.06), cell)
        if small:
            for i in range(6, len(tw), 7):
                px, py = tw[i]
                for sg in (1, -1):
                    la = ang + sg * rng.uniform(0.6, 1.2)
                    L = rng.uniform(15, 21)
                    spr = small[rng.integers(len(small))]
                    young = i > len(tw) * 0.7 and rng.random() < 0.6
                    stamp(rgb, alpha, spr, (px, py), (px + math.cos(la) * L, py + math.sin(la) * L), 0.9,
                          _gain(spr, new_t if young else box_t, rng.uniform(0.8, 1.25), 0.85),
                          flip=rng.random() < 0.5, clip=cell)
    means["boxSprig"] = box_t
    cell = CELLS_PX["boxMat"]
    x0, y0, w, h = cell
    rgb[y0:y0 + h, x0:x0 + w] = np.array((0.010, 0.018, 0.005))
    alpha[y0:y0 + h, x0:x0 + w] = 1.0
    if small:
        # three layers of leaf rosettes, deep (dark) to outer (lit, larger): the clipped surface
        # reads as depth, not a flat green smear
        for layer, (count, gain_, size) in enumerate(((260, 0.45, 15), (190, 0.8, 19), (130, 1.25, 23))):
            for _ in range(count):
                cx_, cy_ = rng.uniform(x0, x0 + w), rng.uniform(y0, y0 + h)
                a0 = rng.uniform(0, 2 * math.pi)
                for q in range(rng.integers(5, 9)):
                    la = a0 + q * 2.4 + rng.uniform(-0.3, 0.3)
                    L = size * rng.uniform(0.8, 1.2)
                    spr = small[rng.integers(len(small))]
                    young = layer == 2 and rng.random() < 0.25
                    stamp(rgb, alpha, spr, (cx_, cy_), (cx_ + math.cos(la) * L, cy_ + math.sin(la) * L), 0.95,
                          _gain(spr, new_t if young else box_t, gain_ * rng.uniform(0.8, 1.2), 0.85),
                          flip=rng.random() < 0.5, clip=cell)
    alpha[y0:y0 + h, x0:x0 + w] = 1.0
    means["boxMat"] = box_t

    # transparent texels take their cell's mean leaf colour (no dark fringes once mip-mapped),
    # and a margin keeps neighbouring cells apart
    for cname, (x0, y0, w, h) in CELLS_PX.items():
        sl = (slice(y0, y0 + h), slice(x0, x0 + w))
        a = alpha[sl]
        if cname != "boxMat":
            a[:3, :] = 0
            a[-2:, :] = 0
            a[:, :3] = 0
            a[:, -3:] = 0
        c = rgb[sl]
        rgb[sl] = np.where(a[..., None] > 0.02, c, np.array(means.get(cname, (0.08, 0.12, 0.04))))
    _save_png(name, textures._to_srgb(rgb), alpha)
    _stamp()                 # (the clay maps are always built first: both sets are current now)
    return path


def build_all(force=False):
    c = clay(force)
    f = foliage(force)
    return c, f
