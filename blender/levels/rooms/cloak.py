"""Cloakroom (ground floor, east of the entry): 5.2 x 9.2 m inside, 4.2 m high. The door is
on the west wall at y -2.8..-1.7 and swings in (keep x -2.6..-1.3, y -3..-0.5 clear).

Four built-in walnut coat closets (two along the north wall, two along the east wall),
a full-length mirror between sconces on the west wall, a long leather bench on a rug in
the middle, a bench and a painting on the south wall. Smoked oak floor, warm plaster.
Local coords: (0, 0) = room centre; +x east, +y north.
"""
from lib import common, textures


def _floor():
    m = common.pbr_material("M_OakFloor_Smoked", (0.08, 0.055, 0.035), roughness=0.75, coat=0.0)
    common.set_base_color_map(m, textures.load(textures.wood(
        "T_OakFloorSmoked_BaseColor", dark=(0.030, 0.020, 0.013), light=(0.095, 0.066, 0.043), rings=30, seed=31)))
    return m


FINISHES = dict(
    floor=_floor,
    walls=lambda: common.pbr_material("M_Plaster_Cloak", (0.50, 0.45, 0.385), roughness=0.92),
    ceiling=lambda: common.pbr_material("M_Ceiling_Warm", (0.48, 0.46, 0.43), roughness=0.9),
)

PLACEMENTS = [
    # --- north wall: two closets
    ("entry_coat_closet", (-1.2, 4.29), 0),
    ("entry_coat_closet", (1.2, 4.29), 0),
    # --- east wall: two closets facing west
    ("entry_coat_closet", (2.29, 2.65), -90),
    ("entry_coat_closet", (2.29, 0.2), -90),
    # --- west wall: full-length mirror between sconces
    ("entry_mirror_tall", (-2.6, 1.2, 1.25), 90),
    ("entry_sconce", (-2.6, 0.2, 1.75), 90),
    ("entry_sconce", (-2.6, 2.2, 1.75), 90),
    # --- the middle: rug and a long bench
    ("rug", (-0.3, 0.7), 90),
    ("entry_bench", (-0.3, 0.7), 90),
    # --- south: bench and painting
    ("bench", (0.4, -4.37), 180),
    ("art_colorfield_b", (0.4, -4.6, 1.75), 180),
]

LIGHTS = [
    dict(kind="strip", pos=(-0.6, 0.3), size=(0.08, 7.0), power=200.0),
    dict(kind="strip", pos=(0.0, 3.3), size=(4.4, 0.08), power=110.0),
    dict(kind="strip", pos=(0.0, -3.2), size=(3.4, 0.08), power=100.0),
    dict(kind="point", pos=(-2.3, 0.2, 1.75), power=45.0, color=(1.0, 0.78, 0.5)),
    dict(kind="point", pos=(-2.3, 2.2, 1.75), power=45.0, color=(1.0, 0.78, 0.5)),
]
