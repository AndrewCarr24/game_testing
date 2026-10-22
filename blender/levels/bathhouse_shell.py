"""What house.py can't build for the bathhouse (bathhouse_plan.py), added to the same House shell
so it's lightmapped, merged and exported like every room: the pools' stone basins (the hall's
pool with its glass east end, the hot pool, the cold plunge with its steps down to the secret
door), the secret stair's solid treads and landing with an invisible ramp along them, skylight
glass in the ceiling slots, invisible blockers over the water, and world-aligned UVs for the
bathhouse's coursed stone (house.box_uv runs u along each box's longest side: on a narrow pier
the courses stood on end). Called by mansion.py right after House.build()."""
import importlib

from lib import common
from lib.house import keep_slices

import bathhouse_plan as BP

importlib.reload(BP)


def _mats():
    import bathhouse as rooms_mod          # blender/levels/rooms/bathhouse.py (materials)
    importlib.reload(rooms_mod)
    return {k: fn() for k, fn in rooms_mod.SHELL.items()}


def basin(h, room, inner, floor_z, mat, holes=None, open_sides="", name="Pool", air=True):
    """A sunken basin: walls T thick round `inner` (x0, y0, x1, y1) from floor_z to 0, a floor
    slab under it. holes: {side: [(a0, a1, z0, z1)]} cut out of a wall (world coordinates along
    it); open_sides: sides with no wall (steps come up there)."""
    T, S = BP.T, 0.2
    x0, y0, x1, y1 = inner
    holes = holes or {}
    ya, yb = y0 - (0 if "S" in open_sides else T), y1 + (0 if "N" in open_sides else T)
    h.box(room, f"{room}_{name}_Floor", (x0 - T, ya, floor_z - S), (x1 + T, yb, floor_z), mat, bake=True)
    sides = {
        "W": ("y", x0 - T, x0, ya, yb),
        "E": ("y", x1, x1 + T, ya, yb),
        "S": ("x", y0 - T, y0, x0, x1),
        "N": ("x", y1, y1 + T, x0, x1),
    }
    for side, (axis, d0, d1, a0, a1) in sides.items():
        if side in open_sides:
            continue
        for i, (s0, s1, keep) in enumerate(keep_slices(a0, a1, floor_z, 0.0, holes.get(side, []))):
            for j, (kz0, kz1) in enumerate(keep):
                lo, hi = ((d0, s0, kz0), (d1, s1, kz1)) if axis == "y" else ((s0, d0, kz0), (s1, d1, kz1))
                h.box(room, f"{room}_{name}_Wall{side}_{i}_{j}", lo, hi, mat, bake=True)
    if air:
        h.air.setdefault(room, []).append(((x0, y0, floor_z), (x1, y1, 0.0)))


def stair(h, mats):
    """The secret stair: solid concrete treads rising north from the tunnel landing (z -4.2) to
    the plunge's floor (z -1.2), a landing at the top, and the invisible ramp the player glides on
    (player.js rampHeight, along: "z")."""
    room = "ph_stair"
    x0, x1 = BP.STAIR[0] + BP.T, BP.STAIR[2] - BP.T
    n = BP.STAIR_RISERS
    rise = (BP.LANDING_Z - BP.DEEP) / n
    run = BP.STAIR_RUN
    for i in range(n - 1):
        ya, yb = BP.STAIR_Y0 + i * run, BP.STAIR_Y0 + (i + 1) * run
        h.box(room, f"PHStair_Tread_{i:02d}", (x0, ya, BP.DEEP), (x1, yb, BP.DEEP + rise * (i + 1)), mats["concrete"],
              uv_tile=1.82, bake=True)
    top_y = BP.STAIR_Y0 + (n - 1) * run
    h.box(room, "PHStair_Landing", (x0, top_y, BP.DEEP), (x1, BP.STAIR[3] - BP.T, BP.LANDING_Z), mats["concrete"],
          uv_tile=1.82, bake=True)
    foot = common.to_gltf((x0, BP.STAIR_Y0 - run, BP.DEEP))
    top = common.to_gltf((x1, top_y, BP.LANDING_Z))
    h.ramps.append({"x": [foot[0], top[0]], "z": [foot[2], top[2]], "y": [BP.DEEP, BP.LANDING_Z], "along": "z"})


def plunge(h, mats):
    """The cold plunge: a basin whose floor is the stair's landing level; its south wall holds the
    sinking slab (the opening in it is the plan's cut on y = 40.5); stone steps rise north out of
    it. The water, the slab and the blocker are a prop (bath_plunge: reacts on bath_plunge)."""
    room = "ph_cold"
    x0, y0, x1, y1 = BP.PLUNGE
    s0, s1 = BP.SLAB_DOOR
    basin(h, room, BP.PLUNGE, BP.LANDING_Z, mats["pool"], holes={"S": [(s0, s1, BP.LANDING_Z, 0.0)]},
          open_sides="N", name="Plunge")
    lo, hi = common.to_gltf((x0, y1, 0)), common.to_gltf((x1, y0, 0))
    h.sunken = getattr(h, "sunken", []) + [{"room": room, "rect": [lo[0], lo[2], hi[0], hi[2]], "floor": BP.LANDING_Z}]
    k = BP.PLUNGE_STEPS
    for i in range(1, k + 1):
        ya = y1 - (k + 1 - i) * 0.3
        h.box(room, f"{room}_Plunge_Step_{i}", (x0, ya, BP.LANDING_Z + 0.2 * (i - 1)), (x1, y1, BP.LANDING_Z + 0.2 * i),
              mats["pool"], bake=True)


def skylight(h, room, hole, z_top):
    """Glass over a ceiling hole (at the slab's top), and the hole counts as air (its sides seen)."""
    x0, y0, x1, y1 = hole
    h.box(None, f"{room}_Skylight", (x0, y0, z_top + 0.188), (x1, y1, z_top + 0.2), h.glass, collide=False, solid=False)
    h.gap_air.append(((x0, y0, z_top), (x1, y1, z_top + 0.2)))


def stones(h, mats):
    """The stepping stones across the hall's pool, near the glass: blocks of the pool's stone from
    its floor to just over the water, 0.55 m square, 0.3 m of water between them."""
    x0, x1 = BP.STONES_X
    for i, (y0, y1) in enumerate(BP.STONES):
        h.box("ph_hall", f"ph_hall_Stone_{i}", (x0, y0, BP.POOL_FLOOR), (x1, y1, BP.STONE_TOP), mats["slab"], bake=True)


def blockers(h):
    """Nobody walks into the hall's pool (but along its stepping stones) or the hot pool (seeThrough,
    like the rails); the plunge's blocker moves with its water (ph_plunge)."""
    _, py0, px1, py1 = BP.POOL
    sx0, sx1 = BP.STONES_X
    for x0, y0, x1, y1 in ((BP.HALL[0], py0, sx0, py1), (sx1, py0, px1, py1), BP.HOT):
        h.colliders.append(dict(common.aabb_gltf((x0, y0, -1.5), (x1, y1, 2.2)), seeThrough=True))


TILES = {"M_PH_Stone": 2.0, "M_PH_StoneDark": 2.0, "M_PH_Slab": 2.4, "M_PH_SlabDark": 2.4,
         "M_PH_PoolStone": 1.2, "M_PH_Concrete": 1.82, "M_PH_Red": 2.0, "M_PH_Mosaic": 0.5,
         "M_PH_Cedar": 0.5, "M_PH_Oak": 2.0, "M_PH_Ceiling": 2.0}


def world_uvs(h, rooms):
    """World-aligned UVs on every box of these rooms: floors and ceilings (u, v) = (x, y), walls
    (along the wall, z), so stone courses stay level and run on across piers and openings."""
    for ob in list(h.col.objects):
        if ob.type != "MESH" or ob.get("room") not in rooms or not ob.data.materials:
            continue
        tile = TILES.get(ob.data.materials[0].name)
        if tile is None:
            continue
        me, off = ob.data, ob.location
        uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            n = [abs(c) for c in poly.normal]
            na = n.index(max(n))
            a, b = {0: (1, 2), 1: (0, 2), 2: (0, 1)}[na]
            for li in poly.loop_indices:
                co = off + me.vertices[me.loops[li].vertex_index].co
                uv.data[li].uv = (co[a] / tile, co[b] / tile)


def build(h, plan):
    rooms = [r for r, d in plan.ROOMS.items() if d.get("building") == BP.B]
    mats = _mats()
    # the hall's pool: its east end is the stair's glass (the plan's window cut on x = 38.5)
    _, wy0, wy1, wz0, wz1 = (None, *BP.POOL_WINDOW)
    basin(h, "ph_hall", BP.POOL, BP.POOL_FLOOR, mats["pool"], holes={"E": [(wy0, wy1, wz0, wz1)]}, name="Pool")
    basin(h, "ph_fire", BP.HOT, BP.HOT_FLOOR, mats["pool"], name="HotPool")
    plunge(h, mats)
    stair(h, mats)
    stones(h, mats)
    for room, hole in (("ph_hall", BP.SKY_HALL), ("ph_fire", BP.SKY_FIRE), ("ph_stair", BP.SKY_STAIR)):
        skylight(h, room, hole, h.z_range(room)[1])
    blockers(h)
    world_uvs(h, set(rooms))
    print(f"BATHHOUSE shell: {len(rooms)} rooms")
