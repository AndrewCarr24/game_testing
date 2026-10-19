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
_WALL_CANS = (-7.6, -5.4, -3.2, 4.9, 7.8)     # lighting: ceiling cans along the south-wall runs

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
    ("art_still_life", (-8.85, 3.55, 1.6), 90),          # small still life canvas
    ("art_linen_check", (8.85, 2.8, 1.6), -90),          # framed linen check

    # --- lighting (see LIGHTS): a linear pendant over the breakfast table, a lamp in the
    #     lounge nook, ceiling cans washing the walnut and steel walls and the two canvases
    ("light_g_pendant_linear", (-4.5, 3.0, 4.2), 0),
    ("library_floorlamp", (6.3, 2.2), 0),
    *[("light_g_downlight", (x, -3.25, 4.2), 0) for x in _WALL_CANS],
    ("light_g_downlight", (-7.9, 3.55, 4.2), 0),
    ("light_g_downlight", (7.9, 2.8, 4.2), 0),
]

# Lighting: the three bronze domes over the marble island are the brightest thing; the
# working walls get task light where real kitchens have it (under the upper cabinets, from
# the hood, a glow under the island overhang) and a row of cans washing the walnut and steel
# fronts; a linear bronze pendant hangs over the breakfast table, a lamp in the lounge nook.
# The glass wall brings the daylight; no ceiling lines.
_WORK = (1.0, 0.88, 0.74)          # a touch cooler for the working walls
LIGHTS = [
    # island pendants (inside the domes) and the LED under the stool overhang
    dict(kind="point", pos=(-0.9, -1.16, 1.90), power=100.0, color=(1.0, 0.76, 0.5)),
    dict(kind="point", pos=(0.5, -1.16, 1.90), power=100.0, color=(1.0, 0.76, 0.5)),
    dict(kind="point", pos=(1.9, -1.16, 1.90), power=100.0, color=(1.0, 0.76, 0.5)),
    dict(kind="area", pos=(0.5, -0.45, 0.85), size=(4.4, 0.04), aim=(0.5, -0.45, 0.0), power=25.0, color=(1.0, 0.8, 0.55)),
    # under-cabinet LED over the sink run (kitchen_wall_run Counter_LED) and the hood light
    dict(kind="area", pos=(-3.7, -4.22, 2.38), size=(2.9, 0.06), aim=(-3.7, -4.0, 0.92), power=90.0, color=_WORK),
    dict(kind="area", pos=(6.35, -4.05, 1.68), size=(1.0, 0.05), aim=(6.35, -4.0, 0.92), power=60.0, color=_WORK),
    # cans washing the cabinetry walls
    *[dict(kind="spot", pos=(x, -3.25, 4.08), aim=(x, -3.95, 1.0), power=220.0, angle=50, blend=0.6, color=_WORK)
      for x in _WALL_CANS],
    # linear pendant over the breakfast table (underside 1.7 m): down, and a glow on the ceiling
    dict(kind="area", pos=(-4.5, 3.0, 1.69), size=(1.5, 0.05), aim=(-4.5, 3.0, 0.0), power=130.0, color=(1.0, 0.8, 0.58)),
    dict(kind="area", pos=(-4.5, 3.0, 1.76), size=(1.5, 0.05), aim=(-4.5, 3.0, 4.2), power=30.0, color=(1.0, 0.8, 0.58)),
    # nook lamp and the two canvases
    dict(kind="point", pos=(6.3, 2.2, 1.42), power=80.0, color=(1.0, 0.76, 0.5)),
    dict(kind="spot", pos=(-7.9, 3.55, 4.08), aim=(-8.8, 3.55, 1.6), power=120.0, angle=32, blend=0.5),
    dict(kind="spot", pos=(7.9, 2.8, 4.08), aim=(8.8, 2.8, 1.6), power=120.0, angle=32, blend=0.5),
]

PROBE = (1.0, 1.0, 1.6)

# the real bake came out darker than the EEVEE previews the lights were tuned on: lift them all
LIGHTS = [dict(L, power=L["power"] * 1.45) for L in LIGHTS]
