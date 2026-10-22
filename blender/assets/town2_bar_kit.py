"""Geometry kit for the bar (town2_bar.py): parts are built as small bmeshes (bevelled boxes,
lathes, tubes along polylines, extruded outlines, displaced grids), transformed into the asset
frame and appended to one bucket per material, so the export is one mesh (one draw call) per
material. Each part carries:
  tint   linear RGB multiplied into the material's texture (exported as COLOR_0 "Tint")
  uv     "box" (world-scaled planar per face: the material's tile), ("cell", name) (into a swatch
         of the props atlas, town2_bar_tex.ATLAS), or a callable (co, normal) -> (u, v)
  lmw    lightmap texel-density weight (1 = the interior's density; the lot is coarser)
  smooth smooth shading (lathes, tubes, cushions)
Colliders and lights are collected alongside (asset frame, Blender z up)."""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

# ------------------------------------------------------------------ the props atlas layout
# 512 px, 16 x 16 cells of 32 px; a swatch is (col, row[, w, h]) in cells
ATLAS_N = 16


def cell_rect(c, inset=0.22):
    """(u0, v0, u1, v1) of an atlas swatch, inset (fraction of a cell) so mips don't bleed."""
    col, row = c[0], c[1]
    w, h = (c[2], c[3]) if len(c) > 2 else (1, 1)
    d = 1.0 / ATLAS_N
    return ((col + inset) * d, 1 - (row + h - inset) * d, (col + w - inset) * d, 1 - (row + inset) * d)


class Kit:
    def __init__(self, tiles=None, cells=None):
        self.tiles = tiles or {}          # material -> metres one texture repeat covers
        self.cells = cells or {}          # swatch name -> (col, row[, w, h])
        self.buckets = {}
        self.colliders = []
        self.lights = []
        self.markers = {}                 # named points (views, entrances)
        self.tris = {}
        self.section = "misc"
        self.sec_tris = {}

    # -------------------------------------------------------------- core: append a bmesh
    def add(self, bm, mat, M=None, tint=(1, 1, 1), uv="box", lmw=1.0, smooth=False, tile=None,
            uv_rot=False, uv_off=(0.0, 0.0), col=False, name=None, free=True, vlit=None):
        """vlit: light this part per vertex (COLOR_0) instead of in the lightmap; default: small
        or low-weight parts (lmw <= 0.6, or under 0.5 m)."""
        if M is not None:
            bm.transform(M)
        bm.normal_update()
        b = self.buckets.setdefault(mat, dict(V=[], F=[], UV=[], T=[], W=[], S=[], L=[], n=0))
        base = b["n"]
        bm.verts.index_update()
        vs = [v.co.copy() for v in bm.verts]
        b["V"].extend((v.x, v.y, v.z) for v in vs)
        b["n"] += len(vs)
        tl = tile or self.tiles.get(mat, 1.0)
        if isinstance(uv, tuple) and uv[0] == "cell":
            r = cell_rect(self.cells[uv[1]])
            lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
            hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
            ext = [max(hi[i] - lo[i], 1e-6) for i in range(3)]
        if vlit is None:
            span = max((max(v[i] for v in vs) - min(v[i] for v in vs)) for i in range(3)) if vs else 0.0
            vlit = lmw <= 0.6 or span < 0.5
        per_face = isinstance(tint, list)
        tint = tint if per_face else tuple(tint)
        for fi, f in enumerate(bm.faces):
            idx = [base + v.index for v in f.verts]
            b["F"].append(idx)
            n = f.normal
            b["T"].append(tuple(tint[fi]) if per_face else tint)
            b["W"].append(lmw)
            b["S"].append(smooth)
            b["L"].append(bool(vlit))
            uvs = []
            ax = max(range(3), key=lambda i: abs(n[i]))
            for lp in f.loops:
                co = lp.vert.co
                if callable(uv):
                    uvs.append(uv(co, n))
                    continue
                if ax == 2:
                    p = (co.x, co.y if n.z > 0 else -co.y)
                elif ax == 0:
                    p = (co.y if n.x > 0 else -co.y, co.z)
                else:
                    p = (-co.x if n.y > 0 else co.x, co.z)
                if isinstance(uv, tuple) and uv[0] == "cell":
                    a0, a1 = [i for i in range(3) if i != ax]
                    t0 = (co[a0] - lo[a0]) / ext[a0]
                    t1 = (co[a1] - lo[a1]) / ext[a1]
                    uvs.append((r[0] + (r[2] - r[0]) * t0, r[1] + (r[3] - r[1]) * t1))
                else:
                    u, v = p[0] / tl, p[1] / tl
                    if uv_rot:
                        u, v = v, -u
                    uvs.append((u + uv_off[0], v + uv_off[1]))
            b["UV"].append(uvs)
        nt = sum(len(f.verts) - 2 for f in bm.faces)
        self.tris[mat] = self.tris.get(mat, 0) + nt
        self.sec_tris[self.section] = self.sec_tris.get(self.section, 0) + nt
        if col:
            lo = [min(v[i] for v in vs) for i in range(3)]
            hi = [max(v[i] for v in vs) for i in range(3)]
            self.colliders.append(lo + hi)
        if free:
            bm.free()
        return self

    def collider(self, x0, y0, z0, x1, y1, z1):
        self.colliders.append([min(x0, x1), min(y0, y1), min(z0, z1), max(x0, x1), max(y0, y1), max(z0, z1)])

    def light(self, kind, pos, color, power, **kw):
        self.lights.append(dict(kind=kind, pos=tuple(pos), color=tuple(color), power=power, **kw))

    # -------------------------------------------------------------- primitives (each returns self)
    def box(self, mat, lo, hi, bevel=0.0, segs=1, skip=(), M=None, **kw):
        """Axis-aligned box lo..hi (asset frame, or local under M), optionally bevelled;
        skip: faces to drop ('-z', '+z', '-x', ...), e.g. a bottom on the floor."""
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        sx, sy, sz = (hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2])
        bmesh.ops.scale(bm, vec=(max(sx, 1e-5), max(sy, 1e-5), max(sz, 1e-5)), verts=bm.verts)
        bmesh.ops.translate(bm, vec=((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2), verts=bm.verts)
        if bevel > 0:
            w = min(bevel, 0.45 * min(sx, sy, sz))
            bmesh.ops.bevel(bm, geom=list(bm.edges) + list(bm.verts), offset=w, offset_type="OFFSET", segments=segs,
                            profile=0.5, affect="EDGES", clamp_overlap=True)
        if skip:
            c = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2))
            dead = []
            for f in bm.faces:
                n = f.normal
                for s in skip:
                    a = "xyz".index(s[1])
                    sg = 1 if s[0] == "+" else -1
                    if n[a] * sg > 0.99 and abs(f.calc_center_median()[a] - (hi[a] if sg > 0 else lo[a])) < 1e-4:
                        dead.append(f)
            bmesh.ops.delete(bm, geom=list(set(dead)), context="FACES_ONLY")
        return self.add(bm, mat, M=M, **kw)

    def quad(self, mat, pts, M=None, **kw):
        """One face from 3-4+ points (counter-clockwise seen from the front)."""
        bm = bmesh.new()
        vs = [bm.verts.new(p) for p in pts]
        bm.faces.new(vs)
        return self.add(bm, mat, M=M, **kw)

    def lathe(self, mat, profile, sides=16, M=None, cap0=True, cap1=True, a0=0.0, a1=2 * math.pi, **kw):
        """Surface of revolution about local z: profile [(r, z), ...] bottom to top."""
        bm = bmesh.new()
        full = abs(a1 - a0 - 2 * math.pi) < 1e-6
        n = sides if full else sides + 1
        rings = []
        for r, z in profile:
            ring = []
            for k in range(n):
                a = a0 + (a1 - a0) * k / sides
                ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
            rings.append(ring)
        m = sides
        for i in range(len(rings) - 1):
            A, B = rings[i], rings[i + 1]
            for k in range(m):
                k1 = (k + 1) % n if full else k + 1
                q = [A[k], A[k1], B[k1], B[k]]
                if profile[i][0] < 1e-6:
                    q = [A[k], B[k1], B[k]]
                elif profile[i + 1][0] < 1e-6:
                    q = [A[k], A[k1], B[k]]
                try:
                    bm.faces.new(q)
                except ValueError:
                    pass
        if full and cap0 and profile[0][0] > 1e-6:
            bm.faces.new(list(reversed(rings[0])))
        if full and cap1 and profile[-1][0] > 1e-6:
            bm.faces.new(rings[-1])
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        kw.setdefault("smooth", True)
        return self.add(bm, mat, M=M, **kw)

    def cyl(self, mat, a, b, r, sides=12, caps=True, r1=None, **kw):
        """Cylinder (or cone: r1) from point a to point b."""
        a, b = Vector(a), Vector(b)
        d = b - a
        L = d.length
        M = Matrix.Translation(a) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
        prof = [(r, 0.0), (r if r1 is None else r1, L)]
        return self.lathe(mat, prof, sides=sides, M=M, cap0=caps, cap1=caps, **kw)

    def tube(self, mat, pts, r, sides=8, closed=False, caps=True, M=None, **kw):
        """A round tube along a polyline (parallel-transport frames)."""
        P = [Vector(p) for p in pts]
        if len(P) < 2:
            return self
        bm = bmesh.new()
        T = []
        for i in range(len(P)):
            if closed:
                t = (P[(i + 1) % len(P)] - P[i - 1])
            else:
                t = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)])
            T.append(t.normalized() if t.length > 1e-9 else Vector((0, 0, 1)))
        up = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))
        nrm = T[0].cross(up).normalized()
        rings = []
        for i in range(len(P)):
            if i > 0:
                nrm = (nrm - T[i] * nrm.dot(T[i]))
                nrm = nrm.normalized() if nrm.length > 1e-9 else T[i].orthogonal().normalized()
            bn = T[i].cross(nrm)
            ring = [bm.verts.new(P[i] + (nrm * math.cos(2 * math.pi * k / sides) + bn * math.sin(2 * math.pi * k / sides)) * r)
                    for k in range(sides)]
            rings.append(ring)
        segs = len(rings) if closed else len(rings) - 1
        for i in range(segs):
            A, B = rings[i], rings[(i + 1) % len(rings)]
            for k in range(sides):
                try:
                    bm.faces.new([A[k], A[(k + 1) % sides], B[(k + 1) % sides], B[k]])
                except ValueError:
                    pass
        if caps and not closed:
            bm.faces.new(list(reversed(rings[0])))
            bm.faces.new(rings[-1])
        kw.setdefault("smooth", True)
        return self.add(bm, mat, M=M, **kw)

    def prism(self, mat, outline, z0, z1, M=None, bevel=0.0, segs=1, caps=(True, True), **kw):
        """Extrude a closed 2D outline [(x, y)] (counter-clockwise) from z0 to z1."""
        bm = bmesh.new()
        lo = [bm.verts.new((x, y, z0)) for x, y in outline]
        hi = [bm.verts.new((x, y, z1)) for x, y in outline]
        n = len(outline)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new([lo[i], lo[j], hi[j], hi[i]])
        if caps[0]:
            bm.faces.new(list(reversed(lo)))
        if caps[1]:
            bm.faces.new(hi)
        if bevel > 0:
            bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, offset_type="OFFSET", segments=segs, profile=0.5,
                            affect="EDGES", clamp_overlap=True)
        return self.add(bm, mat, M=M, **kw)

    def grid(self, mat, fn, nu, nv, M=None, both=False, flip=False, **kw):
        """A surface from fn(u, v) -> (x, y, z), u, v in 0..1 (nu x nv quads)."""
        bm = bmesh.new()
        V = [[bm.verts.new(fn(i / nu, j / nv)) for i in range(nu + 1)] for j in range(nv + 1)]
        B = [[bm.verts.new(v.co) for v in row] for row in V] if both else None
        for j in range(nv):
            for i in range(nu):
                q = [V[j][i], V[j][i + 1], V[j + 1][i + 1], V[j + 1][i]]
                bm.faces.new(q[::-1] if flip else q)
                if both:
                    bm.faces.new([B[j][i], B[j + 1][i], B[j + 1][i + 1], B[j][i + 1]])
        kw.setdefault("smooth", True)
        return self.add(bm, mat, M=M, **kw)

    def bm(self, bm, mat, **kw):
        return self.add(bm, mat, **kw)

    # -------------------------------------------------------------- output
    def to_objects(self, col, materials, prefix):
        """One mesh object per material: UV0 "UVMap", colour "Tint" (corner, linear), face
        float "lmw", sharp faces for the flat-shaded parts."""
        out = {}
        for mat, b in self.buckets.items():
            if not b["F"]:
                continue
            me = bpy.data.meshes.new(f"{prefix}_{mat}")
            me.from_pydata(b["V"], [], b["F"])
            me.update()
            uvl = me.uv_layers.new(name="UVMap")
            uv = np.array([q for f in b["UV"] for q in f], np.float32).ravel()
            uvl.data.foreach_set("uv", uv)
            ca = me.color_attributes.new("Tint", "FLOAT_COLOR", "CORNER")
            tc = np.array([(*b["T"][fi], 1.0) for fi, f in enumerate(b["F"]) for _ in f], np.float32).ravel()
            ca.data.foreach_set("color", tc)
            wa = me.attributes.new("lmw", "FLOAT", "FACE")
            wa.data.foreach_set("value", np.array(b["W"], np.float32))
            va = me.attributes.new("vlit", "INT8", "FACE")
            va.data.foreach_set("value", np.array(b["L"], np.int8))
            sm = np.array(b["S"], bool)
            me.polygons.foreach_set("use_smooth", sm)
            me.materials.append(materials[mat])
            ob = bpy.data.objects.new(f"{prefix}_{mat}", me)
            col.objects.link(ob)
            out[mat] = ob
        return out


# ------------------------------------------------------------------ small math helpers
def rot_z(deg, about=(0, 0, 0)):
    a = Vector(about)
    return Matrix.Translation(a) @ Matrix.Rotation(math.radians(deg), 4, "Z") @ Matrix.Translation(-a)


def place(x, y, z=0.0, yaw=0.0):
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(yaw), 4, "Z")


def arc_pts(c, r, a0, a1, n, z=None, plane="xy"):
    out = []
    for k in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * k / n)
        if plane == "xy":
            out.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a), c[2] if z is None else z))
        elif plane == "xz":
            out.append((c[0] + r * math.cos(a), c[1], c[2] + r * math.sin(a)))
        else:
            out.append((c[0], c[1] + r * math.cos(a), c[2] + r * math.sin(a)))
    return out


def rounded_rect(x0, y0, x1, y1, r, n=4):
    """Counter-clockwise outline of a rectangle with rounded corners."""
    r = min(r, (x1 - x0) / 2 - 1e-4, (y1 - y0) / 2 - 1e-4)
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts
