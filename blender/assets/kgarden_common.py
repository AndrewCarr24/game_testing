"""Shared geometry helpers for the kitchen garden assets (kgarden_*): a small bmesh builder
that welds vertices, makes grid-cut quads (every shadow-receiving surface is cut into cells
of <= 1.5 m so the baked vertex lighting can show shadows), open-ended bars (no hidden end
caps), boxes, domes and crop ridges. Units are metres.

Materials come from blender/lib/outdoor.py only (flat colours are free)."""
import importlib
import math
import os
import sys

import bmesh
import bpy
from mathutils import Euler, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.abspath(os.path.join(HERE, "..", "lib"))
BLENDER = os.path.abspath(os.path.join(HERE, ".."))
if BLENDER not in sys.path:
    sys.path.insert(0, BLENDER)

from lib import common, outdoor  # noqa: E402

importlib.reload(outdoor)

CELL = 1.5          # max shadow-receiving cell


# ---------------------------------------------------------------- colours (linear)
def flat(name, color):
    return outdoor.flat(f"M_Out_{name}", color)


def terracotta():
    return flat("Terracotta", (0.30, 0.11, 0.06))


def leaf_light():
    return flat("Crop_Lettuce", (0.085, 0.24, 0.035))


def leaf_red():
    return flat("Crop_RedLeaf", (0.07, 0.012, 0.025))


def leaf_blue():
    return flat("Crop_Kale", (0.035, 0.085, 0.07))


def leaf_grey():
    return flat("Crop_Sage", (0.13, 0.17, 0.11))


def leaf_dark():
    return flat("Crop_Dark", (0.025, 0.07, 0.02))


def galvanised():
    return flat("Galvanised", (0.22, 0.23, 0.24))


# ---------------------------------------------------------------- builder
class Builder:
    """Collects geometry per material key, then makes one mesh object per key."""

    def __init__(self, name):
        self.name = name
        self.col = common.fresh_collection(name)
        self.root = common.empty(name, self.col)
        self.keys = {}      # key -> [bmesh, material, uv tile, weld cache]

    def mat(self, key, material, tile=None):
        if key not in self.keys:
            self.keys[key] = [bmesh.new(), material, tile, {}]
        return key

    def _v(self, key, p):
        bm, _, _, cache = self.keys[key]
        k = (round(p[0], 4), round(p[1], 4), round(p[2], 4))
        v = cache.get(k)
        if v is None:
            v = bm.verts.new(p)
            cache[k] = v
        return v

    def face(self, key, pts):
        """One polygon, counter-clockwise seen from outside."""
        vs = [self._v(key, tuple(p)) for p in pts]
        if len({id(v) for v in vs}) < 3:
            return None
        try:
            return self.keys[key][0].faces.new(vs)
        except ValueError:      # duplicate face
            return None

    def quad(self, key, a, b, c, d, cell=None):
        """Bilinear grid from corners a,b,c,d (counter-clockwise from outside), cells <= cell."""
        a, b, c, d = (Vector(p) for p in (a, b, c, d))
        if cell is None:
            self.face(key, (a, b, c, d))
            return
        nx = max(1, math.ceil((b - a).length / cell - 1e-6))
        ny = max(1, math.ceil((d - a).length / cell - 1e-6))

        def pt(i, j):
            u, v = i / nx, j / ny
            return (a * (1 - u) + b * u) * (1 - v) + (d * (1 - u) + c * u) * v
        for j in range(ny):
            for i in range(nx):
                self.face(key, (pt(i, j), pt(i + 1, j), pt(i + 1, j + 1), pt(i, j + 1)))

    def tri(self, key, a, b, c):
        self.face(key, (a, b, c))

    def box(self, key, center, size, rot=(0, 0, 0), cell=None, skip=(), cell_on=None):
        """Box; rot = Euler XYZ degrees about its centre; skip: face names among
        -x +x -y +y -z +z (local axes). cell: grid size on its faces."""
        cx, cy, cz = center
        sx, sy, sz = size
        eul = Euler([math.radians(r) for r in rot], "XYZ").to_matrix()

        def P(x, y, z):
            return Vector(center) + eul @ Vector((x * sx / 2, y * sy / 2, z * sz / 2))
        faces = {
            "-x": ((-1, 1, -1), (-1, -1, -1), (-1, -1, 1), (-1, 1, 1)),
            "+x": ((1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)),
            "-y": ((-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)),
            "+y": ((1, 1, -1), (-1, 1, -1), (-1, 1, 1), (1, 1, 1)),
            "-z": ((-1, -1, -1), (-1, 1, -1), (1, 1, -1), (1, -1, -1)),
            "+z": ((-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)),
        }
        for name, cs in faces.items():
            if name in skip:
                continue
            self.quad(key, *[P(*c) for c in cs], cell=cell if (cell_on is None or name in cell_on) else None)

    def bar(self, key, p0, p1, w, h, up=(0, 0, 1), cap=False):
        """Open-ended rectangular bar from p0 to p1; w across (horizontal-ish), h the other way."""
        p0, p1 = Vector(p0), Vector(p1)
        d = (p1 - p0)
        if d.length < 1e-6:
            return
        dn = d.normalized()
        upv = Vector(up)
        if abs(dn.dot(upv)) > 0.98:
            upv = Vector((0, 1, 0)) if abs(dn.y) < 0.9 else Vector((1, 0, 0))
        u = dn.cross(upv).normalized()
        v = u.cross(dn).normalized()
        ring = [(-1, -1), (1, -1), (1, 1), (-1, 1)]

        def at(p, s):
            return p + u * (s[0] * w / 2) + v * (s[1] * h / 2)
        mid = (p0 + p1) / 2
        for i in range(4):
            a, b = ring[i], ring[(i + 1) % 4]
            quad = [at(p0, a), at(p0, b), at(p1, b), at(p1, a)]
            f = self.face(key, quad)
            if f is not None:
                c = sum(quad, Vector()) / 4
                out = c - (mid + u * 0 + v * 0)
                if f.normal.dot(out) < 0:
                    f.normal_flip()
        if cap:
            for p, sgn in ((p0, -1), (p1, 1)):
                f = self.face(key, [at(p, s) for s in ring])
                if f is not None and f.normal.dot(dn * sgn) < 0:
                    f.normal_flip()

    def prism(self, key, pts, z0, z1, cell=None, skip_bottom=True):
        """Vertical prism from a counter-clockwise outline (x, y) between z0 and z1."""
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            self.quad(key, (a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1), cell=cell)
        self.face(key, [(p[0], p[1], z1) for p in pts])
        if not skip_bottom:
            self.face(key, [(p[0], p[1], z0) for p in reversed(pts)])

    def cyl(self, key, c, r, h, n=8, r_top=None, cap_top=True, cap_bottom=False, phase=0.0):
        r_top = r if r_top is None else r_top
        pts0 = [(c[0] + r * math.cos(phase + 2 * math.pi * i / n), c[1] + r * math.sin(phase + 2 * math.pi * i / n)) for i in range(n)]
        pts1 = [(c[0] + r_top * math.cos(phase + 2 * math.pi * i / n), c[1] + r_top * math.sin(phase + 2 * math.pi * i / n)) for i in range(n)]
        z0, z1 = c[2], c[2] + h
        for i in range(n):
            j = (i + 1) % n
            self.face(key, [(*pts0[i], z0), (*pts0[j], z0), (*pts1[j], z1), (*pts1[i], z1)])
        if cap_top and r_top > 1e-6:
            self.face(key, [(*p, z1) for p in pts1])
        if cap_bottom:
            self.face(key, [(*p, z0) for p in reversed(pts0)])

    def dome(self, key, c, r, h, n=6, rng=None, squash=1.0, rot=0.0):
        """Low lumpy mound: top vertex, one mid ring, one base ring (3n triangles-ish)."""
        cx, cy, cz = c
        jit = (lambda s: 1 + (rng.random() - 0.5) * s) if rng else (lambda s: 1.0)
        base, mid = [], []
        for i in range(n):
            a = rot + 2 * math.pi * i / n
            rr = r * jit(0.22)
            base.append((cx + rr * math.cos(a), cy + rr * math.sin(a) * squash, cz))
            mid.append((cx + rr * 0.84 * math.cos(a), cy + rr * 0.84 * math.sin(a) * squash, cz + h * 0.66 * jit(0.2)))
        top = (cx, cy, cz + h * jit(0.2))
        for i in range(n):
            j = (i + 1) % n
            self.face(key, [base[i], base[j], mid[j], mid[i]])
            self.face(key, [mid[i], mid[j], top])

    def ridge(self, key, p0, p1, w, h, sections, rng, lows=0.55, jitter=0.18, profile=None):
        """A row of crop: a lumpy 4-point ridge along p0->p1 (z of p is the ground)."""
        p0, p1 = Vector(p0), Vector(p1)
        d = (p1 - p0)
        L = d.length
        dn = d / L
        side = Vector((-dn.y, dn.x, 0))
        prof = []
        for i in range(sections + 1):
            t = i / sections
            c = p0 + d * t
            hump = profile[i] if profile else (1.0 if i % 2 == 0 else lows)
            hh = h * hump * (1 + (rng.random() - 0.5) * jitter * 2)
            ww = w * (0.55 + 0.45 * hump) * (1 + (rng.random() - 0.5) * jitter)
            prof.append([c - side * ww, c - side * ww * 0.42 + Vector((0, 0, hh)),
                         c + side * ww * 0.42 + Vector((0, 0, hh)), c + side * ww])
        for i in range(sections):
            a, b = prof[i], prof[i + 1]
            for k in range(3):
                self.face(key, [a[k + 1], b[k + 1], b[k], a[k]])
        for pr, rev in ((prof[0], True), (prof[-1], False)):
            self.face(key, list(reversed(pr)) if rev else pr)

    def finish(self):
        parts = []
        for key, (bm, mat, tile, _) in self.keys.items():
            if not bm.faces:
                bm.free()
                continue
            ob = common.mesh_object(f"{self.name}_{key}", bm, self.col, mat, self.root, smooth=False)
            if tile:
                common.box_uv(ob, tile)
            parts.append(ob)
        return self.root, parts


def report(root, parts):
    print(f"{root.name}: {len(parts)} meshes, {common.triangle_count(parts)} tris")
