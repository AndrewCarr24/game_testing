"""Scullery (ground floor, east of the kitchen): 5.2 x 9.2 m inside, ceiling 4.2 m. Open to
the kitchen on the west wall (y -1..1); a door to the wine room on the east wall
(y 1.2..2.3).

The working back kitchen: a stainless-topped sink run with open shelving on the north wall,
pantry banks (with lit glass cabinets) on the west wall either side of the kitchen
opening, a coffee station on the east wall, a pan-rail dresser on the south wall and a
walnut prep table in the middle."""
import importlib

from lib import common, materials

import kitchen_lib

importlib.reload(kitchen_lib)

FINISHES = dict(
    floor=kitchen_lib.stone_floor_mat,
    walls=lambda: common.pbr_material("M_Plaster_Scullery", (0.5, 0.47, 0.42), roughness=0.92),
    ceiling=lambda: common.pbr_material("M_Ceiling_White", (0.8, 0.8, 0.79), roughness=0.9),
    floor_uv_tile=2.4,
)

PLACEMENTS = [
    ("kitchen_scullery_run", (0.0, 4.278), 0),            # north wall, faces south
    ("kitchen_pantry", (-2.289, 2.45), 90),                # west wall, north of the kitchen opening, faces east
    ("kitchen_pantry", (-2.289, -3.1), 90),               # west wall, south of it
    ("kitchen_coffee_station", (2.289, -3.1), -90),       # east wall, faces west
    ("kitchen_shelving", (0.0, -4.338), 180),             # south wall, faces north
    ("kitchen_prep_table", (0.0, -1.9), 90),
    ("art_colorfield_b", (2.6, -0.2, 1.7), -90),          # east wall between the coffee station and the door
]

LIGHTS = [
    dict(kind="strip", pos=(-1.0, 0.0), size=(0.08, 7.5), power=200.0),
    dict(kind="strip", pos=(1.0, 0.0), size=(0.08, 7.5), power=200.0),
    dict(kind="strip", pos=(0.0, 3.4), size=(4.0, 0.08), power=120.0),
]

PROBE = (0.0, 0.0, 1.6)
