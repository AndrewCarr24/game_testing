"""Designer sled-base lounge chair: a polished chrome tube frame (two continuous side loops,
tight mandrel bends, welded cross rails, clip-on glides), walnut seat deck / back panel /
shaped arm pads, and boxed cognac leather cushions.

Reference: the Bauhaus-lineage chromed tube club chairs (Breuer / Thonet S 35 walnut arm
pads, Knoll / Cassina finish): plump boxed cushions with self-welts on both seams, a crowned
seat with a soft sitting hollow, a channel-stitched back cushion, and the two cushions pressed
into each other where they meet.

Cushions are generated directly at their final density (no subdivision modifier): a grid on
a cube is mapped onto a rounded box (plan corners rc, seam edges re), then displaced (crowns,
boxing bulge, channels, sitting hollow), then the seat and back are deformed against each
other in chair space. Welts run along the cushions' own seam vertices, so they sit exactly on
the deformed surface. Leather: Poly Haven `brown_leather` (CC0) scan, recoloured to the
palette's cognac (T_LoungeChair_Leather_*), fetched once into build/polyhaven/.

Units are metres. The chair faces -Y, its origin is the floor centre.
Run inside Blender (see blender/run.py); re-running rebuilds it.
"""
import json
import math
import os
import shutil
import sys
import urllib.request

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import importlib  # noqa: E402

from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(textures)
importlib.reload(materials)

PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))

NAME = "LoungeChair"

P = dict(
    name=NAME,             # collection / object prefix; override to make variants
    leather_name="M_LoungeChair_Leather",
    frame="steel",         # "steel" (polished) or "bronze"
    # frame
    tube_r=0.011,          # tube radius (22 mm stock)
    bend_r=0.06,           # bend radius at frame corners
    half_width=0.38,       # x of the side loops' centre lines
    runner_front=-0.40,    # y where the floor runner starts (front)
    runner_back=0.38,      # y of the rear upright
    front_rake=0.06,       # front upright leans back by this much at arm height
    arm_z=0.62,            # arm tube centre height
    low_rail_z=0.26,       # cross rails supporting the seat platform
    back_rail_z=0.52,      # cross rail the back panel leans on
    # walnut
    board_t=0.025,
    board_half_width=0.36,
    back_tilt_deg=14.0,
    back_panel_h=0.52,
    back_panel_t=0.02,
    arm_cap=(0.07, 0.58, 0.022),
    # leather
    cushion_half_width=0.35,
    seat_cushion_t=0.145,
    seat_overhang=0.02,
    back_cushion_t=0.13,
    back_cushion_h=0.47,
    cushion_edge=0.018,    # radius of the cushions' seam edges (where the welts run)
    piping_r=0.0045,
    # colours (linear)
    leather=(0.15, 0.055, 0.022),   # cognac (mean of the scanned map)
    walnut=(0.105, 0.042, 0.016),
    steel=(0.85, 0.85, 0.86),
    # --- added in the hero pass
    tube_sides=12,         # frame tube profile
    bend_segments=9,       # segments per frame bend
    sled_bend_r=0.085,     # the sweeping front bend of the sled runner
    glide_t=0.003,         # clip-on glides lift the runners off the floor by this much
    seat_rake=0.02,        # front rail sits this much higher: the seat deck tilts back ~1.7 deg
    cushion_corner=0.04,   # plan corner radius of the boxed cushions
    seat_crown=0.028,
    seat_dip=0.014,        # sitting hollow, slightly behind the seat's centre
    seat_bulge=0.010,      # front boxing bulges out at mid height
    back_crown=0.014,
    channels=4,            # horizontal stitched channels on the back cushion
    channel_puff=0.009,
    contact_squash=0.006,  # seat top dips this much where it presses into the back cushion
    crease_x=0.125,        # the seat's two soft thigh creases (x of each)
    crease_depth=0.004,
    leather_scan="brown_leather",   # Poly Haven texture id (CC0)
    leather_tile=0.4,      # metres one leather image covers (the scan is 0.4 m)
    leather_roughness=0.36,
    leather_normal=0.8,
    leather_contrast=1.1,  # mottling of the scan, relative to its own variation
)


# ------------------------------------------------------------------ leather

def _ph_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "game_testing-asset/1.0 (CC0 assets)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def _leather_maps(p):
    """T_LoungeChair_Leather_BaseColor.png (the scan's albedo, its mean colour matched to the
    palette's cognac) and _Normal.jpg. Made once; returns (base, normal) paths or None."""
    base = os.path.join(textures.TEX_DIR, "T_LoungeChair_Leather_BaseColor.png")
    nor = os.path.join(textures.TEX_DIR, "T_LoungeChair_Leather_Normal.jpg")
    ph = p["leather_scan"]
    src = os.path.join(PROJECT, "build", "polyhaven", "textures", ph)
    stamp = os.path.join(src, "T_LoungeChair_Leather.json")     # what the maps were made with
    made_with = json.dumps([ph, list(p["leather"]), p["leather_contrast"]])
    try:
        current = open(stamp).read() == made_with
    except OSError:
        current = not os.path.isdir(src)      # maps without a record (another checkout): keep them
    if os.path.exists(base) and os.path.exists(nor) and current:
        return base, nor
    try:
        os.makedirs(src, exist_ok=True)
        files = json.loads(_ph_get(f"https://api.polyhaven.com/files/{ph}"))
        local = {}
        for key in ("Diffuse", "nor_gl"):
            url = files[key]["1k"]["jpg"]["url"]
            local[key] = os.path.join(src, os.path.basename(url))
            if not os.path.exists(local[key]):
                data = _ph_get(url)
                with open(local[key] + ".tmp", "wb") as f:
                    f.write(data)
                os.replace(local[key] + ".tmp", local[key])
    except Exception as e:  # offline on the first build: flat colour + generated grain
        print(f"lounge_chair: Poly Haven {ph} unavailable ({e})")
        return None
    img = bpy.data.images.load(local["Diffuse"])
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float64).reshape(h, w, 4)[::-1, :, :3]
    bpy.data.images.remove(img)
    lin = np.where(px <= 0.04045, px / 12.92, ((px + 0.055) / 1.055) ** 2.4)
    mean = lin.reshape(-1, 3).mean(axis=0)
    rel = (lin / mean) ** p["leather_contrast"]
    out = rel / rel.reshape(-1, 3).mean(axis=0) * np.array(p["leather"])
    textures._save("T_LoungeChair_Leather_BaseColor", textures._to_srgb(out))
    shutil.copyfile(local["nor_gl"], nor + ".tmp")
    os.replace(nor + ".tmp", nor)
    with open(stamp, "w") as f:
        f.write(made_with)
    return base, nor


def leather_material(p):
    m = common.pbr_material(p["leather_name"], p["leather"], roughness=p["leather_roughness"])
    if not any(n.type == "TEX_IMAGE" for n in m.node_tree.nodes):
        maps = _leather_maps(p)
        if maps:
            common.set_base_color_map(m, textures.load(maps[0]))
            common.set_normal_map(m, textures.load(maps[1], non_color=True), p["leather_normal"])
        else:
            common.set_normal_map(m, textures.load(textures.leather_normal(), non_color=True), 0.6)
    return m


# ------------------------------------------------------------------ upholstered shell

def _bands(rc, re, merge=0.003):
    """Grid lines (distances in from a face) that give the plan corner (radius rc) and the
    seam edge (radius re) 15-degree steps."""
    d = [0.0, re * (1 - math.tan(math.radians(30))), re * (1 - math.tan(math.radians(15))), re,
         rc * (1 - math.tan(math.radians(30))), rc * (1 - math.tan(math.radians(15))), rc]
    out = []
    for v in sorted(d):
        if not out or v - out[-1] > merge:
            out.append(v)
        elif v == rc:
            out[-1] = rc
    return out


def _lines(h, bands, interior):
    """Positions of grid lines along an axis of half-size h: `bands` in from each face, then
    `interior` (a count of even intervals, or a list of absolute positions) between."""
    lo = [-h + d for d in bands]
    hi = [h - d for d in reversed(bands)]
    if isinstance(interior, int):
        a, b = lo[-1], hi[0]
        mid = [a + (b - a) * k / interior for k in range(1, interior)]
    else:
        mid = sorted(v for v in interior if lo[-1] + 1e-4 < v < hi[0] - 1e-4)
    return np.array(lo + mid + hi)


def _round_box(c, h, rc, re_top, re_bot):
    """Map points on the surface of the box [-h, h] onto a rounded box: plan corners of radius
    rc (square-to-quarter-disc), the top / bottom seam edges of radius re_top / re_bot.
    Returns positions and unit normals."""
    hx, hy, hz = h
    sg = np.where(c >= 0, 1.0, -1.0)
    ax, ay, az = np.abs(c[:, 0]), np.abs(c[:, 1]), np.abs(c[:, 2])
    cx, cy = hx - rc, hy - rc
    qx, qy = ax - cx, ay - cy
    corner = (qx > 0) & (qy > 0)
    m = np.maximum(qx, qy)
    k = np.where(corner, m / np.maximum(np.hypot(qx, qy), 1e-12), 1.0)
    ax = np.where(corner, cx + qx * k, ax)
    ay = np.where(corner, cy + qy * k, ay)
    dx, dy = hx - ax, hy - ay
    use_x = dx <= dy
    s = np.where(corner, rc - m, np.where(use_x, dx, dy))
    mm = np.maximum(m, 1e-12)
    nx = np.where(corner, qx * k / mm, np.where(use_x, 1.0, 0.0))
    ny = np.where(corner, qy * k / mm, np.where(use_x, 0.0, 1.0))
    re = np.where(c[:, 2] >= 0, re_top, re_bot)
    a = re - s
    b = az - (hz - re)
    band = (a > 0) & (b > 0)
    m2 = np.maximum(a, b)
    k2 = np.where(band, m2 / np.maximum(np.hypot(a, b), 1e-12), 1.0)
    a2, b2 = a * k2, b * k2
    s2 = np.where(band, re - a2, s)
    az2 = np.where(band, hz - re + b2, az)
    ax = ax - (s2 - s) * nx
    ay = ay - (s2 - s) * ny
    top = (~band) & (a <= 0)
    m2s = np.maximum(m2, 1e-12)
    fn_h = np.where(band, a2 / m2s, np.where(top, 0.0, 1.0))
    fn_z = np.where(band, b2 / m2s, np.where(top, 1.0, 0.0))
    pos = np.stack([sg[:, 0] * ax, sg[:, 1] * ay, sg[:, 2] * az2], axis=1)
    nrm = np.stack([sg[:, 0] * nx * fn_h, sg[:, 1] * ny * fn_h, sg[:, 2] * fn_z], axis=1)
    return pos, nrm


class Shell:
    """A boxed, upholstered volume built on a grid over a cube (the -z face is left open and
    closed with one flat n-gon: it is the side that sits on the deck / leans on the panel).
    Canonical frame: panel face +z, plan axes x and y. Fields: co (cube coords), pos, nrm,
    quads [(vertex ids, face tag)], seam_top / seam_bot (vertex ids around each seam)."""

    def __init__(self, size, lx, ly, lz, rc, re_top, re_bot=None):
        self.h = [s / 2 for s in size]
        self.size = size
        nx, ny, nz = len(lx), len(ly), len(lz)
        ids, co = {}, []

        def v(i, j, k):
            key = (i, j, k)
            if key not in ids:
                ids[key] = len(co)
                co.append((lx[i], ly[j], lz[k]))
            return ids[key]

        quads = []
        K = nz - 1
        for i in range(nx - 1):
            for j in range(ny - 1):
                quads.append(((v(i, j, K), v(i + 1, j, K), v(i + 1, j + 1, K), v(i, j + 1, K)), "+z"))
        for k in range(nz - 1):
            for i in range(nx - 1):
                quads.append(((v(i, 0, k), v(i + 1, 0, k), v(i + 1, 0, k + 1), v(i, 0, k + 1)), "-y"))
                quads.append(((v(i, ny - 1, k), v(i, ny - 1, k + 1), v(i + 1, ny - 1, k + 1), v(i + 1, ny - 1, k)), "+y"))
            for j in range(ny - 1):
                quads.append(((v(0, j, k), v(0, j, k + 1), v(0, j + 1, k + 1), v(0, j + 1, k)), "-x"))
                quads.append(((v(nx - 1, j, k), v(nx - 1, j + 1, k), v(nx - 1, j + 1, k + 1), v(nx - 1, j, k + 1)), "+x"))

        def ring(k):
            r = [v(i, 0, k) for i in range(nx)]
            r += [v(nx - 1, j, k) for j in range(1, ny)]
            r += [v(i, ny - 1, k) for i in range(nx - 2, -1, -1)]
            r += [v(0, j, k) for j in range(ny - 2, 0, -1)]
            return r

        self.seam_top, self.seam_bot = ring(K), ring(0)
        self.quads = quads
        self.co = np.array(co, dtype=np.float64)
        self.pos, self.nrm = _round_box(self.co, self.h, rc, re_top, re_top if re_bot is None else re_bot)
        self.uvw = np.clip(self.co / np.array(self.h), -1, 1)   # normalised cube coords

    def transform(self, M):
        R = np.array(M.to_3x3())
        self.pos = self.pos @ R.T + np.array(M.translation)
        self.nrm = self.nrm @ R.T

    def bmesh(self, tile, seam_start="-y"):
        """UVs: the panel by planar projection of the cube coords, the boxing unwrapped round
        the perimeter (continuous at the corners; its one seam at the corner `seam_start` begins
        with), both at world scale, `tile` metres per UV unit (seams land under the welts)."""
        hx, hy, _ = self.h
        segs = [("-y", 2 * hx, lambda c: c[0] + hx), ("+x", 2 * hy, lambda c: c[1] + hy),
                ("+y", 2 * hx, lambda c: hx - c[0]), ("-x", 2 * hy, lambda c: hy - c[1])]
        s0 = [t for t, _, _ in segs].index(seam_start)
        segs = segs[s0:] + segs[:s0]
        off, acc = {}, 0.0
        for tag, length, fn in segs:
            off[tag] = (acc, fn)
            acc += length
        bm = bmesh.new()
        verts = [bm.verts.new(tuple(p)) for p in self.pos]
        uv = bm.loops.layers.uv.new("UVMap")
        for vids, tag in self.quads:
            f = bm.faces.new([verts[i] for i in vids])
            for lp, i in zip(f.loops, vids):
                c = self.co[i]
                if tag == "+z":
                    lp[uv].uv = (c[0] / tile, c[1] / tile)
                else:
                    o, fn = off[tag]
                    lp[uv].uv = ((o + fn(c)) / tile, c[2] / tile)
        ring = list(reversed(self.seam_bot))
        cap = bm.faces.new([verts[i] for i in ring])
        cap.smooth = False
        for lp, i in zip(cap.loops, ring):
            c = self.co[i]
            lp[uv].uv = (c[0] / tile, c[1] / tile)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        for f in bm.faces:
            if f is not cap:
                f.smooth = True
        return bm


def _undulate(co, nrm, seed, amp, waves=7, lo=0.10, hi=0.26):
    """Low, soft unevenness of a stuffed cover (sum of a few plane waves over the cube coords),
    as offsets along the normal; the open (-z) face is left flat."""
    rng = np.random.default_rng(seed)
    f = np.zeros(len(co))
    for _ in range(waves):
        d = rng.normal(size=3)
        d /= np.linalg.norm(d)
        k = 2 * np.pi / rng.uniform(lo, hi)
        f += np.sin(co @ (d * k) + rng.uniform(0, 2 * np.pi))
    f *= amp / math.sqrt(waves / 2)
    return nrm * (f * (1 - np.clip(-nrm[:, 2], 0, 1)))[:, None]


def _softplus(d, s):
    return s * np.logaddexp(0.0, d / s)


def _smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ tubes

def _fillet(points, radii, segments):
    """Round each corner i of a closed polyline with an arc of radii[i] (segments[i] steps)."""
    pts = [Vector(q) for q in points]
    out = []
    n = len(pts)
    for i in range(n):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        u, w = (a - b).normalized(), (c - b).normalized()
        theta = u.angle(w)
        r = radii[i]
        t = r / math.tan(theta / 2)
        t1, t2 = b + u * t, b + w * t
        centre = b + (u + w).normalized() * (r / math.sin(theta / 2))
        d1, d2 = t1 - centre, t2 - centre
        for k in range(segments[i] + 1):
            out.append(centre + d1.slerp(d2, k / segments[i]).normalized() * r)
    return out


def _sweep(bm, pts, radius, sides, closed, ref, tile=None):
    """Round tube through `pts` (radius: number or per-point list); ring frames from `ref`
    projected off the tangent (no twist for planar paths). Optional world-scale UVs."""
    pts = [Vector(q) for q in pts]
    n = len(pts)
    ref = Vector(ref)
    rings, lengths = [], [0.0]
    for i in range(1, n + (1 if closed else 0)):
        lengths.append(lengths[-1] + (pts[i % n] - pts[i - 1]).length)
    for i, q in enumerate(pts):
        if closed:
            t = pts[(i + 1) % n] - pts[i - 1]
        else:
            t = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        t.normalize()
        u = (ref - ref.dot(t) * t).normalized()
        w = t.cross(u)
        r = radius[i] if isinstance(radius, (list, tuple)) else radius
        rings.append([bm.verts.new(q + r * (math.cos(2 * math.pi * k / sides) * u +
                                            math.sin(2 * math.pi * k / sides) * w)) for k in range(sides)])
    uvl = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap") if tile else None
    rmean = radius if not isinstance(radius, (list, tuple)) else sum(radius) / len(radius)
    faces = []
    for i in range(n - (0 if closed else 1)):
        a, b = rings[i], rings[(i + 1) % n]
        for k in range(sides):
            k2 = (k + 1) % sides
            f = bm.faces.new((a[k], a[k2], b[k2], b[k]))
            f.smooth = True
            faces.append(f)
            if uvl:
                cu = [lengths[i], lengths[i], lengths[i + 1], lengths[i + 1]]
                cv = [k, k + 1, k + 1, k]
                for lp, uu, vv in zip(f.loops, cu, cv):
                    lp[uvl].uv = (uu / tile, vv / sides * 2 * math.pi * rmean / tile)
    return faces


def _simplify(pts, tol, max_len):
    """Greedy chord simplification of a closed polyline: drop points while every skipped
    point stays within `tol` of the chord (and chords stay under max_len)."""
    pts = [np.asarray(q) for q in pts]
    keep = [0]
    i = 0
    n = len(pts)
    while i < n:
        j = i + 2
        while j <= n:
            a, b = pts[i], pts[j % n]
            ab = b - a
            L = np.linalg.norm(ab)
            if L > max_len:
                break
            ok = True
            for k in range(i + 1, j):
                q = pts[k % n] - a
                t = np.clip(np.dot(q, ab) / max(L * L, 1e-12), 0, 1)
                if np.linalg.norm(q - t * ab) > tol:
                    ok = False
                    break
            if not ok:
                break
            j += 1
        i = j - 1
        if i < n:
            keep.append(i)
    return [pts[k] for k in keep]


def _glide(bm, x, y, zc, r, t, length):
    """Clip-on sled glide: a C-shaped nylon shell round the underside of the runner."""
    def profile(grow):
        outer = [math.radians(a) for a in np.linspace(-118, 118, 9)]
        inner = [math.radians(a) for a in np.linspace(118, -118, 5)]
        pts = []
        for a in outer:
            R = r + t * grow
            pts.append((x + R * math.sin(a), max(zc - R * math.cos(a), 0.0)))
        for a in inner:
            pts.append((x + (r + 0.0003) * math.sin(a), zc - (r + 0.0003) * math.cos(a)))
        return pts
    rings = []
    for dy, grow in ((-length / 2, 0.35), (-length / 2 + 0.004, 1.0), (length / 2 - 0.004, 1.0), (length / 2, 0.35)):
        rings.append([bm.verts.new((px, y + dy, pz)) for px, pz in profile(grow)])
    m = len(rings[0])
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(m):
            bm.faces.new((a[k], a[(k + 1) % m], b[(k + 1) % m], b[k]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])


# ------------------------------------------------------------------ build

def build(**overrides):
    p = {**P, **overrides}
    n = p["name"]
    col = common.fresh_collection(n)
    root = common.empty(n, col)

    leather = leather_material(p)
    walnut = materials.walnut()
    steel = materials.bronze() if p["frame"] == "bronze" else materials.steel()
    nylon = materials.black_metal()
    parts = []

    def add(name, bm, mat, smooth=True):
        ob = common.mesh_object(f"{n}_{name}", bm, col, mat, root, smooth=smooth)
        parts.append(ob)
        return ob

    r, gt = p["tube_r"], p["glide_t"]
    rr = r * 0.9
    zr = r + gt                                   # runner centre line
    yf, yb = p["runner_front"], p["runner_back"]
    y_front_top = yf + p["front_rake"]
    hw = p["half_width"]
    tile = p["leather_tile"]

    def front_y_at(z):  # y of the raked front upright's centre line at height z
        return yf + (z - zr) / (p["arm_z"] - zr) * p["front_rake"]

    # --- side loops: sled runner -> rear upright -> arm -> raked front upright
    sides, seg = p["tube_sides"], p["bend_segments"]
    for side, sx in (("L", -1), ("R", 1)):
        x = sx * hw
        corners = [(x, yf, zr), (x, yb, zr), (x, yb, p["arm_z"]), (x, y_front_top, p["arm_z"])]
        radii = [p["sled_bend_r"], p["bend_r"], p["bend_r"], p["bend_r"]]
        bm = bmesh.new()
        segs = [seg, seg - 2, seg - 2, seg - 2]     # the big sled bend gets the most
        _sweep(bm, _fillet(corners, radii, segs), r, sides, True, (1, 0, 0))
        add(f"Frame_{side}", bm, steel)

    # --- cross rails, welded in: each end flares into a ground fillet bead at the upright
    z_fr = p["low_rail_z"] + p["seat_rake"]
    rails = {
        "RailFront": (front_y_at(z_fr), z_fr),
        "RailRear": (yb, p["low_rail_z"]),
        "RailBack": (yb, p["back_rail_z"]),
    }
    flare = [(0.3 * r, 1.04), (r + 0.0012, 1.2), (r + 0.0045, 1.07), (r + 0.010, 1.0)]
    for name, (y, z) in rails.items():
        xs = [-hw + d for d, _ in flare] + [hw - d for d, _ in reversed(flare)]
        rs = [rr * f for _, f in flare] + [rr * f for _, f in reversed(flare)]
        bm = bmesh.new()
        _sweep(bm, [(xx, y, z) for xx in xs], rs, sides, False, (0, 0, 1))
        add(name, bm, steel)

    # --- clip-on glides under the runners
    bm = bmesh.new()
    for sx in (-1, 1):
        for gy in (yf + p["sled_bend_r"] + 0.03, yb - p["bend_r"] - 0.03):
            _glide(bm, sx * hw, gy, zr, r, gt, 0.045)
    add("Glides_NoCollide", bm, nylon, smooth=True)

    # --- seat deck frame S: origin on the rear rail's top, tilted back by the seat rake
    rail_top_rear = p["low_rail_z"] + rr
    run = yb - rails["RailFront"][0]
    rake = math.atan2(p["seat_rake"], run)
    MS = Matrix.Translation((0, yb, rail_top_rear)) @ Matrix.Rotation(-rake, 4, "X")
    bt = p["board_t"]
    s_front = -run / math.cos(rake) - 0.004     # deck front edge, just past the front rail
    s_back = -0.004 / math.cos(rake)

    def board_top_z(y):
        return rail_top_rear + bt / math.cos(rake) + (yb - y) * math.tan(rake)

    bm = common.box_bmesh((2 * p["board_half_width"], s_back - s_front, bt))
    bmesh.ops.transform(bm, verts=bm.verts, matrix=MS @ Matrix.Translation((0, (s_front + s_back) / 2, bt / 2)))
    board = add("SeatBoard", bm, walnut)
    common.add_bevel(board, 0.005)

    # --- back assembly: panel pivots about its rear-bottom edge on the deck so its back face
    #     just touches the back rail
    tilt = math.radians(p["back_tilt_deg"])
    rail_front_y = yb - rr
    pivot_y = rail_front_y
    for _ in range(4):
        pivot_y = rail_front_y - (p["back_rail_z"] - board_top_z(pivot_y)) * math.tan(tilt)
    MB = Matrix.Translation((0, pivot_y, board_top_z(pivot_y))) @ Matrix.Rotation(-tilt, 4, "X")
    pt = p["back_panel_t"]
    bm = common.box_bmesh((2 * p["board_half_width"], pt, p["back_panel_h"]))
    bmesh.ops.transform(bm, verts=bm.verts, matrix=MB @ Matrix.Translation((0, -pt / 2, p["back_panel_h"] / 2)))
    panel = add("BackPanel", bm, walnut)
    common.add_bevel(panel, 0.005)

    # --- back cushion (canonical: x across, y up the back, z out of the front panel)
    cw = 2 * p["cushion_half_width"]
    ct, ch = p["back_cushion_t"], p["back_cushion_h"]
    rc, re = p["cushion_corner"], p["cushion_edge"]
    plan = _bands(rc, re)
    edge = [d for d in plan if d <= re + 1e-9]
    nch = p["channels"]
    hy_b = ch / 2
    grooves = np.linspace(-(hy_b - rc), hy_b - rc, nch + 1)
    ch_lines = list(grooves[1:-1])
    for a, b in zip(grooves[:-1], grooves[1:]):
        ch_lines += [a + 0.009, a + 0.032, b - 0.032, b - 0.009]
    back = Shell((cw, ch, ct), _lines(cw / 2, plan, 12), _lines(hy_b, plan, ch_lines),
                 _lines(ct / 2, edge, 2), rc, re)
    u, v, w = back.uvw.T
    front = np.clip(back.nrm[:, 2], 0, 1) ** 2
    ty = back.co[:, 1]
    t = np.zeros_like(ty)
    groove_d = np.full_like(ty, 1e9)
    for a, b in zip(grooves[:-1], grooves[1:]):
        inside = (ty >= a) & (ty <= b)
        t = np.where(inside, (ty - a) / (b - a), t)
    for g in grooves[1:-1]:
        groove_d = np.minimum(groove_d, np.abs(ty - g))
    in_ch = (ty > grooves[0]) & (ty < grooves[-1])
    ci = np.clip(np.searchsorted(grooves, ty) - 1, 0, nch - 1)       # channel index, bottom up
    fill = np.array([0.72, 1.0, 1.06, 0.94, 1.0, 1.0][:nch])[ci]       # the lowest one is sat against
    wav = 1 + 0.12 * np.sin(2 * np.pi * back.co[:, 0] / 0.33 + 1.7 * ci)
    puff = np.where(in_ch, np.sin(np.pi * t) ** 0.6, 0.0) * fill * wav
    gu = np.clip(1 - np.abs(u) ** 8, 0, 1)
    off = np.zeros_like(back.pos)
    off[:, 2] += front * (p["back_crown"] * ((1 - u ** 2) * (1 - v ** 2)) ** 0.75
                          + p["channel_puff"] * gu * puff
                          - 0.0025 * gu * np.exp(-(groove_d / 0.005) ** 2) * in_ch)
    topw = np.clip(back.nrm[:, 1], 0, 1) ** 2
    off[:, 1] += topw * 0.006 * (1 - u ** 2) * (1 - w ** 2)
    sidew = np.clip(np.abs(back.nrm[:, 0]), 0, 1) ** 2
    off[:, 0] += np.sign(u) * sidew * 0.004 * (1 - v ** 2) * (1 - w ** 2)
    off += _undulate(back.co, back.nrm, 23, 0.001)
    back.pos += off
    back.transform(MB @ Matrix.Translation((0, -pt - ct / 2, ch / 2 + 0.004)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    # the plane the two cushions press together on: the back cushion's front, uncrowned
    nB = np.array(MB.to_3x3() @ Vector((0, -1, 0)))
    pB = np.array(MB @ Vector((0, -pt - ct, 0)))

    # --- seat cushion: from the front overhang back past the back cushion's face (then
    #     pressed flat against it)
    st = p["seat_cushion_t"]
    z0, z1 = bt, bt + st

    def plane_y(zs):   # S-frame y where the plane meets the S-frame height zs
        a = np.array(MS @ Vector((0, 0, zs)))
        dy = np.array(MS.to_3x3() @ Vector((0, 1, 0)))
        return -np.dot(a - pB, nB) / np.dot(dy, nB)

    sy0 = s_front - p["seat_overhang"]
    sy1 = max(plane_y(z0), plane_y(z1)) + 0.015
    sd = sy1 - sy0
    # two long soft creases where the thighs press (grid lines placed on them and their
    # shoulders so they stay crisp), and a soft fold across the front boxing
    creases = [-p["crease_x"], p["crease_x"]]
    even = _lines(cw / 2, plan, 12)
    xs = [c + o for c in creases for o in (-0.014, 0.0, 0.014)]
    xs += [x for x in even if all(abs(x - c) > 0.024 for c in creases)]
    fold_z = 0.028
    seat = Shell((cw, sd, st), _lines(cw / 2, plan, xs), _lines(sd / 2, plan, 10),
                 _lines(st / 2, edge, [0.0, fold_z]), rc, re)
    u, v, w = seat.uvw.T
    top = np.clip(seat.nrm[:, 2], 0, 1) ** 2
    x0 = seat.co[:, 0]
    env = _smoothstep(-1.08, -0.7, v) * (1 - _smoothstep(-0.1, 0.55, v))
    crease = sum(k * np.exp(-((x0 - c) / 0.008) ** 2) for k, c in zip((1.0, 0.8), creases))
    off = np.zeros_like(seat.pos)
    # the creases (and the grid lines carrying them) splay outward toward the front edge
    for c in creases:
        near = np.exp(-((x0 - c) / 0.03) ** 2) * top
        off[:, 0] += np.sign(c) * near * 0.035 * ((1 - v) / 2) ** 2
    off[:, 2] += top * (p["seat_crown"] * ((1 - u ** 2) * (1 - v ** 2)) ** 0.75
                        - p["seat_dip"] * np.exp(-(u / 0.55) ** 2 - ((v - 0.08) / 0.55) ** 2)
                        - p["crease_depth"] * crease * env)
    frontw = np.clip(-seat.nrm[:, 1], 0, 1) ** 2
    off[:, 1] -= frontw * p["seat_bulge"] * (1 - u ** 2) * (1 - w ** 2)
    off[:, 1] += (frontw * 0.0035 * np.exp(-((seat.co[:, 2] - fold_z) / 0.013) ** 2) * (1 - u ** 2) ** 2
                  * (0.75 + 0.25 * np.sin(2 * np.pi * x0 / 0.29 + 0.6)))
    off += _undulate(seat.co, seat.nrm, 11, 0.0012)
    sidew = np.clip(np.abs(seat.nrm[:, 0]), 0, 1) ** 2
    off[:, 0] += np.sign(u) * sidew * 0.006 * (1 - v ** 2) * (1 - w ** 2)
    seat.pos += off
    seat.transform(MS @ Matrix.Translation((0, (sy0 + sy1) / 2, (z0 + z1) / 2)))

    # --- where they meet: the seat's rear rolls flat against the back cushion and its top
    #     dips into it; the back cushion's lower front is pushed back behind the seat
    d = (seat.pos - pB) @ nB
    dn = _softplus(d, 0.003)
    seat.pos[:, 1] -= (dn - d) / math.cos(tilt)      # pushed horizontally, so it stays on the deck
    topw = np.clip(seat.nrm[:, 2], 0, 1)
    seat.pos[:, 2] -= p["contact_squash"] * topw * np.exp(-np.maximum(dn, 0) / 0.03)
    near = (seat.pos - pB) @ nB < 0.02
    z_seat = seat.pos[near, 2].max()
    d = (back.pos - pB) @ nB
    wgt = 1 - _smoothstep(z_seat - 0.015, z_seat + 0.03, back.pos[:, 2])
    dn = -_softplus(-d, 0.003)
    back.pos += np.outer(wgt * (dn - d), nB)

    leather_parts = []
    seat_ob = add("SeatCushion", seat.bmesh(tile, seam_start="-x"), leather)
    back_ob = add("BackCushion", back.bmesh(tile, seam_start="-y"), leather)

    # --- welts along each cushion's two seams, on the deformed surface
    def welts(shell, ob, name, ref):
        me = ob.data
        nrm = np.array([vv.normal[:] for vv in me.vertices])
        for i, ring in enumerate((shell.seam_top, shell.seam_bot)):
            pts = [shell.pos[vid] + nrm[vid] * p["piping_r"] * 0.35 for vid in ring]
            pts = [Vector(q) for q in _simplify(pts, 0.0006, 0.16)]
            bm = bmesh.new()
            _sweep(bm, pts, p["piping_r"], 5, True, ref, tile=tile)
            add(f"{name}_Piping{i}", bm, leather)

    welts(seat, seat_ob, "SeatCushion", tuple(MS.to_3x3() @ Vector((0, 0, 1))))
    welts(back, back_ob, "BackCushion", tuple(MB.to_3x3() @ Vector((0, -1, 0))))

    # --- walnut arm pads: rounded plan, eased top edge, slightly crowned; the arm tube runs
    #     in a routed channel underneath (sunk ~2/3 of its radius into the pad)
    cx, cy, cz = p["arm_cap"]
    arm_mid = (y_front_top + p["bend_r"] + yb - p["bend_r"]) / 2
    prc, pre = 0.028, 0.007
    pplan = [0.0, 0.004, 0.009, 0.017, prc]
    for side, sx in (("L", -1), ("R", 1)):
        pad = Shell((cx, cy, cz), _lines(cx / 2, pplan, 1), _lines(cy / 2, pplan, 3),
                    np.array([-cz / 2, -cz / 2 + 0.002, cz / 2 - pre, cz / 2 - 0.0035, cz / 2]), prc, pre, 0.002)
        uu, vv, _ = pad.uvw.T
        pad.pos[:, 2] += np.clip(pad.nrm[:, 2], 0, 1) * 0.0018 * (1 - uu ** 2) * (1 - vv ** 4)
        pad.transform(Matrix.Translation((sx * hw, arm_mid, p["arm_z"] + r * 0.35 + cz / 2)))
        add(f"ArmCap_{side}", pad.bmesh(0.5), walnut)

    for ob in parts:
        if ob.data.materials and ob.data.materials[0] == walnut:
            common.box_uv(ob, tile=0.5)
    return root, parts


if __name__ == "__main__":
    root, parts = build()
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
