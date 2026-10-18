"""Dining room (ground floor, north-west of the kitchen): 15.7 x 9.2 m inside, north wall
glazed (x -6..6). Openings: south wall x -5..1 (great room) and x 5..7.5 (gallery), east wall
y -2.5..2.5 (kitchen). A long walnut table for 14 under a floating chandelier, a marble-topped
sideboard under a large canvas on the olive west wall, a second sideboard on the south wall."""
import importlib

from lib import common, materials, textures

importlib.reload(materials)

TX, TY = -0.5, 0.6          # table centre
CH_Y = 0.22                 # chair origin outside the table edge (cushions tucked under)
PITCH = 0.8

FINISHES = dict(
    walls=lambda: common.pbr_material("M_Plaster_Dining", (0.60, 0.565, 0.505), roughness=0.92),
    ceiling=lambda: common.pbr_material("M_Ceiling_Warm", (0.48, 0.46, 0.43), roughness=0.9),
    walls_by_side={"W": lambda: common.pbr_material("M_Plaster_Olive", (0.065, 0.085, 0.045), roughness=0.92)},
)


def _chairs():
    out = []
    xs = [TX + (i - 2.5) * PITCH for i in range(6)]
    for x in xs:
        out.append(("dining_chair", (x, TY + 0.65 + CH_Y), 0))        # north side, facing south
        out.append(("dining_chair", (x, TY - 0.65 - CH_Y), 180))      # south side, facing north
    out.append(("dining_chair", (TX - 2.6 - CH_Y - 0.02, TY), 90))   # west head, facing east
    out.append(("dining_chair", (TX + 2.6 + CH_Y + 0.02, TY), -90))  # east head, facing west
    return out


PLACEMENTS = [
    ("dining_rug", (TX, TY), 0),
    ("dining_table", (TX, TY), 0),
    *_chairs(),
    ("dining_centerpiece", (TX, TY, 0.76), 0),
    ("dining_chandelier", (TX, TY, 4.2 - 1.824), 0),
    # west wall: sideboard under the big canvas
    ("dining_sideboard", (-7.85 + 0.28, TY), 90),
    ("dining_artwork", (-7.85, TY, 2.1), 90),
    ("table_lamp", (-7.55, TY - 0.85, 0.84), 0),
    ("table_lamp", (-7.55, TY + 0.85, 0.84), 0),
    ("vase", (-7.55, TY, 0.84), 0),
    # south wall: second sideboard between the openings
    ("dining_sideboard", (3.0, -4.6 + 0.28), 180),
    ("art_colorfield_a", (2.25, -4.6, 1.85), 180),
    ("art_geometric_a", (3.0, -4.6, 1.85), 180),
    ("art_linework_a", (3.75, -4.6, 1.85), 180),
    # south-west wall segment and corner planting
    ("art_colorfield_b", (-6.4, -4.6, 1.85), 180),
    ("library_plant", (-6.35, -3.3), 0),
    ("library_plant", (6.55, 3.2), 40),
    # window nook (north-west): two cognac lounge chairs round a low table
    ("bedroom_rug", (-5.75, 3.25), 0),
    ("coffee_table", (-5.75, 3.25), 90),
    ("lounge_chair", (-6.75, 3.25), 90),
    ("lounge_chair", (-4.75, 3.25), -90),
]

LIGHTS = [
    dict(kind="strip", pos=(TX, TY), size=(5.4, 0.08), power=170.0),
    dict(kind="strip", pos=(-7.15, TY), size=(0.08, 4.6), power=110.0),       # washes the olive wall
    dict(kind="strip", pos=(3.0, -3.9), size=(3.6, 0.08), power=80.0),
    dict(kind="point", pos=(TX - 1.8, TY, 2.65), power=60.0, color=(1.0, 0.8, 0.55)),
    dict(kind="point", pos=(TX, TY, 2.65), power=60.0, color=(1.0, 0.8, 0.55)),
    dict(kind="point", pos=(TX + 1.8, TY, 2.65), power=60.0, color=(1.0, 0.8, 0.55)),
]

PROBE = (TX, TY, 1.6)
