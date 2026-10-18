"""Shared bmesh helpers for the drive_gate zone assets (prefix gate_). Not an asset.

Everything is built directly in bmesh (no modifiers: the grounds copy raw mesh data) with
hard edges, and large faces are cut into cells of <= 1.5 m so the baked vertex lighting
can show shadows across them.
"""
import math
import os
import sys

import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, outdoor  # noqa: E402

STEP = 1.5


def V(*a):
    return Vector(a)


class Parts:
    """One bmesh per (name, material); `finish` turns them into mesh objects under root."""

    def __init__(self, asset, col, root):
        self.asset, self.col, self.root = asset, col, root
        self.items = {}

    def bm(self, part, mat, uv_tile=0.0):
        if part not in self.items:
            self.items[part] = [bmesh.new(), mat, uv_tile]
        return self.items[part][0]

    def finish(self):
        out = []
        for part, (bm, mat, uv_tile) in self.items.items():
            ob = common.mesh_object(f"{self.asset}_{part}", bm, self.col, mat, self.root, smooth=False)
            if uv_tile:
                common.box_uv(ob, tile=uv_tile)
            out.append(ob)
        return out


def quad(bm, a, b, c, d):
    return bm.faces.new([bm.verts.new(p) for p in (a, b, c, d)])


def grid_face(bm, origin, u, v, nu_len, nv_len, step=STEP, cuts_u=None, cuts_v=None):
    """Quad grid on the plane origin + a*u + b*v (u, v unit vectors); normal = u x v.
    Cells <= step; extra grid lines at cuts_u / cuts_v (absolute distances)."""
    def lines(length, extra):
        n = max(1, math.ceil(length / step - 1e-6))
        s = {round(length * i / n, 5) for i in range(n + 1)}
        for e in extra or ():
            s.add(round(e, 5))
        return sorted(s)
    us, vs = lines(nu_len, cuts_u), lines(nv_len, cuts_v)
    verts = {}
    for i, a in enumerate(us):
        for j, b in enumerate(vs):
            verts[i, j] = bm.verts.new(origin + u * a + v * b)
    faces = []
    for i in range(len(us) - 1):
        for j in range(len(vs) - 1):
            faces.append(bm.faces.new((verts[i, j], verts[i + 1, j], verts[i + 1, j + 1], verts[i, j + 1])))
    return faces


def box(bm, lo, hi, step=STEP, bottom=False, top=True, sides="nsew"):
    """Axis-aligned box with all outward faces gridded. bottom/top toggle those faces;
    sides is the subset of 'n','s','e','w' (+y, -y, +x, -x) to emit."""
    lo, hi = Vector(lo), Vector(hi)
    sx, sy, sz = hi.x - lo.x, hi.y - lo.y, hi.z - lo.z
    X, Y, Z = V(1, 0, 0), V(0, 1, 0), V(0, 0, 1)
    if "e" in sides:
        grid_face(bm, V(hi.x, lo.y, lo.z), Y, Z, sy, sz, step)
    if "w" in sides:
        grid_face(bm, V(lo.x, hi.y, lo.z), -Y, Z, sy, sz, step)
    if "n" in sides:
        grid_face(bm, V(hi.x, hi.y, lo.z), -X, Z, sx, sz, step)
    if "s" in sides:
        grid_face(bm, V(lo.x, lo.y, lo.z), X, Z, sx, sz, step)
    if top:
        grid_face(bm, V(lo.x, lo.y, hi.z), X, Y, sx, sy, step)
    if bottom:
        grid_face(bm, V(lo.x, hi.y, lo.z), X, -Y, sx, sy, step)


def wall_face(bm, origin, u, v, n, length, height, openings=(), step=STEP):
    """A wall face at `origin` (u along it, v up, n = u x v outward) with rectangular
    openings [(a0, a1, b0, b1)] left empty. Grid lines run through the opening edges."""
    ca = sorted({o[0] for o in openings} | {o[1] for o in openings})
    cb = sorted({o[2] for o in openings} | {o[3] for o in openings})

    def lines(L, extra):
        n_ = max(1, math.ceil(L / step - 1e-6))
        s = {round(L * i / n_, 5) for i in range(n_ + 1)} | {round(e, 5) for e in extra if 0 < e < L}
        return sorted(s)
    us, vs = lines(length, ca), lines(height, cb)
    verts = {}

    def vert(i, j):
        if (i, j) not in verts:
            verts[i, j] = bm.verts.new(origin + u * us[i] + v * vs[j])
        return verts[i, j]
    for i in range(len(us) - 1):
        for j in range(len(vs) - 1):
            ma, mb = (us[i] + us[i + 1]) / 2, (vs[j] + vs[j + 1]) / 2
            if any(o[0] < ma < o[1] and o[2] < mb < o[3] for o in openings):
                continue
            bm.faces.new((vert(i, j), vert(i + 1, j), vert(i + 1, j + 1), vert(i, j + 1)))


def reveals(bm, origin, u, v, n, thick, openings):
    """The four reveal quads of each opening, running `thick` deep (against n)."""
    def P(a, b, d=0.0):
        return origin + u * a + v * b - n * d
    for a0, a1, b0, b1 in openings:
        quad(bm, P(a0, b0), P(a1, b0), P(a1, b0, thick), P(a0, b0, thick))          # sill, faces +v
        quad(bm, P(a1, b1), P(a0, b1), P(a0, b1, thick), P(a1, b1, thick))          # head, faces -v
        quad(bm, P(a0, b1), P(a0, b0), P(a0, b0, thick), P(a0, b1, thick))          # left jamb, faces +u
        quad(bm, P(a1, b0), P(a1, b1), P(a1, b1, thick), P(a1, b0, thick))          # right jamb, faces -u


def cylinder(bm, centre, r, z0, z1, sides=8, cap_top=True):
    cx, cy = centre
    ring0 = [bm.verts.new((cx + r * math.cos(2 * math.pi * i / sides), cy + r * math.sin(2 * math.pi * i / sides), z0))
             for i in range(sides)]
    ring1 = [bm.verts.new((cx + r * math.cos(2 * math.pi * i / sides), cy + r * math.sin(2 * math.pi * i / sides), z1))
             for i in range(sides)]
    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new((ring0[i], ring0[j], ring1[j], ring1[i]))
    if cap_top:
        bm.faces.new(ring1)
