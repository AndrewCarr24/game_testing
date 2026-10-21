"""Indoor specimen tree for the double-height hall: a multi-stemmed olive (Olea europaea),
about 4.6 m tall, in a honed limestone drum planter dressed with black beach pebbles.

Four fluted, twisting stems rise out of one gnarled root crown and part into a narrow,
upright vase of a crown (it stands in a corner, 0.75 m from the south wall and 0.9 m from
the side wall, so the crown is trained to that footprint). Every leaf clump is reached by a
branch grown from the nearest wood (so thinner branches fork off thicker ones), each clump
ends in a few twigs, and the twigs carry V-folded sprig cards: alpha-tested olive shoots
with opposite pairs of narrow lanceolate leaves, dark grey-green above and silver below
(T_EntryTree_Leaves_BaseColor / _Normal, 1024 RGBA atlas generated here when missing).
Cards that face down show the silver-heavy sprig, which is what you see from below.
Bark is a Poly Haven scan (bark_willow_02, CC0, grey and interlaced like old olive bark:
T_EntryTree_Bark_BaseColor / _Normal), wrapped a whole number of times round each tube
so it never shows a seam, its scale following the tube's girth.

Parts: Planter (limestone), SoilNoCollide + PebblesNoCollide (M_EntryTree_Pebble: the entry's dark marble
texture, satin; each pebble UV'd to its own patch of it), Trunk (stems below 2 m: the only wood collider), LimbsNoCollide
(stems above 2 m, branches, twigs), Canopy (leaf cards, no collider).
Origin: floor centre of the planter. Units are metres.
"""
import importlib
import math
import os
import random
import sys
import urllib.request

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, textures  # noqa: E402
import entry_sculpture  # noqa: E402  (limestone material)
import entry_vanity  # noqa: E402  (dark marble material: the pebbles)

importlib.reload(common)
importlib.reload(textures)
importlib.reload(entry_sculpture)
importlib.reload(entry_vanity)

NAME = "EntryTree"

P = dict(
    name=NAME,
    height=4.6,
    seed=3,
    planter_r=0.50, planter_h=0.72, planter_wall=0.07,
    stems=4,
    blob_segments=7, blob_rings=4,     # (kept for old overrides; the blob canopy is gone)
    mulch_z=0.655,                     # soil level under the pebbles
    pebbles=175,
    clumps=62,                         # leaf clumps in the crown
    crown_c=(0.0, 0.24, 3.42),         # crown ellipsoid centre and semi-axes
    crown_r=(0.70, 0.84, 1.16),
    crown_floor=2.55,                  # lowest clump centre (leaves stay above ~2.3 m)
    card_size=(0.27, 0.38),            # sprig card length (m); leaves ~5.5-7.5 cm
    split_z=2.0,                       # Trunk mesh (collider) below, LimbsNoCollide above
    bark_tile=0.45,                    # girth that gets one wrap of the 1 m bark scan
    # footprint the crown is fitted into (room corner: side wall at |x| 0.9, south wall at y -0.75)
    extent_lo=(-0.84, -0.68),
    extent_hi=(0.84, 1.22),
)

TEX = textures.TEX_DIR
UA = {"User-Agent": "game_testing-entry_tree/1.0 (CC0 assets)"}


# ============================================================== textures

def _save_rgba(name, rgba_yup, non_color=False):
    """Save an RGBA float array whose row 0 is the BOTTOM of the image (Blender order)."""
    path = os.path.join(TEX, name + ".png")
    h, w, _ = rgba_yup.shape
    old = bpy.data.images.get(name)
    if old is not None:
        bpy.data.images.remove(old)
    img = bpy.data.images.new(name, w, h, alpha=True)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    img.alpha_mode = "STRAIGHT"
    img.pixels.foreach_set(np.clip(rgba_yup, 0, 1).astype(np.float32).ravel())
    img.filepath_raw = path + ".tmp.png"
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    os.replace(path + ".tmp.png", path)
    return path


class Canvas:
    """One atlas cell, y-up pixel coordinates (row 0 = bottom = the sprig's base)."""

    def __init__(self, S, bg):
        self.S = S
        self.rgb = np.ones((S, S, 3)) * np.array(bg)
        self.a = np.zeros((S, S))
        self.n = np.zeros((S, S, 3))
        self.n[..., 2] = 1.0

    def window(self, pts, pad):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x0, x1 = int(max(0, min(xs) - pad)), int(min(self.S, max(xs) + pad + 1))
        y0, y1 = int(max(0, min(ys) - pad)), int(min(self.S, max(ys) + pad + 1))
        if x1 <= x0 or y1 <= y0:
            return None
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(float) + 0.5
        return (slice(y0, y1), slice(x0, x1)), xx, yy

    def put(self, sl, cov, col, nrm, shadow=None):
        if shadow is not None:          # soft contact shadow on what lies underneath
            self.rgb[sl] *= (1 - 0.32 * shadow * (1 - cov))[..., None]
        c = cov[..., None]
        self.rgb[sl] = self.rgb[sl] * (1 - c) + col * c
        self.n[sl] = self.n[sl] * (1 - c) + nrm * c
        self.a[sl] = np.maximum(self.a[sl], cov)


def _leaf(cv, rng, p0, ang, L, W, col, under, bend=0.0):
    """Narrow lanceolate olive leaf from its petiole at p0 along angle `ang` (radians, y-up),
    length L, half-width W (px). Top: dark grey-green with a pale midrib and a silvery
    rolled margin; underside: silver-scaled, a raised yellowish midrib. Normals: a domed
    blade (revolute margins) arching along its length."""
    d = np.array([math.cos(ang), math.sin(ang)])
    q = np.array([-d[1], d[0]])
    p0 = np.array(p0, float)
    tip = p0 + d * L
    w = cv.window([p0, tip, p0 + q * W * 1.5, p0 - q * W * 1.5, tip + q * W * 1.5, tip - q * W * 1.5], W + 6)
    if w is None:
        return
    sl, xx, yy = w
    rx, ry = xx - p0[0], yy - p0[1]
    a = (rx * d[0] + ry * d[1]) / L
    b = rx * q[0] + ry * q[1] - bend * L * np.clip(a, 0, 1) ** 2
    ac = np.clip(a, 0, 1)
    pet = 0.07
    t = np.clip((ac - pet) / (1 - pet), 0, 1)
    hw = W * np.maximum(np.sin(math.pi * t ** 0.92), 0) ** 0.62
    hw = np.where(ac < pet, W * 0.13, np.maximum(hw, W * 0.13 * (t < 0.15)))
    sd = np.abs(b) - hw
    ends = np.clip(a * L + 0.5, 0, 1) * np.clip((1 - a) * L + 0.5, 0, 1)
    cov = np.clip(0.5 - sd, 0, 1) * ends
    shadow = np.clip(0.5 - (sd - 3.5) / 3.0, 0, 1) * ends * np.clip((a * L + 3) / 6, 0, 1)
    bn = np.clip(b / np.maximum(hw, 0.5), -1, 1)
    mid = np.exp(-(b / 1.3) ** 2) * (ac > pet * 0.5) * (ac < 0.93)
    grain = rng.normal(0, 1, cov.shape) * 0.035
    if not under:
        c = np.array(col)[None, None, :] * (0.9 + 0.16 * ac)[..., None]
        c = c * (1 - 0.07 * bn)[..., None]                      # one half a touch darker
        c = c * (1 + 0.35 * mid)[..., None]                     # pale, impressed midrib
        rim = np.clip((np.abs(bn) - 0.80) / 0.2, 0, 1) * (t > 0.08)
        silver = np.array([0.30, 0.31, 0.25])
        c = c * (1 - 0.30 * rim[..., None]) + silver * 0.30 * rim[..., None]
        tilt = 0.42 * bn + 0.30 * bn ** 3 - 0.18 * np.sign(b) * mid
    else:
        speck = rng.uniform(0.9, 1.08, cov.shape)
        c = np.array(col)[None, None, :] * speck[..., None] * (0.92 + 0.1 * ac)[..., None]
        c = c * (1 - 0.18 * mid)[..., None] + np.array([0.06, 0.05, 0.0]) * mid[..., None]
        tilt = 0.30 * bn + 0.35 * bn ** 3 + 0.25 * np.sign(b) * mid
    c = c * (1 + grain * (1 - mid))[..., None]
    along = 0.22 * (ac - 0.5)
    nx = q[0] * np.sin(tilt) + d[0] * np.sin(along)
    ny = q[1] * np.sin(tilt) + d[1] * np.sin(along)
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0.05, 1))
    cv.put(sl, cov, c, np.stack([nx, ny, nz], -1), shadow)


def _twig(cv, pts, r0, r1, col):
    """A twig: capsules along the polyline, radius r0 -> r1 px, cylindrical normals."""
    n = len(pts)
    for i in range(n - 1):
        A, B = np.array(pts[i], float), np.array(pts[i + 1], float)
        ra = r0 + (r1 - r0) * i / (n - 1)
        rb = r0 + (r1 - r0) * (i + 1) / (n - 1)
        w = cv.window([A, B], max(ra, rb) + 3)
        if w is None:
            continue
        sl, xx, yy = w
        AB = B - A
        L2 = max(AB @ AB, 1e-6)
        t = np.clip(((xx - A[0]) * AB[0] + (yy - A[1]) * AB[1]) / L2, 0, 1)
        px, py = A[0] + AB[0] * t - xx, A[1] + AB[1] * t - yy
        dist = np.sqrt(px * px + py * py)
        r = ra + (rb - ra) * t
        cov = np.clip(r - dist + 0.5, 0, 1)
        dn = AB / math.sqrt(L2)
        q = np.array([-dn[1], dn[0]])
        off = np.clip(-(px * q[0] + py * q[1]) / np.maximum(r, 0.5), -1, 1)
        nx, ny = q[0] * off * 0.85, q[1] * off * 0.85
        nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0.05, 1))
        shade = (1 - 0.25 * off)[..., None]
        cv.put(sl, cov, np.array(col) * shade, np.stack([nx, ny, nz], -1))


TOPS = [(0.050, 0.066, 0.034), (0.060, 0.074, 0.038), (0.044, 0.058, 0.032), (0.068, 0.080, 0.044),
        (0.056, 0.064, 0.036), (0.074, 0.078, 0.040)]
UNDER = (0.185, 0.215, 0.165)
OLD = (0.085, 0.080, 0.036)          # the odd yellowing older leaf
TWIG = (0.115, 0.11, 0.075)


def _path(rng, base, ang, length, curl, steps=14):
    pts, p, a = [], np.array(base, float), ang
    for k in range(steps + 1):
        pts.append(p.copy())
        a += curl / steps + rng.uniform(-0.04, 0.04)
        p = p + np.array([math.cos(a), math.sin(a)]) * length / steps
    return pts


def _shoot(cv, rng, pts, leaf_l, under_p, thick=1.0):
    """An olive shoot along pts: a twig with opposite, decussate leaf pairs that shrink
    towards the tip; each leaf jittered in angle, size and twist (some seen edge-on, some
    turned to show their silver underside, now and then one missing)."""
    steps = len(pts) - 1
    length = sum(np.linalg.norm(pts[i + 1] - pts[i]) for i in range(steps))
    _twig(cv, pts, max(3.0, leaf_l * 0.042) * thick, 1.3, TWIG)
    spacing = leaf_l * rng.uniform(0.30, 0.38)
    s = spacing * rng.uniform(0.6, 1.0)
    k = int(rng.integers(2))
    seg = length / steps
    leaves = []
    while s < length - 4:
        i = min(int(s / seg), steps - 1)
        f = s / seg - i
        node = pts[i] * (1 - f) + pts[i + 1] * f
        da = math.atan2(*(pts[i + 1] - pts[i])[::-1])
        frac = s / length
        size = leaf_l * (1.0 - 0.6 * max(0.0, frac - 0.5) / 0.5) * rng.uniform(0.8, 1.12)
        flat = (k % 2 == 0)             # decussate: every other pair is seen edge-on
        for side in (-1, 1):
            if rng.uniform(0, 1) < 0.07:
                continue
            spread = (rng.uniform(0.6, 1.15) if flat else rng.uniform(0.2, 0.6)) * (1 - 0.3 * frac)
            Lk = size * (rng.uniform(0.9, 1.05) if flat else rng.uniform(0.5, 0.78))
            Wk = Lk * (rng.uniform(0.090, 0.108) if flat else rng.uniform(0.065, 0.085))
            under = rng.uniform(0, 1) < (under_p if flat else under_p + 0.15)
            if under:
                col = UNDER
            elif rng.uniform(0, 1) < 0.05:
                col = OLD
            else:
                col = TOPS[rng.integers(len(TOPS))]
            g = rng.uniform(0.85, 1.15)
            col = (col[0] * g * rng.uniform(0.96, 1.04), col[1] * g, col[2] * g * rng.uniform(0.94, 1.02))
            leaves.append((node.copy(), da + side * spread + rng.uniform(-0.12, 0.12), Lk, max(Wk, 4.2), col,
                           under, side * rng.uniform(-0.06, 0.10)))
        s += spacing * rng.uniform(0.8, 1.2)
        k += 1
    tip = pts[-1]
    da = math.atan2(*(pts[-1] - pts[-2])[::-1])
    for side in (-1, 1):                 # terminal pair, still folded
        leaves.append((tip - (pts[-1] - pts[-2]) * 0.3, da + side * 0.16, leaf_l * rng.uniform(0.32, 0.42), 4.0,
                       TOPS[5], False, 0.0))
    order = sorted(range(len(leaves)), key=lambda j: j + rng.uniform(-2.5, 2.5))
    for j in order:
        node, la, Lk, Wk, col, under, bend = leaves[j]
        _leaf(cv, rng, node, la, Lk, Wk, col, under, bend)


def _sprig(rng, S, kind):
    """One atlas cell (S px): a leading shoot with side shoots fanning off it (kind 0: two,
    1: three, 2: one long and one short), kind 3 the same seen from below (mostly silver
    undersides). Side shoots grow from the leader's twig and are drawn under it."""
    cv = Canvas(S, (0.07, 0.08, 0.05))
    leaf_l = S * 0.20
    under = 0.60 if kind == 3 else 0.16
    base = (S / 2 + rng.uniform(-6, 6), 8)
    lead = _path(rng, base, math.pi / 2 + rng.uniform(-0.1, 0.1), S * rng.uniform(0.80, 0.88),
                 rng.uniform(-0.3, 0.3))
    n_side = {0: 2, 1: 3, 2: 2, 3: 3}[kind]
    at = sorted(rng.uniform(0.10, 0.45, n_side))
    sides = [(-1) ** (j + int(rng.integers(2))) for j in range(n_side)]
    for j in range(n_side):
        i = int(at[j] * (len(lead) - 1))
        d = lead[i + 1] - lead[i]
        da = math.atan2(d[1], d[0])
        length = S * rng.uniform(0.45, 0.6) * (1 - 0.45 * at[j])
        sp = _path(rng, lead[i], da + sides[j] * rng.uniform(0.6, 0.95), length,
                   -sides[j] * rng.uniform(0.25, 0.55), steps=10)
        _shoot(cv, rng, sp, leaf_l * rng.uniform(0.85, 0.95), under, thick=0.8)
    _shoot(cv, rng, lead, leaf_l, under)
    return cv


def _blur(img, sigma):
    """Gaussian blur (wrapped) of a 2D array via FFT."""
    h, w = img.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2 * (math.pi * sigma) ** 2 * (fx * fx + fy * fy))
    return np.real(np.fft.ifft2(np.fft.fft2(img) * g))


def leaf_atlas(n=1024, seed=12, force=False):
    """RGBA atlas of four olive sprigs (2 x 2 cells of n/2, base at each cell's bottom) and
    its tangent-space normal map. Returns (base_path, normal_path)."""
    bpath = os.path.join(TEX, "T_EntryTree_Leaves_BaseColor.png")
    npath = os.path.join(TEX, "T_EntryTree_Leaves_Normal.png")
    if os.path.exists(bpath) and os.path.exists(npath) and not force:
        return bpath, npath
    rng = np.random.default_rng(seed)
    S = n // 2
    rgb = np.zeros((n, n, 3))
    alpha = np.zeros((n, n))
    nrm = np.zeros((n, n, 3))
    for k in range(4):
        cv = _sprig(rng, S, k)
        a = cv.a.copy()
        m = 6                                   # empty margin: no bleeding between cells in mips
        a[:m, :] = 0
        a[-m:, :] = 0
        a[:, :m] = 0
        a[:, -m:] = 0
        # bleed leaf colour into the transparent ground (no dark fringes when mip-mapped)
        wsum = _blur(a, 5.0) + 1e-4
        bg = np.stack([_blur(cv.rgb[..., c] * a, 5.0) / wsum for c in range(3)], -1)
        mean = (cv.rgb * a[..., None]).sum((0, 1)) / max(a.sum(), 1)
        fill = np.clip(wsum[..., None] / 0.05, 0, 1)
        bg = bg * fill + mean * (1 - fill)
        cell_rgb = np.where(a[..., None] > 0.02, cv.rgb, bg)
        nn = cv.n / np.linalg.norm(cv.n, axis=-1, keepdims=True)
        x0, y0 = (k % 2) * S, (k // 2) * S
        rgb[y0:y0 + S, x0:x0 + S] = cell_rgb
        alpha[y0:y0 + S, x0:x0 + S] = a
        nrm[y0:y0 + S, x0:x0 + S] = nn
    base = np.concatenate([textures._to_srgb(rgb), alpha[..., None]], -1)
    _save_rgba("T_EntryTree_Leaves_BaseColor", base)
    nmap = np.concatenate([nrm * 0.5 + 0.5, np.ones((n, n, 1))], -1)
    _save_rgba("T_EntryTree_Leaves_Normal", nmap, non_color=True)
    return bpath, npath


# atlas cells (u0, v0), each 0.5 x 0.5 UV, sprig base at the bottom centre
CELLS = [(0.0, 0.0), (0.5, 0.0), (0.0, 0.5), (0.5, 0.5)]
UNDERSIDE_CELL = 3


BARK_SCAN = "bark_willow_02"
BARK_MEAN = (0.150, 0.138, 0.118)      # linear mean of the graded bark: olive grey


def _fetch_scan(mp):
    folder = os.path.join(textures.TEX_DIR, "..", "..", "build", "polyhaven", "entry_tree")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{BARK_SCAN}_{mp}_1k.jpg")
    if not os.path.exists(path):
        url = f"https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/{BARK_SCAN}/{BARK_SCAN}_{mp}_1k.jpg"
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            data = r.read()
        with open(path + ".tmp", "wb") as f:
            f.write(data)
        os.replace(path + ".tmp", path)
    return path


def bark_maps(force=False):
    """Poly Haven bark_willow_02 (CC0) 1k: base colour graded to olive grey (half
    desaturated, then a per-channel gain to BARK_MEAN) and the GL normal map, written to
    assets/textures once. None when the scan can't be fetched (offline first build)."""
    base = os.path.join(TEX, "T_EntryTree_Bark_BaseColor.png")
    nor = os.path.join(TEX, "T_EntryTree_Bark_Normal.jpg")
    if os.path.exists(base) and os.path.exists(nor) and not force:
        return dict(BaseColor=base, Normal=nor)
    try:
        diff_src, nor_src = _fetch_scan("diff"), _fetch_scan("nor_gl")
    except Exception as e:  # noqa: BLE001
        print(f"entry_tree: bark scan unavailable ({e}); flat colour")
        return None
    img = bpy.data.images.load(diff_src)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, :3]   # row 0 = top
    bpy.data.images.remove(img)
    lin = np.where(px <= 0.04045, px / 12.92, ((px + 0.055) / 1.055) ** 2.4)
    lum = (lin @ np.array([0.2126, 0.7152, 0.0722]))[..., None]
    lin = lin * 0.5 + lum * 0.5
    lin = lin * (np.array(BARK_MEAN) / lin.reshape(-1, 3).mean(0))
    textures._save("T_EntryTree_Bark_BaseColor", textures._to_srgb(lin))
    import shutil
    shutil.copyfile(nor_src, nor + ".tmp")
    os.replace(nor + ".tmp", nor)
    return dict(BaseColor=base, Normal=nor)


# ============================================================== materials

def bark_material():
    maps = bark_maps()
    if not maps:
        return common.pbr_material("M_EntryTree_Bark", (0.20, 0.185, 0.16), roughness=0.9)
    m = common.pbr_material("M_EntryTree_Bark", (1, 1, 1), roughness=0.88)
    common.set_base_color_map(m, textures.load(maps["BaseColor"]))
    common.set_normal_map(m, textures.load(maps["Normal"], non_color=True), 1.4)
    return m


def leaf_material():
    """Alpha-tested (glTF alphaMode MASK via the rounded alpha), double-sided."""
    m = common.pbr_material("M_EntryTree_Leaves", (1, 1, 1), roughness=0.52)
    bpath, npath = leaf_atlas()
    img = textures.load(bpath)
    img.alpha_mode = "STRAIGHT"
    nodes, links = m.node_tree.nodes, m.node_tree.links
    bsdf = next(nd for nd in nodes if nd.type == "BSDF_PRINCIPLED")
    if not bsdf.inputs["Alpha"].is_linked:
        common.set_base_color_map(m, img)
        tex = next(nd for nd in nodes if nd.type == "TEX_IMAGE" and nd.image == img)
        rnd = nodes.new("ShaderNodeMath")
        rnd.operation = "ROUND"
        rnd.location = (bsdf.location.x - 200, bsdf.location.y - 250)
        links.new(tex.outputs["Alpha"], rnd.inputs[0])
        links.new(rnd.outputs[0], bsdf.inputs["Alpha"])
        common.set_normal_map(m, textures.load(npath, non_color=True), 1.0)
    m.use_backface_culling = False
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "DITHERED"
    return m


# ============================================================== geometry helpers

def spline(pts, per=6):
    q = [Vector(pts[0])] + [Vector(p) for p in pts] + [Vector(pts[-1])]
    out = []
    for i in range(1, len(q) - 2):
        p0, p1, p2, p3 = q[i - 1], q[i], q[i + 1], q[i + 2]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
                              (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(Vector(pts[-1]))
    return out


def smoothstep(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def tri_wave(x):
    """0..1..0 with period 2 (mirrored tiling, continuous)."""
    return 1 - abs((x % 2) - 1)


class Relief:
    """Smooth surface relief for a stem: twisting flutes, two octaves of gnarl, burls."""

    def __init__(self, rng, lobes=3, lobe=0.12, twist=0.5, gnarl=0.05, burls=0, length=1.0):
        self.lobes, self.lobe, self.twist, self.gnarl = lobes, lobe, twist, gnarl
        self.ph = [rng.uniform(0, 2 * math.pi) for _ in range(4)]
        self.burls = [(rng.uniform(0.1, 0.85) * length, rng.uniform(0, 2 * math.pi),
                       rng.uniform(0.08, 0.18), rng.uniform(0.05, 0.12)) for _ in range(burls)]

    def __call__(self, th, s):
        f = 1 + self.lobe * math.sin(self.lobes * th + self.twist * s * 2 * math.pi + self.ph[0])
        f += self.gnarl * (0.6 * math.sin(2 * th + 6.1 * s + self.ph[1]) +
                           0.4 * math.sin(5 * th - 9.7 * s + self.ph[2]) +
                           0.3 * math.sin(3 * th + 17.0 * s + self.ph[3]))
        for s0, t0, amp, w in self.burls:
            d = math.atan2(math.sin(th - t0), math.cos(th - t0))
            f += amp * math.exp(-((s - s0) / w) ** 2 - (d / 0.7) ** 2)
        return f


def sweep(pts, radii, sides, relief=None, tile=0.45):
    """Ring positions swept along pts (parallel-transport frames) plus bark UV coordinates:
    u wraps a whole number of times round (seamless), v advances by arc length over the
    local girth, so the bark keeps its aspect as the tube tapers."""
    n = len(pts)
    tang = [(pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(n)]
    ref = Vector((1, 0, 0)) if abs(tang[0].x) < 0.9 else Vector((0, 1, 0))
    nrm = (ref - tang[0] * ref.dot(tang[0])).normalized()
    rings, s = [], 0.0
    for i in range(n):
        if i:
            s += (pts[i] - pts[i - 1]).length
        t = tang[i]
        nrm = (nrm - t * nrm.dot(t)).normalized()
        bi = t.cross(nrm)
        ring = []
        for k in range(sides):
            th = 2 * math.pi * k / sides
            f = relief(th, s) if relief else 1.0
            ring.append(pts[i] + (nrm * math.cos(th) + bi * math.sin(th)) * radii[i] * f)
        rings.append(ring)
    wraps = max(1, round(2 * math.pi * radii[0] / tile))
    vv = [0.0]
    for i in range(1, n):
        girth = math.pi * (radii[i] + radii[i - 1]) / wraps
        vv.append(vv[-1] + (pts[i] - pts[i - 1]).length / max(girth, 0.004))
    return dict(pts=pts, radii=radii, rings=rings, tang=tang, wraps=wraps, vv=vv, sides=sides)


def emit(bm, uvl, sw, i0, i1, cap=False, uv_off=(0.0, 0.0)):
    """Quads between rings i0..i1 of a sweep into bm (optional cone cap at i1)."""
    rings, vv, wraps, sides = sw["rings"], sw["vv"], sw["wraps"], sw["sides"]
    vs = [[bm.verts.new(q) for q in rings[i]] for i in range(i0, i1 + 1)]
    u0, v0 = uv_off
    for k in range(len(vs) - 1):
        A, B = vs[k], vs[k + 1]
        va, vb = vv[i0 + k] + v0, vv[i0 + k + 1] + v0
        for j in range(sides):
            f = bm.faces.new((A[j], A[(j + 1) % sides], B[(j + 1) % sides], B[j]))
            uj, uk = wraps * j / sides + u0, wraps * (j + 1) / sides + u0
            for loop, uv in zip(f.loops, ((uj, va), (uk, va), (uk, vb), (uj, vb))):
                loop[uvl].uv = uv
    if cap:
        tip = bm.verts.new(sw["pts"][i1] + sw["tang"][i1] * sw["radii"][i1] * 1.2)
        ve = vv[i1] + v0
        for j in range(sides):
            f = bm.faces.new((vs[-1][j], vs[-1][(j + 1) % sides], tip))
            uj, uk = wraps * j / sides + u0, wraps * (j + 1) / sides + u0
            for loop, uv in zip(f.loops, ((uj, ve), (uk, ve), ((uj + uk) / 2, ve + 0.1))):
                loop[uvl].uv = uv
    return sw["tang"][i1]


def tube(bm, uvl, pts, radii, sides, relief=None, cap=False, tile=0.45, uv_off=(0.0, 0.0)):
    sw = sweep(pts, radii, sides, relief, tile)
    return emit(bm, uvl, sw, 0, len(pts) - 1, cap, uv_off)


def taper(n, r0, r1, power=0.85):
    return [r0 + (r1 - r0) * (i / max(n - 1, 1)) ** power for i in range(n)]


# ============================================================== planter

# One stone of T_Entry_Limestone (1 m slabs; in UV the top row's joints are at u = 0, 0.5 and v = 0.5,
# the bottom row's at u = 0.25, 0.75): the drum is
# mapped mirrored inside it, so no paving joint ever lands on the planter.
SLAB = (0.03, 0.53, 0.42, 0.42)        # u0, v0, du, dv (UV units; tile 2 m; image row 0 = v 1)


def build_planter(p, col, root, stone, soil):
    R, H, w = p["planter_r"], p["planter_h"], p["planter_wall"]
    ri = R - w
    mz = p["mulch_z"]
    # outer wall over a recessed shadow-gap plinth, eased arrises, flat honed rim, inner wall
    prof = [(R - 0.035, 0.0), (R - 0.035, 0.028), (R - 0.006, 0.028), (R - 0.0015, 0.0315), (R, 0.037),
            (R, H - 0.009), (R - 0.0025, H - 0.0025), (R - 0.009, H),
            (ri + 0.009, H), (ri + 0.0025, H - 0.0025), (ri, H - 0.009), (ri, mz - 0.06)]
    segs = 64
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    rows = [[bm.verts.new((r * math.cos(2 * math.pi * s / segs), r * math.sin(2 * math.pi * s / segs), z))
             for s in range(segs)] for r, z in prof]
    arc = [0.0]
    for (r0, z0), (r1, z1) in zip(prof[:-1], prof[1:]):
        arc.append(arc[-1] + math.hypot(r1 - r0, z1 - z0))
    u0, v0, du, dv = SLAB
    runs = 4                                  # mirrored runs round the drum (even: closes seamlessly)
    for i in range(len(prof) - 1):
        for s in range(segs):
            t = s + 1
            f = bm.faces.new((rows[i][s], rows[i][t % segs], rows[i + 1][t % segs], rows[i + 1][s]))
            for loop, (ss, ii) in zip(f.loops, ((s, i), (t, i), (t, i + 1), (s, i + 1))):
                x = ss / segs * runs
                loop[uvl].uv = (u0 + du * tri_wave(x), v0 + dv * tri_wave(arc[ii] / 0.8))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # crisp edges only at the plinth's step; the eased arrises shade smooth
    for i in (1, 2):
        for s in range(segs):
            e = bm.edges.get((rows[i][s], rows[i][(s + 1) % segs]))
            if e:
                e.smooth = False
    planter = common.mesh_object(f"{p['name']}_Planter", bm, col, stone, root)

    # ground under the pebbles (dark stone, so the gaps between them read as more stones in shadow)
    sb = bmesh.new()
    rim = [sb.verts.new((ri * math.cos(2 * math.pi * s / 40), ri * math.sin(2 * math.pi * s / 40), mz - 0.004))
           for s in range(40)]
    mid = [sb.verts.new((ri * 0.6 * math.cos(2 * math.pi * s / 40), ri * 0.6 * math.sin(2 * math.pi * s / 40), mz - 0.004))
           for s in range(40)]
    c = sb.verts.new((0, 0, mz - 0.004))
    suv = sb.loops.layers.uv.new("UVMap")
    for s in range(40):
        t = (s + 1) % 40
        for f in (sb.faces.new((rim[s], rim[t], mid[t], mid[s])), sb.faces.new((mid[s], mid[t], c))):
            for loop in f.loops:
                loop[suv].uv = (0.31 + loop.vert.co.x / 0.6, 0.47 + loop.vert.co.y / 0.6)
    common.mesh_object(f"{p['name']}_SoilNoCollide", sb, col, soil, root)
    return planter


def build_pebbles(p, col, root, mat, rng, avoid_r):
    """Black beach pebbles (satin) over the soil: flattened, slightly irregular domes
    (6 sides, 18 triangles), packed by rejection with a little overlap and a few stacked
    on the others; each gets its own patch of the dark marble texture."""
    ri = p["planter_r"] - p["planter_wall"]
    mz = p["mulch_z"]
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    placed = []
    tries = 0
    while len(placed) < p["pebbles"] and tries < 20000:
        tries += 1
        a = rng.uniform(0.030, 0.050) if rng.random() < 0.8 else rng.uniform(0.050, 0.064)
        b = a * rng.uniform(0.62, 0.9)
        re = (a + b) / 2
        r = math.sqrt(rng.random()) * (ri - re * 0.8)
        az = rng.uniform(0, 2 * math.pi)
        x, y = r * math.cos(az), r * math.sin(az)
        if math.hypot(x, y) < avoid_r + a * 0.4:
            continue
        stacked = False
        hits = [q for q in placed if math.hypot(q[0] - x, q[1] - y) < (q[4] + re) * 0.80]
        if hits:
            if len(placed) > p["pebbles"] * 0.75 and len(hits) <= 2 and rng.random() < 0.3:
                stacked = True               # rests on the stones below it
            else:
                continue
        placed.append((x, y, a, b, re, stacked))
    for x, y, a, b, re, stacked in placed:
        h = b * rng.uniform(0.40, 0.58)
        th = rng.uniform(0, math.pi)
        ct, st = math.cos(th), math.sin(th)
        z0 = mz - 0.004 - 0.12 * h + (h * 0.55 if stacked else 0.0)
        tilt = (rng.uniform(-0.15, 0.15), rng.uniform(-0.15, 0.15)) if stacked else (0.0, 0.0)

        def at(rr, ang, zz):
            ex, ey = a * rr * math.cos(ang), b * rr * math.sin(ang)
            ex *= 1 + rng.uniform(-0.06, 0.06)
            ey *= 1 + rng.uniform(-0.06, 0.06)
            px, py = x + ex * ct - ey * st, y + ex * st + ey * ct
            return bm.verts.new((px, py, z0 + zz + tilt[0] * ex + tilt[1] * ey))
        sides = 6
        off = rng.uniform(0, 2 * math.pi)
        top = at(0, 0, h)
        r1 = [at(0.70, off + 2 * math.pi * k / sides, h * 0.80) for k in range(sides)]
        r2 = [at(1.0, off + 2 * math.pi * k / sides + 0.3, h * 0.12) for k in range(sides)]
        faces = []
        for k in range(sides):
            j = (k + 1) % sides
            faces.append(bm.faces.new((top, r1[k], r1[j])))
            faces.append(bm.faces.new((r1[k], r2[k], r2[j], r1[j])))
        uo, vo = rng.uniform(0, 1), rng.uniform(0, 1)
        for f in faces:
            for loop in f.loops:
                co = loop.vert.co
                loop[uvl].uv = (uo + (co.x - x) / 0.9, vo + (co.y - y) / 0.9)      # a small patch each
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    common.mesh_object(f"{p['name']}_PebblesNoCollide", bm, col, mat, root)
    return len(placed)


# ============================================================== tree

def stem_paths(p, rng):
    """Control points for the stems: out of the root crown, winding a little round each
    other, then leaning out into a narrow vase towards the crown's centre (offset +y)."""
    zb = p["mulch_z"] - 0.05
    cx, cy, _ = p["crown_c"]
    out = []
    a0 = rng.uniform(0, 2 * math.pi)
    n = p["stems"]
    for k in range(n):
        a = a0 + 2 * math.pi * k / n + rng.uniform(-0.3, 0.3)
        d = Vector((math.cos(a), math.sin(a), 0))
        side = Vector((-d.y, d.x, 0))
        main = k < 3
        top = rng.uniform(3.55, 4.15) if main else rng.uniform(2.9, 3.3)
        spread = (rng.uniform(0.36, 0.48) if main else rng.uniform(0.46, 0.55))
        twist = rng.uniform(0.07, 0.13) * (1 if k % 2 else -1)
        ctrl = []
        for j, t in enumerate((0.0, 0.08, 0.2, 0.34, 0.5, 0.66, 0.83, 1.0)):
            z = zb + (top - zb) * t
            r = 0.045 + spread * t ** 0.8
            wob = 0.06 * math.sin(t * 8.0 + k * 1.9) * smoothstep(0.05, 0.3, t)
            kink = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)) * 0.045 * smoothstep(0.1, 0.4, t)
            q = d * r + side * (twist * math.sin(t * math.pi) + wob) + kink + \
                Vector((cx, cy, 0)) * smoothstep(0.1, 0.8, t)
            ctrl.append(Vector((q.x, q.y, z)))
        r0 = rng.uniform(0.060, 0.070) if main else rng.uniform(0.040, 0.046)
        out.append((ctrl, r0, main))
    return out


def crown_points(p, rng, n, spacing):
    """Clump centres in the crown ellipsoid, favouring its outer shell (leaves live on the
    outside of a crown; inside is wood), kept apart by Poisson rejection."""
    C, Rr = Vector(p["crown_c"]), Vector(p["crown_r"])
    pts, tries = [], 0
    while len(pts) < n and tries < 30000:
        tries += 1
        d = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1)))
        if d.length < 1e-6:
            continue
        d.normalize()
        f = rng.random() ** 0.3 * 0.92
        q = C + Vector((d.x * Rr.x, d.y * Rr.y, d.z * Rr.z)) * f
        if q.z < p["crown_floor"]:
            continue
        if all((q - o).length > spacing for o in pts):
            pts.append(q)
    return pts


def build_tree(p, col, root, bark, leaf):
    rng = random.Random(p["seed"])
    n = p["name"]
    sz = p["split_z"]
    tile = p["bark_tile"]
    trunk_bm, limb_bm, cards = bmesh.new(), bmesh.new(), bmesh.new()
    tuv, luv, cuv = (b.loops.layers.uv.new("UVMap") for b in (trunk_bm, limb_bm, cards))
    zb = p["mulch_z"] - 0.05

    def uvo():
        return (rng.uniform(0, 1), rng.uniform(0, 1))

    # root crown: a gnarled, buttressed stool the stems grow out of, half buried in the pebbles
    stool_pts = [Vector((0.0, 0.0, zb - 0.03)), Vector((0.005, 0.0, zb + 0.05)), Vector((0.01, 0.005, zb + 0.13)),
                 Vector((0.012, 0.01, zb + 0.21))]
    stool_r = [0.185, 0.16, 0.12, 0.085]
    tube(trunk_bm, tuv, stool_pts, stool_r, 16,
         Relief(rng, lobes=5, lobe=0.22, twist=0.15, gnarl=0.12, burls=4, length=0.3), tile=tile, uv_off=uvo())

    nodes = []                 # (point, radius) the branches can grow from
    tips = []
    stems = []
    for k, (ctrl, r0, main) in enumerate(stem_paths(p, rng)):
        pts = spline(ctrl, per=5)
        nr = len(pts)
        rad = [r0 * (1 + 0.6 * math.exp(-((q.z - zb) / 0.12))) * (1 - 0.76 * (i / (nr - 1)) ** 0.7)
               for i, q in enumerate(pts)]
        length = sum((b - a).length for a, b in zip(pts[:-1], pts[1:]))
        relief = Relief(rng, lobes=3 if main else 2, lobe=0.16 if main else 0.10, twist=0.6 + 0.2 * k,
                        gnarl=0.09, burls=4 if main else 2, length=length)
        sides = 12 if main else 9
        cut = next((i for i, q in enumerate(pts) if q.z >= sz), nr - 1)
        off = uvo()
        sw = sweep(pts, rad, sides, relief, tile)
        emit(trunk_bm, tuv, sw, 0, cut, uv_off=off)
        tip_dir = emit(limb_bm, luv, sw, cut, nr - 1, cap=True, uv_off=off)
        nodes += [(q, r) for q, r in zip(pts, rad) if q.z > 1.85]
        tips.append((pts[-1], tip_dir))
        stems.append((pts, rad, main))

    def branch(start, end, r0, r1, sides, bend=0.16, rise=0.10):
        """A sinuous branch (olive wood kinks and wanders rather than arcing cleanly)."""
        d = end - start
        L = d.length
        dn = d.normalized()
        side = dn.cross(Vector((0, 0, 1)))
        side = side.normalized() if side.length > 1e-3 else Vector((1, 0, 0))
        upv = side.cross(dn).normalized()
        ctrl = [start]
        for j in (1, 2):
            q = start + d * (j / 3) + side * rng.uniform(-bend, bend) * L + upv * rng.uniform(-bend, bend) * L * 0.6
            q.z += rise * L * (0.6 if j == 1 else 0.3)
            ctrl.append(q)
        ctrl.append(end)
        pts = spline(ctrl, per=2 if L < 0.8 else 3)
        rads = taper(len(pts), r0, r1, 0.9)
        rads[0] *= 1.25                       # a little collar where it leaves the parent
        tdir = tube(limb_bm, luv, pts, rads, sides,
                    Relief(rng, lobes=2, lobe=0.05, twist=0.4, gnarl=0.04, length=L), cap=True, tile=tile,
                    uv_off=uvo())
        return pts, rads, tdir

    # main limbs: each big stem forks once or twice between 1.7 and 2.8 m, the limb leaning
    # out of the vase and up into the crown (clumps at their ends too)
    C0 = Vector(p["crown_c"])
    Rr = Vector(p["crown_r"])
    for pts, rad, main in stems:
        if not main:
            continue
        cand = [i for i, q in enumerate(pts) if 1.7 < q.z < 2.8]
        for i in rng.sample(cand, min(len(cand), rng.randint(1, 2))):
            q = pts[i]
            out = Vector((q.x - C0.x, q.y - C0.y, 0))
            out = out.normalized() if out.length > 1e-3 else Vector((1, 0, 0))
            ang = rng.uniform(-0.9, 0.9)
            out = Vector((out.x * math.cos(ang) - out.y * math.sin(ang), out.x * math.sin(ang) + out.y * math.cos(ang), 0))
            d = (out * 0.55 + Vector((0, 0, 1.0))).normalized()
            L = rng.uniform(0.9, 1.4)
            e = q + d * L
            rel = e - C0                                   # keep the end inside the crown
            f = (rel.x / Rr.x) ** 2 + (rel.y / Rr.y) ** 2 + (rel.z / Rr.z) ** 2
            if f > 0.8:
                e = C0 + rel / math.sqrt(f / 0.8)
            bp, br, td = branch(q, e, rad[i] * 0.72, 0.013, 7, bend=0.10, rise=0.05)
            nodes += [(pt, rr) for pt, rr in zip(bp[1:], br[1:])]
            tips.append((bp[-1], td))

    # crown: clumps at the stem tips, then the rest, nearest the axis first, so farther
    # clumps fork off branches already grown (a natural hierarchy of thick to thin)
    C = Vector(p["crown_c"])
    centres = [t + d * 0.12 for t, d in tips]
    centres += crown_points(p, rng, p["clumps"] - len(centres), 0.33)
    head = centres[:len(tips)]
    rest = sorted(centres[len(tips):], key=lambda q: Vector((q.x - C.x, q.y - C.y)).length + 0.15 * abs(q.z - C.z))
    clumps = [(c, d, t) for c, (t, d) in zip(head, tips)]
    for c in rest:
        out = Vector((c.x - C.x, c.y - C.y, 0))
        out = out.normalized() if out.length > 1e-3 else Vector((0, 0, 0))
        tip = c - out * 0.10 - Vector((0, 0, 0.06))
        best = min(nodes, key=lambda nr: (nr[0] - tip).length * (1.0 + 0.6 * max(0.0, nr[0].z - tip.z)))
        q, r = best
        L = (tip - q).length
        if L < 0.10:
            clumps.append((c, (c - q).normalized(), q))
            continue
        r0 = min(r * 0.72, 0.006 + 0.030 * L)
        sides = 5 if r0 > 0.022 else 4 if r0 > 0.011 else 3
        pts, rads, tdir = branch(q, tip, r0, 0.0045, sides)
        nodes += [(pt, rr) for pt, rr in zip(pts[1:-1], rads[1:-1])]
        clumps.append((c, tdir, pts[-1]))

    # leaf clumps: a few twigs off each branch end, V-folded sprig cards on the twigs
    smin, smax = p["card_size"]
    normals = []
    crown_axes = Vector(p["crown_r"])
    up = Vector((0, 0, 1))

    def rvec(s=1.0):
        return Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * s

    def card(base, axis, size, centre):
        axis = axis.normalized()
        rel = base - C
        out_c = Vector((rel.x / crown_axes.x ** 2, rel.y / crown_axes.y ** 2, rel.z / crown_axes.z ** 2)).normalized()
        pref = (out_c * 0.75 + up * 0.25 + rvec(0.55)).normalized()
        right = axis.cross(pref)
        if right.length < 0.2:
            right = axis.cross(rvec())
        right.normalize()
        normal = right.cross(axis)
        if normal.dot(pref) < 0:
            right, normal = -right, -normal
        cell = UNDERSIDE_CELL if normal.z < -0.3 else rng.randrange(3)
        u0, v0 = CELLS[cell]
        flip = rng.random() < 0.5
        hw = right * size * 0.5
        fold = normal * size * rng.uniform(0.10, 0.18)
        b0 = base - axis * size * 0.03
        t0 = b0 + axis * size
        vs = [cards.verts.new(q) for q in (b0 - hw + fold, b0, b0 + hw + fold, t0 - hw + fold, t0, t0 + hw + fold)]
        us = (u0 + 0.5, u0 + 0.25, u0) if flip else (u0, u0 + 0.25, u0 + 0.5)
        uvs = [(us[0], v0), (us[1], v0), (us[2], v0), (us[0], v0 + 0.5), (us[1], v0 + 0.5), (us[2], v0 + 0.5)]
        for quad in ((0, 1, 4, 3), (1, 2, 5, 4)):
            f = cards.faces.new([vs[i] for i in quad])
            for loop, i in zip(f.loops, quad):
                loop[cuv].uv = uvs[i]
        for v in vs:
            oc = (v.co - centre)
            oc = oc.normalized() if oc.length > 1e-4 else out_c
            normals.append((normal * 0.35 + oc * 0.35 + out_c * 0.3 + up * 0.12).normalized())

    for c, cdir, tip in clumps:
        cdir = cdir.normalized()
        rel = c - C
        out_c = Vector((rel.x / crown_axes.x ** 2, rel.y / crown_axes.y ** 2, rel.z / crown_axes.z ** 2)).normalized()
        for _ in range(rng.randint(3, 4)):
            dj = (cdir * 0.8 + out_c * 0.7 + up * 0.25 + rvec(0.7)).normalized()
            L = rng.uniform(0.10, 0.22)
            e = tip + dj * L
            tube(limb_bm, luv, [tip, e], [0.0045, 0.0028], 3, tile=tile, uv_off=uvo())
            # terminal sprig continues the twig; the others leave it at a splay
            card(e - dj * 0.02, (dj + out_c * 0.3 + rvec(0.25)).normalized(), rng.uniform(smin, smax), c)
            for k in range(rng.randint(2, 3)):
                at = tip + (e - tip) * rng.uniform(0.2, 0.9)
                ax = (dj * 0.6 + out_c * 0.55 + rvec(0.75) - up * 0.1).normalized()
                card(at, ax, rng.uniform(smin, smax) * 0.92, c)
        # a couple of sprigs straight off the branch, just behind the clump
        for k in range(rng.randint(1, 2)):
            at = tip - cdir * rng.uniform(0.04, 0.14)
            ax = (out_c * 0.8 + cdir * 0.3 + rvec(0.6)).normalized()
            card(at, ax, rng.uniform(smin, smax) * 0.85, c)

    trunk = common.mesh_object(f"{n}_Trunk", trunk_bm, col, bark, root)
    limbs = common.mesh_object(f"{n}_LimbsNoCollide", limb_bm, col, bark, root)
    canopy = common.mesh_object(f"{n}_Canopy", cards, col, leaf, root)
    return trunk, limbs, canopy, normals


def fit_extent(p, objs):
    """Squeeze the crown (not the lower stems) into the corner's footprint and height."""
    meshes = [o.data for o in objs]
    for _ in range(5):
        lo = Vector((1e9, 1e9, 1e9))
        hi = Vector((-1e9, -1e9, -1e9))
        for me in meshes:
            for v in me.vertices:
                for a in range(3):
                    lo[a] = min(lo[a], v.co[a])
                    hi[a] = max(hi[a], v.co[a])
        sx = (min(1.0, p["extent_hi"][0] / hi.x), min(1.0, p["extent_lo"][0] / lo.x))
        sy = (min(1.0, p["extent_hi"][1] / hi.y), min(1.0, p["extent_lo"][1] / lo.y))
        top = p["height"] + 0.03
        szz = min(1.0, (top - 2.4) / max(hi.z - 2.4, 1e-3))
        if min(sx + sy) > 0.999 and szz > 0.999:
            break
        for me in meshes:
            for v in me.vertices:
                x, y, z = v.co
                w = smoothstep(p["split_z"] + 0.05, p["split_z"] + 0.7, z)
                fx = sx[0] if x > 0 else sx[1]
                fy = sy[0] if y > 0 else sy[1]
                v.co.x = x * (1 + w * (fx - 1))
                v.co.y = y * (1 + w * (fy - 1))
                if z > 2.4:
                    v.co.z = 2.4 + (z - 2.4) * szz
            me.update()


def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rng = random.Random(p["seed"] + 500)

    stone = entry_sculpture.limestone_material()
    # the powder room's dark marble, honed (satin) rather than polished: Mexican beach pebbles
    pebble = entry_vanity.dark_marble_material("M_EntryTree_Pebble", roughness=0.42)
    bark = bark_material()
    leaf = leaf_material()

    build_planter(p, col, root, stone, pebble)      # the soil between the pebbles: dark stone too
    build_pebbles(p, col, root, pebble, rng, avoid_r=0.13)
    trunk, limbs, canopy, normals = build_tree(p, col, root, bark, leaf)
    fit_extent(p, [limbs, canopy])
    try:
        canopy.data.normals_split_custom_set_from_vertices([tuple(v) for v in normals])
    except Exception as e:  # noqa: BLE001
        print("entry_tree: custom normals unavailable:", e)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
