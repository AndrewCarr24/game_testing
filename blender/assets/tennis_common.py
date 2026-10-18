"""Shared building blocks for the tennis_* assets (not an asset itself): a small
multi-part mesh builder (boxes with chosen faces and a maximum cell size so the baked
vertex lighting has resolution, struts at any angle, grids) and the court palette."""
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

# ----------------------------------------------------------------- palette (linear RGB)
COURT_SURROUND = (0.022, 0.082, 0.040)   # dark green hard court
COURT_PLAY = (0.050, 0.105, 0.150)       # blue-grey playing area
LINE_WHITE = (0.72, 0.72, 0.70)
NET_TAPE = (0.78, 0.78, 0.76)

COURT_TOP = 0.05                          # court slab above the lawn (assets sitting on it are placed at z = 0.05)


def mat_surround():
    return outdoor.flat("M_Out_Tennis_Green", COURT_SURROUND)


def mat_play():
    return outdoor.flat("M_Out_Tennis_Blue", COURT_PLAY)


def mat_line():
    return outdoor.flat("M_Out_Tennis_Line", LINE_WHITE)


def mat_tape():
    return outdoor.flat("M_Out_Tennis_Tape", NET_TAPE)


def mat_metal():
    return outdoor.dark_metal()


def mat_render():
    return outdoor.render_white()


def mat_veil():
    """Fence fabric / net mesh: the shared faint dark see-through material."""
    return outdoor.glass()


# ----------------------------------------------------------------------------- builder
FACES = {"+x": (0, 1), "-x": (0, -1), "+y": (1, 1), "-y": (1, -1), "+z": (2, 1), "-z": (2, -1)}
ALL = "+x -x +y -y +z -z"


def _cells(lo, hi, cell):
    if not cell:
        return [lo, hi]
    n = max(1, int(math.ceil((hi - lo) / cell - 1e-6)))
    return [lo + (hi - lo) * k / n for k in range(n + 1)]


class Builder:
    """Parts are meshes of one material each, named `<asset>_<part>`."""

    def __init__(self, asset):
        self.asset = asset
        self.parts = {}      # part -> [material, bmesh, uv_tile]

    def part(self, name, mat, uv=None):
        if name not in self.parts:
            self.parts[name] = [mat, bmesh.new(), uv]
        return name

    def _bm(self, part):
        return self.parts[part][1]

    # -- primitives ---------------------------------------------------------
    def quad(self, part, p0, p1, p2, p3, M=None):
        bm = self._bm(part)
        vs = [bm.verts.new(Vector(p)) for p in (p0, p1, p2, p3)]
        bm.faces.new(vs)
        if M is not None:
            bmesh.ops.transform(bm, matrix=M, verts=vs)

    def grid(self, part, axis, sign, c, us, vs, offset=(0, 0, 0)):
        """Axis-aligned grid at coordinate c on `axis` facing `sign`; us / vs are the
        coordinate lists along axes (axis+1)%3 and (axis+2)%3."""
        bm = self._bm(part)
        i, j = (axis + 1) % 3, (axis + 2) % 3
        for a in range(len(us) - 1):
            for b in range(len(vs) - 1):
                pts = []
                for (u, v) in ((us[a], vs[b]), (us[a + 1], vs[b]), (us[a + 1], vs[b + 1]), (us[a], vs[b + 1])):
                    p = [0.0, 0.0, 0.0]
                    p[axis], p[i], p[j] = c, u, v
                    pts.append(bm.verts.new(Vector(p) + Vector(offset)))
                if sign < 0:
                    pts.reverse()
                bm.faces.new(pts)

    def box(self, part, lo, hi, faces=ALL, cell=None, M=None):
        """Axis-aligned box; `faces` lists the faces to create, `cell` the largest cell
        edge (m) of each face. M: optional transform (applied to this box's vertices)."""
        bm = self._bm(part)
        before = set(bm.verts)
        for f in faces.split():
            ax, sg = FACES[f]
            i, j = (ax + 1) % 3, (ax + 2) % 3
            c = hi[ax] if sg > 0 else lo[ax]
            self.grid(part, ax, sg, c, _cells(lo[i], hi[i], cell), _cells(lo[j], hi[j], cell))
        if M is not None:
            bmesh.ops.transform(bm, matrix=M, verts=[v for v in bm.verts if v not in before])

    def strut(self, part, a, b, wa, wb=None, caps=True, wa2=None, wb2=None):
        """Square (or rectangular: w x w2) post from point a to point b, tapering from
        wa to wb. The cross-section axes: u horizontal, v perpendicular."""
        wb = wa if wb is None else wb
        wa2 = wa if wa2 is None else wa2
        wb2 = wb if wb2 is None else wb2
        bm = self._bm(part)
        a, b = Vector(a), Vector(b)
        d = (b - a).normalized()
        ref = Vector((0, 0, 1)) if abs(d.z) < 0.99 else Vector((1, 0, 0))
        u = d.cross(ref).normalized()
        v = d.cross(u).normalized()
        ring = lambda p, w, w2: [bm.verts.new(p + u * (sx * w / 2) + v * (sy * w2 / 2))
                                 for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        ra, rb = ring(a, wa, wa2), ring(b, wb, wb2)
        for k in range(4):
            bm.faces.new((ra[k], ra[(k + 1) % 4], rb[(k + 1) % 4], rb[k]))
        if caps:
            bm.faces.new(ra[::-1])
            bm.faces.new(rb)

    # -- finishing ----------------------------------------------------------
    def finish(self, col, root, smooth=False):
        out = []
        for name, (mat, bm, uv) in self.parts.items():
            if not bm.faces:
                bm.free()
                continue
            ob = common.mesh_object(f"{self.asset}_{name}", bm, col, mat, root, smooth=smooth)
            if uv:
                common.box_uv(ob, tile=uv)
            out.append(ob)
        return out


def standalone(asset):
    """Collection + root empty for an asset."""
    col = common.fresh_collection(asset)
    root = common.empty(asset, col)
    return col, root
