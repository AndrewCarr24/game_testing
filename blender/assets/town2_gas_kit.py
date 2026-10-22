"""Geometry kit for the gas station (town2_gas.py): brushes that add primitives straight into one
bmesh per (zone, material), with world-scale box UVs (UVMap, 1 unit = the material's tile) or
explicit atlas UVs, a lightmap density weight per face (`lmw`, read by blender/town/gas/make.py
when it packs the Lightmap UVs), a transform stack (props are built at their own origin and placed)
and the collider boxes for the sidecar.

Zones: "ext" (outside: the lot, the canopy, the store's skin), "int" (inside the store), "lod1"
(the far version); each gets its own lightmap atlas. Unlit materials (emissive, glass) go to
"<zone>_g" (no lightmap; the zone still picks their reflection panorama).
"""
import math
from contextlib import contextmanager

import bmesh
import bpy
from mathutils import Matrix, Vector

V = Vector
UNLIT = ("glow",)


class Kit:
    def __init__(self, name, mats, swatches=None, cells=None):
        """mats: name -> dict(mat=bpy material, tile=metres per UV unit, unlit=bool); swatches:
        palette colour name -> uv (brushes on those names paint with the "paint" material);
        cells: atlas name -> {cell: uv rect}."""
        self.name = name
        self.mats = mats
        self.swatches = swatches or {}
        self.cells = cells or {}
        self.bms = {}
        self.colliders = []
        self.M = Matrix.Identity(4)
        self.ngroups = 0
        self.lights = []        # bake lights: dict(kind, loc, rot, size, energy, color, ...)
        self.marks = {}         # named points (views, probes, cameras), asset frame

    # ---------------------------------------------------------------- transform stack
    @contextmanager
    def at(self, loc=(0, 0, 0), rot=0.0, rx=0.0, ry=0.0, scale=1.0):
        """Place what's built inside at loc, turned rot degrees about z (CCW from above), after
        ry about y and rx about x (local)."""
        old = self.M
        S = Matrix.Scale(scale, 4) if not isinstance(scale, (tuple, list)) else Matrix.Diagonal((*scale, 1.0))
        self.M = (old @ Matrix.Translation(V(loc)) @ Matrix.Rotation(math.radians(rot), 4, "Z")
                  @ Matrix.Rotation(math.radians(ry), 4, "Y") @ Matrix.Rotation(math.radians(rx), 4, "X") @ S)
        try:
            yield
        finally:
            self.M = old

    def pt(self, p):
        return self.M @ V(p)

    def _bm(self, zone, mat):
        key = (zone, mat)
        if key not in self.bms:
            bm = bmesh.new()
            bm.faces.layers.int.new("lmg")
            bm.faces.layers.int.new("lma")
            self.bms[key] = (bm, bm.loops.layers.uv.new("UVMap"), bm.faces.layers.float.new("lmw"))
        return self.bms[key]

    def p(self, mat, zone="ext", lmw=1.0, group=None):
        sw = None
        if mat in self.swatches:
            sw, mat = self.swatches[mat], "paint"
        if mat not in self.mats:
            raise KeyError(mat)
        if self.mats[mat].get("unlit"):
            zone = zone + "_g"
        b = Brush(self, mat, zone, lmw)
        b.swatch = sw
        if group:
            b.lmg = group
        return b

    def group(self, axis):
        """A new lightmap group id: faces of brushes given it share one chart, projected along
        `axis` (0 x, 1 y, 2 z) in the asset frame (a shelf of goods: one island, not hundreds)."""
        self.ngroups += 1
        return (self.ngroups, axis)

    def cell(self, atlas, key):
        return self.cells[atlas][key]

    def collide(self, lo, hi):
        """An axis-aligned collider box (corners transformed; boxes stay boxes under 90-degree turns)."""
        cs = [self.M @ V((x, y, z)) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
        self.colliders.append([round(min(c[i] for c in cs), 3) for i in range(3)] + [round(max(c[i] for c in cs), 3) for i in range(3)])

    def light(self, kind, loc, size=(0.5, 0.5), energy=50.0, color=(1, 1, 1), rot=(0, 0, 0), **kw):
        """A bake light (Cycles only: AREA (size x, y; faces -z of its rotation), POINT, SPOT)."""
        self.lights.append(dict(kind=kind, loc=tuple(self.M @ V(loc)), size=size, energy=energy, color=color,
                                rot=rot, zrot=math.atan2(self.M[1][0], self.M[0][0]), **kw))

    def mark(self, name, p):
        self.marks[name] = tuple(round(c, 3) for c in self.M @ V(p))

    # ---------------------------------------------------------------- finishing
    def build(self, col):
        """One mesh object per (zone, material) in `col`. Returns {(zone, mat): object}."""
        out = {}
        for (zone, mat), (bm, uv, lw) in sorted(self.bms.items()):
            if not bm.faces:
                continue
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
            me = bpy.data.meshes.new(f"{self.name}_{zone}_{mat}")
            bm.to_mesh(me)
            bm.free()
            m = self.mats[mat]["mat"]
            if not zone.endswith("_g"):
                # (a lit material per zone: each zone has its own lightmap, named in the material)
                m = m.copy()
                m.name = f"{self.mats[mat]['mat'].name}_{zone.capitalize()}"
            me.materials.append(m)
            ob = bpy.data.objects.new(me.name, me)
            ob["zone"] = zone
            col.objects.link(ob)
            out[(zone, mat)] = ob
        self.bms = {}
        self.objects = out
        return out


class Brush:
    """Adds faces to one (zone, material) bmesh, through the kit's current transform."""

    def __init__(self, kit, mat, zone, lmw):
        self.kit, self.mat, self.zone, self.lmw = kit, mat, zone, lmw
        self.bm, self.uv, self.lw = kit._bm(zone, mat)
        self.tile = kit.mats[mat].get("tile", 1.0)
        self.smooth = False
        self.swatch = None
        self.lmg = (0, 0)
        self.g_l = self.bm.faces.layers.int["lmg"]
        self.a_l = self.bm.faces.layers.int["lma"]

    # ---- low level
    def face(self, pts, uvs=None, smooth=None):
        """A polygon (world = kit transform applied). uvs: explicit UV0 per point, else box projection."""
        M = self.kit.M
        P = [M @ V(p) for p in pts]
        vs = [self.bm.verts.new(p) for p in P]
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.smooth = self.smooth if smooth is None else smooth
        f[self.lw] = self.lmw
        if self.lmg[0]:
            f[self.g_l], f[self.a_l] = self.lmg
        if self.swatch is not None:
            uvs = [self.swatch] * len(P)
        elif uvs is None:
            f.normal_update()
            uvs = box_uv(P, f.normal, self.tile)
        for loop, t in zip(f.loops, uvs):
            loop[self.uv].uv = t
        return f

    def mesh(self, tbm, uvfun=None, smooth=None):
        """Merge a temporary bmesh (local coords) in; it is freed. uvfun(face) -> uvs or None."""
        for f in tbm.faces:
            pts = [v.co.copy() for v in f.verts]
            uvs = uvfun(f) if uvfun else None
            self.face(pts, uvs, smooth=f.smooth if smooth is None else smooth)
        tbm.free()

    # ---- primitives
    def quad(self, a, b, c, d, uvs=None):
        return self.face([a, b, c, d], uvs)

    def box(self, lo, hi, skip="", bevel=0.0, seg=1, cell=None, front="y"):
        """An axis-aligned box. skip: faces left out ('x' = the -x face, 'X' = +x, 'y', 'Y', 'z' bottom,
        'Z' top). bevel: edge bevel width. cell: (u0, v0, u1, v1) atlas rect for the `front` face
        (the other faces take a sliver of the cell's edge: a package's side)."""
        (x0, y0, z0), (x1, y1, z1) = lo, hi
        if x1 - x0 <= 1e-6 or y1 - y0 <= 1e-6 or z1 - z0 <= 1e-6:
            return
        tbm = bmesh.new()
        bmesh.ops.create_cube(tbm, size=1.0)
        for v in tbm.verts:
            v.co = V((x0 if v.co.x < 0 else x1, y0 if v.co.y < 0 else y1, z0 if v.co.z < 0 else z1))
        kill = []
        for f in tbm.faces:
            f.normal_update()
            n = f.normal
            k = "x" if n.x < -0.5 else "X" if n.x > 0.5 else "y" if n.y < -0.5 else "Y" if n.y > 0.5 else "z" if n.z < -0.5 else "Z"
            if k in skip:
                kill.append(f)
        if bevel > 0:
            w = min(bevel, 0.45 * min(x1 - x0, y1 - y0, z1 - z0))
            bmesh.ops.bevel(tbm, geom=list(tbm.edges), offset=w, segments=seg, profile=0.5, affect="EDGES", clamp_overlap=True)
            # (faces to skip: drop those whose normal still points that way)
            kill = []
            for f in tbm.faces:
                f.normal_update()
                n = f.normal
                for k, (ax, sg) in (("x", (0, -1)), ("X", (0, 1)), ("y", (1, -1)), ("Y", (1, 1)), ("z", (2, -1)), ("Z", (2, 1))):
                    if k in skip and n[ax] * sg > 0.99:
                        kill.append(f)
        if kill:
            bmesh.ops.delete(tbm, geom=list(set(kill)), context="FACES")
        uvfun = None
        if cell is not None:
            uvfun = cell_uv(cell, front, lo, hi)
        self.mesh(tbm, uvfun, smooth=False)

    def slab(self, pts2d, z0, z1, caps="both", uvtop=None):
        """A vertical prism over a CCW polygon (x, y) from z0 to z1."""
        n = len(pts2d)
        for i in range(n):
            (ax, ay), (bx, by) = pts2d[i], pts2d[(i + 1) % n]
            self.face([(ax, ay, z0), (bx, by, z0), (bx, by, z1), (ax, ay, z1)])
        if caps in ("both", "top"):
            self.face([(x, y, z1) for x, y in pts2d], uvtop)
        if caps in ("both", "bottom"):
            self.face([(x, y, z0) for x, y in reversed(pts2d)])

    def cyl(self, c, r, z0, z1, seg=16, caps="both", r1=None, smooth=True):
        """A vertical cylinder (or cone frustum with r1) at c = (x, y)."""
        r1 = r if r1 is None else r1
        cx, cy = c
        ring0 = [(cx + r * math.cos(2 * math.pi * k / seg), cy + r * math.sin(2 * math.pi * k / seg)) for k in range(seg)]
        ring1 = [(cx + r1 * math.cos(2 * math.pi * k / seg), cy + r1 * math.sin(2 * math.pi * k / seg)) for k in range(seg)]
        circ = 2 * math.pi * max(r, r1)
        for k in range(seg):
            a0, a1 = ring0[k], ring0[(k + 1) % seg]
            b0, b1 = ring1[k], ring1[(k + 1) % seg]
            u0, u1 = circ * k / seg / self.tile, circ * (k + 1) / seg / self.tile
            self.face([(*a0, z0), (*a1, z0), (*b1, z1), (*b0, z1)],
                      [(u0, z0 / self.tile), (u1, z0 / self.tile), (u1, z1 / self.tile), (u0, z1 / self.tile)], smooth=smooth)
        if caps in ("both", "top"):
            self.face([(*b, z1) for b in ring1], smooth=False)
        if caps in ("both", "bottom"):
            self.face([(*a, z0) for a in reversed(ring0)], smooth=False)

    def lathe(self, prof, c=(0, 0), z=0.0, seg=16, cap_top=True, cell=None):
        """Surface of revolution about the vertical axis at c: prof = [(r, z), ...] bottom to top."""
        cx, cy = c
        rings = []
        for r, h in prof:
            rings.append([(cx + r * math.cos(2 * math.pi * k / seg), cy + r * math.sin(2 * math.pi * k / seg), z + h) for k in range(seg)])
        L = [0.0]
        for i in range(1, len(prof)):
            L.append(L[-1] + math.hypot(prof[i][0] - prof[i - 1][0], prof[i][1] - prof[i - 1][1]))
        circ = 2 * math.pi * max(p[0] for p in prof)
        for i in range(len(prof) - 1):
            for k in range(seg):
                a0, a1, b0, b1 = rings[i][k], rings[i][(k + 1) % seg], rings[i + 1][k], rings[i + 1][(k + 1) % seg]
                if cell:
                    u0, v0, u1, v1 = cell
                    uv = [(u0 + (u1 - u0) * k / seg, v0 + (v1 - v0) * L[i] / L[-1]), (u0 + (u1 - u0) * (k + 1) / seg, v0 + (v1 - v0) * L[i] / L[-1]),
                          (u0 + (u1 - u0) * (k + 1) / seg, v0 + (v1 - v0) * L[i + 1] / L[-1]), (u0 + (u1 - u0) * k / seg, v0 + (v1 - v0) * L[i + 1] / L[-1])]
                else:
                    uv = [(circ * k / seg / self.tile, L[i] / self.tile), (circ * (k + 1) / seg / self.tile, L[i] / self.tile),
                          (circ * (k + 1) / seg / self.tile, L[i + 1] / self.tile), (circ * k / seg / self.tile, L[i + 1] / self.tile)]
                if prof[i][0] < 1e-6:
                    self.face([a0, b1, b0], [uv[0], uv[2], uv[3]], smooth=True)
                elif prof[i + 1][0] < 1e-6:
                    self.face([a0, a1, b0], [uv[0], uv[1], uv[3]], smooth=True)
                else:
                    self.face([a0, a1, b1, b0], uv, smooth=True)
        if cap_top and prof[-1][0] > 1e-6:
            self.face(rings[-1], smooth=False)

    def tube(self, pts, r, sides=8, caps=True):
        """A round tube along a 3D polyline (parallel-transported frames)."""
        P = [V(p) for p in pts]
        if len(P) < 2:
            return
        T = []
        for i in range(len(P)):
            a = P[max(0, i - 1)]
            b = P[min(len(P) - 1, i + 1)]
            t = b - a
            T.append(t.normalized() if t.length > 1e-9 else V((0, 0, 1)))
        up = V((0, 0, 1)) if abs(T[0].z) < 0.9 else V((1, 0, 0))
        n = T[0].cross(up).normalized()
        rings = []
        for i in range(len(P)):
            if i > 0:
                n = (n - T[i] * n.dot(T[i]))
                n = n.normalized() if n.length > 1e-9 else T[i].orthogonal().normalized()
            bvec = T[i].cross(n)
            rings.append([P[i] + (n * math.cos(2 * math.pi * k / sides) + bvec * math.sin(2 * math.pi * k / sides)) * r for k in range(sides)])
        s = 0.0
        for i in range(len(P) - 1):
            ds = (P[i + 1] - P[i]).length
            for k in range(sides):
                self.face([rings[i][k], rings[i][(k + 1) % sides], rings[i + 1][(k + 1) % sides], rings[i + 1][k]],
                          [(k / sides * 2 * math.pi * r / self.tile, s / self.tile), ((k + 1) / sides * 2 * math.pi * r / self.tile, s / self.tile),
                           ((k + 1) / sides * 2 * math.pi * r / self.tile, (s + ds) / self.tile), (k / sides * 2 * math.pi * r / self.tile, (s + ds) / self.tile)],
                          smooth=True)
            s += ds
        if caps:
            self.face(list(reversed(rings[0])), smooth=False)
            self.face(rings[-1], smooth=False)

    def extrude(self, poly, d, caps=True):
        """A prism: the planar polygon `poly` (3D points, CCW seen from where d points) swept by d."""
        d = V(d)
        P = [V(p) for p in poly]
        n = len(P)
        for i in range(n):
            a, b = P[i], P[(i + 1) % n]
            self.face([a, b, b + d, a + d][::-1])
        if caps:
            self.face([p + d for p in P])
            self.face(list(reversed(P)))

    def panel(self, c, facing, w, h, cell=None, uvs=None):
        """A flat w x h rectangle centred on c, facing 'x' (-x), 'X' (+x), 'y', 'Y', 'z' or 'Z'; with
        cell = (u0, v0, u1, v1) the atlas image reads the right way round from the front."""
        n = {"x": V((-1, 0, 0)), "X": V((1, 0, 0)), "y": V((0, -1, 0)), "Y": V((0, 1, 0)), "z": V((0, 0, -1)), "Z": V((0, 0, 1))}[facing]
        up = V((0, 0, 1)) if facing not in "zZ" else V((0, 1, 0))
        right = (-n).cross(up)
        c = V(c)
        pts = [c + right * (-w / 2) + up * (-h / 2), c + right * (w / 2) + up * (-h / 2), c + right * (w / 2) + up * (h / 2), c + right * (-w / 2) + up * (h / 2)]
        if cell:
            u0, v0, u1, v1 = cell
            uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        return self.face(pts, uvs)


def box_uv(P, n, tile):
    """World-scale box projection for one face: horizontal faces (x, y); walls (along, z)."""
    ax = [abs(n.x), abs(n.y), abs(n.z)]
    na = ax.index(max(ax))
    if na == 2:
        return [(p.x / tile, p.y / tile) for p in P]
    if na == 0:
        s = 1 if n.x > 0 else -1
        return [(s * p.y / tile, p.z / tile) for p in P]
    s = -1 if n.y > 0 else 1
    return [(s * p.x / tile, p.z / tile) for p in P]


def cell_uv(cell, front, lo, hi):
    """UVs for a package box: the front face fills the atlas cell, the others a sliver of its edge."""
    u0, v0, u1, v1 = cell
    ax = {"x": 0, "y": 1, "X": 0, "Y": 1, "z": 2, "Z": 2}[front]
    sgn = -1 if front in "xyz" else 1

    def f(face):
        face.normal_update()
        n = face.normal
        P = [v.co for v in face.verts]
        if n[ax] * sgn > 0.5:
            a, b = (0, 2) if ax == 1 else (1, 2) if ax == 0 else (0, 1)
            fl = (ax == 1 and sgn < 0) or (ax == 0 and sgn > 0)
            out = []
            for p in P:
                s = (p[a] - lo[a]) / max(hi[a] - lo[a], 1e-9)
                t = (p[b] - lo[b]) / max(hi[b] - lo[b], 1e-9)
                if not fl:
                    s = 1 - s
                out.append((u0 + (u1 - u0) * s, v0 + (v1 - v0) * t))
            return out
        # sides / top: the cell's left column (its edge colour), stretched
        du = (u1 - u0) * 0.04
        out = []
        for p in P:
            t = (p[2] - lo[2]) / max(hi[2] - lo[2], 1e-9)
            out.append((u0 + du * 0.5, v0 + (v1 - v0) * (0.15 + 0.7 * t)))
        return out
    return f
