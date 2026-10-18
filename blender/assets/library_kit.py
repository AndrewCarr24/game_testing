"""Shared helpers for the library_* assets (not an asset itself): a bmesh builder
with world-scale UVs (boxes, lathed solids, quads) and the library's few materials."""
import importlib
import math
import os
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(textures)
importlib.reload(materials)


class Mesh:
    """Accumulates geometry for ONE mesh object (one material) with a UV layer."""

    def __init__(self, tile=0.5):
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.tile = tile

    def _set_uv_box(self, faces, size, shift, tile):
        for f in faces:
            n = [abs(c) for c in f.normal]
            na = n.index(max(n))
            a, b = [i for i in range(3) if i != na]
            if size[b] > size[a]:
                a, b = b, a
            for lp in f.loops:
                co = lp.vert.co
                lp[self.uv].uv = (co[a] / tile + shift[0], co[b] / tile + shift[1])

    def box(self, centre, size, shift=(0.0, 0.0), rot=None, tile=None, taper=None):
        """Axis-aligned box; rot = (angle, axis 'x'|'y'|'z') about its own centre.
        taper = (sx, sy): scale of the top face's x/y relative to the bottom."""
        tile = tile or self.tile
        res = bmesh.ops.create_cube(self.bm, size=1.0)
        verts = res["verts"]
        bmesh.ops.scale(self.bm, vec=Vector(size), verts=verts)
        if taper:
            for v in verts:
                if v.co.z > 0:
                    v.co.x *= taper[0]
                    v.co.y *= taper[1]
        if rot:
            ang, axis = rot
            bmesh.ops.rotate(self.bm, verts=verts, cent=(0, 0, 0), matrix=Matrix.Rotation(ang, 3, axis.upper()))
        bmesh.ops.translate(self.bm, vec=Vector(centre), verts=verts)
        faces = list({f for v in verts for f in v.link_faces})
        bmesh.ops.recalc_face_normals(self.bm, faces=faces)
        self._set_uv_box(faces, size, shift, tile)
        return verts

    def lathe(self, profile, segs=24, centre=(0, 0, 0), tile=None, smooth_angle=None):
        """Solid of revolution about Z from [(r, z), ...] (r = 0 collapses to the axis).
        UV: u around (metres / tile), v along the profile."""
        tile = tile or self.tile
        bm = self.bm
        rows = []
        for r, z in profile:
            if abs(r) < 1e-9:
                rows.append([bm.verts.new((centre[0], centre[1], centre[2] + z))] * segs)
            else:
                rows.append([bm.verts.new((centre[0] + r * math.cos(2 * math.pi * s / segs),
                                           centre[1] + r * math.sin(2 * math.pi * s / segs),
                                           centre[2] + z)) for s in range(segs)])
        faces = []
        for i in range(len(profile) - 1):
            (r0, z0), (r1, z1) = profile[i], profile[i + 1]
            k = 2 * math.pi * max(r0, r1, 0.01) / segs / tile
            for s in range(segs):
                s2 = (s + 1) % segs
                quad = [(rows[i][s], s, z0), (rows[i][s2], s + 1, z0), (rows[i + 1][s2], s + 1, z1), (rows[i + 1][s], s, z1)]
                uniq = []
                for v, u, z in quad:
                    if all(v is not q[0] for q in uniq):
                        uniq.append((v, u, z))
                if len(uniq) < 3:
                    continue
                try:
                    f = bm.faces.new([q[0] for q in uniq])
                except ValueError:
                    continue
                faces.append(f)
                for lp, (v, u, z) in zip(f.loops, uniq):
                    lp[self.uv].uv = (u * k, z / tile)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        return faces

    def quad(self, pts, uvs):
        f = self.bm.faces.new([self.bm.verts.new(p) for p in pts])
        for lp, uv in zip(f.loops, uvs):
            lp[self.uv].uv = uv
        return f

    def to_object(self, name, col, mat, parent, smooth=False):
        if smooth:
            for f in self.bm.faces:
                f.smooth = True
        return common.mesh_object(name, self.bm, col, mat, parent, smooth=smooth)


# --------------------------------------------------------------- materials
# (names are shared with other assets where the colour is the same)

def leather_cognac():
    m = common.pbr_material("M_Leather_Cognac", (0.23, 0.075, 0.025), roughness=0.62)
    common.set_normal_map(m, textures.load(textures.leather_normal(), non_color=True), 0.6)
    return m


def leather_green():
    m = common.pbr_material("M_Leather_LibraryGreen", (0.012, 0.055, 0.032), roughness=0.55)
    common.set_normal_map(m, textures.load(textures.leather_normal(), non_color=True), 0.6)
    return m


def linen_navy():
    return materials.fabric("M_Fabric_LibraryNavy", (0.018, 0.028, 0.06))


def linen_oat():
    return materials.fabric("M_Fabric_Oat", (0.42, 0.37, 0.30))


def black_felt():
    return common.pbr_material("M_Library_Dark", (0.02, 0.018, 0.016), roughness=0.8)


def merge_objects(objs, name, col, parent):
    """Bake modifiers and transforms of `objs` (same material) and join them into one
    mesh object, so the asset costs one draw call instead of one per cushion."""
    import bpy
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in objs:
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        ob.modifiers.clear()
        old = ob.data
        ob.data = me
        bpy.data.meshes.remove(old)
        me.transform(ob.matrix_basis)
        ob.matrix_basis = Matrix.Identity(4)
        for poly in me.polygons:
            poly.use_smooth = True
    view_layer = bpy.context.view_layer
    for o in list(view_layer.objects.selected):
        o.select_set(False)
    for ob in objs:
        ob.select_set(True)
    view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    joined = view_layer.objects.active
    joined.name = name
    joined.data.name = name
    joined.select_set(False)
    return joined
