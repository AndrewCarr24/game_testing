"""Large square cocktail ottoman in cognac leather (reference: a tailored single-cushion
leather cocktail ottoman of the RH / Holly Hunt kind, seen in an interiors shoot).

Construction, as an upholsterer would make it:
- Top: a picture-frame top. An inner panel framed by a border, joined by a seam 9 cm in
  from the edge, the border mitred at the four corners; seams and mitres are topstitched
  with two rows of tan saddle thread (a seam trim texture on the bands of faces along
  them, over a modelled V groove). The inner panel is padded up inside the seam and
  settles a little toward the centre; the border rolls softly down into the welt. The field where trays and books sit (to |x|, |y| ~0.48) stays
  between 0.434 and 0.442 m, so the room modules' decor at z 0.435 still sits into it.
- Body: one boxing band round the sides with a belly (more below mid-height, the weight of
  the padding), tight at the rounded corners, between leather welts at the top and bottom
  edges; the top welt and the top edge are crowned (a few mm higher and fuller mid-side).
- Below: the leather tucks under onto a flat underside, raised on four square tapered
  walnut legs (taper on the inner faces) shod with bronze sabots.
Every surface is an explicit, smooth-shaded mesh (no subdivision modifier), with a little
seeded low-frequency unevenness so the panels don't read machined.

Leather: Poly Haven `brown_leather` scan (CC0, 0.4 m tile), colour-matched to the house's
cognac; fetched once into build/polyhaven/, maps written to assets/textures as
T_LivingOttoman_Leather_*; the seam trim T_LivingOttoman_Seam_* is generated from the same
scan plus a modelled thread/crease height field. Offline the leather falls back to a flat
cognac with the generated leather normal.

Units are metres; origin is the floor centre; front faces -Y.
"""
import importlib
import json
import math
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

NAME = "LivingOttoman"

P = dict(
    name=NAME,
    size=(1.15, 1.15),
    height=0.42,               # top welt (edge) height; the padded top crowns ~2 cm above it
    leather_name="M_LivingOttoman_Leather",
    leather=(0.20, 0.078, 0.030),   # target mean colour (linear): a deep cognac
    corner=0.05,               # plan corner radius
    welt_r=0.0055,
    seam_inset=0.09,           # picture-frame seam, in from the edge
    frame_z=0.4375,            # border plateau
    puff=0.0042,               # the inner panel padded up just inside the seam
    sag=0.0012,                # ... and settling a little toward the centre (weight, use)
    belly=0.013,               # side panels' outward belly
    bow=0.004,                 # top edge / welt crowned outward and up mid-side
    leg_h=0.10,
    leg_inset=0.09,            # leg centre from the outer edge
    thread=(0.36, 0.25, 0.135),
    seed=5,
)

PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
PH_CACHE = os.path.join(PROJECT, "build", "polyhaven")
SCAN = "brown_leather"
SCAN_TILE = 0.4                # metres per tile (the scan's real size)
SEAM_W = 0.011                 # half width of the frame seam's band of faces (two grid cells)
TRIM_W = 0.022                 # half width the seam trim texture covers (the mitre cells are wider)
SEAM_L = 0.0384                # seam trim tile length along the seam (6 stitches of 6.4 mm)


# ------------------------------------------------------------------ textures

def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "game_testing-texture-fetch/1.0 (Blender; CC0 assets)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def _scan_maps():
    """Paths of the scan's 1k albedo and OpenGL normal (downloaded once), or None offline."""
    os.makedirs(PH_CACHE, exist_ok=True)
    out = {}
    for key, mapname in (("albedo", "Diffuse"), ("normal", "nor_gl")):
        path = os.path.join(PH_CACHE, f"{SCAN}_{key}_1k.jpg")
        if not os.path.exists(path):
            try:
                meta = json.loads(_get(f"https://api.polyhaven.com/files/{SCAN}"))
                data = _get(meta[mapname]["1k"]["jpg"]["url"])
            except Exception as e:
                print(f"living_ottoman: Poly Haven {SCAN} unavailable ({e}); generated leather")
                return None
            with open(path + ".tmp", "wb") as f:
                f.write(data)
            os.replace(path + ".tmp", path)
        out[key] = path
    return out


def _pixels(path):
    """(h, w, 3) float array, row 0 = bottom (Blender order), as stored (sRGB bytes)."""
    img = bpy.data.images.load(path)
    img.colorspace_settings.name = "Non-Color"     # raw stored values
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[..., :3]
    bpy.data.images.remove(img)
    return px


def _srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _write(name, rgb_bottom_up, non_color=False):
    """Save atomically (other agents build at the same time) as assets/textures/<name>.png."""
    path = os.path.join(textures.TEX_DIR, name + ".png")
    tmp_name = name + "_tmp%d" % os.getpid()
    tmp = textures._save(tmp_name, np.ascontiguousarray(rgb_bottom_up[::-1]), non_color=non_color)
    os.replace(tmp, path)
    return path


def _bilinear(img, rows, cols):
    """Sample img (h, w, c) at float pixel coords (wrapping)."""
    h, w, _ = img.shape
    r0 = np.floor(rows).astype(int)
    c0 = np.floor(cols).astype(int)
    fr = (rows - r0)[..., None]
    fc = (cols - c0)[..., None]
    r0 %= h
    c0 %= w
    r1 = (r0 + 1) % h
    c1 = (c0 + 1) % w
    return ((img[r0, c0] * (1 - fc) + img[r0, c1] * fc) * (1 - fr) +
            (img[r1, c0] * (1 - fc) + img[r1, c1] * fc) * fr)


def leather_textures(p, force=False):
    """(base colour path, normal path, seam base path, seam normal path) or None offline."""
    names = ("T_LivingOttoman_Leather_BaseColor", "T_LivingOttoman_Leather_Normal",
             "T_LivingOttoman_Seam_BaseColor", "T_LivingOttoman_Seam_Normal")
    paths = [os.path.join(textures.TEX_DIR, n + ".png") for n in names]
    if all(os.path.exists(x) for x in paths) and not force:
        return paths
    scan = _scan_maps()
    if scan is None:
        return None
    # leather albedo: the scan in linear, gained so its mean is the house's cognac
    alb = _srgb_to_lin(_pixels(scan["albedo"]))
    gain = np.array(p["leather"]) / alb.reshape(-1, 3).mean(axis=0)
    alb = np.clip(alb * gain, 0, 1)
    _write(names[0], textures._to_srgb(alb))
    nor = _pixels(scan["normal"])
    _write(names[1], nor, non_color=True)

    # seam trim: u along the seam (SEAM_L), v across (2 * TRIM_W), crease at v = 0.5
    W, H = 256, 256
    px_m = alb.shape[0] / SCAN_TILE                       # scan pixels per metre
    uu = (np.arange(W) + 0.5) / W * SEAM_L                # metres
    vv = (np.arange(H) + 0.5) / H * 2 * TRIM_W
    U, V = np.meshgrid(uu, vv)                            # (H, W), row 0 = v 0
    # the scan resampled at the same scale, made periodic in u by cross-fading the last quarter
    r0, c0 = 300.0, 200.0
    def crop(img, du=0.0):
        return _bilinear(img, r0 + V * px_m, c0 + (U + du) * px_m)
    fade = np.clip(U / (0.25 * SEAM_L), 0, 1)[..., None]
    base = crop(alb) * fade + crop(alb, SEAM_L) * (1 - fade)
    sn = crop(nor) * fade + crop(nor, SEAM_L) * (1 - fade)
    sn = sn * 2 - 1
    dv = V - TRIM_W
    h = np.zeros_like(U)
    h -= 0.00055 * np.exp(-(dv / 0.0008) ** 2)            # the closed seam's crease
    thread = np.zeros_like(U)
    pitch = SEAM_L / 6
    half_len, rad = 0.0021, 0.00042
    ang = math.radians(14)
    ca, sa = math.cos(ang), math.sin(ang)
    for row, c in enumerate((-0.0052, 0.0052)):
        h -= 0.00018 * np.exp(-((dv - c) / 0.0011) ** 2)   # the leather pulled down by the stitch line
        for k in range(-1, 7):
            cu = (k + 0.5) * pitch + (0.5 * pitch if row else 0.0)
            du = ((U - cu + SEAM_L / 2) % SEAM_L) - SEAM_L / 2
            dvv = dv - c
            a = du * ca + dvv * sa                          # along the slanted stitch
            b = -du * sa + dvv * ca
            a = np.clip(np.abs(a) - half_len, 0, None)
            d = np.sqrt(a ** 2 + b ** 2) / rad
            prof = np.sqrt(np.clip(1 - d ** 2, 0, 1))
            thread = np.maximum(thread, prof)
    h += 0.00038 * thread
    mask = np.clip(thread * 2.5, 0, 1)[..., None]
    crease_dark = 1 - 0.45 * np.exp(-(dv / 0.0011) ** 2)
    row_dark = 1 - 0.12 * (np.exp(-((dv + 0.0052) / 0.0012) ** 2) + np.exp(-((dv - 0.0052) / 0.0012) ** 2))
    leather = base * (crease_dark * row_dark)[..., None]
    tcol = np.array(p["thread"]) * (0.75 + 0.25 * thread[..., None])   # rounder thread reads lighter on top
    col = leather * (1 - mask) + tcol * mask
    _write(names[2], textures._to_srgb(col))
    gy, gx = np.gradient(h, 2 * TRIM_W / H, SEAM_L / W)
    n = np.stack([-gx, -gy, np.ones_like(h)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    keep = (1 - mask)
    n = np.stack([n[..., 0] + sn[..., 0] * keep[..., 0], n[..., 1] + sn[..., 1] * keep[..., 0],
                  n[..., 2] * (sn[..., 2] * keep[..., 0] + (1 - keep[..., 0]))], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    _write(names[3], n * 0.5 + 0.5, non_color=True)
    return paths


def leather_materials(p):
    tex = leather_textures(p)
    leather = common.pbr_material(p["leather_name"], (1, 1, 1) if tex else p["leather"], roughness=0.5)
    seam = common.pbr_material("M_LivingOttoman_Seam", (1, 1, 1) if tex else p["leather"], roughness=0.5)
    if tex:
        common.set_base_color_map(leather, textures.load(tex[0]))
        common.set_normal_map(leather, textures.load(tex[1], non_color=True), 0.8)
        common.set_base_color_map(seam, textures.load(tex[2]))
        common.set_normal_map(seam, textures.load(tex[3], non_color=True), 1.0)
    else:
        nm = textures.load(textures.leather_normal(), non_color=True)
        common.set_normal_map(leather, nm, 0.6)
        common.set_normal_map(seam, nm, 0.6)
    return leather, seam


# ------------------------------------------------------------------ shape functions

def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


class Shape:
    """The ottoman's surfaces as functions of plan position (metres)."""

    def __init__(self, p):
        self.p = p
        self.H = p["size"][0] / 2
        self.R = p["corner"]
        self.a = self.H - self.R
        self.r = p["welt_r"]
        self.zw = p["height"] - 0.002            # welt centre line at the corners
        rng = np.random.default_rng(p["seed"])
        self.waves = [(rng.uniform(2, 7) * rng.choice([-1, 1]), rng.uniform(2, 7) * rng.choice([-1, 1]),
                       rng.uniform(0, 2 * math.pi)) for _ in range(5)]

    def w(self, c):
        """1 mid-side, 0 at the rounded corners (c: coordinate along the side)."""
        return max(0.0, 1.0 - (abs(c) / self.a) ** 2)

    def g(self, e, reach=0.15):
        return max(0.0, 1.0 - e / reach) ** 2

    def bow(self, x, y):
        """Outward (dx, dy) and upward dz of the crowned top edge, fading inward."""
        B, Bz = self.p["bow"], self.p["bow"] * 0.9
        gx, gy = self.g(self.H - abs(x)), self.g(self.H - abs(y))
        dx = math.copysign(B * self.w(y) * gx, x)
        dy = math.copysign(B * self.w(x) * gy, y)
        dz = Bz * (self.w(y) * gx + self.w(x) * gy)
        return dx, dy, dz

    def noise(self, x, y, amp):
        return amp * sum(math.sin(kx * x + ky * y + ph) for kx, ky, ph in self.waves) / len(self.waves) * 1.6

    def sdf_e(self, x, y, h=None, R=None):
        """Distance inside the rounded outline (half size h, corner R)."""
        h = self.H if h is None else h
        R = self.R if R is None else R
        a = h - R
        qx, qy = abs(x) - a, abs(y) - a
        out = math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - R
        return -out

    def outline(self, h=None, R=None, n_side=6, n_corner=5):
        """Closed CCW rounded square: [(x, y, nx, ny)], starting mid +x side."""
        h = self.H if h is None else h
        R = self.R if R is None else R
        a = h - R
        pts = []
        for q in range(4):
            ang0 = q * math.pi / 2
            ca, sa = math.cos(ang0), math.sin(ang0)
            def rot(x, y):
                return x * ca - y * sa, x * sa + y * ca
            # straight half-side from mid (+x side, y 0) up to the corner start, then the arc,
            # then the next side's first half is produced by the next quadrant's rotation
            for k in range(n_side // 2):
                yy = a * k / (n_side // 2)
                x0, y0 = rot(h, yy)
                pts.append((x0, y0, *rot(1, 0)))
            for k in range(n_corner + 1):
                t = math.pi / 2 * k / n_corner
                x0, y0 = rot(a + R * math.cos(t), a + R * math.sin(t))
                pts.append((x0, y0, *rot(math.cos(t), math.sin(t))))
            for k in range(1, n_side // 2):
                xx = a - a * k / (n_side // 2)
                x0, y0 = rot(xx, h)
                pts.append((x0, y0, *rot(0, 1)))
        return pts


# ------------------------------------------------------------------ the top

def top_mesh(S):
    p = S.p
    r = S.r
    Ht = S.H - 0.8 * r                     # the top leather comes out of the welt's inner side
    Rt = S.R - 0.8 * r
    at = Ht - Rt
    s = p["seam_inset"]
    w = SEAM_W
    insets = [0.0, 0.005, 0.013, 0.024, 0.038, 0.056, s - w, s, s + w, 0.13, 0.18]
    cs = sorted({round(Ht - i, 5) for i in insets} | {0.3, 0.2, 0.1})
    X = [-c for c in reversed(cs)] + [0.0] + cs
    n = len(X)
    z_edge0 = S.zw + 0.4 * r
    zf = p["frame_z"]
    inner_edge = Ht - s                    # the seam line (pre-remap)
    bm = bmesh.new()
    vid, grid = {}, {}
    for i in range(n):
        for j in range(n):
            gx, gy = X[i], X[j]
            x, y = gx, gy
            if abs(x) > at and abs(y) > at:     # square -> quarter disc (elliptical grid mapping)
                u, v = (abs(x) - at) / Rt, (abs(y) - at) / Rt
                u2, v2 = u * math.sqrt(1 - v * v / 2), v * math.sqrt(1 - u * u / 2)
                x, y = math.copysign(at + Rt * u2, gx), math.copysign(at + Rt * v2, gy)
            e = max(0.0, S.sdf_e(x, y, Ht, Rt))
            e_box = min(Ht - abs(gx), Ht - abs(gy))
            dx, dy, dz = S.bow(x, y)
            # border roll: out of the welt, rounding over onto the plateau
            f = 1 - (1 - min(e / 0.07, 1.0)) ** 2.4
            z = z_edge0 + dz + (zf - z_edge0) * f
            # inner panel: padded up from the seam, settling slightly toward the centre
            if e_box > s:
                k = e_box - s
                rr2 = min(1.0, (gx * gx + gy * gy) / inner_edge ** 2)
                z += p["puff"] * (1 - math.exp(-k / 0.018)) - p["sag"] * (1 - rr2) * smoothstep(0, 0.1, k)
            # the frame seam (a soft V; the trim texture carries the crease and stitches)
            z -= 0.0026 * math.exp(-((e_box - s) / 0.0065) ** 2) * (1 if e_box > s - 2 * w else 0)
            # mitred corners of the border
            if abs(gx) > inner_edge - 1e-6 and abs(gy) > inner_edge - 1e-6:
                d = abs(abs(gx) - abs(gy)) / math.sqrt(2)
                z -= 0.003 * math.exp(-(d / 0.0055) ** 2) * min(1.0, e / 0.008)
            z += S.noise(x, y, 0.0003 if e_box > s + w else 0.0006)
            vid[i, j] = bm.verts.new((x + dx, y + dy, z))
            grid[vid[i, j]] = (gx, gy)
    for i in range(n - 1):
        for j in range(n - 1):
            a, b, c, d = vid[i, j], vid[i + 1, j], vid[i + 1, j + 1], vid[i, j + 1]
            if i == j:                               # cell on the x = y diagonal: split along it
                bm.faces.new((a, b, c)), bm.faces.new((a, c, d))
            elif j == n - 2 - i:                     # on the x = -y diagonal
                bm.faces.new((a, b, d)), bm.faces.new((b, c, d))
            else:
                bm.faces.new((a, b, c, d))
    bm.verts.index_update()
    return bm, {v.index: g for v, g in grid.items()}, (Ht, s, w)


def seam_trim(ob, grid, inner_edge):
    """Put the seam trim (material 1) on the faces along the frame seam and the four mitres,
    with u along the seam and v across it (crease at v 0.5, TRIM_W either side), mapped
    from each vertex's grid position (planar there, so the trim keeps its real scale)."""
    me = ob.data
    uv = me.uv_layers["UVMap"]
    w = SEAM_W
    r2 = math.sqrt(2)
    for poly in me.polygons:
        g = [grid[k] for k in poly.vertices]
        cx = sum(q[0] for q in g) / len(g)
        cy = sum(q[1] for q in g) / len(g)
        ax, ay = abs(cx), abs(cy)
        if ax >= inner_edge and ay >= inner_edge:
            # a mitre: the diagonal from the frame's inner corner out to the welt
            if any(abs(abs(q[0]) - abs(q[1])) / r2 > TRIM_W * 0.98 for q in g):
                continue
            kind = "m"
        elif inner_edge - w - 1e-6 <= max(ax, ay) <= inner_edge + w + 1e-6:
            kind = "x" if ax > ay else "y"
        else:
            continue
        poly.material_index = 1
        for li in poly.loop_indices:
            gx, gy = grid[me.loops[li].vertex_index]
            if kind == "m":
                along = (abs(gx) + abs(gy)) / r2
                across = (abs(gx) - abs(gy)) / r2 * (1 if cx * cy > 0 else -1)
            elif kind == "x":
                along = gy if cx > 0 else -gy
                across = inner_edge - abs(gx)
            else:
                along = -gx if cy > 0 else gx
                across = inner_edge - abs(gy)
            uv.data[li].uv = (along / SEAM_L, 0.5 + across / (2 * TRIM_W))


# ------------------------------------------------------------------ the body (sides + underside)

def body_mesh(S):
    p = S.p
    r = S.r
    zb = 0.0 + p["leg_h"] + r                 # bottom welt centre
    ring_pts = S.outline(n_side=8, n_corner=4)
    ts = [0.0, 0.05, 0.14, 0.27, 0.42, 0.58, 0.73, 0.86, 0.95, 1.0]
    bm = bmesh.new()
    rings = []
    for t in ts:
        ring = []
        for x, y, nx, ny in ring_pts:
            dx, dy, dz = S.bow(x, y)
            z_top = S.zw - 0.8 * r + dz
            z_bot = zb + 0.8 * r
            z = z_bot + (z_top - z_bot) * t
            along = y if abs(nx) > abs(ny) else x
            side = round(math.atan2(ny, nx) / (math.pi / 2)) % 4
            belly = p["belly"] * (1.0, 0.86, 1.08, 0.93)[side] * S.w(along) ** 1.2 * math.sin(math.pi * t ** 0.85) ** 0.8
            off = belly + S.noise(x * 1.3 + z, y * 1.3 - z, 0.0008) * math.sin(math.pi * t)
            ring.append(bm.verts.new((x + nx * off + dx * t ** 1.5, y + ny * off + dy * t ** 1.5, z)))
        rings.append(ring)
    # under-tuck below the bottom welt, then the flat underside
    tuck = [bm.verts.new((x - nx * 0.012, y - ny * 0.012, zb - 0.9 * r)) for x, y, nx, ny in ring_pts]
    rings.insert(0, tuck)
    m = len(ring_pts)
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(m):
            bm.faces.new((a[k], a[(k + 1) % m], b[(k + 1) % m], b[k]))
    under = bm.faces.new(list(reversed(tuck)))
    under.smooth = False
    return bm, zb


def welts(S, zb):
    sys.path.insert(0, HERE)
    import living_sofa
    r = S.r
    bm = bmesh.new()
    top = []
    for x, y, nx, ny in S.outline(n_side=6, n_corner=5):
        dx, dy, dz = S.bow(x, y)
        top.append((x + dx, y + dy, S.zw + dz))
    living_sofa.tube_into(bm, top, (0, 0, 1), r=r, sides=6)
    bot = [(x, y, zb) for x, y, nx, ny in S.outline(n_side=6, n_corner=5)]
    living_sofa.tube_into(bm, bot, (0, 0, 1), r=r, sides=6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


# ------------------------------------------------------------------ legs

def legs_meshes(S):
    p = S.p
    h = p["leg_h"] + 0.004                     # into the underside
    li = S.H - p["leg_inset"]
    top_s, bot_s, sab_h = 0.05, 0.034, 0.024
    wood, bronze = bmesh.new(), bmesh.new()

    def leg_section(z):
        """Half extents (outer, inner) of the leg at height z: the outer faces are plumb,
        the inner ones taper (the leg leans its weight to the corner)."""
        t = z / h
        s_in = bot_s + (top_s - bot_s) * t
        return top_s / 2, s_in - top_s / 2

    def block(bm, z0, z1, grow, sx, sy):
        cx, cy = sx * li, sy * li
        vs = []
        for z in (z0, z1):
            o, i_ = leg_section(z)
            o += grow
            i_ += grow
            # x from the inner face to the outer face, in the leg's corner direction
            xs = (cx - sx * i_, cx + sx * o)
            ys = (cy - sy * i_, cy + sy * o)
            vs.append([bm.verts.new((xs[a], ys[b], z)) for a, b in ((0, 0), (1, 0), (1, 1), (0, 1))])
        lo, hi = vs
        for k in range(4):
            q = (k + 1) % 4
            f = bm.faces.new((lo[k], lo[q], hi[q], hi[k]))
        bm.faces.new(hi)
        bm.faces.new(lo)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    for sx in (-1, 1):
        for sy in (-1, 1):
            block(wood, sab_h - 0.002, h, 0.0, sx, sy)
            block(bronze, 0.0, sab_h, 0.0012, sx, sy)
    return wood, bronze


# ------------------------------------------------------------------ build

def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)
    leather, seam = leather_materials(p)
    walnut = materials.walnut()
    bronze = materials.bronze()
    S = Shape(p)

    # top: picture-frame panel with the stitched seam band (material 1)
    bm, grid_co, (Ht, s, w) = top_mesh(S)
    top = common.mesh_object(f"{n}_Top", bm, col, leather, root)
    top.data.materials.append(seam)
    common.box_uv(top, SCAN_TILE)
    seam_trim(top, grid_co, Ht - s)

    bm, zb = body_mesh(S)
    body = common.mesh_object(f"{n}_Body", bm, col, leather, root)
    common.box_uv(body, SCAN_TILE)

    pipe = common.mesh_object(f"{n}_Piping", welts(S, zb), col, leather, root)
    common.box_uv(pipe, SCAN_TILE)

    wood, brz = legs_meshes(S)
    legs = common.mesh_object(f"{n}_Legs", wood, col, walnut, root, smooth=False)
    common.add_bevel(legs, 0.0025, segments=2)
    common.box_uv(legs, 0.5)
    sab = common.mesh_object(f"{n}_Sabots", brz, col, bronze, root, smooth=False)
    common.add_bevel(sab, 0.0015, segments=2)
    common.box_uv(sab, 0.5)

    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{NAME}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
