"""Framed and unframed artworks for the whole house (one asset per piece: the small
art_*.py / living_art_*.py wrappers pick a variant).

`build(variant=...)` picks size, frame treatment and painting from VARIANTS: the five
original gallery pieces below plus the collection in art_collection.py (painted by
art_painters.py). Frames: slim black metal or wood with a bevelled mat and glass, a
white box frame with the sheet floated inside, an unframed canvas on a deep
stretcher, or a black floater tray (see art_collection). Frames, mats and glass share
materials across pieces; each piece's only unique material is its artwork.

Paintings are numpy-generated (no external images) and saved as T_Art_<Variant>.png
at the piece's own texture size; they are repainted only when missing or resized.

Hangs on a wall. Origin: centre of the frame, on the wall plane. The picture faces
-Y and extends +-w/2 in X and +-h/2 in Z. The frame's back sits 1 cm off the wall
(a hidden spacer fills the gap).
"""
import importlib
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

sys.path.insert(0, HERE)
import art_collection  # noqa: E402
import art_painters  # noqa: E402

importlib.reload(common)
importlib.reload(textures)
importlib.reload(materials)
importlib.reload(art_painters)
importlib.reload(art_collection)

NAME = "PictureFrame"

# size = outer frame (w, h) in metres; border = visible mat width, frame edge to window
VARIANTS = {
    "colorfield_a": dict(size=(0.9, 1.2), border=0.09, art="colorfield_a", rough=0.8, px=256),
    "colorfield_b": dict(size=(1.2, 0.8), border=0.09, art="colorfield_b", rough=0.8, px=256),
    "geometric_a": dict(size=(0.8, 0.8), border=0.09, art="geometric_a", rough=0.78, px=512),
    "geometric_b": dict(size=(0.6, 0.8), border=0.08, art="geometric_b", rough=0.88, px=384),
    "linework_a": dict(size=(0.9, 1.2), border=0.10, art="linework_a", rough=0.9, px=512),
}

P = dict(
    name=NAME,
    variant="colorfield_a",
    face=0.02,             # width of the frame face
    depth=0.04,            # frame depth
    spacer=0.01,           # gap between wall and the frame's back
    mat_t=0.0035,          # mat board thickness (= width of the 45 degree bevel)
    mat_front=0.030,       # depth of the mat's front face, measured from the frame's back
    glass_at=0.0315,
    art_at=0.0255,
    art_overlap=0.012,     # artwork extends this far behind the mat on every side
    mat=(0.88, 0.87, 0.83),
)


# =============================================================================
# painting toolkit (all colours are sRGB 0..1, rows run top to bottom)
# =============================================================================

def _fnoise(h, w, rng, beta=2.0, ax=1.0, ay=1.0):
    """Fractal noise with unit standard deviation. ax / ay penalise detail along
    x / y: a large ax gives horizontal streaks (smooth along x)."""
    white = rng.standard_normal((h, w))
    ky = np.fft.fftfreq(h)[:, None] * h
    kx = np.fft.fftfreq(w)[None, :] * w
    k = np.sqrt((kx * ax) ** 2 + (ky * ay) ** 2)
    k[0, 0] = 1.0
    spec = np.fft.fft2(white) / k ** beta
    spec[0, 0] = 0
    out = np.real(np.fft.ifft2(spec))
    return out / (out.std() + 1e-9)


def _smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _grid(h, w):
    """X, Y in units of the picture height; Y runs 0 (top) to 1 (bottom)."""
    y = (np.arange(h) + 0.5) / h
    x = (np.arange(w) + 0.5) / h
    return np.meshgrid(x, y)


def _col(c):
    return np.array(c, dtype=float)


def _weave(h, w, rng, pitch=3.7, amp=0.012):
    """Faint canvas weave as a multiplicative pattern."""
    yy, xx = np.mgrid[0:h, 0:w]
    jx = 0.35 * _fnoise(h, w, rng, 1.0)
    jy = 0.35 * _fnoise(h, w, rng, 1.0)
    a = np.sin(2 * np.pi * xx / pitch + jx)
    b = np.sin(2 * np.pi * yy / pitch + jy)
    pat = 0.55 * a * b + 0.3 * (a + b) * 0.5
    thick = 0.6 * _fnoise(h, w, rng, 0.5)
    return 1.0 + amp * (pat + 0.35 * thick)


def _blur(img, sigma):
    h, w = img.shape[:2]
    ky = np.fft.fftfreq(h)[:, None]
    kx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2 * (np.pi * sigma) ** 2 * (kx ** 2 + ky ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(img) * g))


# ----------------------------------------------------------------- colour fields

def _colorfield(w, h, seed, ground, blocks):
    """Soft-edged stacked colour fields (Rothko-like): a stained ground, then each
    block built from several translucent glazes with feathered, breathing edges.
    Block boxes are fractions of the picture width / height."""
    rng = np.random.default_rng(seed)
    X, Y = _grid(h, w)
    asp = w / h
    cloud = _fnoise(h, w, rng, 2.2, ax=2.0, ay=1.0)
    cloud2 = _fnoise(h, w, rng, 1.6, ax=5.0, ay=1.0)
    tooth = _fnoise(h, w, rng, 0.45)
    img = _col(ground) * (1 + 0.035 * cloud + 0.018 * cloud2 + 0.006 * tooth)[..., None]
    edge = np.minimum.reduce([X, asp - X, Y, 1 - Y])
    img *= (1 - 0.10 * (1 - _smooth(0.0, 0.05, edge)))[..., None]

    for b in blocks:
        fx0, fy0, fx1, fy1 = b["box"]
        x0, x1, y0, y1 = fx0 * asp, fx1 * asp, fy0, fy1
        wob = (0.0034 * _fnoise(h, w, rng, 2.4, ax=2, ay=1) + 0.0012 * _fnoise(h, w, rng, 1.0, ax=10, ay=1))
        rad = 0.03
        base_d = rad - _sdf_box(X, Y, (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 - rad, (y1 - y0) / 2 - rad) + wob
        low = _fnoise(h, w, rng, 2.7, ax=1.3, ay=1)
        mid = _fnoise(h, w, rng, 1.7, ax=6, ay=1)
        brush = _fnoise(h, w, rng, 1.0, ax=18, ay=1)
        hair = _fnoise(h, w, rng, 0.5, ax=7, ay=1)
        for col, inset, blur, alpha in b["glazes"]:
            m = _smooth(-blur, blur, base_d - inset) * alpha
            # each glaze breathes: thinner in places so the layer below shows through
            m = m * np.clip(1 + 0.14 * _fnoise(h, w, rng, 2.4, ax=1.5, ay=1), 0.5, 1.4)
            tone_g = 1 + 0.075 * low + 0.035 * mid + 0.007 * brush + 0.004 * hair + 0.006 * tooth
            c = _col(col) * tone_g[..., None]
            img = img * (1 - m[..., None]) + c * m[..., None]
    img *= _weave(h, w, rng, amp=0.010)[..., None]
    return np.clip(img, 0, 1)


def _art_colorfield_a(w, h):
    # dark cognac ground; muted ochre field above a rust-cognac one
    return _colorfield(w, h, 11, (0.235, 0.105, 0.080), [
        dict(box=(0.105, 0.090, 0.895, 0.520), glazes=[
            ((0.55, 0.30, 0.15), -0.014, 0.034, 0.42),       # bleed halo
            ((0.70, 0.47, 0.20), 0.0, 0.020, 0.80),
            ((0.82, 0.62, 0.32), 0.040, 0.055, 0.42),        # luminous core
            ((0.62, 0.36, 0.15), 0.0, 0.012, 0.16),
        ]),
        dict(box=(0.105, 0.585, 0.895, 0.910), glazes=[
            ((0.33, 0.12, 0.07), -0.014, 0.034, 0.42),
            ((0.46, 0.19, 0.10), 0.0, 0.020, 0.84),
            ((0.60, 0.29, 0.14), 0.045, 0.060, 0.36),
            ((0.38, 0.14, 0.08), 0.0, 0.012, 0.16),
        ]),
    ])


def _art_colorfield_b(w, h):
    # tobacco-putty ground; wide ink-blue field above a slim cognac one
    return _colorfield(w, h, 29, (0.60, 0.46, 0.31), [
        dict(box=(0.060, 0.095, 0.940, 0.610), glazes=[
            ((0.20, 0.24, 0.34), -0.014, 0.034, 0.34),
            ((0.065, 0.095, 0.185), 0.0, 0.020, 0.90),
            ((0.14, 0.19, 0.32), 0.050, 0.065, 0.36),
            ((0.04, 0.06, 0.13), 0.0, 0.012, 0.18),
        ]),
        dict(box=(0.085, 0.700, 0.915, 0.900), glazes=[
            ((0.60, 0.34, 0.16), -0.012, 0.030, 0.42),
            ((0.56, 0.26, 0.12), 0.0, 0.018, 0.84),
            ((0.74, 0.46, 0.20), 0.032, 0.050, 0.34),
        ]),
    ])


# ------------------------------------------------------------------- geometric

def _sdf_box(X, Y, cx, cy, hx, hy):
    qx = np.abs(X - cx) - hx
    qy = np.abs(Y - cy) - hy
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0)


def _sdf_circle(X, Y, cx, cy, r):
    return np.hypot(X - cx, Y - cy) - r


def _geometric(w, h, seed, ground, shapes, grain=0.012):
    """Flat matte paint with taped edges: each shape is (sdf function, colour).
    Edges are a pixel wide with a trace of hand wobble; paint has faint
    roller stipple and slow tonal drift."""
    rng = np.random.default_rng(seed)
    X, Y = _grid(h, w)
    drift = _fnoise(h, w, rng, 2.4)
    stipple = _fnoise(h, w, rng, 0.25)
    wob = 0.00045 * _fnoise(h, w, rng, 1.6)
    roller = _fnoise(h, w, rng, 1.3, ax=6, ay=1)
    paper = _col(ground)
    img = paper * (1 + 0.012 * drift + 0.5 * grain * stipple)[..., None]
    for sdf, col in shapes:
        d = sdf(X, Y) + wob
        cov = np.clip(0.5 - d * h, 0, 1)
        # thin ridge of paint along the tape edge
        ridge = np.exp(-((d * h + 1.2) / 1.6) ** 2) * 0.05
        paint = _col(col) * (1 + 0.022 * drift + 0.014 * roller + grain * stipple)[..., None]
        paint = paint * (1 - ridge[..., None])
        img = img * (1 - cov[..., None]) + paint * cov[..., None]
    img *= _weave(h, w, rng, amp=0.012)[..., None]
    edge = np.minimum.reduce([X, (w / h) - X, Y, 1 - Y])
    img *= (1 - 0.06 * (1 - _smooth(0.0, 0.04, edge)))[..., None]
    return np.clip(img, 0, 1)


def _art_geometric_a(w, h):
    ink, ochre, cognac = (0.085, 0.13, 0.25), (0.80, 0.58, 0.21), (0.60, 0.26, 0.13)
    cream, umber = (0.925, 0.89, 0.81), (0.13, 0.095, 0.075)
    return _geometric(w, h, 41, (0.865, 0.82, 0.735), [
        (lambda X, Y: _sdf_box(X, Y, 0.340, 0.230, 0.235, 0.325), ink),          # bleeds off the top
        (lambda X, Y: _sdf_box(X, Y, 0.900, 0.640, 0.300, 0.190), ochre),        # bleeds off the right
        (lambda X, Y: _sdf_circle(X, Y, 0.390, 0.565, 0.135), cognac),           # straddles the blue's edge
        (lambda X, Y: _sdf_box(X, Y, 0.500, 0.880, 0.300, 0.0045), umber),       # hairline
    ])


def _art_geometric_b(w, h):
    ink, ochre, cognac = (0.10, 0.145, 0.27), (0.80, 0.58, 0.21), (0.58, 0.25, 0.12)
    return _geometric(w, h, 53, (0.915, 0.895, 0.845), [
        (lambda X, Y: _sdf_box(X, Y, 0.340, 0.735, 0.230, 0.0075), ink),
        (lambda X, Y: _sdf_circle(X, Y, 0.428, 0.372, 0.066), ochre),
        (lambda X, Y: _sdf_box(X, Y, 0.215, 0.595, 0.0050, 0.140), cognac),
    ], grain=0.010)


# -------------------------------------------------------------------- line art

def _centripetal(points, per_seg=60):
    """Centripetal Catmull-Rom spline through `points` (Nx2)."""
    p = np.asarray(points, dtype=float)
    p = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        t0 = 0.0
        t1 = t0 + np.linalg.norm(p1 - p0) ** 0.5
        t2 = t1 + np.linalg.norm(p2 - p1) ** 0.5
        t3 = t2 + np.linalg.norm(p3 - p2) ** 0.5
        t = np.linspace(t1, t2, per_seg, endpoint=False)[:, None]
        a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
        a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
        a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
        b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
        b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
        out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    out.append(p[-2][None, :])
    return np.vstack(out)


def _arc(cx, cy, rx, ry, a0, a1, step=15):
    n = max(2, int(abs(a1 - a0) / step) + 1)
    return [(cx + rx * np.cos(np.radians(a)), cy - ry * np.sin(np.radians(a))) for a in np.linspace(a0, a1, n)]


def _profile_path():
    """One continuous line: up the back of the neck and head, round a bun, over the
    crown, down the forehead, nose, lips, chin and throat, and away across the
    collarbone. Picture-height units, x right, y down."""
    pts = [(0.060, 0.880), (0.140, 0.810), (0.215, 0.735), (0.245, 0.640), (0.225, 0.545),
           (0.190, 0.470), (0.172, 0.370), (0.160, 0.290), (0.156, 0.235)]
    bx, by = 0.205, 0.140
    for th, r in zip(np.linspace(-145, -362, 17), np.linspace(0.082, 0.070, 17)):
        pts.append((bx + r * np.cos(np.radians(th)), by - r * np.sin(np.radians(th))))
    pts += [(0.277, 0.178), (0.298, 0.196), (0.340, 0.196), (0.405, 0.205), (0.466, 0.238), (0.506, 0.285),
            (0.530, 0.332), (0.538, 0.356), (0.525, 0.384), (0.552, 0.414), (0.566, 0.434),
            (0.553, 0.445), (0.530, 0.452), (0.528, 0.468), (0.536, 0.480), (0.524, 0.491),
            (0.531, 0.505), (0.521, 0.520), (0.524, 0.548), (0.506, 0.577), (0.462, 0.590),
            (0.428, 0.575), (0.408, 0.610), (0.410, 0.690), (0.440, 0.765), (0.500, 0.820),
            (0.575, 0.850), (0.640, 0.855)]
    return pts


def _art_linework_a(w, h):
    rng = np.random.default_rng(67)
    S = 2                                   # supersampling
    H, W = h * S, w * S
    pts = _centripetal(_profile_path(), per_seg=60)
    n = len(pts)
    # hand tremor
    t = np.linspace(0, 1, n)
    for k, amp in ((7, 0.0016), (23, 0.0007)):
        ph = rng.uniform(0, 6.28, 4)
        pts = pts + amp * np.stack([np.sin(2 * np.pi * k * t + ph[0]) + 0.5 * np.sin(5.3 * k * t + ph[1]),
                                    np.sin(2 * np.pi * k * t + ph[2]) + 0.5 * np.sin(4.1 * k * t + ph[3])], 1)
    # pen pressure: taper in and out, slow swell
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    arc = np.concatenate([[0], np.cumsum(seg)])
    arc /= arc[-1]
    swell = np.interp(np.linspace(0, 1, n), np.linspace(0, 1, 40), rng.uniform(0.0, 1.0, 40))
    swell = np.convolve(swell, np.ones(25) / 25, mode="same")
    press = 1.9 + 1.1 * swell
    press *= np.minimum(1.0, 0.18 + arc / 0.035) * np.minimum(1.0, 0.18 + (1 - arc) / 0.05)
    radius = press * S * 1.0                # pixels in the supersampled canvas
    cov = np.zeros((H, W), dtype=np.float32)
    px = pts[:, 0] * h * S
    py = pts[:, 1] * h * S
    for x, y, r in zip(px, py, radius):
        ri = int(np.ceil(r + 1.5))
        x0, y0 = int(x) - ri, int(y) - ri
        xs, ys = np.arange(x0, x0 + 2 * ri + 1), np.arange(y0, y0 + 2 * ri + 1)
        if x0 < 0 or y0 < 0 or x0 + 2 * ri + 1 > W or y0 + 2 * ri + 1 > H:
            continue
        d = np.hypot(xs[None, :] + 0.5 - x, ys[:, None] + 0.5 - y)
        c = np.clip(r - d + 0.5, 0, 1)
        win = cov[y0:y0 + 2 * ri + 1, x0:x0 + 2 * ri + 1]
        np.maximum(win, c, out=win)
    cov = cov.reshape(h, S, w, S).mean(axis=(1, 3))

    # paper: warm cream, fibres and a slow tonal drift
    X, Y = _grid(h, w)
    drift = _fnoise(h, w, rng, 2.6)
    fibre = _fnoise(h, w, rng, 0.6)
    speck = _fnoise(h, w, rng, 0.2)
    paper = _col((0.935, 0.895, 0.800)) * (1 + 0.018 * drift + 0.012 * fibre + 0.008 * speck)[..., None]
    edge = np.minimum.reduce([X, (w / h) - X, Y, 1 - Y])
    paper *= (1 - 0.07 * (1 - _smooth(0.0, 0.05, edge)))[..., None]
    # ink: blue-black, slightly broken where the pen skims the tooth of the paper
    tooth = np.clip(0.5 + 0.5 * fibre + 0.5 * speck, 0, 1)
    dens = np.clip(cov * (0.93 + 0.10 * tooth) * (0.92 + 0.08 * drift), 0, 1)
    halo = np.clip(_blur(cov, 1.6), 0, 1) * 0.10          # a little bleed into the fibres
    ink = _col((0.055, 0.065, 0.115))
    img = paper * (1 - halo[..., None]) + paper * _col((0.80, 0.78, 0.76)) * halo[..., None]
    img = img * (1 - dens[..., None]) + ink * dens[..., None]
    return np.clip(img, 0, 1)


ART = {
    "colorfield_a": _art_colorfield_a,
    "colorfield_b": _art_colorfield_b,
    "geometric_a": _art_geometric_a,
    "geometric_b": _art_geometric_b,
    "linework_a": _art_linework_a,
}

# the rest of the collection (art_collection.py): style + spec painted by art_painters
VARIANTS.update(art_collection.PIECES)


def _tex_name(variant):
    return "T_Art_" + "".join(s.capitalize() for s in variant.split("_"))


def art_texture(variant, v, force=False):
    """Paint and save T_Art_<Variant>.png at the variant's texture size (long side
    `px`); repainted only when the file is missing or has another size. Delete the
    file after changing a piece's spec."""
    name = _tex_name(variant)
    path = os.path.join(textures.TEX_DIR, name + ".png")
    tw, th = art_collection.texture_px(v)
    if os.path.exists(path) and not force:
        img = bpy.data.images.load(path, check_existing=False)
        size = tuple(img.size)
        bpy.data.images.remove(img)
        if size == (tw, th):
            return path
    if v.get("art") in ART:
        # the original pieces were tuned at 1024 px: paint them there and box-filter down
        f = max(1, 1024 // max(tw, th))
        rgb = art_painters.down(ART[v["art"]](tw * f, th * f), f)
    else:
        rgb = art_painters.paint(v["style"], tw, th, v["spec"], art_collection.art_size(v))
    return textures._save(name, np.clip(rgb, 0, 1))


# =============================================================================
# geometry
# =============================================================================

def _ring_mesh(bm, profile, hw, hh, y_of):
    """Rectangular ring swept around a w x h outline. `profile` is a closed list of
    (inset, depth): each point becomes a rectangle with half extents (hw - inset,
    hh - inset) at that depth; consecutive rectangles are joined (mitred corners)."""
    rings = []
    for inset, depth in profile:
        x, z, y = hw - inset, hh - inset, y_of(depth)
        rings.append([bm.verts.new(v) for v in ((-x, y, -z), (x, y, -z), (x, y, z), (-x, y, z))])
    for i in range(len(rings)):
        a, b = rings[i], rings[(i + 1) % len(rings)]
        for k in range(4):
            bm.faces.new((a[k], a[(k + 1) % 4], b[(k + 1) % 4], b[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def _quad(bm, x, z, y):
    vs = [bm.verts.new(v) for v in ((-x, y, -z), (x, y, -z), (x, y, z), (-x, y, z))]
    bm.faces.new(vs)          # normal = +x cross +z = -y, towards the viewer
    return bm


def _set_uv(ob, x, z):
    me = ob.data
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = ((co.x + x) / (2 * x), (co.z + z) / (2 * z))


def _art_material(variant, v):
    tex = art_texture(variant, v)
    m = common.pbr_material("M_Art_" + variant, (1, 1, 1), roughness=v.get("rough", 0.85),
                            metallic=v.get("metal", 0.0))
    common.set_base_color_map(m, textures.load(tex))
    return m


def _box(name, size, y_front, col, mat, root):
    """Box of `size` (x, depth, z) whose front face sits at y = y_front."""
    ob = common.mesh_object(name, common.box_bmesh(size), col, mat, root, smooth=False)
    ob.location = (0, y_front + size[1] / 2, 0)
    return ob


def build(**overrides):
    p = {**P, **overrides}
    v = VARIANTS[p["variant"]]
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    w, h = v["size"]
    hw, hh = w / 2, h / 2
    fr = v.get("frame", "metal")
    y0 = -p["spacer"]                        # y of the frame's / canvas's back

    def y_of(d):
        return y0 - d

    black = materials.black_metal()
    glass = materials.glass("M_Glass_Picture", alpha=0.06, roughness=0.02)
    white = common.pbr_material("M_Picture_Mat", p["mat"], roughness=0.92)
    art_m = _art_material(p["variant"], v)
    aw, ah = art_collection.art_size(v)
    c = 0.0012                               # tiny chamfers that catch the light

    if fr in ("metal", "wood"):
        f = art_collection.FRAMES[fr]
        face, depth = (p["face"], p["depth"]) if fr == "metal" else (f["face"], f["depth"])
        fmat = black if fr == "metal" else (materials.walnut() if v.get("wood") == "walnut" else materials.smoked_oak())
        profile = [(0.0, 0.0), (0.0, depth - c), (c, depth), (face - c, depth), (face, depth - c), (face, 0.0)]
        frame = common.mesh_object(f"{n}_Frame", _ring_mesh(bmesh.new(), profile, hw, hh, y_of),
                                   col, fmat, root, smooth=False)
        if fr == "wood":
            common.box_uv(frame, 0.5)
        ow, oh = hw - face - 0.0004, hh - face - 0.0004          # opening in the frame
        border = v.get("border", 0.09)
        art_at, glass_at = p["art_at"], p["glass_at"]
        if border > 0:
            bw, bh = hw - face - border, hh - face - border      # window at the mat's front face
            t = p["mat_t"]
            zf = p["mat_front"]
            mat_profile = [(hw - ow, zf), (hw - bw, zf), (hw - bw + t, zf - t), (hw - ow, zf - t)]
            common.mesh_object(f"{n}_Mat", _ring_mesh(bmesh.new(), mat_profile, hw, hh, y_of),
                               col, white, root, smooth=False)
        else:                                # photograph mounted right up to the frame
            art_at, glass_at = depth - 0.008, depth - 0.005
        art = common.mesh_object(f"{n}_Art", _quad(bmesh.new(), aw / 2, ah / 2, y_of(art_at)),
                                 col, art_m, root, smooth=False)
        _set_uv(art, aw / 2, ah / 2)
        common.mesh_object(f"{n}_Glass", _quad(bmesh.new(), ow, oh, y_of(glass_at)), col, glass, root,
                           smooth=False)
        back = common.mesh_object(f"{n}_Backing", common.box_bmesh((2 * ow, 0.022, 2 * oh)), col, black, root,
                                  smooth=False)
        back.location = (0, y_of(0.011), 0)

    elif fr == "box":
        f = art_collection.FRAMES["box"]
        face, depth = f["face"], f["depth"]
        profile = [(0.0, 0.0), (0.0, depth - c), (c, depth), (face - c, depth), (face, depth - c), (face, 0.0)]
        common.mesh_object(f"{n}_Frame", _ring_mesh(bmesh.new(), profile, hw, hh, y_of), col, white, root,
                           smooth=False)
        ow, oh = hw - face - 0.0004, hh - face - 0.0004
        _box(f"{n}_Backing", (2 * ow, 0.012, 2 * oh), y_of(0.012), col, white, root)
        # the sheet floats 6 mm proud of the backing on a hidden riser, so it casts a shadow line
        _box(f"{n}_Riser", (aw - 0.06, 0.006, ah - 0.06), y_of(0.018), col, white, root)
        paper_ob = _box(f"{n}_Art", (aw, 0.0015, ah), y_of(0.0195), col, art_m, root)
        _set_uv(paper_ob, aw / 2, ah / 2)
        common.mesh_object(f"{n}_Glass", _quad(bmesh.new(), ow, oh, y_of(depth - 0.006)), col, glass, root,
                           smooth=False)

    elif fr == "canvas":
        depth = v.get("depth", art_collection.FRAMES["canvas"]["depth"])
        canvas = _box(f"{n}_Art", (w, depth, h), y_of(depth), col, art_m, root)
        common.add_bevel(canvas, 0.003, segments=1)
        _set_uv(canvas, w / 2, h / 2)          # front: the painting; sides: its edges, wrapped round

    elif fr == "floater":
        f = art_collection.FRAMES["floater"]
        face, gap, depth = f["face"], f["gap"], f["depth"]
        profile = [(0.0, 0.0), (0.0, depth - c), (c, depth), (face - c, depth), (face, depth - c), (face, 0.0)]
        common.mesh_object(f"{n}_Frame", _ring_mesh(bmesh.new(), profile, hw, hh, y_of), col, black, root,
                           smooth=False)
        ow, oh = hw - face - 0.0004, hh - face - 0.0004
        _box(f"{n}_Tray", (2 * ow, 0.008, 2 * oh), y_of(0.008), col, black, root)
        cd = depth - 0.008 - 0.004              # canvas face sits 4 mm behind the frame's lip
        canvas = _box(f"{n}_Art", (aw, cd, ah), y_of(0.008 + cd), col, art_m, root)
        common.add_bevel(canvas, 0.002, segments=1)
        _set_uv(canvas, aw / 2, ah / 2)
    else:
        raise ValueError(fr)

    # hidden spacer between the wall and the back, so nothing floats
    sp = common.mesh_object(f"{n}_Spacer", common.box_bmesh((max(0.1, w - 0.16), p["spacer"], max(0.1, h - 0.16))),
                            col, black, root, smooth=False)
    sp.location = (0, -p["spacer"] / 2, 0)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
