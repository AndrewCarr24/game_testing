"""Executive office level.

Builds the room shell, builds every prop from its asset script, places the
props, and exports:
  assets/models/office_shell.gltf     static architecture
  assets/models/<asset>.gltf          one file per prop (origin at floor centre)
  assets/models/textures/*.webp       textures shared by all of the above
  assets/levels/office.json           placements, colliders and lights for the engine

Blender is Z-up with the room's window wall on +Y; the JSON is in glTF/three.js
coordinates (Y-up), converted with common.to_gltf.
"""
import importlib
import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
BLENDER_DIR = os.path.join(HERE, "..")
PROJECT = os.path.abspath(os.path.join(BLENDER_DIR, ".."))
sys.path.insert(0, BLENDER_DIR)
sys.path.insert(0, os.path.join(BLENDER_DIR, "assets"))
from lib import common, textures  # noqa: E402

importlib.reload(common)
importlib.reload(textures)

NAME = "Office"

P = dict(
    width=7.0,            # x, interior
    depth=6.0,            # y, interior
    height=3.4,           # floor to ceiling
    wall_t=0.2,
    door_x=2.4,           # centre of the door opening in the south (-Y) wall
    door_w=1.1,
    door_h=2.5,
    mullion_pitch=1.4,
    mullion=(0.05, 0.12),  # width, depth
    glass_t=0.012,
    # placeholder corridor behind the door, until the next room exists
    corridor=dict(width=1.5, length=3.3, height=2.8),
    # recessed ceiling light strips: centre (x, y), size (x, y), ceiling height, area-light watts
    light_strips=[
        dict(pos=(-1.3, -0.6), size=(4.0, 0.08), z=3.4, power=80.0),
        dict(pos=(0.6, 1.6), size=(4.0, 0.08), z=3.4, power=80.0),
        dict(pos=(2.4, -4.85), size=(0.08, 2.6), z=2.8, power=35.0),   # corridor
    ],
    # lighting, shared by the Blender bake and the engine
    sun_dir=(-0.35, -0.72, -0.6),   # direction the light travels (Blender coords): in through the window
    sun_strength=4.0,               # W/m² in Blender = DirectionalLight intensity in three.js
    sky=(0.55, 0.68, 0.85),
    sky_strength=1.0,
    lightmap_res=1024,
    exposure=0.8,                   # engine tone-mapping exposure for the baked look
)

# (asset module, Blender location, rotation about Z in degrees[, options])
# Every asset faces -Y at rotation 0. Options:
#   lock:   item id needed to use the asset's interactable (e.g. a locked door)
#   attach: (asset, node) - parent to that node of the asset's first placement;
#           location/rotation are then local to the node (e.g. inside a drawer)
PLACEMENTS = [
    ("desk", (0.3, 1.5, 0.0), 0),
    ("desk_chair", (0.3, 2.5, 0.0), 0),   # clear of the drawer when it's open
    ("rug", (-1.6, -1.0, 0.0), 0),
    ("coffee_table", (-1.6, -1.0, 0.0), 90),
    ("lounge_chair", (-2.55, -1.0, 0.0), 90),
    ("lounge_chair", (-0.65, -1.0, 0.0), -90),
    ("door", (2.4, -3.1, 0.0), 0, {"lock": "keycard"}),
    # in the drawer: drawer-local, its floor is 1.85 cm below the drawer's origin
    ("keycard", (0.09, -0.16, -0.0185), 18, {"attach": ("desk", "Desk_Drawer")}),
]


def shell(p):
    col = common.fresh_collection(f"{NAME}_Shell")
    root = common.empty(f"{NAME}_Shell", col)

    oak = common.pbr_material("M_OakFloor", (0.4, 0.27, 0.15), roughness=0.45, coat=0.1)
    common.set_base_color_map(oak, textures.load(textures.oak_floor()))
    plaster = common.pbr_material("M_Plaster_WarmWhite", (0.72, 0.70, 0.66), roughness=0.9)
    ceiling_m = common.pbr_material("M_Ceiling_White", (0.8, 0.8, 0.79), roughness=0.9)
    alu = common.pbr_material("M_Aluminium_Black", (0.02, 0.02, 0.022), roughness=0.35, metallic=0.7)
    glass = common.pbr_material("M_Glass", (0.9, 0.95, 0.95), roughness=0.02)
    bsdf = next(nd for nd in glass.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Alpha"].default_value = 0.12
    if hasattr(glass, "surface_render_method"):
        glass.surface_render_method = "BLENDED"
    else:
        glass.blend_method = "BLEND"
    glow = common.pbr_material("M_LightStrip", (1, 1, 1), roughness=0.5)
    gb = next(nd for nd in glow.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    gb.inputs["Emission Color"].default_value = (1.0, 0.92, 0.82, 1)
    gb.inputs["Emission Strength"].default_value = 4.0

    W, D, H, T = p["width"], p["depth"], p["height"], p["wall_t"]
    hw, hd = W / 2, D / 2
    colliders, solids, baked = [], [], []

    def box(name, lo, hi, mat, collide=True, uv_tile=1.0, bake=False):
        size = [hi[i] - lo[i] for i in range(3)]
        ob = common.mesh_object(f"{NAME}_{name}", common.box_bmesh(size), col, mat, root, smooth=False)
        ob.location = [(lo[i] + hi[i]) / 2 for i in range(3)]
        common.box_uv(ob, tile=uv_tile)
        solids.append((lo, hi))
        if collide:
            colliders.append(common.aabb_gltf(lo, hi))
        if bake:
            baked.append(ob)
        return ob

    box("Floor", (-hw - T, -hd - T, -0.1), (hw + T, hd + T, 0.0), oak, uv_tile=2.0, bake=True)
    box("Ceiling", (-hw - T, -hd - T, H), (hw + T, hd + T, H + 0.1), ceiling_m, bake=True)
    box("Wall_W", (-hw - T, -hd - T, 0), (-hw, hd + T, H), plaster, bake=True)
    box("Wall_E", (hw, -hd - T, 0), (hw + T, hd + T, H), plaster, bake=True)
    dx0, dx1 = p["door_x"] - p["door_w"] / 2, p["door_x"] + p["door_w"] / 2
    c = p["corridor"]
    cx0, cx1 = p["door_x"] - c["width"] / 2, p["door_x"] + c["width"] / 2
    # south wall, split where the corridor walls meet it so each face is either
    # in the office or in the corridor (keeps the lightmap atlas tight)
    box("Wall_S_A", (-hw, -hd - T, 0), (cx0, -hd, H), plaster, bake=True)
    box("Wall_S_A2", (cx0, -hd - T, 0), (dx0, -hd, H), plaster, bake=True)
    box("Wall_S_B2", (dx1, -hd - T, 0), (cx1, -hd, H), plaster, bake=True)
    box("Wall_S_B", (cx1, -hd - T, 0), (hw, -hd, H), plaster, bake=True)
    box("Wall_S_Header", (dx0, -hd - T, p["door_h"]), (dx1, -hd, H), plaster, bake=True)

    # corridor stub behind the door
    Hc, y1 = c["height"], -hd - T
    y0c = y1 - c["length"]
    box("Corridor_Floor", (cx0 - T, y0c - T, -0.1), (cx1 + T, y1, 0.0), oak, uv_tile=2.0, bake=True)
    box("Corridor_Ceiling", (cx0 - T, y0c - T, Hc), (cx1 + T, y1, Hc + 0.1), ceiling_m, bake=True)
    box("Corridor_Wall_W", (cx0 - T, y0c - T, 0), (cx0, y1, Hc), plaster, bake=True)
    box("Corridor_Wall_E", (cx1, y0c - T, 0), (cx1 + T, y1, Hc), plaster, bake=True)
    box("Corridor_Wall_End", (cx0, y0c - T, 0), (cx1, y0c, Hc), plaster, bake=True)

    # window wall: head and sill channels, mullions, one glass pane
    mw, md = p["mullion"]
    y0 = hd
    box("Window_Sill", (-hw, y0, 0), (hw, y0 + md, 0.05), alu, collide=False)
    box("Window_Head", (-hw, y0, H - 0.05), (hw, y0 + md, H), alu, collide=False)
    count = int(round(W / p["mullion_pitch"]))
    for i in range(count + 1):
        x = -hw + i * W / count
        x0, x1 = max(-hw, x - mw / 2), min(hw, x + mw / 2)
        box(f"Mullion_{i}", (x0, y0, 0.05), (x1, y0 + md, H - 0.05), alu, collide=False)
    gy = y0 + md / 2
    box("Glass", (-hw, gy - p["glass_t"] / 2, 0.05), (hw, gy + p["glass_t"] / 2, H - 0.05),
        glass, collide=False)
    colliders.append(common.aabb_gltf((-hw, y0, 0), (hw, y0 + md, H)))

    # ceiling light coves (emissive strips; real lights are listed in the JSON)
    lights = []
    for i, ls in enumerate(p["light_strips"]):
        (x, y), (sw, sd), z = ls["pos"], ls["size"], ls["z"]
        box(f"LightStrip_{i}", (x - sw / 2, y - sd / 2, z - 0.006), (x + sw / 2, y + sd / 2, z - 0.001),
            glow, collide=False)
        lights.append({"type": "rect", "position": common.to_gltf((x, y, z - 0.01)),
                       "width": max(sw, 0.25), "height": max(sd, 0.25), "intensity": 6.0,
                       "color": [1.0, 0.92, 0.82], "lookAt": common.to_gltf((x, y, 0))})

    # lightmap atlas over every surface visible from the office, doorway or corridor
    air = [((-hw, -hd - T - 0.01, 0.0), (hw, hd, H)), ((cx0, y0c, 0.0), (cx1, y1 + 0.01, Hc))]
    texels = common.lightmap_uv(baked, solids, air, resolution=p["lightmap_res"])
    print(f"lightmap: {len(baked)} objects at {texels} texels/m")

    sun = Vector(p["sun_dir"]).normalized()
    lights.append({"type": "sun", "direction": common.to_gltf(sun), "intensity": p["sun_strength"],
                   "color": [1.0, 0.96, 0.9]})
    lights.append({"type": "ambient_env", "intensity": 0.6})
    # stand-in for bounced light until lightmaps are baked: warm floor bounce lights the ceiling
    lights.append({"type": "hemisphere", "sky": [0.85, 0.9, 1.0], "ground": [0.95, 0.8, 0.62],
                   "intensity": 1.1})
    return root, colliders, lights


def blender_lights(p):
    """Blender lights + sky. These drive the Cycles bake (blender/levels/bake.py);
    they are not exported. The engine gets the sun from the level JSON."""
    col = common.fresh_collection(f"{NAME}_PreviewLights")
    for i, ls in enumerate(p["light_strips"]):
        ld = bpy.data.lights.get(f"{NAME}_Cove_{i}") or bpy.data.lights.new(f"{NAME}_Cove_{i}", "AREA")
        ld.shape = "RECTANGLE"
        ld.size, ld.size_y = max(ls["size"][0], 0.25), max(ls["size"][1], 0.25)
        ld.energy = ls["power"]
        ld.color = (1.0, 0.92, 0.82)
        ob = bpy.data.objects.new(f"{NAME}_Cove_{i}", ld)
        ob.location = (*ls["pos"], ls["z"] - 0.02)
        col.objects.link(ob)
    sd = bpy.data.lights.get(f"{NAME}_Sun") or bpy.data.lights.new(f"{NAME}_Sun", "SUN")
    sd.energy = p["sun_strength"]
    sd.color = (1.0, 0.96, 0.9)
    sd.angle = math.radians(1.5)
    sun = bpy.data.objects.new(f"{NAME}_Sun", sd)
    sun.rotation_euler = Vector(p["sun_dir"]).to_track_quat("-Z", "Y").to_euler()
    col.objects.link(sun)

    scene = bpy.context.scene
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    try:
        world.use_nodes = True
    except AttributeError:
        pass
    bg = next(nd for nd in world.node_tree.nodes if nd.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (*p["sky"], 1)
    bg.inputs["Strength"].default_value = p["sky_strength"]


def build(export=True):
    p = P
    models = os.path.join(PROJECT, "assets", "models")
    levels = os.path.join(PROJECT, "assets", "levels")
    os.makedirs(models, exist_ok=True)
    os.makedirs(levels, exist_ok=True)

    props_col = common.fresh_collection(f"{NAME}_Props")  # linked copies; clear before rebuilding assets
    shell_root, colliders, lights = shell(p)
    blender_lights(p)

    assets, roots, placed = {}, {}, []
    for asset, loc, rot, *rest in PLACEMENTS:
        opts = rest[0] if rest else {}
        if asset not in roots:
            mod = importlib.import_module(asset)
            importlib.reload(mod)
            root, parts = mod.build()
            roots[asset] = root
            lo, hi = common.world_aabb(parts)
            assets[asset] = {"file": f"models/{asset}.gltf", "aabb": common.aabb_gltf(lo, hi),
                             "colliders": common.part_colliders(parts),
                             "tris": common.triangle_count(parts)}
            if export:
                common.export_gltf(root, os.path.join(models, f"{asset}.gltf"))
            ob = root
        else:
            ob = common.duplicate_hierarchy(roots[asset], props_col, f".{len(placed):02d}")
        entry = {"asset": asset, "position": common.to_gltf(loc), "rotationY": rot}
        if "attach" in opts:
            host, node = opts["attach"]
            ob.parent = bpy.data.objects[node]       # the host asset's first placement
            entry["attach"] = {"asset": host, "node": node}
        if "lock" in opts:
            entry["lock"] = opts["lock"]
        ob.location = loc
        ob.rotation_euler = (0, 0, math.radians(rot))
        placed.append(entry)

    if export:
        common.export_gltf(shell_root, os.path.join(models, "office_shell.gltf"))
    level = {
        "name": NAME,
        "units": "metres, Y-up (glTF)",
        "shell": "models/office_shell.gltf",
        "assets": assets,
        "props": placed,
        "colliders": colliders,
        "lights": lights,
        "spawn": {"position": common.to_gltf((2.4, -2.2, 1.65)), "lookAt": common.to_gltf((-0.5, 2.0, 1.2))},
    }
    with open(os.path.join(levels, "office.json"), "w") as f:
        json.dump(level, f, indent=2)
    shell_parts = [o for o in shell_root.children_recursive if o.type == "MESH"]
    total = common.triangle_count(shell_parts) + sum(
        assets[e[0]]["tris"] for e in PLACEMENTS)
    print(f"{NAME}: {len(placed)} props, {len(colliders)} colliders, {total} tris total")
    return level


if __name__ == "__main__":
    build()
