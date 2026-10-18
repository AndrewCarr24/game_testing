"""Wine room (ground floor, east of the scullery): 12.2 x 9.2 m inside, no windows. The only
door is on the west wall at y = +1.75 (swings in). A collector's cellar: floor-to-ceiling
racking round three walls, a glass-fronted climate wall at the centre of the north wall, a
marble tasting table with stools and pendants, and a leather conversation nook in the south.
Dark honed-slate floor, deep taupe plaster, smoked oak and bronze."""
import importlib
import os

import numpy as np

from lib import common, materials, textures

importlib.reload(materials)


def _slate():
    """Large-format dark honed slate: 3 x 3 tiles per 2 m (the floor UV tile), fine grout lines."""
    path = os.path.join(textures.TEX_DIR, "T_Dining_Slate_BaseColor.png")
    if not os.path.exists(path):
        n = 1024
        rng = np.random.default_rng(57)
        u = np.linspace(0, 1, n, endpoint=False)[None, :] * np.ones((n, 1))
        v = np.linspace(0, 1, n, endpoint=False)[:, None] * np.ones((1, n))
        ti, tj = np.floor(u * 3).astype(int), np.floor(v * 3).astype(int)
        tone = rng.uniform(-1, 1, (3, 3))[tj, ti]
        cloud = textures._noise(n, 1.0, 1.0, 2.0, rng) * 0.5 + 0.5
        vein = np.abs(textures._noise(n, 1.0, 1.0, 1.5, rng))
        fine = textures._noise(n, 1.0, 1.0, 0.5, rng)
        t = np.clip(0.45 + 0.25 * cloud - 0.30 * (vein < 0.05) + 0.08 * fine + 0.10 * tone, 0, 1)
        base = np.array([0.034, 0.028, 0.024])
        light = np.array([0.105, 0.087, 0.070])
        lin = base + (light - base) * t[..., None]
        fu, fv = (u * 3) % 1.0, (v * 3) % 1.0
        grout = (np.minimum(fu, 1 - fu) < 0.004) | (np.minimum(fv, 1 - fv) < 0.004)
        lin[grout] *= 0.4
        textures._save("T_Dining_Slate_BaseColor", textures._to_srgb(lin))
    return path


def _floor():
    m = common.pbr_material("M_Slate_Dark", (0.06, 0.055, 0.05), roughness=0.5, coat=0.15)
    common.set_base_color_map(m, textures.load(_slate()))
    return m


FINISHES = dict(
    floor=_floor,
    walls=lambda: common.pbr_material("M_Plaster_Cellar", (0.27, 0.20, 0.14), roughness=0.92),
    ceiling=lambda: common.pbr_material("M_Ceiling_Cellar", (0.17, 0.135, 0.10), roughness=0.9),
    floor_uv_tile=2.0,
)

T_Y = 0.2            # tasting table centre y

PLACEMENTS = [
    # north wall: racking either side of the climate wall
    ("dining_wine_rack", (-4.05, 4.6 - 0.2), 0),
    ("dining_wine_rack", (4.05, 4.6 - 0.2), 0),
    ("dining_climate_wall", (0.0, 4.6 - 0.275), 0),
    # east wall (faces west)
    ("dining_wine_rack_long", (6.1 - 0.2, 0.0), -90),
    # west wall, south of the door (faces east)
    ("dining_wine_rack_short", (-6.1 + 0.2, -2.4), 90),
    # tasting table, stools, pendants, a tasting set
    ("dining_tasting_table", (0.0, T_Y), 0),
    ("dining_stool", (-0.95, T_Y - 0.78), 0),
    ("dining_stool", (0.0, T_Y - 0.78), 0),
    ("dining_stool", (0.95, T_Y - 0.78), 0),
    ("dining_stool", (-0.95, T_Y + 0.78), 180),
    ("dining_stool", (0.0, T_Y + 0.78), 180),
    ("dining_stool", (0.95, T_Y + 0.78), 180),
    ("dining_wine_set", (-0.55, T_Y, 0.92), 0),
    ("dining_pendants", (0.0, T_Y, 4.2 - 2.3), 0),
    # barrels in the north-west corner by the door wall
    ("dining_barrel", (-5.45, 3.72), 0),
    ("dining_wine_set", (-5.45, 3.72, 0.92), 20),
    ("dining_barrel", (-4.55, 3.62), 0),
    # south: leather conversation nook
    ("bedroom_rug", (2.6, -2.9), 0),
    ("coffee_table", (2.6, -2.9), 90),
    ("lounge_chair", (1.65, -2.9), 90),
    ("lounge_chair", (3.55, -2.9), -90),
    # south wall art
    ("dining_artwork", (2.6, -4.6, 2.1), 180),
    ("art_colorfield_b", (-1.2, -4.6, 1.8), 180),
    ("art_geometric_b", (-2.6, -4.6, 1.8), 180),
    # south-west: two barrels as standing tables
    ("dining_barrel", (-5.0, -3.8), 0),
    ("dining_wine_set", (-5.0, -3.8, 0.92), 160),
    ("dining_stool", (-4.1, -3.9), 0),
]

LIGHTS = [
    dict(kind="strip", pos=(0.0, 3.7), size=(4.4, 0.08), power=198.0),                 # washes the climate wall
    dict(kind="strip", pos=(0.0, T_Y), size=(3.4, 0.08), power=126.0),                  # tasting table
    dict(kind="strip", pos=(5.2, 0.0), size=(0.08, 6.4), power=234.0),                 # east racking
    dict(kind="strip", pos=(-5.2, -2.4), size=(0.08, 3.4), power=126.0),                # west racking
    dict(kind="strip", pos=(2.6, -3.9), size=(3.4, 0.08), power=108.0),                 # nook / south wall
    dict(kind="point", pos=(-0.9, T_Y, 2.0), power=35.0, color=(1.0, 0.72, 0.45)),
    dict(kind="point", pos=(0.9, T_Y, 2.0), power=35.0, color=(1.0, 0.72, 0.45)),
]

PROBE = (0.0, -1.0, 1.6)
