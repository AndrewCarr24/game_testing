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
  LIGHTS     room-local, all baked (none reach the engine as real-time lights):
             dict(kind="strip", pos=(x, y), size=(w, d), power=W)   glowing ceiling slot
             dict(kind="point", pos=(x, y, z), power=W, color=(r, g, b))   bulb in a lamp,
                 pendant, sconce, chandelier (the fixture itself is a prop)
             dict(kind="spot", pos=(x, y, z), aim=(x, y, z), power=W, angle=deg, blend=0..1,
                 color=...)   downlight, picture light, wall grazer, reading light
             dict(kind="area", pos=(x, y, z), size=(w, d), aim=(x, y, z), power=W, color=...)
                 hidden soft source: cove / valance wash, backlit headboard or shelf,
                 under-cabinet, toe-kick; no glowing geometry of its own. size's axes follow
                 the aim (to_track_quat("-Z", "Y")): aimed straight down it's (x, y); aimed
                 sideways it's (along the wall, vertical); tilted towards +-x they swap
             spot power counts like a bare bulb's: a narrow beam doesn't concentrate it
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
from lib import common, house, materials, outdoor, textures, vertex_ao  # noqa: E402
import plan  # noqa: E402
import grounds  # noqa: E402
import sunlight  # noqa: E402
import visibility  # noqa: E402

for m in (common, textures, materials, outdoor, vertex_ao, house, plan, grounds, sunlight, visibility):
    importlib.reload(m)

NAME = "Mansion"

# Times of day: everything that lights the level, shared by the bake (Cycles), the horizon
# render (horizon.py) and the engine (sun, sky dome). Switch LOOK and rebuild + rebake.
LOOKS = {
    "day": dict(
        sun_dir=(-0.35, -0.72, -0.6),     # direction the light travels (Blender coords)
        sun_strength=4.0,                 # W/m² in Blender = DirectionalLight intensity in three.js
        sun_color=(1.0, 0.96, 0.9),
        sky=(0.55, 0.68, 0.85), sky_strength=1.0,       # the world light in the bake
        sky_horizon=(0.80, 0.86, 0.95), sky_zenith=(0.28, 0.46, 0.85), haze=(0.62, 0.70, 0.84),
        cove_color=(1.0, 0.92, 0.82),
        exposure=0.8,
    ),
    # late afternoon: a low sun in the west, straight down the west garden's open axis (over the
    # reflecting pool; nothing tall stands on it), pours through the great room's glass wall
    "golden": dict(
        sun_dir=(0.94, 0.12, -0.32),      # ~19 degrees up, from just south of west
        sun_strength=6.0,                 # a low sun reaches floors at a grazing angle: it must
                                          # clearly beat the ceiling strips to read as sunlight
        sun_color=(1.0, 0.70, 0.45),
        sky=(0.42, 0.52, 0.72), sky_strength=0.85,
        sky_horizon=(0.98, 0.76, 0.56), sky_zenith=(0.20, 0.33, 0.66), haze=(0.82, 0.70, 0.60),
        cove_color=(1.0, 0.86, 0.70), cove_scale=0.75,
        exposure=0.95,
    ),
}
LOOK = "golden"
P = dict(LOOKS[LOOK], look=LOOK,
         lightmap_res=1024)                # upper limit per room; small rooms get 512


def plaster_walls():
    """Warm-white painted plaster: a Poly Haven scan tinted to the house white (polyhaven_textures.py
    GENERATE), falling back to the flat colour if it hasn't been made."""
    m = common.pbr_material("M_Plaster_WarmWhite", (0.72, 0.70, 0.66), roughness=0.9)
    path = os.path.join(textures.TEX_DIR, "T_Plaster_Wall_BaseColor.png")
    if os.path.exists(path):
        common.set_base_color_map(m, textures.load(path))
    return m


def default_finishes():
    oak = common.pbr_material("M_OakFloor", (0.4, 0.27, 0.15), roughness=0.45, coat=0.1)
    common.set_base_color_map(oak, textures.load(textures.oak_floor()))
    return dict(
        floor=oak,
        walls=plaster_walls(),
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
        ld.energy = ls["power"] * p.get("cove_scale", 1.0)
        ld.color = p["cove_color"]
        ob = bpy.data.objects.new(f"{NAME}_Cove_{i}", ld)
        ob.location = (*ls["pos"], ls["z"] - 0.02)
        col.objects.link(ob)
    for i, pt in enumerate(h.points):
        ld = bpy.data.lights.get(f"{NAME}_Lamp_{i}") or bpy.data.lights.new(f"{NAME}_Lamp_{i}", "POINT")
        ld.energy, ld.color, ld.shadow_soft_size = pt["power"], pt["color"], pt["radius"]
        ob = bpy.data.objects.new(f"{NAME}_Lamp_{i}", ld)
        ob.location = pt["pos"]
        col.objects.link(ob)
    for i, sp in enumerate(h.spots):
        ld = bpy.data.lights.get(f"{NAME}_Spot_{i}") or bpy.data.lights.new(f"{NAME}_Spot_{i}", "SPOT")
        ld.energy, ld.color, ld.shadow_soft_size = sp["power"], sp["color"], sp["radius"]
        ld.spot_size, ld.spot_blend = math.radians(sp["angle"]), sp["blend"]
        ob = bpy.data.objects.new(f"{NAME}_Spot_{i}", ld)
        ob.location = sp["pos"]
        ob.rotation_euler = (Vector(sp["aim"]) - Vector(sp["pos"])).to_track_quat("-Z", "Y").to_euler()
        col.objects.link(ob)
    for i, ar in enumerate(h.areas):
        ld = bpy.data.lights.get(f"{NAME}_Area_{i}") or bpy.data.lights.new(f"{NAME}_Area_{i}", "AREA")
        ld.shape = "RECTANGLE"
        ld.size, ld.size_y = ar["size"]
        ld.energy, ld.color = ar["power"], ar["color"]
        ob = bpy.data.objects.new(f"{NAME}_Area_{i}", ld)
        ob.location = ar["pos"]
        ob.rotation_euler = (Vector(ar["aim"]) - Vector(ar["pos"])).to_track_quat("-Z", "Y").to_euler()
        col.objects.link(ob)
    sd = bpy.data.lights.get(f"{NAME}_Sun") or bpy.data.lights.new(f"{NAME}_Sun", "SUN")
    sd.energy = p["sun_strength"]
    sd.color = p["sun_color"]
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


def baked_prop(asset):
    """Flat, static props drawn as part of the room's shell, lit by the floor's lightmap right
    under them (baked with them hidden), so the furniture's contact shadows land on them (as
    props they were lit by the room probe alone, so a sofa floated on its rug). Baking a rug
    itself failed: a few mm above the floor, most of its texels came out black."""
    return "rug" in asset


def bake_into_shell(h, room, asset, loc, rot):
    """Build `asset` and copy its meshes into the shell at a placement, transforms applied,
    tagged ob["lm_borrow"] (see borrow_floor_lightmap); returns False if there's no asset."""
    from mathutils import Matrix
    try:
        mod = importlib.import_module(asset)
    except ModuleNotFoundError:
        return False
    importlib.reload(mod)
    root, parts = mod.build()
    import bmesh
    floor = h.to_world(room, loc)[2]
    place = Matrix.Translation(h.to_world(room, loc)) @ Matrix.Rotation(math.radians(rot), 4, "Z")
    for part in parts:
        me = part.data.copy()
        me.transform(place @ part.matrix_world)
        # keep only what faces up above the floor (it borrows the floor's light from above;
        # its 7 mm edge isn't seen from eye height)
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z < 0.3 or f.calc_center_median().z < floor + 0.001],
                         context="FACES")
        bm.to_mesh(me)
        bm.free()
        if not me.polygons:
            continue
        ob = bpy.data.objects.new(f"{NAME}_{room}_{part.name}", me)
        h.col.objects.link(ob)
        ob.parent = h.root
        ob["room"], ob["lm_borrow"] = room, True
        h.borrowed.setdefault(room, []).append(ob)
        if not any(t in part.name for t in common.COLLIDER_SKIP):
            vs = [v.co for v in me.vertices]
            h.colliders.append(common.aabb_gltf(tuple(min(v[i] for v in vs) for i in range(3)),
                                                tuple(max(v[i] for v in vs) for i in range(3))))
    col = root.users_collection[0]
    for ob in [root] + list(root.children_recursive):
        bpy.data.objects.remove(ob, do_unlink=True)
    if col.name != "Scene Collection" and not col.objects:
        bpy.data.collections.remove(col)
    return True


def borrow_floor_lightmap(h):
    """Give each rug the floor lightmap's UVs at the same x, y (the floor's top face is one
    axis-aligned rectangle in its room's atlas, so the mapping is affine)."""
    for room, obs in h.borrowed.items():
        floor = bpy.data.objects[f"{NAME}_{room}_Floor"]
        me = floor.data
        top = max(me.polygons, key=lambda f: f.normal.z)
        pts = [(floor.matrix_world @ me.vertices[me.loops[li].vertex_index].co, me.uv_layers["Lightmap"].data[li].uv)
               for li in top.loop_indices]
        (xa, ua), (xb, ub) = min(((p.x, uv.x) for p, uv in pts)), max(((p.x, uv.x) for p, uv in pts))
        (ya, va), (yb, vb) = min(((p.y, uv.y) for p, uv in pts)), max(((p.y, uv.y) for p, uv in pts))
        for ob in obs:
            layer = ob.data.uv_layers.get("Lightmap") or ob.data.uv_layers.new(name="Lightmap")
            ob.data.uv_layers.active_index = 0
            for li, loop in enumerate(ob.data.loops):
                co = ob.matrix_world @ ob.data.vertices[loop.vertex_index].co
                layer.data[li].uv = (ua + (co.x - xa) * (ub - ua) / (xb - xa), va + (co.y - ya) * (vb - va) / (yb - ya))


def default_lights(h, room):
    """An undressed room gets one soft ceiling strip along its long axis so it isn't black."""
    if plan.ROOMS[room].get("kind") == "courtyard":
        return []
    (x0, y0, x1, y1), _, _ = h.interior(room)
    w, d = x1 - x0, y1 - y0
    size = (w * 0.6, 0.08) if w >= d else (0.08, d * 0.6)
    return [dict(kind="strip", pos=(0, 0), size=size, power=30.0 + 1.5 * w * d)]


def build(export=True, rooms_only=None, write_json=True, zones_only=None):
    """rooms_only: dress just these rooms (the shell is always complete); zones_only: dress
    just these outdoor zones (the lawn, terrace and hedge are always there); for previews."""
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
            elif L["kind"] == "spot":
                h.spot(h.to_world(room, L["pos"]), h.to_world(room, L["aim"]), L["power"],
                       L.get("angle", 40.0), L.get("blend", 0.6), L.get("color", (1.0, 0.82, 0.62)))
            elif L["kind"] == "area":
                h.area(h.to_world(room, L["pos"]), L["size"], h.to_world(room, L["aim"]), L["power"],
                       L.get("color", (1.0, 0.84, 0.66)))
            else:
                raise ValueError(f"{room}: unknown light kind {L['kind']!r}")
        probe = per_room(mod, "PROBE", room, None)
        if probe:
            h.probes[room] = h.to_world(room, probe)

    # rugs become part of the shell, lit by the floor's lightmap under them
    in_shell = set()
    h.borrowed = {}
    for room in plan.ROOMS:
        if rooms_only and room not in rooms_only:
            continue
        for i, (asset, loc, rot, *rest) in enumerate(per_room(mods[room], "PLACEMENTS", room, []) or []):
            if baked_prop(asset) and "attach" not in (rest[0] if rest else {}) and bake_into_shell(h, room, asset, loc, rot):
                in_shell.add((room, i))

    air_all = [box for boxes in h.air.values() for box in boxes]
    lm_res = {}
    for room, objs in h.baked.items():
        lm_res[room] = min(p["lightmap_res"], h.lightmap_resolution(room))
        common.lightmap_uv(objs, h.solids, air_all, resolution=lm_res[room])
    borrow_floor_lightmap(h)
    h.merge()
    blender_lights(p, h)

    # placements: doors from the plan's cuts, then every room's furniture
    entries = []
    for d in h.doors:
        entries.append((d["room"], d["asset"], d["pos"], d["rot"], {"lock": d["lock"]} if d["lock"] else {}))
    for room in plan.ROOMS:
        if rooms_only and room not in rooms_only:
            continue
        for i, (asset, loc, rot, *rest) in enumerate(per_room(mods[room], "PLACEMENTS", room, []) or []):
            if (room, i) in in_shell:
                continue
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
                vertex_ao.bake(root)          # the asset's own occlusion -> vertex colours
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

    # the grounds (after the rooms: they reuse assets the rooms already built)
    bpy.context.view_layer.update()
    out_root, _, zone_tris = grounds.build(h, plan, roots, zones_only)
    if export:
        common.export_gltf(h.root, os.path.join(models, "mansion_shell.gltf"))
        common.export_gltf(out_root, os.path.join(models, "mansion_outdoor.gltf"))
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
        "outdoor": "models/mansion_outdoor.gltf",
        "zones": {z: {"rect": [x0, -y1, x1, -y0], "tris": zone_tris.get(z)}      # glTF x0, z0, x1, z1
                  for z, (x0, y0, x1, y1) in ((z, i["rect"]) for z, i in plan.GROUNDS["zones"].items())},
        "rooms": rooms,
        "assets": assets,
        "props": placed,
        "colliders": h.colliders,
        "ramps": h.ramps,
        "lights": h.lights + [
            {"type": "sun", "direction": common.to_gltf(sun), "intensity": p["sun_strength"], "color": list(p["sun_color"])},
            {"type": "ambient_env", "intensity": 0.6},
            {"type": "hemisphere", "sky": [0.85, 0.9, 1.0], "ground": [0.95, 0.8, 0.62], "intensity": 1.1},
        ],
        "spawn": {"position": common.to_gltf((sx, sy, 1.65)), "lookAt": common.to_gltf(plan.SPAWN["look"])},
        "sky": {"look": p["look"], "horizon": list(p["sky_horizon"]), "zenith": list(p["sky_zenith"]),
                "haze": list(p["haze"]), "light": list(p["sky"]), "light_strength": p["sky_strength"],
                "sun_strength": p["sun_strength"], "sun_color": list(p["sun_color"])},
    }
    # rooms direct sunlight never reaches: their props skip real-time sun (sunlight.py)
    lit = sunlight.sunlit_rooms({r: h.interior(r) for r in rooms}, list(h.root.children_recursive), p["sun_dir"])
    for r, v in lit.items():
        rooms[r]["sun"] = v
    # which rooms can see into which (doors closed): the engine's culler (visibility.py)
    interiors, shell_obs = {r: h.interior(r) for r in rooms}, list(h.root.children_recursive)
    for key, closed in (("sees", True), ("seesOpen", False)):
        for r, v in visibility.room_visibility(interiors, shell_obs, plan, doors_closed=closed).items():
            rooms[r][key] = v
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
