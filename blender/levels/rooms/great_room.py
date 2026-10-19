"""Great room (ground floor, west): 12.2 x 20.7 m inside, double height (8.4 m).
Full-height glass on the west wall, two openings to the gallery on the east wall (y -5.5..-1.5
and +1.5..5.5), an opening to the dining room at the north (x -3.25..2.75), the den door
at the south (x = 0). Local coords: (0, 0) = room centre, +x east, +y north.

Three seating groups: a fireplace group facing the east feature wall, a window lounge in
the north-west and a conversation group in the south-west, with consoles, art, sculpture and
plants on the north and south flanks."""
import importlib
import os
import sys

from lib import common, materials, textures

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets"))
import living_fireplace  # noqa: E402

importlib.reload(living_fireplace)


def _floor():
    return living_fireplace.limestone()


FINISHES = dict(
    floor=_floor,
    floor_uv_tile=living_fireplace.TILE,
    walls=lambda: common.pbr_material("M_Plaster_Living", (0.52, 0.47, 0.40), roughness=0.92),
    ceiling=lambda: common.pbr_material("M_Ceiling_Living", (0.60, 0.575, 0.54), roughness=0.9),
    walls_by_side={"S": lambda: common.pbr_material("M_Plaster_LivingClay", (0.27, 0.20, 0.155), roughness=0.95)},
)

PLACEMENTS = [
    # ---- A: fireplace group, facing the east feature wall -------------------------
    ("living_fireplace", (5.74, 0.0), -90),
    ("living_chandelier", (-1.0, 0.5, 8.4), 0),
    ("living_rug", (2.0, 0.0), 0),
    ("living_sofa", (-0.1, 0.0), 90),
    ("living_coffee_round", (1.9, 0.0), 0),
    ("vase", (1.9, 0.15, 0.36), 0),
    ("living_armchair_cognac", (2.0, 2.15), 0),
    ("living_armchair_cognac", (2.0, -2.15), 180),
    ("living_side_table", (-0.1, 1.75), 0),
    ("living_side_table", (-0.1, -1.75), 0),
    ("living_table_lamp", (-0.1, 1.75, 0.55), 0),
    ("living_table_lamp", (-0.1, -1.75, 0.55), 0),
    ("living_console", (-0.85, 0.0), -90),            # behind the sofa, dividing the room
    ("living_table_lamp", (-0.85, -0.6, 0.82), 0),
    ("living_table_lamp", (-0.85, 0.6, 0.82), 0),
    # ---- B: window lounge, north-west -----------------------------------------------
    ("living_rug_b", (-3.4, 6.3), 90),
    ("living_sofa_ink", (-1.95, 6.3), -90),
    ("coffee_table", (-3.6, 6.3), 90),
    ("living_armchair", (-3.7, 4.55), 180),
    ("living_armchair", (-3.7, 8.05), 0),
    ("living_floor_lamp", (-1.15, 7.1), -90),
    ("living_side_table", (-1.95, 7.95), 0),
    # ---- C: conversation group, south-west --------------------------------------------
    ("living_rug", (-3.4, -6.5), 0),
    ("living_sofa", (-3.4, -4.9), 0),
    ("living_sofa_ink", (-3.4, -8.15), 180),
    ("living_coffee_round", (-3.4, -6.65), 0, ),
    ("living_ottoman", (-5.35, -6.65), 0),
    ("living_armchair_cognac", (-1.1, -6.65), -90),
    ("living_floor_lamp", (-4.3, -4.0), 0),
    ("living_side_table", (-1.85, -8.2), 0),
    ("living_table_lamp", (-1.85, -8.2, 0.55), 0),
    ("living_art_tall", (-4.3, -10.34, 2.5), 180),            # black brush bars, 1.5 x 2.3 canvas
    ("art_pencil_grid", (-2.45, -10.34, 1.9), 180),          # pencil grid, bottoms aligned with the tall canvas
    # ---- south wall, east of the den door: console, art, plant ---------------------------
    ("living_console", (3.3, -10.14), 180),
    ("living_art_large", (3.3, -10.34, 2.0), 180),           # seascape photograph over the console
    ("library_plant", (1.6, -9.9), 0),
    ("vase", (2.6, -10.14, 0.82), 0),
    # ---- east wall, either side of the fireplace -----------------------------------------------
    ("living_console", (5.89, 8.2), -90),
    ("art_blocks_umber", (6.09, 8.2, 2.05), -90),           # painterly blocks, floater frame
    ("living_plant_olive", (5.4, 6.3), 0),
    ("living_console", (5.89, -7.9), -90),
    ("art_curve_vermilion", (6.09, -7.9, 2.05), -90),       # one vermilion curve
    ("living_sculpture", (5.4, -5.95), 0),
    # ---- north wall flanks (the dining opening is x -3.25..2.75) -----------------------------
    ("living_console", (4.0, 10.14), 0),
    ("art_mono_ultramarine", (4.0, 10.34, 2.15), 0),        # ultramarine monochrome
    ("living_console", (-4.45, 10.14), 0),
    ("art_weave_indigo", (-4.45, 10.34, 2.15), 0),          # woven blocks
    ("library_plant", (-5.55, 2.6), 0),
    # ---- lighting (see LIGHTS): bronze ledges across the two end walls at 4.3 m, ceiling
    #      cans grazing the chimney breast and lighting the east-wall art
    ("light_g_cove", (-4.0, 10.35, 4.3), 0),
    ("light_g_cove", (0.0, 10.35, 4.3), 0),
    ("light_g_cove", (4.0, 10.35, 4.3), 0),
    ("light_g_cove_down", (-4.0, -10.35, 4.45), 180),
    ("light_g_cove_down", (0.0, -10.35, 4.45), 180),
    ("light_g_cove_down", (4.0, -10.35, 4.45), 180),
    ("light_g_downlight", (5.3, 0.9, 8.4), 0),
    ("light_g_downlight", (5.3, -0.9, 8.4), 0),
    ("light_g_downlight", (4.9, 8.2, 8.4), 0),
    ("light_g_downlight", (4.9, -7.9, 8.4), 0),
]

# Lighting: the fire and the cascade chandelier are the heart of the room; the stone chimney
# breast is grazed from two ceiling cans so it glows to the top; every lamp is lit, so each
# seating group sits in its own warm pool; bronze ledges across the north and south walls
# wash them (the north one also throws light up the wall to the ceiling, the south one only
# down: the clerestory is above it). No ceiling lines; the west glass brings the daylight.
LIGHTS = [
    dict(kind="point", pos=(-1.0, 0.5, 6.3), power=450.0, color=(1.0, 0.82, 0.6)),      # chandelier, upper drops
    dict(kind="point", pos=(-1.0, 0.5, 5.3), power=500.0, color=(1.0, 0.80, 0.56)),     # chandelier, lower drops
    dict(kind="point", pos=(5.2, 0.0, 1.0), power=180.0, color=(1.0, 0.55, 0.25)),      # fire
    dict(kind="point", pos=(-2.55, 7.1, 1.8), power=150.0, color=(1.0, 0.75, 0.5)),     # arc lamp B
    dict(kind="point", pos=(-4.3, -5.4, 1.8), power=150.0, color=(1.0, 0.75, 0.5)),     # arc lamp C
    # table lamps (shade centres): sofa ends, the console behind the sofa, group C
    dict(kind="point", pos=(-0.1, 1.75, 1.0), power=60.0, color=(1.0, 0.76, 0.5)),
    dict(kind="point", pos=(-0.1, -1.75, 1.0), power=60.0, color=(1.0, 0.76, 0.5)),
    dict(kind="point", pos=(-0.85, 0.6, 1.27), power=55.0, color=(1.0, 0.76, 0.5)),
    dict(kind="point", pos=(-0.85, -0.6, 1.27), power=55.0, color=(1.0, 0.76, 0.5)),
    dict(kind="point", pos=(-1.85, -8.2, 1.0), power=60.0, color=(1.0, 0.76, 0.5)),
    # chimney breast grazers and the east-wall art (cans at 8.4 m)
    dict(kind="spot", pos=(5.3, 0.9, 8.33), aim=(5.45, 0.9, 1.2), power=900.0, angle=24, blend=0.5),
    dict(kind="spot", pos=(5.3, -0.9, 8.33), aim=(5.45, -0.9, 1.2), power=900.0, angle=24, blend=0.5),
    dict(kind="spot", pos=(4.9, 8.2, 8.33), aim=(6.05, 8.2, 2.05), power=650.0, angle=18, blend=0.4),
    dict(kind="spot", pos=(4.9, -7.9, 8.33), aim=(6.05, -7.9, 2.05), power=650.0, angle=18, blend=0.4),
    # north ledge (z 4.3): up the wall to the ceiling, and down over the consoles and art
    dict(kind="area", pos=(0.0, 10.27, 4.37), size=(11.8, 0.08), aim=(0.0, 9.6, 8.4), power=550.0, color=(1.0, 0.84, 0.66)),
    dict(kind="area", pos=(0.0, 10.25, 4.27), size=(11.8, 0.08), aim=(0.0, 9.4, 1.0), power=450.0, color=(1.0, 0.82, 0.62)),
    # south ledge (z 4.45, lip down): down the clay wall and its art
    dict(kind="area", pos=(0.0, -10.27, 4.38), size=(11.8, 0.08), aim=(0.0, -9.4, 1.0), power=500.0, color=(1.0, 0.82, 0.62)),
]

PROBE = (-3.0, 0.0, 1.6)
