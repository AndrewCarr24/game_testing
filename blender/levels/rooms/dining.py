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
    # a row of three on the 4 m of wall between the openings (0.9 + 0.8 + 0.9 m frames, 0.2 m
    # gaps, centred on the sideboard; they were 0.75 m apart centre to centre and overlapped)
    ("art_colorfield_a", (1.95, -4.6, 1.85), 180),
    ("art_geometric_a", (3.0, -4.6, 1.85), 180),
    ("art_linework_a", (4.05, -4.6, 1.85), 180),
    # south-west wall segment and corner planting
    ("art_sweep_terracotta", (-6.4, -4.6, 1.6), 180),   # brush sweep on raw linen
    ("library_plant", (-6.35, -3.3), 0),
    ("library_plant", (6.55, 3.2), 40),
    # window nook (north-west): two cognac lounge chairs round a low table
    ("bedroom_rug", (-5.75, 3.25), 0),
    ("coffee_table", (-5.75, 3.25), 90),
    ("lounge_chair", (-6.75, 3.25), 90),
    ("lounge_chair", (-4.75, 3.25), -90),
    # lighting (see LIGHTS): a bronze ledge over the olive wall, a reading lamp in the nook,
    # ceiling cans on the south-wall art
    ("light_g_cove", (-7.85, TY, 3.75), 90),
    ("library_floorlamp", (-7.35, 2.3), 0),
    ("light_g_downlight", (2.4, -3.6, 4.2), 0),
    ("light_g_downlight", (3.6, -3.6, 4.2), 0),
    ("light_g_downlight", (-6.4, -3.6, 4.2), 0),
]

# Lighting: the floating globe chandelier over the walnut table is the brightest thing; a
# bronze ledge high on the olive wall washes down over the big canvas (and a little up onto
# the ceiling); the lamps glow on the west sideboard; cans light the south-wall art over
# the second sideboard; the window nook has its own lamp. No ceiling lines.
LIGHTS = [
    *[dict(kind="point", pos=(TX + dx, TY, 2.8), power=110.0, color=(1.0, 0.8, 0.55)) for dx in (-1.8, -0.9, 0.0, 0.9, 1.8)],
    # olive-wall ledge (z 3.75): down over the canvas, a little up
    dict(kind="area", pos=(-7.75, TY, 3.72), size=(3.9, 0.08), aim=(-7.1, TY, 1.0), power=280.0, color=(1.0, 0.82, 0.62)),
    dict(kind="area", pos=(-7.77, TY, 3.82), size=(3.9, 0.08), aim=(-7.4, TY, 4.2), power=100.0, color=(1.0, 0.84, 0.66)),
    # sideboard lamps (shade centres) and the nook lamp
    dict(kind="point", pos=(-7.55, TY - 0.85, 1.29), power=60.0, color=(1.0, 0.76, 0.5)),
    dict(kind="point", pos=(-7.55, TY + 0.85, 1.29), power=60.0, color=(1.0, 0.76, 0.5)),
    dict(kind="point", pos=(-7.35, 2.3, 1.42), power=80.0, color=(1.0, 0.76, 0.5)),
    # cans on the south-wall art
    dict(kind="spot", pos=(2.4, -3.6, 4.08), aim=(2.4, -4.55, 1.85), power=150.0, angle=38, blend=0.5),
    dict(kind="spot", pos=(3.6, -3.6, 4.08), aim=(3.6, -4.55, 1.85), power=150.0, angle=38, blend=0.5),
    dict(kind="spot", pos=(-6.4, -3.6, 4.08), aim=(-6.4, -4.55, 1.6), power=130.0, angle=34, blend=0.5),
]

PROBE = (-0.5, -2.2, 1.6)          # clear of the table (on it, the panorama was the walnut top)

# set dressing (decor_b_*): composed vignettes on the sideboards, the nook's coffee table and
# either end of the dining table (all NoCollide)
PLACEMENTS += [
    ("decor_b_vignette_sideboard", (3.0, -4.32, 0.84), 180),      # ceramics + branches, books, carafe tray
    ("decor_b_vignette_console", (-7.57, TY, 0.84), 90),          # either side of the vase, between the lamps
    ("decor_b_vignette_coffee", (-5.75, 3.4, 0.38), 90),
    ("decor_b_table_buds", (TX - 1.75, TY, 0.76), 0),
    ("decor_b_table_buds", (TX + 1.75, TY, 0.76), 180),
]


# --- interactivity (prompts/interactivity.md): the light switch east of the gallery opening (S wall),
# interactive props, and this room's light fixtures wired to lights_dining (ix_common.wire)
import importlib as _il  # noqa: E402
import ix_common  # noqa: E402

_il.reload(ix_common)
PLACEMENTS = list(PLACEMENTS) + [
    ('ix_switch', (1.17, -4.6, 1.1), 180, {'signal': 'lights_dining', 'state': True}),
    ('ix_switch_blinds', (1.27, -4.6, 1.1), 180, {'signal': 'blinds_dining'}),
    ('ix_blind_dining', (0.0, 4.75), 0, {'signal': 'blinds_dining'}),
]
PLACEMENTS = ix_common.wire(PLACEMENTS, "dining")
