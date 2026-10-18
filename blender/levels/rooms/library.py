"""Library (upper floor, north wing): 17.7 x 9.2 m inside, ceiling 3.8 m.
Local coords: (0, 0) = room centre. North wall: interior glass x -8.0..2.5 (looks down into
the great room) and the door at x = +6.25 (+5.7..+6.8); west wall glazed y -3.75..3.75.
Bookcases line the south wall, the east wall and the solid stretches of the north wall."""
import importlib

from lib import common, materials, textures

importlib.reload(materials)

D = 0.18          # half a bookcase's depth: the origin sits this far off the wall


def _floor():
    m = common.pbr_material("M_OakFloor_Smoked", (0.08, 0.055, 0.035), roughness=0.75, coat=0.0)
    common.set_base_color_map(m, textures.load(textures.wood(
        "T_OakFloorSmoked_BaseColor", dark=(0.030, 0.020, 0.013), light=(0.095, 0.066, 0.043), rings=30, seed=31)))
    return m


FINISHES = dict(
    floor=_floor,
    walls=lambda: common.pbr_material("M_Plaster_Library", (0.20, 0.17, 0.14), roughness=0.92),
    ceiling=lambda: common.pbr_material("M_Ceiling_Warm", (0.48, 0.46, 0.43), roughness=0.9),
)


def _run(seq, start, along, fixed, rot):
    """Place bookcases end to end. seq: [(asset, width)]; `along` is "x" or "y"."""
    out, cur = [], start
    for asset, w in seq:
        c = cur + w / 2
        out.append((asset, (c, fixed) if along == "x" else (fixed, c), rot))
        cur += w
    return out


A, B, C, S = "library_bookcase_a", "library_bookcase_b", "library_bookcase_c", "library_bookcase_s"
PLACEMENTS = (
    # south wall: 17.7 m of books, a single bay in the middle
    _run([(A, 2.36), (B, 2.36), (C, 2.36), (S, 1.18), (B, 2.36), (A, 2.36), (C, 2.36), (A, 2.36)],
         -8.85, "x", -4.6 + D, 180)
    # east wall
    + _run([(C, 2.36), (A, 2.36), (B, 2.36), (S, 1.18)], -4.15, "y", 8.85 - D, -90)
    # north wall, the solid stretches either side of the door
    + _run([(B, 2.36)], 2.65, "x", 4.6 - D, 0)
    + _run([(S, 1.18)], 7.28, "x", 4.6 - D, 0)

    # the reading table on the big rug (its long axis along x), six chairs and two lamps
    + [
        ("library_rug", (1.4, 0.0), 0),
        ("library_table", (1.4, 0.0), 0),
        ("library_chair", (0.45, 0.85), 0), ("library_chair", (1.4, 0.85), 0), ("library_chair", (2.35, 0.85), 0),
        ("library_chair", (0.45, -0.85), 180), ("library_chair", (1.4, -0.85), 180), ("library_chair", (2.35, -0.85), 180),
        ("library_lamp", (0.5, 0.12, 0.764), 0),
        ("library_lamp", (2.3, -0.12, 0.764), 180),
    ]
    # reading nook by the west glass: two armchairs round a side table and a lamp
    + [
        ("rug", (-6.8, 0.0), 90),
        ("library_armchair", (-6.5, 1.45), -65),
        ("library_armchair", (-6.5, -1.45), -115),
        ("library_sidetable", (-7.55, 0.0), 0),
        ("library_lamp", (-7.55, 0.0, 0.56), -90),
        ("library_floorlamp", (-5.5, 2.3), 0),
        # a sofa facing out through the interior glass into the great room
        ("library_sofa_navy", (-3.6, 3.85), 180),
        ("library_sidetable", (-5.25, 4.0), 0),
        ("library_lamp", (-5.25, 4.0, 0.564), 90),
        ("library_plant", (-1.6, 4.0), 0),
        # a collector's corner: globe, cognac reading chair, floor lamp
        ("library_globe", (6.3, -3.2), 0),
        ("library_armchair_cognac", (5.2, -1.6), -135),
        ("library_sidetable", (6.6, -1.9), 0),
        ("library_floorlamp", (7.8, -3.5), 0),
        # the ladder hangs from the south wall's rail
        ("library_ladder", (-3.7, -4.165), 180),
    ]
)

LIGHTS = [
    dict(kind="strip", pos=(-0.5, -2.3), size=(15.0, 0.08), power=572.0),
    dict(kind="strip", pos=(-2.0, 2.2), size=(10.0, 0.08), power=396.0),
    dict(kind="point", pos=(0.5, 0.12, 1.08), power=45.0, color=(1.0, 0.8, 0.5)),    # banker's lamps
    dict(kind="point", pos=(2.3, -0.12, 1.08), power=45.0, color=(1.0, 0.8, 0.5)),
    dict(kind="point", pos=(-7.55, 0.0, 0.88), power=55.0, color=(1.0, 0.72, 0.45)),  # nook table lamp
    dict(kind="point", pos=(-5.5, 2.3, 1.4), power=70.0, color=(1.0, 0.75, 0.48)),    # floor lamp
]
