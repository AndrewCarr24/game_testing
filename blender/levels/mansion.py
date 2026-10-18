"""The mansion level: the floor plan (plan.py) built into one walkable scene, each
room dressed by its module in blender/levels/rooms/.

Exports:
  assets/models/mansion_shell.gltf    architecture for every room
  assets/models/<asset>.gltf          one file per prop (origin at floor centre)
  assets/models/textures/*.webp       textures shared by all of the above
  assets/levels/mansion.json          rooms + probes, props, colliders, lights, spawn

Room modules (blender/levels/rooms/<module>.py) may define, all optional:
  FINISHES   dict(floor=fn, walls=fn, ceiling=fn, walls_by_side={"N": fn, ...},
             floor_uv_tile=2.0, wall_uv_tile=1.0); each fn returns a Blender material
             (lib/materials.py); uv_tile = metres per texture repeat
  PLACEMENTS [(asset, (x, y[, z]), rot_deg[, opts]), ...] in room-local metres:
             (0, 0) is the room's interior centre, z = 0 its floor; +y north, +x east.
             A module shared by several rooms uses {room: [...]} instead.
  LIGHTS     [dict(kind="strip", pos=(x, y), size=(w, d), power=W),
              dict(kind="point", pos=(x, y, z), power=W, color=(r, g, b))], room-local
  PROBE      (x, y, z) room-local point for the room's environment panorama

Each room has its own lightmap atlas and environment probe (bake.py), sized by area.
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
for d in (BLENDER_DIR, os.path.join(BLENDER_DIR, "assets"), HERE, os.path.join(HERE, "rooms")):
    if d not in sys.path:
        sys.path.insert(0, d)
from lib import common, house, materials, textures  # noqa: E402
import plan  # noqa: E402

for m in (common, textures, materials, house, plan):
    importlib.reload(m)

NAME = "Mansion"

P = dict(
    # lighting, shared by the Blender bake and the engine
    sun_dir=(-0.35, -0.72, -0.6),   # direction the light travels (Blender coords)
    sun_strength=4.0,               # W/m² in Blender = DirectionalLight intensity in three.js
    sky=(0.55, 0.68, 0.85),
    sky_strength=1.0,
    lightmap_res=1024,              # upper limit per room; small rooms get 512
    exposure=0.8,
)


def default_finishes():
    oak = common.pbr_material("M_OakFloor", (0.4, 0.27, 0.15), roughness=0.45, coat=0.1)
    common.set_base_color_map(oak, textures.load(textures.oak_floor()))
    return dict(
        floor=oak,
        walls=common.pbr_material("M_Plaster_WarmWhite", (0.72, 0.70, 0.66), roughness=0.9),
        ceiling=common.pbr_material("M_Ceiling_White", (0.8, 0.8, 0.79), roughness=0.9),
        floor_uv_tile=2.0,
    )


def courtyard_finishes():
    stone = common.pbr_material("M_Stone_Paving", (0.55, 0.52, 0.47), roughness=0.85)
    return dict(floor=stone, walls=stone, ceiling=stone, floor_uv_tile=2.0)


def room_module(room):
    name = plan.ROOMS[room].get("module", room)
    try:
        mod = importlib.import_module(name)
    except ModuleNotFoundError:
        return None
    importlib.reload(mod)
    return mod


def per_room(mod, attr, room, default):
    v = getattr(mod, attr, default) if mod else default
    if isinstance(v, dict):
        return v.get(room, default)
    return v


def finishes_for(room, mod, base):
    f = dict(base)
    spec = getattr(mod, "FINISHES", None) if mod else None
    if isinstance(spec, dict) and room in spec and isinstance(spec[room], dict):
        spec = spec[room]                     # shared module with per-room finishes
    for k, v in (spec or {}).items():
        if k in plan.ROOMS:
            continue
        if k == "walls_by_side":
            f[k] = {side: fn() for side, fn in v.items()}
        elif callable(v):
            f[k] = v()
        else:
            f[k] = v
    return f


def blender_lights(p, h):
    """Blender lights + sky. These drive the Cycles bake; the engine gets the sun from the JSON."""
    col = common.fresh_collection(f"{NAME}_PreviewLights")
    for i, ls in enumerate(h.strips):
        ld = bpy.data.lights.get(f"{NAME}_Cove_{i}") or bpy.data.lights.new(f"{NAME}_Cove_{i}", "AREA")
        ld.shape = "RECTANGLE"
        ld.size, ld.size_y = max(ls["size"][0], 0.25), max(ls["size"][1], 0.25)
        ld.energy = ls["power"]
        ld.color = (1.0, 0.92, 0.82)
        ob = bpy.data.objects.new(f"{NAME}_Cove_{i}", ld)
        ob.location = (*ls["pos"], ls["z"] - 0.02)
        col.objects.link(ob)
    for i, pt in enumerate(h.points):
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


def default_lights(h, room):
    """An undressed room gets one soft ceiling strip along its long axis so it isn't black."""
    if plan.ROOMS[room].get("kind") == "courtyard":
        return []
    (x0, y0, x1, y1), _, _ = h.interior(room)
    w, d = x1 - x0, y1 - y0
    size = (w * 0.6, 0.08) if w >= d else (0.08, d * 0.6)
    return [dict(kind="strip", pos=(0, 0), size=size, power=30.0 + 1.5 * w * d)]


def build(export=True, rooms_only=None, write_json=True):
    """rooms_only: dress just these rooms (the shell is always complete); for previews."""
    p = P
    models = os.path.join(PROJECT, "assets", "models")
    levels = os.path.join(PROJECT, "assets", "levels")
    os.makedirs(models, exist_ok=True)
    os.makedirs(levels, exist_ok=True)

    props_col = common.fresh_collection(f"{NAME}_Props")
    base = default_finishes()
    mods = {room: room_module(room) for room in plan.ROOMS}
    court = courtyard_finishes()
    h = house.House(plan, {room: finishes_for(room, mods[room],
                                              court if plan.ROOMS[room].get("kind") == "courtyard" else base)
                           for room in plan.ROOMS}, NAME).build()

    for room in plan.ROOMS:
        mod = mods[room]
        _, z0, z1 = h.interior(room)
        lights = per_room(mod, "LIGHTS", room, None)
        if lights is None:
            lights = default_lights(h, room)
        for L in lights:
            if L["kind"] == "strip":
                wx, wy, _ = h.to_world(room, L["pos"])
                h.strip(room, (wx, wy), L["size"], z1, L["power"])
            elif L["kind"] == "point":
                h.point(h.to_world(room, L["pos"]), L["power"], L.get("color", (1.0, 0.78, 0.55)))
        probe = per_room(mod, "PROBE", room, None)
        if probe:
            h.probes[room] = h.to_world(room, probe)

    air_all = [box for boxes in h.air.values() for box in boxes]
    lm_res = {}
    for room, objs in h.baked.items():
        lm_res[room] = min(p["lightmap_res"], h.lightmap_resolution(room))
        common.lightmap_uv(objs, h.solids, air_all, resolution=lm_res[room])
    h.merge()
    blender_lights(p, h)

    # placements: doors from the plan's cuts, then every room's furniture
    entries = []
    for d in h.doors:
        entries.append((d["room"], d["asset"], d["pos"], d["rot"], {"lock": d["lock"]} if d["lock"] else {}))
    for room in plan.ROOMS:
        if rooms_only and room not in rooms_only:
            continue
        for asset, loc, rot, *rest in per_room(mods[room], "PLACEMENTS", room, []) or []:
            opts = rest[0] if rest else {}
            pos = loc if "attach" in opts else h.to_world(room, loc)
            entries.append((room, asset, pos, rot, opts))

    assets, roots, placed = {}, {}, []
    for room, asset, loc, rot, opts in entries:
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
            ob.parent = bpy.data.objects[node]
            entry["attach"] = {"asset": host, "node": node}
        if opts.get("lock"):
            entry["lock"] = opts["lock"]
        ob.location = loc
        ob.rotation_euler = (0, 0, math.radians(rot))
        placed.append(entry)

    if export:
        common.export_gltf(h.root, os.path.join(models, "mansion_shell.gltf"))
    sun = Vector(p["sun_dir"]).normalized()
    sx, sy = plan.SPAWN["position"]
    rooms = {}
    for r, pt in h.probes.items():
        x0, y0, x1, y1 = plan.ROOMS[r]["rect"]
        _, z0, z1 = h.interior(r)
        rooms[r] = {"probe": common.to_gltf(pt), "lightmap": lm_res.get(r), "level": plan.ROOMS[r]["level"],
                    "floor": z0, "height": round(z1 - z0, 3),
                    "rect": [x0, -y1, x1, -y0]}          # glTF: x0, z0, x1, z1
    level = {
        "name": NAME,
        "units": "metres, Y-up (glTF)",
        "shell": "models/mansion_shell.gltf",
        "rooms": rooms,
        "assets": assets,
        "props": placed,
        "colliders": h.colliders,
        "lights": h.lights + [
            {"type": "sun", "direction": common.to_gltf(sun), "intensity": p["sun_strength"], "color": [1.0, 0.96, 0.9]},
            {"type": "ambient_env", "intensity": 0.6},
            {"type": "hemisphere", "sky": [0.85, 0.9, 1.0], "ground": [0.95, 0.8, 0.62], "intensity": 1.1},
        ],
        "spawn": {"position": common.to_gltf((sx, sy, 1.65)), "lookAt": common.to_gltf(plan.SPAWN["look"])},
    }
    if write_json:
        with open(os.path.join(levels, "mansion.json"), "w") as f:
            json.dump(level, f, indent=2)
    shell_parts = [o for o in h.root.children_recursive if o.type == "MESH"]
    total = common.triangle_count(shell_parts) + sum(assets[e["asset"]]["tris"] for e in placed if e["asset"] in assets)
    print(f"{NAME}: {len(plan.ROOMS)} rooms, {len(placed)} props, {len(h.colliders)} colliders, "
          f"{len(shell_parts)} shell meshes, {total} tris total")
    return level, h


if __name__ == "__main__":
    build()
