"""Shared building blocks for the cabana_* assets (the pool house zone); not an asset itself.

Everything is built from boxes whose big faces can be cut into cells (outdoor lighting is
baked per vertex, so a shadow can only show up where there are vertices), plus a few
cylinders and quads. Materials come from lib/outdoor.py only.
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

_DIRS = {"+x": (1, 0, 0), "-x": (-1, 0, 0), "+y": (0, 1, 0), "-y": (0, -1, 0), "+z": (0, 0, 1), "-z": (0, 0, -1)}


# ------------------------------------------------------------------ materials
def M():
    """The palette of the pool house (all from lib/outdoor.py)."""
    return dict(
        stone=outdoor.stone(), teak=outdoor.teak(), foliage=outdoor.foliage(),
        glass=outdoor.glass(), dark=outdoor.dark_metal(), bronze=outdoor.bronze(),
        white=outdoor.render_white(), concrete=outdoor.concrete(),
        sand=outdoor.cushion("Sand", (0.55, 0.50, 0.42)),
        charcoal=outdoor.cushion("Charcoal", (0.05, 0.05, 0.055)),
        cream=outdoor.cushion("Cream", (0.62, 0.59, 0.52)),
        clay=outdoor.cushion("Clay", (0.30, 0.15, 0.09)),
        steel=outdoor.flat("M_Out_Steel", (0.20, 0.205, 0.21)),
        warm_dark=outdoor.flat("M_Out_Metal_Warm", (0.045, 0.04, 0.036)),
        lamp=outdoor.lamp("Warm"),
        gravel=outdoor.gravel(),
        rug=outdoor.flat("M_Out_Rug_Flax", (0.36, 0.31, 0.23)),
    )


def tex_tile(mat):
    n = mat.name
    if "Teak" in n:
        return 0.5
    if "Stone" in n:
        return 2.0
    if "Hedge" in n:
        return 1.5
    if "Gravel" in n:
        return 2.0
    return None


# ------------------------------------------------------------------ geometry
def _finish(bm, name, mat, col, parent, smooth=False):
    ob = common.mesh_object(name, bm, col, mat, parent, smooth=smooth)
    t = tex_tile(mat) if mat else None
    if t:
        common.box_uv(ob, tile=t)
    return ob


def box(name, lo, hi, mat, col, parent, step=None, drop=(), keep=None, top=None, bevel=0.0):
    """Axis-aligned box from lo to hi. step: cut every face into cells <= step metres.
    drop / keep: face directions ("+z", "-y", ...) to delete / the only ones to keep.
    top: a second material for the +z faces. bevel: a 1-segment chamfer (soft edges)."""
    d = [hi[i] - lo[i] for i in range(3)]
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=d, verts=bm.verts)
    bmesh.ops.translate(bm, vec=[(hi[i] + lo[i]) / 2 for i in range(3)], verts=bm.verts)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=1, affect="EDGES")
    if step:
        for ax in range(3):
            n = max(1, math.ceil(d[ax] / step - 1e-6))
            for k in range(1, n):
                co, no = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
                co[ax] = lo[ax] + d[ax] * k / n
                no[ax] = 1.0
                bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no)
    bm.faces.ensure_lookup_table()
    kill = []
    for f in bm.faces:
        nm = f.normal
        dirn = max(_DIRS, key=lambda k: nm.dot(Vector(_DIRS[k])))
        if nm.dot(Vector(_DIRS[dirn])) < 0.9:
            continue          # chamfer faces stay
        if dirn in drop or (keep is not None and dirn not in keep):
            kill.append(f)
    if kill:
        bmesh.ops.delete(bm, geom=kill, context="FACES")
    if top is not None:
        for f in bm.faces:
            if f.normal.z > 0.9:
                f.material_index = 1
    ob = common.mesh_object(name, bm, col, mat, parent, smooth=False)
    if top is not None:
        ob.data.materials.append(top)
    t = tex_tile(mat) if mat else None
    if t or (top is not None and tex_tile(top)):
        common.box_uv(ob, tile=t or tex_tile(top))
    return ob


def grid(name, lo, hi, z, mat, col, parent, step=1.5, up=True, uv=None):
    """Horizontal grid of quads between lo (x, y) and hi (x, y) at height z, facing up (or down)."""
    nx = max(1, math.ceil((hi[0] - lo[0]) / step - 1e-6))
    ny = max(1, math.ceil((hi[1] - lo[1]) / step - 1e-6))
    bm = bmesh.new()
    v = {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            v[i, j] = bm.verts.new((lo[0] + (hi[0] - lo[0]) * i / nx, lo[1] + (hi[1] - lo[1]) * j / ny, z))
    for i in range(nx):
        for j in range(ny):
            q = (v[i, j], v[i + 1, j], v[i + 1, j + 1], v[i, j + 1])
            bm.faces.new(q if up else q[::-1])
    ob = common.mesh_object(name, bm, col, mat, parent, smooth=False)
    t = uv or (tex_tile(mat) if mat else None)
    if t:
        me = ob.data
        layer = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
        for p in me.polygons:
            for li in p.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                layer.data[li].uv = (co.x / t, co.y / t)
    return ob


def quad(name, pts, mat, col, parent):
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in pts]
    bm.faces.new(vs)
    return common.mesh_object(name, bm, col, mat, parent, smooth=False)


def cyl(name, centre, r, z0, z1, mat, col, parent, seg=12, caps=(True, True), r1=None):
    """Upright cylinder / cone frustum (r at the bottom, r1 at the top)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r,
                          radius2=r if r1 is None else r1, depth=z1 - z0)
    bmesh.ops.translate(bm, vec=(centre[0], centre[1], (z0 + z1) / 2), verts=bm.verts)
    kill = [f for f in bm.faces if (f.normal.z > 0.9 and not caps[1]) or (f.normal.z < -0.9 and not caps[0])]
    if kill:
        bmesh.ops.delete(bm, geom=kill, context="FACES")
    ob = common.mesh_object(name, bm, col, mat, parent, smooth=False)
    for p in ob.data.polygons:
        p.use_smooth = len(p.vertices) == 4 and abs(p.normal.z) < 0.5
    return ob


def start(name, **_):
    col = common.fresh_collection(name)
    root = common.empty(name, col)
    return col, root


def group(name, col, parent, loc=(0, 0, 0), rot=0.0):
    """Empty used to place/rotate a sub-assembly (children use local coordinates)."""
    ob = common.empty(name, col)
    ob.location = loc
    ob.rotation_euler = (0, 0, math.radians(rot))
    ob.parent = parent
    return ob


def finish(root):
    bpy.context.view_layer.update()
    parts = [o for o in root.children_recursive if o.type == "MESH"]
    return root, parts
