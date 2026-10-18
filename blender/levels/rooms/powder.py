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

PLACEMENTS = [
    # --- vanity wall (north)
    ("entry_vanity", (0.0, 4.32), 0),
    ("entry_mirror", (0.0, 4.6, 1.72), 0),
    ("entry_sconce", (-1.4, 4.6, 1.72), 0),
    ("entry_sconce", (1.4, 4.6, 1.72), 0),
    # --- WC behind its screen (north-west corner)
    ("entry_wc", (-2.30, 2.0), 90),
    ("entry_screen", (-1.84, 0.85), 0),
    ("entry_artwork_ink", (-2.6, 2.0, 2.15), 90),
    ("entry_sconce", (-2.6, 3.4, 1.72), 90),
    # --- south: a small lounge corner
    ("entry_rug_round", (-0.5, -2.1), 0),
    ("entry_round_table", (-0.5, -2.1), 0),
    ("entry_flowers_small", (-0.5, -2.1, 0.80), 0),
    ("bench", (-0.5, -4.37), 180),
    ("art_colorfield_a", (-0.5, -4.6, 1.8), 180),
]

LIGHTS = [
    dict(kind="strip", pos=(0.0, 3.4), size=(3.2, 0.08), power=170.0),
    dict(kind="strip", pos=(0.0, -1.0), size=(3.6, 0.08), power=150.0),
    dict(kind="point", pos=(-1.4, 4.3, 1.72), power=70.0, color=(1.0, 0.78, 0.5)),
    dict(kind="point", pos=(1.4, 4.3, 1.72), power=70.0, color=(1.0, 0.78, 0.5)),
    dict(kind="point", pos=(-2.3, 3.4, 1.72), power=50.0, color=(1.0, 0.78, 0.5)),
    dict(kind="point", pos=(-0.5, -3.6, 2.6), power=60.0, color=(1.0, 0.80, 0.55)),
]
