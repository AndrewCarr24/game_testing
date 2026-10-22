"""The armory (below ground; design/house/secret_passage.md): 7.2 x 13.72 m inside, 3.4 m high,
its long axis north-south under the den and the great room. The library's cold twin: where the
library has oak, books on a 1.18 m bay rhythm, a reading table under a linear pendant and warm
lamps, the armory has a polished dark concrete floor, a gun-safe wall on the same bay rhythm
whose stainless doors lift like jewel-case lids, a stainless layout table in the middle under
two cold ceiling lines, and nothing warm at all.

You come in from the secret stair through the steel door in the south wall (x -1.7..-0.5) and
see the whole room at once. West wall: the safe wall (the wheel opens it). East wall, south to
north: the emergency power and air (battery units, transfer switch, NBC filter), the security
station (a bank of monitors), the gunsmith's bench; then the blast door to the tunnel (y
4.11..6.11; it swings into the room along y 4.11). North wall: supplies.

Weapons are set dressing for now (the weapons workstream turns them into pickups): each is a
placement with {"weapon_slot": kind} (written to mansion.json props[].weapon_slot), standing in
the safe wall's bays.

Local coords: (0, 0) = the interior centre (world -13.75, -7.51), z = 0 the floor (world -4.2).
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets"))
import bunker_kit  # noqa: E402

importlib.reload(bunker_kit)

FINISHES = dict(
    floor=lambda: bunker_kit.concrete("M_Armory_Floor", (0.12, 0.12, 0.125), roughness=0.22),
    floor_uv_tile=6.0,
    walls=lambda: bunker_kit.concrete("M_Armory_Wall", (0.40, 0.405, 0.41), roughness=0.9),
    wall_uv_tile=4.0,
    ceiling=lambda: bunker_kit.concrete("M_Armory_Ceiling", (0.52, 0.525, 0.53), roughness=0.92),
)

SAFE = (-3.29, 0.0, 90)       # armory_safe_wall: its back on the west wall, facing east
BAY = 1.18


def _in_safe(ax, ay, az=0.0, rot=0.0):
    """A point in the safe wall's own frame (x along the wall, +y into it) -> a room placement."""
    x, y, r = SAFE
    # rotation 90: the asset's (ax, ay) -> room (-ay, ax)
    return (round(x - ay, 3), round(y + ax, 3), az), r + rot


def _slot(asset, kind, ax, ay, az, rot=0.0):
    pos, r = _in_safe(ax, ay, az, rot)
    return (asset, pos, r, {"weapon_slot": kind})


_LONG = {0: ["armory_rifle"] * 3, 1: ["armory_rifle", "armory_rifle", "armory_rifle"],
         3: ["armory_shotgun"] * 3, 4: ["armory_rifle", "armory_shotgun", "armory_bat"]}
PLACEMENTS = [
    ("armory_safe_wall", (SAFE[0], SAFE[1]), SAFE[2]),
    # weapon slots in the bays (the safe wall's spec: long guns upright at bay centre -0.3/0/+0.3,
    # y +0.12, on the felt floor at 0.22; pistols on the middle bay's pegboard)
    *[_slot(a, a.split("_")[1], (i - 2) * BAY + dx, 0.12, 0.22)
      for i, assets in _LONG.items() for a, dx in zip(assets, (-0.3, 0.0, 0.3))],
    *[_slot("armory_pistol", "pistol", sx * 0.2, 0.2, z) for sx in (-1, 1) for z in (1.25, 1.65)],
    # the east wall, south to north (backs on the wall at x 3.6, facing west)
    ("armory_power", (3.325, -4.0), -90),
    ("armory_security", (3.2, 0.0), -90),
    ("armory_bench", (3.225, 2.55), -90),
    # the layout table in the middle, its long axis north-south
    ("armory_table", (0.35, -0.6), 90),
    # supplies along the north wall (the blast door's way in stays clear: x 1.6..3.6, y 4..6.86)
    ("armory_supplies", (-2.2, 6.61), 180),
    ("armory_supplies", (0.25, 6.61), 180),
]

# Light: two cold lines in the ceiling the length of the room (6000 K), the safe wall's doors
# grazed by five ceiling spots (they gleam), two spots on the layout table, the bench lamp, the
# monitors' glow. The bunker has its own power: nothing here is switched (signal None).
_COLD = (0.82, 0.90, 1.0)
LIGHTS = [
    dict(kind="strip", pos=(-1.2, 0.2), size=(0.06, 11.6), power=240.0, color=_COLD, signal=None),
    dict(kind="strip", pos=(1.9, 0.2), size=(0.06, 11.6), power=240.0, color=_COLD, signal=None),
    *[dict(kind="spot", pos=(-2.45, (i - 2) * BAY, 3.36), aim=(-3.0, (i - 2) * BAY, 1.2), power=70.0, angle=48,
           blend=0.8, color=_COLD, signal=None) for i in range(5)],
    dict(kind="spot", pos=(0.35, -1.5, 3.36), aim=(0.35, -1.5, 0.92), power=120.0, angle=38, blend=0.6,
         color=_COLD, signal=None),
    dict(kind="spot", pos=(0.35, 0.3, 3.36), aim=(0.35, 0.3, 0.92), power=120.0, angle=38, blend=0.6,
         color=_COLD, signal=None),
    dict(kind="point", pos=(2.9, 2.0, 1.55), power=18.0, color=_COLD, signal=None),             # bench lamp
    dict(kind="area", pos=(2.95, 0.0, 1.45), size=(2.0, 0.7), aim=(0.0, 0.0, 1.2), power=16.0,   # monitors
         color=(0.55, 0.70, 0.86), signal=None),
]

PROBE = (0.0, 2.6, 1.6)
