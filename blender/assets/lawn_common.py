"""Shared building blocks for the lawn_* assets (not an asset itself): materials and
geometry helpers for the south sculpture lawn. Everything is outdoors, so materials come
from lib/outdoor.py (flat colours are free; textured ones are the shared palette)."""
import importlib
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, outdoor  # noqa: E402

importlib.reload(common)
importlib.reload(outdoor)


# ------------------------------------------------------------------ materials
def bronze_polished():
    """Warm polished bronze: brighter than the shared dark bronze so it glints at distance."""
    return outdoor.flat("M_Out_Bronze_Polished", (0.30, 0.165, 0.065))


def stone_pale():
    """Honed pale stone for monolithic sculpture (no paving joints)."""
    return outdoor.flat("M_Out_Stone_Pale", (0.56, 0.535, 0.48))


def steel_weathered():
    """Dark, warm weathered steel."""
    return outdoor.flat("M_Out_Steel_Weathered", (0.085, 0.045, 0.027))


def gravel_pale():
    return outdoor.gravel()


# ------------------------------------------------------------------ geometry
def finish(name, bm, col, root, mat, smooth=False, uv_tile=None):
    ob = common.mesh_object(name, bm, col, mat, root, smooth=smooth)
    if uv_tile:
        common.box_uv(ob, tile=uv_tile)
    return ob


def box_bmesh(lo, hi, step=1.5):
    """Axis-aligned box lo..hi whose horizontal axes are cut every <= `step` metres
    (vertex lighting needs the resolution to show shadows); vertical axis cut too."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=[hi[i] - lo[i] for i in range(3)], verts=bm.verts)
    bmesh.ops.translate(bm, vec=[(hi[i] + lo[i]) / 2 for i in range(3)], verts=bm.verts)
    for axis in (0, 1, 2):
        span = hi[axis] - lo[axis]
        n = max(1, math.ceil(span / step - 1e-6))
        for k in range(1, n):
            c = lo[axis] + span * k / n
            no = [0, 0, 0]
            no[axis] = 1
            co = [0, 0, 0]
            co[axis] = c
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def box(name, lo, hi, mat, col, root, step=1.5, uv_tile=None, skip_bottom=True, skip=()):
    """skip: faces to leave out because they are buried: any of "+x" "-x" "+y" "-y" "+z"."""
    bm = box_bmesh(lo, hi, step)
    drop = []
    for f in bm.faces:
        n = f.normal
        if skip_bottom and n.z < -0.9:
            drop.append(f)
        for tag, (ax, sg) in {"+x": (0, 1), "-x": (0, -1), "+y": (1, 1), "-y": (1, -1), "+z": (2, 1)}.items():
            if tag in skip and n[ax] * sg > 0.9:
                drop.append(f)
    bmesh.ops.delete(bm, geom=list(set(drop)), context="FACES_ONLY")
    return finish(name, bm, col, root, mat, smooth=False, uv_tile=uv_tile)


def grid_pad(name, x0, y0, x1, y1, z, mat, col, root, step=1.5, uv_tile=None):
    """Upward-facing flat grid with cells <= `step`."""
    nx = max(1, math.ceil((x1 - x0) / step - 1e-6))
    ny = max(1, math.ceil((y1 - y0) / step - 1e-6))
    bm = bmesh.new()
    vs = {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            vs[i, j] = bm.verts.new((x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny, z))
    for i in range(nx):
        for j in range(ny):
            bm.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
    return finish(name, bm, col, root, mat, smooth=False, uv_tile=uv_tile)


def sweep(bm, rings, cap=True, loop=False):
    """Skin a list of rings (each a list of points, same count, same winding) into a
    closed solid. loop=True joins the last ring back to the first (no caps)."""
    vr = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(vr[0])
    last = len(vr) if loop else len(vr) - 1
    for i in range(last):
        a, b = vr[i], vr[(i + 1) % len(vr)]
        for k in range(n):
            k2 = (k + 1) % n
            bm.faces.new((a[k], a[k2], b[k2], b[k]))
    if cap and not loop:
        bm.faces.new(vr[0][::-1])
        bm.faces.new(vr[-1])
    return vr


def finish_solid(bm, hard_angle_deg=35.0):
    """Orient normals outward and split edges sharper than `hard_angle_deg`, so smooth
    shading rounds the long sweeps but keeps crisp arrises."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    sharp = [e for e in bm.edges if e.is_manifold and e.calc_face_angle(0.0) > math.radians(hard_angle_deg)]
    if sharp:
        bmesh.ops.split_edges(bm, edges=sharp)
    return bm


def refine(bm, max_len=1.5):
    """Cut quads whose edges exceed `max_len` across that direction only (no slivers),
    repeating until every edge is short enough. Triangles are left alone."""
    for _ in range(6):
        cut = set()
        for f in bm.faces:
            if len(f.verts) != 4:
                continue
            es = list(f.edges)
            for e in es:
                if e.calc_length() > max_len:
                    cut.add(e)
                    for o in es:       # the opposite edge of the quad
                        if o is not e and not (set(o.verts) & set(e.verts)):
                            cut.add(o)
        if not cut:
            break
        bmesh.ops.subdivide_edges(bm, edges=list(cut), cuts=1, use_grid_fill=True)
    return bm
