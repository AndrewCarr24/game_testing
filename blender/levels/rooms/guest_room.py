"""Guest suite (upper floor, east wing): 12.2 x 10.2 m inside, floor-to-ceiling glass on
the east wall (y -3.75..3.75), door on the west wall at y -2.3..-1.2. Palette: pale
oak, white linen, sage. The bed's headboard is on the sage west wall, foot toward the
glass; a reading corner by the window, a writing desk on the south wall, a dresser on
the north wall."""
import importlib

from lib import common, materials, textures

importlib.reload(materials)


def _floor():
    m = common.pbr_material("M_OakFloor_Pale", (0.42, 0.30, 0.18), roughness=0.6, coat=0.0)
    common.set_base_color_map(m, textures.load(textures.wood(
        "T_OakFloorPale_BaseColor", dark=(0.27, 0.18, 0.10), light=(0.56, 0.41, 0.25), rings=26, seed=47)))
    return m


FINISHES = dict(
    floor=_floor,
    floor_uv_tile=1.0,
    walls=lambda: common.pbr_material("M_Plaster_Linen", (0.52, 0.49, 0.43), roughness=0.92),
    ceiling=lambda: common.pbr_material("M_Ceiling_Warm", (0.48, 0.46, 0.43), roughness=0.9),
    walls_by_side={"W": lambda: common.pbr_material("M_Plaster_Sage", (0.17, 0.235, 0.15), roughness=0.92)},
)

PLACEMENTS = [
    # sleeping zone: headboard on the sage west wall
    ("guest_rug", (-3.3, 1.8), 0),
    ("guest_bed", (-4.99, 1.8), 90),
    ("guest_nightstand", (-5.88, 3.18), 90),
    ("guest_nightstand", (-5.88, 0.42), 90),
    ("table_lamp", (-5.88, 3.18, 0.52), 0),
    ("table_lamp", (-5.88, 0.42, 0.52), 0),
    ("guest_bench", (-3.5, 1.8), 90),
    ("art_linework_a", (-6.09, 1.8, 1.95), 90),
    # writing desk on the south wall
    ("guest_desk", (-1.6, -4.74), 180),
    ("guest_chair", (-1.6, -4.05), 0),
    ("art_geometric_a", (-1.6, -5.09, 1.75), 180),
    ("library_plant", (-4.3, -4.4), 0),
    # dresser on the north wall, with a vase and art
    ("guest_dresser", (-2.2, 4.86), 0),
    ("vase", (-2.9, 4.86, 0.80), 0),
    ("art_colorfield_a", (-2.2, 5.09, 1.7), 0),
    # reeded wardrobe wall
    ("guest_wardrobe", (3.0, 4.78), 0),
    # reading corner by the glass
    ("guest_rug_small", (3.9, 1.8), 0),
    ("guest_armchair", (3.4, 2.9), 40),
    ("guest_armchair", (3.4, 0.7), 140),
    ("guest_side_table", (4.35, 1.8), 0),
    ("guest_floor_lamp", (2.45, 0.0), 0),
    ("library_plant", (4.3, -4.4), 0),
    # curtains gathered at the ends of the glass
    ("guest_curtain", (5.93, 4.4), -90),
    ("guest_curtain", (5.93, -4.4), -90),
]

LIGHTS = [
    dict(kind="strip", pos=(-3.0, 0.5), size=(0.08, 6.0), power=90.0),
    dict(kind="strip", pos=(1.5, -4.0), size=(7.0, 0.08), power=90.0),
    dict(kind="strip", pos=(3.5, 1.8), size=(4.0, 0.08), power=60.0),
    dict(kind="point", pos=(-5.88, 3.18, 0.97), power=45.0, color=(1.0, 0.72, 0.45)),
    dict(kind="point", pos=(-5.88, 0.42, 0.97), power=45.0, color=(1.0, 0.72, 0.45)),
    dict(kind="point", pos=(2.45, 0.0, 1.4), power=40.0, color=(1.0, 0.76, 0.5)),
]
