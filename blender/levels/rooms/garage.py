"""Garage (ground floor, south-east): 12.2 x 19.7 m inside, 4.2 m high. The garage door
is the south wall (x -4.25..4.25); the mudroom door is on the north wall at x = 0.
A car showroom in polished concrete and graphite: two display bays at (-3, -5.5) and
(+3, -5.5) (the orchestrator places the cars there), two more at (+-3, +1.5), a lit
vitrine and an EV charger on each side wall, cabinetry and a workbench on the west half
of the north wall, a tool wall on the east half, and long strip lights."""
import importlib
import os

import numpy as np

from lib import common, textures

importlib.reload(textures)


def _concrete_texture(n=1024, force=False):
    """Polished concrete slab: 6 m x 6 m tile (saw-cut joints on the tile edges),
    soft trowel clouds, fine aggregate speckle and a few hairline cracks."""
    path = os.path.join(textures.TEX_DIR, "T_Garage_Concrete_BaseColor.png")
    if os.path.exists(path) and not force:
        return path
    rng = np.random.default_rng(77)
    cloud = textures._noise(n, 1.0, 1.0, 2.0, rng)
    mid = textures._noise(n, 1.0, 1.0, 1.2, rng)
    fine = textures._noise(n, 1.0, 1.0, 0.2, rng)
    streak = textures._noise(n, 0.15, 1.0, 1.4, rng)         # trowel direction
    t = 0.5 + 0.30 * cloud + 0.12 * mid + 0.05 * fine + 0.08 * streak
    spec = rng.random((n, n)) < 0.004                           # aggregate flecks
    lin = 0.205 * (0.80 + 0.40 * np.clip(t, 0, 1))
    lin = np.where(spec, lin * 0.65, lin)
    # saw-cut joints on the tile edges (2 px wide) with a soft shadow
    d = np.minimum(np.arange(n), n - 1 - np.arange(n)).astype(np.float32)
    joint_x = np.clip(1.0 - d / 5.0, 0, 1)[None, :]
    joint_y = np.clip(1.0 - d / 5.0, 0, 1)[:, None]
    joint = np.maximum(joint_x, joint_y)
    lin = lin * (1 - 0.55 * joint)
    rgb = np.stack([lin * 1.0, lin * 0.995, lin * 0.975], axis=-1)
    return textures._save("T_Garage_Concrete_BaseColor", textures._to_srgb(rgb))


def _floor():
    m = common.pbr_material("M_Garage_PolishedConcrete", (0.2, 0.2, 0.2), roughness=0.22, coat=0.4)
    common.set_base_color_map(m, textures.load(_concrete_texture()))
    return m


FINISHES = dict(
    floor=_floor,
    floor_uv_tile=6.0,
    walls=lambda: common.pbr_material("M_Garage_Wall", (0.27, 0.27, 0.265), roughness=0.9),
    ceiling=lambda: common.pbr_material("M_Garage_Ceiling", (0.62, 0.62, 0.61), roughness=0.9),
    walls_by_side={"N": lambda: common.pbr_material("M_Garage_WallDark", (0.07, 0.072, 0.076), roughness=0.85)},
)

CAR_Y = -5.5
PLACEMENTS = [
    # parking bays marked in the floor (cars come at the two south bays)
    ("garage_bay", (-3.0, CAR_Y), 0),
    ("garage_bay", (3.0, CAR_Y), 0),
    ("garage_bay", (-3.0, 1.5), 0),
    ("garage_bay", (3.0, 1.5), 0),
    # display cases on the side walls, level with the cars
    ("garage_vitrine", (-5.89, -6.5), 90),
    ("garage_vitrine", (5.89, -6.5), -90),
    # walnut slat feature walls behind the workshop end of each side wall
    ("garage_slatwall", (-6.055, 5.6), 90),
    ("garage_slatwall", (6.055, 5.6), -90),
    # EV charging posts (back against the wall)
    ("garage_ev_charger", (-6.03, -3.4), 90),
    ("garage_ev_charger", (6.03, -3.4), -90),
    ("garage_ev_charger", (-6.03, 1.5), 90),
    ("garage_ev_charger", (6.03, 1.5), -90),
    # north wall: cabinetry (west) and the tool wall (east), either side of the mudroom door
    ("garage_cabinets", (-3.9, 9.53), 0),
    ("garage_toolwall", (3.9, 9.6), 0),
    # workshop island on the west side, stools facing south
    ("garage_workbench", (-3.0, 6.7), 0),
]

# Lighting: a car showroom is where long ceiling lines are the right answer, so the garage
# keeps its four (and the workshop's); added: pairs of ceiling cans over the two display bays
# so the cars' paint catches tight highlights, and the vitrines' glow.
_CAR_CANS = [(sx * 3.0, y) for sx in (-1, 1) for y in (-4.3, -6.7)]
PLACEMENTS += [("light_g_downlight", (x, y, 4.2), 0) for x, y in _CAR_CANS]
LIGHTS = [
    dict(kind="strip", pos=(-4.5, -0.5), size=(0.1, 17.0), power=180.0),
    dict(kind="strip", pos=(-1.5, -0.5), size=(0.1, 17.0), power=180.0),
    dict(kind="strip", pos=(1.5, -0.5), size=(0.1, 17.0), power=180.0),
    dict(kind="strip", pos=(4.5, -0.5), size=(0.1, 17.0), power=180.0),
    dict(kind="strip", pos=(0.0, 8.4), size=(11.0, 0.1), power=160.0),
    dict(kind="point", pos=(-5.0, -6.5, 2.2), power=40.0, color=(1.0, 0.82, 0.6)),
    dict(kind="point", pos=(5.0, -6.5, 2.2), power=40.0, color=(1.0, 0.82, 0.6)),
    *[dict(kind="spot", pos=(x, y, 4.08), aim=(x, y, 0.0), power=300.0, angle=36, blend=0.5, color=(1.0, 0.92, 0.84))
      for x, y in _CAR_CANS],
]

PROBE = (0.0, -1.0, 1.6)


# the two cars, in the bays left for them (placed by the orchestrator), facing the garage door
PLACEMENTS += [
    ("car_ev", (-3.0, -5.5), 0),
    ("car_ev_ink", (3.0, -5.5), 0),
]
