"""Shared building blocks for the firepit_* assets (not an asset itself): bmesh boxes with
real bevels (no modifiers, because the grounds copy raw mesh data), arc sweeps, lathes,
outline walls and the zone's flat colours. All transforms are baked into the vertices.
"""
import importlib
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, outdoor  # noqa: E402

importlib.reload(common)
importlib.reload(outdoor)

# ------------------------------------------------------------------ colours (linear RGB)
def basalt():
    return outdoor.flat("M_Out_Basalt", (0.05, 0.05, 0.055))


def sand_cushion():
    return outdoor.cushion("Sand", (0.52, 0.47, 0.39))


def charcoal_cushion():
    return outdoor.cushion("Charcoal", (0.045, 0.045, 0.05))


def ember():
    return outdoor.lamp("Ember")


def coal():
    return outdoor.flat("M_Out_Coal", (0.02, 0.014, 0.012))


def edging():
    """Black steel landscape edging."""
    return outdoor.flat("M_Out_Metal_Dark", (0.025, 0.025, 0.027))


# ------------------------------------------------------------------ objects
def new_asset(name):
    col = common.fresh_collection(name)
    root = common.empty(name, col)
    return col, root


def finish(bm, name, col, root, mat, smooth=False, uv_tile=None):
    ob = common.mesh_object(name, bm, col, mat, root, smooth=smooth)
    if uv_tile:
        common.box_uv(ob, tile=uv_tile)
    return ob


def transform(bm, loc=(0, 0, 0), rot=(0, 0, 0)):
    """rot: degrees about X, Y, Z (applied in that order) around the origin, then loc."""
    m = Matrix.Translation(loc) @ Matrix.Rotation(math.radians(rot[2]), 4, "Z") \
        @ Matrix.Rotation(math.radians(rot[1]), 4, "Y") @ Matrix.Rotation(math.radians(rot[0]), 4, "X")
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)


def box_bm(size, loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.0, bm=None):
    """Box of `size` centred at `loc`. Added to `bm` if given, else a new bmesh."""
    own = bm is None
    tmp = bmesh.new()
    bmesh.ops.create_cube(tmp, size=1.0)
    bmesh.ops.scale(tmp, vec=Vector(size), verts=tmp.verts)
    if bevel:
        bmesh.ops.bevel(tmp, geom=tmp.edges[:], offset=bevel, segments=1, affect="EDGES")
    transform(tmp, loc, rot)
    if own:
        return tmp
    mesh = bpy.data.meshes.new("_tmp")
    tmp.to_mesh(mesh)
    tmp.free()
    bm.from_mesh(mesh)
    bpy.data.meshes.remove(mesh)
    return bm


def box(name, size, loc, mat, col, root, rot=(0, 0, 0), bevel=0.0, uv_tile=None):
    return finish(box_bm(size, loc, rot, bevel), name, col, root, mat, uv_tile=uv_tile)


def merge_boxes(name, specs, mat, col, root, uv_tile=None):
    """One object from many boxes: specs = [(size, loc, rot, bevel), ...]."""
    bm = bmesh.new()
    for size, loc, rot, bevel in specs:
        box_bm(size, loc, rot, bevel, bm)
    return finish(bm, name, col, root, mat, uv_tile=uv_tile)


# ------------------------------------------------------------------ sweeps
def sweep_bm(profile, a0, a1, n, centre=(0, 0), z0=0.0, caps=True, bm=None):
    """Sweep a (r, z) profile, listed counter-clockwise (right side up), round Z from angle
    a0 to a1 (degrees) in n steps. The polygon closes from last point to first, but that
    closing edge gets no side faces (bottoms sit on the ground and are never seen)."""
    bm = bm or bmesh.new()
    m = len(profile)
    rows = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        rows.append([bm.verts.new((centre[0] + r * math.cos(a), centre[1] + r * math.sin(a), z0 + z))
                     for r, z in profile])
    for i in range(n):
        for j in range(m - 1):
            bm.faces.new((rows[i][j], rows[i + 1][j], rows[i + 1][j + 1], rows[i][j + 1]))
    if caps:
        bm.faces.new(rows[0])
        bm.faces.new(rows[n][::-1])
    return bm


def lathe_bm(profile, segs, bm=None, z0=0.0, closed=True):
    """Revolve an (r, z) polygon (counter-clockwise, r >= 0) fully round Z; closed=False leaves
    the last-to-first edge (the hidden underside) out.
    Points on the axis (r = 0) collapse to one vertex."""
    bm = bm or bmesh.new()
    m = len(profile)
    rows = []
    axis = {}
    for j, (r, z) in enumerate(profile):
        if r < 1e-9:
            axis[j] = bm.verts.new((0, 0, z0 + z))
            rows.append(None)
        else:
            rows.append([bm.verts.new((r * math.cos(2 * math.pi * s / segs),
                                       r * math.sin(2 * math.pi * s / segs), z0 + z)) for s in range(segs)])

    def v(j, s):
        return axis[j] if rows[j] is None else rows[j][s % segs]

    for j in range(m if closed else m - 1):
        k = (j + 1) % m
        for s in range(segs):
            quad = []
            for vt in (v(j, s), v(j, s + 1), v(k, s + 1), v(k, s)):
                if vt not in quad:
                    quad.append(vt)
            if len(quad) >= 3:
                bm.faces.new(quad)
    return bm


def wall_loop_bm(pts, thick, z0, z1, closed=True, bm=None):
    """A thin vertical wall (top + both faces) along a polyline in XY."""
    bm = bm or bmesh.new()
    n = len(pts)
    P = [Vector((p[0], p[1], 0)) for p in pts]
    off = []
    for i in range(n):
        a = P[(i - 1) % n] if (closed or i > 0) else P[i]
        b = P[(i + 1) % n] if (closed or i < n - 1) else P[i]
        t = (b - a).normalized()
        nrm = Vector((-t.y, t.x, 0))
        d1 = (P[i] - a).normalized() if (a - P[i]).length > 1e-9 else t
        d2 = (b - P[i]).normalized() if (b - P[i]).length > 1e-9 else t
        mid = Vector((-(d1 + d2).y, (d1 + d2).x, 0)).normalized()
        k = 1.0 / max(0.5, mid.dot(Vector((-d1.y, d1.x, 0))))
        off.append(mid * k * thick / 2)
    L = [bm.verts.new((P[i].x + off[i].x, P[i].y + off[i].y, z1)) for i in range(n)]
    R = [bm.verts.new((P[i].x - off[i].x, P[i].y - off[i].y, z1)) for i in range(n)]
    Lb = [bm.verts.new((P[i].x + off[i].x, P[i].y + off[i].y, z0)) for i in range(n)]
    Rb = [bm.verts.new((P[i].x - off[i].x, P[i].y - off[i].y, z0)) for i in range(n)]
    for i in range(n if closed else n - 1):
        j = (i + 1) % n
        bm.faces.new((R[i], R[j], L[j], L[i]))          # top
        bm.faces.new((L[i], L[j], Lb[j], Lb[i]))        # left face
        bm.faces.new((Rb[i], Rb[j], R[j], R[i]))        # right face
    return bm


def orient_up(bm):
    """Flip any face on a flat upward surface that points down."""
    bad = [f for f in bm.faces if f.normal.z < -0.5]
    bmesh.ops.reverse_faces(bm, faces=bad)


def fix_outward(bm, centre=(0, 0)):
    """Make every face point away from the vertical axis through `centre`, unless it is
    mostly horizontal (then up). For simple radial solids built from loose quads."""
    bm.normal_update()
    flip = []
    for f in bm.faces:
        c = f.calc_center_median()
        radial = Vector((c.x - centre[0], c.y - centre[1], 0))
        if abs(f.normal.z) > 0.7:
            if f.normal.z < 0:
                flip.append(f)
        elif radial.dot(f.normal) < 0:
            flip.append(f)
    bmesh.ops.reverse_faces(bm, faces=flip)
