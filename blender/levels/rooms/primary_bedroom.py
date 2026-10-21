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
    ("art_colorfield_dawn", (-7.85, 0.0, 1.95), 90),     # above the headboard (1.15 m)
    ("library_plant", (-7.1, 3.9), 0),
    # sitting area by the glass
    ("living_rug_b", (3.4, 1.2), 0),
    ("living_sofa_ink", (3.4, -0.3), 180),               # faces the window
    ("living_armchair", (2.2, 2.6), 0),
    ("living_armchair", (4.6, 2.6), 0),
    ("living_coffee_round", (3.4, 1.2), 0),
    # arc lamp east of the sofa, its shade swung west over the sofa's east end at (3.9, -0.3)
    # (at rot 180 it hung over the walkway at head height)
    ("living_floor_lamp", (5.3, -0.3), -90),
    ("library_plant", (7.1, 3.9), 0),
    ("art_wash_horizon", (7.85, -2.4, 1.6), -90),        # east wall, south of the bath door
    # dressing along the south wall
    ("wardrobe", (-1.4, -4.29), 180),
    ("wardrobe", (0.45, -4.29), 180),
    ("guest_desk", (3.4, -4.25), 180),                   # a writing desk / vanity
    ("guest_chair", (3.4, -3.55), 0),
    ("table_lamp", (2.85, -4.3, 0.74), 0),
]

# --- lighting --------------------------------------------------------------------------------
# The ink headboard wall glows: a hidden light behind the headboard washes up the dark plaster
# in a soft halo, the picture above the bed gets its own tight downlight, and the bedside lamps
# are the warm pools either side. Across the room the wardrobes carry a hidden uplight on top
# (a cove on the joinery) that lights the ceiling over the dressing wall, the arc lamp hangs
# over the sofa, the desk lamp marks the writing desk. No ceiling strips.
CEIL = 3.8
PLACEMENTS += [
    ("light_u_downlight", (-7.0, 0.0, CEIL), 0),          # picture light over the bed
    ("light_u_downlight", (7.05, -2.4, CEIL), 0),         # east wall art
    ("light_u_downlight", (3.4, 1.2, CEIL), 0),           # a pool on the sitting area's round table
    ("light_u_downlight", (-5.0, 0.0, CEIL), 0),          # a pool on the bench at the foot of the bed
]

LIGHTS = [
    # bedside lamps
    dict(kind="point", pos=(-7.6, 1.41, 0.97), power=80.0, color=(1.0, 0.72, 0.45)),
    dict(kind="point", pos=(-7.6, -1.41, 0.97), power=80.0, color=(1.0, 0.72, 0.45)),
    # behind the headboard, washing up the ink wall (and onto the ceiling's edge)
    dict(kind="area", pos=(-7.78, 0.0, 1.22), size=(2.0, 0.06), aim=(-7.85, 0.0, 3.8), power=240.0,
         color=(1.0, 0.78, 0.56)),
    # picture light on the art above the bed (aimed at its centre, 1.40..2.50 m)
    dict(kind="spot", pos=(-7.0, 0.0, CEIL - 0.03), aim=(-7.85, 0.0, 1.95), power=160.0, angle=28.0, blend=0.6,
         color=(1.0, 0.82, 0.62)),
    # hidden uplight on top of the two wardrobes (x -2.3..1.35), onto the ceiling
    dict(kind="area", pos=(-0.475, -4.3, 2.43), size=(3.5, 0.3), aim=(-0.475, -3.9, CEIL), power=320.0,
         color=(1.0, 0.82, 0.62)),
    # east wall art, the round table between the sofa and the armchairs
    dict(kind="spot", pos=(7.05, -2.4, CEIL - 0.03), aim=(7.85, -2.4, 1.6), power=170.0, angle=30.0, blend=0.75,
         color=(1.0, 0.82, 0.62)),
    dict(kind="spot", pos=(3.4, 1.2, CEIL - 0.03), aim=(3.4, 1.2, 0.0), power=220.0, angle=45.0, blend=0.8,
         color=(1.0, 0.82, 0.62)),
    dict(kind="spot", pos=(-5.0, 0.0, CEIL - 0.03), aim=(-5.0, 0.0, 0.0), power=200.0, angle=55.0, blend=0.8,
         color=(1.0, 0.82, 0.62)),
    # arc floor lamp over the sofa, desk lamp
    dict(kind="point", pos=(3.9, -0.3, 1.8), power=75.0, color=(1.0, 0.75, 0.48)),     # in the arc lamp's shade
    dict(kind="point", pos=(2.85, -4.3, 1.15), power=45.0, color=(1.0, 0.72, 0.45)),
]

# --- set dressing (decor_d_* assets; z = the surface each group stands on) --------------------
PLACEMENTS += [
    ("decor_d_nightstand_a", (-7.6, 1.41, 0.55), 90),           # novels + glasses on the bed side, bud vase
    ("decor_d_nightstand_b", (-7.6, -1.41, 0.55), 90),          # carafe on a bronze tray, two books
    ("decor_d_books_bench", (-5.25, 0.40, 0.452), 97),          # art books + stones on the bench end
    ("decor_d_slippers", (-6.5, -1.24, 0.015), 172),            # on the rug by the bed, toes out
    ("decor_d_vignette_coffee", (3.4, 1.2, 0.36), 0),           # books + bronze ring, vase pair, oak bowl
    ("decor_d_vignette_vanity_desk", (3.4, -4.25, 0.74), 180),  # scent tray, notebook + pen, books
    ("decor_d_floor_vase", (2.0, -4.2, 0.0), 180),              # olive branches between wardrobe and desk
]


# --- interactivity (prompts/interactivity.md): the light switch by the suite door (S wall, latch side),
# interactive props, and this room's light fixtures wired to lights_primary_bedroom (ix_common.wire)
import importlib as _il  # noqa: E402
import ix_common  # noqa: E402

_il.reload(ix_common)
PLACEMENTS = list(PLACEMENTS) + [
    ('ix_switch', (5.53, -4.6, 1.1), 180, {'signal': 'lights_primary_bedroom', 'state': True}),
    ('ix_switch_blinds', (-6.45, 4.6, 1.1), 0, {'signal': 'blinds_primary_bedroom'}),   # (controls) glass, bed side
    ('ix_blind_bedroom', (0.0, 4.75), 0, {'signal': 'blinds_primary_bedroom'}),
    # (a spare battery in the nightstand drawer, behind the keycard door: caches.py)
]
PLACEMENTS = ix_common.wire(PLACEMENTS, "primary_bedroom")

# --- distractions (viewer/devices.js): an alarm clock on the south nightstand, facing the bed
# (set it, leave: it rings 10 s later for 12 s; also from the tablet, through the locked door)
PLACEMENTS = list(PLACEMENTS) + [
    ("ix_alarm_clock", (-7.5, -1.78, 0.55), 110),
]
