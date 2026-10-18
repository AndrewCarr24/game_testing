"""Courtyard (ground level, open to the sky): 20 x 14 m inside, glass on all four sides,
the only doorway on the south wall at x -1.5..1.5. Local coords: (0, 0) = centre,
+y north. An axial reflecting pool runs north from the doorway forecourt to a water wall;
olive trees in stone bowls stand either side of it, a teak and linen lounge on the east
side, sun loungers on the west, stone troughs of grasses and boxwood round the glass.
No ceiling, so no LIGHTS: sun and sky do the work."""
import importlib

from lib import common, textures

importlib.reload(textures)


def _limestone():
    import courtyard_common
    importlib.reload(courtyard_common)
    return courtyard_common.limestone_mat()


FINISHES = dict(
    floor=_limestone,
    floor_uv_tile=2.0,
)

PLACEMENTS = [
    # reflecting pool on the central axis: forecourt south of it, water wall to the north
    ("courtyard_pool", (0.0, 1.2), 0),
    # olive trees in limestone bowls
    ("courtyard_olive_tree", (-5.4, 2.6), 0),
    ("courtyard_olive_tree", (5.7, 4.0), 137),
    # east lounge: a flat-weave rug, sofa facing west, two armchairs, a stone table
    ("courtyard_rug", (7.2, -2.6), 0),
    ("courtyard_sofa", (8.1, -2.6), -90),
    ("courtyard_coffee_table", (6.7, -2.6), 90),
    ("courtyard_armchair", (6.7, -1.0), 0),
    ("courtyard_armchair", (6.7, -4.2), 180),
    # west: two loungers facing the pool
    ("courtyard_lounger", (-5.3, -1.3), 90),
    ("courtyard_lounger", (-5.3, -3.2), 90),
    # low planting round the glass
    ("courtyard_planter", (-4.8, 6.4), 0),
    ("courtyard_planter", (4.8, 6.4), 0),
    ("courtyard_planter", (-9.45, 1.0), 90),
    ("courtyard_planter", (9.45, 3.5), 90),
    ("courtyard_planter", (-6.0, -6.4), 0),
    ("courtyard_planter", (6.0, -6.4), 0),
]

LIGHTS = []

PROBE = (0.0, 0.0, 1.6)
