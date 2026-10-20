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
                 sideways it's (along the wall, vertical); tilted towards +-x they swap;
                 shape="ellipse" for a round or pill-shaped source (default "rectangle")
             point / spot / area may add no_shadow=[asset, ...]: those props in this room
                 don't block this light in the bake (a sculpture under its own spot). A
                 fixture never shadows its own light anyway (bake.py)
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
         lightmap_res=1024,                # upper limit per room
         # GPU memory for all lightmap atlases together (lightmap_policy shares it out by
         # texel density; 2026-10-20: 5 x 1024² + 21 x 512² were 57.4 MB)
         lightmap_mb=62.0,
         lightmap_hero=1.3)                # double-height rooms count their density / this (big, seen from afar)
LIGHTMAP_SIZES = [(512, 512), (1024, 512), (1024, 1024)]


def plaster_walls():
    """Warm-white painted plaster: a Poly Haven scan tinted to the house white (polyhaven_textures.py
    GENERATE), falling back to the flat colour if it hasn't been made."""
    m = common.pbr_material("M_Plaster_WarmWhite", (0.72, 0.70, 0.66), roughness=0.9)
    path = os.path.join(textures.TEX_DIR, "T_Plaster_Wall_BaseColor.png")
    if os.path.exists(path):
        common.set_base_color_map(m, textures.load(path))
    return m


def default_finishes():
    # oiled oak, no lacquer coat (a mirror-sharp coat slid the room panorama's lamps over the floor)
    oak = common.pbr_material("M_OakFloor", (0.4, 0.27, 0.15), roughness=0.45)
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
        ld.shape = "ELLIPSE" if ar.get("shape") == "ellipse" else "RECTANGLE"
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


# flat wall art: drawn with the shell and lit by the wall's lightmap behind it (as a prop it
# had only the room probe: spot-lit art came out darker than its wall)
WALL_ART = ("art_", "picture_frame", "dining_artwork", "entry_artwork", "living_art_")


FIXTURE_WORDS = ("light", "lamp", "pendant", "chandelier", "sconce", "halo")


def is_fixture(asset):
    """A light fixture (its own light shouldn't be shadowed by it in the bake, its glow is the
    light object's), by name: lamps, pendants, chandeliers, sconces, downlights, halos (not the
    built-ins with LED strips in ix_common.FIXTURES: a cabinet should still block light)."""
    return any(w in asset for w in FIXTURE_WORDS) and not asset.startswith(("ix_switch", "ix_flashlight"))


def baked_prop(asset):
    """Flat, static props drawn as part of the room's shell, lit by the lightmap of the
    surface right under/behind them (baked with them hidden), so the furniture's contact
    shadows land on them (as props they were lit by the room probe alone, so a sofa floated on
    its rug) and spot-lit art gets its spot. Baking a rug itself failed: a few mm above the
    floor, most of its texels came out black. Returns "floor" (rugs), "wall" (wall art) or None."""
    if "rug" in asset:
        return "floor"
    if asset.startswith(WALL_ART) and asset != "art_painters" and asset != "art_collection":
        return "wall"
    return None


def bake_into_shell(h, room, asset, loc, rot, mode):
    """Build `asset` and copy its meshes into the shell at a placement, transforms applied,
    tagged ob["lm_borrow"] = mode (see borrow_lightmaps); returns False if there's no asset."""
    from mathutils import Matrix
    try:
        mod = importlib.import_module(asset)
    except ModuleNotFoundError:
        return False
    importlib.reload(mod)
    root, parts = mod.build()
    # the parts' matrix_world is stale until the depsgraph updates (their location was set in
    # build()): without this every rug part sat at z 0, the border slab covered the body and
    # stripes and the rug came out one flat muddy slab (courtyard)
    bpy.context.view_layer.update()
    import bmesh
    origin = Vector(h.to_world(room, loc))
    inward = Matrix.Rotation(math.radians(rot), 4, "Z") @ Vector((0, -1, 0))    # art faces -Y
    place = Matrix.Translation(origin) @ Matrix.Rotation(math.radians(rot), 4, "Z")
    for part in parts:
        me = part.data.copy()
        me.transform(place @ part.matrix_world)
        bm = bmesh.new()
        bm.from_mesh(me)
        if mode == "floor":
            # keep only what faces up above the floor (it borrows the floor's light from above;
            # its 7 mm edge isn't seen from eye height)
            drop = [f for f in bm.faces if f.normal.z < 0.3 or f.calc_center_median().z < origin.z + 0.001]
        else:
            # everything but the back (against the wall): side faces take the light at their
            # footprint on the wall
            drop = [f for f in bm.faces if f.normal.dot(inward) < -0.3 or
                    (f.calc_center_median() - origin).dot(inward) < -0.002]
        bmesh.ops.delete(bm, geom=drop, context="FACES")
        bm.to_mesh(me)
        bm.free()
        if not me.polygons:
            continue
        mat = me.materials[0] if me.materials else None
        if mode == "wall" and mat is not None and mat.name.startswith("M_Glass"):
            bpy.data.meshes.remove(me)        # picture glass: near-invisible, one more draw call per room
            continue
        ob = bpy.data.objects.new(f"{NAME}_{room}_{part.name}", me)
        h.col.objects.link(ob)
        ob.parent = h.root
        if mode == "wall" and mat is not None and mat.name == h.frame.name:
            # black metal frames and backings: one unbaked mesh for the whole house (at 2% albedo
            # the lightmap shows nothing; a draw call per room saved), hidden from every bake
            # like the art (left in, they shadowed the wall texels the art borrows: black art)
            ob["art_frame"] = True
            h.art_frame_rooms.add(room)
            continue
        ob["room"], ob["lm_borrow"] = room, mode
        ob["lm_plane"] = list(origin) + list(inward if mode == "wall" else Vector((0, 0, 1)))
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


def _surface_map(h, room, point, normal):
    """The lightmap UV of the room's baked surface through `point` facing `normal` (an
    axis): (axes, M) with uv = M @ (co[axes[0]], co[axes[1]], 1), an affine map from that
    face's loops (the lightmap charts are axis-aligned, and one chart covers a whole wall
    plane, so it extends across the wall)."""
    import numpy as np
    na = max(range(3), key=lambda i: abs(normal[i]))
    sign = normal[na] > 0
    axes = [i for i in range(3) if i != na]
    best = None
    for ob in h.baked.get(room, []):
        me = ob.data
        if "Lightmap" not in me.uv_layers:
            continue
        lm = me.uv_layers["Lightmap"].data
        off = Vector(ob.location)
        for poly in me.polygons:
            if abs(poly.normal[na]) < 0.99 or (poly.normal[na] > 0) != sign:
                continue
            cos = [off + me.vertices[me.loops[li].vertex_index].co for li in poly.loop_indices]
            d = abs(cos[0][na] - point[na])
            if d > 0.05:
                continue
            uvs = [lm[li].uv for li in poly.loop_indices]
            if max(abs(u.x - uvs[0].x) + abs(u.y - uvs[0].y) for u in uvs) < 1e-6:
                continue                      # collapsed: not in the atlas
            lo = [min(c[a] for c in cos) for a in axes]
            hi = [max(c[a] for c in cos) for a in axes]
            out = sum(max(0.0, lo[k] - point[a], point[a] - hi[k]) for k, a in enumerate(axes))
            score = (out, d)
            if best is None or score < best[0]:
                A = np.array([[c[axes[0]], c[axes[1]], 1.0] for c in cos])
                B = np.array([[u.x, u.y] for u in uvs])
                M = np.linalg.lstsq(A, B, rcond=None)[0].T
                best = (score, M)
    if best is None:
        return None
    if best[0][0] > 0.05:
        print(f"WARN {room}: no lightmapped surface under borrowed piece at {tuple(round(v, 2) for v in point)}")
    return axes, best[1]


def borrow_lightmaps(h):
    """Give each borrowed piece (rug, wall art) the lightmap UVs of the surface it lies on at
    the same point (an affine mapping onto that face's atlas region)."""
    for room, obs in h.borrowed.items():
        for ob in obs:
            plane = list(ob["lm_plane"])
            found = _surface_map(h, room, Vector(plane[:3]), Vector(plane[3:]))
            layer = ob.data.uv_layers.get("Lightmap") or ob.data.uv_layers.new(name="Lightmap")
            ob.data.uv_layers.active_index = 0
            if found is None:
                print(f"WARN {room}: {ob.name} found no surface to borrow light from")
                continue
            axes, M = found
            for li, loop in enumerate(ob.data.loops):
                co = ob.matrix_world @ ob.data.vertices[loop.vertex_index].co
                u, v = M @ (co[axes[0]], co[axes[1]], 1.0)
                layer.data[li].uv = (float(u), float(v))


def lightmap_policy(h, rooms_objs, air_all, p):
    """Lightmap charts and atlas size per room, within a GPU memory budget: every room starts
    at the smallest LIGHTMAP_SIZES entry; the room with the lowest texel density (after
    packing) moves up a size while the total stays within p["lightmap_mb"] (w*h*4 bytes + 1/3
    for mips, as viewer/tools/bench.mjs counts). Returns {room: (charts, (W, H), k, placements, fill)}."""
    sizes = [s for s in LIGHTMAP_SIZES if max(s) <= p["lightmap_res"]]
    mb = lambda s: s[0] * s[1] * 4 * 4 / 3 / 1e6
    packs = {}
    for room, objs in sorted(rooms_objs.items()):
        charts = common.lightmap_charts(objs, h.solids, air_all)
        packs[room] = (charts, [common.pack_charts(charts, *size) for size in sizes])
    level = {room: 0 for room in packs}
    total = sum(mb(sizes[0]) for _ in packs)
    while True:
        weight = lambda r: p.get("lightmap_hero", 1.0) if plan.ROOMS[r].get("double") else 1.0
        cand = sorted((packs[r][1][level[r]][0] / weight(r), r) for r in packs if level[r] + 1 < len(sizes))
        moved = False
        for k, r in cand:
            extra = mb(sizes[level[r] + 1]) - mb(sizes[level[r]])
            if total + extra <= p["lightmap_mb"]:
                level[r] += 1
                total += extra
                moved = True
                break
        if not moved:
            break
    out = {}
    for room, (charts, results) in packs.items():
        k, placed, fill = results[level[room]]
        out[room] = (charts, sizes[level[room]], k, placed, fill)
    print("LIGHTMAPS " + ", ".join(f"{r} {W}x{H} {k:.1f}/m {fill:.0%} (" + "/".join(f"{x[0]:.0f}" for x in packs[r][1]) + ")"
                                   for r, (_, (W, H), k, _, fill) in out.items()))
    print(f"LIGHTMAPS total ~{total:.1f} MB GPU (budget {p['lightmap_mb']}), lowest density "
          f"{min(v[2] for v in out.values()):.1f} texels/m")
    return out


def check_probes(h, roots_placed, probes, clearance=0.15):
    """Warn about probes inside furniture or within `clearance` of it (the panorama would see
    the inside of a table, or one surface filling half the view). Returns {room: [asset]}."""
    out = {}
    for room, pt in probes.items():
        pt = Vector(pt)
        hits = []
        for r, asset, ob in roots_placed:
            meshes = [o for o in [ob] + list(ob.children_recursive) if o.type == "MESH" and o.data.polygons]
            if r != room or not meshes:
                continue
            lo, hi = common.world_aabb(meshes)
            if not all(lo[i] - clearance <= pt[i] <= hi[i] + clearance for i in range(3)):
                continue
            for o in meshes:
                inv = o.matrix_world.inverted()
                ok, loc, nrm, _ = o.closest_point_on_mesh(inv @ pt)
                if not ok:
                    continue
                w = o.matrix_world @ loc
                inside = (pt - w).dot((o.matrix_world.to_3x3() @ nrm).normalized()) < 0
                if (w - pt).length < clearance or (inside and (w - pt).length < 1.0):
                    hits.append(f"{asset}:{o.name.split('.')[0]} ({(w - pt).length:.2f} m{', inside' if inside else ''})")
                    break
        if hits:
            out[room] = hits
            print(f"WARN probe {room} at {tuple(round(v, 2) for v in pt)} is inside / within {clearance} m of {hits}")
    return out


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
                       L.get("color", (1.0, 0.84, 0.66)), L.get("shape", "rectangle"))
            else:
                raise ValueError(f"{room}: unknown light kind {L['kind']!r}")
            if L.get("no_shadow") and L["kind"] != "strip":
                lst = {"point": h.points, "spot": h.spots, "area": h.areas}[L["kind"]]
                lst[-1]["no_shadow"] = (room, list(L["no_shadow"]))
        probe = per_room(mod, "PROBE", room, None)
        if probe:
            h.probes[room] = h.to_world(room, probe)

    # rugs and flat wall art become part of the shell, lit by the lightmap under/behind them
    in_shell = set()
    h.borrowed, h.art_frame_rooms = {}, set()
    for room in plan.ROOMS:
        if rooms_only and room not in rooms_only:
            continue
        for i, (asset, loc, rot, *rest) in enumerate(per_room(mods[room], "PLACEMENTS", room, []) or []):
            mode = baked_prop(asset)
            if mode and "attach" not in (rest[0] if rest else {}) and bake_into_shell(h, room, asset, loc, rot, mode):
                in_shell.add((room, i))

    # the air: the rooms and the gaps through the walls at openings, windows, balustrades
    air_all = [box for boxes in h.air.values() for box in boxes] + h.gap_air
    lm_res = {}
    for room, (charts, size, k, placed, fill) in lightmap_policy(h, h.baked, air_all, p).items():
        lm_res[room] = list(size)
        common.apply_charts(h.baked[room], charts, k, placed, *size)
    borrow_lightmaps(h)
    print("ART FRAMES (hidden from the bake) in", ",".join(sorted(h.art_frame_rooms)))
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

    assets, roots, placed, prop_roots = {}, {}, [], []
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
            prop_roots.append((room, asset, root))
            lo, hi = common.world_aabb(parts)
            assets[asset] = {"file": f"models/{asset}.gltf", "aabb": common.aabb_gltf(lo, hi),
                             "colliders": common.part_colliders(parts),
                             "tris": common.triangle_count(parts)}
            if export:
                vertex_ao.bake(root)          # the asset's own occlusion -> vertex colours
                common.export_gltf(root, os.path.join(models, f"{asset}.gltf"))
            if is_fixture(asset):
                root["fixture"] = True        # for bake.py (after the export: not a glTF extra); copies inherit it
            ob = root
        elif roots[asset] is None:
            continue
        else:
            ob = common.duplicate_hierarchy(roots[asset], props_col, f".{len(placed):02d}")
        prop_roots.append((room, asset, ob))
        entry = {"asset": asset, "room": room, "position": common.to_gltf(loc), "rotationY": rot}
        if "attach" in opts:
            host, node = opts["attach"]
            ob.parent = bpy.data.objects[node]
            entry["attach"] = {"asset": host, "node": node}
        if opts.get("lock"):
            entry["lock"] = opts["lock"]
        for k in ("signal", "state"):         # interactivity: switch/reactor signal override, initial state
            if k in opts:
                entry[k] = opts[k]
        ob.location = loc
        ob.rotation_euler = (0, 0, math.radians(rot))
        placed.append(entry)

    bpy.context.view_layer.update()
    check_probes(h, prop_roots, h.probes)
    # LIGHTS no_shadow: the props (by asset, in the light's room) that don't block that light in the bake
    for kind, lst in (("Lamp", h.points), ("Spot", h.spots), ("Area", h.areas)):
        for i, L in enumerate(lst):
            if "no_shadow" in L:
                room, names = L["no_shadow"]
                bpy.data.objects[f"{NAME}_{kind}_{i}"]["no_shadow"] = [ob.name for r, a, ob in prop_roots
                                                                       if r == room and a in names]
    # the grounds (after the rooms: they reuse assets the rooms already built)
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
        "breakables": h.breakables,
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
