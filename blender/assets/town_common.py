"""Shared builders for the town kit (blender/assets/town_*.py). Not an asset.

Materials: the whole kit is ONE material, M_Town_Atlas (base colour = T_Town_Atlas, see
town_textures.py), plus M_Town_Glow (the same atlas as emission: neon, lamps, lit signs).
A part asks for a *surface*: a tiling region ("bb_white", "ledgestone", "seam_black", ...),
a cell region ("windows", "signs": explicit cell UVs) or a flat palette swatch ("trim",
"trim_black", "neon_red", ...). Tiling faces are split at every tile boundary of their
world-scale UVs, so each piece maps inside its region (that is what lets one atlas repeat).

UVs: on vertical faces u runs horizontally along the face and v = height, so siding,
battens, coursing and roof seams line up across walls, gables and openings; horizontal faces
u = x, v = y; roof slopes u along the eave, v up the slope.

Every building also gets explicit collider boxes (kit.collide), entrances, a `<Asset>_LOD1`
mesh (palette swatches only, about a quarter of the triangles or fewer, hidden in previews)
and a sidecar assets/models/<asset>.json; the same dict goes in the root's "town" custom
property (glTF extras, a JSON string). Coordinates there: Blender, metres, z up, asset-local,
front (street side) -Y, origin = floor centre at the front door's sill height.
"""
import json
import math
import os
import sys
from contextlib import contextmanager

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from lib import common  # noqa: E402
import town_textures as tt  # noqa: E402

PROJECT = tt.PROJECT
MODELS = os.path.join(PROJECT, "assets", "models")
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
EPS = 1e-5
GLOW = ("neon_", "lamp", "glow_")


def V(*a):
    return Vector(a)


# ===================================================================== materials

_mats = {}


def material(glow=False):
    key = "glow" if glow else "atlas"
    m = _mats.get(key)
    if m is not None and m.name in bpy.data.materials:
        return m
    img = bpy.data.images.load(tt.atlas_path(), check_existing=True)
    img.colorspace_settings.name = "sRGB"
    m = common.pbr_material("M_Town_Glow" if glow else "M_Town_Atlas", (1, 1, 1), roughness=0.75)
    common.set_base_color_map(m, img)
    if glow:
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        tex = next(n for n in m.node_tree.nodes if n.type == "TEX_IMAGE")
        m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 3.0
    _mats[key] = m
    return m


def kind(surf):
    if surf in tt.REGIONS:
        return tt.REGIONS[surf]["kind"]          # tile / cells / palette
    tt.swatch_index(surf)                         # raises for unknown names
    return "swatch"


def is_glow(surf):
    return surf.startswith(GLOW)


# ===================================================================== geometry helpers

def newell(pts):
    n = Vector((0, 0, 0))
    for i, a in enumerate(pts):
        b = pts[(i + 1) % len(pts)]
        n.x += (a.y - b.y) * (a.z + b.z)
        n.y += (a.z - b.z) * (a.x + b.x)
        n.z += (a.x - b.x) * (a.y + b.y)
    return n.normalized() if n.length > 1e-12 else Vector((0, 0, 1))


def auto_uv(pts, tile):
    n = newell(pts)
    if abs(n.z) > 0.97:
        t, b = X, Y
    else:
        t = Z.cross(n)
        t.normalize()
        b = n.cross(t)
    return [(p.dot(t) / tile, p.dot(b) / tile) for p in pts]


def _clip(poly, axis, val, keep_ge):
    """Sutherland-Hodgman on [(pos, uv)] against uv[axis] >= val (or <=)."""
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ia = (a[1][axis] >= val - EPS) if keep_ge else (a[1][axis] <= val + EPS)
        ib = (b[1][axis] >= val - EPS) if keep_ge else (b[1][axis] <= val + EPS)
        if ia:
            out.append(a)
        if ia != ib:
            da, db = a[1][axis] - val, b[1][axis] - val
            t = da / (da - db)
            pos = a[0].lerp(b[0], t)
            uv = (a[1][0] + (b[1][0] - a[1][0]) * t, a[1][1] + (b[1][1] - a[1][1]) * t)
            out.append((pos, uv))
    return out


class Part:
    """Faces in one surface. face() takes world points (through the part's transform)."""

    def __init__(self, kit, name, surf, glow=None):
        self.kit, self.name, self.surf = kit, name, surf
        self.kind = kind(surf)
        self.glow = is_glow(surf) if glow is None else glow
        self.tile = tt.REGIONS[surf]["tile"] if self.kind == "tile" else 1.0
        self.v, self.f, self.uv = [], [], []
        self.M = Matrix.Identity(4)

    @contextmanager
    def xf(self, m):
        old = self.M
        self.M = old @ m
        try:
            yield self
        finally:
            self.M = old

    def _emit(self, pts, uvs):
        base = len(self.v)
        self.v.extend(tuple(p) for p in pts)
        self.f.append(list(range(base, base + len(pts))))
        self.uv.append(uvs)

    def face(self, pts, uvs=None, toward=None, uv_offset=(0.0, 0.0)):
        """uvs: for cell surfaces, region-local [0, 1] UVs (cell_uv/sign_uv); for tiling
        surfaces, tile-unit UVs (default: world-scale auto UVs)."""
        P = [self.M @ Vector(p) for p in pts]
        if toward is not None and newell(P).dot(Vector(toward)) < 0:
            P = P[::-1]
            if uvs:
                uvs = uvs[::-1]
        if self.kind == "swatch" or self.kind == "palette":
            u = tt.swatch_uv(self.surf)
            self._emit(P, [u] * len(P))
            return self
        u0, v0, du, dv = tt.region_rect(self.surf)
        if self.kind == "cells":
            uvs = uvs or [(0, 0), (1, 0), (1, 1), (0, 1)][:len(P)]
            self._emit(P, [(u0 + a * du, v0 + b * dv) for a, b in uvs])
            return self
        uvs = uvs or auto_uv(P, self.tile)
        uvs = [(a + uv_offset[0], b + uv_offset[1]) for a, b in uvs]
        us = [a for a, _ in uvs]
        vs = [b for _, b in uvs]
        iu0, iu1 = math.floor(min(us) + EPS), math.ceil(max(us) - EPS)
        iv0, iv1 = math.floor(min(vs) + EPS), math.ceil(max(vs) - EPS)
        poly0 = list(zip(P, uvs))
        for iu in range(iu0, max(iu1, iu0 + 1)):
            pu = _clip(_clip(poly0, 0, iu, True), 0, iu + 1, False)
            if len(pu) < 3:
                continue
            for iv in range(iv0, max(iv1, iv0 + 1)):
                pc = _clip(_clip(pu, 1, iv, True), 1, iv + 1, False)
                if len(pc) < 3:
                    continue
                if newell([p for p, _ in pc]).length < 0.5:     # degenerate
                    continue
                area = 0.0
                for k in range(len(pc)):
                    a_, b_ = pc[k][1], pc[(k + 1) % len(pc)][1]
                    area += a_[0] * b_[1] - b_[0] * a_[1]
                if abs(area) < 1e-7:
                    continue
                self._emit([p for p, _ in pc],
                           [(u0 + min(max(a - iu, 0), 1) * du, v0 + min(max(b - iv, 0), 1) * dv) for _, (a, b) in pc])
        return self

    def tris(self):
        return sum(len(f) - 2 for f in self.f)

    # ---------------------------------------------------------- primitives
    def box(self, lo, hi, skip=""):
        """Axis-aligned box; skip any of b t f k l r (bottom, top, front -Y, back +Y, -X, +X)."""
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        F = {
            "b": [(x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0)],
            "t": [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
            "f": [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
            "k": [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)],
            "l": [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)],
            "r": [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
        }
        for k_, pts in F.items():
            if k_ not in skip:
                self.face(pts)
        return self

    def cbox(self, c, size, skip=""):
        c, s = Vector(c), Vector(size) / 2
        return self.box(c - s, c + s, skip)

    def beam(self, a, b, w, h, up=None, skip_ends=False):
        """Box along a->b, w across (horizontal), h in the plane with `up`."""
        a, b = Vector(a), Vector(b)
        d = b - a
        L = d.length
        if L < 1e-6:
            return self
        x = d / L
        upv = Vector(up) if up is not None else (Z if abs(x.dot(Z)) < 0.95 else Y)
        y = upv.cross(x).normalized()
        z = x.cross(y)
        m = Matrix((x, y, z)).transposed().to_4x4()
        m.translation = a
        with self.xf(m):
            self.box((0, -w / 2, -h / 2), (L, w / 2, h / 2), skip="lr" if skip_ends else "")
        return self

    def cyl(self, c, r, z0, z1, sides=8, caps="t", r1=None):
        """Vertical cylinder (or frustum, r1 at the top) at plan point c."""
        cx, cy = c[0], c[1]
        r1 = r if r1 is None else r1
        ring = [(math.cos(2 * math.pi * i / sides), math.sin(2 * math.pi * i / sides)) for i in range(sides)]
        circ = 2 * math.pi * max(r, r1)
        for i in range(sides):
            j = (i + 1) % sides
            (ca, sa), (cb, sb) = ring[i], ring[j]
            pts = [(cx + r * ca, cy + r * sa, z0), (cx + r * cb, cy + r * sb, z0),
                   (cx + r1 * cb, cy + r1 * sb, z1), (cx + r1 * ca, cy + r1 * sa, z1)]
            if self.kind == "tile":
                u0, u1 = circ * i / sides / self.tile, circ * (i + 1) / sides / self.tile
                self.face(pts, uvs=[(u0, z0 / self.tile), (u1, z0 / self.tile), (u1, z1 / self.tile), (u0, z1 / self.tile)])
            else:
                self.face(pts)
        if "t" in caps and r1 > 0:
            self.face([(cx + r1 * ca, cy + r1 * sa, z1) for ca, sa in ring])
        if "b" in caps:
            self.face([(cx + r * ca, cy + r * sa, z0) for ca, sa in ring[::-1]])
        return self

    def tube(self, a, b, r, sides=6, caps=False):
        """Cylinder along a->b, for pipes, rails, poles, neon tubes."""
        a, b = Vector(a), Vector(b)
        d = b - a
        L = d.length
        if L < 1e-6:
            return self
        x = d / L
        ref = Z if abs(x.dot(Z)) < 0.95 else X
        y = ref.cross(x).normalized()
        z = x.cross(y)
        ring = [(y * math.cos(2 * math.pi * i / sides) + z * math.sin(2 * math.pi * i / sides)) * r for i in range(sides)]
        for i in range(sides):
            o0, o1 = ring[i], ring[(i + 1) % sides]
            self.face([a + o0, a + o1, b + o1, b + o0], toward=(o0 + o1))
        if caps:
            self.face([a + o for o in ring], toward=-x)
            self.face([b + o for o in ring], toward=x)
        return self

    def polyline(self, pts, r, sides=5, closed=False):
        """Tubes along a polyline (neon script, rails); joints overlap slightly."""
        pts = [Vector(p) for p in pts]
        segs = list(zip(pts, pts[1:])) + ([(pts[-1], pts[0])] if closed else [])
        for a, b in segs:
            d = (b - a)
            if d.length < 1e-6:
                continue
            e = d.normalized() * r * 0.5
            self.tube(a - e, b + e, r, sides)
        return self

    def prism(self, poly, z0, z1, caps="t"):
        """Extrude a CCW plan polygon from z0 to z1."""
        n = len(poly)
        for i in range(n):
            a, b = poly[i], poly[(i + 1) % n]
            self.face([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)])
        if "t" in caps:
            self.face([(p[0], p[1], z1) for p in poly])
        if "b" in caps:
            self.face([(p[0], p[1], z0) for p in poly[::-1]])
        return self


class Kit:
    """Everything one building is made of."""

    def __init__(self, name, module=None):
        self.name = name
        self.module = module
        self.parts = {}
        self.colliders = []
        self.entrances = []
        self.info = {}

    def p(self, part, surf, glow=None):
        """Part `part` in surface `surf` (parts merge by name and material at finish)."""
        k = (part, surf, glow)
        if k not in self.parts:
            self.parts[k] = Part(self, part, surf, glow)
        return self.parts[k]

    def collide(self, lo, hi):
        self.colliders.append([round(c, 3) for c in (*lo, *hi)])

    def entrance(self, pos, facing, width, kind="door", note=""):
        self.entrances.append({"pos": [round(c, 3) for c in pos], "facing": facing, "width": round(width, 3),
                               "kind": kind, **({"note": note} if note else {})})

    def tris(self):
        return sum(p.tris() for p in self.parts.values())


def _mesh(name, faces_parts, col, parent, glow):
    verts, faces, uvs = [], [], []
    for pt in faces_parts:
        base = len(verts)
        verts.extend(pt.v)
        faces.extend([[i + base for i in f] for f in pt.f])
        uvs.extend(pt.uv)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    uvl = me.uv_layers.new(name="UVMap")
    for poly, uv in zip(me.polygons, uvs):
        for k in range(poly.loop_total):
            uvl.data[poly.loop_start + k].uv = uv[k]
    for poly in me.polygons:
        poly.use_smooth = False
    me.materials.append(material(glow))
    ob = bpy.data.objects.new(name, me)
    common.link(ob, col, parent)
    return ob


def objects(kit, col, parent, prefix=None):
    """The kit's parts as mesh objects, one per (part name, material)."""
    prefix = prefix or kit.name
    groups = {}
    for (part, surf, g), pt in kit.parts.items():
        if pt.f:
            groups.setdefault((part, pt.glow), []).append(pt)
    out = []
    for (part, glow), pts in groups.items():
        out.append(_mesh(f"{prefix}_{part}" + ("_Glow" if glow and not part.endswith("Glow") else ""), pts, col, parent, glow))
    return out


def finish(kit, col, root, far=None, extra_info=None):
    """Mesh objects under `root` (+ the LOD1 from `far`), the sidecar and root extras."""
    out = objects(kit, col, root)
    lo, hi = common.world_aabb(out)
    lod = None
    if far is not None and far.part.f:
        lod = _mesh(f"{kit.name}_LOD1", [far.part], col, root, False)
        lod.hide_render = True                    # (the preview shows LOD0)
        lod["lod"] = 1
    info = {
        "asset": kit.module or kit.name,
        "root": kit.name,
        "size": [round(hi[i] - lo[i], 3) for i in range(3)],
        "bounds": [[round(c, 3) for c in lo], [round(c, 3) for c in hi]],
        "below_m": round(max(0.0, -lo.z), 3),
        "tris_lod0": common.triangle_count(out),
        "tris_lod1": common.triangle_count([lod]) if lod else 0,
        "colliders": kit.colliders,
        "entrances": kit.entrances,
        "materials": sorted({m.name for o in out for m in o.data.materials}),
        **kit.info, **(extra_info or {}),
    }
    root["town"] = json.dumps(info)
    if kit.module:
        os.makedirs(MODELS, exist_ok=True)
        with open(os.path.join(MODELS, f"{kit.module}.json"), "w") as fh:
            json.dump(info, fh, indent=1)
    print(f"TOWN {kit.name}: LOD0 {info['tris_lod0']} tris, LOD1 {info['tris_lod1']}, "
          f"{len(kit.colliders)} colliders, size {info['size']}")
    return out + ([lod] if lod else [])


def begin(name, module=None):
    col = common.fresh_collection(name)
    root = common.empty(name, col)
    return col, root, Kit(name, module)


# ===================================================================== walls

def frame(side, plane):
    """(point fn P(a, z, d), u, n) for an axis-aligned wall: S (y=plane, out -Y, along +X),
    N (out +Y, along -X), E (x=plane, out +X, along +Y), W (out -X, along -Y). a = the world
    coordinate along the wall (x for S/N, y for E/W), d = offset along the outward normal."""
    if side == "S":
        return (lambda a, z, d=0.0: V(a, plane - d, z)), X, -Y
    if side == "N":
        return (lambda a, z, d=0.0: V(a, plane + d, z)), -X, Y
    if side == "E":
        return (lambda a, z, d=0.0: V(plane + d, a, z)), Y, X
    if side == "W":
        return (lambda a, z, d=0.0: V(plane - d, a, z)), -Y, -X
    raise ValueError(side)


def wall(part, side, plane, a0, a1, z0, z1, openings=(), gable=None, inward=False, d=0.0, apex_a=None):
    """A wall face with rectangular openings [(a0, a1, z0, z1)] (world coords along the
    wall); `gable` = apex z (at apex_a, default the middle) adds the triangle on top.
    inward=True faces the other way (an interior lining)."""
    P, u, n = frame(side, plane)
    lo, hi = min(a0, a1), max(a0, a1)
    As = sorted({lo, hi} | {c for o in openings for c in (o[0], o[1]) if lo < c < hi})
    Zs = sorted({z0, z1} | {c for o in openings for c in (o[2], o[3]) if z0 < c < z1})
    toward = (-n if inward else n)
    for i in range(len(As) - 1):
        for j in range(len(Zs) - 1):
            ma, mz = (As[i] + As[i + 1]) / 2, (Zs[j] + Zs[j + 1]) / 2
            if any(min(o[0], o[1]) < ma < max(o[0], o[1]) and o[2] < mz < o[3] for o in openings):
                continue
            part.face([P(As[i], Zs[j], d), P(As[i + 1], Zs[j], d), P(As[i + 1], Zs[j + 1], d), P(As[i], Zs[j + 1], d)],
                      toward=toward)
    if gable is not None:
        ap = (lo + hi) / 2 if apex_a is None else apex_a
        pts = [P(a, z1, d) for a in As] + [P(ap, gable, d)]
        part.face(pts, toward=toward)


def reveals(part, side, plane, openings, depth, d0=0.0, sill=True):
    """Jambs, head (and sill) of each opening, from offset d0 inward by `depth`."""
    P, u, n = frame(side, plane)
    for a0, a1, z0, z1 in openings:
        lo, hi = min(a0, a1), max(a0, a1)
        e0, e1 = d0, d0 - depth
        part.face([P(lo, z0, e0), P(lo, z0, e1), P(lo, z1, e1), P(lo, z1, e0)], toward=P(1, 0) - P(0, 0))
        part.face([P(hi, z0, e0), P(hi, z0, e1), P(hi, z1, e1), P(hi, z1, e0)], toward=P(0, 0) - P(1, 0))
        part.face([P(lo, z1, e0), P(hi, z1, e0), P(hi, z1, e1), P(lo, z1, e1)], toward=(0, 0, -1))
        if sill:
            part.face([P(lo, z0, e0), P(hi, z0, e0), P(hi, z0, e1), P(lo, z0, e1)], toward=(0, 0, 1))


def wbox(part, side, plane, a0, a1, z0, z1, d0, d1, skip=""):
    """A box in a wall's frame: along a0..a1, height z0..z1, offset d0..d1 (outward).
    skip may contain "back" (the face against the wall) plus box face letters."""
    P, u, n = frame(side, plane)
    p0, p1 = P(a0, z0, d0), P(a1, z1, d1)
    lo = V(min(p0.x, p1.x), min(p0.y, p1.y), min(p0.z, p1.z))
    hi = V(max(p0.x, p1.x), max(p0.y, p1.y), max(p0.z, p1.z))
    back = {"S": "k", "N": "f", "E": "l", "W": "r"}[side]
    part.box(lo, hi, skip.replace("back", back))


def wquad(part, side, plane, a0, a1, z0, z1, d, uvs=None, inward=False):
    P, u, n = frame(side, plane)
    part.face([P(a0, z0, d), P(a1, z0, d), P(a1, z1, d), P(a0, z1, d)], uvs=uvs, toward=(-n if inward else n))


def cell_uv(cell, n_cells=4, inset=0.004, sub=None):
    """Region-local UVs (bl, br, tr, tl) of window cell `cell` (0 = top-left, row-major).
    sub = (u0, v0, u1, v1) picks part of the cell (e.g. one pane)."""
    r, c = divmod(cell % (n_cells * n_cells), n_cells)
    u0, u1 = c / n_cells + inset, (c + 1) / n_cells - inset
    v1 = 1 - r / n_cells - inset
    v0 = 1 - (r + 1) / n_cells + inset
    if sub:
        a0, b0, a1, b1 = sub
        u0, u1, v0, v1 = u0 + (u1 - u0) * a0, u0 + (u1 - u0) * a1, v0 + (v1 - v0) * b0, v0 + (v1 - v0) * b1
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


def sign_uv(name, inset=0.004):
    """Region-local UVs of a sign cell (2 columns x 4 rows, 2:1 cells, 0 = top-left)."""
    cell = tt.SIGN_KINDS.index(name) if isinstance(name, str) else name
    r, c = divmod(cell, 2)
    u0, u1 = c / 2 + inset, (c + 1) / 2 - inset
    v1 = 1 - r / 4 - inset
    v0 = 1 - (r + 1) / 4 + inset
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]


WIN = {k: i for i, k in enumerate(tt.WINDOW_KINDS)}


# ===================================================================== windows and doors

def window(kit, side, plane, a, z, w, h, cell="dh_dark", trim="trim", boarded=False, depth=0.10, casing=0.09,
           proud=0.025, wall_part=None, sill=True, head=True):
    """A window centred at a (along the wall), sill at z, w x h opening: casing, sill, a
    recessed glass plane showing one window-atlas cell (frames painted in). ~40 tris."""
    a0, a1 = a - w / 2, a + w / 2
    z1 = z + h
    if wall_part is not None:
        reveals(wall_part, side, plane, [(a0, a1, z, z1)], depth, sill=False)
    T = kit.p("Trim", trim)
    if casing > 0:
        wbox(T, side, plane, a0 - casing, a0, z, z1, 0, proud, skip="back")
        wbox(T, side, plane, a1, a1 + casing, z, z1, 0, proud, skip="back")
        if head:
            wbox(T, side, plane, a0 - casing, a1 + casing, z1, z1 + casing * 1.2, 0, proud + 0.01, skip="back")
    if sill:
        wbox(T, side, plane, a0 - casing - 0.03, a1 + casing + 0.03, z - 0.045, z, -depth, proud + 0.045, skip="back")
    else:
        reveals(T, side, plane, [(a0, a1, z, z)], 0, sill=False)
        wquad(T, side, plane, a0, a1, z, z, 0)
    if boarded:
        wquad(kit.p("WindowDark", "glass_dark"), side, plane, a0, a1, z, z1, -depth)
        Wd = kit.p("Boards", "deck")
        nb = max(2, round(h / 0.22))
        for i in range(nb):
            zz = z + (i + 0.5) * h / nb
            tilt = 0.03 * ((i * 7919) % 5 - 2)
            wbox(Wd, side, plane, a0 - 0.08, a1 + 0.08, zz - 0.09 + tilt, zz + 0.09 + tilt, proud, proud + 0.022, skip="back")
        return
    c = WIN[cell] if isinstance(cell, str) else cell
    wquad(kit.p("Window", "windows"), side, plane, a0, a1, z, z1, -depth, uvs=cell_uv(c))


def glazing(kit, side, plane, a0, a1, z0, z1, cell="bk_dark", mullions=(), transom=None, depth=0.06, frame_w=0.05,
            frame="trim_black", wall_part=None, cells=None):
    """A modern storefront / window wall: black frame, mullions at the given a positions,
    an optional transom bar at z; each pane shows (a sub-rectangle of) a window cell."""
    if wall_part is not None:
        reveals(wall_part, side, plane, [(a0, a1, z0, z1)], depth, sill=True)
    F = kit.p("Frames", frame)
    xs = [a0] + sorted(mullions) + [a1]
    zs = [z0] + ([transom] if transom else []) + [z1]
    G = kit.p("Window", "windows")
    d = -depth
    k = 0
    for i in range(len(xs) - 1):
        for j in range(len(zs) - 1):
            cc = cells[k % len(cells)] if cells else cell
            k += 1
            c = WIN[cc] if isinstance(cc, str) else cc
            sub = (0.06, 0.06, 0.94, 0.94)          # inside the painted frame
            wquad(G, side, plane, xs[i], xs[i + 1], zs[j], zs[j + 1], d, uvs=cell_uv(c, sub=sub))
    for x in xs:
        wbox(F, side, plane, x - frame_w / 2, x + frame_w / 2, z0, z1, d, d + 0.06, skip="back")
    for z in zs:
        wbox(F, side, plane, a0, a1, z - frame_w / 2, z + frame_w / 2, d, d + 0.06, skip="back")


def door(kit, side, plane, a, w, h, z=0.0, leaf="door_wood", trim="trim", depth=0.10, casing=0.10, proud=0.025,
         wall_part=None, glass=None, boarded=False, style="panel"):
    """A closed door centred at a, threshold at z (solid shells). style: panel (four
    panels; glass = a window cell in the top pair), glass (full-lite black storefront door)."""
    a0, a1 = a - w / 2, a + w / 2
    z1 = z + h
    if wall_part is not None:
        reveals(wall_part, side, plane, [(a0, a1, z, z1)], depth, sill=False)
    T = kit.p("Trim", trim)
    if casing > 0:
        wbox(T, side, plane, a0 - casing, a0, z, z1, 0, proud, skip="back")
        wbox(T, side, plane, a1, a1 + casing, z, z1, 0, proud, skip="back")
        wbox(T, side, plane, a0 - casing, a1 + casing, z1, z1 + casing * 1.3, 0, proud + 0.01, skip="back")
    wbox(kit.p("Sill", "stone"), side, plane, a0 - 0.02, a1 + 0.02, max(0.0, z - 0.03), z + 0.015, -depth, proud + 0.02, skip="back")
    if boarded:
        Wd = kit.p("Boards", "deck")
        wbox(Wd, side, plane, a0, a1, z, z1, -depth, -depth + 0.03, skip="back")
        for zz, t in ((z + 0.4, 0.02), (z + 1.1, -0.03), (z + 1.75, 0.01)):
            wbox(Wd, side, plane, a0 - 0.12, a1 + 0.12, zz - 0.1 + t, zz + 0.1 - t, proud, proud + 0.022, skip="back")
        return
    L = kit.p("Door", leaf)
    dl = -depth + 0.045
    wbox(L, side, plane, a0, a1, z, z1, -depth, dl, skip="back")
    if style == "glass":
        wquad(kit.p("Window", "windows"), side, plane, a0 + 0.1, a1 - 0.1, z + 0.25, z1 - 0.12, dl + 0.002,
              uvs=cell_uv(WIN[glass or "bk_dark"], sub=(0.06, 0.06, 0.94, 0.94)))
        wbox(kit.p("Knob", "chrome"), side, plane, a1 - 0.14, a1 - 0.1, z + 0.75, z + 1.35, dl, dl + 0.06, skip="back")
        return
    pw = (w - 0.3) / 2
    for i, (pz0, pz1) in enumerate(((z + 0.15, z + 0.95), (z + 1.1, z1 - 0.15))):
        for k_ in range(2):
            pa = a0 + 0.1 + k_ * (pw + 0.1)
            if glass and i == 1:
                wquad(kit.p("Window", "windows"), side, plane, pa, pa + pw, pz0, pz1, dl + 0.002,
                      uvs=cell_uv(WIN[glass], sub=(0.1, 0.1, 0.9, 0.9)))
            else:
                wbox(L, side, plane, pa, pa + pw, pz0, pz1, dl, dl + 0.012, skip="back")
    wbox(kit.p("Knob", "brass"), side, plane, a1 - 0.1, a1 - 0.05, z + 0.95, z + 1.0, dl, dl + 0.06, skip="back")


def hinged_door(kit, col, root, side, plane, a, w, h, z=0.0, depth=0.10, leaf="door_wood", index=None,
                style="panel", glass=None, swing=1, prompt="Open door", wall_thick=None):
    """A walk-in door: the leaf is its own object under an empty `<Asset>_Door[_n]` at the
    hinge (low-a jamb) with a `rotate` interact (inert in the wild runtime, read later by
    interactables). swing=+1 opens inwards. Returns the hinge empty."""
    P, u, n = frame(side, plane)
    a0 = a - w / 2
    hp = P(a0, z, -depth)
    nm = f"{kit.name}_Door" + (f"_{index}" if index is not None else "")
    hinge = common.empty(nm, col, hp)
    hinge.parent = root
    # the angle sign that turns the leaf inwards (about +Z) for each wall side
    inward = {"S": -1, "E": -1, "N": -1, "W": -1}[side]
    hinge["interact"] = {"type": "rotate", "axis": common.to_gltf((0, 0, 1)), "angle": 95 * inward * swing,
                         "duration": 0.9, "range": 1.8, "side": "both", "collide": True,
                         "prompt": prompt, "promptActive": "Close door"}
    lk = Kit(nm)
    L = lk.p("Leaf", leaf)
    t = 0.045
    with L.xf(Matrix.Translation(-hp)):
        wbox(L, side, plane, a0 + 0.005, a0 + w - 0.005, z + 0.01, z + h - 0.005, -depth - t, -depth)
        if style == "glass":
            wquad(lk.p("Glass", "windows"), side, plane, a0 + 0.1, a0 + w - 0.1, z + 0.25, z + h - 0.12, -depth + 0.002,
                  uvs=cell_uv(WIN[glass or "bk_dark"], sub=(0.06, 0.06, 0.94, 0.94)))
            wquad(lk.p("Glass", "windows"), side, plane, a0 + 0.1, a0 + w - 0.1, z + 0.25, z + h - 0.12, -depth - t - 0.002,
                  uvs=cell_uv(WIN[glass or "bk_dark"], sub=(0.06, 0.06, 0.94, 0.94)), inward=True)
        else:
            pw = (w - 0.3) / 2
            for pz0, pz1 in ((z + 0.15, z + 0.95), (z + 1.1, z + h - 0.15)):
                for k_ in range(2):
                    pa = a0 + 0.1 + k_ * (pw + 0.1)
                    wbox(L, side, plane, pa, pa + pw, pz0, pz1, -depth, -depth + 0.012, skip="back")
        K = lk.p("Knob", "brass" if style != "glass" else "chrome")
        wbox(K, side, plane, a0 + w - 0.1, a0 + w - 0.05, z + 0.95, z + 1.0, -depth, -depth + 0.06, skip="back")
        wbox(K, side, plane, a0 + w - 0.1, a0 + w - 0.05, z + 0.95, z + 1.0, -depth - t - 0.06, -depth - t)
    objects(lk, col, hinge, prefix=nm)
    return hinge


# ===================================================================== roofs

def gable_roof(kit, x0, x1, y0, y1, z_eave, pitch, axis="y", over_eave=0.35, over_gable=0.25, thick=0.14,
               roof="seam_black", soffit="trim", fascia="trim", ridge_cap=True, collide=True):
    """Gable roof over the wall rect; ridge along `axis`. z_eave = top of the wall plate at the
    wall line. Returns the ridge height (top surface)."""
    R = kit.p("Roof", roof)
    S = kit.p("Soffit", soffit)
    F = kit.p("Fascia", fascia)
    if axis == "y":
        s, c = (x1 - x0) / 2, (x0 + x1) / 2
        A0, A1 = y0 - over_gable, y1 + over_gable

        def pt(across, along, z):
            return V(c + across, along, z)
    else:
        s, c = (y1 - y0) / 2, (y0 + y1) / 2
        A0, A1 = x0 - over_gable, x1 + over_gable

        def pt(across, along, z):
            return V(along, c + across, z)
    tv = thick * math.sqrt(1 + pitch * pitch)
    zr_top = z_eave + s * pitch + tv
    e = s + over_eave
    ze_top = z_eave + tv - over_eave * pitch
    ze_bot, zr_bot = ze_top - tv, zr_top - tv
    for sgn in (-1, 1):
        out = pt(sgn, 0, 0) - pt(0, 0, 0)
        nrm = out * pitch + Z
        R.face([pt(sgn * e, A0, ze_top), pt(sgn * e, A1, ze_top), pt(0, A1, zr_top), pt(0, A0, zr_top)], toward=nrm)
        S.face([pt(sgn * e, A0, ze_bot), pt(sgn * e, A1, ze_bot), pt(0, A1, zr_bot), pt(0, A0, zr_bot)], toward=-nrm)
        F.face([pt(sgn * e, A0, ze_bot), pt(sgn * e, A1, ze_bot), pt(sgn * e, A1, ze_top), pt(sgn * e, A0, ze_top)], toward=out)
        for A, dirv in ((A0, -1), (A1, 1)):
            along = (pt(0, 1, 0) - pt(0, 0, 0)) * dirv
            F.face([pt(sgn * e, A, ze_bot), pt(sgn * e, A, ze_top), pt(0, A, zr_top), pt(0, A, zr_bot)], toward=along)
    if ridge_cap:
        kit.p("Ridge", fascia if roof.startswith("seam") else roof).beam(pt(0, A0, zr_top), pt(0, A1, zr_top), 0.2, 0.05)
    if collide:
        lo, hi = pt(-e, A0, z_eave), pt(e, A1, zr_top)
        kit.collide((min(lo.x, hi.x), min(lo.y, hi.y), z_eave), (max(lo.x, hi.x), max(lo.y, hi.y), zr_top))
    return zr_top


def shed_roof(kit, x0, x1, y_high, y_low, z_high, z_low, over_side=0.15, over_low=0.25, thick=0.10,
              roof="seam_black", soffit="trim", fascia="trim"):
    """Single slope from (y_high, z_high) down to (y_low, z_low) across x0..x1."""
    R, S, F = kit.p("Roof", roof), kit.p("Soffit", soffit), kit.p("Fascia", fascia)
    dy = y_low - y_high
    slope = (z_high - z_low) / abs(dy)
    sg = 1 if dy > 0 else -1
    yl = y_low + sg * over_low
    zl = z_low - over_low * slope
    xa, xb = x0 - over_side, x1 + over_side
    top = [V(xa, y_high, z_high + thick), V(xb, y_high, z_high + thick), V(xb, yl, zl + thick), V(xa, yl, zl + thick)]
    bot = [V(xa, y_high, z_high), V(xb, y_high, z_high), V(xb, yl, zl), V(xa, yl, zl)]
    R.face(top, toward=(0, sg * slope, 1))
    S.face(bot, toward=(0, -sg * slope, -1))
    F.face([bot[3], bot[2], top[2], top[3]], toward=(0, sg, 0))
    F.face([bot[0], bot[3], top[3], top[0]], toward=(-1, 0, 0))
    F.face([bot[2], bot[1], top[1], top[2]], toward=(1, 0, 0))


def hip_roof(kit, x0, x1, y0, y1, z_eave, pitch, over=0.4, thick=0.14, roof="shingle", soffit="trim",
             fascia="trim", collide=True):
    """Hip roof (equal pitch all round) over the wall rect. Returns the ridge height."""
    R, S, F = kit.p("Roof", roof), kit.p("Soffit", soffit), kit.p("Fascia", fascia)
    tv = thick * math.sqrt(1 + pitch * pitch)
    X0, X1, Y0, Y1 = x0 - over, x1 + over, y0 - over, y1 + over
    ze = z_eave + tv - over * pitch
    W, D = X1 - X0, Y1 - Y0
    h = min(W, D) / 2
    zr = ze + h * pitch
    cx, cy = (X0 + X1) / 2, (Y0 + Y1) / 2
    r0, r1 = (V(X0 + h, cy, zr), V(X1 - h, cy, zr)) if W >= D else (V(cx, Y0 + h, zr), V(cx, Y1 - h, zr))
    c00, c10, c11, c01 = V(X0, Y0, ze), V(X1, Y0, ze), V(X1, Y1, ze), V(X0, Y1, ze)
    if W >= D:
        R.face([c00, c10, r1, r0], toward=(0, -1, 1))
        R.face([c11, c01, r0, r1], toward=(0, 1, 1))
        R.face([c01, c00, r0], toward=(-1, 0, 1))
        R.face([c10, c11, r1], toward=(1, 0, 1))
    else:
        R.face([c10, c11, r1, r0], toward=(1, 0, 1))
        R.face([c01, c00, r0, r1], toward=(-1, 0, 1))
        R.face([c00, c10, r0], toward=(0, -1, 1))
        R.face([c11, c01, r1], toward=(0, 1, 1))
    zb = ze - tv
    S.face([V(X0, Y0, zb), V(X1, Y0, zb), V(X1, Y1, zb), V(X0, Y1, zb)], toward=(0, 0, -1))
    for a, b, o in (((X0, Y0), (X1, Y0), (0, -1, 0)), ((X1, Y0), (X1, Y1), (1, 0, 0)),
                    ((X1, Y1), (X0, Y1), (0, 1, 0)), ((X0, Y1), (X0, Y0), (-1, 0, 0))):
        F.face([V(a[0], a[1], zb), V(b[0], b[1], zb), V(b[0], b[1], ze), V(a[0], a[1], ze)], toward=o)
    if collide:
        kit.collide((X0, Y0, z_eave), (X1, Y1, zr))
    return zr


def flat_roof(kit, x0, x1, y0, y1, z, parapet=0.6, wall="brick_red", coping="stone", t=0.25, deck="tar",
              sides="SNEW", collide=True):
    """A flat roof deck at z with parapet walls (outer faces in `wall`) and a coping."""
    kit.p("RoofDeck", deck).face([V(x0 + t, y0 + t, z), V(x1 - t, y0 + t, z), V(x1 - t, y1 - t, z), V(x0 + t, y1 - t, z)],
                                 toward=(0, 0, 1))
    W = kit.p("Parapet", wall)
    C = kit.p("Coping", coping)
    zt = z + parapet
    for side, plane, a0, a1 in (("S", y0, x0, x1), ("N", y1, x0, x1), ("E", x1, y0, y1), ("W", x0, y0, y1)):
        if side not in sides:
            continue
        P, u, n = frame(side, plane)
        wall(W, side, plane, a0 + (0.0 if side in "SN" else t), a1 - (0.0 if side in "SN" else t), z - 0.3, zt, d=0.0)
        wall(W, side, plane, a0 + t, a1 - t, z, zt, d=-t, inward=True)
        wbox(C, side, plane, a0 - 0.03, a1 + 0.03, zt, zt + 0.08, -t - 0.02, 0.04)
    if collide:
        kit.collide((x0, y0, z - 0.3), (x1, y1, zt + 0.08))


# ===================================================================== porches, steps, rails

def steps(kit, x0, x1, y_top, z_top, n=None, run=0.3, direction=-1, mat="concrete", stringer=None, collide=True,
          z_bottom=0.0):
    """Steps down from (y_top, z_top) to z_bottom toward `direction` (-1 = -Y). Returns the
    foot's y."""
    n = n or max(1, round((z_top - z_bottom) / 0.18))
    rise = (z_top - z_bottom) / n
    T = kit.p("Steps", mat)
    for i in range(n):
        zt = z_top - i * rise
        ya, yb = y_top + direction * i * run, y_top + direction * (i + 1) * run
        T.box((x0, min(ya, yb), zt - rise if i < n - 1 else z_bottom), (x1, max(ya, yb), zt), skip="b")
        if collide:
            kit.collide((x0, min(ya, yb), z_bottom), (x1, max(ya, yb), zt))
    if stringer:
        St = kit.p("Stringer", stringer)
        y_end = y_top + direction * n * run
        for x in (x0 - 0.04, x1):
            for xx, o in ((x, -1), (x + 0.04, 1)):
                St.face([V(xx, y_top, z_top - rise), V(xx, y_end, z_bottom), V(xx, y_end, z_bottom + rise * 0.3),
                         V(xx, y_top, z_top)], toward=(o, 0, 0))
    return y_top + direction * n * run


def railing(kit, a, b, z, h=0.95, spacing=0.12, mat="trim_black", style="bars", collide=True):
    """A rail a->b (plan points) on a deck at z. style bars (square balusters), cable
    (modern horizontal cables), solid (a panel)."""
    a, b = Vector((a[0], a[1], z)), Vector((b[0], b[1], z))
    R = kit.p("Railing", mat)
    R.beam(a + V(0, 0, h - 0.03), b + V(0, 0, h - 0.03), 0.07, 0.05)
    L = (b - a).length
    d = (b - a) / max(L, 1e-6)
    if style == "bars":
        R.beam(a + V(0, 0, 0.1), b + V(0, 0, 0.1), 0.05, 0.04)
        n = max(1, int(L / spacing))
        for i in range(1, n):
            p = a + d * (i * L / n)
            R.box((p.x - 0.012, p.y - 0.012, z + 0.12), (p.x + 0.012, p.y + 0.012, z + h - 0.055), skip="tb")
    elif style == "cable":
        for k in range(6):
            R.beam(a + V(0, 0, 0.12 + k * 0.14), b + V(0, 0, 0.12 + k * 0.14), 0.008, 0.008)
        n = max(1, int(L / 1.5))
        for i in range(n + 1):
            p = a + d * (i * L / n)
            R.box((p.x - 0.03, p.y - 0.03, z), (p.x + 0.03, p.y + 0.03, z + h - 0.03), skip="b")
    if collide:
        side = Vector((-d.y, d.x, 0)) * 0.05
        lo = Vector(map(min, a - side, b + side))
        hi = Vector(map(max, a - side, b + side))
        kit.collide((lo.x, lo.y, z), (hi.x, hi.y, z + h))


def porch(kit, x0, x1, y_wall, depth, z_deck, z_roof_wall, posts=4, roof="seam_black", rail=True, steps_at=None,
          step_w=1.2, deck="deck", trim="trim", post_w=0.14, z_roof_low=None, rail_style="bars", rail_mat=None,
          post_mat=None, ribbon=False):
    """A porch on the -Y side of a wall at y_wall: deck at z_deck, a shed roof from the wall
    down over the posts; steps_at = the steps' centre x (None: no steps)."""
    y_out = y_wall - depth
    kit.p("Deck", deck).box((x0, y_out, z_deck - 0.06), (x1, y_wall, z_deck), skip="bk")
    T = kit.p("Trim", trim)
    if z_deck > 0.1:
        T.box((x0 - 0.02, y_out - 0.03, max(0.0, z_deck - 0.3)), (x1 + 0.02, y_out, z_deck - 0.02), skip="bk")
        kit.p("Underside", "shade").face([V(x0, y_out, 0.0), V(x1, y_out, 0.0), V(x1, y_out, z_deck - 0.3),
                                          V(x0, y_out, z_deck - 0.3)], toward=(0, -1, 0))
    kit.collide((x0, y_out, 0), (x1, y_wall, z_deck))
    z_low = z_roof_low if z_roof_low is not None else z_roof_wall - depth * 0.25
    xs = [x0 + 0.12 + (x1 - x0 - 0.24) * i / (posts - 1) for i in range(posts)]
    Pp = kit.p("Posts", post_mat or trim)
    for x in xs:
        Pp.box((x - post_w / 2, y_out + 0.08, z_deck), (x + post_w / 2, y_out + 0.08 + post_w, z_low - 0.2), skip="bt")
        kit.collide((x - post_w / 2, y_out + 0.08, z_deck), (x + post_w / 2, y_out + 0.08 + post_w, z_low - 0.2))
    T.box((x0 + 0.02, y_out + 0.06, z_low - 0.22), (x1 - 0.02, y_out + 0.1 + post_w, z_low))
    shed_roof(kit, x0, x1, y_wall, y_out + 0.08, z_roof_wall, z_low, roof=roof, soffit=trim, fascia=trim)
    if rail:
        yr = y_out + 0.08 + post_w / 2
        gap = (steps_at - step_w / 2, steps_at + step_w / 2) if steps_at is not None else None
        for i in range(len(xs) - 1):
            a_, b_ = xs[i] + post_w / 2, xs[i + 1] - post_w / 2
            segs = [(a_, b_)]
            if gap:
                segs = [s for s in ((a_, min(b_, gap[0])), (max(a_, gap[1]), b_)) if s[1] - s[0] > 0.25]
            for s0, s1 in segs:
                railing(kit, (s0, yr), (s1, yr), z_deck, style=rail_style, mat=rail_mat or trim)
        for x in (x0 + 0.06, x1 - 0.06):
            railing(kit, (x, yr), (x, y_wall - 0.05), z_deck, style=rail_style, mat=rail_mat or trim)
    if steps_at is not None and z_deck > 0.05:
        steps(kit, steps_at - step_w / 2, steps_at + step_w / 2, y_out, z_deck, mat=deck, stringer=trim)
    if ribbon:
        tie_ribbon(kit, (xs[0], y_out + 0.08), 1.35)
    return xs, y_out


def tie_ribbon(kit, at, z):
    """Orange flagging tape knotted round a post or pole (see kit_status: the town's sign)."""
    R = kit.p("Ribbon", "ribbon")
    x, y = at
    R.box((x - 0.08, y - 0.006, z), (x + 0.08, y + 0.15, z + 0.04))
    for dx, L in ((0.0, 0.33), (0.035, 0.25)):
        q = [V(x - 0.02 + dx, y - 0.007, z), V(x + 0.015 + dx, y - 0.007, z), V(x + 0.04 + dx, y - 0.03, z - L),
             V(x + 0.005 + dx, y - 0.03, z - L - 0.01)]
        R.face(q, toward=(0, -1, 0))
        R.face(q, toward=(0, 1, 0))


def chimney(kit, x, y, z0, z1, w=0.6, d=0.5, mat="fieldstone"):
    kit.p("Chimney", mat).box((x - w / 2, y - d / 2, z0), (x + w / 2, y + d / 2, z1), skip="b")
    kit.p("ChimneyCap", "trim_black").box((x - w / 2 - 0.05, y - d / 2 - 0.05, z1), (x + w / 2 + 0.05, y + d / 2 + 0.05, z1 + 0.06))
    kit.p("ChimneyCap", "trim_black").box((x - 0.12, y - 0.12, z1 + 0.06), (x + 0.12, y + 0.12, z1 + 0.3), skip="b")


def corner_boards(kit, x0, x1, y0, y1, z0, z1, w=0.12, proud=0.025, mat="trim"):
    T = kit.p("Trim", mat)
    for (x, y, sx, sy) in ((x0, y0, -1, -1), (x1, y0, 1, -1), (x1, y1, 1, 1), (x0, y1, -1, 1)):
        xa, xb = sorted((x, x + sx * proud))
        ya, yb = sorted((y - sy * (w - proud), y + sy * proud))
        T.box((xa, ya, z0), (xb, yb, z1), skip="bt")
        xa, xb = sorted((x - sx * (w - proud), x + sx * proud))
        ya, yb = sorted((y, y + sy * proud))
        T.box((xa, ya, z0), (xb, yb, z1), skip="bt")


def band(kit, x0, x1, y0, y1, z0, z1, proud=0.02, mat="trim", sides="SNEW"):
    """A horizontal band (frieze, water table, sign band) round the walls."""
    T = kit.p("Trim", mat)
    for side, plane, a0, a1 in (("S", y0, x0 - proud, x1 + proud), ("N", y1, x0 - proud, x1 + proud),
                                ("E", x1, y0, y1), ("W", x0, y0, y1)):
        if side in sides:
            wbox(T, side, plane, a0, a1, z0, z1, 0, proud, skip="back")


def sign(kit, side, plane, a, z, w, h, kind, d=0.03, glow=False, frame="trim_black", thick=0.05):
    """A sign board with a pictogram (no lettering) on a wall; glow=True lights it."""
    wbox(kit.p("SignBoard", frame), side, plane, a - w / 2 - 0.03, a + w / 2 + 0.03, z - 0.03, z + h + 0.03, d, d + thick,
         skip="back")
    wquad(kit.p("Sign", "signs", glow=glow), side, plane, a - w / 2, a + w / 2, z, z + h, d + thick + 0.002, uvs=sign_uv(kind))


def blade_sign(kit, side, plane, a, z, w=0.9, h=0.45, kind="cafe", arm=1.0, glow=False):
    """A projecting blade sign on a black bracket (both faces)."""
    P, u, n = frame(side, plane)
    B = kit.p("Bracket", "trim_black")
    p0, p1 = P(a, z + h + 0.08, 0), P(a, z + h + 0.08, arm)
    B.beam(p0, p1, 0.03, 0.03)
    B.beam(P(a, z + h * 0.2, 0), P(a, z + h + 0.08, arm * 0.6), 0.02, 0.02)
    S = kit.p("Sign", "signs", glow=glow)
    c = (P(a, z, 0.15) + P(a, z, arm)) / 2
    half = (arm - 0.15) / 2
    pts = [c - n * half, c + n * half, c + n * half + Z * h, c - n * half + Z * h]
    uv = sign_uv(kind)
    side_dir = u
    S.face([p + side_dir * 0.02 for p in pts], uvs=uv, toward=side_dir)
    S.face([p - side_dir * 0.02 for p in pts[::-1]], uvs=uv[1::-1] + uv[:1:-1], toward=-side_dir)
    kit.p("SignBoard", "trim_black").box(Vector(map(min, pts[0] - side_dir * 0.019, pts[2] + side_dir * 0.019)) - V(0, 0, 0.02),
                                         Vector(map(max, pts[0] - side_dir * 0.019, pts[2] + side_dir * 0.019)) + V(0, 0, 0.02))


def gooseneck(kit, side, plane, a, z, arm=0.45):
    """A black gooseneck barn light over a sign or door (the lamp is a glow swatch)."""
    P, u, n = frame(side, plane)
    B = kit.p("Lamps", "trim_black")
    B.tube(P(a, z, 0), P(a, z, arm * 0.6), 0.015, 5)
    B.tube(P(a, z, arm * 0.6), P(a, z - 0.12, arm), 0.015, 5)
    c = P(a, z - 0.16, arm)
    B.cyl((c.x, c.y), 0.16, c.z, c.z + 0.07, sides=8, caps="t", r1=0.04)
    kit.p("Lamps", "lamp").cyl((c.x, c.y), 0.1, c.z - 0.005, c.z + 0.005, sides=8, caps="b")


# ===================================================================== small details

def meter(kit, side, plane, a, z=1.5):
    M = kit.p("Meter", "metal_galv")
    wbox(M, side, plane, a - 0.12, a + 0.12, z - 0.18, z + 0.18, 0, 0.12, skip="back")
    wbox(M, side, plane, a - 0.02, a + 0.02, z + 0.18, z + 1.6, 0.03, 0.07, skip="back")


def hvac(kit, x, y, z=0.0, w=0.8, d=0.8, h=0.75):
    """A condenser unit on a pad (behind modern buildings, or on flat roofs)."""
    kit.p("HVAC", "concrete").box((x - w / 2 - 0.1, y - d / 2 - 0.1, z), (x + w / 2 + 0.1, y + d / 2 + 0.1, z + 0.08), skip="b")
    kit.p("HVAC", "metal_galv").box((x - w / 2, y - d / 2, z + 0.08), (x + w / 2, y + d / 2, z + h), skip="b")
    kit.p("HVACFan", "metal_dark").cyl((x, y), min(w, d) * 0.38, z + h, z + h + 0.01, sides=10)
    kit.collide((x - w / 2 - 0.1, y - d / 2 - 0.1, z), (x + w / 2 + 0.1, y + d / 2 + 0.1, z + h))


def downspout(kit, x, y, z_top, mat="trim_black"):
    kit.p("Gutter", mat).box((x - 0.04, y - 0.04, 0.05), (x + 0.04, y + 0.04, z_top))


# ===================================================================== far meshes (LOD1)

FAR_OF = {   # surface -> palette swatch for the LOD1 (region means where we have them)
    "bb_white": "bb_white", "bb_charcoal": "bb_charcoal", "lap_cream": "lap_cream", "ledgestone": "ledgestone",
    "fieldstone": "fieldstone", "brick_red": "brick_red", "seam_black": "seam_black", "shingle": "shingle",
    "lap_white": "bb_white", "brick_white": "paint_white", "bb_sage": "trim_green", "seam_green": "trim_green",
    "cedar": "trim_brown", "corrugated": "metal_galv", "block": "paint_white", "concrete": "stone",
    "asphalt": "tar", "deck": "trim_brown", "windows": "glass_dark", "signs": "trim_red",
}


def far_key(s):
    return FAR_OF.get(s, s)


class Far:
    """A cheap LOD1: boxes and gabled prisms in palette swatches only."""

    def __init__(self, name):
        self.kit = Kit(name)
        self.part = self.kit.p("LOD1", "palette")

    def _f(self, pts, key, toward=None):
        u = tt.swatch_uv(far_key(key))
        P = [Vector(p) for p in pts]
        if toward is not None and newell(P).dot(Vector(toward)) < 0:
            P = P[::-1]
        self.part._emit(P, [u] * len(P))

    def box(self, lo, hi, side="bb_white", top=None, skip="b"):
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        F = {
            "b": [(x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0)],
            "t": [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
            "f": [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
            "k": [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)],
            "l": [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)],
            "r": [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
        }
        for k_, pts in F.items():
            if k_ not in skip:
                self._f(pts, (top or side) if k_ in "tb" else side)

    def gable(self, x0, x1, y0, y1, z0, z_eave, z_ridge, axis="y", wall="bb_white", roof="seam_black", over=0.3):
        self.box((x0, y0, z0), (x1, y1, z_eave), wall, skip="bt")
        if axis == "y":
            c, s = (x0 + x1) / 2, (x1 - x0) / 2
            for y, o in ((y0, -1), (y1, 1)):
                self._f([(x0, y, z_eave), (x1, y, z_eave), (c, y, z_ridge)], wall, toward=(0, o, 0))
            pz = (z_ridge - z_eave) / s
            for sg, xe in ((-1, x0 - over), (1, x1 + over)):
                ze = z_eave - over * pz
                q = [(xe, y0 - over, ze), (xe, y1 + over, ze), (c, y1 + over, z_ridge), (c, y0 - over, z_ridge)]
                self._f(q, roof, toward=(sg, 0, 1))
                self._f(q, "shade", toward=(0, 0, -1))
        else:
            c, s = (y0 + y1) / 2, (y1 - y0) / 2
            for x, o in ((x0, -1), (x1, 1)):
                self._f([(x, y0, z_eave), (x, y1, z_eave), (x, c, z_ridge)], wall, toward=(o, 0, 0))
            pz = (z_ridge - z_eave) / s
            for sg, ye in ((-1, y0 - over), (1, y1 + over)):
                ze = z_eave - over * pz
                q = [(x0 - over, ye, ze), (x1 + over, ye, ze), (x1 + over, c, z_ridge), (x0 - over, c, z_ridge)]
                self._f(q, roof, toward=(0, sg, 1))
                self._f(q, "shade", toward=(0, 0, -1))

    def hip(self, x0, x1, y0, y1, z_eave, z_ridge, roof="shingle", over=0.4):
        X0, X1, Y0, Y1 = x0 - over, x1 + over, y0 - over, y1 + over
        W, D = X1 - X0, Y1 - Y0
        h = min(W, D) / 2
        cx, cy = (X0 + X1) / 2, (Y0 + Y1) / 2
        r0, r1 = ((X0 + h, cy, z_ridge), (X1 - h, cy, z_ridge)) if W >= D else ((cx, Y0 + h, z_ridge), (cx, Y1 - h, z_ridge))
        c = [(X0, Y0, z_eave), (X1, Y0, z_eave), (X1, Y1, z_eave), (X0, Y1, z_eave)]
        faces = ([[c[0], c[1], r1, r0], [c[2], c[3], r0, r1], [c[3], c[0], r0], [c[1], c[2], r1]] if W >= D else
                 [[c[1], c[2], r1, r0], [c[3], c[0], r0, r1], [c[0], c[1], r0], [c[2], c[3], r1]])
        for f in faces:
            self._f(f, roof, toward=(0, 0, 1))
        self._f(c, "shade", toward=(0, 0, -1))

    def shed(self, x0, x1, y_high, y_low, z_high, z_low, roof="seam_black"):
        q = [(x0, y_high, z_high), (x1, y_high, z_high), (x1, y_low, z_low), (x0, y_low, z_low)]
        self._f(q, roof, toward=(0, 0, 1))
        self._f(q, "shade", toward=(0, 0, -1))

    def quad(self, side, plane, a0, a1, z0, z1, key, d=0.03):
        P, u, n = frame(side, plane)
        self._f([P(a0, z0, d), P(a1, z0, d), P(a1, z1, d), P(a0, z1, d)], key, toward=n)

    def windows(self, side, plane, centres, z, w, h, key="glass_dark", d=0.03):
        for a in centres:
            self.quad(side, plane, a - w / 2, a + w / 2, z, z + h, key, d)

    def cyl(self, c, r, z0, z1, key, sides=6, cap=True, r1=None):
        r1 = r if r1 is None else r1
        ring = [(math.cos(2 * math.pi * i / sides), math.sin(2 * math.pi * i / sides)) for i in range(sides)]
        for i in range(sides):
            (ca, sa), (cb, sb) = ring[i], ring[(i + 1) % sides]
            self._f([(c[0] + r * ca, c[1] + r * sa, z0), (c[0] + r * cb, c[1] + r * sb, z0),
                     (c[0] + r1 * cb, c[1] + r1 * sb, z1), (c[0] + r1 * ca, c[1] + r1 * sa, z1)], key,
                    toward=(ca + cb, sa + sb, 0))
        if cap and r1 > 0:
            self._f([(c[0] + r1 * ca, c[1] + r1 * sa, z1) for ca, sa in ring], key, toward=(0, 0, 1))

    def beam(self, a, b, w, h, key):
        tmp = Part(self.kit, "_", "trim")
        tmp.beam(a, b, w, h)
        u = tt.swatch_uv(far_key(key))
        for f in tmp.f:
            self.part._emit([Vector(tmp.v[i]) for i in f], [u] * len(f))

    def tris(self):
        return self.part.tris()
