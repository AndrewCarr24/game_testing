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
    # lighting (see LIGHTS): a linear pendant over the prep table
    ("light_g_pendant_linear", (0.0, -1.9, 4.2), 90),
]

# Lighting: the back kitchen is a working room, so it keeps two slim ceiling lines (the only
# room on this floor besides the garage that does); everything else is task light where the
# work is: LEDs under each open shelf of the sink run, the pantries' glass cabinets lit from
# inside, the coffee niche's soffit LED, and a linear pendant over the walnut prep table.
_WORK = (1.0, 0.88, 0.74)
LIGHTS = [
    dict(kind="strip", pos=(-1.0, 0.0), size=(0.08, 7.5), power=160.0),
    dict(kind="strip", pos=(1.0, 0.0), size=(0.08, 7.5), power=160.0),
    # under the three open shelves of the sink run (LED 0.03 behind the shelf fronts)
    *[dict(kind="area", pos=(0.0, 4.32, z - 0.03), size=(4.9, 0.03), aim=(0.0, 4.2, 0.0), power=28.0, color=_WORK)
      for z in (1.50, 1.95, 2.40)],
    # glass cabinets in the two pantries, lit from inside, out through the glass
    dict(kind="area", pos=(-2.12, 2.45, 1.35), size=(0.8, 1.6), aim=(0.0, 2.45, 1.35), power=25.0, color=(1.0, 0.82, 0.6)),
    dict(kind="area", pos=(-2.12, -3.1, 1.35), size=(0.8, 1.6), aim=(0.0, -3.1, 1.35), power=25.0, color=(1.0, 0.82, 0.6)),
    # coffee niche soffit LED (niche top 2.05)
    dict(kind="area", pos=(2.48, -3.1, 2.03), size=(0.05, 1.6), aim=(2.48, -3.1, 0.0), power=35.0, color=(1.0, 0.82, 0.6)),
    # linear pendant over the prep table (underside 1.7 m)
    dict(kind="area", pos=(0.0, -1.9, 1.69), size=(0.05, 1.5), aim=(0.0, -1.9, 0.0), power=120.0, color=(1.0, 0.8, 0.58)),
    dict(kind="area", pos=(0.0, -1.9, 1.76), size=(0.05, 1.5), aim=(0.0, -1.9, 4.2), power=25.0, color=(1.0, 0.8, 0.58)),
]

PROBE = (0.0, 0.0, 1.6)

# set dressing (decor_b_*): bread, spoons, bowls and lemons on the butcher-block run, a dish
# rack on the drainer, soap and brush by the sink
PLACEMENTS += [
    ("decor_b_vignette_bread", (0.0, -4.30, 0.92), 180),
    ("decor_b_dish_rack", (0.64, 4.28, 0.92), 0),
    ("decor_b_sink_set", (-1.25, 4.38, 0.92), 0),
]
