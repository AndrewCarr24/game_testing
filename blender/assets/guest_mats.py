"""Shared materials for the guest suite and the gym (guest_* assets): light oak,
linen, sage, a pale wool for rugs. Every guest_* asset takes its materials from
here so the game loads each of them once. Not an asset itself."""
import importlib
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(materials)
importlib.reload(textures)


def oak():
    """Pale European oak, straight grain, matte oil finish. One tile = 0.5 m."""
    m = common.pbr_material("M_Oak_Light", (0.42, 0.28, 0.15), roughness=0.55, coat=0.05)
    common.set_base_color_map(m, textures.load(textures.wood(
        "T_Guest_Oak_BaseColor", dark=(0.30, 0.19, 0.095), light=(0.55, 0.385, 0.215), rings=34, seed=41)))
    return m


def linen():
    return materials.fabric("M_Fabric_Linen", (0.52, 0.49, 0.42))


def sage():
    return materials.fabric("M_Fabric_Sage", (0.16, 0.225, 0.14))


def sage_light():
    return materials.fabric("M_Fabric_SageLight", (0.30, 0.38, 0.26))


def black():
    return materials.black_metal()


def brass():
    return materials.bronze()


def rug_wool():
    """Soft oat wool with a faint loop texture. One tile = 0.5 m."""
    path = os.path.join(textures.TEX_DIR, "T_Guest_Wool_BaseColor.png")
    if not os.path.exists(path):
        rng = np.random.default_rng(55)
        n = 1024
        fibre = textures._noise(n, 1.0, 1.0, 0.3, rng)
        loops = textures._noise(n, 1.0, 1.0, 1.2, rng)
        mottle = textures._noise(n, 1.0, 1.0, 2.4, rng)
        t = np.clip(0.5 + 0.30 * fibre + 0.22 * loops + 0.16 * mottle, 0, 1)
        dark = np.array([0.40, 0.36, 0.30])
        light = np.array([0.62, 0.58, 0.50])
        lin = dark + (light - dark) * (t ** 1.4)[..., None]
        textures._save("T_Guest_Wool_BaseColor", textures._to_srgb(lin))
    m = common.pbr_material("M_Wool_Oat", (0.5, 0.46, 0.4), roughness=0.95)
    common.set_base_color_map(m, textures.load(path))
    return m


# ------------------------------------------------------------------ geometry
import bmesh  # noqa: E402


def cyl_bmesh(r, h, r2=None, seg=24, axis="z"):
    """Capped cylinder / cone of radius r (bottom) and r2 (top), height h, centred on the
    origin, axis z (or x / y)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                          radius1=r, radius2=r if r2 is None else r2, depth=h)
    if axis == "x":
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=__import__("mathutils").Matrix.Rotation(1.5707963, 3, "Y"))
    elif axis == "y":
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=__import__("mathutils").Matrix.Rotation(1.5707963, 3, "X"))
    return bm


def taper_bmesh(w_top, w_bot, h, d_top=None, d_bot=None):
    """Square (or rectangular) tapering leg centred on the origin; wide at the top."""
    d_top = w_top if d_top is None else d_top
    d_bot = w_bot if d_bot is None else d_bot
    bm = common.box_bmesh((1, 1, h))
    for v in bm.verts:
        top = v.co.z > 0
        v.co.x = (w_top if top else w_bot) * (0.5 if v.co.x > 0 else -0.5)
        v.co.y = (d_top if top else d_bot) * (0.5 if v.co.y > 0 else -0.5)
    return bm


def add(owner, name, bm, mat, location=(0, 0, 0), bevel=0.003, bucket=None, tile=0.5, parent=None):
    """mesh_object + location + bevel + box UVs in one call. `owner` is (col, root, prefix)."""
    col, root, n = owner
    ob = common.mesh_object(f"{n}_{name}", bm, col, mat, parent or root)
    ob.location = location
    if bevel:
        common.add_bevel(ob, bevel, segments=2)
    common.box_uv(ob, tile=tile)
    if bucket is not None:
        bucket.append(ob)
    return ob


# ---------------------------------------------------------------------- gym
def graphite():
    """Powder-coated graphite steel for gym frames."""
    return common.pbr_material("M_Steel_Graphite", (0.045, 0.047, 0.05), roughness=0.4, metallic=0.85)


def rubber():
    return common.pbr_material("M_Rubber_Black", (0.012, 0.012, 0.013), roughness=0.85)


def pad(name="M_Pad_Charcoal", color=(0.035, 0.036, 0.04)):
    m = common.pbr_material(name, color, roughness=0.55)
    common.set_normal_map(m, textures.load(textures.leather_normal(), non_color=True), 0.5)
    return m


def screen():
    return materials.emissive("M_Screen_Dark", (0.04, 0.13, 0.2), 0.6)


# ---------------------------------------------------------- draw-call savers
import bpy  # noqa: E402


def consolidate(root, max_dim=0.35, min_group=2):
    """Merge the small mesh parts of an asset that share a material into one mesh
    each (named `<Asset>_DetailPiping_<material>`: the level's collider pass skips
    names containing "Piping", so small hardware never makes invisible blocks).
    Parts bigger than `max_dim` (anything the player could stand on or bump into),
    parts under an interactable and parts with no material are left alone.
    Returns the asset's mesh parts."""
    def moves(ob):
        while ob is not None:
            if "interact" in ob.keys():
                return True
            ob = ob.parent
        return False

    groups = {}
    for ob in root.children:
        if ob.type != "MESH" or moves(ob) or not ob.data.materials or ob.data.materials[0] is None:
            continue
        if max(ob.dimensions) > max_dim:
            continue
        groups.setdefault(ob.data.materials[0].name, []).append(ob)
    view = bpy.context.view_layer
    for matname, obs in groups.items():
        if len(obs) < min_group:
            continue
        for o in view.objects.selected:
            o.select_set(False)
        for o in obs:
            o.select_set(True)
        view.objects.active = obs[0]
        bpy.ops.object.convert(target="MESH")
        bpy.ops.object.join()
        merged = view.objects.active
        merged.name = f"{root.name}_DetailPiping_{matname.replace('M_', '')}"
        merged.data.name = merged.name
        merged.select_set(False)
    return [o for o in root.children_recursive if o.type == "MESH"]
