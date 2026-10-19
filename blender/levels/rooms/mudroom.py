"""Mudroom (ground floor, between the gallery and the garage): 12.2 x 10.2 m inside.
Garage door on the south wall (x = 0), gallery door on the west wall (y = -1.75), a
window on the east wall (y -2.25..2.25, sill 0.9 m).
A smart utility room in cream, light oak and sage: locker walls either side of the
garage door, a laundry wall (washer, dryer, sink, folding counter) on the north wall,
an island with stools, and a window seat under the east window."""
import importlib
import os

import numpy as np

from lib import common, textures

importlib.reload(textures)


def _tile_texture(n=1024, force=False):
    """Large-format warm stone tile: 2 x 2 tiles of 0.6 m per 1.2 m texture tile,
    cloudy veining per tile, 2 mm grout lines."""
    path = os.path.join(textures.TEX_DIR, "T_Garage_MudroomTile_BaseColor.png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(55)
    u = np.arange(n)[None, :] * np.ones((n, 1))
    v = np.arange(n)[:, None] * np.ones((1, n))
    half = n // 2
    tx, ty = (u // half).astype(int), (v // half).astype(int)
    tone = (rng.uniform(-1, 1, (2, 2)))[ty, tx]
    cloud = textures._noise(n, 1.0, 1.0, 2.0, rng)
    vein = textures._noise(n, 1.0, 1.0, 1.0, rng)
    t = 0.55 + 0.25 * cloud + 0.08 * vein + 0.06 * tone
    base = np.array([0.36, 0.33, 0.29])
    lin = base[None, None, :] * (0.82 + 0.36 * np.clip(t, 0, 1))[..., None]
    du = np.minimum(u % half, half - 1 - (u % half))
    dv = np.minimum(v % half, half - 1 - (v % half))
    d = np.minimum(du, dv)
    grout = np.clip(1.0 - d / 2.0, 0, 1)
    lin = lin * (1 - grout[..., None]) + np.array([0.15, 0.145, 0.135]) * grout[..., None]
    return textures._save("T_Garage_MudroomTile_BaseColor", textures._to_srgb(lin))


def _floor():
    m = common.pbr_material("M_Mudroom_Tile", (0.5, 0.5, 0.5), roughness=0.4, coat=0.15)
    common.set_base_color_map(m, textures.load(_tile_texture()))
    return m


FINISHES = dict(
    floor=_floor,
    floor_uv_tile=1.2,
    walls=lambda: common.pbr_material("M_Plaster_Cream", (0.36, 0.325, 0.27), roughness=0.9),
    ceiling=lambda: common.pbr_material("M_Ceiling_Warm", (0.48, 0.46, 0.43), roughness=0.9),
)

# lighting: ceiling cans (x, y): four over the lockers, two over the laundry wall, then the
# boot mat and the drawing (see LIGHTS)
_CANS = ((-5.0, -3.75), (-2.9, -3.75), (2.9, -3.75), (5.0, -3.75), (-1.6, 3.95), (1.6, 3.95),
         (0.0, -3.2), (5.0, 4.1))

PLACEMENTS = [
    # lockers either side of the garage door (backs on the south wall)
    ("garage_lockers", (-3.95, -4.82), 180),
    ("garage_lockers_b", (3.95, -4.82), 180),
    # laundry wall, north
    ("garage_laundry", (0.0, 4.78), 0),
    # island with stools (stools on the south side)
    ("garage_island", (0.6, 0.9), 0),
    # rugs: oat wool under the island, a charcoal boot mat in front of the garage door
    ("bedroom_rug", (0.6, 0.5), 0),
    ("rug", (0.0, -3.4), 90),
    # window seat under the east window
    ("garage_seat", (5.82, 0.0), -90),
    # art
    ("art_contour_map", (5.0, 5.1, 1.6), 0),             # topographic drawing, white box frame
    # lighting (see LIGHTS): a linear pendant over the island, up/down sconces either side of
    # the window seat, ceiling cans washing the lockers and the laundry wall
    ("light_g_pendant_linear", (0.6, 0.9, 4.2), 0),
    ("light_g_sconce_updown", (6.1, 2.75, 2.25), -90),
    ("light_g_sconce_updown", (6.1, -2.75, 2.25), -90),
    *[("light_g_downlight", (x, y, 4.2), 0) for x, y in _CANS],
]

# Lighting: a crisp utility room without ceiling lines. The linear bronze pendant over the
# oak island is the focus; the locker walls and the laundry wall are washed by cans (and the
# worktop has its LED under the wall units); bronze sconces flank the window seat; a can
# over the boot mat at the garage door and one on the drawing. Slightly cooler white.
_WORK = (1.0, 0.88, 0.76)


def _updown(x, y, wx, wy, up=40.0, down=50.0):
    """The two scallops of a light_g_sconce_updown at (x, y) on a wall, 0.13 m out along (wx, wy)."""
    px, py = x + 0.13 * wx, y + 0.13 * wy
    return [dict(kind="spot", pos=(px, py, 2.40), aim=(px, py, 4.2), power=up, angle=60, blend=0.7),
            dict(kind="spot", pos=(px, py, 2.10), aim=(px, py, 0.0), power=down, angle=60, blend=0.7)]


LIGHTS = [
    # linear pendant over the island (underside 1.7 m): down, and a glow on the ceiling
    dict(kind="area", pos=(0.6, 0.9, 1.69), size=(1.5, 0.05), aim=(0.6, 0.9, 0.0), power=130.0, color=(1.0, 0.8, 0.58)),
    dict(kind="area", pos=(0.6, 0.9, 1.76), size=(1.5, 0.05), aim=(0.6, 0.9, 4.2), power=30.0, color=(1.0, 0.8, 0.58)),
    # LED under the laundry wall units (garage_laundry Under_LED, z 1.58)
    dict(kind="area", pos=(0.0, 4.80, 1.56), size=(4.5, 0.04), aim=(0.0, 4.6, 0.92), power=60.0, color=_WORK),
    # cans: lockers, laundry wall, boot mat, the drawing
    *[dict(kind="spot", pos=(x, y, 4.08), aim=(x, y - 0.75 if y < 0 else y + 0.75, 1.2), power=170.0, angle=50, blend=0.6,
           color=_WORK) for x, y in _CANS[:6]],
    dict(kind="spot", pos=(0.0, -3.2, 4.08), aim=(0.0, -3.2, 0.0), power=200.0, angle=45, blend=0.6, color=_WORK),
    dict(kind="spot", pos=(5.0, 4.1, 4.08), aim=(5.0, 5.05, 1.6), power=110.0, angle=32, blend=0.5),
    *_updown(6.1, 2.75, -1, 0), *_updown(6.1, -2.75, -1, 0),
]

PROBE = (0.0, 0.0, 1.6)

# the real bake came out darker than the EEVEE previews the lights were tuned on: lift them all
LIGHTS = [dict(L, power=L["power"] * 1.35) for L in LIGHTS]

# set dressing (decor_b_*; the lockers are dressed already): keys and post on the island by
# the garage door, a folded throw on the window seat with a basket of blankets beside it, a
# bird of paradise in the north-west corner
PLACEMENTS += [
    ("decor_b_vignette_keys", (1.6, 0.82, 0.92), 90),
    ("decor_b_throw_folded", (5.78, -1.83, 0.49), -90),
    ("decor_b_basket_blankets", (5.65, -2.58), 15),
    ("decor_b_plant_floor_b", (-5.55, 4.55), 120),
]
