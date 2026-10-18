"""Shared building blocks for the garden_* assets (west garden; not an asset itself).

All garden assets are modelled in the garden's own frame: origin on the lawn at the pool's
centre (world x -46.5, y 0), +x east (towards the house), +y north, z = 0 the lawn. The
zone module places them all at that one point. Surfaces that take baked shadows are cut
into cells of 1.5 m or less. Materials come from lib/outdoor.py only.
"""
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

CELL = 1.5          # largest lit surface cell
PAVE_Z = 0.06       # paving top = terrace top
JOINT_Z = 0.035     # dark joint plane under the slabs
GRAVEL_Z = 0.04


# --------------------------------------------------------------------- palette
def coping():
    """Honed pale limestone for the pool coping and the plinths: a touch lighter than the
    textured paving so the water's edge reads as a crisp line."""
    return outdoor.flat("M_Garden_Coping", (0.57, 0.55, 0.50))


def joint():
    return outdoor.flat("M_Garden_Joint", (0.10, 0.095, 0.09))


def pool_floor():
    return outdoor.flat("M_Garden_PoolFloor", (0.015, 0.05, 0.06))


def bronze():
    return outdoor.flat("M_Garden_Bronze", (0.27, 0.145, 0.058))


def render():
    return outdoor.flat("M_Garden_Render", (0.72, 0.71, 0.67))


# --------------------------------------------------------------------- builder
def _n(length, step=CELL):
    return max(1, int(math.ceil(length / step - 1e-6)))


class Builder:
    """Collects quads per material in one bmesh each, then makes one object per material."""

    def __init__(self):
        self.bms = {}
        self.mats = {}
        self.uv = {}

    def bm(self, mat, uv_tile=None):
        b = self.bms.get(mat.name)
        if b is None:
            b = self.bms[mat.name] = bmesh.new()
            self.mats[mat.name] = mat
            self.uv[mat.name] = uv_tile
        return b

    def grid(self, mat, origin, du, dv, step=CELL, uv_tile=None):
        """Quads over the parallelogram origin + a*du + b*dv, cells of at most `step`."""
        b = self.bm(mat, uv_tile)
        du, dv, o = Vector(du), Vector(dv), Vector(origin)
        nu, nv = _n(du.length, step), _n(dv.length, step)
        verts = [[b.verts.new(o + du * (i / nu) + dv * (j / nv)) for j in range(nv + 1)] for i in range(nu + 1)]
        for i in range(nu):
            for j in range(nv):
                b.faces.new((verts[i][j], verts[i + 1][j], verts[i + 1][j + 1], verts[i][j + 1]))

    def box(self, mat, lo, hi, step=CELL, skip=(), only=None, uv_tile=None):
        """Axis-aligned box faces, outward normals. skip / only: names like "-z", "+x"."""
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
        faces = {
            "+z": ((x0, y0, z1), (dx, 0, 0), (0, dy, 0)),
            "-z": ((x0, y0, z0), (0, dy, 0), (dx, 0, 0)),
            "+x": ((x1, y0, z0), (0, dy, 0), (0, 0, dz)),
            "-x": ((x0, y0, z0), (0, 0, dz), (0, dy, 0)),
            "+y": ((x0, y1, z0), (0, 0, dz), (dx, 0, 0)),
            "-y": ((x0, y0, z0), (dx, 0, 0), (0, 0, dz)),
        }
        for name, (o, a, c) in faces.items():
            if name in skip or (only is not None and name not in only):
                continue
            self.grid(mat, o, a, c, step, uv_tile)

    def finish(self, name, col, root, smooth=False):
        objs = []
        for key, b in self.bms.items():
            bmesh.ops.remove_doubles(b, verts=b.verts[:], dist=1e-5)
            ob = common.mesh_object(f"{name}_{key.replace('M_Garden_', '').replace('M_Out_', '').replace('M_Grounds_', '')}",
                                    b, col, self.mats[key], root, smooth=smooth)
            if self.uv[key]:
                common.box_uv(ob, tile=self.uv[key])
            objs.append(ob)
        return objs


def tile_rect(x0, y0, x1, y1, size_u, size_v):
    """Equal slabs filling the rectangle, each about size_u x size_v."""
    nu, nv = max(1, round((x1 - x0) / size_u)), max(1, round((y1 - y0) / size_v))
    out = []
    for i in range(nu):
        for j in range(nv):
            out.append((x0 + (x1 - x0) * i / nu, y0 + (y1 - y0) * j / nv,
                        x0 + (x1 - x0) * (i + 1) / nu, y0 + (y1 - y0) * (j + 1) / nv))
    return out


def clipped_cube(b, mat, cx, cy, z0, half, height, taper=0.05, uv_tile=1.5):
    """A clipped box-hedge cube: a slightly tapered frustum with a flat top (no bottom)."""
    bm = b.bm(mat, uv_tile)
    rings = [(half, z0), (half - taper, z0 + height)]
    vs = [[bm.verts.new((cx + sx * r, cy + sy * r, z)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
          for r, z in rings]
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((vs[0][i], vs[0][j], vs[1][j], vs[1][i]))
    bm.faces.new(vs[1])      # counter-clockwise seen from above: faces up


def new_asset(name):
    col = common.fresh_collection(name)
    root = common.empty(name, col)
    return col, root
