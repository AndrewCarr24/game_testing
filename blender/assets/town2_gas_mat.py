"""Materials for the gas station (town2_gas.py): Principled BSDF + image textures only (what glTF
carries). Lit materials get a lightmap per zone (make.py); `reflect` is the strength of the
zone's reflection panorama on them (envMap in the extras; 0 = none). The palette material
("paint") holds every flat colour: a brush on a palette name samples that swatch.
"""
import importlib
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common  # noqa: E402
import town2_gas_tex as TX  # noqa: E402

importlib.reload(TX)


def _img(path, name, non_color=False):
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)
    img = bpy.data.images.load(path)
    img.name = name
    img.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
    return img


def _bsdf(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def textured(name, path, rough=0.6, reflect=0.0, tile=1.0, rough_map=None):
    m = common.pbr_material(f"M_Town2Gas_{name}", (1, 1, 1), roughness=rough)
    common.set_base_color_map(m, _img(path, os.path.splitext(os.path.basename(path))[0]))
    if rough_map:
        nt = m.node_tree
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = _img(rough_map, os.path.splitext(os.path.basename(rough_map))[0], non_color=True)
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(tex.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], _bsdf(m).inputs["Roughness"])
    return dict(mat=m, tile=tile, reflect=reflect)


def emissive(name, path, strength=1.0):
    m = common.pbr_material(f"M_Town2Gas_{name}", (0, 0, 0), roughness=0.4)
    b = _bsdf(m)
    tex = m.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = _img(path, os.path.splitext(os.path.basename(path))[0])
    m.node_tree.links.new(tex.outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = strength
    b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    return dict(mat=m, tile=1.0, unlit=True, reflect=0.0)


def glass(name, tint, alpha, reflect=1.0):
    m = common.pbr_material(f"M_Town2Gas_{name}", tint, roughness=0.04)
    b = _bsdf(m)
    b.inputs["Alpha"].default_value = alpha
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "BLENDED"
    else:
        m.blend_method = "BLEND"
    return dict(mat=m, tile=1.0, unlit=True, reflect=reflect, glass=True)


def materials(feeds=None):
    """Returns (mats, tex): mats name -> dict(mat, tile, unlit, reflect); tex = the atlases' cells
    and the palette's swatches."""
    T = TX.build_all(feeds)
    P = T["paths"]
    mats = {
        "concrete": textured("Concrete", P["concrete"], 0.85, 0.05, tile=3.0),
        "asphalt": textured("Asphalt", P["asphalt"], 0.9, 0.0, tile=2.1),
        "stone": textured("Stone", P["stone"], 0.85, 0.0, tile=1.5),
        "siding": textured("Siding", P["siding"], 0.6, 0.05, tile=1.2),
        "oak": textured("Oak", P["oak"], 0.45, 0.25, tile=0.5),
        "floor": textured("Floor", P["floor"], 0.22, 0.55, tile=1.2),
        "ceiling": textured("Ceiling", P["ceiling"], 0.95, 0.0, tile=0.61),
        "paint": textured("Paint", P["paint"], 0.45, 0.35, tile=1.0, rough_map=P["paint_rough"]),
        "goods": textured("Goods", P["goods"], 0.5, 0.12),
        "drinks": emissive("Drinks", P["drinks"], 1.25),
        "signs": emissive("Signs", P["signs"], 1.8),
        "glass": glass("Glass", (0.80, 0.86, 0.86), 0.14, reflect=1.0),
        "glass_dark": glass("GlassDark", (0.05, 0.06, 0.07), 0.55, reflect=0.8),
    }
    return mats, T
