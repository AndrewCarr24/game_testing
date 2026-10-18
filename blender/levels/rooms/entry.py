"""Entry hall (ground floor, double height): 15.7 x 9.2 m inside, 8.4 m to the roof, the
8.4 m glass front on the south wall (y = -4.6, x -6..6). Doors to the powder room (west)
and cloakroom (east) at y -2.8..-1.7; opening to the gallery in the north wall at
x 2.5..7; the floating stair runs along the north wall (x -6..4.5, y 2.2..4.6), entered
from its west end (x < -6).

Zones: a round marble table under the chandelier on the axis of the front door/stair,
a leather bench under a monumental painting on the west wall, a bronze trefoil on a
limestone plinth against the east wall, a seating nook by the glass.
Local coords: (0, 0) = room centre; +x east, +y north.
"""
import importlib
import os
import sys

from lib import common

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets"))
import entry_sculpture  # noqa: E402  (shares the limestone material)

importlib.reload(entry_sculpture)


def _plaster(name, colour):
    return lambda: common.pbr_material(name, colour, roughness=0.92)


FINISHES = dict(
    floor=entry_sculpture.limestone_material,
    floor_uv_tile=2.0,
    walls=_plaster("M_Plaster_Entry", (0.56, 0.52, 0.46)),
    ceiling=_plaster("M_Ceiling_Entry", (0.58, 0.56, 0.52)),
    walls_by_side={"N": _plaster("M_Plaster_Entry_Greige", (0.30, 0.265, 0.225))},
)

PLACEMENTS = [
    # --- the centre of the hall: marble table, flowers, chandelier overhead
    ("entry_rug_round", (0.0, -0.3), 0),
    ("entry_round_table", (0.0, -0.3), 0),
    ("entry_flowers", (0.0, -0.3, 0.80), 0),
    ("entry_chandelier", (0.0, -0.3), 0),
    # --- west wall: bench under the monumental painting
    ("entry_bench", (-7.60, 0.0), 90),
    ("entry_artwork", (-7.85, 0.0, 3.35), 90),
    # --- east wall: sculpture on its plinth
    ("entry_sculpture", (7.2, -0.3), 0),
    # --- south-west nook by the glass
    ("entry_tree", (-6.95, -3.85), 0),
    ("entry_tree", (6.95, -3.85), 0),
    ("entry_artwork_ink", (7.85, 2.6, 3.4), -90),
    ("rug", (-4.3, -2.35), 0),
    ("coffee_table", (-4.3, -2.35), 0),
    ("lounge_chair", (-4.3, -3.55), 180),
    ("lounge_chair", (-4.3, -1.15), 0),
]

LIGHTS = [
    dict(kind="strip", pos=(0.0, -1.6), size=(12.0, 0.10), power=300.0),
    dict(kind="strip", pos=(0.0, 1.2), size=(12.0, 0.10), power=240.0),
    dict(kind="point", pos=(0.0, -0.3, 5.3), power=450.0, color=(1.0, 0.80, 0.55)),
    dict(kind="point", pos=(0.0, -0.3, 4.2), power=240.0, color=(1.0, 0.80, 0.55)),
    dict(kind="point", pos=(-6.2, 0.0, 5.6), power=200.0, color=(1.0, 0.82, 0.60)),   # washes the painting
    dict(kind="point", pos=(6.2, -0.3, 4.2), power=100.0, color=(1.0, 0.80, 0.55)),   # sculpture
]

PROBE = (0.0, -0.5, 3.0)
