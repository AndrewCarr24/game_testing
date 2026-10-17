"""Shared material palette. Assets get their materials here so the same
material (and texture) is reused across assets and the game loads it once.

Each function returns a Blender material, creating it on first use. Texture
tiles assume world-scale UVs from common.box_uv (wood 0.5 m, fabric 0.25 m).
"""
import importlib

from . import common, textures

importlib.reload(common)
importlib.reload(textures)


def _alpha_blend(mat, alpha):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Alpha"].default_value = alpha
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    else:
        mat.blend_method = "BLEND"
    return mat


# --- office palette ---------------------------------------------------------

def walnut():
    m = common.pbr_material("M_Walnut", (0.105, 0.042, 0.016), roughness=0.5, coat=0.25)
    common.set_base_color_map(m, textures.load(textures.walnut()))
    return m


def steel():
    return common.pbr_material("M_Steel_Polished", (0.85, 0.85, 0.86), roughness=0.08, metallic=1.0)


def black_metal():
    return common.pbr_material("M_Aluminium_Black", (0.02, 0.02, 0.022), roughness=0.35, metallic=0.7)


# --- bedroom palette: smoked oak, bronze, ink-blue and oat fabrics -------------

def smoked_oak():
    m = common.pbr_material("M_OakSmoked", (0.05, 0.035, 0.024), roughness=0.55, coat=0.15)
    common.set_base_color_map(m, textures.load(textures.wood(
        "T_OakSmoked_BaseColor", dark=(0.022, 0.015, 0.010), light=(0.075, 0.052, 0.034), seed=23)))
    return m


def bronze():
    """Brushed, slightly darkened bronze for pulls, lamp bases, legs."""
    return common.pbr_material("M_Bronze", (0.42, 0.26, 0.13), roughness=0.32, metallic=1.0)


def fabric(name, color, roughness=0.9):
    """Upholstery or bedding: base colour + shared weave normal map.
    e.g. fabric("M_Fabric_Ink", (0.02, 0.03, 0.06)) for velvet-ish headboards,
    fabric("M_Fabric_Oat", (0.42, 0.37, 0.30)) for linen."""
    m = common.pbr_material(name, color, roughness=roughness)
    common.set_normal_map(m, textures.load(textures.fabric("T_Fabric_Normal"), non_color=True), 0.5)
    return m


def glass(name="M_Glass_Clear", tint=(0.85, 0.9, 0.9), alpha=0.18, roughness=0.03):
    """Clear or tinted glass, rendered alpha-blended (cheap on the web; no
    transmission pass). Reflections come from the room's environment."""
    m = common.pbr_material(name, tint, roughness=roughness)
    return _alpha_blend(m, alpha)


def emissive(name, color, strength):
    m = common.pbr_material(name, color, roughness=0.6)
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Emission Color"].default_value = (*color, 1)
    bsdf.inputs["Emission Strength"].default_value = strength
    return m
