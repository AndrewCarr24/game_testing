"""Shared palette for the rooms below ground (the secret passage: design/house/secret_passage.md):
the armory (`armory_*` assets), the shaft, the tunnels and the pump room (`tunnel_*`, `pump_*`),
their doors. One function per material, created once by name, so every asset down there shares
the same few materials (the engine merges each room's static props per material: fewer
materials = fewer draw calls) and no new textures are downloaded.

The armory is the library's cold twin: the same 1.18 m bay rhythm, brushed steel, graphite powder
coat, charcoal felt and cold white LED instead of oak, books and warm lamps. The tunnels are raw
concrete, galvanised steel and grey conduit under caged bulkhead lights.

Textures: none new. `concrete()` reuses the garage's polished-concrete map (T_Garage_Concrete,
6 m tile); fabrics reuse the shared weave normal (materials.fabric).
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(materials)


def _emit(name, color, strength, base=None):
    m = common.pbr_material(name, base or tuple(c * 0.2 for c in color), roughness=0.35)
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Emission Color"].default_value = (*color, 1)
    bsdf.inputs["Emission Strength"].default_value = strength
    return m


# ---- the armory --------------------------------------------------------------------------------
def graphite():
    """Graphite powder-coated steel: safe bodies, cabinets, frames."""
    return common.pbr_material("M_Armory_Graphite", (0.040, 0.043, 0.047), roughness=0.48, metallic=0.55)


def stainless():
    """Brushed (satin) stainless: the safe wall's doors, the layout table, trims."""
    return common.pbr_material("M_Armory_Stainless", (0.58, 0.585, 0.59), roughness=0.26, metallic=1.0)


def felt():
    """Charcoal felt: the lining of the gun bays, the foam of a rifle case."""
    return materials.fabric("M_Armory_Felt", (0.045, 0.048, 0.054), roughness=0.95)


def led(strength=6.0):
    """Cold white LED (6000 K): edge lights inside the bays, status lines, linear fixtures."""
    return _emit("M_Armory_LED", (0.80, 0.90, 1.0), strength)


def backlight():
    """A backlit opal diffuser: the gun bays' backs (the guns stand in silhouette against it)."""
    return _emit("M_Armory_Backlight", (0.62, 0.70, 0.80), 0.9, base=(0.30, 0.32, 0.34))


def white():
    """White enamel / polymer: battery units, the medical cabinet, the filter unit."""
    return common.pbr_material("M_Armory_White", (0.74, 0.75, 0.76), roughness=0.38)


def polymer():
    """Matte black polymer / rubber: weapon furniture, grips, mats, cable."""
    return common.pbr_material("M_Armory_Polymer", (0.018, 0.018, 0.019), roughness=0.72)


def tan():
    """Flat dark earth polymer: a stock, a case, webbing."""
    return common.pbr_material("M_Armory_Tan", (0.30, 0.245, 0.17), roughness=0.62)


def gunmetal():
    """Blued / Cerakote gunmetal: barrels, receivers, slides, tools."""
    return common.pbr_material("M_Armory_Gunmetal", (0.055, 0.057, 0.062), roughness=0.32, metallic=1.0)


def red():
    """Signal red: the medical cross, the transfer switch's handle, a valve."""
    return common.pbr_material("M_Armory_Red", (0.42, 0.025, 0.02), roughness=0.4)


def kraft():
    """Kraft board: ration cases."""
    return common.pbr_material("M_Armory_Kraft", (0.34, 0.245, 0.15), roughness=0.9)


def drum_blue():
    """Blue HDPE: water drums."""
    return common.pbr_material("M_Armory_DrumBlue", (0.035, 0.12, 0.34), roughness=0.45)


def olive():
    """Olive drab: ammo cans, a plate carrier, a gas mask's bag."""
    return common.pbr_material("M_Armory_Olive", (0.10, 0.11, 0.06), roughness=0.6, metallic=0.2)


def ballistic_glass():
    """Ballistic glass: thick, faintly green at the edges."""
    return materials.glass("M_Glass_Ballistic", tint=(0.03, 0.045, 0.042), alpha=0.22, roughness=0.02)


def screen():
    """A monitor that is on but shows only a dim blue-grey field (no texture, no text)."""
    return _emit("M_Armory_Screen", (0.30, 0.42, 0.52), 1.6, base=(0.01, 0.012, 0.015))


# ---- the tunnels, the shaft and the pump room ----------------------------------------------------
def concrete(name="M_Bunker_Concrete", color=(0.30, 0.30, 0.295), roughness=0.8):
    """Raw concrete, the garage's concrete map tinted lighter (6 m tile). Walls, floors, plinths."""
    m = common.pbr_material(name, color, roughness=roughness)
    path = os.path.join(textures.TEX_DIR, "T_Garage_Concrete_BaseColor.png")
    if os.path.exists(path):
        common.set_base_color_map(m, textures.load(path))
    return m


def galvanised():
    """Hot-dip galvanised steel: cable trays, struts, grates, cages, pipe supports."""
    return common.pbr_material("M_Tunnel_Galvanised", (0.46, 0.47, 0.48), roughness=0.5, metallic=1.0)


def pvc():
    """Grey PVC: conduit, junction boxes."""
    return common.pbr_material("M_Tunnel_PVC", (0.30, 0.31, 0.32), roughness=0.55)


def safety_yellow():
    """Safety yellow paint: kick plates, a pipe band, the pump room's floor line."""
    return common.pbr_material("M_Tunnel_Yellow", (0.55, 0.40, 0.02), roughness=0.55)


def pump_blue():
    """Enamelled pump-body blue."""
    return common.pbr_material("M_Tunnel_PumpBlue", (0.03, 0.12, 0.22), roughness=0.35, metallic=0.3)


def lens(on=True):
    """A bulkhead light's opal lens: lit (warm-neutral 4000 K) or dead."""
    if on:
        return _emit("M_Tunnel_Lens", (1.0, 0.92, 0.80), 5.0)
    return common.pbr_material("M_Tunnel_LensDead", (0.20, 0.20, 0.19), roughness=0.3)


def wet():
    """Standing water on concrete: almost black, mirror-glossy (opaque: no alpha)."""
    return common.pbr_material("M_Tunnel_Wet", (0.025, 0.026, 0.027), roughness=0.05)


def rust():
    """Old rust-brown steel: a sump grate, a valve, a pipe's bottom."""
    return common.pbr_material("M_Tunnel_Rust", (0.16, 0.07, 0.03), roughness=0.75, metallic=0.4)
