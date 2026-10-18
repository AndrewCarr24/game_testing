"""Shared helpers for the primary bath assets and room (not an asset itself).

Materials: book-matched Calacatta-style wall/floor marble, dark Marquina-style
feature marble, honed white stone, white ceramic, mirror, brushed brass.
Textures (T_Bath_*) are written with numpy and only regenerated when missing.
Book-matching: one quadrant of marble is mirrored in both directions, so every
tile is seamless and every neighbouring tile mirrors the veins across the joint.
"""
import importlib
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(materials)

WALL_TEX = "T_Bath_Marble_BaseColor"
DARK_TEX = "T_Bath_MarbleDark_BaseColor"
FLOOR_TEX = "T_Bath_MarbleFloor_BaseColor"


# ---------------------------------------------------------------- textures

def _unit(a):
    return a / (a.std() + 1e-9)


def _lines(f, period, width, offset=0.0):
    """Periodic gaussian lines along the level sets of f (period / width in tile fractions)."""
    d = ((f + offset) % period) - period / 2
    return np.exp(-(d / width) ** 2)


def _smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def _quadrant(seed, dark, m=512):
    """One m x m quadrant of marble, linear RGB (m, m, 3)."""
    n = 2 * m
    rng = np.random.default_rng(seed)
    nz = lambda beta: textures._noise(n, 1.0, 1.0, beta, rng)[:m, :m]
    big, mid, fine = _unit(nz(2.4)), _unit(nz(1.8)), _unit(nz(1.2))
    cloud = nz(2.6) * 0.5 + 0.5
    mask1, mask2, mask3 = (_smooth(-1.6, 0.2, _unit(nz(2.4))) for _ in range(3))
    x = np.linspace(0, 0.5, m, endpoint=False)[None, :] * np.ones((m, 1))
    y = np.linspace(0, 0.5, m, endpoint=False)[:, None] * np.ones((1, m))

    def field(angle, wob):
        a = math.radians(angle)
        return x * math.cos(a) + y * math.sin(a) + wob * big + 0.25 * wob * mid + 0.0035 * fine

    f1, f2, f3 = field(34 if not dark else 55, 0.075), field(-18, 0.06), field(70, 0.05)
    wv = 0.7 + 0.6 * _smooth(-1, 1, _unit(nz(2.0)))
    v1 = _lines(f1, 0.62, 0.0075 * wv) * mask1
    halo = _lines(f1, 0.62, 0.030) * mask1
    v2 = _lines(f2, 0.33, 0.0042 * wv, 0.07) * mask2
    v3 = _lines(f3, 0.17, 0.0020 * wv, 0.03) * mask3
    if not dark:
        base = np.array([0.80, 0.785, 0.755])
        warm = np.array([0.70, 0.60, 0.46])
        grey = np.array([0.28, 0.285, 0.31])
        lin = base * (0.93 + 0.07 * cloud)[..., None]
        lin = lin * (1 - 0.25 * halo[..., None]) + warm * 0.25 * halo[..., None] * 0.9
        for v, wgt in ((v3, 0.55), (v2, 0.8), (v1, 0.95)):
            lin = lin * (1 - wgt * v[..., None]) + grey * wgt * v[..., None]
    else:
        base = np.array([0.0085, 0.0088, 0.010]) * (0.7 + 0.9 * cloud)[..., None]
        lin = base + 0.020 * halo[..., None]
        white = np.array([0.66, 0.65, 0.63])
        for v, wgt in ((v3, 0.5), (v2, 0.8), (v1, 0.95)):
            lin = lin * (1 - wgt * v[..., None]) + white * wgt * v[..., None]
    return lin


def _mirror4(q):
    top = np.concatenate([q, q[:, ::-1]], axis=1)
    return np.concatenate([top, top[::-1]], axis=0)


def marble_texture(kind="wall"):
    """Returns the texture path, generating it when missing. One tile = 1 m (wall),
    1 tile per floor_uv_tile (floor, with 3 mm joints)."""
    name = {"wall": WALL_TEX, "dark": DARK_TEX, "floor": FLOOR_TEX}[kind]
    path = os.path.join(textures.TEX_DIR, name + ".png")
    if os.path.exists(path):
        return path
    seed = {"wall": 41, "dark": 53, "floor": 67}[kind]
    q = _quadrant(seed, kind == "dark")
    lin = _mirror4(q)
    if kind == "floor":
        lin = lin * np.array([0.82, 0.79, 0.74])        # a warmer, deeper greige than the walls
        j = 2                                   # hairline joints at the tile edge and across the middle
        m = lin.shape[0] // 2
        for sl in (np.s_[:j, :], np.s_[-j:, :], np.s_[:, :j], np.s_[:, -j:],
                   np.s_[m - j:m + j, :], np.s_[:, m - j:m + j]):
            lin[sl] *= 0.38
    return textures._save(name, textures._to_srgb(np.clip(lin, 0, 1)))


# --------------------------------------------------------------- materials

def marble_wall():
    m = common.pbr_material("M_Bath_Marble", (0.8, 0.78, 0.75), roughness=0.22, coat=0.35)
    common.set_base_color_map(m, textures.load(marble_texture("wall")))
    return m


def marble_dark():
    m = common.pbr_material("M_Bath_MarbleDark", (0.05, 0.05, 0.05), roughness=0.16, coat=0.5)
    common.set_base_color_map(m, textures.load(marble_texture("dark")))
    return m


def marble_floor():
    m = common.pbr_material("M_Bath_MarbleFloor", (0.8, 0.78, 0.75), roughness=0.14, coat=0.5)
    common.set_base_color_map(m, textures.load(marble_texture("floor")))
    return m


def wall_base():
    """Honed warm-white backing wall (shows only in the joints between the marble slabs)."""
    return common.pbr_material("M_Bath_WallBase", (0.74, 0.72, 0.68), roughness=0.5)


def wall_base_dark():
    return common.pbr_material("M_Bath_WallBaseDark", (0.012, 0.012, 0.014), roughness=0.4)


def stone():
    """Honed warm-white solid stone (tub, basins' surround, stools)."""
    return common.pbr_material("M_Bath_Stone", (0.74, 0.715, 0.67), roughness=0.5)


def ceramic():
    return common.pbr_material("M_Bath_Ceramic", (0.88, 0.88, 0.86), roughness=0.07, coat=0.3)


def mirror():
    return common.pbr_material("M_Bath_Mirror", (0.86, 0.88, 0.89), roughness=0.015, metallic=1.0)


def brass():
    """Brushed champagne brass for taps and sconces."""
    return common.pbr_material("M_Bath_Brass", (0.62, 0.46, 0.24), roughness=0.28, metallic=1.0)


def frosted(name="M_Bath_Frosted", strength=2.2):
    return materials.emissive(name, (1.0, 0.82, 0.58), strength)


# -------------------------------------------------------------- geometry

def lathe(profile, segs, closed=False, sharp=40.0):
    """Revolve profile [(r, z), ...] about Z (r == 0 collapses to the axis)."""
    bm = bmesh.new()
    rows = []
    for r, z in profile:
        if abs(r) < 1e-9:
            rows.append([bm.verts.new((0.0, 0.0, z))] * segs)
        else:
            rows.append([bm.verts.new((r * math.cos(2 * math.pi * s / segs),
                                       r * math.sin(2 * math.pi * s / segs), z))
                         for s in range(segs)])
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
                bm.faces.new(quad)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-7)
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
                if e is not None and e.is_valid:
                    e.smooth = False
    return bm


def catmull(pts, per=6):
    """Catmull-Rom through 2D points -> dense polyline (ends included)."""
    q = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(q) - 2):
        p0, p1, p2, p3 = q[i - 1], q[i], q[i + 1], q[i + 2]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t +
                                    (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 +
                                    (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(q[-2])
    return out


def cylinder_between(bm, a, b, radius, segs=8, cap=True):
    a, b = Vector(a), Vector(b)
    d = b - a
    rot = d.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
    m = Matrix.Translation((a + b) / 2) @ rot
    bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=segs,
                          radius1=radius, radius2=radius, depth=d.length, matrix=m)


def cylindrical_uv(ob, tile=0.5, axis_tiles=1.0):
    """u along z, v once round the circumference; flat caps planar."""
    me = ob.data
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        if abs(poly.normal.z) > 0.92:
            for li in poly.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                uv.data[li].uv = (co.x / tile, co.y / tile)
            continue
        angs = [math.atan2(me.vertices[me.loops[li].vertex_index].co.y,
                           me.vertices[me.loops[li].vertex_index].co.x) for li in poly.loop_indices]
        a0 = angs[0]
        for li, a in zip(poly.loop_indices, angs):
            d = a - a0
            d -= 2 * math.pi * round(d / (2 * math.pi))
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (co.z / tile, (a0 + d) / (2 * math.pi) * axis_tiles)


def superellipse(a, b, n, segs):
    pts = []
    for i in range(segs):
        t = 2 * math.pi * i / segs
        c, s = math.cos(t), math.sin(t)
        pts.append((a * math.copysign(abs(c) ** (2 / n), c), b * math.copysign(abs(s) ** (2 / n), s)))
    return pts


def loft(rings, segs, close_bottom=True):
    """rings: [(z, [(x, y)...]) ...] bottom -> top, or a ('pole', x, y, z) entry."""
    bm = bmesh.new()
    rows = []
    for ring in rings:
        if ring[0] == "pole":
            _, x, y, z = ring
            rows.append([bm.verts.new((x, y, z))] * segs)
        else:
            z, pts = ring
            rows.append([bm.verts.new((x, y, z)) for x, y in pts])
    for i in range(len(rows) - 1):
        a, b = rows[i], rows[i + 1]
        for s in range(segs):
            t = (s + 1) % segs
            quad = []
            for v in (a[s], a[t], b[t], b[s]):
                if v not in quad:
                    quad.append(v)
            if len(quad) >= 3:
                bm.faces.new(quad)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def box(col, root, name, size, centre, mat, bevel=0.002, uv_tile=None, parent=None, smooth=True):
    """Box part: `name` is the full object name. Optional bevel and box UVs."""
    ob = common.mesh_object(name, common.box_bmesh(size), col, mat, parent or root, smooth=smooth)
    ob.location = centre
    if bevel:
        common.add_bevel(ob, bevel, segments=2)
    if uv_tile:
        common.box_uv(ob, tile=uv_tile)
    return ob


def merge(root, objs, name):
    """Join mesh objects (modifiers applied) into one object called `name`: fewer draw calls.
    Objects must share a material. Meshes named with 'Piping' get no collider in the level."""
    objs = [o for o in objs if o is not None and o.name in bpy.data.objects]
    if not objs:
        return None
    vl = bpy.context.view_layer
    for o in list(vl.objects.selected):
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    vl.objects.active = objs[0]
    bpy.ops.object.convert(target="MESH")
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = vl.objects.active
    ob.name = name
    ob.data.name = name
    ob.select_set(False)
    return ob


def by_material(root, mat):
    """Mesh children of root whose first material is `mat`."""
    return [o for o in root.children_recursive
            if o.type == "MESH" and o.data.materials and o.data.materials[0] == mat]


def children(root, *needles):
    """Mesh children of root whose name contains any of the needles."""
    return [o for o in root.children_recursive if o.type == "MESH" and any(k in o.name for k in needles)]


def parts_of(root):
    return [o for o in root.children_recursive if o.type == "MESH"]
