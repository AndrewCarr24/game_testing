"""Outdoor material palette (the grounds around the house).

Everything outdoors is merged into a handful of meshes and its lighting is baked into
vertex colours (blender/levels/grounds.py, bake.py), then drawn with the cheapest
material the engine has. How a material is drawn depends only on its kind:

  flat      any UNTEXTURED material (any name, any colour): its colour and its lighting
            are baked together, so ALL flat materials share one draw call. Use as many
            flat colours as you like. Emission (lamps) is kept.
  textured  only the textured materials below (stone, teak, foliage, grass, gravel):
            one draw call each, the texture times the baked lighting.
  water     water() only: a cheap sky-reflecting water shader in the engine.
  glass     glass() only: faintly tinted, see-through.

So: never add a texture to a new material (it would cost a draw call and memory);
vary colour with separate flat materials instead. Roughness/metalness don't matter
outdoors (the engine shows baked diffuse light), so choose colours carefully: they are
what the player sees. Tiles assume world-scale UVs from common.box_uv.
"""
import importlib
import os

from . import common, textures

importlib.reload(common)
importlib.reload(textures)

TEX = textures.TEX_DIR


def flat(name, color, emission=None, strength=0.0):
    """Any untextured outdoor material. name: M_Out_<What> (unique per colour)."""
    m = common.pbr_material(name, color, roughness=0.8)
    if emission:
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = strength
    return m


# --- textured (one draw call each; use these, don't invent new ones) ---------

def stone():
    """Pale limestone paving / coping / steps / walls. Tile 2 m (box_uv tile=2.0)."""
    m = common.pbr_material("M_Grounds_Stone", (0.55, 0.52, 0.47), roughness=0.8)
    common.set_base_color_map(m, textures.load(os.path.join(TEX, "T_Courtyard_Limestone_BaseColor.png")))
    return m


def coursed_stone():
    """(the bathhouse) Its walls outside: the same thin-coursed grey-green gneiss as inside
    (lib/ph_textures.py), one more textured outdoor draw call, chosen on purpose: the building
    is half stone, half glass, and from the lawn the stone must read as stone. Tile 2 m."""
    from . import ph_textures
    m = common.pbr_material("M_Out_BathStone", (0.21, 0.21, 0.19), roughness=0.86)
    common.set_base_color_map(m, textures.load(ph_textures.coursed_stone()))
    return m


def teak():
    """Weathered teak: decking, benches, loungers, pergola timbers. Tile 0.5 m."""
    m = common.pbr_material("M_Out_Teak", (0.35, 0.25, 0.16), roughness=0.7)
    common.set_base_color_map(m, textures.load(os.path.join(TEX, "T_Courtyard_Teak_BaseColor.png")))
    return m


def foliage():
    """Leaves: tree crowns, clipped hedges, shrubs, topiary. Tile 1.5 m. Tint it via
    variants of crown shape, not colour (it's one material)."""
    m = common.pbr_material("M_Grounds_Hedge", (0.02, 0.05, 0.015), roughness=0.9)
    common.set_base_color_map(m, textures.load(textures.hedge()))
    return m


def grass():
    """Mown grass (lawn panels, grass steps, the tennis surround if grass). Tile 3 m."""
    m = common.pbr_material("M_Grounds_Lawn", (0.05, 0.11, 0.02), roughness=0.95)
    common.set_base_color_map(m, textures.load(textures.grass()))
    return m


def gravel():
    """Pale raked gravel: paths, the motor court, pétanque. Tile 2 m."""
    m = common.pbr_material("M_Out_Gravel", (0.5, 0.47, 0.42), roughness=0.95)
    common.set_base_color_map(m, textures.load(textures.gravel()))
    return m


# --- special -----------------------------------------------------------------

def water():
    """Every water surface (pools, fountains, ponds, rills): a flat, upward-facing plane
    just below the coping. The engine shades it (sky reflection, depth colour)."""
    return common.pbr_material("M_Water", (0.02, 0.09, 0.10), roughness=0.05)


def glass():
    """Greenhouse / pavilion glazing: faint tint, see-through."""
    m = common.pbr_material("M_Out_Glass", (0.03, 0.04, 0.04), roughness=0.05)
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Alpha"].default_value = 0.2
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "BLENDED"
    return m


# --- common flat colours (shared names so zones look like one estate) ---------

def dark_metal():
    return flat("M_Out_Metal_Dark", (0.025, 0.025, 0.027))


def bronze():
    return flat("M_Out_Bronze", (0.20, 0.12, 0.06))


def render_white():
    """Smooth white render / painted masonry (pool house walls, garden walls)."""
    return flat("M_Out_Render_White", (0.70, 0.69, 0.66))


def concrete():
    return flat("M_Out_Concrete", (0.36, 0.35, 0.33))


def bark():
    return flat("M_Out_Bark", (0.07, 0.055, 0.04))


def cushion(name="Sand", color=(0.55, 0.50, 0.42)):
    """Outdoor upholstery; name the colour: cushion('Charcoal', (0.05, 0.05, 0.055))."""
    return flat(f"M_Out_Cushion_{name}", color)


def soil():
    return flat("M_Out_Soil", (0.05, 0.035, 0.025))


def sedum():
    """Green roof: a low sedum mat (olive green with rust and straw), the low roofs of the house."""
    return flat("M_Out_Sedum", (0.11, 0.13, 0.06))


def lamp(name="Warm"):
    """Glowing part of a landscape light (bollard lens, lantern)."""
    return flat(f"M_Out_Lamp_{name}", (0.9, 0.8, 0.6), emission=(1.0, 0.8, 0.55), strength=6.0)
