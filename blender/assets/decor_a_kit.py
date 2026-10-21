"""Set-dressing kit for the decor_a_* assets (not an asset itself; like library_kit.py).

A `Builder` gathers every small object of a vignette into ONE mesh per material (so a whole
console vignette costs one draw call per material), each named `<Asset>_<Key>_NoCollide`
(small things never become colliders). Item functions (book stacks, vessels, trays, candles,
cups, glasses, magazines, plants, throws, towels...) add geometry to it at a 4x4 matrix
(`at(x, y, z, rot_deg)`), with world-scale UVs (box projection at the material's tile) or their
own atlas UVs (book spines, leaves).

Materials are only reused, never redefined: `mat(key)` returns the existing material of that
name when the level already has it (so this kit never recolours someone else's asset), else
creates it with exactly the arguments of the asset that defines it. Books use the library's
spine atlas (M_Library_Spines: one material for every colour), or, in rooms that already have
them, the flat M_Book_* colours of living_shelving.
"""
import importlib
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common, materials, pickups, textures  # noqa: E402

importlib.reload(common)
importlib.reload(materials)
importlib.reload(textures)
importlib.reload(pickups)


# ------------------------------------------------------------------ materials

def _get(name, create):
    m = bpy.data.materials.get(name)
    return m if m is not None else create()


def _spines():
    import library_bookcase
    return library_bookcase.books_material()


def _leaf():
    import library_plant
    m = common.pbr_material("M_Library_Leaf", (1, 1, 1), roughness=0.38)
    common.set_base_color_map(m, textures.load(library_plant.leaf_texture()))
    m.use_backface_culling = False
    return m


def _leather():
    m = common.pbr_material("M_Leather_Cognac", (0.23, 0.075, 0.025), roughness=0.62)
    common.set_normal_map(m, textures.load(textures.leather_normal(), non_color=True), 0.6)
    return m


def _wool():
    m = common.pbr_material("M_Wool_Charcoal", (0.06, 0.06, 0.065), roughness=0.95)
    common.set_base_color_map(m, textures.load(textures.wool()))
    return m


BOOK_FLAT = [("M_Book_Cream", (0.42, 0.38, 0.30)), ("M_Book_Ink", (0.025, 0.04, 0.07)),
             ("M_Book_Moss", (0.04, 0.07, 0.05)), ("M_Book_Rust", (0.20, 0.07, 0.035)),
             ("M_Book_Charcoal", (0.03, 0.03, 0.032)), ("M_Book_Sand", (0.30, 0.24, 0.16))]

# key: (material name, creator, uv tile in metres)
MATS = {
    "spines": ("M_Library_Spines", _spines, None),
    "glaze": ("M_Ceramic_Glaze", lambda: common.pbr_material("M_Ceramic_Glaze", (0.55, 0.52, 0.46), roughness=0.18), 0.5),
    "stoneware": ("M_Entry_Stoneware", lambda: common.pbr_material("M_Entry_Stoneware", (0.60, 0.56, 0.50), roughness=0.62), 0.5),
    "porcelain": ("M_Entry_Ceramic", lambda: common.pbr_material("M_Entry_Ceramic", (0.80, 0.80, 0.78), roughness=0.10), 0.5),
    "charcoal": ("M_Ceramic_Charcoal", lambda: common.pbr_material("M_Ceramic_Charcoal", (0.05, 0.05, 0.055), roughness=0.3), 0.5),
    "bronze": ("M_Bronze", materials.bronze, 0.5),
    "bronze_polished": ("M_Entry_Bronze_Polished", lambda: common.pbr_material(
        "M_Entry_Bronze_Polished", (0.50, 0.30, 0.14), roughness=0.2, metallic=1.0), 0.5),
    "walnut": ("M_Walnut", materials.walnut, 0.5),
    "steel": ("M_Steel_Polished", materials.steel, 0.5),
    "oak": ("M_OakSmoked", materials.smoked_oak, 0.5),
    "black": ("M_Aluminium_Black", materials.black_metal, 0.5),
    "marble": ("M_Marble_White", lambda: common.pbr_material("M_Marble_White", (0.8, 0.79, 0.77), roughness=0.12), 0.5),
    "leather": ("M_Leather_Cognac", _leather, 0.2),
    "oat": ("M_Fabric_Oat", lambda: materials.fabric("M_Fabric_Oat", (0.50, 0.44, 0.35)), 0.25),
    "ink": ("M_Fabric_Ink", lambda: materials.fabric("M_Fabric_Ink", (0.018, 0.024, 0.04), roughness=0.8), 0.25),
    "cognac": ("M_Fabric_Cognac", lambda: materials.fabric("M_Fabric_Cognac", (0.20, 0.085, 0.035)), 0.25),
    "moss": ("M_Fabric_Moss", lambda: materials.fabric("M_Fabric_Moss", (0.030, 0.050, 0.035)), 0.25),
    "wool": ("M_Wool_Charcoal", lambda: _wool(), 0.5),
    "coat_camel": ("M_Entry_Coat_Camel", lambda: materials.fabric("M_Entry_Coat_Camel", (0.31, 0.19, 0.085), roughness=0.95), 0.25),
    "coat_navy": ("M_Entry_Coat_Navy", lambda: materials.fabric("M_Entry_Coat_Navy", (0.020, 0.028, 0.055), roughness=0.95), 0.25),
    "coat_charcoal": ("M_Entry_Coat_Charcoal", lambda: materials.fabric("M_Entry_Coat_Charcoal", (0.035, 0.036, 0.04), roughness=0.95), 0.25),
    "coat_oat": ("M_Entry_Coat_Oat", lambda: materials.fabric("M_Entry_Coat_Oat", (0.30, 0.26, 0.20), roughness=0.95), 0.25),
    "coat_olive": ("M_Entry_Coat_Olive", lambda: materials.fabric("M_Entry_Coat_Olive", (0.07, 0.085, 0.04), roughness=0.95), 0.25),
    "glass": ("M_Glass_Smoke", lambda: materials.glass("M_Glass_Smoke", tint=(0.42, 0.40, 0.37), alpha=0.35, roughness=0.04), 0.5),
    "leaf": ("M_Library_Leaf", _leaf, None),
    "soil": ("M_Plant_Soil", lambda: common.pbr_material("M_Plant_Soil", (0.025, 0.016, 0.010), roughness=1.0), 0.5),
    "bark": ("M_Plant_Bark", lambda: common.pbr_material("M_Plant_Bark", (0.10, 0.07, 0.045), roughness=0.8), 0.5),
    "blossom": ("M_Entry_Blossom_White", lambda: common.pbr_material("M_Entry_Blossom_White", (0.78, 0.74, 0.68), roughness=0.8), 0.5),
    "blossom_blush": ("M_Entry_Blossom_Blush", lambda: common.pbr_material("M_Entry_Blossom_Blush", (0.62, 0.36, 0.38), roughness=0.8), 0.5),
    "twig": ("M_Entry_Twig", lambda: common.pbr_material("M_Entry_Twig", (0.045, 0.030, 0.020), roughness=0.8), 0.5),
    "candle": ("M_Candle_Cream", lambda: common.pbr_material("M_Candle_Cream", (0.78, 0.72, 0.58), roughness=0.55), 0.5),
    "lemon": ("M_Lemon", lambda: common.pbr_material("M_Lemon", (0.75, 0.55, 0.03), roughness=0.5), 0.5),
    "felt": ("M_Felt_Black", lambda: common.pbr_material("M_Felt_Black", (0.012, 0.012, 0.013), roughness=1.0), 0.5),
}
for _nm, _c in BOOK_FLAT:
    MATS[_nm] = (_nm, (lambda nm=_nm, c=_c: common.pbr_material(nm, c, roughness=0.75)), 0.5)


def mat(key):
    name, create, _ = MATS[key]
    return _get(name, create)


# ------------------------------------------------------------------ builder

def at(x=0.0, y=0.0, z=0.0, rot=0.0, tilt=None):
    """Placement matrix: translate, then rotate `rot` degrees about Z; tilt = (deg, axis)."""
    m = Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(rot), 4, "Z")
    if tilt:
        m = m @ Matrix.Rotation(math.radians(tilt[0]), 4, tilt[1])
    return m


class Builder:
    def __init__(self, name, collide=()):
        self.n = name
        self.col = common.fresh_collection(name)
        self.root = common.empty(name, self.col)
        self.meshes = {}                 # key -> bmesh with UVMap
        self.collide = set(collide)      # keys whose object may collide (floor pieces)

    def bm(self, key):
        if key not in self.meshes:
            b = bmesh.new()
            b.loops.layers.uv.new("UVMap")
            self.meshes[key] = b
        return self.meshes[key]

    def add(self, key, src, M=None, tile=None, smooth=None):
        """Merge bmesh `src` (freed) into material `key` at matrix M. UVs: src's own UV layer
        if it has one, else a box projection in src's local coordinates at `tile` metres."""
        M = M or Matrix.Identity(4)
        dst = self.bm(key)
        uvl = dst.loops.layers.uv.active
        suv = src.loops.layers.uv.active
        tile = tile or MATS.get(key, (None, None, 0.5))[2] or 0.5
        vm = {v: dst.verts.new(M @ v.co) for v in src.verts}
        flip = M.to_3x3().determinant() < 0          # mirrored: keep faces pointing outward
        for f in src.faces:
            loops = list(f.loops)[::-1] if flip else list(f.loops)
            try:
                nf = dst.faces.new([vm[lp.vert] for lp in loops])
            except ValueError:
                continue
            nf.smooth = f.smooth if smooth is None else smooth
            nrm = [abs(c) for c in f.normal]
            ax = nrm.index(max(nrm))
            a, b = [i for i in range(3) if i != ax]
            for ls, ld in zip(loops, nf.loops):
                if suv is not None:
                    ld[uvl].uv = ls[suv].uv
                else:
                    co = ls.vert.co
                    ld[uvl].uv = (co[a] / tile, co[b] / tile)
        for e in src.edges:
            if not e.smooth:
                de = dst.edges.get((vm[e.verts[0]], vm[e.verts[1]]))
                if de is not None:
                    de.smooth = False
        src.free()

    def finish(self):
        # loose things become pickups (lib/pickups.py), the rest stays one mesh per material
        pickups.emit(self, self.n, self.col, self.root, list(self.meshes.values()), lambda b: b, mat)
        for key, b in self.meshes.items():
            suffix = key.replace("M_", "").replace("_", "")
            name = f"{self.n}_{suffix}" + ("" if key in self.collide else "_NoCollide")
            ob = common.mesh_object(name, b, self.col, mat(key), self.root, smooth=False)
        parts = [o for o in self.root.children_recursive if o.type == "MESH"]
        return self.root, parts


# ------------------------------------------------------------------ primitives

def box(size, centre=(0, 0, 0), skip=(), chamfer=0.0):
    """Box bmesh; skip = faces to leave out ('-z', '+y', ...). chamfer: one-segment bevel."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    if chamfer > 0:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=chamfer, segments=1, affect="EDGES")
    for f in list(bm.faces):
        for s in skip:
            ax = "xyz".index(s[1])
            sg = 1 if s[0] == "+" else -1
            if f.normal[ax] * sg > 0.99:
                bm.faces.remove(f)
                break
    bmesh.ops.translate(bm, vec=Vector(centre), verts=bm.verts)
    for f in bm.faces:
        f.smooth = False
    return bm


def lathe(profile, segs=16, sharp=40.0, smooth=True, closed=False, phase=0.0):
    """Revolve [(r, z), ...] about Z (r == 0 collapses to the axis). Corners turning more than
    `sharp` degrees get sharp edges."""
    bm = bmesh.new()
    rows = []
    for r, z in profile:
        if abs(r) < 1e-9:
            rows.append([bm.verts.new((0.0, 0.0, z))] * segs)
        else:
            rows.append([bm.verts.new((r * math.cos(2 * math.pi * (s + phase) / segs),
                                       r * math.sin(2 * math.pi * (s + phase) / segs), z)) for s in range(segs)])
    n = len(profile)
    for i in range(n if closed else n - 1):
        a, b = rows[i], rows[(i + 1) % n]
        for s in range(segs):
            t = (s + 1) % segs
            quad = []
            for v in (a[s], a[t], b[t], b[s]):
                if v not in quad:
                    quad.append(v)
            if len(quad) >= 3:
                try:
                    f = bm.faces.new(quad)
                    f.smooth = smooth
                except ValueError:
                    pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for i, (r, z) in enumerate(profile):
        if abs(r) < 1e-9 or (not closed and i in (0, n - 1)):
            continue
        pr, nx = profile[(i - 1) % n], profile[(i + 1) % n]
        d1, d2 = (r - pr[0], z - pr[1]), (nx[0] - r, nx[1] - z)
        ang = math.degrees(abs(math.atan2(d1[0] * d2[1] - d1[1] * d2[0], d1[0] * d2[0] + d1[1] * d2[1])))
        if ang > sharp:
            for s in range(segs):
                e = bm.edges.get((rows[i][s], rows[i][(s + 1) % segs]))
                if e is not None:
                    e.smooth = False
    return bm


def catmull(pts, per=3):
    """Catmull-Rom through [(r, z)], `per` points per span."""
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(per):
            t = k / per
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in (0, 1)))
    out.append(P[-2])
    return out


def open_vessel(outer, wall=0.006, floor=0.008, per=2, lip=True, inner_n=None):
    """Profile of an open vessel from its outer silhouette [(r, z), ...] (foot edge -> rim):
    smooth outer wall, a rounded lip, the inner wall offset by `wall`, an inner floor."""
    o = catmull(outer, per)
    inner = []
    for i, (r, z) in enumerate(o):
        a, b = o[max(i - 1, 0)], o[min(i + 1, len(o) - 1)]
        tr, tz = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(tr, tz) or 1.0
        nr, nz = tz / ln, -tr / ln            # outward normal
        inner.append((max(r - wall * nr, 0.0), z - wall * nz))
    inner = [(r, max(z, floor)) for r, z in inner if z >= floor - 1e-6]
    if inner_n and len(inner) > inner_n:      # narrow vessels: only the inside of the lip is ever seen
        inner = [(inner[-inner_n][0], floor)] + inner[-inner_n:]
    top_o, top_i = o[-1], inner[-1]
    prof = [(0.0, 0.0)] + o
    if lip:
        prof.append(((top_o[0] + top_i[0]) / 2, top_o[1] + wall * 0.35))
    prof += list(reversed(inner)) + [(inner[0][0] * 0.9, floor), (0.0, floor)]
    return prof


def rrect(w, d, r, segs=3):
    """Rounded rectangle outline (counter-clockwise) as [(x, y)]."""
    r = min(r, w / 2 - 1e-4, d / 2 - 1e-4)
    out = []
    for cx, cy, a0 in ((w / 2 - r, d / 2 - r, 0), (-w / 2 + r, d / 2 - r, 90), (-w / 2 + r, -d / 2 + r, 180),
                       (w / 2 - r, -d / 2 + r, 270)):
        for k in range(segs + 1):
            a = math.radians(a0 + 90 * k / segs)
            out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def loft(rings, cap_top=False, cap_bottom=False, smooth=False, sharp_rows=()):
    """Bridge rings [[(x, y, z), ...], ...] of equal length (closed loops)."""
    bm = bmesh.new()
    vr = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    for a, b in zip(vr, vr[1:]):
        for k in range(n):
            q = (k + 1) % n
            try:
                f = bm.faces.new((a[k], a[q], b[q], b[k]))
                f.smooth = smooth
            except ValueError:
                pass
    if cap_bottom:
        f = bm.faces.new(list(reversed(vr[0])))
        f.smooth = False
    if cap_top:
        f = bm.faces.new(vr[-1])
        f.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for i in sharp_rows:
        for k in range(n):
            e = bm.edges.get((vr[i][k], vr[i][(k + 1) % n]))
            if e is not None:
                e.smooth = False
    return bm


def ellipsoid(rx, ry, rz, segs=10, rings=6, z0=None, squash=0.0):
    """UV ellipsoid sitting on z = 0 (or centred at z0); squash flattens its underside."""
    zc = rz if z0 is None else z0
    prof = []
    for i in range(rings + 1):
        t = math.pi * i / rings
        z = -math.cos(t) * rz
        if z < 0:
            z *= (1 - squash)
        prof.append((math.sin(t) * 1.0, z + zc))
    bm = lathe([(r, z) for r, z in prof], segs, sharp=179)
    for v in bm.verts:
        v.co.x *= rx
        v.co.y *= ry
    return bm


def tube(points, radius, sides=5, taper=None, cap=True):
    """Tube along a polyline [(x, y, z)]; taper = end radius (linear)."""
    bm = bmesh.new()
    pts = [Vector(p) for p in points]
    rings = []
    up = Vector((0, 0, 1))
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        ref = up if abs(d.dot(up)) < 0.95 else Vector((1, 0, 0))
        u = d.cross(ref).normalized()
        w = d.cross(u)
        r = radius if taper is None else radius + (taper - radius) * i / (len(pts) - 1)
        rings.append([bm.verts.new(p + r * (math.cos(2 * math.pi * k / sides) * u + math.sin(2 * math.pi * k / sides) * w))
                      for k in range(sides)])
    for a, b in zip(rings, rings[1:]):
        for k in range(sides):
            q = (k + 1) % sides
            f = bm.faces.new((a[k], a[q], b[q], b[k]))
            f.smooth = True
    if cap:
        tip = bm.verts.new(pts[-1] + (pts[-1] - pts[-2]).normalized() * (taper if taper is not None else radius) * 0.5)
        for k in range(sides):
            f = bm.faces.new((rings[-1][k], rings[-1][(k + 1) % sides], tip))
            f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


# ------------------------------------------------------------------ books (spine atlas)

ATLAS_N = 1024.0
CELL_W, CELL_H = 64, 256
PAPER_Y0 = 768
# atlas cells that read as modern cloth / paper bindings: (col, row, cover patch y0, y1 in cell px)
_CLOTH, _TWO, _PLAIN = (64, 86), (58, 130), (112, 200)
MODERN_CELLS = [(2, 0, *_PLAIN), (9, 0, *_CLOTH), (15, 0, *_CLOTH), (1, 1, *_TWO), (2, 1, *_PLAIN),
                (8, 1, *_CLOTH), (0, 2, *_CLOTH), (1, 2, *_TWO), (8, 2, *_CLOTH), (9, 2, *_PLAIN),
                (10, 2, *_PLAIN), (15, 2, *_CLOTH), (4, 2, *_TWO), (5, 2, *_TWO), (11, 2, *_TWO), (0, 1, *_TWO)]
# palettes (indices into MODERN_CELLS) for curated, colour-coordinated stacks
PALETTES = {
    "neutral": [0, 3, 4, 8, 2, 13, 15],          # cream, cream, black, black, grey, brown, brown
    "warm": [0, 3, 13, 15, 11, 4, 14],            # cream, brown, olive, black
    "cool": [0, 2, 1, 6, 10, 4, 12, 7],           # cream, grey, sage, green, navy, black, teal, slate
    "all": list(range(len(MODERN_CELLS))),
}


def _uv_rect(face, uvl, axes, lo, hi, u_rng, v_rng):
    """Map a face's vertices linearly: coordinate axes[0] in lo[0]..hi[0] -> u_rng, axes[1] -> v_rng."""
    for lp in face.loops:
        co = lp.vert.co
        s = (co[axes[0]] - lo[0]) / max(hi[0] - lo[0], 1e-6)
        t = (co[axes[1]] - lo[1]) / max(hi[1] - lo[1], 1e-6)
        lp[uvl].uv = (u_rng[0] + (u_rng[1] - u_rng[0]) * s, v_rng[0] + (v_rng[1] - v_rng[0]) * t)


def book_atlas(L, D, T, cell, rnd, hide_bottom=True):
    """A book lying flat, spine toward -y: two cover boards, a spine and a paper block
    between them, UV'd onto the spine atlas. x: -L/2..L/2 (spine length), y: -D/2..D/2,
    z: 0..T. Returns a bmesh with UVs."""
    col, row, cy0, cy1 = MODERN_CELLS[cell]
    px, py = col * CELL_W, row * CELL_H
    cu = ((px + 16) / ATLAS_N, (px + 48) / ATLAS_N)
    cv = (1 - (py + cy1) / ATLAS_N, 1 - (py + cy0) / ATLAS_N)
    su = ((px + 3) / ATLAS_N, (px + CELL_W - 3) / ATLAS_N)
    sv = (1 - (py + CELL_H - 3) / ATLAS_N, 1 - (py + 3) / ATLAS_N)
    bt = min(0.0028, T * 0.14)          # board
    st = 0.003                          # spine
    ov = min(0.003, L * 0.02)           # board overhang over the page block
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")

    def add_box(lo, hi, skip, mapper):
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        V = [bm.verts.new(c) for c in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                       (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
        faces = {"-z": (3, 2, 1, 0), "+z": (4, 5, 6, 7), "-y": (0, 1, 5, 4), "+y": (2, 3, 7, 6),
                 "-x": (3, 0, 4, 7), "+x": (1, 2, 6, 5)}
        for k, idx in faces.items():
            if k in skip:
                continue
            f = bm.faces.new([V[i] for i in idx])
            f.smooth = False
            mapper(k, f, lo, hi)

    def cover(k, f, lo, hi):
        _uv_rect(f, uvl, (0, 1), lo[:2], hi[:2], cu, cv)

    def spine(k, f, lo, hi):
        if k == "-y":   # cell's long axis along the spine (x), its width across the thickness (z)
            for lp in f.loops:
                co = lp.vert.co
                s = (co.x - lo[0]) / (hi[0] - lo[0])
                t = (co.z - lo[2]) / (hi[2] - lo[2])
                lp[uvl].uv = (su[0] + (su[1] - su[0]) * t, sv[1] - (sv[1] - sv[0]) * s)
        else:
            cover(k, f, lo, hi)

    pu = rnd.uniform(0.02, 0.6)
    pv = 1 - (PAPER_Y0 + rnd.uniform(20, 160)) / ATLAS_N

    def paper(k, f, lo, hi):
        ax = 1 if k in ("-x", "+x") else 0
        span = (hi[ax] - lo[ax]) / 0.4 * 0.3
        th = (hi[2] - lo[2]) / 0.001 * 1.6 / ATLAS_N     # ~1.6 px of paper texture per mm
        _uv_rect(f, uvl, (ax, 2), (lo[ax], lo[2]), (hi[ax], hi[2]), (pu, pu + span), (pv, pv - th))

    hb = ("-z",) if hide_bottom else ()
    add_box((-L / 2, -D / 2, 0), (L / 2, D / 2, bt), hb, cover)
    add_box((-L / 2, -D / 2, T - bt), (L / 2, D / 2, T), ("-z",), cover)
    add_box((-L / 2, -D / 2, bt), (L / 2, -D / 2 + st, T - bt), ("-z", "+z", "+y"), spine)
    add_box((-L / 2 + ov, -D / 2 + st, bt), (L / 2 - ov, D / 2 - ov, T - bt), ("-z", "+z", "-y"), paper)
    return bm


def book_flat(L, D, T, hide_bottom=True):
    """Same construction for flat-colour books: returns (cover bmesh, paper bmesh)."""
    bt, st, ov = min(0.0028, T * 0.14), 0.003, min(0.003, L * 0.02)
    hb = ("-z",) if hide_bottom else ()
    c = box((L, D, bt), (0, 0, bt / 2), hb)
    _merge(c, box((L, D, bt), (0, 0, T - bt / 2), ("-z",)))
    _merge(c, box((L, st, T - 2 * bt), (0, -D / 2 + st / 2, T / 2), ("-z", "+z", "+y")))
    p = box((L - 2 * ov, D - st - ov, T - 2 * bt), (0, (st - ov) / 2, T / 2), ("-z", "+z", "-y"))
    return c, p


def _merge(dst, src):
    vm = {v: dst.verts.new(v.co) for v in src.verts}
    for f in src.faces:
        nf = dst.faces.new([vm[v] for v in f.verts])
        nf.smooth = f.smooth
    src.free()
    return dst


def book(B, M, L, D, T, rnd, palette="neutral", flat=False, hide_bottom=True, cell=None):
    if flat:
        c, p = book_flat(L, D, T, hide_bottom)
        key = rnd.choice([k for k, _ in BOOK_FLAT if k != "M_Book_Cream"] + ["M_Book_Cream"] * 1)
        B.add(key, c, M)
        B.add("M_Book_Cream", p, M)
    else:
        cell = cell if cell is not None else rnd.choice(PALETTES[palette])
        B.add("spines", book_atlas(L, D, T, cell, rnd, hide_bottom), M)


def stack(B, M, rnd, n=3, size=(0.30, 0.24), thick=(0.022, 0.045), palette="neutral", flat=False,
          jitter=4.0, shrink=0.9):
    """Art books lying flat, biggest at the bottom, each slightly turned. Returns the top z."""
    z = 0.0
    L0, D0 = size
    for i in range(n):
        k = 1.0 - (1.0 - shrink) * i - rnd.uniform(0.0, 0.06)
        L, D = L0 * k * rnd.uniform(0.96, 1.04), D0 * k * rnd.uniform(0.95, 1.05)
        T = rnd.uniform(*thick)
        rot = rnd.uniform(-jitter, jitter)
        dx, dy = rnd.uniform(-0.008, 0.008), rnd.uniform(-0.008, 0.008)
        book(B, M @ at(dx, dy, z, rot), L, D, T, rnd, palette, flat, hide_bottom=True)
        z += T
    return z


def upright_row(B, M, rnd, n=6, height=(0.22, 0.30), depth=(0.15, 0.20), thick=(0.018, 0.04), palette="all",
                flat=False, lean_last=0.0):
    """Books standing on a shelf in a row along +x from x=0, spines toward -y. Returns the row width."""
    x = 0.0
    for i in range(n):
        H, D, T = rnd.uniform(*height), rnd.uniform(*depth), rnd.uniform(*thick)
        # lay a book with spine length H along x, depth D, thickness T; stand it up on its tail
        Mi = M @ at(x + T / 2, 0, H / 2) @ Matrix.Rotation(math.radians(90), 4, "Y") @ at(0, 0, -T / 2)
        book(B, Mi, H, D, T, rnd, palette, flat, hide_bottom=False)
        x += T + 0.001
    return x


# ------------------------------------------------------------------ objects

def vase(B, M, key, kind="bottle", h=0.30, r=0.07, segs=14):
    """Ceramic vases of one family, scaled to (h, r): bottle, ovoid, cylinder, jar, bud."""
    shapes = {
        "bottle": [(0.62, 0.0), (0.82, 0.08), (1.0, 0.32), (0.92, 0.55), (0.42, 0.74), (0.26, 0.86), (0.25, 0.97), (0.30, 1.0)],
        "ovoid": [(0.55, 0.0), (0.85, 0.12), (1.0, 0.42), (0.88, 0.75), (0.62, 0.93), (0.58, 1.0)],
        "cylinder": [(0.86, 0.0), (0.95, 0.03), (1.0, 0.25), (0.98, 0.8), (0.93, 1.0)],
        "jar": [(0.62, 0.0), (0.9, 0.12), (1.0, 0.42), (0.9, 0.72), (0.58, 0.86), (0.55, 1.0)],
        "bud": [(0.7, 0.0), (1.0, 0.18), (0.82, 0.42), (0.28, 0.7), (0.22, 0.95), (0.26, 1.0)],
        "flask": [(0.9, 0.0), (1.0, 0.06), (1.0, 0.5), (0.85, 0.66), (0.3, 0.78), (0.24, 0.98), (0.27, 1.0)],
    }
    outer = [(a * r, b * h) for a, b in shapes[kind]]
    prof = open_vessel(outer, wall=max(0.004, r * 0.08), floor=0.01, per=1, inner_n=2)
    B.add(key, lathe(prof, segs if r >= 0.06 else min(segs, 12)), M)


def bowl(B, M, key, r=0.16, h=0.07, segs=16, foot=0.45, wall=0.006):
    outer = [(r * foot, 0.0), (r * foot * 1.04, 0.006), (r * 0.78, h * 0.35), (r * 0.95, h * 0.75), (r, h)]
    B.add(key, lathe(open_vessel(outer, wall=wall, floor=0.012, per=1), segs), M)


def plate(B, M, key, r=0.10, h=0.014, segs=20):
    prof = [(0.0, 0.0), (r * 0.55, 0.0), (r * 0.6, 0.004), (r * 0.62, h * 0.4), (r * 0.98, h), (r, h * 0.95),
            (r * 0.96, h * 0.75), (r * 0.62, h * 0.55), (0.0, h * 0.55)]
    B.add(key, lathe(prof, segs, sharp=50), M)


def tray(B, M, key, w=0.45, d=0.30, h=0.035, rim=0.008, r=0.03, segs=3, floor=0.006):
    """Rounded-rectangle tray with a raised rim (bottom open: it lies on a surface)."""
    rings = [[(x, y, 0.0) for x, y in rrect(w, d, r, segs)],
             [(x, y, h) for x, y in rrect(w, d, r, segs)],
             [(x, y, h) for x, y in rrect(w - 2 * rim, d - 2 * rim, max(r - rim, 0.004), segs)],
             [(x, y, floor) for x, y in rrect(w - 2 * rim, d - 2 * rim, max(r - rim, 0.004), segs)]]
    bm = loft(rings, cap_top=True, smooth=False)
    B.add(key, bm, M)


def walnut_box(B, M, w=0.20, d=0.13, h=0.07, key="walnut"):
    """Lidded box: body and a lid with a 2 mm shadow line."""
    B.add(key, box((w, d, h * 0.72), (0, 0, h * 0.36), ("-z",), chamfer=0.002), M)
    B.add(key, box((w, d, h * 0.26), (0, 0, h * 0.74 + 0.002), chamfer=0.003), M)
    B.add("black", box((w - 0.006, d - 0.006, 0.004), (0, 0, h * 0.72 + 0.001), ("-z", "+z")), M)


def candle(B, M, r=0.035, h=0.09, holder="charcoal", jar=True):
    """Scented candle in a glazed jar (or a pillar on a bronze dish): wax surface below the rim, wick."""
    if jar:
        outer = [(r * 0.92, 0.0), (r, 0.01), (r, h)]
        B.add(holder, lathe(open_vessel(outer, wall=0.004, floor=0.01, per=1), 16), M)
        B.add("candle", lathe([(0.0, h - 0.018), (r - 0.004, h - 0.016), (r - 0.004, h - 0.022)], 16), M)
        B.add("black", box((0.002, 0.002, 0.008), (0, 0, h - 0.013)), M)
    else:
        B.add(holder, lathe([(0.0, 0.0), (r * 1.6, 0.0), (r * 1.7, 0.008), (r * 1.6, 0.01), (0.0, 0.01)], 16, sharp=50), M)
        B.add("candle", lathe([(r, 0.01), (r, 0.01 + h), (r * 0.85, 0.01 + h - 0.002), (0.0, 0.01 + h - 0.006)], 14), M)
        B.add("black", box((0.002, 0.002, 0.01), (0, 0, 0.01 + h - 0.002)), M)


def cup(B, M, key="porcelain", coffee=True, saucer=True):
    """Coffee cup on a saucer, handle to +x."""
    z0 = 0.0
    if saucer:
        plate(B, M, key, r=0.072, h=0.013, segs=16)
        z0 = 0.007
    outer = [(0.022, 0.0), (0.03, 0.008), (0.040, 0.035), (0.043, 0.062)]
    B.add(key, lathe(open_vessel(outer, wall=0.003, floor=0.008, per=1), 14), M @ at(0, 0, z0))
    hp = [(0.040, 0, 0.05), (0.056, 0, 0.049), (0.062, 0, 0.036), (0.052, 0, 0.022), (0.036, 0, 0.018)]
    B.add(key, tube([(x, y, z + z0) for x, y, z in hp], 0.004, sides=5, cap=False), M)
    if coffee:
        B.add("charcoal", lathe([(0.0, 0.050), (0.0385, 0.050)], 14), M @ at(0, 0, z0))


def tumbler(B, M, r=0.036, h=0.09, key="glass", liquid=None):
    outer = [(r * 0.94, 0.0), (r, 0.004), (r, h)]
    B.add(key, lathe(open_vessel(outer, wall=0.0025, floor=0.014, per=1, lip=False), 14), M)
    if liquid:
        B.add(liquid, lathe([(0.0, h * 0.45), (r - 0.003, h * 0.45)], 14), M)


def carafe(B, M, h=0.26, r=0.06, key="glass"):
    outer = [(r * 0.8, 0.0), (r * 0.98, 0.02), (r, h * 0.42), (r * 0.62, h * 0.68), (r * 0.34, h * 0.8),
             (r * 0.32, h * 0.97), (r * 0.36, h)]
    B.add(key, lathe(open_vessel(outer, wall=0.003, floor=0.012, per=2), 16), M)


def decanter(B, M, h=0.22, r=0.055, key="glass"):
    """Square-shouldered whisky decanter with a ball stopper."""
    outer = [(r * 0.95, 0.0), (r, 0.01), (r, h * 0.62), (r * 0.6, h * 0.74), (r * 0.3, h * 0.8), (r * 0.3, h * 0.9)]
    B.add(key, lathe(open_vessel(outer, wall=0.004, floor=0.02, per=1), 8, sharp=30, phase=0.5), M)
    B.add(key, ellipsoid(r * 0.42, r * 0.42, r * 0.42, 10, 6, z0=h * 0.9 + r * 0.38), M)


def magazine(B, M, rnd, w=0.215, d=0.28, t=0.006, palette="all"):
    """A magazine: a thin book with a soft cover (paper block shows on three sides)."""
    book(B, M, d, w, t, rnd, palette, hide_bottom=True)


def fanned(B, M, rnd, n=3, palette="all", step=(0.035, 0.025), turn=9.0):
    for i in range(n):
        magazine(B, M @ at(step[0] * i, step[1] * i, 0.0062 * i, turn * i), rnd, palette=palette)
    return 0.0062 * n


def open_book(B, M, rnd, L=0.24, D=0.17, T=0.022, palette="neutral"):
    """An open book face up: two page blocks rising toward the gutter on an opened cover."""
    cell = rnd.choice(PALETTES[palette])
    # opened cover: a flat board D*2 + spine wide
    col, row, cy0, cy1 = MODERN_CELLS[cell]
    px, py = col * CELL_W, row * CELL_H
    cu = ((px + 16) / ATLAS_N, (px + 48) / ATLAS_N)
    cv = (1 - (py + cy1) / ATLAS_N, 1 - (py + cy0) / ATLAS_N)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    W = 2 * D + 0.01
    cov = box((W, L, 0.0028), (0, 0, 0.0014), ("-z",))
    _merge(bm, cov)
    for f in bm.faces:
        _uv_rect(f, uvl, (0, 1), (-W / 2, -L / 2), (W / 2, L / 2), cu, cv)
    B.add("spines", bm, M)
    # page blocks: each slopes from the outer edge (h0) up to the gutter (h1) then dips
    pv = 1 - (PAPER_Y0 + rnd.uniform(30, 150)) / ATLAS_N
    for s in (-1, 1):
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("UVMap")
        h0, h1 = 0.0028 + T * 0.35, 0.0028 + T * 0.5
        xs = [s * (D - 0.002), s * D * 0.55, s * 0.012, s * 0.002]
        zs = [h0, h0 + (h1 - h0) * 0.7, h1, h1 - 0.006]
        top = []
        for x, z in zip(xs, zs):
            top.append((bm.verts.new((x, -L / 2 + 0.004, z)), bm.verts.new((x, L / 2 - 0.004, z))))
        bot = [(bm.verts.new((x, -L / 2 + 0.004, 0.0028)), bm.verts.new((x, L / 2 - 0.004, 0.0028))) for x in xs]
        faces = []
        for i in range(len(xs) - 1):
            a, b = top[i], top[i + 1]
            faces.append(("top", bm.faces.new((a[0], b[0], b[1], a[1]) if s > 0 else (b[0], a[0], a[1], b[1]))))
            # front / back edges of the block
            faces.append(("edge", bm.faces.new((bot[i][0], bot[i + 1][0], top[i + 1][0], top[i][0]))))
            faces.append(("edge", bm.faces.new((bot[i + 1][1], bot[i][1], top[i][1], top[i + 1][1]))))
        faces.append(("edge", bm.faces.new((bot[0][1], bot[0][0], top[0][0], top[0][1]))))
        for kind, f in faces:
            f.smooth = kind == "top"
            for lp in f.loops:
                co = lp.vert.co
                if kind == "top":   # text-like lines run across the page
                    lp[uvl].uv = (0.1 + abs(co.x) / 0.4 * 0.5, pv + co.y * 0.35)
                else:
                    lp[uvl].uv = (0.1 + (co.x + co.y) * 0.3, pv - co.z * 1.6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        B.add("spines", bm, M)


def glasses(B, M):
    """Folded reading glasses lying on a surface: two round lenses, bridge, folded temples."""
    rl, sides = 0.024, 10
    for s in (-1, 1):
        cx = s * 0.032
        ring = [(cx + rl * math.cos(2 * math.pi * k / sides), 0.0, 0.012 + rl * 0.85 * math.sin(2 * math.pi * k / sides))
                for k in range(sides + 1)]
        B.add("black", tube(ring, 0.0018, sides=4, cap=False), M @ at(0, 0, 0, 0, tilt=(-70, "X")))
        lens = lathe([(0.0, 0.0), (rl, 0.0)], sides)
        for v in lens.verts:
            v.co.y = v.co.y * 0.85
        B.add("glass", lens, M @ at(cx, 0, 0.012, 0, tilt=(20, "X")))
        # temple folded back behind the lenses
        B.add("black", tube([(s * 0.056, 0.0, 0.004), (s * 0.05, 0.03, 0.003), (-s * 0.02, 0.034, 0.003)], 0.0015,
                            sides=4, cap=False), M)
    B.add("black", tube([(-0.009, -0.002, 0.016), (0.0, -0.004, 0.019), (0.009, -0.002, 0.016)], 0.0016, sides=4, cap=False), M)


def sphere_on_block(B, M, r=0.05, block=0.07, top="bronze", base="marble"):
    B.add(base, box((block, block, block * 0.8), (0, 0, block * 0.4), ("-z",), chamfer=0.002), M)
    B.add(top, ellipsoid(r, r, r, 12, 8, z0=block * 0.8 + r * 0.97), M)


def cairn(B, M, rnd, keys=("charcoal", "stoneware", "charcoal"), r=0.06):
    """Three balanced stones, shrinking upward."""
    z = 0.0
    for i, k in enumerate(keys):
        rr = r * (1 - 0.22 * i) * rnd.uniform(0.92, 1.05)
        rz = rr * rnd.uniform(0.42, 0.55)
        B.add(k, ellipsoid(rr, rr * rnd.uniform(0.82, 0.95), rz, 12, 6, squash=0.25),
              M @ at(rnd.uniform(-0.004, 0.004), 0, z, rnd.uniform(0, 180)))
        z += rz * 2 * 0.86
    return z


def ring_sculpture(B, M, R=0.09, r=0.012, base="marble", key="bronze_polished"):
    """A bronze ring standing on a small stone base."""
    B.add(base, box((0.10, 0.06, 0.03), (0, 0, 0.015), ("-z",), chamfer=0.002), M)
    pts = [(R * math.sin(2 * math.pi * k / 24), 0.0, 0.03 + R + R * -math.cos(2 * math.pi * k / 24) * 0.98) for k in range(25)]
    B.add(key, tube(pts, r, sides=8, cap=False), M)


def lemons(B, M, rnd, n=5, r=0.034, spread=0.06):
    for i in range(n):
        a = 2 * math.pi * i / max(n - 1, 1) + rnd.uniform(-0.3, 0.3)
        rr = 0 if i == n - 1 else spread * rnd.uniform(0.8, 1.0)
        z = 0.0 if i < n - 1 else r * 1.1
        e = ellipsoid(r * 1.25, r, r, 10, 6)
        B.add("lemon", e, M @ at(rr * math.cos(a), rr * math.sin(a), z, rnd.uniform(0, 180), tilt=(rnd.uniform(-15, 15), "X")))


def small_plant(B, M, rnd, pot_r=0.065, pot_h=0.09, pot="stoneware", leaves=16, spread=0.16, trail=0.0):
    """A small potted plant for a shelf or counter: a glazed pot, soil, glossy leaves on short stems."""
    outer = [(pot_r * 0.8, 0.0), (pot_r * 0.86, 0.005), (pot_r, pot_h * 0.5), (pot_r * 1.02, pot_h)]
    B.add(pot, lathe(open_vessel(outer, wall=0.006, floor=0.012, per=1), 16), M)
    B.add("soil", lathe([(0.0, pot_h - 0.012), (pot_r - 0.005, pot_h - 0.015)], 12), M)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    for i in range(leaves):
        phi = i * 2.399963 + rnd.uniform(-0.3, 0.3)
        d = Vector((math.cos(phi), math.sin(phi), 0))
        side = Vector((-math.sin(phi), math.cos(phi), 0))
        f = (i + 0.5) / leaves
        reach = spread * (0.25 + 0.75 * f ** 0.6) * rnd.uniform(0.75, 1.1)
        rise = 0.05 + 0.12 * (1 - f) * rnd.uniform(0.6, 1.0)
        if trail and i % 3 == 0:
            rise = -trail * rnd.uniform(0.5, 1.0)
            reach = pot_r + 0.03
        base = Vector((0, 0, pot_h - 0.01))
        stem_end = base + d * reach * 0.6 + Vector((0, 0, rise))
        # petiole as a ribbon
        pv = [bm.verts.new(base + side * o) for o in (-0.002, 0.002)] + \
             [bm.verts.new(stem_end + side * o) for o in (0.002, -0.002)]
        fc = bm.faces.new(pv)
        for lp, uv in zip(fc.loops, ((0.5, 0.0), (0.52, 0.0), (0.52, 0.04), (0.5, 0.04))):
            lp[uvl].uv = uv
        L = rnd.uniform(0.07, 0.11)
        Wd = L * rnd.uniform(0.5, 0.65)
        pitch = math.radians(rnd.uniform(-10, 35) if rise > 0 else rnd.uniform(-70, -40))
        rows = 3
        grid = []
        for r in range(rows + 1):
            t = r / rows
            half = Wd * (0.35, 0.5, 0.38, 0.0)[r]
            c = stem_end + d * (math.cos(pitch) * L * t) + Vector((0, 0, math.sin(pitch) * L * t - 0.015 * t * t))
            fold = 0.006 * math.sin(math.pi * t)
            grid.append([bm.verts.new(c - side * half - Vector((0, 0, fold))), bm.verts.new(c),
                         bm.verts.new(c + side * half - Vector((0, 0, fold)))])
        for r in range(rows):
            for cc in range(2):
                quad = [grid[r][cc], grid[r][cc + 1], grid[r + 1][cc + 1], grid[r + 1][cc]]
                uvs = [(cc * 0.5, r / rows), (cc * 0.5 + 0.5, r / rows), (cc * 0.5 + 0.5, (r + 1) / rows), (cc * 0.5, (r + 1) / rows)]
                if r == rows - 1:
                    quad = [quad[0], quad[1], grid[r + 1][1]] if cc == 0 else [quad[0], quad[1], grid[r + 1][1]]
                    uvs = [uvs[0], uvs[1], (0.5, 1.0)]
                try:
                    fc = bm.faces.new(quad)
                except ValueError:
                    continue
                fc.smooth = True
                for lp, uv in zip(fc.loops, uvs):
                    lp[uvl].uv = uv
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    B.add("leaf", bm, M)


def folded(B, M, key, w=0.42, d=0.30, layers=3, t=0.018, fold_side="-y", crown=0.004, cuts=3):
    """A folded textile (throw, towel): stacked soft layers, the fold edge rounded and slightly
    proud on one side, the layers' edges visibly offset. Bottom not modelled."""
    z = 0.0
    for i in range(layers):
        ww, dd = w - 0.004 * i, d - 0.006 * i
        bm = common.cushion_bmesh((ww, dd, t), cuts=cuts, edge=t * 0.48, crown={"+z": crown, "-y": 0.004, "+y": 0.002})
        for f in list(bm.faces):
            if f.normal.z < -0.9 and i == 0:
                bm.faces.remove(f)
        bmesh.ops.translate(bm, vec=Vector((0.0015 * (i % 2), -0.003 * i, z + t / 2)), verts=bm.verts)
        for f in bm.faces:
            f.smooth = True
        B.add(key, bm, M)
        z += t * 0.9
    return z


def throw_over(B, M, key, w=0.55, depth=0.47, drop_front=0.32, drop_back=0.18, t=0.012, rnd=None):
    """A throw folded lengthwise and laid over a bench end / back: lies on z=0 across `depth`
    (y) and hangs down both long sides (front -y by drop_front, back +y by drop_back)."""
    rnd = rnd or random.Random(4)
    rc = 0.02
    y0, y1 = -depth / 2, depth / 2
    sec = [(y0 - t / 2 - 0.004, -drop_front), (y0 - t / 2 - 0.003, -drop_front * 0.5), (y0 - t / 2, -rc)]
    for k in range(1, 3):
        a = math.pi / 2 * k / 3
        sec.append((y0 + rc - (rc + t / 2) * math.cos(a), -rc + (rc + t / 2) * math.sin(a)))
    sec += [(y0 + rc, t / 2), (0.0, t / 2 + 0.006), (y1 - rc, t / 2)]
    for k in range(1, 3):
        a = math.pi / 2 * k / 3
        sec.append((y1 - rc + (rc + t / 2) * math.sin(a), -rc + (rc + t / 2) * math.cos(a)))
    sec += [(y1 + t / 2, -rc), (y1 + t / 2 + 0.002, -drop_back)]
    m = 6
    rings = []
    for i, (y, z) in enumerate(sec):
        hang = max(0.0, -z - rc) / 0.3
        row = []
        for j in range(m + 1):
            v = j / m
            x = -w / 2 + w * v
            rip = 0.008 * hang * math.sin(v * math.pi * 3 + 1.3 * i)
            row.append((x, y + (rip if y < 0 else -rip), z))
        rings.append(row)
    bm = bmesh.new()
    V = [[bm.verts.new(p) for p in row] for row in rings]
    for a, b in zip(V, V[1:]):
        for j in range(m):
            f = bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
            f.smooth = True
    # give it thickness: solidify
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ret = bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=t)
    for f in bm.faces:
        f.smooth = True
    B.add(key, bm, M)


def with_base(B, module, M=None, **kw):
    """Preview only (`--set base=<asset>`): build the furniture the vignette sits on under the
    same root, so the preview sheet shows them together. Never used in the level."""
    mod = importlib.import_module(module)
    importlib.reload(mod)
    r, _ = mod.build(**kw)
    r.parent = B.root
    if M is not None:
        r.matrix_basis = M
    return r


def keys(B, M, key="steel"):
    """A ring of two keys lying flat."""
    ring = [(0.014 * math.cos(2 * math.pi * k / 10), 0.014 * math.sin(2 * math.pi * k / 10), 0.003) for k in range(11)]
    B.add(key, tube(ring, 0.0013, sides=3, cap=False), M)
    for a in (-20, 35):
        Mk = M @ at(0, 0, 0.0015, a)
        B.add(key, box((0.045, 0.011, 0.002), (0.038, 0, 0.001), ("-z",)), Mk)
        B.add(key, lathe([(0.0, 0.0), (0.011, 0.0), (0.011, 0.003), (0.0, 0.003)], 8, sharp=50), Mk @ at(0.012, 0, 0))


# ------------------------------------------------------------------ pickups
# the loose things a player expects to lift (lib/pickups.py has the rule): each call of these
# becomes its own pickup; books standing in a row stay part of the furniture
pickups.wrap(sys.modules[__name__], "meshes", items=dict(
    book="book", magazine="magazine", open_book="book", vase="vase", bowl="bowl", plate="plate",
    walnut_box="box", candle="candle", cup="cup", tumbler="glass", carafe="carafe", decanter="decanter",
    glasses="spectacles", sphere_on_block="ornament", cairn="ornament", ring_sculpture="ornament",
), fixed=("upright_row",))
