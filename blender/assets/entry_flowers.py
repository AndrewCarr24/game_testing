"""Entry flower arrangement: flowering cherry branches in a tall hand-thrown stoneware vase,
on the entry's round centre table (the first prop the player sees).

Branches: real cut branches, each a tapered tube (parallel-transport frames, 6 sides) that
zig-zags at its nodes the way Prunus wood grows, forks into side shoots and carries short
spurs. Every spur ends in a cup of brown bud scales and an umbel of 2-4 flowers on thin,
drooping pedicels (cherry flowers hang on long stalks), some young bronze leaves and buds.
Flowers: a red-brown hypanthium cup, five reflexed sepals, five cupped, notched petals (each
a 14-triangle curved sheet, two-sided material) whose UVs pick one of six pale-to-pink tiles
of a generated atlas, and a ring of stamens with yellow anthers. Stages: open, half open,
balloon and closed bud. The vase: lathed with real wall thickness (a rolled lip, the inner
wall going down to the water, an opaque water surface the stems pass through), a turned foot
ring, slight hand-thrown asymmetry, and a generated glaze texture (dark iron glaze breaking
rust at the lip, a pale ash glaze poured over the shoulder running down in beads, unglazed
foot) with throwing rings in its normal map. A few petals have fallen on the table.
Flower clusters are spread evenly along the branches until the triangle budget `tris` is
spent, and the spray is fitted to `fit` (overall size) after it has grown.

Textures (generated with numpy once, saved in assets/textures): T_EntryFlowers_Blossom_BaseColor
(atlas: bark strip, petals, bud, leaf, stamen, calyx, scales) and T_EntryFlowers_Vase_BaseColor
+ _Normal. Materials: M_EntryFlowers_Blossom (branches and flowers, one draw call),
M_EntryFlowers_Vase, M_EntryFlowers_Water.
Origin: centre of the underside of the vase. Units are metres.
"""
import importlib
import math
import os
import random
import sys

import bmesh
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, textures  # noqa: E402

importlib.reload(common)
importlib.reload(textures)

NAME = "EntryFlowers"

P = dict(
    name=NAME,
    branches=7,              # main stems (each forks into side shoots)
    seed=11,
    vase_h=0.36,
    # outer profile (r, z) of the vase, bottom to lip
    vase_profile=[(0.066, 0.0), (0.074, 0.014), (0.092, 0.055), (0.106, 0.130), (0.103, 0.190),
                  (0.087, 0.250), (0.063, 0.298), (0.048, 0.328), (0.046, 0.347), (0.054, 0.360)],
    spray=(0.50, 0.80),      # main stem length above the lip
    vase_segs=32,
    wall=0.0075,             # vase wall thickness at the neck
    fit=(0.80, 0.76, 1.07),  # overall size (x, y, z) the spray is fitted to
    forks=(1, 2),            # side shoots per main stem
    node=(0.040, 0.060),     # node spacing along the branches
    spacing=0.035,           # mean distance between candidate cluster sites along a branch
    tris=17800,              # triangle budget (the clusters stop there)
    umbel=(2, 5),            # flowers per spur
    petal=(0.0170, 0.0210),  # petal length
    stages=(0.68, 0.08, 0.12, 0.12),   # open, half open, balloon, bud
    tiles=(1, 2, 3, 0, 5),   # petal tiles used (atlas), per main stem in turn
    leaves=0.32,             # chance of young leaves at a spur
    fallen=4,                # petals fallen on the table round the vase
    lean=(12, 44),           # main stem lean from vertical (degrees)
    retexture=False,         # regenerate the textures even if they exist
)

S_MAX = 1.15                 # branch arc length mapped over the bark strip (cut end -> tip)
UP = Vector((0, 0, 1))
MIN_ELEV = math.radians(14)  # branches rise at least this much above horizontal

# atlas regions (u0, v0, u1, v1) of T_EntryFlowers_Blossom_BaseColor (v up)
_G = 0.006
BARK = (0.0 + _G, 0.785 + _G, 1.0 - _G, 1.0 - _G)
PETAL = [(i / 8 + _G, 0.385 + _G, (i + 1) / 8 - _G, 0.765 - _G) for i in range(6)]
BUD = (6 / 8 + _G, 0.385 + _G, 7 / 8 - _G, 0.765 - _G)
LEAF = (7 / 8 + _G, 0.385 + _G, 1.0 - _G, 0.765 - _G)
STAMEN = (0 / 8 + _G, 0.0 + _G, 1 / 8 - _G, 0.365 - _G)
CALYX = (1 / 8 + _G, 0.0 + _G, 2 / 8 - _G, 0.365 - _G)
SCALES = (2 / 8 + _G, 0.0 + _G, 3 / 8 - _G, 0.365 - _G)
PEDICEL = (3 / 8 + _G, 0.0 + _G, 4 / 8 - _G, 0.365 - _G)


def R(reg, lu, lv):
    u0, v0, u1, v1 = reg
    return (u0 + (u1 - u0) * min(max(lu, 0.0), 1.0), v0 + (v1 - v0) * min(max(lv, 0.0), 1.0))


# =========================================================================== textures
def _smooth(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def _mix(a, b, t):
    t = np.asarray(t)[..., None]
    return np.asarray(a) * (1 - t) + np.asarray(b) * t


def _nz(n, su, sv, beta, rng):
    return textures._noise(n, su, sv, beta, rng)


def _region_px(reg, W, H, bleed=4):
    u0, v0, u1, v1 = reg
    x0, x1 = max(0, int(u0 * W) - bleed), min(W, int(math.ceil(u1 * W)) + bleed)
    y0, y1 = max(0, int(v0 * H) - bleed), min(H, int(math.ceil(v1 * H)) + bleed)
    xs = (np.arange(x0, x1) + 0.5) / W
    ys = (np.arange(y0, y1) + 0.5) / H
    lu = np.clip((xs - u0) / (u1 - u0), 0, 1)
    lv = np.clip((ys - v0) / (v1 - v0), 0, 1)
    LU, LV = np.meshgrid(lu, lv)
    return (slice(y0, y1), slice(x0, x1)), LU, LV


def _sample(field, LU, LV):
    """Bilinear-free nearest lookup of a periodic noise field at local coords."""
    h, w = field.shape
    return field[(np.clip(LV, 0, 0.9999) * h).astype(int), (np.clip(LU, 0, 0.9999) * w).astype(int)]


def blossom_atlas(path, rng):
    """Base colour atlas for branches, flowers and leaves (linear values, saved as sRGB)."""
    W = H = 1024
    img = np.zeros((H, W, 3))
    img[:] = (0.42, 0.25, 0.24)                  # neutral fill (mip levels bleed into it)
    n1 = _nz(256, 1, 1, 1.6, rng)
    n2 = _nz(256, 1, 1, 1.0, rng)

    # ---- bark strip: u along the branch (cut end -> tip), v around (periodic) ----------
    sl, LU, LV = _region_px(BARK, W, H)
    long_n = _sample(_nz(512, 0.08, 1.0, 1.2, rng), LU, LV)         # streaks along the branch
    blot = _sample(_nz(256, 1.0, 1.0, 1.8, rng), LU, LV)
    old = (0.056, 0.040, 0.034)
    grey = (0.110, 0.102, 0.094)
    young = (0.085, 0.032, 0.022)
    age = _smooth((LU - 0.22) / 0.45)
    col = _mix(old, young, age)
    col = _mix(col, grey, np.clip(blot * 1.4 - 0.25, 0, 1) * (1 - age) * 0.4)
    col = col * (1 + 0.16 * long_n[..., None])
    # lenticels: short horizontal (around the stem) pale dashes
    hgt, wid = LU.shape
    lent = np.zeros_like(LU)
    for _ in range(420):
        cu = rng.uniform(0, 1)
        cv = rng.uniform(0, 1)
        ln = rng.uniform(0.05, 0.16) * (1.3 - 0.6 * cu)
        th = rng.uniform(0.9, 1.8) / wid
        du = (LU - cu) / th
        dv = (LV - cv + 0.5) % 1.0 - 0.5
        lent = np.maximum(lent, np.exp(-du * du) * _smooth(1 - np.abs(dv) / (ln / 2)))
    col = _mix(col, (0.19, 0.15, 0.115), np.clip(lent, 0, 1) * (0.8 - 0.35 * age))
    img[sl] = col

    # ---- petals: six tiles, pale tip -> pink base, fine radiating veins -------------------
    tiles = [  # (base, mid, tip) linear
        ((0.70, 0.36, 0.42), (0.86, 0.72, 0.74), (0.88, 0.85, 0.83)),   # 0 Tai Haku white
        ((0.72, 0.32, 0.42), (0.86, 0.62, 0.68), (0.89, 0.80, 0.81)),   # 1 Yoshino blush
        ((0.70, 0.26, 0.38), (0.84, 0.52, 0.60), (0.88, 0.72, 0.75)),   # 2 soft pink
        ((0.66, 0.20, 0.33), (0.80, 0.42, 0.52), (0.86, 0.62, 0.67)),   # 3 pink
        ((0.55, 0.12, 0.24), (0.72, 0.28, 0.40), (0.80, 0.46, 0.55)),   # 4 deep (balloons)
        ((0.80, 0.52, 0.54), (0.88, 0.80, 0.79), (0.90, 0.88, 0.86)),   # 5 aged, nearly white
    ]
    for (base, mid, tip), reg in zip(tiles, PETAL):
        sl, LU, LV = _region_px(reg, W, H)
        y = (LU - 0.5) * 2                       # across, -1..1
        x = LV                                   # base -> tip
        col = _mix(base, mid, _smooth(x / 0.55))
        col = _mix(col, tip, _smooth((x - 0.45) / 0.5))
        col = _mix(col, tip, 0.35 * np.clip(np.abs(y), 0, 1) ** 3)       # paler, thinner margins
        claw = _smooth(1 - x / 0.12)
        col = _mix(col, (0.60, 0.48, 0.22), 0.55 * claw)                  # yellow-green claw
        ang = np.arctan2(y * 0.5, x + 0.12)
        veins = (0.5 + 0.5 * np.cos(ang * 46 + 0.6 * _sample(n1, LU, LV))) ** 6
        col = col * (1 - (0.10 * veins * (1 - 0.6 * x))[..., None])
        col = col * (1 + 0.035 * _sample(n2, LU, LV)[..., None])
        img[sl] = col

    # ---- bud: five overlapping petals wrapped in a spiral (u around, v base -> tip) -------
    sl, LU, LV = _region_px(BUD, W, H)
    ph = (LU * 5 + LV * 0.8) % 1.0
    edge = _smooth(1 - np.abs(ph - 0.5) / 0.5) ** 0.6
    col = _mix((0.62, 0.18, 0.30), (0.80, 0.50, 0.58), edge * _smooth(LV / 0.6))
    col = _mix(col, (0.50, 0.10, 0.22), _smooth((LV - 0.7) / 0.3) * 0.6)             # darker tip
    col = _mix(col, (0.30, 0.20, 0.08), _smooth(1 - LV / 0.16))                       # base
    img[sl] = col

    # ---- leaf: young bronze-green, paler midrib and veins, reddish margins --------------
    sl, LU, LV = _region_px(LEAF, W, H)
    y = (LU - 0.5) * 2
    col = _mix((0.075, 0.105, 0.030), (0.14, 0.085, 0.035), np.clip(np.abs(y), 0, 1) ** 2 * 0.8 + LV * 0.25)
    mid = np.exp(-(y / 0.05) ** 2)
    lat = (0.5 + 0.5 * np.cos((LV * 9 - np.abs(y) * 2.2) * 2 * math.pi)) ** 10 * (np.abs(y) < 0.85)
    col = _mix(col, (0.20, 0.20, 0.08), 0.6 * mid + 0.25 * lat)
    col = col * (1 + 0.08 * _sample(n2, LU, LV)[..., None])
    img[sl] = col

    # ---- stamen: pale filament, yellow anther at the tip ---------------------------------
    sl, LU, LV = _region_px(STAMEN, W, H)
    col = _mix((0.78, 0.62, 0.58), (0.70, 0.36, 0.40), _smooth(LV / 0.7) * 0.4)
    col = _mix(col, (0.78, 0.52, 0.10), _smooth((LV - 0.66) / 0.1))
    col = _mix(col, (0.45, 0.28, 0.06), _smooth((LV - 0.9) / 0.1) * 0.5)
    img[sl] = col

    # ---- calyx: green base -> red-brown sepals; top quarter: yellow-green nectary disc ----
    sl, LU, LV = _region_px(CALYX, W, H)
    col = _mix((0.12, 0.13, 0.04), (0.30, 0.07, 0.06), _smooth(LV / 0.55))
    col = _mix(col, (0.50, 0.42, 0.12), _smooth((LV - 0.72) / 0.06))
    img[sl] = col

    # ---- bud scales: glossy brown with paler margins --------------------------------------
    sl, LU, LV = _region_px(SCALES, W, H)
    col = _mix((0.10, 0.050, 0.030), (0.30, 0.18, 0.10), _smooth((LV - 0.55) / 0.45))
    col = col * (1 + 0.15 * _sample(n1, LU, LV)[..., None])
    img[sl] = col

    # ---- pedicel: green flushed red ------------------------------------------------------
    sl, LU, LV = _region_px(PEDICEL, W, H)
    col = _mix((0.10, 0.14, 0.035), (0.26, 0.08, 0.05), _smooth(LV))
    img[sl] = col

    textures._save(os.path.splitext(os.path.basename(path))[0], textures._to_srgb(img[::-1]))


def vase_textures(base_path, nor_path, rng):
    """Ash-glazed stoneware, u around the vase (periodic), v: 0-0.04 underside, 0.04-0.90 the
    outer wall by height, 0.90-1 lip and inside. Dark iron glaze breaking rust on the throwing
    ridges and the lip, pale ash runs from the shoulder ending in drops, unglazed foot."""
    N = 1024
    U, V = np.meshgrid((np.arange(N) + 0.5) / N, (np.arange(N) + 0.5) / N)
    zf = np.clip((V - 0.04) / 0.86, 0, 1)                    # height fraction on the outer wall
    n_lo = _nz(N, 1, 1, 2.0, rng)
    n_mid = _nz(N, 1, 1, 1.4, rng)
    n_str = _nz(N, 0.03, 1.0, 0.9, rng)                       # vertical streaks (along v)
    n_u = _nz(N, 1, 40, 2.0, rng)[0]                          # 1-D wobble around (periodic)

    # throwing rings: a shallow spiral (periodic in u)
    ring_ph = 2 * math.pi * (zf * 27 + U) + 1.6 * n_lo
    amp = np.clip(0.55 + 0.6 * n_mid, 0.1, 1.0) * (0.35 + 0.65 * _smooth((zf - 0.1) / 0.3))
    rings = (0.75 * np.sin(ring_ph) + 0.25 * np.sin(2.3 * ring_ph + 2 * n_mid)) * amp
    ridge = np.clip(rings, 0, 1) ** 2

    # glaze line near the foot (wavy, with a few runs further down)
    gl = 0.075 + 0.012 * n_u[None, :]
    for _ in range(6):
        c = rng.uniform(0, 1)
        w = rng.uniform(0.006, 0.016)
        d = (U - c + 0.5) % 1.0 - 0.5
        gl = gl - rng.uniform(0.01, 0.03) * np.exp(-(d / w) ** 2)
    glazed = _smooth((zf - gl) / 0.006)

    # dark iron glaze with rust "hare's fur" where it thins
    dark = np.array((0.020, 0.017, 0.015))
    rust = np.array((0.13, 0.055, 0.022))
    thin = np.clip(0.10 * ridge + 0.55 * _smooth((zf - 0.86) / 0.12) + 0.10 * (n_str * 0.5 + 0.5) ** 3
                   + 0.12 * _smooth((zf - 0.62) / 0.2) * _smooth((n_str - 0.3) / 0.3), 0, 1)
    col = _mix(dark, rust, thin * 0.85)
    col = col * (1 + 0.25 * n_mid[..., None])

    # pale ash glaze poured over the shoulder: a mottled pooled band with an irregular lower
    # edge, from which thin translucent runs descend (straight, gravity) ending in beads
    low = 0.73 + 0.035 * n_u[None, :] + 0.02 * _nz(N, 1, 12, 1.5, rng)[0][None, :]
    band = _smooth((zf - low) / 0.025) * _smooth((0.965 - zf) / 0.03)
    ash = band * np.clip(0.45 + 0.9 * n_mid + 0.4 * n_lo, 0.15, 1)
    for _ in range(30):
        c = rng.uniform(0, 1)
        w = rng.uniform(0.0025, 0.0075) * (2.2 if rng.uniform() < 0.2 else 1.0)
        top = 0.74 + 0.05 * float(np.interp(c, np.linspace(0, 1, N), n_u))
        end = rng.uniform(0.30, 0.70) if rng.uniform() < 0.6 else rng.uniform(0.62, 0.74)
        op = rng.uniform(0.25, 0.65)
        d = (U - c + 0.5) % 1.0 - 0.5
        wob = d + 0.0015 * np.sin(zf * 23 + c * 30)
        taper = 0.55 + 0.45 * _smooth((zf - end) / max(top - end, 0.02))
        body = np.exp(-(wob / (w * taper)) ** 2) * _smooth((zf - end) / 0.008) * _smooth((top + 0.03 - zf) / 0.03)
        wd = w * 1.3                                    # bead: round (u spans 2.1x more metres than zf)
        drop = np.exp(-((wob / wd) ** 2 + ((zf - end - wd * 1.2) / (wd * 2.6)) ** 2))
        ash = np.maximum(ash, op * np.maximum(body, drop))
    ash = np.clip(ash, 0, 1)
    ash_col = _mix((0.10, 0.12, 0.115), (0.22, 0.24, 0.215), np.clip(0.45 + 0.6 * n_mid, 0, 1))
    col = _mix(col, ash_col, ash ** 0.8 * 0.9)
    # unglazed foot: warm buff-grey clay with iron speckles
    clay = _mix((0.20, 0.155, 0.115), (0.26, 0.21, 0.16), np.clip(0.5 + 0.5 * n_mid, 0, 1))
    speck = (rng.uniform(0, 1, U.shape) > 0.99).astype(float)
    clay = _mix(clay, (0.05, 0.035, 0.03), speck * 0.8)
    col = _mix(clay, col, glazed)
    # underside (v < 0.04): clay; lip and inside (v > 0.90): glaze, rust on the rolled lip edge
    under = V < 0.04
    col[under] = clay[under]
    inner = V > 0.90
    lipt = _smooth(1 - np.abs(V - 0.915) / 0.02)
    inside = _mix(dark * (1 + 0.25 * n_mid[..., None]), rust, lipt * 0.8)
    col[inner] = inside[inner]

    # height -> normal: rings, ash runs stand slightly proud, pinholes
    h = 0.22 * rings * glazed + 0.15 * ash + 0.2 * n_mid
    pin = (rng.uniform(0, 1, U.shape) > 0.9985).astype(float)
    h = h - 0.8 * pin * glazed
    h[under] = 0.2 * n_mid[under]
    dhu = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5
    dhv = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5
    k = 2.2
    nx, ny, nz = -dhu * k, -dhv * k, np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nor = np.stack([nx / ln, ny / ln, nz / ln], axis=-1) * 0.5 + 0.5

    textures._save(os.path.splitext(os.path.basename(base_path))[0], textures._to_srgb(col[::-1]))
    textures._save(os.path.splitext(os.path.basename(nor_path))[0], nor[::-1])


def _materials(p):
    tdir = textures.TEX_DIR
    atlas = os.path.join(tdir, "T_EntryFlowers_Blossom_BaseColor.png")
    vbase = os.path.join(tdir, "T_EntryFlowers_Vase_BaseColor.png")
    vnor = os.path.join(tdir, "T_EntryFlowers_Vase_Normal.png")
    if p["retexture"] or not os.path.exists(atlas):
        blossom_atlas(atlas, np.random.default_rng(11))
    if p["retexture"] or not (os.path.exists(vbase) and os.path.exists(vnor)):
        vase_textures(vbase, vnor, np.random.default_rng(23))
    bl = common.pbr_material("M_EntryFlowers_Blossom", (1, 1, 1), roughness=0.55)
    if not any(nd.type == "TEX_IMAGE" for nd in bl.node_tree.nodes):
        common.set_base_color_map(bl, textures.load(atlas))
    vs = common.pbr_material("M_EntryFlowers_Vase", (1, 1, 1), roughness=0.5)
    if not any(nd.type == "TEX_IMAGE" for nd in vs.node_tree.nodes):
        common.set_base_color_map(vs, textures.load(vbase))
        common.set_normal_map(vs, textures.load(vnor, non_color=True), 1.0)
    wt = common.pbr_material("M_EntryFlowers_Water", (0.012, 0.016, 0.016), roughness=0.03)
    return bl, vs, wt


# =========================================================================== mesh helpers
class Mesh:
    def __init__(self):
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.tris = 0

    def v(self, co):
        return self.bm.verts.new(co)

    def f(self, verts, uvs):
        try:
            face = self.bm.faces.new(verts)
        except ValueError:
            return None
        for lp, uv in zip(face.loops, uvs):
            lp[self.uv].uv = uv
        self.tris += len(verts) - 2
        return face


def frame(n):
    n = Vector(n).normalized()
    t = n.orthogonal().normalized()
    return n, t, n.cross(t)


def rot(vec, axis, ang):
    return Matrix.Rotation(ang, 3, Vector(axis).normalized()) @ Vector(vec)


def tube(m, pts, radii, ss, sides, reg=BARK, tip=False, start_frame=None):
    """Tapered tube along `pts` with parallel-transported rings; UVs: u = arc length on the
    bark strip, v around. `ss`: arc length (m) at each point. Open at the start; tip=True
    closes the end with a point."""
    pts = [Vector(q) for q in pts]
    n = len(pts)
    tans = []
    for k in range(n):
        d = pts[min(k + 1, n - 1)] - pts[max(k - 1, 0)]
        tans.append(d.normalized() if d.length > 1e-9 else UP.copy())
    u = start_frame if start_frame is not None else tans[0].orthogonal().normalized()
    u = (u - tans[0] * u.dot(tans[0])).normalized()
    rings, prev = [], tans[0]
    for k in range(n):
        d = tans[k]
        q = prev.rotation_difference(d)
        u = (q @ u)
        u = (u - d * u.dot(d)).normalized()
        w = d.cross(u)
        prev = d
        rings.append([m.v(pts[k] + (u * math.cos(2 * math.pi * s / sides) + w * math.sin(2 * math.pi * s / sides)) * radii[k])
                      for s in range(sides)])
    U = [min(s / S_MAX, 1.0) for s in ss]
    for k in range(n - 1):
        A, B = rings[k], rings[k + 1]
        for s in range(sides):
            s1 = (s + 1) % sides
            m.f((A[s], A[s1], B[s1], B[s]),
                (R(reg, U[k], s / sides), R(reg, U[k], (s + 1) / sides),
                 R(reg, U[k + 1], (s + 1) / sides), R(reg, U[k + 1], s / sides)))
    if tip:
        d = tans[-1]
        tp = m.v(pts[-1] + d * radii[-1] * 2.5)
        ut = min((ss[-1] + radii[-1] * 2.5) / S_MAX, 1.0)
        B = rings[-1]
        for s in range(sides):
            s1 = (s + 1) % sides
            m.f((B[s], B[s1], tp), (R(reg, U[-1], s / sides), R(reg, U[-1], (s + 1) / sides),
                                    R(reg, ut, (s + 0.5) / sides)))
    return rings


def cone(m, a, b, ra, rb, sides, reg, va=0.0, vb=1.0, spin=0.0, cap=None):
    """Open frustum from a (radius ra) to b (rb); UVs u around, v along within `reg`.
    cap=(reg, lv): close the b end with a fan."""
    a, b = Vector(a), Vector(b)
    n, t, bb = frame(b - a)
    ring = lambda c, r: [m.v(c + (t * math.cos(spin + 2 * math.pi * s / sides) + bb * math.sin(spin + 2 * math.pi * s / sides)) * r)
                         for s in range(sides)]
    A, B = ring(a, ra), ring(b, rb)
    for s in range(sides):
        s1 = (s + 1) % sides
        m.f((A[s], A[s1], B[s1], B[s]), (R(reg, s / sides, va), R(reg, (s + 1) / sides, va),
                                         R(reg, (s + 1) / sides, vb), R(reg, s / sides, vb)))
    if cap:
        creg, lv = cap
        c = m.v(b + n * rb * 0.25)
        for s in range(sides):
            s1 = (s + 1) % sides
            m.f((B[s], B[s1], c), (R(creg, 0.2, lv), R(creg, 0.8, lv), R(creg, 0.5, lv + 0.05)))


# =========================================================================== flower parts
def _centreline(c, r, n, L, th0, th1, base_r, base_h, steps=10):
    """Points and surface normals along a petal's midline: it leaves the receptacle at angle
    th0 above the flower's plane and ends at th1 (both radians, measured towards n)."""
    pts, nrm = [], []
    p = c + r * base_r + n * base_h
    dx = L / steps
    for k in range(steps + 1):
        th = th0 + (th1 - th0) * k / steps
        pts.append(p.copy())
        nrm.append(-r * math.sin(th) + n * math.cos(th))
        p = p + (r * math.cos(th) + n * math.sin(th)) * dx
    return pts, nrm


def petal(m, c, n, phi, L, W, th0, th1, cup, notch, reg, base_r=0.0016, base_h=0.0, twist=0.0):
    n, t, b = frame(n)
    r = t * math.cos(phi) + b * math.sin(phi)
    s = n.cross(r)
    if twist:
        s = rot(s, r, twist)
    pts, nrm = _centreline(c, r, n, L, th0, th1, base_r, base_h)
    steps = len(pts) - 1

    def at(x, y):
        f = min(max(x, 0.0), 1.0) * steps
        i = min(int(f), steps - 1)
        a = f - i
        C = pts[i].lerp(pts[i + 1], a)
        N = nrm[i].lerp(nrm[i + 1], a)
        yy = y * W
        return m.v(C + s * yy + N * (cup * W * y * y * (0.35 + 0.65 * x)))

    def uv(x, y):
        return R(reg, 0.5 + 0.5 * y, x)

    rows = [(0.0, 0.18), (0.62, 1.0)]
    grid = [[(x, -hw), (x, 0.0), (x, hw)] for x, hw in rows]
    tipxy = [(0.88, -0.84), (0.995, -0.44), (1.0 - notch, 0.0), (0.995, 0.44), (0.88, 0.84)]
    G = [[at(x, y) for x, y in row] for row in grid]
    T = [at(x, y) for x, y in tipxy]
    for k in range(len(rows) - 1):
        for j in range(2):
            q = (grid[k][j], grid[k][j + 1], grid[k + 1][j + 1], grid[k + 1][j])
            m.f((G[k][j], G[k][j + 1], G[k + 1][j + 1], G[k + 1][j]), [uv(*e) for e in q])
    A, M, B = G[-1]
    a, bq, cq, d, e = T
    gA, gM, gB = grid[-1]
    ta, tb, tc, td, te = tipxy
    m.f((A, M, cq, bq), [uv(*gA), uv(*gM), uv(*tc), uv(*tb)])
    m.f((A, bq, a), [uv(*gA), uv(*tb), uv(*ta)])
    m.f((M, B, d, cq), [uv(*gM), uv(*gB), uv(*td), uv(*tc)])
    m.f((B, e, d), [uv(*gB), uv(*te), uv(*td)])


def flower(m, c, n, L, stage, tile, rnd):
    """One cherry flower whose receptacle sits at c, facing n. stage: open / half / balloon."""
    n, t, b = frame(n)
    spin = rnd.uniform(0, 2 * math.pi)
    W = L * rnd.uniform(0.44, 0.50)
    if stage == "open":
        th0, th1, cup = math.radians(rnd.uniform(28, 42)), math.radians(rnd.uniform(-8, 10)), 0.38
    elif stage == "half":
        th0, th1, cup = math.radians(rnd.uniform(52, 62)), math.radians(rnd.uniform(34, 46)), 0.38
    else:                            # balloon: petals still wrapped round each other
        th0, th1, cup = math.radians(rnd.uniform(70, 76)), math.radians(rnd.uniform(100, 112)), 0.55
        L *= 0.58
        W = L * 0.66
    for k in range(5):
        phi = spin + 2 * math.pi * k / 5 + rnd.uniform(-0.08, 0.08)
        lift = 0.0004 * (k % 2) + 0.0002 * (k == 4)          # quincuncial overlap, no z-fight
        petal(m, c, n, phi, L * rnd.uniform(0.92, 1.06), W * rnd.uniform(0.92, 1.06),
              th0 + rnd.uniform(-0.05, 0.05) + 0.03 * (k % 2), th1 + rnd.uniform(-0.08, 0.08),
              cup * rnd.uniform(0.8, 1.2), rnd.uniform(0.06, 0.13), PETAL[tile],
              base_h=lift, twist=rnd.uniform(-0.15, 0.15))
    # hypanthium cup + nectary disc, sepals reflexed between the petals
    cone(m, c - n * 0.0040, c + n * 0.0002, 0.0008, 0.0019, 5, CALYX, 0.0, 0.95, spin)
    for k in range(5):
        az = spin + 2 * math.pi * (k + 0.5) / 5
        rd = t * math.cos(az) + b * math.sin(az)
        sd = n.cross(rd)
        base = c - n * 0.0006 + rd * 0.0017
        back = 0.55 if stage == "open" else (0.1 if stage == "half" else -0.35)
        tipp = base + (rd * 0.8 - n * back).normalized() * 0.0045
        m.f((m.v(base - sd * 0.0013), m.v(base + sd * 0.0013), m.v(tipp)),
            (R(CALYX, 0.2, 0.05), R(CALYX, 0.8, 0.05), R(CALYX, 0.5, 0.55)))
    if stage == "balloon":
        return
    # stamens: thin wedges widening to the anther, and the pistil
    ns = 6 if stage == "open" else 4
    ls = L * (0.50 if stage == "open" else 0.38)
    for k in range(ns):
        az = spin + 2 * math.pi * (k + rnd.uniform(-0.2, 0.2)) / ns
        rd = t * math.cos(az) + b * math.sin(az)
        sd = n.cross(rd)
        be = math.radians(rnd.uniform(18, 38) if stage == "open" else rnd.uniform(8, 18))
        base = c + n * 0.0004 + rd * 0.0011
        tip = base + (n * math.cos(be) + rd * math.sin(be)) * ls * rnd.uniform(0.8, 1.1)
        w0, w1 = 0.00018, 0.00062
        m.f((m.v(base - sd * w0), m.v(base + sd * w0), m.v(tip + sd * w1), m.v(tip - sd * w1)),
            (R(STAMEN, 0.0, 0.0), R(STAMEN, 1.0, 0.0), R(STAMEN, 1.0, 1.0), R(STAMEN, 0.0, 1.0)))
    sd = t
    tip = c + n * ls * 0.9
    m.f((m.v(c - sd * 0.0002), m.v(c + sd * 0.0002), m.v(tip + sd * 0.0003), m.v(tip - sd * 0.0003)),
        (R(PEDICEL, 0.2, 0.1), R(PEDICEL, 0.8, 0.1), R(PEDICEL, 0.8, 0.3), R(PEDICEL, 0.2, 0.3)))


def bud(m, c, n, Rr, rnd, reg=BUD, lobes=False, shape=((0.18, 0.62), (0.52, 1.0), (0.84, 0.62)), elong=(2.0, 2.5),
        sides=5, sepals=True):
    """Closed bud: a twisted, lobed ovoid (rings at `shape` = (fraction along, radius)), with
    a cup of sepals. lobes=True maps each face column across a whole petal tile (a
    balloon-stage flower: five petals still wrapped)."""
    n, t, b = frame(n)
    spin = rnd.uniform(0, 2 * math.pi)
    Lb = Rr * rnd.uniform(*elong)
    rings = []
    for k, (f, rr) in enumerate(shape):
        rings.append([m.v(c + n * (Lb * f) + (t * math.cos(a) + b * math.sin(a)) * Rr * rr * rnd.uniform(0.94, 1.06))
                      for a in (spin + 0.22 * k + 2 * math.pi * s / sides for s in range(sides))])
    base, tip = m.v(c), m.v(c + n * Lb)
    vs = tuple(f for f, _ in shape)
    nr = len(rings)
    for s in range(sides):
        s1 = (s + 1) % sides
        ua, ub = ((0.06, 0.94) if lobes else (s / sides, (s + 1) / sides))
        um = (ua + ub) / 2
        m.f((base, rings[0][s1], rings[0][s]), (R(reg, um, 0.0), R(reg, ub, vs[0]), R(reg, ua, vs[0])))
        for k in range(nr - 1):
            A, B = rings[k], rings[k + 1]
            m.f((A[s], A[s1], B[s1], B[s]), (R(reg, ua, vs[k]), R(reg, ub, vs[k]),
                                             R(reg, ub, vs[k + 1]), R(reg, ua, vs[k + 1])))
        m.f((rings[-1][s], rings[-1][s1], tip), (R(reg, ua, vs[-1]), R(reg, ub, vs[-1]), R(reg, um, 1.0)))
    if not sepals:
        return
    for k in range(5):
        az = spin + 2 * math.pi * (k + 0.5) / 5
        rd = t * math.cos(az) + b * math.sin(az)
        sd = n.cross(rd)
        bs = c + n * 0.0005 + rd * Rr * 0.4
        tp = bs + (rd * 0.55 + n * 0.8).normalized() * Lb * 0.36
        m.f((m.v(bs - sd * Rr * 0.32), m.v(bs + sd * Rr * 0.32), m.v(tp)),
            (R(CALYX, 0.2, 0.05), R(CALYX, 0.8, 0.05), R(CALYX, 0.5, 0.55)))


def leaf(m, base, d, up, L, W, fold, droop):
    """Young leaf, folded along the midrib and arching (14 tris)."""
    d = Vector(d).normalized()
    side = d.cross(up)
    if side.length < 1e-6:
        side = d.orthogonal()
    side.normalize()
    nrm0 = side.cross(d).normalized()
    rows = [(0.0, 0.10), (0.25, 0.80), (0.55, 1.0), (0.82, 0.60)]

    def C(x):
        xl = x * L
        return base + d * xl + nrm0 * (-0.5 * droop * xl * xl / L), nrm0

    G = []
    for x, hw in rows:
        p, nn = C(x)
        G.append([m.v(p + side * (j * hw * W) + nn * (fold * hw * W * abs(j))) for j in (-1, 0, 1)])
    tp, _ = C(1.0)
    T = m.v(tp)
    uv = lambda x, j, hw: R(LEAF, 0.5 + 0.5 * j * hw, x)
    for k in range(3):
        for j in range(2):
            x0, h0 = rows[k]
            x1, h1 = rows[k + 1]
            jj = (-1, 0, 1)
            m.f((G[k][j], G[k][j + 1], G[k + 1][j + 1], G[k + 1][j]),
                (uv(x0, jj[j], h0), uv(x0, jj[j + 1], h0), uv(x1, jj[j + 1], h1), uv(x1, jj[j], h1)))
    x3, h3 = rows[3]
    m.f((G[3][0], G[3][1], T), (uv(x3, -1, h3), uv(x3, 0, h3), R(LEAF, 0.5, 1.0)))
    m.f((G[3][1], G[3][2], T), (uv(x3, 0, h3), uv(x3, 1, h3), R(LEAF, 0.5, 1.0)))


# =========================================================================== vase
def _catmull(pts, per=3):
    out = []
    P = [pts[0]] + list(pts) + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = (np.array(P[j], float) for j in (i - 1, i, i + 1, i + 2))
        for k in range(per):
            t = k / per
            out.append(tuple(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                                    + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)))
    out.append(tuple(pts[-1]))
    return out


def vase(m, p, rnd):
    """Lathed vase with UVs (see vase_textures for the v layout). Returns (water z, inner
    radius at the water, mouth inner radius)."""
    H = p["vase_h"]
    vp = p["vase_profile"]
    segs = p["vase_segs"]
    wall = p["wall"]
    r0 = vp[0][0]
    outer = _catmull(vp[1:], per=2)
    foot = [(r0 - 0.013, 0.0035), (r0 - 0.008, 0.0), (r0 - 0.003, 0.0), (r0, 0.0025)]
    outer = foot + outer
    rt, zt = vp[-1]
    lip = [(rt - 0.0015, zt + 0.0032), (rt - 0.0045, zt + 0.0046), (rt - wall + 0.0005, zt + 0.0030),
           (rt - wall - 0.0004, zt - 0.0005)]
    zw = H - 0.046

    def r_out(z):
        for (ra, za), (rb, zb) in zip(outer, outer[1:]):
            if za <= z <= zb and zb > za:
                return ra + (rb - ra) * (z - za) / (zb - za)
        return outer[-1][0]

    inner = []
    for z in np.linspace(zt - 0.010, zw - 0.012, 3):
        inner.append((r_out(z) - wall, float(z)))
    prof = [(0.0, 0.0035), (r0 - 0.030, 0.0035)] + outer + lip + inner
    # v coordinate per profile point
    vs = []
    lipstart = len([(0, 0), (0, 0)]) + len(outer)
    arc = [0.0]
    for (ra, za), (rb, zb) in zip(prof[lipstart - 1:], prof[lipstart:]):
        arc.append(arc[-1] + math.hypot(rb - ra, zb - za))
    for i, (r, z) in enumerate(prof):
        if i < 2:
            vs.append(0.04 * r / r0)
        elif i < lipstart:
            vs.append(0.04 + 0.86 * min(z / zt, 1.0))
        else:
            vs.append(0.90 + 0.10 * arc[i - lipstart + 1] / arc[-1])
    ph1, ph2, ph3 = (rnd.uniform(0, 2 * math.pi) for _ in range(3))

    def wob(th, z):
        f = z / H
        return 1.0 + 0.010 * math.sin(th + ph1) * f + 0.006 * math.sin(2 * th + ph2) * (1 - f) + 0.004 * math.sin(3 * th + ph3) * f

    rings = []
    for i, (r, z) in enumerate(prof):
        if r < 1e-6:
            rings.append(m.v((0, 0, z)))
            continue
        ring = []
        for s in range(segs):
            th = 2 * math.pi * s / segs
            rr = r * wob(th, z)
            zz = z + (0.0012 * math.sin(2 * th + ph3) if z > zt - 0.002 else 0.0)
            ring.append(m.v((rr * math.cos(th), rr * math.sin(th), zz)))
        rings.append(ring)
    for i in range(len(prof) - 1):
        A, B = rings[i], rings[i + 1]
        for s in range(segs):
            s1 = (s + 1) % segs
            u0, u1 = s / segs, (s + 1) / segs
            if not isinstance(A, list):
                m.f((A, B[s1], B[s]), ((u0 + 0.5 / segs, vs[i]), (u1, vs[i + 1]), (u0, vs[i + 1])))
            else:
                m.f((A[s], A[s1], B[s1], B[s]), ((u0, vs[i]), (u1, vs[i]), (u1, vs[i + 1]), (u0, vs[i + 1])))
    # bottom pole faces the floor: flip so the underside's normal points down
    return zw, r_out(zw) - wall, rt - wall - 0.0004


# =========================================================================== branches
def _grow(start, d0, length, seg, zig, lean_gain, upturn, rnd, plane=None):
    """Zig-zagging branch path from `start`: alternate kinks at each node in a slowly
    rotating plane, gradually leaning out, with the tip turning up."""
    pts = [Vector(start)]
    d = Vector(d0).normalized()
    nseg = max(2, int(round(length / seg)))
    side = plane or d.cross(UP)
    if side.length < 1e-6:
        side = d.orthogonal()
    side.normalize()
    for k in range(nseg):
        t = k / nseg
        side = rot(side, d, rnd.uniform(-0.5, 0.5))
        kink = zig * (1 if k % 2 else -1) * rnd.uniform(0.6, 1.3)
        d = rot(d, side, kink)
        out = Vector((d.x, d.y, 0))
        if out.length > 1e-6:
            axis = out.normalized().cross(UP)
            d = rot(d, axis, -lean_gain * rnd.uniform(0.5, 1.5))      # leans out a little more
            d = rot(d, axis, upturn * t * t)                           # tip turns up
            el = math.asin(max(-1.0, min(1.0, d.normalized().z)))
            if el < MIN_ELEV:                                          # never droops below
                d = rot(d, axis, MIN_ELEV - el)
        pts.append(pts[-1] + d.normalized() * seg * rnd.uniform(0.8, 1.2))
    return pts


class Branch:
    def __init__(self, pts, r0, r1, s0, level, first_node=0):
        self.pts = pts
        self.s = [s0]
        for a, b in zip(pts, pts[1:]):
            self.s.append(self.s[-1] + (b - a).length)
        self.r0, self.r1 = r0, r1
        self.level = level
        self.first_node = first_node

    def radius(self, k):
        f = (self.s[k] - self.s[0]) / max(self.s[-1] - self.s[0], 1e-6)
        return self.r0 + (self.r1 - self.r0) * f ** 0.8

    def at(self, sv):
        """(segment index, point, direction, radius) at arc length sv."""
        for k in range(len(self.pts) - 1):
            if self.s[k + 1] >= sv or k == len(self.pts) - 2:
                f = min(max((sv - self.s[k]) / max(self.s[k + 1] - self.s[k], 1e-9), 0.0), 1.0)
                q = self.pts[k].lerp(self.pts[k + 1], f)
                d = (self.pts[k + 1] - self.pts[k]).normalized()
                r = self.radius(k) * (1 - f) + self.radius(k + 1) * f
                return k, q, d, r
        return len(self.pts) - 1, self.pts[-1], self.dir(len(self.pts) - 1), self.r1

    def dir(self, k):
        n = len(self.pts)
        return (self.pts[min(k + 1, n - 1)] - self.pts[max(k - 1, 0)]).normalized()


def skeleton(p, rnd, mouth_r):
    H = p["vase_h"]
    nb = p["branches"]
    branches = []
    mouths = []
    az0 = rnd.uniform(0, 2 * math.pi)
    for i in range(nb):
        az = az0 + 2 * math.pi * (i + rnd.uniform(-0.25, 0.25)) / nb
        lo, hi = p["lean"]
        lean = math.radians(lo + (hi - lo) * ((i * 0.618) % 1.0) + rnd.uniform(-4, 4))
        L = rnd.uniform(*p["spray"]) * (1.0 - 0.25 * (lean - math.radians(lo)) / math.radians(hi - lo + 1e-6))
        r0 = rnd.uniform(0.0058, 0.0078)
        # position in the mouth: pushed towards its lean side, kept apart from the others
        for _try in range(40):
            rho = rnd.uniform(0.15, 0.85) * (mouth_r - r0 - 0.0015)
            a = az + rnd.uniform(-1.2, 1.2)
            M = Vector((rho * math.cos(a), rho * math.sin(a), H))
            if all((M - q).length > (r0 + rq) * 1.05 for q, rq in mouths):
                break
        mouths.append((M, r0))
        l_in = min(lean, math.radians(11))
        d_in = Vector((math.sin(l_in) * math.cos(az), math.sin(l_in) * math.sin(az), math.cos(l_in)))
        B = M - d_in * ((H - 0.07) / math.cos(l_in))
        d0 = Vector((math.sin(lean) * math.cos(az), math.sin(lean) * math.sin(az), math.cos(lean)))
        seg = rnd.uniform(*p["node"])
        out = _grow(M, d0, L, seg, math.radians(rnd.uniform(7, 13)), math.radians(1.5),
                    math.radians(rnd.uniform(10, 30)), rnd)
        pts = [B, B.lerp(M, 0.5)] + out
        main = Branch(pts, r0, 0.0011, 0.0, 0, first_node=2 + max(1, int(len(out) * 0.28)))
        branches.append(main)
        # side shoots from the middle of the stem, angled away from it
        nf = rnd.randint(*p["forks"])
        ks = sorted(rnd.sample(range(2 + int(len(out) * 0.25), 2 + int(len(out) * 0.75)), min(nf, max(1, int(len(out) * 0.5)))))
        for k in ks:
            d = main.dir(k)
            side = d.cross(UP)
            side = rot(side, d, rnd.uniform(-1.4, 1.4)) if side.length > 1e-6 else d.orthogonal()
            dd = rot(d, side, math.radians(rnd.uniform(26, 44)))
            rem = main.s[-1] - main.s[k]
            Ls = max(0.10, rem * rnd.uniform(0.38, 0.62))
            sp = _grow(main.pts[k], dd, Ls, rnd.uniform(*p["node"]) * 0.9, math.radians(rnd.uniform(8, 14)),
                       math.radians(2.0), math.radians(rnd.uniform(5, 25)), rnd)
            sb = Branch(sp, main.radius(k) * 0.62, 0.0009, main.s[k], 1, first_node=1)
            branches.append(sb)
            if rnd.random() < 0.55 and len(sp) > 3:            # a short twig off the side shoot
                k2 = rnd.randint(1, len(sp) - 2)
                d2 = sb.dir(k2)
                s2 = rot(d2.cross(UP) if d2.cross(UP).length > 1e-6 else d2.orthogonal(), d2, rnd.uniform(-1.5, 1.5))
                tw = _grow(sp[k2], rot(d2, s2, math.radians(rnd.uniform(30, 50))), rnd.uniform(0.06, 0.13),
                           0.035, math.radians(10), math.radians(2), math.radians(10), rnd)
                branches.append(Branch(tw, sb.radius(k2) * 0.6, 0.0008, sb.s[k2], 2, first_node=1))
    return branches


def fit(branches, p, margin):
    """Scale the spray (above the lip) so the arrangement's overall size is p["fit"]."""
    H = p["vase_h"]
    pts = [q for b in branches for q in b.pts if q.z > H]
    fx, fy, fz = p["fit"]
    sx = (fx - 2 * margin) / max(max(q.x for q in pts) - min(q.x for q in pts), 1e-3)
    sy = (fy - 2 * margin) / max(max(q.y for q in pts) - min(q.y for q in pts), 1e-3)
    sz = (fz - margin - H) / max(max(q.z for q in pts) - H, 1e-3)
    sx, sy, sz = (min(max(v, 0.6), 1.6) for v in (sx, sy, sz))
    for b in branches:
        for q in b.pts:
            if q.z > H:
                w = min(max((q.z - H) / 0.12, 0.0), 1.0)
                w = w * w * (3 - 2 * w)
                q.x *= 1 + (sx - 1) * w
                q.y *= 1 + (sy - 1) * w
                q.z = H + (q.z - H) * sz
        b.s = [b.s[0]]
        for a, c in zip(b.pts, b.pts[1:]):
            b.s.append(b.s[-1] + (c - a).length)
    return sx, sy, sz


def fit_mesh(bm, p):
    """Final, exact fit of the finished spray to p["fit"] (the coarse fit above works on the
    skeleton, before the flowers): the same blend, so the stems in the vase stay put."""
    H = p["vase_h"]
    vs = [v for v in bm.verts if v.co.z > H]
    fx, fy, fz = p["fit"]
    xs = [v.co.x for v in vs]
    ys = [v.co.y for v in vs]
    sx = fx / max(max(xs) - min(xs), 1e-3)
    sy = fy / max(max(ys) - min(ys), 1e-3)
    sz = (fz - H) / max(max(v.co.z for v in vs) - H, 1e-3)
    for v in vs:
        w = min(max((v.co.z - H) / 0.12, 0.0), 1.0)
        w = w * w * (3 - 2 * w)
        v.co.x *= 1 + (sx - 1) * w
        v.co.y *= 1 + (sy - 1) * w
        v.co.z = H + (v.co.z - H) * sz
    return sx, sy, sz


# =========================================================================== build
def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    rnd = random.Random(p["seed"])
    bl_mat, vase_mat, water_mat = _materials(p)

    # ---- vase + water -------------------------------------------------------------------
    vm = Mesh()
    zw, r_water, mouth_r = vase(vm, p, random.Random(p["seed"] + 7))
    vm_tris = vm.tris
    common.mesh_object(f"{n}_Vase", vm.bm, col, vase_mat, root)
    wm = Mesh()
    ring = [wm.v((r_water * 1.02 * math.cos(2 * math.pi * s / 24), r_water * 1.02 * math.sin(2 * math.pi * s / 24), zw))
            for s in range(24)]
    wm.f(ring, [(0.5 + 0.5 * math.cos(2 * math.pi * s / 24), 0.5 + 0.5 * math.sin(2 * math.pi * s / 24)) for s in range(24)])
    common.mesh_object(f"{n}_Water_NoCollide", wm.bm, col, water_mat, root, smooth=False)

    # ---- branches -----------------------------------------------------------------------
    branches = skeleton(p, rnd, mouth_r)
    rnd = random.Random(p["seed"] + 1000)            # flowers: own stream, the branches stay put
    print(f"{n}: fit scale %.2f %.2f %.2f" % fit(branches, p, 0.035))
    low = min((q.z for b in branches for q in b.pts if math.hypot(q.x, q.y) > 0.16), default=9)
    print(f"{n}: lowest branch point beyond r 0.16: z = {low:.3f}")
    m = Mesh()
    for b in branches:
        radii = [b.radius(k) for k in range(len(b.pts))]
        sides = 6 if b.r0 > 0.0035 else 5
        pts = list(b.pts)
        if b.level > 0:                              # start buried in the parent stem
            pts[0] = pts[0] - b.dir(0) * radii[0] * 0.8
        tube(m, pts, radii, b.s, sides, tip=True)
    tc = dict(branches=m.tris, spur=0, open=0, half=0, balloon=0, bud=0, leaf=0)

    # ---- spurs with umbels of flowers ----------------------------------------------------
    placed = []                                      # (centre, radius) of flowers, no overlaps
    stage_names = ("open", "half", "balloon", "bud")
    counts = dict(open=0, half=0, balloon=0, bud=0, leaf=0, spur=0)
    # cluster sites evenly along the flowering part of every branch (its outer ~70%) and the
    # tips; built tips first, then in random order until the triangle budget is spent, so the
    # density is even across the spray whatever the seed
    sites = []
    for bi, b in enumerate(branches):
        s_a, s_b = b.s[b.first_node], b.s[-1] - 0.012
        sv = s_a + rnd.uniform(0, 0.5) * p["spacing"]
        while sv < s_b:
            sites.append((bi, sv, False))
            sv += p["spacing"] * rnd.uniform(0.65, 1.35)
    rnd.shuffle(sites)
    sites = [(bi, b.s[-1], True) for bi, b in enumerate(branches)] + sites
    mains = [bi for bi, b in enumerate(branches) if b.level == 0]
    phyls = [rnd.uniform(0, 2 * math.pi) for _ in branches]
    budget = p["tris"] - vm_tris - 24
    for bi, sv, terminal in sites:
        if m.tris > budget - 150:
            break
        b = branches[bi]
        main_i = sum(1 for x in mains if x <= bi) - 1
        tile0 = p["tiles"][main_i % len(p["tiles"])]
        k, q, d, rk = b.at(sv)
        t_before = m.tris
        if terminal:
            sd = d
            tipq = q + d * rk * 2.5
        else:
            phyls[bi] += math.radians(137.5) * rnd.choice((1, 2, 3))
            n0, t0, b0 = frame(d)
            rd = t0 * math.cos(phyls[bi]) + b0 * math.sin(phyls[bi])
            sd = (rd * 0.85 + d * 0.45 + UP * 0.15).normalized()
            if rnd.random() < 0.5:                 # a short spur
                ls = rnd.uniform(0.008, 0.018)
                mid = q + sd * ls * 0.5 + d * ls * 0.12
                tipq = q + sd * ls + d * ls * 0.2
                tube(m, [q - sd * rk * 0.5, mid, tipq], [0.0019, 0.0017, 0.0015],
                     [sv, sv + ls * 0.5, sv + ls], 4)
                counts["spur"] += 1
            else:                                  # flowering straight from the node
                tipq = q + sd * rk * 0.9
        cone(m, tipq - sd * 0.0015, tipq + sd * 0.0035, 0.0017, 0.0026, 4, SCALES, 0.0, 1.0, rnd.uniform(0, 6))
        base = tipq + sd * 0.002
        tc["spur"] += m.tris - t_before
        nfl = rnd.randint(*p["umbel"]) if not terminal else rnd.randint(1, 2)
        n0, t0, b0 = frame(sd)
        az = rnd.uniform(0, 2 * math.pi)
        for j in range(nfl):
            if m.tris > budget - 60:
                break
            az += 2 * math.pi / nfl + rnd.uniform(-0.4, 0.4)
            spread = math.radians(rnd.uniform(38, 70))
            d0 = (sd * math.cos(spread) + (t0 * math.cos(az) + b0 * math.sin(az)) * math.sin(spread)).normalized()
            Lp = rnd.uniform(*p["petal"])
            lped = Lp * rnd.uniform(0.9, 1.7)
            d1 = (d0 + Vector((0, 0, -rnd.uniform(0.15, 0.6)))).normalized()
            pm = base + d0 * lped * 0.5
            pe = pm + d1 * lped * 0.5
            if terminal:
                st = "bud" if rnd.random() < 0.75 else "balloon"
            else:
                x = rnd.random()
                w = p["stages"]
                st = stage_names[0 if x < w[0] else 1 if x < w[0] + w[1] else 2 if x < w[0] + w[1] + w[2] else 3]
            rad = Lp * (1.05 if st == "open" else 0.8 if st == "half" else 0.5)
            cen = pe + d1 * Lp * 0.25
            if any((cen - c2).length < (rad + r2) * 0.62 for c2, r2 in placed):
                continue
            placed.append((cen, rad))
            t_before = m.tris
            tube(m, [base, pm, pe], [0.00075, 0.00068, 0.0006], [0.0, 0.5, 1.0], 3, reg=PEDICEL)
            counts[st] += 1
            tile = tile0 if rnd.random() < 0.7 else rnd.choice(p["tiles"])
            fdir = (d1 + Vector((rnd.uniform(-0.25, 0.25), rnd.uniform(-0.25, 0.25), rnd.uniform(-0.1, 0.3)))).normalized()
            if st == "bud":
                bud(m, pe, fdir, rnd.uniform(0.0028, 0.0036), rnd, sides=4, sepals=False,
                    shape=((0.22, 0.75), (0.62, 0.95)))
            elif st == "balloon":
                flower(m, pe, fdir, Lp, st, 4 if rnd.random() < 0.6 else 3, rnd)
            else:
                flower(m, pe, fdir, Lp, st, tile, rnd)
            tc[st] += m.tris - t_before
        t_before = m.tris
        if not terminal and rnd.random() < p["leaves"]:
            for _ in range(rnd.randint(1, 2)):
                a2 = rnd.uniform(0, 2 * math.pi)
                ldir = (sd * 0.7 + (t0 * math.cos(a2) + b0 * math.sin(a2)) * 0.7).normalized()
                leaf(m, tipq, ldir, UP, rnd.uniform(0.024, 0.042), rnd.uniform(0.008, 0.012),
                     rnd.uniform(0.25, 0.5), rnd.uniform(0.3, 0.9))
                counts["leaf"] += 1
        tc["leaf"] += m.tris - t_before
    print(f"{n}: final fit %.3f %.3f %.3f" % fit_mesh(m.bm, p))
    # a few petals fallen on the table round the vase, cupped, resting just clear of the top
    for _ in range(p["fallen"]):
        a = math.radians(rnd.uniform(110, 250))     # the -x side: the tables' books stand at +x
        rr = rnd.uniform(0.125, 0.19)
        L = rnd.uniform(*p["petal"])
        petal(m, Vector((rr * math.cos(a), rr * math.sin(a), 0.0024)), UP, rnd.uniform(0, 2 * math.pi), L, L * 0.47,
              math.radians(-10), math.radians(rnd.uniform(8, 16)), 0.5, rnd.uniform(0.06, 0.12),
              PETAL[rnd.choice((5, 0, 1))], base_r=0.0, twist=rnd.uniform(-0.2, 0.2))
    common.mesh_object(f"{n}_Blossom_NoCollide", m.bm, col, bl_mat, root)
    print(f"{n}: counts {counts}")
    print(f"{n}: tris {tc} vase {vm_tris}")

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
