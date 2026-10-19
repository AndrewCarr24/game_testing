"""Powder room (ground floor, west of the entry): 5.2 x 9.2 m inside, 4.2 m high. The
door is on the east wall at y -2.8..-1.7 and swings in (keep x 1.3..2.6, y -3..-0.5 clear).

Dark veined marble walls, pale limestone underfoot. North wall: a floating walnut vanity
with a vessel basin under a round halo mirror between two glass sconces. West wall: a
wall-hung WC behind a slatted walnut screen under an ink painting. South: a round marble
table with blossom, a bench and a small painting.
Local coords: (0, 0) = room centre; +x east, +y north.
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets"))
import entry_sculpture  # noqa: E402  (limestone)
import entry_vanity  # noqa: E402  (dark marble)

importlib.reload(entry_sculpture)
importlib.reload(entry_vanity)
from lib import common  # noqa: E402

FINISHES = dict(
    floor=entry_sculpture.limestone_material,
    floor_uv_tile=2.0,
    walls=lambda: entry_vanity.dark_marble_material("M_Entry_DarkMarble", roughness=0.3),
    wall_uv_tile=2.6,           # large slabs: the veins no longer repeat every metre
    ceiling=lambda: common.pbr_material("M_Ceiling_Powder", (0.16, 0.145, 0.13), roughness=0.9),
)

# lighting: ceiling cans (x, y, (aim, power W, cone deg)), see LIGHTS
_CANS = [
    (-1.75, 2.0, ((-2.55, 2.0, 1.85), 180.0, 32)),     # the photograph over the WC
    (-0.5, -3.7, ((-0.5, -4.55, 1.45), 200.0, 34)),    # the gold-leaf panel
    (-0.5, -2.1, ((-0.5, -2.1, 0.8), 450.0, 50)),      # the blossom on the round table
    (0.5, 1.7, ((0.5, 1.7, 0.0), 420.0, 60)),          # the floor before the vanity
    (1.6, -1.6, ((1.6, -1.6, 0.0), 360.0, 60)),        # the way in
]

PLACEMENTS = [
    # --- vanity wall (north)
    ("entry_vanity", (0.0, 4.32), 0),
    ("entry_mirror", (0.0, 4.6, 1.72), 0),
    ("entry_sconce", (-1.4, 4.6, 1.72), 0),
    ("entry_sconce", (1.4, 4.6, 1.72), 0),
    # --- WC behind its screen (north-west corner)
    ("entry_wc", (-2.30, 2.0), 90),
    ("entry_screen", (-1.84, 0.85), 0),
    ("art_moon_sea", (-2.6, 2.0, 1.85), 90),             # night photograph above the flush plate
    ("entry_sconce", (-2.6, 3.4, 1.72), 90),
    # --- south: a small lounge corner
    ("entry_rug_round", (-0.5, -2.1), 0),
    ("entry_round_table", (-0.5, -2.1), 0),
    ("entry_flowers_small", (-0.5, -2.1, 0.80), 0),
    ("bench", (-0.5, -4.37), 180),
    ("art_gold_leaf", (-0.5, -4.6, 1.45), 180),          # gold-leaf panel over the bench
    # --- lighting (see LIGHTS): bronze valances high on the long walls (light grazing down the
    #     marble), ceiling cans on the art, the blossom and the floor
    ("light_g_cove_down", (-2.6, -2.0, 3.9), 90),
    ("light_g_cove_down", (-2.6, 2.0, 3.9), 90),
    ("light_g_cove_down", (2.6, -2.0, 3.9), -90),
    ("light_g_cove_down", (2.6, 2.0, 3.9), -90),
    *[("light_g_downlight", (x, y, 4.2), 0) for x, y, _ in _CANS],
]

# Lighting: a jewel box. The halo mirror between its two glass sconces is the brightest
# thing; the floating vanity glows from underneath; bronze valances high on the two long
# walls graze light down the veined marble; cans pick out the photograph over the WC, the
# gold-leaf panel and the blossom on the round table. No ceiling lines.
LIGHTS = [
    dict(kind="point", pos=(-1.4, 4.3, 1.72), power=130.0, color=(1.0, 0.78, 0.5)),
    dict(kind="point", pos=(1.4, 4.3, 1.72), power=130.0, color=(1.0, 0.78, 0.5)),
    dict(kind="point", pos=(-2.3, 3.4, 1.72), power=80.0, color=(1.0, 0.78, 0.5)),
    # toe glow under the floating vanity (its underside is 0.34 m up)
    dict(kind="area", pos=(0.0, 4.3, 0.32), size=(1.7, 0.05), aim=(0.0, 4.0, 0.0), power=60.0, color=(1.0, 0.8, 0.55)),
    # the halo mirror's glow on the marble round it (a ring of LED behind the glass)
    dict(kind="area", pos=(0.0, 4.5, 1.72), size=(1.6, 1.6), aim=(0.0, 0.0, 1.72), power=40.0, color=(1.0, 0.8, 0.55)),
    # valance washes (lip down at 3.9 m) grazing the veined marble of both long walls
    dict(kind="area", pos=(-2.5, 0.0, 3.84), size=(7.8, 0.06), aim=(-2.1, 0.0, 0.5), power=300.0, color=(1.0, 0.82, 0.6)),
    dict(kind="area", pos=(2.5, 0.0, 3.84), size=(7.8, 0.06), aim=(2.1, 0.0, 0.5), power=300.0, color=(1.0, 0.82, 0.6)),
    *[dict(kind="spot", pos=(x, y, 4.08), aim=aim, power=pw, angle=ang, blend=0.5) for (x, y, (aim, pw, ang)) in _CANS],
]
