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
    # (north of centre: its south edge clears the door's sconces by 0.35 m)
    ("entry_bench", (-7.60, 0.8), 90),
    ("entry_artwork", (-7.85, 0.8, 3.35), 90),
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
    # --- lighting (see LIGHTS): bronze cove ledges high on the side walls, opal sconces
    #     either side of the two doors, a reading lamp in the nook
    ("light_g_cove", (-7.85, -2.0, 5.2), 90),
    ("light_g_cove", (-7.85, 2.0, 5.2), 90),
    ("light_g_cove", (7.85, -2.0, 5.2), -90),
    ("light_g_cove", (7.85, 2.0, 5.2), -90),
    ("entry_sconce", (-7.85, -3.3, 2.35), 90),          # tube 2.12..2.58 m, clear of heads
    ("entry_sconce", (-7.85, -1.25, 2.35), 90),
    ("entry_sconce", (7.85, -3.3, 2.35), -90),
    ("entry_sconce", (7.85, -1.25, 2.35), -90),
    ("library_floorlamp", (-5.4, -3.75), 0),
]

# Lighting: the orb cascade is the brightest thing in the hall; the floating stair is lit
# tread by tread (an LED under each tread lights the one below); high bronze ledges on the
# side walls wash the ceiling and graze down over the painting and the ink canvas; opal
# sconces mark the two doors; a lamp pools light in the nook. Daylight does the rest.
_RISE, _RUN = 4.6 / 26, 7.5 / 25          # plan.STAIR: 26 risers from x -6.0 to the landing at 1.5
LIGHTS = [
    # chandelier: inside the cloud of orbs (3.55..6.3 m)
    dict(kind="point", pos=(0.0, -0.3, 6.4), power=300.0, color=(1.0, 0.82, 0.58)),
    dict(kind="point", pos=(0.0, -0.3, 5.2), power=700.0, color=(1.0, 0.80, 0.55)),
    dict(kind="point", pos=(0.0, -0.3, 4.2), power=420.0, color=(1.0, 0.80, 0.55)),
    # cove ledges (z 5.2): up-light washing the upper walls and ceiling, down-light grazing the walls
    dict(kind="area", pos=(-7.77, 0.0, 5.27), size=(7.8, 0.08), aim=(-7.3, 0.0, 8.4), power=420.0, color=(1.0, 0.84, 0.66)),
    dict(kind="area", pos=(7.77, 0.0, 5.27), size=(7.8, 0.08), aim=(7.3, 0.0, 8.4), power=420.0, color=(1.0, 0.84, 0.66)),
    dict(kind="area", pos=(-7.75, 0.0, 5.17), size=(7.8, 0.08), aim=(-7.2, 0.0, 2.5), power=300.0, color=(1.0, 0.82, 0.62)),
    dict(kind="area", pos=(7.75, 0.0, 5.17), size=(7.8, 0.08), aim=(7.2, 0.0, 2.5), power=260.0, color=(1.0, 0.82, 0.62)),
    dict(kind="spot", pos=(7.72, -0.3, 5.15), aim=(7.2, -0.3, 1.4), power=250.0, angle=28, blend=0.5),   # the trefoil
    # opal sconces at the doors (in front of the tube, 0.095 m off the wall)
    dict(kind="point", pos=(-7.6, -3.3, 2.35), power=60.0, color=(1.0, 0.80, 0.55)),
    dict(kind="point", pos=(-7.6, -1.25, 2.35), power=60.0, color=(1.0, 0.80, 0.55)),
    dict(kind="point", pos=(7.6, -3.3, 2.35), power=60.0, color=(1.0, 0.80, 0.55)),
    dict(kind="point", pos=(7.6, -1.25, 2.35), power=60.0, color=(1.0, 0.80, 0.55)),
    # nook reading lamp (shade centre 1.42 m)
    dict(kind="point", pos=(-5.4, -3.75, 1.42), power=80.0, color=(1.0, 0.76, 0.5)),
    # under the landing: a soft glow over the way into the gallery
    dict(kind="area", pos=(3.0, 3.4, 4.37), size=(2.8, 2.2), aim=(3.0, 3.4, 0.0), power=90.0, color=(1.0, 0.84, 0.66)),
] + [
    # under each stair tread (0.06 m thick), lighting the tread below
    dict(kind="area", pos=(-6.0 + (i + 0.5) * _RUN, 3.4, _RISE * (i + 1) - 0.075), size=(0.2, 2.2),
         aim=(-6.0 + (i + 0.5) * _RUN, 3.4, 0.0), power=8.0, color=(1.0, 0.84, 0.66))
    for i in range(25)
]

PROBE = (0.0, -0.5, 3.0)
