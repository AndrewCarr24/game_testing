"""Shared building blocks for the pool_* assets (not an asset itself).

Outdoor assets are copied into the grounds WITHOUT their modifiers (grounds.place_zones
copies the raw mesh), so everything here is real geometry: hard-edged boxes whose hidden
faces can be skipped, long faces cut into cells (for per-vertex baked lighting), a few
chamfered cushions, spheres, cylinders and patches. Materials come from lib/outdoor.py.

A Builder collects faces per material (one object per material, parented to the root);
push()/pop() apply a transform to everything added in between (rotated loungers, pairs).
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

FACES = ("+x", "-x", "+y", "-y", "+z", "-z")


# --------------------------------------------------------------------- materials
def stone():
    return outdoor.stone()


def teak():
    return outdoor.teak()


def coping():
    """Pale honed limestone for the pool coping and nosings (flat colour, reads crisper
    than the textured paving)."""
    return outdoor.flat("M_Out_Coping", (0.60, 0.575, 0.52))


def weir():
    """Wet dark stone of the infinity-edge weir face."""
    return outdoor.flat("M_Out_Weir", (0.045, 0.05, 0.05))


def shelf_water():
    """Shallow sun-shelf water: a bright turquoise flat plane (the engine's water shader
    is dark and deep; this one is lit by the floor showing through)."""
    return outdoor.flat("M_Out_PoolShelf", (0.055, 0.30, 0.32))


def canvas():
    return outdoor.flat("M_Out_Canvas_Charcoal", (0.050, 0.052, 0.056))


def sand():
    return outdoor.cushion("Sand", (0.55, 0.50, 0.42))


def towel():
    return outdoor.flat("M_Out_Towel", (0.66, 0.65, 0.62))


def planter_stone():
    return outdoor.flat("M_Out_PlanterStone", (0.50, 0.475, 0.425))


def lunge(a, b, t):
    return a + (b - a) * t


class Builder:
    def __init__(self, name):
        self.name = name
        self.col = common.fresh_collection(name)
        self.root = common.empty(name, self.col)
        self.mats = {}
        self.bms = {}
        self.xf = Matrix.Identity(4)
        self.stack = []

    # ---- transforms
    def push(self, m):
        self.stack.append(self.xf)
        self.xf = self.xf @ m

    def pop(self):
        self.xf = self.stack.pop()

    # ---- internals
    def _bm(self, mat):
        if mat.name not in self.bms:
            self.mats[mat.name] = mat
            bm = bmesh.new()
            bm.loops.layers.uv.new("UVMap")
            self.bms[mat.name] = bm
        return self.bms[mat.name]

    def _finish(self, bm, faces, tile, grain=None, apply_xf=True):
        """UVs (world-scale planar by the dominant normal axis) then the transform."""
        uvl = bm.loops.layers.uv.active
        for f in faces:
            n = f.normal if f.normal.length > 0.5 else f.calc_normal()
            an = [abs(c) for c in n]
            na = an.index(max(an))
            a, b = [i for i in range(3) if i != na]
            if grain is not None and grain in (a, b):
                a, b = grain, (b if grain == a else a)
            elif grain is None:
                # keep u along the longer extent of the face (wood grain, slabs)
                xs = [lp.vert.co for lp in f.loops]
                ea = max(v[a] for v in xs) - min(v[a] for v in xs)
                eb = max(v[b] for v in xs) - min(v[b] for v in xs)
                if eb > ea + 1e-6:
                    a, b = b, a
            for lp in f.loops:
                lp[uvl].uv = (lp.vert.co[a] / tile, lp.vert.co[b] / tile)
        if apply_xf and self.xf != Matrix.Identity(4):
            for v in {v for f in faces for v in f.verts}:
                v.co = self.xf @ v.co

    # ---- primitives
    def grid(self, mat, o, du, dv, nu, nv, normal, tile=1.0, grain=None):
        """Quads over the parallelogram o + s*du + t*dv, nu x nv cells, facing `normal`."""
        bm = self._bm(mat)
        o, du, dv, normal = Vector(o), Vector(du), Vector(dv), Vector(normal)
        flip = du.cross(dv).dot(normal) < 0
        verts = {}
        for i in range(nu + 1):
            for j in range(nv + 1):
                verts[i, j] = bm.verts.new(o + du * (i / nu) + dv * (j / nv))
        faces = []
        for i in range(nu):
            for j in range(nv):
                q = [verts[i, j], verts[i + 1, j], verts[i + 1, j + 1], verts[i, j + 1]]
                if flip:
                    q.reverse()
                faces.append(bm.faces.new(q))
        bm.normal_update()
        self._finish(bm, faces, tile, grain)
        return faces

    def box(self, mat, lo, hi, tile=1.0, step=None, skip=(), grain=None):
        """Hard-edged box; skip = faces to leave out ('-z' ...); step = max cell size."""
        lo, hi = Vector(lo), Vector(hi)
        for face in FACES:
            if face in skip:
                continue
            a = "xyz".index(face[1])
            s = 1 if face[0] == "+" else -1
            b, c = (a + 1) % 3, (a + 2) % 3
            o = Vector(lo)
            o[a] = hi[a] if s > 0 else lo[a]
            du, dv = Vector((0, 0, 0)), Vector((0, 0, 0))
            du[b], dv[c] = hi[b] - lo[b], hi[c] - lo[c]
            nu = max(1, math.ceil(du[b] / step - 1e-6)) if step else 1
            nv = max(1, math.ceil(dv[c] / step - 1e-6)) if step else 1
            nrm = Vector((0, 0, 0))
            nrm[a] = s
            self.grid(mat, o, du, dv, nu, nv, nrm, tile, grain)

    def hquad(self, mat, x0, y0, x1, y1, z, step=None, tile=1.0, up=True):
        nu = max(1, math.ceil((x1 - x0) / step - 1e-6)) if step else 1
        nv = max(1, math.ceil((y1 - y0) / step - 1e-6)) if step else 1
        self.grid(mat, (x0, y0, z), (x1 - x0, 0, 0), (0, y1 - y0, 0), nu, nv,
                  (0, 0, 1 if up else -1), tile)

    def vwall(self, mat, p0, p1, z0, z1, out, step=1.5, tile=1.0):
        """Vertical wall from plan point p0 to p1 between z0 and z1, facing `out` (x, y)."""
        ln = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        nu = max(1, math.ceil(ln / step - 1e-6)) if step else 1
        self.grid(mat, (p0[0], p0[1], z0), (p1[0] - p0[0], p1[1] - p0[1], 0), (0, 0, z1 - z0), nu, 1,
                  (out[0], out[1], 0), tile)

    def poly(self, mat, pts, tile=1.0, flip=False):
        bm = self._bm(mat)
        vs = [bm.verts.new(p) for p in pts]
        if flip:
            vs.reverse()
        f = bm.faces.new(vs)
        bm.normal_update()
        self._finish(bm, [f], tile)
        return f

    def patch(self, mat, x0, y0, x1, y1, nx, ny, zf, up=True, tile=1.0):
        """Height-field patch z = zf(x, y) over a rectangle (canopies)."""
        bm = self._bm(mat)
        verts = {}
        for i in range(nx + 1):
            for j in range(ny + 1):
                x, y = lunge(x0, x1, i / nx), lunge(y0, y1, j / ny)
                verts[i, j] = bm.verts.new((x, y, zf(x, y)))
        faces = []
        for i in range(nx):
            for j in range(ny):
                q = [verts[i, j], verts[i + 1, j], verts[i + 1, j + 1], verts[i, j + 1]]
                if not up:
                    q.reverse()
                faces.append(bm.faces.new(q))
        bm.normal_update()
        self._finish(bm, faces, tile)

    def cyl(self, mat, centre, radius, z0, z1, seg=12, caps=("+z",), tile=1.0, step=None):
        bm = self._bm(mat)
        cx, cy = centre
        ring0 = [bm.verts.new((cx + radius * math.cos(2 * math.pi * k / seg),
                               cy + radius * math.sin(2 * math.pi * k / seg), z0)) for k in range(seg)]
        ring1 = [bm.verts.new((cx + radius * math.cos(2 * math.pi * k / seg),
                               cy + radius * math.sin(2 * math.pi * k / seg), z1)) for k in range(seg)]
        faces = []
        for k in range(seg):
            m = (k + 1) % seg
            faces.append(bm.faces.new((ring0[k], ring0[m], ring1[m], ring1[k])))
        if "+z" in caps:
            faces.append(bm.faces.new(ring1))
        if "-z" in caps:
            faces.append(bm.faces.new(list(reversed(ring0))))
        bm.normal_update()
        self._finish(bm, faces, tile)

    def ball(self, mat, centre, radii, seg=12, rings=7, tile=1.5):
        """Squashed UV sphere (clipped shrub)."""
        bm = self._bm(mat)
        geom = bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
        verts = geom["verts"]
        for v in verts:
            v.co = Vector((v.co.x * radii[0] + centre[0], v.co.y * radii[1] + centre[1],
                           v.co.z * radii[2] + centre[2]))
        faces = list({f for v in verts for f in v.link_faces})
        bm.normal_update()
        self._finish(bm, faces, tile)

    def chamfer_box(self, mat, lo, hi, r=0.02, tile=0.25, skip_bottom=False):
        """Cushion: a box with one-segment chamfered edges."""
        bm = self._bm(mat)
        lo, hi = Vector(lo), Vector(hi)
        before = set(bm.faces)
        geom = bmesh.ops.create_cube(bm, size=1.0)
        verts = geom["verts"]
        for v in verts:
            v.co = Vector(((hi.x - lo.x) * v.co.x + (hi.x + lo.x) / 2,
                           (hi.y - lo.y) * v.co.y + (hi.y + lo.y) / 2,
                           (hi.z - lo.z) * v.co.z + (hi.z + lo.z) / 2))
        edges = list({e for v in verts for e in v.link_edges})
        bmesh.ops.bevel(bm, geom=edges, offset=r, segments=1, affect="EDGES")
        faces = [f for f in bm.faces if f not in before]
        bm.normal_update()
        if skip_bottom:
            bot = [f for f in faces if f.normal.z < -0.99]
            bmesh.ops.delete(bm, geom=bot, context="FACES_ONLY")
            faces = [f for f in faces if f.is_valid]
        self._finish(bm, faces, tile)

    # ---- output
    def finish(self):
        parts = []
        for key, bm in self.bms.items():
            mat = self.mats[key]
            if not bm.faces:
                bm.free()
                continue
            short = key.replace("M_Out_", "").replace("M_Grounds_", "").replace("M_", "")
            ob = common.mesh_object(f"{self.name}_{short}", bm, self.col, mat, self.root, smooth=False)
            parts.append(ob)
        return self.root, parts


def report(root, parts):
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
