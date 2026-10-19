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
    ("art_vineyard", (2.6, -4.6, 1.85), 180),             # aerial vineyard photograph
    ("art_wine_rings", (-1.35, -4.6, 1.7), 180),          # pair: wine rings on paper ...
    ("art_oxblood_zip", (-2.35, -4.6, 1.7), 180),         # ... and an oxblood monochrome
    # south-west: two barrels as standing tables
    ("dining_barrel", (-5.0, -3.8), 0),
    ("dining_wine_set", (-5.0, -3.8, 0.92), 160),
    ("dining_stool", (-4.1, -3.9), 0),
    # lighting (see LIGHTS): up/down sconces either side of the photograph, a reading lamp
    # in the nook, ceiling cans on the art and the barrels
    ("light_g_sconce_updown", (0.75, -4.6, 2.25), 180),
    ("light_g_sconce_updown", (4.45, -4.6, 2.25), 180),
    ("library_floorlamp", (4.5, -2.0), 0),
    ("light_g_downlight", (2.0, -3.6, 4.2), 0),
    ("light_g_downlight", (3.2, -3.6, 4.2), 0),
    ("light_g_downlight", (-1.85, -3.7, 4.2), 0),
    ("light_g_downlight", (-5.0, 3.67, 4.2), 0),
]

# Lighting: the bottle walls are the room's display: each run of racking is washed from a
# hidden LED where the racks meet the slatted bulkhead (2.6 m), and the climate wall glows
# from inside; the three bronze cones pool light on the marble tasting table; bronze up/down
# sconces flank the vineyard photograph over the leather nook, which has its own lamp; cans
# pick out the pair of works and the barrels. Warm 2700 K throughout, no ceiling lines.
_WARM = (1.0, 0.76, 0.5)


def _updown(x, y, wx, wy, up=40.0, down=50.0):
    """The two scallops of a light_g_sconce_updown at (x, y) on a wall, 0.13 m out along (wx, wy)."""
    px, py = x + 0.13 * wx, y + 0.13 * wy
    return [dict(kind="spot", pos=(px, py, 2.40), aim=(px, py, 4.2), power=up, angle=60, blend=0.7, color=_WARM),
            dict(kind="spot", pos=(px, py, 2.10), aim=(px, py, 0.0), power=down, angle=60, blend=0.7, color=_WARM)]


LIGHTS = [
    # rack washes (rack fronts: north y 4.2, east x 5.7, west x -5.7)
    dict(kind="area", pos=(-4.05, 4.12, 2.55), size=(3.9, 0.05), aim=(-4.05, 4.3, 0.9), power=120.0, color=_WARM),
    dict(kind="area", pos=(4.05, 4.12, 2.55), size=(3.9, 0.05), aim=(4.05, 4.3, 0.9), power=120.0, color=_WARM),
    dict(kind="area", pos=(5.62, 0.0, 2.55), size=(5.9, 0.05), aim=(5.85, 0.0, 0.9), power=180.0, color=_WARM),
    dict(kind="area", pos=(-5.62, -2.4, 2.55), size=(2.9, 0.05), aim=(-5.85, -2.4, 0.9), power=90.0, color=_WARM),
    # the climate wall, from behind its glass
    dict(kind="area", pos=(0.0, 4.06, 1.75), size=(3.8, 1.7), aim=(0.0, 0.0, 1.75), power=70.0, color=(1.0, 0.70, 0.45)),
    # tasting pendants (bulbs inside the cones, rims at 1.9 m)
    *[dict(kind="point", pos=(x, T_Y, 2.0), power=100.0, color=(1.0, 0.72, 0.45)) for x in (-0.9, 0.0, 0.9)],
    # nook lamp, the photograph, the pair of works, the barrels
    dict(kind="point", pos=(4.5, -2.0, 1.42), power=80.0, color=_WARM),
    dict(kind="spot", pos=(2.0, -3.6, 4.08), aim=(2.0, -4.55, 1.85), power=140.0, angle=35, blend=0.5),
    dict(kind="spot", pos=(3.2, -3.6, 4.08), aim=(3.2, -4.55, 1.85), power=140.0, angle=35, blend=0.5),
    dict(kind="spot", pos=(-1.85, -3.7, 4.08), aim=(-1.85, -4.55, 1.7), power=150.0, angle=45, blend=0.5),
    dict(kind="spot", pos=(-5.0, 3.67, 4.08), aim=(-5.0, 3.67, 0.0), power=150.0, angle=40, blend=0.6),
    *_updown(0.75, -4.6, 0, 1), *_updown(4.45, -4.6, 0, 1),
]

PROBE = (0.0, -1.0, 1.6)

# the real bake came out darker than the EEVEE previews the lights were tuned on: lift them all
LIGHTS = [dict(L, power=L["power"] * 1.15) for L in LIGHTS]
