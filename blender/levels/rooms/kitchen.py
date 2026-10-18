"""Kitchen (ground floor, north-centre): 17.7 x 9.2 m inside, ceiling 4.2 m, north wall
glazed (x -7..7). Openings: west to the dining room (y -2.5..2.5), south to the gallery
(x -2..4), east to the scullery (y -1..1).

Zones: a floor-to-ceiling walnut wall (pantry, two steel fridge columns, oven tower, base
drawers) on the south wall's west half; the cooking wall (steel range under a Calacatta
slab and hood) on its east half; a 4.8 m waterfall-marble island with stools and pendants
in the middle; a breakfast table by the glass in the north-west; a lounge nook by the
glass in the north-east."""
import importlib

from lib import common, materials

import kitchen_lib

importlib.reload(kitchen_lib)

FINISHES = dict(
    floor=kitchen_lib.stone_floor_mat,
    walls=lambda: common.pbr_material("M_Plaster_Kitchen", (0.66, 0.62, 0.56), roughness=0.92),
    ceiling=lambda: common.pbr_material("M_Ceiling_White", (0.8, 0.8, 0.79), roughness=0.9),
    floor_uv_tile=2.4,
)

WALL_Y = -4.27            # back of the south-wall runs (depth 0.66) against the wall

PLACEMENTS = [
    # --- south wall: walnut tower wall (west) and cooking wall (east), both facing north
    ("kitchen_wall_run", (-5.5, WALL_Y), 180),
    ("kitchen_range_wall", (6.5, WALL_Y), 180),

    # --- island: working side (drawers, sink) faces the south wall, stools on the north side
    ("kitchen_island", (0.5, -1.14), 0),
    ("kitchen_stool", (-0.6, -0.30), 0),
    ("kitchen_stool", (0.1, -0.30), 0),
    ("kitchen_stool", (0.8, -0.30), 0),
    ("kitchen_stool", (1.5, -0.30), 0),
    ("kitchen_stool", (2.2, -0.30), 0),
    ("kitchen_pendant", (-0.9, -1.16, 1.95), 0),
    ("kitchen_pendant", (0.5, -1.16, 1.95), 0),
    ("kitchen_pendant", (1.9, -1.16, 1.95), 0),

    # --- breakfast table by the glass, north-west
    ("kitchen_table", (-4.5, 3.0), 0),
    ("kitchen_chair", (-5.2, 2.25), 180),
    ("kitchen_chair", (-4.5, 2.25), 180),
    ("kitchen_chair", (-3.8, 2.25), 180),
    ("kitchen_chair", (-5.2, 3.75), 0),
    ("kitchen_chair", (-4.5, 3.75), 0),
    ("kitchen_chair", (-3.8, 3.75), 0),
    ("vase", (-4.5, 3.0, 0.75), 0),

    # --- lounge nook by the glass, north-east
    ("rug", (4.5, 3.0), 90),
    ("coffee_table", (4.5, 3.0), 90),
    ("lounge_chair", (3.55, 3.0), 90),
    ("lounge_chair", (5.45, 3.0), -90),
    ("vase", (4.48, 3.22, 0.38), 0),

    # --- art on the two short wall stretches beside the glass
    ("art_colorfield_a", (-8.85, 3.55, 1.7), 90),
    ("art_linework_a", (8.85, 2.8, 1.7), -90),
]

LIGHTS = [
    dict(kind="strip", pos=(0.5, -1.15), size=(5.4, 0.08), power=230.0),     # over the island
    dict(kind="strip", pos=(-1.0, -3.1), size=(12.0, 0.08), power=380.0),    # wash on the cabinetry wall
    dict(kind="strip", pos=(-0.5, 1.9), size=(13.0, 0.08), power=380.0),     # circulation / glass side
    dict(kind="point", pos=(-0.9, -1.16, 1.8), power=70.0, color=(1.0, 0.76, 0.5)),
    dict(kind="point", pos=(0.5, -1.16, 1.8), power=70.0, color=(1.0, 0.76, 0.5)),
    dict(kind="point", pos=(1.9, -1.16, 1.8), power=70.0, color=(1.0, 0.76, 0.5)),
]

PROBE = (1.0, 1.0, 1.6)
