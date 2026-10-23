"""Shared bits for the bathhouse's props (ph_*; blender/levels/rooms/bathhouse.py), not an asset.

Materials share names with the bathhouse shell's (rooms/bathhouse.py) where they're the same
stone, so the engine folds them into one (index.html shareMaterial). Water surfaces and the fx
cards (viewer/water_fx.js) are hidden from the bake's light paths (the basins are baked as if
empty: light reaches their floors and steps, which the drained plunge shows)."""
import importlib
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import ph_textures, common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(ph_textures)


def start(name):
    col = common.fresh_collection(name)
    root = common.empty(name, col)
    return col, root


def finish(root):
    bpy.context.view_layer.update()
    return root, [o for o in root.children_recursive if o.type == "MESH"]


def group(name, col, parent, loc=(0, 0, 0), rot=0.0):
    ob = common.empty(name, col, loc)
    ob.rotation_euler = (0, 0, math.radians(rot))
    ob.parent = parent
    return ob


def box(name, lo, hi, mat, col, parent, uv_tile=None, bevel=0.0, smooth=False):
    size = [hi[i] - lo[i] for i in range(3)]
    bm = common.box_bmesh(size)
    bmesh.ops.translate(bm, vec=[(hi[i] + lo[i]) / 2 for i in range(3)], verts=bm.verts)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=2, affect="EDGES", profile=0.5)
    ob = common.mesh_object(name, bm, col, mat, parent, smooth=smooth)
    if uv_tile:
        common.box_uv(ob, tile=uv_tile)
    return ob


def card(name, w, h, mat, col, parent, at=(0, 0, 0), facing="-y", fx=None, **extra):
    """A flat rectangle w x h (UV 0..1 across and up) centred at `at`, facing `facing`
    ("-y", "+y", "-x", "+x", "+z"); fx + extra become custom properties (viewer/water_fx.js)."""
    bm = bmesh.new()
    if facing == "+z":
        pts = [(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)]
    else:
        pts = [(-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2)]
    vs = [bm.verts.new(p) for p in pts]
    f = bm.faces.new(vs)
    uv = bm.loops.layers.uv.new("UVMap")
    for lp, (u, v) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        lp[uv].uv = (u, v)
    rot = {"-y": 0, "+y": 180, "+x": 90, "-x": -90, "+z": 0}[facing]
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(rot), 3, "Z"))
    bmesh.ops.translate(bm, vec=at, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # (recalc may flip a lone face: make it face where it was asked to)
    want = {"-y": (0, -1, 0), "+y": (0, 1, 0), "+x": (1, 0, 0), "-x": (-1, 0, 0), "+z": (0, 0, 1)}[facing]
    for face in bm.faces:
        if sum(face.normal[i] * want[i] for i in range(3)) < 0:
            face.normal_flip()
    ob = common.mesh_object(name, bm, col, mat, parent, smooth=False)
    if fx:
        ob["fx"] = fx
        ob.visible_camera = False      # (not a surface: out of the probes' panoramas too)
    for k, v in extra.items():
        ob[k] = v
    return ob


def no_bake_light(ob):
    """Out of the bake's light paths (water, fx cards): still seen by the probe's camera."""
    ob.visible_diffuse = ob.visible_glossy = ob.visible_shadow = False
    ob.visible_transmission = False
    return ob


# ------------------------------------------------------------------ materials
def stone():
    m = common.pbr_material("M_PH_Stone", (0.21, 0.21, 0.19), roughness=0.86)
    common.set_base_color_map(m, textures.load(ph_textures.coursed_stone()))
    return m


def slab():
    m = common.pbr_material("M_PH_Slab", (0.24, 0.235, 0.215), roughness=0.5)
    common.set_base_color_map(m, textures.load(ph_textures.slabs()))
    return m


def pool_stone():
    m = common.pbr_material("M_PH_PoolStone", (0.12, 0.15, 0.14), roughness=0.35)
    common.set_base_color_map(m, textures.load(ph_textures.slabs(name="T_PH_PoolStone_BaseColor", seed=75,
                                                                    color=(0.11, 0.145, 0.135), rows=8, n=512)))
    return m


def mosaic():
    m = common.pbr_material("M_PH_Mosaic", (0.02, 0.05, 0.05), roughness=0.18)
    common.set_base_color_map(m, textures.load(ph_textures.mosaic(n=512)))
    return m


def cedar():
    m = common.pbr_material("M_PH_Cedar", (0.36, 0.22, 0.13), roughness=0.7)
    common.set_base_color_map(m, textures.load(textures.wood("T_PH_Cedar_BaseColor", (0.22, 0.12, 0.065),
                                                             (0.42, 0.26, 0.15), seed=91, rings=26, n=512)))
    return m


def bronze():
    return common.pbr_material("M_PH_Bronze", (0.30, 0.19, 0.10), roughness=0.38, metallic=0.9)


def dark_bronze():
    return common.pbr_material("M_PH_BronzeDark", (0.07, 0.05, 0.035), roughness=0.45, metallic=0.85)


def linen():
    return materials.fabric("M_PH_Linen", (0.62, 0.6, 0.55), roughness=0.95)


def water(name="M_PH_Water", color=(0.012, 0.045, 0.048), alpha=0.5):
    """A pool's surface: dark teal, glossy; seen through looking down (water_fx: Fresnel alpha)."""
    m = common.pbr_material(name, color, roughness=0.03)
    materials._alpha_blend(m, alpha)
    return m


def fx_material(name="M_PH_FX"):
    """Placeholder for the fx cards (the engine replaces it); black in Blender's previews."""
    return common.pbr_material(name, (0.0, 0.0, 0.0), roughness=1.0)
