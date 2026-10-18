"""West garden: a formal axial garden on the great room's centre line (world y = 0).

Composition, in the garden frame (u west-east from the pool's centre, world x = -46.5 + u;
v north-south, world y = v): a 27 m reflecting pool on the axis, stone walks either side,
a gravel parterre of clipped box cubes beyond each walk, an allée of olive trees, clipped
yew hedge walls at +-13.2 m, and at the far (west) end a bronze ribbon sculpture on a plinth
against a stepped white wall. Zone-local coordinates: (0, 0) = rect centre (-48.5, 1.5).
"""
CX, CY = 2.0, -1.5          # the garden frame's origin (pool centre) in zone-local metres
PAVE_Z = 0.06
GRAVEL_Z = 0.04


def at(u, v, z=0.0):
    return (CX + u, CY + v, z) if z else (CX + u, CY + v)


PLACEMENTS = [
    ("garden_pool", at(0, 0), 0),
    ("garden_paving", at(0, 0), 0),
    ("garden_parterre", at(0, 0), 0),
    ("garden_hedges", at(0, 0), 0),
    ("garden_wall", at(0, 0), 0),
    ("garden_sculpture", at(0, 0), 0),
    # benches in the parterre gaps, facing the pool (front faces -y)
    ("garden_bench", at(0, 6.1, PAVE_Z), 0),
    ("garden_bench", at(0, -6.1, PAVE_Z), 180),
    # planters on the landing, beside the great room's glass wall
    ("garden_planter", at(14.5, 7.2, PAVE_Z), 0),
    ("garden_planter", at(14.5, -7.2, PAVE_Z), 0),
]

# olive allée: three a side (variants of the planting agent's olive), the middle pair behind the benches
_OLIVES = ("plant_tree_olive", "plant_tree_olive_b", "plant_tree_olive_c")
for _i, _u in enumerate((-9.0, 0.0, 9.0)):
    PLACEMENTS.append((_OLIVES[_i % 3], at(_u, 9.6), 70 * _i))
    PLACEMENTS.append((_OLIVES[(_i + 1) % 3], at(_u, -9.6), 55 * _i + 30))
# cypress frame the sculpture court
for _i, _u in enumerate((-17.0, -12.0)):
    PLACEMENTS.append(("plant_tree_cypress" if _i == 0 else "plant_tree_cypress_b", at(_u, 9.6), 0))
    PLACEMENTS.append(("plant_tree_cypress_b" if _i == 0 else "plant_tree_cypress", at(_u, -9.6), 0))
