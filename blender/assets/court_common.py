"""Shared helpers for the court_* assets (the motor court; not an asset itself).

Outdoor surfaces are lit per vertex (baked), so everything big is built as grids of cells
of at most `cell` metres (default 1.5), with clean quads and no sliver triangles:
  panel()        a rectangle in space cut into a grid of quads (normal = u x v)
  box()          six panels (optionally without the bottom)
  polar_patch()  an annulus / arc built from rings and angular steps, facing up
  wall()         a vertical cylinder wall, facing outward or inward
  finish()       turns a bmesh into a part with one material (box-projected UVs if textured)
Colours/materials come from lib/outdoor.py only.
"""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, outdoor  # noqa: E402

importlib.reload(common)
importlib.reload(outdoor)

CELL = 1.5

# colours not in the shared palette (linear RGB)
SOIL_DARK = (0.04, 0.03, 0.022)


def v3(x, y, z):
    return Vector((x, y, z))


def panel(bm, o, u, v, cell=CELL):
    """Grid of quads over the parallelogram o + s*u + t*v; the normal is u x v."""
    o, u, v = Vector(o), Vector(u), Vector(v)
    nu = max(1, math.ceil(u.length / cell - 1e-6))
    nv = max(1, math.ceil(v.length / cell - 1e-6))
    vs = [[bm.verts.new(o + u * (i / nu) + v * (j / nv)) for j in range(nv + 1)] for i in range(nu + 1)]
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))


def box(bm, lo, hi, cell=CELL, bottom=False, top=True, sides="nsew"):
    """Axis-aligned box from lo to hi. sides: which vertical faces to build (n s e w)."""
    lx, ly, lz = lo
    hx, hy, hz = hi
    dx, dy, dz = hx - lx, hy - ly, hz - lz
    if top:
        panel(bm, (lx, ly, hz), (dx, 0, 0), (0, dy, 0), cell)
    if bottom:
        panel(bm, (lx, ly, lz), (0, dy, 0), (dx, 0, 0), cell)
    if "e" in sides:
        panel(bm, (hx, ly, lz), (0, dy, 0), (0, 0, dz), cell)
    if "w" in sides:
        panel(bm, (lx, ly, lz), (0, 0, dz), (0, dy, 0), cell)
    if "n" in sides:
        panel(bm, (lx, hy, lz), (0, 0, dz), (dx, 0, 0), cell)
    if "s" in sides:
        panel(bm, (lx, ly, lz), (dx, 0, 0), (0, 0, dz), cell)


def polar_patch(bm, c, radii, z, seg=64, theta=None, up=True):
    """Rings at `radii` around c, facing up. theta(r) -> (a0, a1) angle range in radians
    (standard maths angle, counter-clockwise from +x), default the full circle. Angular
    steps are shared by every ring so the patch is a clean quad grid."""
    cx, cy = c
    spans = [theta(r) if theta else (0.0, 2 * math.pi) for r in radii]
    full = not theta
    n = max(3, math.ceil(max(b - a for a, b in spans) / (2 * math.pi) * seg - 1e-6))
    rings = []
    for r, (a0, a1) in zip(radii, spans):
        cnt = n if not full else n
        pts = []
        for i in range(cnt + (0 if full else 1)):
            a = a0 + (a1 - a0) * i / cnt
            pts.append(bm.verts.new((cx + r * math.cos(a), cy + r * math.sin(a), z)))
        rings.append(pts)
    for k in range(len(radii) - 1):
        a, b = rings[k], rings[k + 1]
        m = len(a) if full else len(a) - 1
        for i in range(m):
            j = (i + 1) % len(a)
            quad = (a[i], b[i], b[j], a[j])
            bm.faces.new(quad if up else quad[::-1])


def wall(bm, c, r, z0, z1, seg=64, outward=True, rows=1):
    """Vertical cylinder wall around c."""
    cx, cy = c
    for i in range(seg):
        a0, a1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
        for k in range(rows):
            za = z0 + (z1 - z0) * k / rows
            zb = z0 + (z1 - z0) * (k + 1) / rows
            p = [bm.verts.new((cx + r * math.cos(a0), cy + r * math.sin(a0), za)),
                 bm.verts.new((cx + r * math.cos(a1), cy + r * math.sin(a1), za)),
                 bm.verts.new((cx + r * math.cos(a1), cy + r * math.sin(a1), zb)),
                 bm.verts.new((cx + r * math.cos(a0), cy + r * math.sin(a0), zb))]
            bm.faces.new(p if outward else p[::-1])


def finish(name, bm, mat, col, parent, uv_tile=None, smooth=False):
    ob = common.mesh_object(name, bm, col, mat, parent, smooth=smooth)
    if uv_tile:
        common.box_uv(ob, tile=uv_tile)
    return ob


def start(name):
    col = common.fresh_collection(name)
    root = common.empty(name, col)
    return col, root
