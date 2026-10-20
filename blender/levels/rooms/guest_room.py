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
    floor_uv_tile=2.0,            # the scanned plank floor (polyhaven_textures) covers ~2 m per tile
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
    ("art_clouds", (-6.09, 1.8, 1.8), 90),                 # cloud photograph over the bed
    # writing desk on the south wall
    ("guest_desk", (-1.6, -4.74), 180),
    ("guest_chair", (-1.6, -4.05), 0),
    ("art_wash_circles", (-1.6, -5.09, 1.6), 180),         # small watercolour, oak frame
    ("library_plant", (-4.3, -4.4), 0),
    # dresser on the north wall, with a vase and art
    ("guest_dresser", (-2.2, 4.86), 0),
    ("vase", (-2.9, 4.86, 0.80), 0),
    ("art_bone_white", (-2.2, 5.09, 1.65), 0),             # white-on-white canvas
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

# --- lighting --------------------------------------------------------------------------------
# Calm and residential: the sage headboard wall is the lit wall, with a hidden glow behind
# the headboard, a picture light on the art above the bed and two downlights grazing the sage
# either side of the nightstand lamps. The reeded wardrobe carries a hidden uplight on top
# onto the ceiling; a lamp on the writing desk, a downlight washing the dresser's picture,
# the reading corner's floor lamp by the glass. No ceiling strips.
CEIL = 3.8
_DL = [((-5.35, 1.8), (-6.1, 1.8, 1.95), 150.0, 34.0),      # picture light over the bed
       ((-5.4, 4.2), (-6.1, 4.2, 1.0), 230.0, 50.0),        # sage wall grazers flanking the bed
       ((-5.4, -0.6), (-6.1, -0.6, 1.0), 230.0, 50.0),
       ((-3.6, 1.8), (-3.6, 1.8, 0.0), 200.0, 55.0),        # a pool on the bench at the foot of the bed
       ((-2.2, 4.3), (-2.2, 5.1, 1.5), 170.0, 50.0),        # dresser and its picture
       ((-1.6, -4.3), (-1.6, -5.1, 1.5), 150.0, 50.0)]      # desk and its picture
PLACEMENTS += (
    [("light_u_downlight", (x, y, CEIL), 0) for (x, y), *_ in _DL]
    + [("table_lamp", (-2.05, -4.85, 0.74), 0)]               # on the writing desk
)

LIGHTS = (
    [dict(kind="spot", pos=(x, y, CEIL - 0.03), aim=aim, power=pw, angle=ang, blend=0.7, color=(1.0, 0.82, 0.62))
     for (x, y), aim, pw, ang in _DL]
    + [
        # behind the headboard (top at ~1.08 m), up the sage wall
        dict(kind="area", pos=(-6.03, 1.8, 1.12), size=(1.9, 0.06), aim=(-6.1, 1.8, 3.8), power=190.0,
             color=(1.0, 0.80, 0.58)),
        # on top of the reeded wardrobe (2.7 m), onto the ceiling
        dict(kind="area", pos=(3.0, 4.78, 2.73), size=(3.4, 0.3), aim=(3.0, 4.4, CEIL), power=260.0,
             color=(1.0, 0.82, 0.62)),
        # bedside lamps, desk lamp, reading floor lamp
        dict(kind="point", pos=(-5.88, 3.18, 0.97), power=50.0, color=(1.0, 0.72, 0.45)),
        dict(kind="point", pos=(-5.88, 0.42, 0.97), power=50.0, color=(1.0, 0.72, 0.45)),
        dict(kind="point", pos=(-2.05, -4.85, 1.19), power=45.0, color=(1.0, 0.72, 0.45)),
        dict(kind="point", pos=(2.45, 0.0, 1.38), power=55.0, color=(1.0, 0.76, 0.5)),
    ]
)

# --- set dressing (decor_d_* assets; z = the surface each group stands on) --------------------
PLACEMENTS += [
    ("decor_d_nightstand_guest_a", (-5.88, 3.18, 0.52), 90),    # novels + glasses on the bed side, bud vase
    ("decor_d_nightstand_guest_b", (-5.88, 0.42, 0.52), 90),    # carafe on a tray, two books
    ("decor_d_towels_guest", (-3.5, 2.12, 0.437), 93),          # welcome towels + eucalyptus on the bench
    ("decor_d_vignette_dresser", (-2.2, 4.86, 0.80), 0),        # books + terracotta bowl, carafe tray
    ("decor_d_vignette_guest_desk", (-1.6, -4.74, 0.74), 180),  # books + pilea, notebook + pen, mug
    ("decor_d_side_reading", (4.35, 1.8, 0.50), -60),           # open book, espresso, reading glasses
    ("decor_d_basket_guest", (2.65, 3.75, 0.0), 20),            # rolled sage throws by the armchairs
    ("decor_d_floor_vase_guest", (-3.7, 4.74, 0.0), 0),         # olive branches flanking the dresser
]


# --- interactivity (prompts/interactivity.md): the light switch by the door (W wall, latch side),
# interactive props, and this room's light fixtures wired to lights_guest_room (ix_common.wire)
import importlib as _il  # noqa: E402
import ix_common  # noqa: E402

_il.reload(ix_common)
PLACEMENTS = list(PLACEMENTS) + [
    ('ix_switch', (-6.1, -2.47, 1.1), 90, {'signal': 'lights_guest_room', 'state': True}),
]
PLACEMENTS = ix_common.wire(PLACEMENTS, "guest_room")
