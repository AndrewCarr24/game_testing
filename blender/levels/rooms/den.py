"""Den / media room (ground floor, south-west): 12.2 x 9.2 m inside, no windows, 4.2 m
ceiling. The door to the great room is in the north wall at x = 0. The screen wall is the
south wall (y = -4.6). Smoked-oak floor, deep green fabric walls, a dark warm ceiling.
Local coords: (0, 0) = room centre, +x east, +y north."""
import importlib

from lib import common, materials, textures

importlib.reload(materials)


def _floor():
    m = common.pbr_material("M_OakFloor_Smoked", (0.08, 0.055, 0.035), roughness=0.75, coat=0.0)
    common.set_base_color_map(m, textures.load(textures.wood(
        "T_OakFloorSmoked_BaseColor", dark=(0.030, 0.020, 0.013), light=(0.095, 0.066, 0.043), rings=30, seed=31)))
    return m


FINISHES = dict(
    floor=_floor,
    walls=lambda: materials.fabric("M_Fabric_DenGreen", (0.026, 0.058, 0.040)),
    ceiling=lambda: common.pbr_material("M_Ceiling_Den", (0.11, 0.10, 0.092), roughness=0.9),
    walls_by_side={"S": lambda: materials.fabric("M_Fabric_DenGreen", (0.026, 0.058, 0.040))},
)

PLACEMENTS = [
    # ---- screen wall (south) ----------------------------------------------------------
    ("living_media_wall", (0.0, -4.34), 180),
    # ---- seating: the sectional faces the screen -----------------------------------------
    ("living_rug_den", (0.0, -0.8), 0),
    ("living_sectional", (-0.6, 0.6), 0),
    ("living_ottoman", (-0.7, -1.9), 0),
    ("vase", (-0.7, -1.9, 0.44), 0),
    ("living_side_table", (-3.3, 1.2), 0),
    ("living_table_lamp", (-3.3, 1.2, 0.55), 0),
    ("living_side_table", (2.2, 1.2), 0),
    ("living_table_lamp", (2.2, 1.2, 0.55), 0),
    ("living_floor_lamp", (-2.2, 2.1), 0),
    ("living_armchair_cognac", (3.7, -0.5), -40),
    ("living_armchair_cognac", (4.5, 1.8), -75),
    ("living_side_table", (4.3, 0.55), 0),
    # ---- west wall: shelving ------------------------------------------------------------------
    ("living_shelving", (-5.9, -1.9), 90),
    ("living_shelving", (-5.9, 1.9), 90),
    # ---- east wall: bar console and art --------------------------------------------------------
    ("living_console", (5.85, 3.0), -90),
    ("art_colorfield_b", (6.09, 3.0, 1.8), -90),
    ("vase", (5.85, 3.6, 0.82), 0),
    # ---- corners ---------------------------------------------------------------------------------
    ("library_plant", (4.9, -2.8), 0),
    ("library_plant", (-4.9, -2.8), 0),
    # ---- north wall flanks (the door is at x = 0) ---------------------------------------------
    ("living_console", (-3.4, 4.39), 0),
    ("living_art_tall", (-3.4, 4.59, 2.2), 0),
    ("living_plant_olive", (3.6, 3.95), 0),
]

LIGHTS = [
    dict(kind="strip", pos=(0.0, -1.0), size=(7.0, 0.08), power=340.0),
    dict(kind="strip", pos=(0.0, 2.8), size=(7.0, 0.08), power=240.0),
    dict(kind="point", pos=(0.0, -3.3, 1.7), power=70.0, color=(1.0, 0.75, 0.5)),
    dict(kind="point", pos=(-3.3, 1.2, 1.2), power=40.0, color=(1.0, 0.72, 0.45)),
    dict(kind="point", pos=(2.2, 1.2, 1.2), power=40.0, color=(1.0, 0.72, 0.45)),
    dict(kind="point", pos=(-2.2, 0.7, 1.8), power=60.0, color=(1.0, 0.75, 0.5)),
]

PROBE = (0.0, -1.2, 1.6)
