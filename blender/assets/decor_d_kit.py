"""Set-dressing kit for the decor_d_* assets (primary bedroom, primary bath, guest room).
Not an asset itself (like library_kit.py / guest_mats.py).

A `Builder` gathers every small object of a vignette into ONE mesh per material, named
`<Asset>_<Key>_NoCollide` (small things never become colliders; keys listed in `collide`
keep a plain name so a floor basket or floor vase gets its box). Item functions add
geometry at a 4x4 matrix (`at(x, y, z, rot)`), with world-scale box UVs at the material's
tile, or their own UVs (leaves on the leaf texture).

Materials: reused by name when the level already has them (`mat(key)` never recolours
someone else's material: it returns the existing one, else creates it with the defining
asset's arguments). Three new ones, shared by all three rooms: M_DecorD_Paper (page
blocks, candles, soap), M_DecorD_Charcoal (dark glaze, coffee, soles), M_DecorD_Terracotta
(guest-room accent). Everything else is already in the rooms: fabrics for book cloth,
M_Library_Planter as matte stoneware, M_Marble_White, M_Bronze, M_Glass_Smoke...
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
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from lib import common, materials, pickups, textures  # noqa: E402

importlib.reload(common)
importlib.reload(materials)
importlib.reload(textures)
importlib.reload(pickups)
import bath_common as bc  # noqa: E402
import bath_vanity as bv  # noqa: E402  (soft_extrude, round_outline)

importlib.reload(bc)


# ------------------------------------------------------------------ materials

def _get(name, create):
    m = bpy.data.materials.get(name)
    return m if m is not None else create()


def _leaf():
    import library_plant
    m = common.pbr_material("M_Library_Leaf", (1, 1, 1), roughness=0.38)
    common.set_base_color_map(m, textures.load(library_plant.leaf_texture()))
    m.use_backface_culling = False
    return m


def _marble():
    m = common.pbr_material("M_Marble_White", (0.8, 0.79, 0.77), roughness=0.12, coat=0.0)
    common.set_base_color_map(m, textures.load(textures.marble()))
    return m


def _guest(fn):
    def f():
        import guest_mats
        return getattr(guest_mats, fn)()
    return f


def _fab(name, c, rough=0.9):
    return lambda: materials.fabric(name, c, roughness=rough)


def _flat(name, c, rough, metal=0.0, coat=0.0):
    return lambda: common.pbr_material(name, c, roughness=rough, metallic=metal, coat=coat)


# key: (material name, creator, uv tile in metres)
MATS = {
    # new (decor_d)
    "paper": ("M_DecorD_Paper", _flat("M_DecorD_Paper", (0.70, 0.68, 0.62), 0.85), 0.5),
    "charcoal": ("M_DecorD_Charcoal", _flat("M_DecorD_Charcoal", (0.030, 0.029, 0.028), 0.42, coat=0.15), 0.5),
    "terracotta": ("M_DecorD_Terracotta", _flat("M_DecorD_Terracotta", (0.33, 0.13, 0.065), 0.62), 0.5),
    # reused
    "stoneware": ("M_Library_Planter", _flat("M_Library_Planter", (0.46, 0.42, 0.35), 0.85), 0.5),
    "marble": ("M_Marble_White", _marble, 0.5),
    "bronze": ("M_Bronze", materials.bronze, 0.5),
    "black": ("M_Aluminium_Black", materials.black_metal, 0.5),
    "glass": ("M_Glass_Smoke", lambda: materials.glass("M_Glass_Smoke", tint=(0.42, 0.40, 0.37), alpha=0.35,
                                                       roughness=0.04), 0.5),
    "oak": ("M_OakSmoked", materials.smoked_oak, 0.5),
    "oak_light": ("M_Oak_Light", _guest("oak"), 1.5),
    "walnut": ("M_Walnut", materials.walnut, 0.5),
    "oat": ("M_Fabric_Oat", _fab("M_Fabric_Oat", (0.42, 0.37, 0.30)), 0.25),
    "ink": ("M_Fabric_Ink", _fab("M_Fabric_Ink", (0.018, 0.024, 0.04), 0.8), 0.25),
    "stone_fabric": ("M_Fabric_Stone", _fab("M_Fabric_Stone", (0.16, 0.15, 0.135)), 0.25),
    "linen": ("M_Fabric_Linen", _guest("linen"), 0.25),
    "sage": ("M_Fabric_Sage", _guest("sage"), 0.25),
    "sage_light": ("M_Fabric_SageLight", _guest("sage_light"), 0.25),
    "ivory": ("M_Fabric_Linen_Ivory", _fab("M_Fabric_Linen_Ivory", (0.55, 0.52, 0.46)), 0.25),
    "bath_stone": ("M_Bath_Stone", bc.stone, 0.5),
    "ceramic": ("M_Bath_Ceramic", bc.ceramic, 0.5),
    "brass": ("M_Bath_Brass", bc.brass, 0.5),
    "leaf": ("M_Library_Leaf", _leaf, None),
    "bark": ("M_Plant_Bark", _flat("M_Plant_Bark", (0.10, 0.07, 0.045), 0.8), 0.5),
    "soil": ("M_Plant_Soil", _flat("M_Plant_Soil", (0.025, 0.016, 0.010), 1.0), 0.5),
    "bath_leaf": ("M_Bath_Leaf", _flat("M_Bath_Leaf", (0.055, 0.15, 0.05), 0.45), 0.5),
    "bath_soil": ("M_Bath_Soil", _flat("M_Bath_Soil", (0.02, 0.018, 0.015), 0.95), 0.5),
}

# room palettes: book cloth, vessels, metal, wood
PALETTES = {
    "ink": dict(covers=["oat", "ink", "stone_fabric", "linen", "sage", "oat", "ink"], novels=["stone_fabric", "oat"],
                vessels=["charcoal", "stoneware", "marble"], metal="bronze", wood="oak", frame="bronze"),
    "sage": dict(covers=["linen", "sage", "sage_light", "linen", "terracotta", "stoneware"], novels=["sage", "linen"],
                 vessels=["terracotta", "stoneware", "charcoal"], metal="bronze", wood="oak_light", frame="black"),
    "bath": dict(covers=["ivory", "ink", "oat"], novels=["ink", "ivory"], vessels=["bath_stone", "charcoal", "ceramic"], metal="brass",
                 wood="walnut", frame="brass"),
}


def mat(key):
    name, create, _ = MATS[key.split("@")[0]]
    return _get(name, create)


# ------------------------------------------------------------------ builder

def at(x=0.0, y=0.0, z=0.0, rot=0.0, tilt=None):
    """Translate, then rotate `rot` degrees about Z; tilt = (deg, 'X'|'Y') applied after."""
    m = Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(rot), 4, "Z")
    if tilt:
        m = m @ Matrix.Rotation(math.radians(tilt[0]), 4, tilt[1])
    return m


class Builder:
    """One bmesh per key ('material' or 'material@Part'); finish() makes the objects."""

    def __init__(self, name, collide=()):
        self.n = name
        self.col = common.fresh_collection(name)
        self.root = common.empty(name, self.col)
        self.meshes = {}
        self.collide = set(collide)

    def bm(self, key):
        if key not in self.meshes:
            b = bmesh.new()
            b.loops.layers.uv.new("UVMap")
            self.meshes[key] = b
        return self.meshes[key]

    def add(self, key, src, M=None, smooth=None):
        """Merge bmesh `src` (freed) into `key` at matrix M (rotation + translation only).
        UVs: src's own layer if it has one, else a box projection in src's local frame
        (u along src's longest axis, like common.box_uv) at the material's tile."""
        M = M if M is not None else Matrix.Identity(4)
        dst = self.bm(key)
        uvl = dst.loops.layers.uv.active
        suv = src.loops.layers.uv.active
        tile = MATS[key.split("@")[0]][2] or 0.5
        src.normal_update()
        if src.verts:
            dims = [max(v.co[a] for v in src.verts) - min(v.co[a] for v in src.verts) for a in range(3)]
        vmap = {v: dst.verts.new(M @ v.co) for v in src.verts}
        for f in src.faces:
            try:
                nf = dst.faces.new([vmap[v] for v in f.verts])
            except ValueError:
                continue
            nf.smooth = f.smooth if smooth is None else smooth
            if suv is not None:
                for lo, ln in zip(f.loops, nf.loops):
                    ln[uvl].uv = lo[suv].uv
            else:
                nrm = [abs(c) for c in f.normal]
                na = nrm.index(max(nrm))
                a, b = [i for i in range(3) if i != na]
                if dims[b] > dims[a]:
                    a, b = b, a
                for lo, ln in zip(f.loops, nf.loops):
                    co = lo.vert.co
                    ln[uvl].uv = (co[a] / tile, co[b] / tile)
        for e in src.edges:
            if not e.smooth:
                ne = dst.edges.get((vmap[e.verts[0]], vmap[e.verts[1]]))
                if ne is not None:
                    ne.smooth = False
        src.free()

    def finish(self):
        # loose things become pickups (lib/pickups.py), the rest stays one mesh per material
        pickups.emit(self, self.n, self.col, self.root, list(self.meshes.values()), lambda b: b,
                     lambda key: mat(key.split("@")[0]))
        for key, b in self.meshes.items():
            if not b.faces:
                b.free()
                continue
            base, _, part = key.partition("@")
            label = (part or base).title().replace("_", "")
            nm = f"{self.n}_{label}" if key in self.collide else f"{self.n}_{label}_NoCollide"
            ob = common.mesh_object(nm, b, self.col, mat(base), self.root, smooth=False)
            # faces keep their own smooth flags (mesh_object's smooth=False leaves them alone)
        return self.root, [o for o in self.root.children_recursive if o.type == "MESH"]


# ------------------------------------------------------------------ primitives (bmesh)

def lathe(profile, segs=16, sharp=38.0, closed=False):
    """[(r, z)] revolved about Z, smooth-shaded with hard rings where the profile turns."""
    bm = bc.lathe(profile, segs, closed=closed, sharp=sharp)
    for f in bm.faces:
        f.smooth = True
    return bm


def resample(poly, n):
    """n points evenly spaced along a 2D polyline."""
    d = [0.0]
    for i in range(1, len(poly)):
        d.append(d[-1] + math.hypot(poly[i][0] - poly[i - 1][0], poly[i][1] - poly[i - 1][1]))
    out, j = [], 0
    for i in range(n):
        s = d[-1] * i / (n - 1)
        while j < len(d) - 2 and d[j + 1] < s:
            j += 1
        t = (s - d[j]) / max(d[j + 1] - d[j], 1e-12)
        out.append((poly[j][0] + (poly[j + 1][0] - poly[j][0]) * t, poly[j][1] + (poly[j + 1][1] - poly[j][1]) * t))
    return out


def vessel_profile(ctrl, wall=0.004, inner_depth=0.05, rings=9, foot=0.003, floor=None):
    """Outer (z, r) control points base -> lip, a rounded lip of wall thickness, and the
    inside down `inner_depth` (enough to read as hollow) or to `floor` (bowls). (r, z) out."""
    dense = bc.catmull([(r, z) for z, r in ctrl], per=8)
    outer = resample(dense, rings)
    r0 = outer[0][0]
    prof = [(0.0, 0.0), (r0 - foot, 0.0)]
    prof += [(r, max(z, foot)) for r, z in outer]
    rt, zt = outer[-1]
    prof += [(rt - wall * 0.5, zt + wall * 0.3), (rt - wall, zt - wall * 0.2)]
    zb = floor if floor is not None else zt - inner_depth
    inner = [(max(r - wall, 0.003), z) for r, z in reversed(outer[:-1]) if z > zb + 0.002]
    prof += inner
    rb = max(min((r for r, z in outer if z >= zb), default=rt) - wall, 0.003)
    prof += [(rb * 0.85, zb), (0.0, zb)]
    return prof


def cbox(size, chamfer=0.0, drop=()):
    """Box centred on the origin, flat shaded, optionally chamfered; `drop` removes faces
    whose normal is one of '+x' '-x' '+y' '-y' '+z' '-z' (hidden sides)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    if chamfer > 0:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=chamfer, segments=1, affect="EDGES", profile=0.5)
    if drop:
        bm.normal_update()
        kill = []
        for f in bm.faces:
            for d in drop:
                ax = "xyz".index(d[1])
                if (f.normal[ax] > 0.95 if d[0] == "+" else f.normal[ax] < -0.95):
                    kill.append(f)
        bmesh.ops.delete(bm, geom=kill, context="FACES_ONLY")
    for f in bm.faces:
        f.smooth = False
    return bm


def prism(outline, y0, y1, smooth=False):
    """Closed (x, z) outline extruded along Y from y0 to y1, capped."""
    bm = bmesh.new()
    a = [bm.verts.new((x, y0, z)) for x, z in outline]
    b = [bm.verts.new((x, y1, z)) for x, z in outline]
    m = len(outline)
    for i in range(m):
        j = (i + 1) % m
        bm.faces.new((a[i], a[j], b[j], b[i]))
    ca = bm.faces.new(a[::-1])
    cb = bm.faces.new(b)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        f.smooth = smooth and f not in (ca, cb)
    if smooth:
        for cap in (ca, cb):
            for e in cap.edges:
                e.smooth = False
    return bm


def rrect(w, d, r, seg=3):
    """Rounded rectangle (x, y) points, counter-clockwise."""
    r = max(min(r, w / 2 - 1e-4, d / 2 - 1e-4), 0.0)
    pts = []
    for cx, cy, a0 in ((w / 2 - r, d / 2 - r, 0), (-w / 2 + r, d / 2 - r, 90), (-w / 2 + r, -d / 2 + r, 180),
                       (w / 2 - r, -d / 2 + r, 270)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def loft(rings, cap_bottom=True, cap_top=True, smooth=True):
    """rings [(z, [(x, y) ...]) ...] of equal length, bottom -> top, optional n-gon caps."""
    bm = bmesh.new()
    rows = [[bm.verts.new((x, y, z)) for x, y in pts] for z, pts in rings]
    m = len(rows[0])
    for ra, rb in zip(rows, rows[1:]):
        for i in range(m):
            j = (i + 1) % m
            bm.faces.new((ra[i], ra[j], rb[j], rb[i]))
    if cap_bottom:
        bm.faces.new(rows[0][::-1])
    if cap_top:
        bm.faces.new(rows[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        f.smooth = smooth and len(f.verts) == 4
    # hard edges round the caps
    for row in (rows[0], rows[-1]):
        for i in range(m):
            e = bm.edges.get((row[i], row[(i + 1) % m]))
            if e is not None:
                e.smooth = False
    return bm


def tube(pts, radius, sides=6, caps=True, taper=None):
    """Circle swept along a polyline (parallel-transport frames). taper(t) scales the radius."""
    bm = bmesh.new()
    P = [Vector(p) for p in pts]
    n = len(P)
    T = [(P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized() for i in range(n)]
    up = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))
    N = T[0].cross(up).normalized()
    rows = []
    for i in range(n):
        if i:
            N = (N - T[i] * N.dot(T[i])).normalized()
        B = T[i].cross(N)
        r = radius * (taper(i / max(n - 1, 1)) if taper else 1.0)
        rows.append([bm.verts.new(P[i] + (N * math.cos(2 * math.pi * k / sides) + B * math.sin(2 * math.pi * k / sides)) * r)
                     for k in range(sides)])
    for ra, rb in zip(rows, rows[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((ra[k], ra[j], rb[j], rb[k]))
    if caps:
        bm.faces.new(rows[0][::-1])
        bm.faces.new(rows[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        f.smooth = len(f.verts) == 4
    return bm


def ellipsoid(rx, ry, rz, u=8, v=5, flat=0.0):
    """Low-poly ellipsoid centred on the origin (flat > 0 squashes the underside)."""
    prof = []
    for i in range(v + 1):
        a = -math.pi / 2 + math.pi * i / v
        z = math.sin(a) * rz
        if z < 0:
            z *= (1 - flat)
        prof.append((math.cos(a) * 1.0, z))
    bm = lathe([(max(r, 0.0) if abs(r) > 1e-6 else 0.0, z) for r, z in prof], u, sharp=89)
    bmesh.ops.scale(bm, vec=(rx, ry, 1.0), verts=bm.verts)
    return bm


def smoothstep(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ items
# Every item takes the builder and a matrix M (its origin: centre of its underside on the
# surface it stands on, front -Y) and returns its height where something could go on top.

def book(B, M, w, d, t, cover):
    """Hardback lying flat: cloth case (boards + rounded spine on -X) round a page block
    set back 3 mm. w across (X, spine side -X), d along Y, t thick."""
    bt = min(0.0028, t * 0.14)
    o = 0.003
    sr = min(0.006, t * 0.3)
    xs = -w / 2 + sr
    out = [(w / 2, 0.0), (w / 2, bt), (xs + bt * 0.6, bt), (xs + bt * 0.6, t - bt), (w / 2, t - bt), (w / 2, t)]
    for k in range(1, 6):
        a = math.pi / 2 + math.pi * k / 6
        out.append((xs + sr * math.cos(a), t / 2 + (t / 2) * math.sin(a)))
    out.append((xs, 0.0))
    B.add(cover, prism(out, -d / 2, d / 2), M)
    pw = w / 2 - o - (xs + bt * 0.6)
    pages = cbox((pw, d - 2 * o, t - 2 * bt), drop=("+z", "-z", "-x"))
    B.add("paper", pages, M @ Matrix.Translation(((xs + bt * 0.6) + pw / 2, 0, t / 2)))
    return t


ART_SIZES = [(0.24, 0.31), (0.26, 0.33), (0.28, 0.36), (0.23, 0.29), (0.30, 0.30), (0.25, 0.25),
             (0.31, 0.39), (0.21, 0.27)]


def book_stack(B, M, rng, n, covers, sizes=None, thick=(0.02, 0.045), spin=5.0, spines="front", fixed=False):
    """n books lying flat, largest at the bottom, each a little turned and offset, spines
    facing front (-Y) or alternating. Returns the stack height."""
    sizes = list(sizes or rng.sample(ART_SIZES, min(n, len(ART_SIZES))))
    while len(sizes) < n:
        sizes.append(rng.choice(ART_SIZES))
    sizes.sort(key=lambda s: -s[0] * s[1])
    z = 0.0
    last = None
    for i in range(n):
        w, d = sizes[i]
        if i and rng.random() < 0.35:                  # not strictly pyramid
            w, d = w * rng.uniform(0.92, 1.0), d * rng.uniform(0.92, 1.0)
        t = rng.uniform(*thick)
        c = covers[i] if fixed else rng.choice([c for c in covers if c != last] or covers)
        last = c
        if spines == "side":
            base = 0.0 if i % 2 == 0 else 180.0
        elif spines == "outside":
            base = 180.0
        else:
            base = 90.0 if (spines == "front" or i % 2 == 0) else -90.0
        rot = base + rng.uniform(-spin, spin)
        dx, dy = rng.uniform(-0.012, 0.012), rng.uniform(-0.01, 0.01)
        book(B, M @ at(dx, dy, z, rot), w, d, t, c)
        z += t
    return z


def vessel(B, M, key, kind="bottle", h=0.30, r=0.07, segs=16):
    """Ceramic vase of a family: bottle, ovoid, cylinder, bud, globe, flask."""
    shapes = {
        "bottle": [(0.0, 0.80), (0.25, 0.95), (0.48, 1.0), (0.62, 0.78), (0.74, 0.36), (0.86, 0.27), (0.97, 0.29),
                   (1.0, 0.32)],
        "ovoid": [(0.0, 0.62), (0.18, 0.86), (0.45, 1.0), (0.72, 0.88), (0.9, 0.6), (1.0, 0.55)],
        "cylinder": [(0.0, 0.94), (0.05, 1.0), (0.95, 1.0), (1.0, 0.97)],
        "bud": [(0.0, 0.85), (0.22, 1.0), (0.45, 0.82), (0.7, 0.32), (0.92, 0.26), (1.0, 0.34)],
        "globe": [(0.0, 0.48), (0.15, 0.82), (0.42, 1.0), (0.7, 0.86), (0.88, 0.5), (0.97, 0.36), (1.0, 0.38)],
        "flask": [(0.0, 0.70), (0.06, 0.98), (0.40, 1.0), (0.52, 0.72), (0.62, 0.30), (0.95, 0.26), (1.0, 0.30)],
    }
    ctrl = [(z * h, s * r) for z, s in shapes[kind]]
    narrow = ctrl[-1][1] < r * 0.5
    prof = vessel_profile(ctrl, wall=min(0.005, ctrl[-1][1] * 0.25), inner_depth=0.03 if narrow else min(0.06, h * 0.3),
                          rings=9 if kind != "cylinder" else 4)
    B.add(key, lathe(prof, segs), M)
    return h


def bowl(B, M, key, r=0.12, h=0.06, segs=18, foot=0.45, wall=0.006):
    """Open bowl on a small foot ring, rounded lip, the inside down to a flat floor."""
    ctrl = [(0.0, r * foot), (h * 0.08, r * (foot + 0.06)), (h * 0.35, r * 0.82), (h * 0.7, r * 0.97), (h, r)]
    prof = vessel_profile(ctrl, wall=wall, rings=7, floor=h * 0.25)
    B.add(key, lathe(prof, segs), M)
    return h * 0.25


def tray(B, M, key, w=0.36, d=0.22, h=0.025, r=0.03, wall=0.006, base=0.006):
    """Rounded-rectangle tray: eased foot, straight rim of `wall` thickness, flat floor."""
    seg = 3
    rings = [(0.0, rrect(w - 0.006, d - 0.006, r - 0.003, seg)), (0.003, rrect(w, d, r, seg)),
             (h - 0.002, rrect(w, d, r, seg)), (h, rrect(w - 0.002, d - 0.002, r - 0.001, seg)),
             (h, rrect(w - 2 * wall + 0.002, d - 2 * wall + 0.002, r - wall + 0.001, seg)),
             (h - 0.002, rrect(w - 2 * wall, d - 2 * wall, r - wall, seg)),
             (base, rrect(w - 2 * wall, d - 2 * wall, r - wall, seg))]
    bm = loft(rings, smooth=False)
    B.add(key, bm, M)
    return base


def round_tray(B, M, key, r=0.12, h=0.022, wall=0.005, base=0.005, segs=24):
    prof = [(0.0, 0.0), (r - 0.003, 0.0), (r, 0.003), (r, h - 0.0015), (r - wall * 0.5, h), (r - wall, h - 0.0015),
            (r - wall, base + 0.002), (r - wall - 0.002, base), (0.0, base)]
    B.add(key, lathe(prof, segs, sharp=30), M)
    return base


def candle(B, M, r=0.035, h=0.09, wax="paper", segs=12, lit=False):
    """Pillar candle with a softened top, a shallow melt pool and a black wick."""
    prof = [(0.0, 0.0), (r, 0.0), (r, h - 0.004), (r - 0.003, h), (r * 0.7, h - 0.004), (0.0, h - 0.006)]
    B.add(wax, lathe(prof, segs, sharp=50), M)
    wick = tube([(0, 0, h - 0.006), (0.001, 0, h + 0.008), (0.003, 0.0, h + 0.012)], 0.0012, sides=4, caps=False)
    B.add("charcoal", wick, M)
    return h


def candle_jar(B, M, jar="stoneware", r=0.04, h=0.08, lid=None):
    """Candle in a straight-sided ceramic jar: wax surface sunk below the rim."""
    prof = [(0.0, 0.0), (r - 0.003, 0.0), (r, 0.003), (r, h - 0.002), (r - 0.002, h), (r - 0.005, h - 0.002),
            (r - 0.005, h - 0.02), (0.0, h - 0.02)]
    B.add(jar, lathe(prof, 16, sharp=40), M)
    B.add("paper", lathe([(0.0, h - 0.019), (r - 0.0052, h - 0.019), (r - 0.0052, h - 0.021)], 16), M)
    B.add("charcoal", tube([(0, 0, h - 0.02), (0, 0, h - 0.008)], 0.0012, sides=4, caps=False), M)
    if lid:
        lp = [(0.0, h + 0.012), (r * 0.5, h + 0.012), (r - 0.002, h + 0.009), (r + 0.001, h + 0.004), (r + 0.001, h + 0.001),
              (r - 0.006, h + 0.001), (r - 0.006, h - 0.004), (0.0, h - 0.004)]
        B.add(lid, lathe(lp, 16, sharp=40), M)
    return h


def carafe(B, M, key="glass", tumbler=True):
    """Bedside water carafe with its tumbler upturned over the neck."""
    prof = [(0.0, 0.0), (0.036, 0.0), (0.042, 0.004), (0.046, 0.03), (0.046, 0.10), (0.040, 0.135), (0.026, 0.16),
            (0.0185, 0.175), (0.0175, 0.205), (0.0195, 0.215), (0.0165, 0.215), (0.0145, 0.205), (0.0145, 0.18),
            (0.0, 0.17)]
    B.add(key, lathe(prof, 16, sharp=50), M)
    if tumbler:
        zt = 0.17                                   # rim of the upturned tumbler rests on the shoulder
        tp = [(0.031, zt), (0.0335, zt + 0.002), (0.036, zt + 0.07), (0.036, zt + 0.078), (0.0, zt + 0.078),
              (0.0, zt + 0.072), (0.032, zt + 0.07), (0.029, zt + 0.004), (0.031, zt)]
        B.add(key, lathe(tp, 16, sharp=50, closed=False), M)
    return 0.25


def tumbler(B, M, key="glass", r=0.034, h=0.09):
    prof = [(0.0, 0.0), (r - 0.002, 0.0), (r, 0.002), (r + 0.002, h), (r - 0.001, h), (r - 0.002, 0.012), (0.0, 0.010)]
    B.add(key, lathe(prof, 16, sharp=50), M)
    return h


def wine_glass(B, M, key="glass"):
    prof = [(0.0, 0.0), (0.036, 0.0), (0.037, 0.002), (0.008, 0.006), (0.004, 0.012), (0.0035, 0.09), (0.012, 0.10),
            (0.036, 0.125), (0.042, 0.16), (0.038, 0.20), (0.036, 0.20), (0.039, 0.16), (0.033, 0.127), (0.0, 0.106)]
    B.add(key, lathe(prof, 14, sharp=50), M)
    return 0.20


def perfume(B, M, w=0.05, d=0.035, h=0.085, cap="bronze", cap_h=0.03):
    """Thick-walled glass bottle (chamfered block) with a metal collar and a cap."""
    B.add("glass", cbox((w, d, h), 0.004), M @ Matrix.Translation((0, 0, h / 2)))
    B.add(cap, lathe([(0.0, h), (0.008, h), (0.008, h + 0.006), (0.0, h + 0.006)], 10), M)
    if cap_h:
        cp = [(0.0, h + 0.006), (0.016, h + 0.006), (0.0165, h + 0.008), (0.0165, h + 0.006 + cap_h - 0.002),
              (0.0145, h + 0.006 + cap_h), (0.0, h + 0.006 + cap_h)]
        B.add(cap if cap != "bronze" else "charcoal", lathe(cp, 12, sharp=40), M)
    return h + 0.006 + cap_h


def glasses(B, M, frame="bronze"):
    """Folded reading glasses resting on their lens rims and folded temples."""
    lens_w, lens_h, gap = 0.048, 0.034, 0.018
    tilt = Matrix.Rotation(math.radians(-14), 4, "X")      # lens plane leaning back (+Y)
    base = M @ Matrix.Translation((0, 0, 0.0015))
    for sx in (-1, 1):
        cx = sx * (gap / 2 + lens_w / 2)
        ring = []
        for k in range(12):
            a = 2 * math.pi * k / 12
            ex = lens_w / 2 * math.cos(a)
            ez = lens_h / 2 * math.sin(a) * (1 - 0.15 * (math.sin(a) < 0) * abs(math.cos(a)))
            ring.append(Vector((cx + ex, 0, lens_h / 2 + ez)))
        ring.append(ring[0])
        B.add(frame, tube(ring, 0.0016, sides=4, caps=False), base @ tilt)
        disc = bmesh.new()
        vs = [disc.verts.new(p) for p in ring[:-1]]
        disc.faces.new(vs)
        B.add("glass", disc, base @ tilt)
        # folded temple lying flat behind
        L = 0.125
        hx = sx * (gap / 2 + lens_w + 0.002)
        tz = 0.004 + (0.004 if sx > 0 else 0.0)
        pts = [(hx, 0.004, lens_h * 0.7), (hx - sx * 0.006, 0.012, tz + 0.002), (hx - sx * L, 0.018, tz)]
        B.add(frame, tube(pts, 0.0014, sides=4, caps=True), base)
    bridge = [Vector((-gap / 2, 0, lens_h * 0.62)), Vector((0, 0.002, lens_h * 0.76)), Vector((gap / 2, 0, lens_h * 0.62))]
    B.add(frame, tube(bridge, 0.0015, sides=4, caps=False), base @ tilt)
    return 0.03


def cup_saucer(B, M, key="stoneware", coffee="charcoal"):
    """Espresso-size cup on a saucer, with handle and coffee in it."""
    sp = [(0.0, 0.0), (0.03, 0.0), (0.032, 0.003), (0.055, 0.006), (0.068, 0.013), (0.07, 0.016), (0.067, 0.016),
          (0.052, 0.011), (0.034, 0.009), (0.0, 0.009)]
    B.add(key, lathe(sp, 20, sharp=40), M)
    z0 = 0.009
    cp = [(0.0, z0), (0.022, z0), (0.024, z0 + 0.003), (0.034, z0 + 0.025), (0.040, z0 + 0.06), (0.0405, z0 + 0.064),
          (0.0375, z0 + 0.064), (0.036, z0 + 0.05), (0.030, z0 + 0.02), (0.0, z0 + 0.012)]
    B.add(key, lathe(cp, 16, sharp=40), M)
    B.add(coffee, lathe([(0.0, z0 + 0.05), (0.0362, z0 + 0.05)], 16), M)
    hp = [(0.036, 0, z0 + 0.052), (0.052, 0, z0 + 0.05), (0.058, 0, z0 + 0.036), (0.05, 0, z0 + 0.024), (0.033, 0, z0 + 0.02)]
    B.add(key, tube(hp, 0.0042, sides=6), M)
    return z0 + 0.064


def mug(B, M, key="stoneware", coffee="charcoal", r=0.042, h=0.095):
    cp = [(0.0, 0.0), (r - 0.003, 0.0), (r, 0.004), (r, h - 0.002), (r - 0.002, h), (r - 0.005, h - 0.002),
          (r - 0.005, 0.012), (0.0, 0.010)]
    B.add(key, lathe(cp, 16, sharp=40), M)
    B.add(coffee, lathe([(0.0, h - 0.018), (r - 0.0048, h - 0.018)], 16), M)
    hp = [(r - 0.002, 0, h - 0.02), (r + 0.02, 0, h - 0.025), (r + 0.026, 0, h * 0.5), (r + 0.018, 0, 0.022), (r - 0.002, 0, 0.02)]
    B.add(key, tube(hp, 0.005, sides=6), M)
    return h


def open_book(B, M, w=0.15, d=0.22, t=0.012, cover="oat", ribbon=None):
    """A book lying open: two page blocks curving up out of a deep gutter and rolling over
    at the fore-edges, on cover boards that show round the pages; optional ribbon marker
    lying across the pages and trailing over the bottom edge."""
    bt = 0.0025
    xs = [0.0, 0.003, 0.009, 0.018, 0.032, 0.055, 0.09, w - 0.025, w - 0.008, w]
    f = [0.05, 0.38, 0.66, 0.84, 0.95, 1.0, 0.99, 0.96, 0.86, 0.7]
    for sx in (-1, 1):
        top = [(sx * x, bt + t * k) for x, k in zip(xs, f)]
        outline = top + [(sx * w, bt), (0.0, bt)]
        if sx < 0:
            outline = outline[::-1]
        B.add("paper", prism(outline, -d / 2, d / 2, smooth=True), M)
    board = cbox((2 * w + 0.016, d + 0.010, bt), 0.0008)
    B.add(cover, board, M @ Matrix.Translation((0, 0, bt / 2)))
    if ribbon:
        x0 = 0.012
        pts = [(x0, d * 0.25, bt + t * 0.5 + 0.0006), (x0 + 0.004, -d * 0.2, bt + t * 0.62 + 0.0006),
               (x0 + 0.006, -d / 2 + 0.002, bt + t * 0.55), (x0 + 0.007, -d / 2 - 0.004, bt * 0.5),
               (x0 + 0.012, -d / 2 - 0.03, 0.0006)]
        rb = bmesh.new()
        prev = None
        for p_ in pts:
            q = [rb.verts.new((p_[0] - 0.003, p_[1], p_[2])), rb.verts.new((p_[0] + 0.003, p_[1], p_[2]))]
            if prev:
                fc = rb.faces.new((prev[0], prev[1], q[1], q[0]))
                fc.smooth = True
            prev = q
        bmesh.ops.recalc_face_normals(rb, faces=rb.faces[:])
        for fc in rb.faces:
            if fc.normal.z < 0:
                fc.normal_flip()
        B.add(ribbon, rb, M)
    return bt + t


def tent_book(B, M, w=0.14, d=0.21, t=0.018, cover="ink"):
    """A book laid open face-down (a low tent over the surface)."""
    ang = math.radians(12)
    for sx in (-1, 1):
        R = Matrix.Rotation(sx * ang, 4, "Y")
        o = M @ Matrix.Translation((0, 0, math.sin(ang) * w)) @ R @ Matrix.Translation((sx * w / 2, 0, -t / 2))
        B.add(cover, cbox((w, d, 0.0025), 0.0008), o @ Matrix.Translation((0, 0, t / 2 - 0.0012)))
        B.add("paper", cbox((w - 0.004, d - 0.006, t - 0.003), drop=("+z",)), o @ Matrix.Translation((-sx * 0.002, 0, -0.001)))
    spine = tube([(0, -d / 2, math.sin(ang) * w + 0.002), (0, d / 2, math.sin(ang) * w + 0.002)], 0.006, sides=6)
    B.add(cover, spine, M)
    return math.sin(ang) * w + 0.006


def notebook(B, M, w=0.15, d=0.21, t=0.014, cover="ink", band="charcoal"):
    """Bound notebook (a slim book) with an elastic band round it."""
    book(B, M, w, d, t, cover)
    B.add(band, cbox((0.004, d + 0.002, t + 0.001), drop=("-z",)), M @ Matrix.Translation((w / 2 - 0.025, 0, t / 2 + 0.0004)))
    return t


def pen(B, M, key="bronze", L=0.14):
    B.add(key, tube([(-L / 2, 0, 0.005), (L / 2 - 0.01, 0, 0.005)], 0.0048, sides=8), M)
    B.add("charcoal", tube([(L / 2 - 0.012, 0, 0.005), (L / 2, 0, 0.005)], 0.0035, sides=8, taper=lambda s: 1 - 0.7 * s), M)
    B.add(key, cbox((0.035, 0.002, 0.004)), M @ Matrix.Translation((-L / 2 + 0.03, 0.0035, 0.008)))
    return 0.01


def towel(B, M, key, L=0.32, D=0.22, t=0.04):
    """Folded towel: the fold rounds the front (-Y), the hems sit squarer at the back."""
    out = bv.round_outline(-D / 2, D / 2, 0.0, t, t * 0.48, 0.008, segs=3)
    out = [(y, z - (0.002 if z > t * 0.9 and -D / 2 + 0.03 < y < D / 2 - 0.03 else 0.0)) for y, z in out]
    bm = bv.soft_extrude(out, -L / 2, L / 2, ease=0.010, inset=0.006)
    for f in bm.faces:
        f.smooth = True
    B.add(key, bm, M)
    return t


def towel_stack(B, M, rng, keys, sizes):
    """sizes [(L, D, t) ...] bottom -> top; returns the stack height."""
    z = 0.0
    for i, (L, D, t) in enumerate(sizes):
        towel(B, M @ at(rng.uniform(-0.006, 0.006), rng.uniform(-0.006, 0.006), z, rng.uniform(-2.5, 2.5)),
              keys[i % len(keys)], L, D, t)
        z += t - 0.003
    return z


def towel_roll(B, M, key, r=0.05, L=0.3, upright=False):
    """Rolled towel: a soft cylinder with eased ends and a spiral hint (stepped end disc)."""
    e = 0.006
    prof = [(0.0, -L / 2 + 0.004), (r * 0.45, -L / 2 + 0.006), (r * 0.5, -L / 2 + 0.002), (r - e, -L / 2),
            (r, -L / 2 + e), (r, L / 2 - e), (r - e, L / 2), (r * 0.5, L / 2 - 0.002), (r * 0.45, L / 2 - 0.006),
            (0.0, L / 2 - 0.004)]
    bm = lathe(prof, 12, sharp=60)
    if not upright:
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "Y"))
        bmesh.ops.translate(bm, vec=(0, 0, r * 0.94), verts=bm.verts)
        bmesh.ops.scale(bm, vec=(1, 1, 0.94), verts=bm.verts)
    else:
        bmesh.ops.translate(bm, vec=(0, 0, L / 2), verts=bm.verts)
    B.add(key, bm, M)
    return 2 * r * 0.94 if not upright else L


def pebbles(B, M, key="stoneware", n=3, rng=None, r=0.05):
    """Balanced stones: flattened river stones, each smaller, stacked."""
    rng = rng or random.Random(3)
    z = 0.0
    for i in range(n):
        s = r * (1 - 0.22 * i)
        rz = s * rng.uniform(0.38, 0.48)
        bm = ellipsoid(s * rng.uniform(1.0, 1.2), s * rng.uniform(0.8, 0.95), rz, u=14, v=6, flat=0.3)
        B.add(key, bm, M @ at(rng.uniform(-0.006, 0.006), rng.uniform(-0.004, 0.004), z + rz * 0.7, rng.uniform(0, 180)),
              smooth=True)
        z += rz * 0.7 + rz * 0.95
    return z


def ring_sculpture(B, M, key="bronze", R=0.07, r=0.012, base_key="marble"):
    """A bronze ring standing in a slot in a small stone block."""
    B.add(base_key, cbox((0.07, 0.05, 0.025), 0.003), M @ Matrix.Translation((0, 0, 0.0125)))
    pts = [(R * math.cos(2 * math.pi * k / 20), 0, 0.025 + R - 0.006 + R * math.sin(2 * math.pi * k / 20)) for k in range(21)]
    B.add(key, tube(pts, r, sides=8, caps=False), M)
    return 0.025 + 2 * R


def soap(B, M, key="paper", w=0.085, d=0.055, h=0.025):
    out = bv.round_outline(-d / 2, d / 2, 0.0, h, h * 0.45, h * 0.45, segs=3)
    bm = bv.soft_extrude(out, -w / 2, w / 2, ease=0.008, inset=0.006)
    for f in bm.faces:
        f.smooth = True
    B.add(key, bm, M)
    return h


def pump_bottle(B, M, key="charcoal", pump="brass", r=0.032, h=0.15):
    prof = [(0.0, 0.0), (r - 0.003, 0.0), (r, 0.004), (r, h * 0.82), (r * 0.8, h * 0.93), (r * 0.42, h * 0.97),
            (r * 0.42, h), (0.0, h)]
    B.add(key, lathe(prof, 16, sharp=35), M)
    B.add(pump, lathe([(0.0, h), (0.012, h), (0.012, h + 0.012), (0.0045, h + 0.016), (0.0045, h + 0.034), (0.0, h + 0.034)],
                      10, sharp=40), M)
    B.add(pump, cbox((0.012, 0.042, 0.01), 0.0015), M @ Matrix.Translation((0, -0.014, h + 0.038)))
    B.add(pump, tube([(0, -0.034, h + 0.038), (0, -0.044, h + 0.032)], 0.0028, sides=6), M)
    return h + 0.043


def leaf_strip(bm, uvl, base, d, side, L, Wd, rows=3, shape=(0.45, 0.95, 0.8), pitch=0.4, droop=0.3, fold=0.2):
    """A leaf on the library leaf texture (u across, v along): grid of rows x 2 quads
    folded on the midrib, tip collapsed. d = direction (unit), side = across (unit)."""
    grid = []
    for r in range(rows + 1):
        t = r / rows
        dist = t * L
        c = base + d * (math.cos(pitch) * dist) + Vector((0, 0, math.sin(pitch) * dist - droop * L * t * t))
        half = Wd * 0.5 * (shape[r] if r < rows else 0.0)
        fz = fold * half
        grid.append([bm.verts.new(c - side * half - Vector((0, 0, fz))), bm.verts.new(c),
                     bm.verts.new(c + side * half - Vector((0, 0, fz)))])
    for r in range(rows):
        for cc in range(2):
            if r == rows - 1:
                quad = [grid[r][cc], grid[r][cc + 1], grid[r + 1][1]]
                uvs = [(cc * 0.5, r / rows), (cc * 0.5 + 0.5, r / rows), (0.5, 1.0)]
            else:
                quad = [grid[r][cc], grid[r][cc + 1], grid[r + 1][cc + 1], grid[r + 1][cc]]
                uvs = [(cc * 0.5, r / rows), (cc * 0.5 + 0.5, r / rows), (cc * 0.5 + 0.5, (r + 1) / rows),
                       (cc * 0.5, (r + 1) / rows)]
            try:
                fc = bm.faces.new(quad)
            except ValueError:
                continue
            fc.smooth = True
            for lp, uv in zip(fc.loops, uvs):
                lp[uvl].uv = uv
    return grid[0][1].co.copy()


def petiole(bm, uvl, a, b, w=0.0025):
    a, b = Vector(a), Vector(b)
    d = (b - a)
    side = d.cross(Vector((0, 0, 1)))
    side = side.normalized() * w if side.length > 1e-6 else Vector((w, 0, 0))
    vs = [bm.verts.new(p) for p in (a - side, a + side, b + side, b - side)]
    fc = bm.faces.new(vs)
    for lp, uv in zip(fc.loops, ((0.49, 0.0), (0.51, 0.0), (0.51, 0.06), (0.49, 0.06))):
        lp[uvl].uv = uv


def small_plant(B, M, rng, pot="stoneware", r=0.055, h=0.075, leaves=11, size=0.07, kind="pilea", leaf="leaf",
                soil="soil"):
    """Desk / shelf plant: a small eased pot, soil, leaves on the library leaf texture.
    kind 'pilea': round leaves on long stalks radiating out; 'upright': taller pointed leaves."""
    pp = [(0.0, 0.0), (r * 0.78, 0.0), (r * 0.84, 0.006), (r, h * 0.8), (r * 1.01, h - 0.003), (r * 0.97, h),
          (r * 0.9, h), (r * 0.88, h - 0.012), (0.0, h - 0.012)]
    B.add(pot, lathe(pp, 16, sharp=40), M)
    B.add(soil, lathe([(0.0, h - 0.011), (r * 0.885, h - 0.011)], 16), M)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    for i in range(leaves):
        f = i / max(leaves - 1, 1)
        phi = i * 2.399963 + rng.uniform(-0.25, 0.25)
        d = Vector((math.cos(phi), math.sin(phi), 0))
        side = Vector((-math.sin(phi), math.cos(phi), 0))
        if kind == "pilea":
            reach = size * (0.35 + 0.9 * f ** 0.6) * rng.uniform(0.85, 1.1)
            zt = h + size * (1.6 - 1.1 * f) * rng.uniform(0.85, 1.15)
            tip = Vector((0, 0, h - 0.01)) + d * reach * 0.8 + Vector((0, 0, zt - h))
            petiole(bm, uvl, (0, 0, h - 0.01), tip, 0.0018)
            L = size * rng.uniform(0.75, 1.0)
            leaf_strip(bm, uvl, tip, d, side, L, L * 0.95, rows=3, shape=(0.55, 1.0, 0.75),
                       pitch=math.radians(rng.uniform(-5, 25)), droop=0.15, fold=0.15)
        else:
            base = Vector((0, 0, h - 0.01)) + d * 0.008
            L = size * rng.uniform(1.6, 2.2) * (1.0 - 0.3 * f)
            leaf_strip(bm, uvl, base, d, side, L, L * 0.32, rows=3, shape=(0.6, 1.0, 0.7),
                       pitch=math.radians(rng.uniform(50, 75)), droop=0.12, fold=0.25)
    B.add(leaf, bm, M)
    return h


def sprig(B, M, rng, n=7, L=0.16):
    """A cut eucalyptus sprig lying flat: a fine stem with paired round leaves."""
    stem = [(-L / 2 + L * k / 4, 0.006 * math.sin(k * 1.3), 0.004 + 0.002 * k / 4) for k in range(5)]
    B.add("bark", tube(stem, 0.0013, sides=4), M)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    for i in range(n):
        t = (i + 0.5) / n
        x = -L / 2 + L * (0.15 + 0.85 * t)
        s = 1 if i % 2 else -1
        d = Vector((0.35, s * 1.0, 0)).normalized()
        side = Vector((-d.y, d.x, 0))
        sz = 0.042 * (1.0 - 0.4 * t)
        leaf_strip(bm, uvl, Vector((x, 0, 0.005)), d, side, sz, sz * 0.95, rows=3, shape=(0.6, 1.0, 0.7),
                   pitch=math.radians(4), droop=0.02, fold=0.05)
    B.add("leaf", bm, M)
    return 0.01


def branch_spray(B, M, rng, n=4, height=0.75, spread=0.28, leaves=120, z0=0.0, twigs=2, arc=None):
    """Cut olive branches standing in a vase mouth at z0: stems leaning out and arching over
    at the top, side twigs, narrow grey-green leaves along their outer two thirds."""
    lb = bmesh.new()
    uvl = lb.loops.layers.uv.new("UVMap")
    stems = []
    for b in range(n):
        if arc:                                       # (centre, width) in degrees: keep off a wall
            phi = math.radians(arc[0] + arc[1] * ((b + 0.5) / n - 0.5)) + rng.uniform(-0.15, 0.15)
        else:
            phi = 2 * math.pi * b / n + rng.uniform(-0.45, 0.45)
        d = Vector((math.cos(phi), math.sin(phi), 0))
        H = height * rng.uniform(0.72, 1.05)
        S = spread * rng.uniform(0.6, 1.15)
        pts = [Vector((0, 0, z0 - 0.05)) + d * 0.004]
        for k in range(1, 7):
            t = k / 6
            pts.append(Vector((0, 0, z0)) + d * (S * t ** 1.5) + Vector((0, 0, H * (t - 0.18 * t ** 3))) +
                       Vector((rng.uniform(-0.012, 0.012), rng.uniform(-0.012, 0.012), 0)))
        B.add("bark", tube([tuple(p) for p in pts], 0.0055, sides=5, caps=True, taper=lambda s: 1 - 0.75 * s), M)
        stems.append((pts, 1.0))
        side0 = Vector((-d.y, d.x, 0))
        for k in range(twigs):
            k0 = 3 + k
            if k0 >= len(pts) - 1:
                break
            a = pts[k0]
            sd = side0 * (1 if (b + k) % 2 else -1)
            ln = rng.uniform(0.12, 0.2)
            tw = [a, a + (sd * 0.5 + d * 0.3) * ln * 0.5 + Vector((0, 0, ln * 0.45)),
                  a + (sd * 0.8 + d * 0.5) * ln + Vector((0, 0, ln * 0.6))]
            B.add("bark", tube([tuple(p) for p in tw], 0.003, sides=4, caps=True, taper=lambda s: 1 - 0.6 * s), M)
            stems.append((tw, 0.55))
    total = sum(w for _, w in stems)
    for stem, w in stems:
        segs = len(stem) - 1
        per = max(3, round(leaves * w / total))
        for i in range(per):
            t = 0.35 + 0.65 * ((i + rng.random() * 0.6) / per) ** 0.8
            u = min(t * segs, segs - 1e-3)
            k = int(u)
            p = stem[k].lerp(stem[k + 1], u - k)
            tan = (stem[k + 1] - stem[k]).normalized()
            ang = rng.uniform(0, 2 * math.pi)
            perp = tan.cross(Vector((math.cos(ang), math.sin(ang), 0.2))).normalized()
            dirv = (perp * 0.75 + tan * 0.65).normalized()
            dh = Vector((dirv.x, dirv.y, 0))
            dh = dh.normalized() if dh.length > 1e-4 else Vector((1, 0, 0))
            side = Vector((-dh.y, dh.x, 0))
            L = rng.uniform(0.07, 0.10) * (1.0 - 0.25 * t)
            pitch = math.asin(max(-0.9, min(0.9, dirv.z)))
            leaf_strip(lb, uvl, p, dh, side, L, L * 0.26, rows=2, shape=(0.85, 1.0), pitch=pitch, droop=0.25, fold=0.12)
    B.add("leaf", lb, M)
    return height


def stem_sprig(B, M, rng, h=0.22, leaves=7, lean=12.0, azim=None):
    """A single cut stem standing in a bud vase (M at the vase mouth, the stem's foot 4 cm
    inside): a fine curved twig with small narrow leaves toward its top, leaning `lean`
    degrees toward `azim` (degrees about Z; random if None)."""
    a = math.radians(rng.uniform(0, 360) if azim is None else azim + rng.uniform(-20, 20))
    d = Vector((math.cos(a), math.sin(a), 0))
    tl = math.radians(lean)
    pts = [Vector((0, 0, -0.04))]
    for k in range(1, 5):
        t = k / 4
        pts.append(Vector((0, 0, -0.04)) + d * (math.sin(tl) * h * t ** 1.4) + Vector((0, 0, (h + 0.04) * t)))
    B.add("bark", tube([tuple(p) for p in pts], 0.0016, sides=4, caps=True, taper=lambda s: 1 - 0.5 * s), M)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    for i in range(leaves):
        t = 0.45 + 0.55 * (i + 0.5) / leaves
        u = t * 4
        k = min(int(u), 3)
        p = pts[k].lerp(pts[k + 1], u - k)
        ang = i * 2.4 + rng.uniform(-0.3, 0.3)
        dh = Vector((math.cos(ang), math.sin(ang), 0))
        side = Vector((-dh.y, dh.x, 0))
        L = rng.uniform(0.04, 0.058) * (1.1 - 0.4 * t)
        leaf_strip(bm, uvl, p, dh, side, L, L * 0.3, rows=2, shape=(0.85, 1.0), pitch=math.radians(rng.uniform(15, 45)),
                   droop=0.2, fold=0.1)
    B.add("leaf", bm, M)
    return h


def slipper(B, M, side=1, sole="charcoal", upper="oat", L=0.27, footbed=None):
    """Closed-toe house slipper (right foot for side=1, left for -1): a felt sole, a lighter
    footbed, and a domed upper over the front half with a rolled throat."""
    # plan outline: toe at +Y, heel at -Y, the inner (arch) side toward -X*side
    def hw(t):          # half width along the length, t 0 heel .. 1 toe
        return 0.5 * (0.068 + 0.03 * math.sin(math.pi * min(t * 1.15, 1.0)) ** 0.8) * (1 - 0.85 * smoothstep(0.86, 1.0, t) ** 2)

    def shift(t):       # toes splay outward
        return side * 0.008 * smoothstep(0.4, 1.0, t)

    n = 10
    right, left = [], []
    for i in range(1, n):
        t = i / n
        y = -L / 2 + L * t
        right.append((shift(t) + hw(t), y))
        left.append((shift(t) - hw(t), y))
    toe = [(shift(1.0) + 0.6 * hw(1 - 1 / n), L / 2 - 0.004), (shift(1.0), L / 2 + 0.002),
           (shift(1.0) - 0.6 * hw(1 - 1 / n), L / 2 - 0.004)]
    h0 = hw(1 / n)
    heel = [(-0.65 * h0, -L / 2 + 0.003), (0.0, -L / 2), (0.65 * h0, -L / 2 + 0.003)]
    outline = right + toe + left[::-1] + heel
    st = 0.016
    rings = [(0.0, [(x * 0.97, y * 0.985) for x, y in outline]), (0.004, outline), (st, outline)]
    B.add(sole, loft(rings, smooth=False), M)
    fb = [(x * 0.93, y * 0.96) for x, y in outline]
    B.add(footbed or upper, loft([(st, fb), (st + 0.004, fb)], smooth=False), M)
    # upper: arches from the toe back to the throat at 58 % of the length
    bm = bmesh.new()
    arch = 6
    stations = 5
    rows_o, rows_i = [], []
    for s in range(stations + 1):
        u = s / stations
        t = 1.0 - 0.42 * u                      # 1 at the toe -> 0.58
        y = -L / 2 + L * t
        w = hw(t) + 0.003
        hgt = 0.012 + 0.052 * math.sin(math.pi / 2 * min(1.0, 0.25 + u * 1.1)) ** 0.7
        if s == 0:
            w, hgt = w * 0.5, hgt * 0.55
        ro, ri = [], []
        for k in range(arch):
            a = math.pi * k / (arch - 1)
            ro.append(bm.verts.new((shift(t) + w * math.cos(a), y, st + hgt * math.sin(a))))
            ri.append(bm.verts.new((shift(t) + (w - 0.006) * math.cos(a), y, st + 0.002 + (hgt - 0.007) * math.sin(a))))
        rows_o.append(ro)
        rows_i.append(ri)
    for s in range(stations):
        for k in range(arch - 1):
            bm.faces.new((rows_o[s][k], rows_o[s][k + 1], rows_o[s + 1][k + 1], rows_o[s + 1][k]))
            bm.faces.new((rows_i[s][k + 1], rows_i[s][k], rows_i[s + 1][k], rows_i[s + 1][k + 1]))
        for k in (0, arch - 1):                 # the strip along the sole
            bm.faces.new((rows_o[s][k], rows_o[s + 1][k], rows_i[s + 1][k], rows_i[s][k]))
    for k in range(arch - 1):                   # toe closure and the rolled throat edge
        bm.faces.new((rows_o[0][k + 1], rows_o[0][k], rows_i[0][k], rows_i[0][k + 1]))
        bm.faces.new((rows_o[-1][k], rows_o[-1][k + 1], rows_i[-1][k + 1], rows_i[-1][k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        f.smooth = True
    B.add(upper, bm, M)
    return st


def drape_band(path, t, gap=0.001):
    """Closed (y, z) outline of a cloth band of thickness t following `path` (a polyline in
    the y-z plane) on the side its left normal points to (cloth over a surface)."""
    P = [Vector(q) for q in path]
    a_side, b_side = [], []
    for i, q in enumerate(P):
        d = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        nrm = Vector((-d.y, d.x))
        a_side.append(q + nrm * (gap + t))
        b_side.append(q + nrm * gap)
    return [tuple(v) for v in a_side] + [tuple(v) for v in reversed(b_side)]


def basket(B, M, key, r=0.2, h=0.34, ribs=9, segs=14, part="Basket"):
    """Woven rope basket: ribbed wall (alternating radius), a rolled rim, open top, thick
    floor; the inside visible. Returns the floor height."""
    prof = [(0.0, 0.0), (r * 0.92 - 0.006, 0.0), (r * 0.92, 0.006)]
    for k in range(ribs):
        z0 = 0.012 + (h - 0.03) * k / ribs
        z1 = 0.012 + (h - 0.03) * (k + 0.5) / ribs
        rr = r * (0.92 + 0.08 * z0 / h)
        prof += [(rr, z0), (rr + 0.008, z1)]
    prof += [(r + 0.006, h - 0.016), (r + 0.010, h - 0.006), (r + 0.004, h), (r - 0.008, h - 0.004), (r - 0.012, h - 0.016),
             (r * 0.92 - 0.012, 0.05), (r * 0.6, 0.03), (0.0, 0.03)]
    B.add(key + "@" + part, lathe(prof, segs, sharp=50), M)
    return 0.03


# ------------------------------------------------------------------ pickups
# the loose things a player expects to lift (lib/pickups.py has the rule): each call of these
# becomes its own pickup; trays, plants and sprays, towels, slippers and baskets stay furniture
pickups.wrap(sys.modules[__name__], "meshes", items=dict(
    book="book", vessel="vase", bowl="bowl", candle="candle", candle_jar="candle", carafe="carafe",
    tumbler="glass", wine_glass="wine_glass", perfume="perfume", glasses="spectacles", cup_saucer="cup",
    mug="mug", open_book="book", tent_book="book", notebook="notebook", pebbles="ornament",
    ring_sculpture="ornament", soap="soap", pump_bottle="soap_pump",
), fixed=("small_plant", "sprig", "branch_spray", "stem_sprig"))
