"""Primary bedroom (upper floor, north-west): 15.7 x 9.2 m inside, north wall glazed
(x -6..6). Gallery door on the south wall at x = +6.25 (locked: keycard), bath door on
the east wall (x = +7.85) at y = +1.75. The bed's headboard wall (west) is ink blue.
Zones: sleeping (west), a sitting area by the glass (east), dressing along the south wall."""
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
    walls=lambda: common.pbr_material("M_Plaster_Stone", (0.36, 0.335, 0.30), roughness=0.92),
    ceiling=lambda: common.pbr_material("M_Ceiling_Warm", (0.48, 0.46, 0.43), roughness=0.9),
    walls_by_side={"W": lambda: common.pbr_material("M_Plaster_Ink", (0.035, 0.045, 0.062), roughness=0.92)},
)

PLACEMENTS = [
    # sleeping
    ("bedroom_rug", (-5.6, 0.0), 90),
    ("bed", (-6.7, 0.0), 90),                # headboard against the west wall
    ("nightstand", (-7.6, 1.41), 90),
    ("nightstand", (-7.6, -1.41), 90),
    ("table_lamp", (-7.6, 1.41, 0.55), 0),
    ("table_lamp", (-7.6, -1.41, 0.55), 0),
    ("bench", (-5.25, 0.0), 90),
    ("art_linework_a", (-7.85, 0.0, 2.75), 90),          # above the headboard
    ("library_plant", (-7.1, 3.9), 0),
    # sitting area by the glass
    ("living_rug_b", (3.4, 1.2), 0),
    ("living_sofa_ink", (3.4, -0.3), 180),               # faces the window
    ("living_armchair", (2.2, 2.6), 0),
    ("living_armchair", (4.6, 2.6), 0),
    ("living_coffee_round", (3.4, 1.2), 0),
    ("living_floor_lamp", (5.6, -0.6), 180),
    ("library_plant", (7.1, 3.9), 0),
    ("art_colorfield_b", (7.85, -2.4, 1.7), -90),        # east wall, south of the bath door
    # dressing along the south wall
    ("wardrobe", (-1.4, -4.29), 180),
    ("wardrobe", (0.45, -4.29), 180),
    ("guest_desk", (3.4, -4.25), 180),                   # a writing desk / vanity
    ("guest_chair", (3.4, -3.55), 0),
    ("table_lamp", (2.85, -4.3, 0.74), 0),
]

LIGHTS = [
    dict(kind="point", pos=(-7.6, 1.41, 0.97), power=65.0, color=(1.0, 0.72, 0.45)),
    dict(kind="point", pos=(-7.6, -1.41, 0.97), power=65.0, color=(1.0, 0.72, 0.45)),
    dict(kind="strip", pos=(0.0, -3.9), size=(9.0, 0.08), power=180.0),   # wash on the wardrobe wall
    dict(kind="strip", pos=(-1.0, 0.8), size=(10.0, 0.08), power=260.0),  # general, along the room
    dict(kind="point", pos=(5.6, -0.6, 1.9), power=60.0, color=(1.0, 0.75, 0.48)),   # floor lamp
    dict(kind="point", pos=(2.85, -4.3, 1.15), power=40.0, color=(1.0, 0.72, 0.45)), # desk lamp
]
