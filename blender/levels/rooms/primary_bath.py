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
    ("art_shoreline", (-0.70, WS, ART_Z), 180),
    ("bath_plant", (-2.35, -3.95), 150),
]

# --- lighting --------------------------------------------------------------------------------
# A spa at night: the dark Marquina wall behind the tub is the stage, grazed by two downlights
# either side of the alabaster globe cluster, with the two wall sconces glowing on it. At the
# vanity the pill mirrors are backlit (a halo on the marble round each) between the three
# alabaster sconces, and the floating vanity has a toe-kick glow on the floor. Downlights wash
# the art over the daybed and light the shower and the water closet. No ceiling strips.
CEIL = 3.8
_DL = [(4.4, 1.05), (4.4, 2.45),          # tub wall grazers
       (-0.70, -3.85),                    # art over the daybed
       (3.9, -3.5),                       # shower
       (-3.95, -3.6),                     # water closet
       (VX, 2.2),                         # the middle of the room, in front of the vanity
       (1.3, -1.2)]                       # between the shower and the daybed
PLACEMENTS += [("light_u_downlight", (x, y, CEIL), 0) for x, y in _DL]

_WARM = (1.0, 0.76, 0.52)
LIGHTS = [
    # the five alabaster sconces (vanity trio, tub pair): a bulb in each light bar
    *[dict(kind="point", pos=(x, WN - 0.06, 1.90), power=50.0, color=_WARM) for x in (VX, VX - 1.80, VX + 1.80)],
    *[dict(kind="point", pos=(WE - 0.06, y, 1.70), power=50.0, color=_WARM) for y in (0.35, 3.15)],
    # backlit mirrors: a soft source behind each, facing the wall
    *[dict(kind="area", pos=(x, WN - 0.012, 1.90), size=(0.7, 1.05), aim=(x, WN, 1.90), power=100.0,
           color=(1.0, 0.84, 0.66)) for x in (VX - 0.76, VX + 0.76)],
    # toe-kick under the vanity (front of the plinth ~ y 4.09)
    dict(kind="area", pos=(VX, WN - 0.53, 0.09), size=(2.75, 0.04), aim=(VX, WN - 0.9, 0.0), power=85.0,
         color=(1.0, 0.84, 0.66)),
    # tub wall grazers, down the dark marble
    *[dict(kind="spot", pos=(4.4, y, CEIL - 0.03), aim=(WE, y, 0.8), power=370.0, angle=40.0, blend=0.7,
           color=(1.0, 0.82, 0.62)) for y in (1.05, 2.45)],
    # the alabaster pendant over the tub
    dict(kind="point", pos=(3.72, 1.75, 2.50), power=140.0, color=(1.0, 0.76, 0.52)),
    # art over the daybed, shower, water closet, the floor in front of the vanity
    dict(kind="spot", pos=(-0.70, -3.85, CEIL - 0.03), aim=(-0.70, WS, 1.5), power=340.0, angle=55.0, blend=0.75,
         color=(1.0, 0.82, 0.62)),
    dict(kind="spot", pos=(3.9, -3.5, CEIL - 0.03), aim=(3.9, -3.5, 0.0), power=240.0, angle=70.0, blend=0.8,
         color=(1.0, 0.84, 0.66)),
    dict(kind="spot", pos=(-3.95, -3.6, CEIL - 0.03), aim=(-3.95, -3.6, 0.0), power=160.0, angle=70.0, blend=0.8,
         color=(1.0, 0.84, 0.66)),
    dict(kind="spot", pos=(1.3, -1.2, CEIL - 0.03), aim=(1.3, -1.2, 0.0), power=380.0, angle=70.0, blend=0.8,
         color=(1.0, 0.84, 0.66)),
    dict(kind="spot", pos=(VX, 2.2, CEIL - 0.03), aim=(VX, 2.6, 0.0), power=400.0, angle=70.0, blend=0.8,
         color=(1.0, 0.84, 0.66)),
]

PROBE = (-0.5, 0.0, 1.6)

# the real bake came out darker than the EEVEE previews the lights were tuned on: lift them all
LIGHTS = [dict(L, power=L["power"] * 1.35) for L in LIGHTS]

# --- set dressing (decor_d_* assets; z = the surface each group stands on) --------------------
PLACEMENTS += [
    ("decor_d_vanity_tray", (VX - 0.29, WN - 0.20, 0.80), 0),    # walnut tray: pump, bottle, soap
    ("decor_d_vanity_towels", (VX + 1.22, WN - 0.30, 0.80), 0),  # hand towels + candle jar, right end
    ("decor_d_vanity_plant", (VX - 1.22, WN - 0.28, 0.80), 0),   # small plant + candle, left end
    ("decor_d_tub_caddy", (3.72, 2.08, 0.58), 0),                # walnut caddy across both rims (rim_inner at 0.33 m off centre)
    ("decor_d_tub_towel", (3.33, 1.70, 0.58), -90),              # towel over the rim near mid-length, toward the door
    ("decor_d_basket", (0.85, -4.25, 0.0), 0),                   # rolled towels by the towel warmer
]


# --- interactivity (prompts/interactivity.md): the light switch by the door (W wall, latch side),
# interactive props, and this room's light fixtures wired to lights_primary_bath (ix_common.wire)
import importlib as _il  # noqa: E402
import ix_common  # noqa: E402

_il.reload(ix_common)
PLACEMENTS = list(PLACEMENTS) + [
    ('ix_switch', (-4.85, 1.03, 1.1), 90, {'signal': 'lights_primary_bath', 'state': True}),
]
PLACEMENTS = ix_common.wire(PLACEMENTS, "primary_bath")
