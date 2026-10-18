"""Primary bath (upper floor, between the primary bedroom and the office): 9.7 x 9.2 m
inside, no windows. The door is on the west wall at y = +1.75 (swings in).

Book-matched marble: the floor is 1.2 m Calacatta-style slabs with hairline joints; the
walls (lightmapped shell linings) use the same mirrored book-match texture at 2.4 m per
repeat, pale on the north / south / west walls and dark Marquina-style on the east wall
behind the freestanding stone tub (the view from the door). Double vanity with
three sconces and two mirrors on the north wall, a walk-in shower in the south-east
corner, a water closet behind a marble screen in the south-west corner, a towel warmer by
the shower, a daybed and artwork on the south wall.
"""
import importlib
import os
import sys

from lib import common

HERE = os.path.dirname(os.path.abspath(__file__))
_assets = os.path.abspath(os.path.join(HERE, "..", "..", "assets"))
if _assets not in sys.path:
    sys.path.insert(0, _assets)
import bath_common as bc  # noqa: E402

importlib.reload(bc)


def _ceiling():
    return common.pbr_material("M_Ceiling_Bath", (0.70, 0.68, 0.64), roughness=0.85)


FINISHES = dict(
    floor=bc.marble_floor,
    floor_uv_tile=2.4,
    walls=bc.marble_wall,               # book-matched slabs: 2.4 m per texture repeat (mirrored every 1.2 m)
    wall_uv_tile=2.4,
    ceiling=_ceiling,
    walls_by_side={"E": bc.marble_dark},
)

# wall faces are at the limits (x +-4.85, y +-4.60)
WN, WS, WE, WW = 4.60, -4.60, 4.85, -4.85
VX = -0.40            # vanity centre
ART_Z = 1.65

PLACEMENTS = [
    # --- north wall: double vanity, two pill mirrors, three sconces
    ("bath_vanity", (VX, WN - 0.29), 0),
    ("bath_mirror", (VX - 0.76, WN, 1.90), 0),
    ("bath_mirror", (VX + 0.76, WN, 1.90), 0),
    ("bath_sconce", (VX, WN, 1.90), 0),
    ("bath_sconce", (VX - 1.80, WN, 1.90), 0),
    ("bath_sconce", (VX + 1.80, WN, 1.90), 0),
    ("vase", (VX, WN - 0.29, 0.80), 0),
    ("bath_mat", (VX, 3.45), 0),
    # --- east wall: freestanding tub on the axis of the door, sconces either side
    ("bath_tub", (3.72, 1.75), 90),
    ("bath_mat", (2.90, 1.75), 90),
    ("bath_stool", (3.72, 0.42), 0),
    ("bath_sconce", (WE, 0.35, 1.70), -90),
    ("bath_sconce", (WE, 3.15, 1.70), -90),
    ("bath_pendant", (3.72, 1.75, 3.80), 0),
    ("bath_plant", (4.10, 3.90), 20),
    # --- south-east corner: walk-in shower (back wall = east wall), towel warmer
    ("bath_shower", (WE - 0.95, -3.50), -90),
    ("bath_towel_warmer", (1.75, WS, 1.05), 180),
    # --- south-west corner: water closet behind a marble screen
    ("bath_toilet", (WW + 0.14, -3.60), 90),
    # --- south wall between: daybed under a large artwork
    ("bath_daybed", (-0.70, WS + 0.45), 180),
    ("art_colorfield_b", (-0.70, WS, ART_Z), 180),
    ("bath_plant", (-2.35, -3.95), 150),
]

LIGHTS = [
    dict(kind="strip", pos=(VX, 3.55), size=(4.2, 0.08), power=110.0),       # wash on the vanity wall
    dict(kind="strip", pos=(2.2, 0.0), size=(0.08, 5.0), power=95.0),       # along the tub side
    dict(kind="strip", pos=(-1.2, -1.2), size=(5.0, 0.08), power=90.0),     # general light
    dict(kind="point", pos=(VX, 4.40, 2.10), power=45.0, color=(1.0, 0.74, 0.48)),     # vanity sconces
    dict(kind="point", pos=(3.72, 1.75, 2.50), power=70.0, color=(1.0, 0.76, 0.52)),   # pendant over the tub
    dict(kind="point", pos=(3.9, -3.5, 3.2), power=45.0, color=(1.0, 0.78, 0.55)),     # in the shower
]

PROBE = (-0.5, 0.0, 1.6)
