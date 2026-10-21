"""Den / media room (ground floor, south-west): 12.2 x 9.2 m inside, no windows, 4.2 m
ceiling. The door to the great room is in the north wall at x = 0. The screen wall is the
south wall (y = -4.6). Smoked-oak floor, deep green fabric walls, a dark warm ceiling.
Local coords: (0, 0) = room centre, +x east, +y north."""
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
    walls=lambda: materials.fabric("M_Fabric_DenGreen", (0.026, 0.058, 0.040)),
    ceiling=lambda: common.pbr_material("M_Ceiling_Den", (0.11, 0.10, 0.092), roughness=0.9),
    walls_by_side={"S": lambda: materials.fabric("M_Fabric_DenGreen", (0.026, 0.058, 0.040))},
)

PLACEMENTS = [
    # ---- screen wall (south) ----------------------------------------------------------
    # the TV starts off (distractions: on, it's a noise the Grimble hears, so the player turns it
    # on to lure it); the bake has no screen light
    ("living_media_wall", (0.0, -4.34), 180, {"signal": {"tv": "tv_den"}, "state": False}),
    # ---- seating: the sectional faces the screen -----------------------------------------
    ("living_rug_den", (0.0, -0.8), 0),
    ("living_sectional", (-0.6, 0.6), 0),
    ("living_ottoman", (-0.7, -1.9), 0),
    ("vase", (-0.7, -1.9, 0.44), 0),
    ("living_side_table", (-3.3, 1.2), 0),
    ("living_table_lamp", (-3.3, 1.2, 0.55), 0),
    ("living_side_table", (2.2, 1.2), 0),
    ("living_table_lamp", (2.2, 1.2, 0.55), 0),
    ("living_floor_lamp", (-2.2, 2.1), 0),
    ("living_armchair_cognac", (3.7, -0.5), -40),
    ("living_armchair_cognac", (4.5, 1.8), -75),
    ("living_side_table", (4.3, 0.55), 0),
    # ---- west wall: shelving ------------------------------------------------------------------
    ("living_shelving", (-5.9, -1.9), 90),
    ("living_shelving", (-5.9, 1.9), 90),
    # ---- east wall: bar console and art --------------------------------------------------------
    ("living_console", (5.85, 3.0), -90),
    ("art_colorfield_b", (6.09, 3.0, 1.8), -90),
    ("vase", (5.85, 3.6, 0.82), 0),
    # ---- corners ---------------------------------------------------------------------------------
    ("library_plant", (4.9, -2.8), 0),
    ("library_plant", (-4.9, -2.8), 0),
    # ---- north wall flanks (the door is at x = 0) ---------------------------------------------
    ("living_console", (-3.4, 4.39), 0),
    ("art_stain_tall", (-3.4, 4.59, 2.05), 0),           # soak-stain canvas over the console
    ("living_plant_olive", (3.6, 3.95), 0),
    # ---- lighting (see LIGHTS): up/down sconces on the green walls, three ceiling cans
    ("light_g_sconce_updown", (-1.2, 4.6, 2.25), 0),
    ("light_g_sconce_updown", (1.2, 4.6, 2.25), 0),
    ("light_g_sconce_updown", (6.1, -0.8, 2.25), -90),
    ("light_g_sconce_updown", (6.1, -3.4, 2.25), -90),
    ("light_g_downlight", (-3.4, 3.6, 4.2), 0),
    ("light_g_downlight", (5.1, 3.0, 4.2), 0),
    ("light_g_downlight", (-0.7, -1.9, 4.2), 0),
    # ---- set dressing (decor_a_*) ------------------------------------------------------------------
    ("decor_a_console_den", (-3.4, 4.39), 0),
    ("decor_a_console_bar", (5.85, 3.0), -90),               # the vase stays at its north end
    ("decor_a_table_ottoman_den", (-0.7, -1.9, 0.435), 0),    # round the vase
    ("decor_a_table_side_glass", (-3.3, 1.2, 0.55), 0),
    ("decor_a_table_side_cup", (2.2, 1.2, 0.55), 0),
    ("decor_a_table_side_plant_den", (4.3, 0.55, 0.55), 0),
    ("decor_a_table_credenza", (0.0, -4.37, 0.54), 180),     # low groups at both ends of the credenza
    ("decor_a_soft_sectional_throw", (-0.6, 0.6), 0),        # over the sectional's left arm
]

# Lighting: a dark, cinematic room. The screen and the backlit bookshelves are the brightest
# things; a hidden LED on top of the slat wall washes the ceiling over the screen; bronze
# up/down sconces throw scallops on the green fabric either side of the door and along the
# east wall; the lamps pool warm light round the sectional; cans pick out the two canvases
# and the ottoman. No ceiling lines.
_SHELF_LEDS = (0.86, 1.34, 1.82, 2.30, 2.665)     # under living_shelving's boards (and its top)


def _updown(x, y, wx, wy, up=90.0, down=110.0):
    """The two scallops of a light_g_sconce_updown at (x, y) on a wall, 0.13 m out along (wx, wy)."""
    px, py = x + 0.13 * wx, y + 0.13 * wy
    return [dict(kind="spot", pos=(px, py, 2.40), aim=(px, py, 4.2), power=up, angle=60, blend=0.7),
            dict(kind="spot", pos=(px, py, 2.10), aim=(px, py, 0.0), power=down, angle=60, blend=0.7)]


LIGHTS = [
    # the warm glow under the floating credenza (the TV starts off: its screen isn't in the bake)
    dict(kind="area", pos=(0.0, -4.2, 0.12), size=(4.7, 0.05), aim=(0.0, -4.2, 0.0), power=20.0, color=(1.0, 0.62, 0.30)),
    # cove on top of the 3.75 m slat wall (4.9 m wide, living_media_wall slat_zone), up onto the ceiling
    dict(kind="area", pos=(0.0, -4.4, 3.8), size=(4.9, 0.15), aim=(0.0, -4.4, 4.2), power=130.0, color=(1.0, 0.84, 0.66)),
    # table lamps and the arc lamp
    dict(kind="point", pos=(-3.3, 1.2, 1.2), power=80.0, color=(1.0, 0.72, 0.45)),
    dict(kind="point", pos=(2.2, 1.2, 1.2), power=80.0, color=(1.0, 0.72, 0.45)),
    dict(kind="point", pos=(-2.2, 0.7, 1.8), power=120.0, color=(1.0, 0.75, 0.5)),
    # cans: the two canvases and the ottoman
    dict(kind="spot", pos=(-3.4, 3.6, 4.08), aim=(-3.4, 4.55, 2.0), power=160.0, angle=32, blend=0.5),
    dict(kind="spot", pos=(5.1, 3.0, 4.08), aim=(6.05, 3.0, 1.8), power=130.0, angle=30, blend=0.5),
    dict(kind="spot", pos=(-0.7, -1.9, 4.08), aim=(-0.7, -1.9, 0.0), power=220.0, angle=40, blend=0.6),
    *_updown(-1.2, 4.6, 0, -1), *_updown(1.2, 4.6, 0, -1),
    *_updown(6.1, -0.8, -1, 0), *_updown(6.1, -3.4, -1, 0),
] + [
    # backlit shelving: an LED under each board of the two west-wall units (fronts at x -5.72)
    dict(kind="area", pos=(-5.78, y, z), size=(0.05, 3.2), aim=(-5.78, y, 0.0), power=30.0, color=(1.0, 0.82, 0.6))
    for y in (-1.9, 1.9) for z in _SHELF_LEDS
] + [
    # and a soft glow off each unit's back panel, round the books
    dict(kind="area", pos=(-6.03, y, 1.5), size=(3.2, 2.2), aim=(0.0, y, 1.5), power=90.0, color=(1.0, 0.82, 0.6))
    for y in (-1.9, 1.9)
]

PROBE = (0.0, -1.2, 1.6)


# --- interactivity (prompts/interactivity.md): the light switch by the door (N wall, latch side),
# interactive props, and this room's light fixtures wired to lights_den (ix_common.wire)
import importlib as _il  # noqa: E402
import ix_common  # noqa: E402

_il.reload(ix_common)
PLACEMENTS = list(PLACEMENTS) + [
    ('ix_switch', (-0.72, 4.6, 1.1), 0, {'signal': 'lights_den', 'state': True}),
]
PLACEMENTS = ix_common.wire(PLACEMENTS, "den")
