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
    ("art_linework_a", (-6.1, 2.4, 1.6), 90),
    ("art_geometric_a", (5.0, 5.1, 1.6), 0),
]

LIGHTS = [
    dict(kind="strip", pos=(0.0, 4.2), size=(6.0, 0.08), power=70.0),
    dict(kind="strip", pos=(0.0, 0.3), size=(7.0, 0.08), power=80.0),
    dict(kind="strip", pos=(0.0, -3.9), size=(11.0, 0.08), power=70.0),
    dict(kind="point", pos=(5.4, 0.0, 2.0), power=25.0, color=(1.0, 0.8, 0.58)),
]

PROBE = (0.0, 0.0, 1.6)
