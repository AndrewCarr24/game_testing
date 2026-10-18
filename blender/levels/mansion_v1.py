"""The mansion level: rooms (office, hall, bedroom) built into one walkable scene.

Builds every room's shell, builds each prop from its asset script, places the
props, and exports:
  assets/models/mansion_shell.gltf    static architecture for all rooms
  assets/models/<asset>.gltf          one file per prop (origin at floor centre)
  assets/models/textures/*.webp       textures shared by all of the above
  assets/levels/mansion.json          placements, colliders, lights, rooms for the engine

Each room has its own lightmap atlas and environment probe (see bake.py), so a
room's lighting can have its own mood and adding rooms doesn't dilute the others.

Blender is Z-up; the office's window wall is on +Y and the hall runs south (-Y)
from the office door to the bedroom. The JSON is in glTF/three.js coordinates
(Y-up), converted with common.to_gltf.
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
from lib import common, materials, textures  # noqa: E402

importlib.reload(common)
importlib.reload(textures)
importlib.reload(materials)

NAME = "Mansion"

P = dict(
    wall_t=0.2,
    door_w=1.1,
    door_h=2.5,
    # lighting, shared by the Blender bake and the engine
    sun_dir=(-0.35, -0.72, -0.6),   # direction the light travels (Blender coords): in through the office window
    sun_strength=4.0,               # W/m² in Blender = DirectionalLight intensity in three.js
    sky=(0.55, 0.68, 0.85),
    sky_strength=1.0,
    lightmap_res=1024,              # per room
    exposure=0.8,                   # engine tone-mapping exposure for the baked look
)

OFFICE = dict(x=(-3.5, 3.5), y=(-3.0, 3.0), h=3.4, door_x=2.4,
              mullion_pitch=1.4, mullion=(0.05, 0.12), glass_t=0.012)
HALL = dict(x=(1.2, 3.6), y=(-13.2, -3.2), h=3.0, door_x=2.4)
BEDROOM = dict(x=(-2.0, 4.0), y=(-18.9, -13.4), h=3.2, door_x=2.4,
               window_y=(-17.6, -14.6))   # floor-to-ceiling window in the west wall

# (asset module, Blender location, rotation about Z in degrees[, options])
# Every asset faces -Y at rotation 0. Options:
#   lock:   item id needed to use the asset's interactable (e.g. a locked door)
#   attach: (asset, node) - parent to that node of the asset's first placement;
#           location/rotation are then local to the node (e.g. inside a drawer)
PLACEMENTS = {
    "office": [
        ("desk", (0.3, 1.5, 0.0), 0),
        ("desk_chair", (0.3, 2.5, 0.0), 0),   # clear of the drawer when it's open
        ("rug", (-1.6, -1.0, 0.0), 0),
        ("coffee_table", (-1.6, -1.0, 0.0), 90),
        ("lounge_chair", (-2.55, -1.0, 0.0), 90),
        ("lounge_chair", (-0.65, -1.0, 0.0), -90),
        ("vase", (-1.62, -0.78, 0.38), 0),    # on the coffee table (top at 0.38 m)
        ("door", (2.4, -3.1, 0.0), 0, {"lock": "keycard"}),
        # in the drawer: drawer-local, its floor is 1.85 cm below the drawer's origin
        ("keycard", (0.09, -0.16, -0.0185), 18, {"attach": ("desk", "Desk_Drawer")}),
    ],
    "hall": [
        # pictures hang on the wall planes (x = 1.2 west, 3.6 east), centres at 1.55 m
        ("art_colorfield_a", (1.2, -5.4, 1.55), 90),
        ("art_geometric_a", (1.2, -8.9, 1.55), 90),
        ("art_linework_a", (1.2, -11.6, 1.55), 90),
        ("art_colorfield_b", (3.6, -6.9, 1.55), -90),
        ("art_geometric_b", (3.6, -10.3, 1.55), -90),
        ("door_plain", (2.4, -13.3, 0.0), 180),   # swings into the bedroom
    ],
    "bedroom": [
        ("bedroom_rug", (1.0, -17.0, 0.0), 0),
        ("bed", (1.0, -17.78, 0.0), 180),        # headboard against the south wall
        ("nightstand", (-0.41, -18.66, 0.0), 180),   # clear of the duvet overhang
        ("nightstand", (2.41, -18.66, 0.0), 180),
        ("table_lamp", (-0.41, -18.66, 0.55), 0),
        ("table_lamp", (2.41, -18.66, 0.55), 0),
        ("bench", (1.0, -16.35, 0.0), 180),
        ("wardrobe", (3.69, -15.2, 0.0), -90),   # against the east wall, doors face west
        ("bedroom_chair", (-1.25, -14.35, 0.0), 135),   # reading corner by the window
    ],
}


class Shell:
    """Collects a level's architecture: boxes (with colliders), which room each
    baked surface belongs to, the solid/air volumes for lightmap packing, and lights."""

    def __init__(self, p):
        self.p = p
        self.col = common.fresh_collection(f"{NAME}_Shell")
        self.root = common.empty(f"{NAME}_Shell", self.col)
        self.colliders, self.solids = [], []
        self.baked = {}          # room -> [objects]
        self.air = {}            # room -> [(lo, hi)]
        self.strips = []         # ceiling light strips (emissive + area light)
        self.points = []         # extra Blender lights for the bake (lamps)
        self.probes = {}         # room -> Blender point for its environment panorama
        self.lights = []         # engine fallback lights (used when there's no bake)
        self.glow = materials.emissive("M_LightStrip", (1.0, 0.92, 0.82), 4.0)

    def box(self, room, name, lo, hi, mat, collide=True, uv_tile=1.0, bake=False):
        size = [hi[i] - lo[i] for i in range(3)]
        ob = common.mesh_object(f"{NAME}_{name}", common.box_bmesh(size), self.col, mat, self.root, smooth=False)
        ob.location = [(lo[i] + hi[i]) / 2 for i in range(3)]
        ob["room"] = room
        common.box_uv(ob, tile=uv_tile)
        self.solids.append((lo, hi))
        if collide:
            self.colliders.append(common.aabb_gltf(lo, hi))
        if bake:
            self.baked.setdefault(room, []).append(ob)
        return ob

    def wall_with_door(self, room, name, axis, at, span, door_c, z_top, mat):
        """A wall of thickness wall_t along `axis` ('x' or 'y') whose inner faces
        are at `at`..`at`+T, from span[0] to span[1], with a door opening centred on
        door_c (None: a plain wall)."""
        T, w, dh = self.p["wall_t"], self.p["door_w"], self.p["door_h"]

        def seg(n, a0, a1, z0, z1):
            if a1 - a0 < 1e-3:
                return
            if axis == "x":
                self.box(room, n, (a0, at, z0), (a1, at + T, z1), mat, bake=True)
            else:
                self.box(room, n, (at, a0, z0), (at + T, a1, z1), mat, bake=True)
        if door_c is None:
            seg(name, span[0], span[1], 0, z_top)
            return
        d0, d1 = door_c - w / 2, door_c + w / 2
        seg(f"{name}_A", span[0], d0, 0, z_top)
        seg(f"{name}_B", d1, span[1], 0, z_top)
        seg(f"{name}_Header", d0, d1, dh, z_top)

    def strip(self, room, pos, size, z, power):
        (x, y), (sw, sd) = pos, size
        self.box(room, f"LightStrip_{len(self.strips)}", (x - sw / 2, y - sd / 2, z - 0.006),
                 (x + sw / 2, y + sd / 2, z - 0.001), self.glow, collide=False)
        self.strips.append(dict(pos=pos, size=size, z=z, power=power))
        self.lights.append({"type": "rect", "position": common.to_gltf((x, y, z - 0.01)),
                            "width": max(sw, 0.25), "height": max(sd, 0.25), "intensity": 6.0,
                            "color": [1.0, 0.92, 0.82], "lookAt": common.to_gltf((x, y, 0))})

    def glazing(self, room, axis, at, span, z, mat_frame, mat_glass, pitch=1.4, mullion=(0.05, 0.12)):
        """Floor-to-ceiling glass in a wall plane: sill, head, mullions, one pane, one collider."""
        mw, md = mullion
        a0, a1 = span
        z0, z1 = z

        def b(n, lo_a, hi_a, lo_d, hi_d, lo_z, hi_z, m):
            if axis == "x":   # wall runs along x, depth along y
                self.box(room, n, (lo_a, lo_d, lo_z), (hi_a, hi_d, hi_z), m, collide=False)
            else:
                self.box(room, n, (lo_d, lo_a, lo_z), (hi_d, hi_a, hi_z), m, collide=False)
        b(f"{room}_Window_Sill", a0, a1, at, at + md, z0, z0 + 0.05, mat_frame)
        b(f"{room}_Window_Head", a0, a1, at, at + md, z1 - 0.05, z1, mat_frame)
        count = max(1, int(round((a1 - a0) / pitch)))
        for i in range(count + 1):
            c = a0 + i * (a1 - a0) / count
            b(f"{room}_Mullion_{i}", max(a0, c - mw / 2), min(a1, c + mw / 2), at, at + md, z0 + 0.05, z1 - 0.05, mat_frame)
        g = at + md / 2
        b(f"{room}_Glass", a0, a1, g - 0.006, g + 0.006, z0 + 0.05, z1 - 0.05, mat_glass)
        lo, hi = ((a0, at, z0), (a1, at + md, z1)) if axis == "x" else ((at, a0, z0), (at + md, a1, z1))
        self.colliders.append(common.aabb_gltf(lo, hi))
        self.solids.append((lo, hi))


def shell_materials():
    m = dict(
        oak=common.pbr_material("M_OakFloor", (0.4, 0.27, 0.15), roughness=0.45, coat=0.1),
        plaster=common.pbr_material("M_Plaster_WarmWhite", (0.72, 0.70, 0.66), roughness=0.9),
        ceiling=common.pbr_material("M_Ceiling_White", (0.8, 0.8, 0.79), roughness=0.9),
        frame=materials.black_metal(),
        glass=materials.glass("M_Glass", tint=(0.9, 0.95, 0.95), alpha=0.12, roughness=0.02),
        # bedroom: darker, warmer
        oak_dark=common.pbr_material("M_OakFloor_Smoked", (0.08, 0.055, 0.035), roughness=0.75, coat=0.0),   # matte oiled finish
        plaster_stone=common.pbr_material("M_Plaster_Stone", (0.36, 0.335, 0.30), roughness=0.92),
        plaster_ink=common.pbr_material("M_Plaster_Ink", (0.035, 0.045, 0.062), roughness=0.92),
        ceiling_warm=common.pbr_material("M_Ceiling_Warm", (0.48, 0.46, 0.43), roughness=0.9),
    )
    common.set_base_color_map(m["oak"], textures.load(textures.oak_floor()))
    common.set_base_color_map(m["oak_dark"], textures.load(textures.wood(
        "T_OakFloorSmoked_BaseColor", dark=(0.030, 0.020, 0.013), light=(0.095, 0.066, 0.043), rings=30, seed=31)))
    return m


def office(s, m):
    o, T = OFFICE, s.p["wall_t"]
    (x0, x1), (y0, y1), H = o["x"], o["y"], o["h"]
    s.box("office", "Office_Floor", (x0 - T, y0 - T, -0.1), (x1 + T, y1 + T, 0.0), m["oak"], uv_tile=2.0, bake=True)
    s.box("office", "Office_Ceiling", (x0 - T, y0 - T, H), (x1 + T, y1 + T, H + 0.1), m["ceiling"], bake=True)
    s.box("office", "Office_Wall_W", (x0 - T, y0 - T, 0), (x0, y1 + T, H), m["plaster"], bake=True)
    s.box("office", "Office_Wall_E", (x1, y0 - T, 0), (x1 + T, y1 + T, H), m["plaster"], bake=True)
    # south wall with the door to the hall; split where the hall's walls meet it so
    # each face sits in one room (keeps the lightmap atlases tight)
    hx0, hx1 = HALL["x"]
    s.wall_with_door("office", "Office_Wall_S_West", "x", y0 - T, (x0, hx0), None, H, m["plaster"])
    s.wall_with_door("office", "Office_Wall_S", "x", y0 - T, (hx0, min(hx1, x1)), o["door_x"], H, m["plaster"])
    s.glazing("office", "x", y1, (x0, x1), (0, H), m["frame"], m["glass"], o["mullion_pitch"], o["mullion"])
    s.strip("office", (-1.3, -0.6), (4.0, 0.08), H, 80.0)
    s.strip("office", (0.6, 1.6), (4.0, 0.08), H, 80.0)
    s.air["office"] = [((x0, y0 - T - 0.01, 0.0), (x1, y1, H))]
    s.probes["office"] = (0.0, 0.0, 1.3)


def hall(s, m):
    h, T = HALL, s.p["wall_t"]
    (x0, x1), (y0, y1), H = h["x"], h["y"], h["h"]
    y1 -= T   # the office's south wall occupies the first wall thickness
    s.box("hall", "Hall_Floor", (x0 - T, y0, -0.1), (x1 + T, y1, 0.0), m["oak"], uv_tile=2.0, bake=True)
    s.box("hall", "Hall_Ceiling", (x0 - T, y0, H), (x1 + T, y1, H + 0.1), m["ceiling"], bake=True)
    s.box("hall", "Hall_Wall_W", (x0 - T, y0, 0), (x0, y1, H), m["plaster"], bake=True)
    s.box("hall", "Hall_Wall_E", (x1, y0, 0), (x1 + T, y1, H), m["plaster"], bake=True)
    s.strip("hall", ((x0 + x1) / 2, (y0 + y1) / 2), (0.08, (y1 - y0) - 1.6), H, 70.0)
    s.air["hall"] = [((x0, y0 - T - 0.01, 0.0), (x1, y1 + 0.01, H))]
    s.probes["hall"] = ((x0 + x1) / 2, (y0 + y1) / 2, 1.5)


def bedroom(s, m):
    b, T = BEDROOM, s.p["wall_t"]
    (x0, x1), (y0, y1), H = b["x"], b["y"], b["h"]
    s.box("bedroom", "Bedroom_Floor", (x0 - T, y0 - T, -0.1), (x1 + T, y1 + T, 0.0), m["oak_dark"], uv_tile=2.0, bake=True)
    s.box("bedroom", "Bedroom_Ceiling", (x0 - T, y0 - T, H), (x1 + T, y1 + T, H + 0.1), m["ceiling_warm"], bake=True)
    # north wall (shared with the hall's end): door at door_x
    s.wall_with_door("bedroom", "Bedroom_Wall_N", "x", y1, (x0 - T, x1 + T), b["door_x"], H, m["plaster_stone"])
    s.box("bedroom", "Bedroom_Wall_S", (x0 - T, y0 - T, 0), (x1 + T, y0, H), m["plaster_ink"], bake=True)   # behind the bed
    s.box("bedroom", "Bedroom_Wall_E", (x1, y0, 0), (x1 + T, y1, H), m["plaster_stone"], bake=True)
    # west wall: solid either side of a floor-to-ceiling window
    wy0, wy1 = b["window_y"]
    s.box("bedroom", "Bedroom_Wall_W_S", (x0 - T, y0, 0), (x0, wy0, H), m["plaster_stone"], bake=True)
    s.box("bedroom", "Bedroom_Wall_W_N", (x0 - T, wy1, 0), (x0, y1, H), m["plaster_stone"], bake=True)
    s.glazing("bedroom", "y", x0 - 0.12, (wy0, wy1), (0, H), m["frame"], m["glass"], pitch=1.5)
    s.strip("bedroom", (x1 - 0.4, (y0 + y1) / 2), (0.08, 4.4), H, 120.0)     # soft wash along the wardrobe wall
    for x in (-0.41, 2.41):                                                   # the bedside lamps' glow
        s.points.append(dict(pos=(x, -18.66, 0.55 + 0.42), power=65.0, color=(1.0, 0.72, 0.45), radius=0.12))
    s.air["bedroom"] = [((x0, y0, 0.0), (x1, y1 + T + 0.01, H))]
    s.probes["bedroom"] = (1.0, -15.6, 1.3)


def blender_lights(p, s):
    """Blender lights + sky. These drive the Cycles bake (blender/levels/bake.py);
    they are not exported. The engine gets the sun from the level JSON."""
    col = common.fresh_collection(f"{NAME}_PreviewLights")
    for i, ls in enumerate(s.strips):
        ld = bpy.data.lights.get(f"{NAME}_Cove_{i}") or bpy.data.lights.new(f"{NAME}_Cove_{i}", "AREA")
        ld.shape = "RECTANGLE"
        ld.size, ld.size_y = max(ls["size"][0], 0.25), max(ls["size"][1], 0.25)
        ld.energy = ls["power"]
        ld.color = (1.0, 0.92, 0.82)
        ob = bpy.data.objects.new(f"{NAME}_Cove_{i}", ld)
        ob.location = (*ls["pos"], ls["z"] - 0.02)
        col.objects.link(ob)
    for i, pt in enumerate(s.points):
        ld = bpy.data.lights.get(f"{NAME}_Lamp_{i}") or bpy.data.lights.new(f"{NAME}_Lamp_{i}", "POINT")
        ld.energy, ld.color, ld.shadow_soft_size = pt["power"], pt["color"], pt["radius"]
        ob = bpy.data.objects.new(f"{NAME}_Lamp_{i}", ld)
        ob.location = pt["pos"]
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
    s = Shell(p)
    m = shell_materials()
    office(s, m)
    hall(s, m)
    bedroom(s, m)
    air_all = [box for boxes in s.air.values() for box in boxes]
    for room, objs in s.baked.items():
        texels = common.lightmap_uv(objs, s.solids, air_all, resolution=p["lightmap_res"])
        print(f"lightmap {room}: {len(objs)} objects at {texels} texels/m")
    blender_lights(p, s)

    sun = Vector(p["sun_dir"]).normalized()
    lights = s.lights + [
        {"type": "sun", "direction": common.to_gltf(sun), "intensity": p["sun_strength"], "color": [1.0, 0.96, 0.9]},
        {"type": "ambient_env", "intensity": 0.6},
        # stand-in for bounced light when there is no bake
        {"type": "hemisphere", "sky": [0.85, 0.9, 1.0], "ground": [0.95, 0.8, 0.62], "intensity": 1.1},
    ]

    assets, roots, placed = {}, {}, []
    for room, entries in PLACEMENTS.items():
        for asset, loc, rot, *rest in entries:
            opts = rest[0] if rest else {}
            if asset not in roots:
                try:
                    mod = importlib.import_module(asset)
                except ModuleNotFoundError:
                    print(f"SKIP {asset}: no blender/assets/{asset}.py yet")
                    roots[asset] = None
                    continue
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
            elif roots[asset] is None:
                continue
            else:
                ob = common.duplicate_hierarchy(roots[asset], props_col, f".{len(placed):02d}")
            entry = {"asset": asset, "room": room, "position": common.to_gltf(loc), "rotationY": rot}
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
        common.export_gltf(s.root, os.path.join(models, "mansion_shell.gltf"))
    level = {
        "name": NAME,
        "units": "metres, Y-up (glTF)",
        "shell": "models/mansion_shell.gltf",
        "rooms": {r: {"probe": common.to_gltf(pt)} for r, pt in s.probes.items()},
        "assets": assets,
        "props": placed,
        "colliders": s.colliders,
        "lights": lights,
        "spawn": {"position": common.to_gltf((2.4, -2.2, 1.65)), "lookAt": common.to_gltf((-0.5, 2.0, 1.2))},
    }
    with open(os.path.join(levels, "mansion.json"), "w") as f:
        json.dump(level, f, indent=2)
    shell_parts = [o for o in s.root.children_recursive if o.type == "MESH"]
    total = common.triangle_count(shell_parts) + sum(assets[e["asset"]]["tris"] for e in placed)
    print(f"{NAME}: {len(placed)} props, {len(s.colliders)} colliders, {total} tris total")
    return level


if __name__ == "__main__":
    build()
