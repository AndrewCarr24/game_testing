"""Set-dressing kit for the decor_b_* assets (not an asset itself): the small things a stylist
puts on surfaces (art books, ceramics in families, trays, carafes and glasses, candles,
fruit, bread, herbs, plants, sculpture, magazines, cups, keys) as functions that add
geometry to an accumulator, so a vignette asset comes out as ONE mesh per material.

Every part is named ..._NoCollide (small things never become colliders; the furniture under
them is the collider). Materials are the house's existing ones, created with exactly the
same values as their owners (the engine folds identical materials across assets into one
draw call per room), plus three of our own: M_Decor_Paper, M_Decor_Cloth_Rust and
M_Decor_Cloth_Ink (book pages and covers, magazines).

Conventions: metres; z = 0 is the surface the object stands on; front faces -Y.
"""
import importlib
import math
import os
import random
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(materials)


# ------------------------------------------------------------------ materials

def _pbr(name, c, r, metallic=0.0, coat=0.0):
    return lambda: common.pbr_material(name, c, roughness=r, metallic=metallic, coat=coat)


def _leather():
    m = common.pbr_material("M_Leather_Cognac", (0.23, 0.075, 0.025), roughness=0.62)
    common.set_normal_map(m, textures.load(textures.leather_normal(), non_color=True), 0.6)
    return m


def _garage(fn):
    def f():
        import garage_cabinets as gk
        return getattr(gk, fn)()
    return f


MATS = {
    # woods and metals
    "walnut": materials.walnut,
    "oak_smoked": materials.smoked_oak,
    "oak_light": _garage("oak_light"),                       # M_Mudroom_Oak
    "bronze": materials.bronze,
    "steel": materials.steel,
    "black_metal": materials.black_metal,
    "copper": _pbr("M_Copper", (0.62, 0.30, 0.17), 0.3, metallic=1.0),
    # stone and ceramics
    "marble": _pbr("M_Marble_White", (0.8, 0.79, 0.77), 0.3),
    "ceramic_white": _pbr("M_Ceramic_White", (0.78, 0.76, 0.72), 0.22),
    "ceramic_charcoal": _pbr("M_Ceramic_Charcoal", (0.05, 0.05, 0.055), 0.3),
    "ceramic_oat": _pbr("M_Ceramic_Oat", (0.55, 0.50, 0.40), 0.35),
    "terracotta": _pbr("M_Mudroom_Pot", (0.30, 0.13, 0.07), 0.7),
    "planter": _pbr("M_Library_Planter", (0.46, 0.42, 0.35), 0.85),
    # paper, wax, textiles
    "candle": _pbr("M_Candle_Cream", (0.78, 0.72, 0.58), 0.55),
    "paper_white": _pbr("M_Picture_Mat", (0.88, 0.87, 0.83), 0.92),
    "label": _pbr("M_Label_Cream", (0.62, 0.56, 0.42), 0.8),
    "linen_oat": lambda: materials.fabric("M_Fabric_Oat", (0.42, 0.37, 0.30)),
    "linen_stone": lambda: materials.fabric("M_Fabric_Stone", (0.16, 0.15, 0.14)),
    "linen_sage": lambda: materials.fabric("M_Fabric_Sage", (0.16, 0.22, 0.16)),
    "linen_clay": lambda: materials.fabric("M_Fabric_Clay", (0.30, 0.12, 0.07)),
    "wool_charcoal": _pbr("M_Wool_Charcoal", (0.06, 0.06, 0.065), 0.95),
    "wool_oat": _pbr("M_Wool_Oat", (0.45, 0.40, 0.32), 1.0),
    "wool_greige": _pbr("M_Wool_Greige_Dining", (0.2, 0.18, 0.15), 1.0),
    "leather": _leather,
    "wicker": _pbr("M_Wicker", (0.30, 0.21, 0.12), 0.95),
    # glass (alpha-blended: each glass mesh is its own draw call, so keep them few)
    "glass_smoke": lambda: materials.glass("M_Glass_Smoke", tint=(0.42, 0.40, 0.37), alpha=0.35, roughness=0.04),
    "glass_crystal": lambda: materials.glass("M_Glass_Crystal", tint=(0.9, 0.93, 0.95), alpha=0.22, roughness=0.02),
    "glass_jar": lambda: materials.glass("M_Glass_Jar", (0.9, 0.95, 0.92), 0.25),
    "glass_olive": lambda: materials.glass("M_Glass_Olive", (0.2, 0.28, 0.1), 0.55),
    "bottle_green": _pbr("M_Bottle_Green", (0.022, 0.060, 0.028), 0.15),
    "bottle_black": _pbr("M_Bottle_Black", (0.020, 0.018, 0.022), 0.15),
    # food and plants
    "lemon": _pbr("M_Lemon", (0.75, 0.55, 0.03), 0.5),
    "lime": _pbr("M_Lime", (0.12, 0.30, 0.03), 0.5),
    "quince": _pbr("M_Quince", (0.50, 0.40, 0.05), 0.5),
    "wine": _pbr("M_Wine_Red", (0.12, 0.006, 0.012), 0.08),
    "crust": _pbr("M_Grain_Dark", (0.28, 0.2, 0.12), 0.9),
    "flour": _pbr("M_Grain_Flour", (0.55, 0.45, 0.28), 0.9),
    "coffee": _pbr("M_Coffee_Beans", (0.05, 0.03, 0.02), 0.5),
    "leaf": _pbr("M_Mudroom_Leaf", (0.04, 0.12, 0.035), 0.6),
    "soil": _pbr("M_Plant_Soil", (0.025, 0.016, 0.010), 1.0),
    "bark": _pbr("M_Plant_Bark", (0.10, 0.07, 0.045), 0.8),
    # garage palette
    "graphite": _garage("graphite"),
    "graphite_dark": _garage("graphite_dark"),
    "aluminium": _garage("aluminium"),
    "accent": _pbr("M_Garage_Accent", (0.55, 0.07, 0.025), 0.5),
    "white_lacquer": _garage("white_lacquer"),
    "garage_leather": _pbr("M_Garage_Leather", (0.30, 0.17, 0.09), 0.55),
    # ours (shared by every decor_b_ asset)
    "paper": _pbr("M_Decor_Paper", (0.64, 0.60, 0.50), 0.85),
    "cloth_rust": _pbr("M_Decor_Cloth_Rust", (0.30, 0.10, 0.045), 0.85),
    "cloth_ink": _pbr("M_Decor_Cloth_Ink", (0.022, 0.03, 0.055), 0.8),
}

# UV tile (metres per repeat) for the textured materials; flat colours don't care
TILES = {"walnut": 0.5, "oak_smoked": 0.5, "oak_light": 0.5, "linen_oat": 0.25, "linen_stone": 0.25,
         "linen_sage": 0.25, "linen_clay": 0.25, "leather": 0.2}


def mat(key):
    m = MATS[key]()
    if key == "leaf":
        m.use_backface_culling = False
    return m


# ----------------------------------------------------------------- accumulator

class Acc:
    """One bmesh (with a UV layer) per material key; finish() turns each into one mesh."""

    def __init__(self):
        self.parts = {}

    def _get(self, key):
        if key not in self.parts:
            bm = bmesh.new()
            self.parts[key] = (bm, bm.loops.layers.uv.new("UVMap"))
        return self.parts[key]

    def emit(self, key, src, M, smooth=True, sharp=40.0):
        """Copy temp bmesh `src` into the key's mesh, transformed by M (frees src)."""
        bm, uv = self._get(key)
        vmap = {v: bm.verts.new(M @ v.co) for v in src.verts}
        new = []
        for f in src.faces:
            try:
                nf = bm.faces.new([vmap[v] for v in f.verts])
            except ValueError:
                continue
            nf.smooth = smooth
            new.append(nf)
        src.free()
        tile = TILES.get(key, 0.5)
        for f in new:
            f.normal_update()
            n = [abs(c) for c in f.normal]
            na = n.index(max(n))
            a, b = [i for i in range(3) if i != na]
            for lp in f.loops:
                co = lp.vert.co
                lp[uv].uv = (co[a] / tile, co[b] / tile)
        if smooth and sharp is not None:
            lim = math.radians(sharp)
            for e in {e for f in new for e in f.edges}:
                if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim:
                    e.smooth = False
        return new

    def finish(self, name, col, root, collide=()):
        """collide: keys whose mesh may be a collider (a floor plant's pot); the rest are
        named _NoCollide."""
        parts = []
        for key, (bm, _) in self.parts.items():
            if not bm.faces:
                bm.free()
                continue
            tag = "" if key in collide else "_NoCollide"
            ob = common.mesh_object(f"{name}_{key.title().replace('_', '')}{tag}", bm, col, mat(key), root,
                                    smooth=False)
            parts.append(ob)
        self.parts = {}
        return parts


def T(x=0.0, y=0.0, z=0.0, rz=0.0, rx=0.0, ry=0.0, s=1.0):
    """Placement matrix: translate, then rotations about z (deg), x, y, then uniform scale."""
    return (Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(rz), 4, "Z") @
            Matrix.Rotation(math.radians(rx), 4, "X") @ Matrix.Rotation(math.radians(ry), 4, "Y") @
            Matrix.Scale(s, 4))


# ------------------------------------------------------------------ primitives

def box_bm(sx, sy, sz, z0=True, bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector((sx, sy, sz)), verts=bm.verts)
    if z0:
        bmesh.ops.translate(bm, vec=Vector((0, 0, sz / 2)), verts=bm.verts)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=1, affect="EDGES", profile=0.5)
    return bm


def box(acc, key, M, sx, sy, sz, bevel=0.0):
    """Box standing on z = 0 of frame M (flat shaded)."""
    acc.emit(key, box_bm(sx, sy, sz, True, bevel), M, smooth=False)


def lathe_bm(profile, segs, start=0.0):
    """Spin [(r, z), ...] around Z (profile travelling up the outside, then down the inside
    gives outward / inward normals). r ~ 0 makes a pole."""
    bm = bmesh.new()
    rows = []
    for r, z in profile:
        if r < 1e-6:
            rows.append([bm.verts.new((0, 0, z))] * segs)
        else:
            rows.append([bm.verts.new((r * math.cos(start + 2 * math.pi * k / segs),
                                       r * math.sin(start + 2 * math.pi * k / segs), z)) for k in range(segs)])
    for a, b in zip(rows[:-1], rows[1:]):
        for k in range(segs):
            j = (k + 1) % segs
            q = []
            for v in (a[k], a[j], b[j], b[k]):
                if v not in q:
                    q.append(v)
            if len(q) >= 3:
                try:
                    bm.faces.new(q)
                except ValueError:
                    pass
    return bm


def lathe(acc, key, M, profile, segs=16, sharp=40.0):
    acc.emit(key, lathe_bm(profile, segs), M, smooth=True, sharp=sharp)


def sphere(acc, key, M, r, u=10, v=7, scale=(1, 1, 1)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=r)
    bmesh.ops.scale(bm, vec=Vector(scale), verts=bm.verts)
    acc.emit(key, bm, M, smooth=True, sharp=None)


def tube(acc, key, M, pts, radius, sides=5, cap=True):
    """Polygonal tube along pts (radius: float or one per point), parallel-transported frame."""
    pts = [Vector(p) for p in pts]
    rad = radius if isinstance(radius, (list, tuple)) else [radius] * len(pts)
    bm = bmesh.new()
    t0 = (pts[1] - pts[0]).normalized()
    ref = Vector((0, 0, 1)) if abs(t0.z) < 0.9 else Vector((1, 0, 0))
    nrm = t0.cross(ref).normalized()
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        nrm = (nrm - t * nrm.dot(t)).normalized()
        bi = t.cross(nrm)
        rings.append([bm.verts.new(p + rad[i] * (math.cos(2 * math.pi * k / sides) * nrm +
                                                 math.sin(2 * math.pi * k / sides) * bi)) for k in range(sides)])
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((a[k], a[j], b[j], b[k]))
    if cap:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    acc.emit(key, bm, M, smooth=True, sharp=60.0)


def torus(acc, key, M, R, r, u=16, v=6):
    bm = bmesh.new()
    rows = []
    for i in range(u):
        a = 2 * math.pi * i / u
        c = Vector((math.cos(a), math.sin(a), 0))
        rows.append([bm.verts.new(c * (R + r * math.cos(2 * math.pi * k / v)) +
                                  Vector((0, 0, r * math.sin(2 * math.pi * k / v)))) for k in range(v)])
    for i in range(u):
        a, b = rows[i], rows[(i + 1) % u]
        for k in range(v):
            j = (k + 1) % v
            bm.faces.new((a[k], b[k], b[j], a[j]))
    acc.emit(key, bm, M, smooth=True, sharp=None)


def rrect(L, W, r, k=3):
    """Rounded-rectangle contour (counter-clockwise), centred."""
    r = min(r, L / 2 - 1e-4, W / 2 - 1e-4)
    pts = []
    for cx, cy, a0 in ((L / 2 - r, W / 2 - r, 0), (-L / 2 + r, W / 2 - r, 90), (-L / 2 + r, -W / 2 + r, 180),
                       (L / 2 - r, -W / 2 + r, 270)):
        for i in range(k + 1):
            a = math.radians(a0 + 90 * i / k)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def slab(acc, key, M, L, W, t, r=0.02, k=3, sharp=50.0):
    """Rounded-corner slab on z = 0 (boards, trays' floors, cheese, books' covers...)."""
    c = rrect(L, W, r, k)
    bm = bmesh.new()
    lo = [bm.verts.new((x, y, 0)) for x, y in c]
    hi = [bm.verts.new((x, y, t)) for x, y in c]
    bm.faces.new(list(reversed(lo)))
    bm.faces.new(hi)
    n = len(c)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    acc.emit(key, bm, M, smooth=True, sharp=sharp)


def tray(acc, key, M, L, W, h=0.035, rim=0.008, floor=0.006, r=0.03, k=3):
    """Shallow tray with a rounded-rectangle rim."""
    co, ci = rrect(L, W, r, k), rrect(L - 2 * rim, W - 2 * rim, max(r - rim, 0.004), k)
    bm = bmesh.new()
    n = len(co)
    b0 = [bm.verts.new((x, y, 0)) for x, y in co]
    o1 = [bm.verts.new((x, y, h)) for x, y in co]
    i1 = [bm.verts.new((x, y, h)) for x, y in ci]
    i0 = [bm.verts.new((x, y, floor)) for x, y in ci]
    bm.faces.new(list(reversed(b0)))
    bm.faces.new(i0)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((b0[i], b0[j], o1[j], o1[i]))
        bm.faces.new((o1[i], o1[j], i1[j], i1[i]))
        bm.faces.new((i1[i], i1[j], i0[j], i0[i]))
    acc.emit(key, bm, M, smooth=True, sharp=50.0)


# ------------------------------------------------------------------ profiles

def _catmull(pts, per=4):
    pts = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for s in range(per):
            t = s / per
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t +
                                    (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in (0, 1)))
    out.append(pts[-2])
    return out


VESSELS = {
    # (r, z) on a unit height and unit max radius: foot -> lip (outside)
    "ovoid": [(0.62, 0.0), (0.86, 0.12), (1.0, 0.42), (0.88, 0.74), (0.55, 0.92), (0.46, 1.0)],
    "bottle": [(0.70, 0.0), (0.95, 0.08), (1.0, 0.38), (0.80, 0.58), (0.32, 0.72), (0.24, 0.92), (0.30, 1.0)],
    "cylinder": [(0.94, 0.0), (1.0, 0.03), (1.0, 0.97)],
    "bud": [(0.75, 0.0), (1.0, 0.25), (0.85, 0.55), (0.30, 0.78), (0.26, 0.94), (0.34, 1.0)],
    "urn": [(0.45, 0.0), (0.55, 0.05), (0.92, 0.35), (1.0, 0.55), (0.80, 0.85), (0.70, 0.95), (0.74, 1.0)],
    "flask": [(0.80, 0.0), (1.0, 0.18), (1.0, 0.50), (0.55, 0.70), (0.20, 0.80), (0.18, 0.97), (0.22, 1.0)],
    "beaker": [(0.78, 0.0), (0.85, 0.05), (0.95, 0.6), (1.0, 1.0)],
    "bowl": [(0.42, 0.0), (0.50, 0.04), (0.78, 0.30), (0.95, 0.70), (1.0, 1.0)],
    "dish": [(0.55, 0.0), (0.62, 0.10), (0.92, 0.55), (1.0, 1.0)],
    "pot": [(0.72, 0.0), (0.80, 0.06), (0.92, 0.82), (1.0, 0.86), (1.0, 1.0)],
}


def vessel(acc, key, M, kind, h, r, segs=14, wall=0.005, depth=None, smooth_per=None, fill=None):
    """A lathed open vessel with real wall thickness: outside up, rounded lip, inside down
    to `depth` below the lip (default: the whole way for open shapes, a little for narrow
    necks), closed with a floor. fill = (key, level 0..1) puts a flat surface inside (water,
    soil, coffee). Returns the inner floor height."""
    prof = [(rr * r, zz * h) for rr, zz in VESSELS[kind]]
    if smooth_per is None:
        smooth_per = 2 if h >= 0.2 else 1
    dense = _catmull(prof, smooth_per) if smooth_per > 1 else prof
    dense = [(rr, max(zz, 0.0)) for rr, zz in dense]
    out = [(0.0, 0.0)] + dense
    lip_r, lip_z = dense[-1]
    t = min(wall, lip_r * 0.4)
    # rounded lip: two points over the top
    out += [(lip_r - t * 0.25, lip_z + t * 0.45), (lip_r - t * 0.75, lip_z + t * 0.45)]
    narrow = lip_r < 0.45 * r
    d = depth if depth is not None else (min(h * 0.18, 0.04) if narrow else h - max(0.006, h * 0.06))
    zf = lip_z - d
    inner = []
    for i, (rr, zz) in enumerate(reversed(dense)):
        if zz < zf:
            break
        if i % 2 == 0:
            inner.append((max(rr - t, 0.001), zz))
    # inner wall at the floor level: interpolate the radius
    rf = max(_radius_at(dense, zf) - t, 0.001)
    inner.append((rf, zf))
    inner.append((0.0, zf))
    lathe(acc, key, M, out + inner, segs)
    if fill:
        fk, lvl = fill
        zl = zf + (lip_z - zf) * lvl
        rl = max(_radius_at(dense, zl) - t - 0.0005, 0.001)
        lathe(acc, fk, M, [(0.0, zl), (rl, zl)], segs)
    return zf


def _radius_at(dense, z):
    for (r0, z0), (r1, z1) in zip(dense[:-1], dense[1:]):
        if z0 <= z <= z1 and z1 > z0:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return dense[-1][0] if z > dense[-1][1] else dense[0][0]


# ------------------------------------------------------------------ objects

def book(acc, M, L, W, T_, cover, pages="paper", spine_band=None):
    """Hardback lying flat: L along x (head to tail), W along y (spine on -y), thickness T_
    on z = 0. Two boards proud of the page block by 3 mm, a spine, an optional band
    (a printed title strip) across the spine."""
    c = min(0.0028, T_ * 0.18)
    o = 0.0028
    box(acc, cover, M, L, W, c)
    box(acc, cover, M @ T(z=T_ - c), L, W, c)
    box(acc, cover, M @ T(y=-W / 2 + c * 0.6), L, c * 1.2, T_)
    pw = W - o - c * 1.2
    box(acc, pages, M @ T(y=-W / 2 + c * 1.2 + pw / 2, z=c), L - 2 * o, pw, T_ - 2 * c)
    if spine_band:
        bk, frac = spine_band
        box(acc, bk, M @ T(x=L * (frac - 0.5), y=-W / 2 - 0.0004, z=T_ * 0.2), L * 0.18, 0.0012, T_ * 0.6)


def book_stack(acc, M, rnd, n, covers, size=(0.30, 0.24), thick=(0.018, 0.04), pages="paper", bands=None,
               shrink=0.06, jitter=4.0):
    """n books lying flat, largest at the bottom, each turned a little. Returns (top z, top L, top W)."""
    z = 0.0
    L, W = size
    order = list(covers)
    rnd.shuffle(order)
    for i in range(n):
        f = 1.0 - shrink * i * rnd.uniform(0.6, 1.4)
        l, w = L * f * rnd.uniform(0.94, 1.0), W * f * rnd.uniform(0.92, 1.0)
        t = rnd.uniform(*thick)
        band = (bands[i % len(bands)], rnd.uniform(0.3, 0.7)) if bands and rnd.random() < 0.6 else None
        book(acc, M @ T(rnd.uniform(-0.008, 0.008), rnd.uniform(-0.006, 0.006), z, rz=rnd.uniform(-jitter, jitter)),
             l, w, t, order[i % len(order)], pages, band)
        z += t
        top = (l, w)
    return z, top[0], top[1]


def magazine(acc, M, cover, pages="paper", size=(0.285, 0.225), t=0.007):
    box(acc, cover, M, size[0], size[1], 0.0008)
    box(acc, pages, M @ T(x=0.001, z=0.0008), size[0] - 0.003, size[1] - 0.002, t - 0.0016)
    box(acc, cover, M @ T(z=t - 0.0008), size[0], size[1], 0.0008)


def open_book(acc, M, cover, pages="paper", L=0.24, W=0.17, t=0.034):
    """A book lying open, pages fanning up from the gutter (along x at y = 0)."""
    box(acc, cover, M @ T(y=-W / 2 - 0.004), L + 0.012, W + 0.008, 0.003)
    box(acc, cover, M @ T(y=W / 2 + 0.004), L + 0.012, W + 0.008, 0.003)
    for side in (-1, 1):
        bm = bmesh.new()
        # page block: a curved surface rising from the cover edge to the gutter
        nx, ny = 2, 5
        top = []
        for j in range(ny + 1):
            s = j / ny
            yy = side * W * (1 - s)
            zz = 0.003 + t * 0.5 * (0.35 + 0.65 * math.sin(math.pi / 2 * s) ** 0.6) - 0.004 * s * s
            top.append([bm.verts.new((-L / 2 + L * i / nx, yy, zz)) for i in range(nx + 1)])
        bot = [[bm.verts.new((v.co.x, v.co.y, 0.003)) for v in row] for row in (top[0], top[-1])]
        for j in range(ny):
            for i in range(nx):
                q = (top[j][i], top[j][i + 1], top[j + 1][i + 1], top[j + 1][i])
                bm.faces.new(q if side > 0 else tuple(reversed(q)))
        # head and tail edges of the block
        for i in (0, nx):
            col_ = [top[j][i] for j in range(ny + 1)]
            base = [bm.verts.new((v.co.x, v.co.y, 0.003)) for v in col_]
            for j in range(ny):
                q = (col_[j], col_[j + 1], base[j + 1], base[j])
                bm.faces.new(q if (i == 0) == (side > 0) else tuple(reversed(q)))
        # fore-edge
        q = (top[0][0], top[0][nx], bot[0][nx], bot[0][0])
        bm.faces.new(q if side < 0 else tuple(reversed(q)))
        acc.emit(pages, bm, M, smooth=True, sharp=50.0)


def candle(acc, M, h=0.12, r=0.022, holder="bronze", wax="candle", style="stick"):
    """A candle in a holder: 'stick' (turned candlestick), 'cup' (low bowl holder), 'pillar' (none)."""
    z = 0.0
    if style == "stick":
        hh = 0.10
        lathe(acc, holder, M, [(0.0, 0.0), (0.038, 0.0), (0.038, 0.005), (0.014, 0.012), (0.009, 0.03), (0.009, hh - 0.03),
                               (0.016, hh - 0.018), (r + 0.004, hh - 0.006), (r + 0.004, hh), (0.0, hh - 0.006)], 14)
        z = hh - 0.008
    elif style == "cup":
        lathe(acc, holder, M, [(0.0, 0.0), (r + 0.012, 0.0), (r + 0.016, 0.02), (r + 0.012, 0.03), (r + 0.002, 0.03),
                               (r + 0.002, 0.008), (0.0, 0.008)], 14)
        z = 0.008
    top = z + h
    lathe(acc, wax, M, [(0.0, z), (r, z), (r, top - 0.003), (r - 0.003, top), (0.006, top - 0.004), (0.0, top - 0.005)], 12)
    tube(acc, "black_metal", M, [(0, 0, top - 0.005), (0.0005, 0, top + 0.009)], 0.0012, sides=3)
    return top


def carafe(acc, M, key="glass_crystal", h=0.24, r=0.055, liquid=None):
    """Lathed glass carafe with a narrow neck and a rounded lip (inner wall to the floor)."""
    prof = [(0.0, 0.0), (r * 0.82, 0.0), (r * 0.96, 0.012), (r, h * 0.28), (r * 0.94, h * 0.5), (r * 0.62, h * 0.70),
            (r * 0.42, h * 0.84), (r * 0.40, h * 0.96), (r * 0.47, h)]
    w = 0.003
    inner = [(r * 0.47 - w, h - 0.001), (r * 0.40 - w, h * 0.96), (r * 0.42 - w, h * 0.84), (r * 0.62 - w, h * 0.70),
             (r * 0.94 - w, h * 0.5), (r - w, h * 0.28), (r * 0.96 - w, 0.014), (0.0, 0.010)]
    lathe(acc, key, M, prof + inner, 16)
    if liquid:
        lk, zl = liquid
        rl = r - w - 0.001 if zl <= h * 0.5 else r * 0.6
        lathe(acc, lk, M, [(0.0, 0.011), (r * 0.94 - w, 0.014), (rl, h * zl), (0.0, h * zl)], 14)


def tumbler(acc, M, key="glass_crystal", h=0.09, r=0.036, base=0.012):
    lathe(acc, key, M, [(0.0, 0.0), (r * 0.92, 0.0), (r, 0.006), (r, h), (r - 0.0025, h), (r - 0.0025, base),
                        (0.0, base)], 14)


def wine_glass(acc, M, key="glass_crystal", h=0.21, r=0.042, wine=None):
    bowl_z = h * 0.48
    lathe(acc, key, M, [(0.0, 0.0), (0.036, 0.0), (0.034, 0.003), (0.005, 0.008), (0.0035, bowl_z - 0.01),
                        (0.012, bowl_z + 0.004), (r, bowl_z + h * 0.18), (r * 0.94, h * 0.86), (r * 0.80, h),
                        (r * 0.80 - 0.0015, h - 0.001), (r * 0.94 - 0.0015, h * 0.86), (r - 0.0015, bowl_z + h * 0.18),
                        (0.0, bowl_z + 0.006)], 14)
    if wine:
        zl = bowl_z + h * 0.12
        lathe(acc, wine, M, [(0.0, bowl_z + 0.007), (r * 0.82, zl - 0.004), (r * 0.86, zl), (0.0, zl)], 12)


def cup_saucer(acc, M, key="ceramic_white", coffee="coffee", saucer=True):
    z = 0.0
    if saucer:
        lathe(acc, key, M, [(0.0, 0.0), (0.04, 0.0), (0.045, 0.004), (0.07, 0.01), (0.072, 0.014), (0.068, 0.013),
                            (0.045, 0.009), (0.0, 0.008)], 18)
        z = 0.008
    h = 0.062
    lathe(acc, key, M, [(0.0, z), (0.024, z), (0.027, z + 0.004), (0.038, z + 0.03), (0.042, z + h), (0.039, z + h),
                        (0.035, z + 0.03), (0.022, z + 0.008), (0.0, z + 0.007)], 16)
    if coffee:
        lathe(acc, coffee, M, [(0.0, z + h - 0.012), (0.039, z + h - 0.012)], 14)
    pts = [(0.040, 0, z + 0.048), (0.058, 0, z + 0.046), (0.060, 0, z + 0.03), (0.050, 0, z + 0.018), (0.036, 0, z + 0.016)]
    tube(acc, key, M, pts, 0.0035, sides=5, cap=False)


def plate(acc, M, key="ceramic_white", r=0.13, segs=20):
    lathe(acc, key, M, [(0.0, 0.0), (r * 0.55, 0.0), (r * 0.58, 0.004), (r * 0.62, 0.008), (r, 0.018), (r - 0.003, 0.02),
                        (r * 0.64, 0.011), (0.0, 0.010)], segs)


def lemons(acc, M, rnd, key, pts, r=0.032):
    """Lemon-ish fruit (ellipsoid with tips) at pts [(x, y, z)], lying on their side."""
    for x, y, z in pts:
        Mf = M @ T(x, y, z + r * 0.9, rz=rnd.uniform(0, 180), ry=90 + rnd.uniform(-20, 20))
        lathe(acc, key, Mf, [(0.0, -r * 1.35), (r * 0.3, -r * 1.2), (r * 0.85, -r * 0.7), (r, 0.0), (r * 0.85, r * 0.7),
                             (r * 0.3, r * 1.2), (0.0, r * 1.35)], 10, sharp=None)


def apples(acc, M, rnd, key, pts, r=0.036, stem="bark"):
    for x, y, z in pts:
        Mf = M @ T(x, y, z, rz=rnd.uniform(0, 360), rx=rnd.uniform(-15, 15))
        lathe(acc, key, Mf, [(0.0, 0.004), (r * 0.45, 0.0), (r * 0.9, r * 0.35), (r, r * 0.9), (r * 0.85, r * 1.45),
                             (r * 0.4, r * 1.75), (0.0, r * 1.6)], 10, sharp=None)
        tube(acc, stem, Mf, [(0, 0, r * 1.55), (0.002, 0.001, r * 1.95)], 0.0018, sides=3)


def grapes(acc, M, rnd, key, n=16, r=0.0085, spread=0.05, stem="bark"):
    """A loose bunch lying on its side (along x)."""
    for i in range(n):
        f = i / max(n - 1, 1)
        x = (f - 0.4) * spread * 1.6
        rad = spread * 0.55 * (1 - abs(f - 0.35) * 1.1)
        a = i * 2.4
        y = math.cos(a) * rad * rnd.uniform(0.5, 1.0)
        z = r + abs(math.sin(a)) * rad * 0.8 * rnd.uniform(0.3, 1.0)
        sphere(acc, key, M @ T(x, y, z), r * rnd.uniform(0.9, 1.1), u=6, v=4, scale=(1, 1, 1.1))
    tube(acc, stem, M, [(-spread * 0.7, 0, r * 1.2), (-spread * 1.0, 0.004, r * 1.8), (-spread * 1.15, 0.0, r * 2.6)],
         0.002, sides=3)


def boule(acc, M, key="crust", r=0.095, h=0.085, flour="flour"):
    """A round sourdough loaf with a dusted top and a cross score."""
    prof = [(0.0, 0.0), (r * 0.9, 0.0), (r, h * 0.2), (r * 0.96, h * 0.5), (r * 0.78, h * 0.82), (r * 0.42, h * 0.98),
            (0.0, h)]
    lathe(acc, key, M, prof, 16, sharp=None)
    lathe(acc, flour, M @ T(z=0.0015), [(0.0, h), (r * 0.42, h * 0.98), (r * 0.62, h * 0.9)], 16, sharp=None)


def baguette(acc, M, key="crust", L=0.5, r=0.03):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * L / 2, v.co.y * r, (v.co.z * 0.8 + 0.8) * r))
    acc.emit(key, bm, M, smooth=True, sharp=None)


def board(acc, M, key="walnut", L=0.42, W=0.26, t=0.022, handle=True):
    """Chopping / serving board with a rounded handle tab on +x."""
    slab(acc, key, M, L, W, t, r=0.025)
    if handle:
        slab(acc, key, M @ T(x=L / 2 + 0.045), 0.12, 0.055, t, r=0.026)


def spoon(acc, M, key="oak_smoked", L=0.30):
    tube(acc, key, M, [(0, 0, 0), (0, 0, L * 0.72)], 0.0055, sides=5)
    sphere(acc, key, M @ T(z=L * 0.82), 0.024, u=8, v=5, scale=(1.0, 0.32, 1.4))


def crock(acc, M, rnd, key="ceramic_white", wood="oak_smoked", h=0.17, r=0.06, n=5):
    """Utensil crock with wooden spoons and spatulas."""
    vessel(acc, key, M, "pot", h, r, segs=16, wall=0.006)
    for i in range(n):
        a = 2 * math.pi * i / n + rnd.uniform(-0.3, 0.3)
        lean = rnd.uniform(6, 16)
        Mi = M @ T(math.cos(a) * r * 0.35, math.sin(a) * r * 0.35, 0.02, rz=math.degrees(a) + 90, rx=lean)
        if i % 2:
            spoon(acc, Mi, wood, rnd.uniform(0.28, 0.33))
        else:
            L = rnd.uniform(0.28, 0.32)
            tube(acc, wood, Mi, [(0, 0, 0), (0, 0, L * 0.7)], 0.006, sides=5)
            box(acc, wood, Mi @ T(z=L * 0.7), 0.05, 0.006, L * 0.28, bevel=0.002)


def bottle(acc, M, key="bottle_green", h=0.30, r=0.037, label="label", cap="black_metal", kind="wine"):
    if kind == "wine":
        prof = [(0.0, 0.0), (r * 0.9, 0.0), (r, 0.008), (r, h * 0.62), (r * 0.85, h * 0.72), (r * 0.42, h * 0.80),
                (r * 0.38, h * 0.97), (r * 0.42, h * 0.975), (r * 0.42, h), (0.0, h)]
    else:   # oil / vinegar: a slim square-shouldered bottle
        prof = [(0.0, 0.0), (r * 0.9, 0.0), (r, 0.006), (r, h * 0.70), (r * 0.6, h * 0.78), (r * 0.32, h * 0.82),
                (r * 0.30, h * 0.97), (0.0, h * 0.97)]
    lathe(acc, key, M, prof, 12)
    if label:
        lathe(acc, label, M, [(r + 0.0007, h * 0.18), (r + 0.0007, h * 0.45)], 12)
    if cap:
        top = h if kind == "wine" else h * 0.97
        lathe(acc, cap, M, [(r * 0.44, top - 0.05 if kind == "wine" else top - 0.004), (r * 0.44, top + 0.002),
                            (0.0, top + 0.002)], 10)


def herb_pot(acc, M, rnd, pot="terracotta", leaf="leaf", soil="soil", r=0.06, h=0.11, n=26, height=0.14,
             leaf_len=0.04, kind="basil"):
    """A potted herb: lathed pot with a rim, soil, a mound of small leaves on short stems."""
    vessel(acc, pot, M, "pot", h, r, segs=14, wall=0.006, fill=(soil, 0.85))
    zs = h * 0.9
    stems = []
    for i in range(n):
        a = i * 2.39996 + rnd.uniform(-0.2, 0.2)
        f = math.sqrt((i + 0.5) / n)
        rr = f * r * 1.15
        z = zs + height * (1.0 - 0.75 * f * f) * rnd.uniform(0.7, 1.05)
        base = Vector((math.cos(a) * r * 0.25 * f, math.sin(a) * r * 0.25 * f, zs))
        tip = Vector((math.cos(a) * rr, math.sin(a) * rr, z))
        L = leaf_len * rnd.uniform(0.8, 1.2) * (1.15 - 0.35 * (1 - f))
        if kind == "grass":
            L = height * rnd.uniform(0.8, 1.3)
        stems.append((base, tip, a, L))
    bm = bmesh.new()
    for base, tip, a, L in stems:
        d = Vector((math.cos(a), math.sin(a), 0.0))
        up = rnd.uniform(0.15, 0.7) if kind != "grass" else rnd.uniform(1.6, 3.0)
        dirv = (d + Vector((0, 0, up))).normalized()
        side = Vector((-math.sin(a), math.cos(a), 0.0)) * rnd.uniform(0.85, 1.15)
        Wd = L * (0.55 if kind == "basil" else 0.12)
        p0 = tip
        p1 = p0 + dirv * L * 0.45 + Vector((0, 0, 0.004))
        p2 = p0 + dirv * L - Vector((0, 0, L * 0.18))
        v0 = bm.verts.new(p0)
        vl = bm.verts.new(p1 - side * Wd * 0.5 - Vector((0, 0, 0.003)))
        vm = bm.verts.new(p1)
        vr = bm.verts.new(p1 + side * Wd * 0.5 - Vector((0, 0, 0.003)))
        vt = bm.verts.new(p2)
        bm.faces.new((v0, vm, vl))
        bm.faces.new((v0, vr, vm))
        bm.faces.new((vl, vm, vt))
        bm.faces.new((vm, vr, vt))
    acc.emit(leaf, bm, M, smooth=True, sharp=None)
    if kind == "basil":
        stem_bm = None
        for base, tip, a, L in stems[::3]:
            tube(acc, leaf, M, [tuple(base), tuple(base.lerp(tip, 0.5) + Vector((0, 0, 0.01))), tuple(tip)], 0.0018,
                 sides=3, cap=False)


def sprigs(acc, M, rnd, twig="bark", leaf="leaf", n=4, h=0.45, spread=0.18, leaves=9, leaf_len=0.06, leaf_w=0.024):
    """Cut branches (olive / eucalyptus) arching out of a vase mouth at the origin."""
    bm = bmesh.new()
    for i in range(n):
        a = 2 * math.pi * i / n + rnd.uniform(-0.5, 0.5)
        hh = h * rnd.uniform(0.7, 1.05)
        sp = spread * rnd.uniform(0.5, 1.1)
        d = Vector((math.cos(a), math.sin(a), 0))
        pts = [Vector((0, 0, -0.05)), Vector((0, 0, 0.0)) + d * 0.005,
               d * sp * 0.35 + Vector((0, 0, hh * 0.45)), d * sp * 0.8 + Vector((0, 0, hh * 0.8)), d * sp + Vector((0, 0, hh))]
        tube(acc, twig, M, [tuple(p) for p in pts], [0.003, 0.003, 0.0025, 0.0018, 0.0012], sides=4, cap=False)
        for k in range(leaves):
            f = 0.3 + 0.7 * k / max(leaves - 1, 1)
            seg = min(int(f * 3), 2) + 1
            q = pts[seg].lerp(pts[seg + 1], (f * 3) % 1.0 if f < 1 else 1.0)
            ang = a + (1 if k % 2 else -1) * rnd.uniform(0.9, 1.6)
            ld = Vector((math.cos(ang), math.sin(ang), rnd.uniform(-0.1, 0.9))).normalized()
            side = ld.cross(Vector((0, 0, 1))).normalized()
            roll = rnd.uniform(0.6, 1.3) * (1 if k % 2 else -1)
            side = (side * math.cos(roll) + ld.cross(side) * math.sin(roll)).normalized()
            L = leaf_len * rnd.uniform(0.7, 1.15)
            v0 = bm.verts.new(q)
            vm = bm.verts.new(q + ld * L * 0.5 + Vector((0, 0, 0.002)))
            vl = bm.verts.new(q + ld * L * 0.45 - side * leaf_w * 0.5)
            vr = bm.verts.new(q + ld * L * 0.45 + side * leaf_w * 0.5)
            vt = bm.verts.new(q + ld * L - Vector((0, 0, L * 0.15)))
            for f_ in ((v0, vm, vl), (v0, vr, vm), (vl, vm, vt), (vm, vr, vt)):
                bm.faces.new(f_)
    acc.emit(leaf, bm, M, smooth=True, sharp=None)


def sculpture(acc, M, kind, key="bronze", base="marble", s=1.0):
    """Small objects for the top of a book stack or a console: 'sphere' (on a little block),
    'ring' (a standing hoop on a block), 'pebbles' (three stacked), 'arc' (a bronze crescent)."""
    if kind == "sphere":
        box(acc, base, M, 0.07 * s, 0.07 * s, 0.035 * s, bevel=0.002)
        sphere(acc, key, M @ T(z=0.035 * s + 0.045 * s), 0.045 * s, u=14, v=8)
    elif kind == "ring":
        box(acc, base, M, 0.09 * s, 0.05 * s, 0.03 * s, bevel=0.002)
        torus(acc, key, M @ T(z=0.03 * s + 0.07 * s, rx=90), 0.068 * s, 0.009 * s, u=24, v=6)
    elif kind == "pebbles":
        z = 0.0
        for i, (r, sq) in enumerate(((0.05, 0.42), (0.038, 0.5), (0.026, 0.58))):
            sphere(acc, key, M @ T(0.004 * i, -0.003 * i, z + r * sq * s, rz=30 * i), r * s, u=12, v=7,
                   scale=(1.15, 1.0, sq))
            z += 2 * r * sq * s * 0.92
    elif kind == "arc":
        box(acc, base, M, 0.11 * s, 0.05 * s, 0.025 * s, bevel=0.002)
        pts = [(0.045 * s * math.cos(math.radians(a)), 0, 0.025 * s + 0.11 * s * math.sin(math.radians(a)) * 0.9 + 0.006)
               for a in range(10, 171, 16)]
        pts = [(x * 1.2, y, z) for x, y, z in pts]
        tube(acc, key, M, pts, [0.004 * s + 0.006 * s * math.sin(math.pi * i / (len(pts) - 1)) for i in range(len(pts))],
             sides=6)


def glasses(acc, M, key="black_metal"):
    """Folded reading glasses lying on a surface."""
    R, r = 0.024, 0.0022
    for sx in (-1, 1):
        torus(acc, key, M @ T(sx * 0.032, 0, R + r, rx=80), R, r, u=12, v=4)
    tube(acc, key, M, [(-0.008, 0, 2 * R), (0.0, 0, 2 * R + 0.004), (0.008, 0, 2 * R)], 0.0016, sides=3)
    for sx in (-1, 1):
        tube(acc, key, M, [(sx * 0.056, -0.004, R * 1.3), (sx * 0.05, 0.03, 0.006), (-sx * 0.02, 0.045, 0.0018)],
             0.0016, sides=3)


def keys(acc, M, rnd, metal="steel", fob="leather"):
    torus(acc, metal, M @ T(z=0.002), 0.012, 0.0013, u=10, v=3)
    for i in range(3):
        a = rnd.uniform(-60, 60) + 120 * i
        Mi = M @ T(z=0.003 + 0.0015 * i, rz=a) @ T(x=0.012)
        box(acc, metal, Mi @ T(x=0.010), 0.018, 0.016, 0.002)
        box(acc, metal, Mi @ T(x=0.034), 0.032, 0.006, 0.0018)
    box(acc, fob, M @ T(x=-0.04, rz=rnd.uniform(-20, 20)), 0.05, 0.022, 0.006, bevel=0.002)


def towel_stack(acc, M, key, n=3, size=(0.32, 0.22), t=0.035):
    for i in range(n):
        bm = common.cushion_bmesh((size[0], size[1], t), cuts=2, edge=t * 0.45,
                                  crown={"+z": 0.004, "-y": 0.006})
        bmesh.ops.translate(bm, vec=Vector((0, 0, t / 2)), verts=bm.verts)
        acc.emit(key, bm, M @ T(0.004 * (i % 2), -0.003 * i, i * t * 0.96, rz=(i - 1) * 2.0), smooth=True, sharp=None)


def plant_paddle(acc, M, rnd, pot="ceramic_charcoal", leaf="leaf", soil="soil", pot_r=0.24, pot_h=0.42,
                 leaves=11, height=1.75, leaf_len=0.62, leaf_w=0.24, seed_tilt=0.0):
    """A bird-of-paradise floor plant: a lathed planter, soil, upright petioles, big paddle
    leaves folded along the midrib with a few splits along the edges (which drop in tone)."""
    R, PH = pot_r, pot_h
    lathe(acc, pot, M, [(R * 0.82, 0.0), (R * 0.9, 0.02), (R * 0.98, PH * 0.4), (R, PH - 0.02), (R, PH),
                        (R - 0.015, PH), (R - 0.016, PH - 0.05)], 20)
    lathe(acc, soil, M, [(0.0, PH - 0.04), (R - 0.016, PH - 0.05)], 16)
    bm = bmesh.new()
    for i in range(leaves):
        f = i / max(leaves - 1, 1)
        a = i * 2.39996 + rnd.uniform(-0.3, 0.3)
        lean = math.radians(6 + 26 * (1 - f) ** 0.7 + rnd.uniform(-4, 4))
        top = PH + (height - PH - leaf_len * 0.8) * (0.55 + 0.45 * f) * rnd.uniform(0.85, 1.05)
        d = Vector((math.cos(a), math.sin(a), 0))
        base = Vector((math.cos(a) * R * 0.25 * rnd.random(), math.sin(a) * R * 0.25 * rnd.random(), PH - 0.04))
        stem_len = (top - base.z) / math.cos(lean)
        tip = base + (d * math.sin(lean) + Vector((0, 0, math.cos(lean)))) * stem_len
        mid = base.lerp(tip, 0.5) + d * 0.02
        tube(acc, leaf, M, [tuple(base), tuple(mid), tuple(tip)], [0.012, 0.009, 0.007], sides=5, cap=False)
        # leaf: rises on from the petiole, arching out and drooping at the tip
        L = leaf_len * rnd.uniform(0.75, 1.1) * (0.8 + 0.2 * f)
        Wd = leaf_w * rnd.uniform(0.85, 1.1) * (0.8 + 0.2 * f)
        out = Vector((math.cos(a + rnd.uniform(-0.3, 0.3)), math.sin(a + rnd.uniform(-0.3, 0.3)), 0))
        side = Vector((-out.y, out.x, 0)).normalized()
        pitch0 = math.radians(70 - 25 * (1 - f) + rnd.uniform(-8, 8))
        rows = 6
        grid = []
        p = tip.copy()
        for r_ in range(rows + 1):
            t = r_ / rows
            pitch = pitch0 - math.radians(70) * t ** 1.6
            if r_ > 0:
                p = p + (out * math.cos(pitch) + Vector((0, 0, math.sin(pitch)))) * (L / rows)
            half = Wd * 0.5 * math.sin(math.pi * min(0.08 + t, 1.0)) ** 0.7 if r_ < rows else 0.0
            fold = 0.035 * Wd / 0.24 * (1 - t * 0.5)
            row = []
            for s in (-1, 0, 1):
                tear = 0.0
                if s and r_ in (2, 4) and rnd.random() < 0.5:
                    tear = 0.012
                row.append(bm.verts.new(p + side * (s * half) - Vector((0, 0, fold * abs(s) + tear))))
            grid.append(row)
        for r_ in range(rows):
            for c in range(2):
                bm.faces.new((grid[r_][c], grid[r_][c + 1], grid[r_ + 1][c + 1], grid[r_ + 1][c]))
    acc.emit(leaf, bm, M, smooth=True, sharp=None)


def knife(acc, M, blade="steel", handle="walnut", L=0.24):
    """A kitchen / cheese knife lying flat along +x."""
    box(acc, handle, M, L * 0.42, 0.016, 0.012, bevel=0.003)
    bm = bmesh.new()
    b = L * 0.58
    pts = [(L * 0.21, -0.012), (L * 0.21 + b * 0.9, -0.004), (L * 0.21 + b, 0.008), (L * 0.21, 0.010)]
    lo = [bm.verts.new((x, y, 0.004)) for x, y in pts]
    hi = [bm.verts.new((x, y, 0.0055)) for x, y in pts]
    bm.faces.new(list(reversed(lo)))
    bm.faces.new(hi)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    acc.emit(blade, bm, M, smooth=False)


def mortar(acc, M, key="marble", wood="walnut", r=0.065):
    vessel(acc, key, M, "dish", r * 1.1, r, segs=16, wall=0.012)
    lathe(acc, key, M @ T(0.01, 0.0, r * 0.5, ry=35), [(0.0, 0.0), (0.016, 0.004), (0.019, 0.02), (0.011, 0.07),
                                                        (0.012, 0.10), (0.0, 0.104)], 10, sharp=None)


def mill(acc, M, key="walnut", h=0.19, r=0.026):
    lathe(acc, key, M, [(0.0, 0.0), (r, 0.0), (r, h * 0.55), (r * 0.8, h * 0.62), (r * 0.92, h * 0.68), (r * 0.92, h * 0.9),
                        (r * 0.55, h * 0.97), (0.0, h)], 12)


def salt_cellar(acc, M, key="marble", lid="walnut", r=0.045):
    lathe(acc, key, M, [(0.0, 0.0), (r * 0.9, 0.0), (r, 0.01), (r, 0.05), (r - 0.006, 0.05), (r - 0.006, 0.012),
                        (0.0, 0.012)], 14)
    lathe(acc, "paper_white" if key != "paper_white" else "candle", M,
          [(0.0, 0.036), (r - 0.0065, 0.036)], 12)
    if lid:
        lathe(acc, lid, M @ T(z=0.05), [(0.0, 0.0), (r * 1.02, 0.0), (r * 1.02, 0.006), (r * 0.9, 0.012), (0.0, 0.012)], 14)


def soap_pump(acc, M, key="ceramic_white", pump="steel", h=0.16, r=0.035):
    lathe(acc, key, M, [(0.0, 0.0), (r * 0.9, 0.0), (r, 0.01), (r, h * 0.8), (r * 0.6, h * 0.9), (r * 0.3, h), (0.0, h)], 14)
    tube(acc, pump, M, [(0, 0, h), (0, 0, h + 0.03)], 0.006, sides=8)
    tube(acc, pump, M, [(0, 0.004, h + 0.03), (0, -0.035, h + 0.03), (0, -0.04, h + 0.022)], 0.004, sides=6)


def brush(acc, M, wood="oak_smoked", bristle="wicker", L=0.24):
    """Wooden dish brush lying on its side along +x."""
    tube(acc, wood, M @ T(z=0.012), [(0, 0, 0), (L * 0.75, 0, 0.005)], 0.009, sides=6)
    sphere(acc, wood, M @ T(L * 0.8, 0, 0.022), 0.024, u=10, v=6, scale=(0.8, 1, 0.9))
    sphere(acc, bristle, M @ T(L * 0.86, 0, 0.022), 0.026, u=10, v=6, scale=(0.75, 1, 0.9))


def mug(acc, M, key="ceramic_white", coffee="coffee", h=0.095, r=0.042):
    lathe(acc, key, M, [(0.0, 0.0), (r * 0.9, 0.0), (r, 0.006), (r, h), (r - 0.004, h), (r - 0.004, 0.01), (0.0, 0.01)], 16)
    if coffee:
        lathe(acc, coffee, M, [(0.0, h - 0.018), (r - 0.0045, h - 0.018)], 14)
    tube(acc, key, M, [(r - 0.002, 0, h * 0.82), (r + 0.022, 0, h * 0.78), (r + 0.026, 0, h * 0.45), (r + 0.014, 0, h * 0.25),
                       (r - 0.002, 0, h * 0.22)], 0.005, sides=5, cap=False)


def basket(acc, M, key="wicker", r=0.22, h=0.32, rim="leather"):
    """A woven floor basket: a slightly flared lathe with a rolled rim and two leather handles."""
    vessel(acc, key, M, "pot", h, r, segs=20, wall=0.01)
    torus(acc, key, M @ T(z=h - 0.004), r * 1.0, 0.012, u=20, v=5)
    if rim:
        for sx in (-1, 1):
            box(acc, rim, M @ T(sx * (r + 0.004), 0, h - 0.07, rz=90), 0.11, 0.008, 0.03, bevel=0.002)


def rolled_throw(acc, M, key, L=0.55, r=0.07):
    """A rolled blanket (a capsule with a spiral end), lying along x."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=12, radius1=r, radius2=r, depth=L)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "Y"))
    for v in bm.verts:
        v.co.z *= 0.92
    acc.emit(key, bm, M, smooth=True, sharp=60.0)


def throw_folded(acc, M, key, size=(0.48, 0.36), t=0.075, drape=0.20):
    """A folded throw: a soft folded block with the fold edge to the front, its loose end
    dropping over the front edge of the seat by `drape`."""
    layers = 3
    lt = t / layers
    for i in range(layers):
        # folded layers, each a soft slab, the fold edges stepping back a little
        bm = common.cushion_bmesh((size[0] - 0.008 * i, size[1] - 0.012 * i, lt * 1.05), cuts=2, edge=lt * 0.48,
                                  crown={"+z": 0.003, "-y": 0.004})
        bmesh.ops.translate(bm, vec=Vector((0.003 * (i % 2), 0.006 * i, lt * (i + 0.5))), verts=bm.verts)
        acc.emit(key, bm, M, smooth=True, sharp=None)
    if drape > 0:
        # a soft flap from under the block over the front edge (y = -size/2), hanging down
        bm = bmesh.new()
        rows = []
        W = size[0] * 0.92
        prof = [(-size[1] * 0.3, 0.004), (-size[1] * 0.5, 0.002), (-size[1] * 0.5 - 0.02, -0.02), (-size[1] * 0.5 - 0.03, -drape * 0.5),
                (-size[1] * 0.5 - 0.028, -drape)]
        for y, z in prof:
            rows.append([bm.verts.new((x, y, z)) for x in (-W / 2, -W / 6, W / 6, W / 2)])
        for a, b in zip(rows[:-1], rows[1:]):
            for i in range(3):
                bm.faces.new((a[i], a[i + 1], b[i + 1], b[i]))
        acc.emit(key, bm, M, smooth=True, sharp=None)


def crate(acc, M, key="oak_light", L=0.50, W=0.34, H=0.20, t=0.012, lid=False, label="label"):
    """An open wooden wine crate (base, four sides; optional lid), a branded label on the front."""
    box(acc, key, M, L, W, t)
    box(acc, key, M @ T(y=-W / 2 + t / 2), L, t, H)
    box(acc, key, M @ T(y=W / 2 - t / 2), L, t, H)
    box(acc, key, M @ T(x=-L / 2 + t / 2), t, W - 2 * t, H)
    box(acc, key, M @ T(x=L / 2 - t / 2), t, W - 2 * t, H)
    if lid:
        box(acc, key, M @ T(z=H), L, W, t)
    if label:
        box(acc, label, M @ T(y=-W / 2 - 0.0006, z=H * 0.3), L * 0.4, 0.001, H * 0.4)


def spray_bottle(acc, M, body="white_lacquer", head="accent", h=0.22, r=0.035):
    lathe(acc, body, M, [(0.0, 0.0), (r * 0.9, 0.0), (r, 0.008), (r, h * 0.7), (r * 0.5, h * 0.8), (r * 0.42, h * 0.84), (0.0, h * 0.84)], 12)
    box(acc, head, M @ T(z=h * 0.84), 0.03, 0.06, 0.035, bevel=0.004)
    box(acc, head, M @ T(0, -0.02, h * 0.84 - 0.03, rx=12), 0.012, 0.012, 0.04, bevel=0.002)
