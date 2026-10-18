"""Fire garden: a raised circular limestone terrace with a built-in curved bench and a
central fire bowl, ringed by a low clipped hedge, seen from the dining room (ground) and
the primary bedroom (upper). A gravel axis runs north from the house terrace through the
hedge opening on the dining window's centre line (world x = -18) to the fire; a second
path runs west from it to a small petanque court with teak benches, a third east toward
the pool deck, a fourth north to a limestone stele framed by two cypress.

Zone-local metres: (0, 0) = rect centre (world -28, 41.5). Positions below are written in
world metres and converted by w(); the fire's centre is world (-18, 38.9). The terrace top
is 0.2 m above the lawn.
"""
import math as _m

CX, CY = -28.0, 41.5         # the zone rect's centre in world metres
FX, FY = -18.0, 38.9         # fire centre, world
TZ = 0.20                    # terrace top


def w(wx, wy, z=0.0):
    """World metres -> zone-local placement position."""
    return (wx - CX, wy - CY, z) if z else (wx - CX, wy - CY)


def f(dx, dy, z=0.0):
    """Offset from the fire centre (+x east, +y north)."""
    return w(FX + dx, FY + dy, z)


PLACEMENTS = [
    ("firepit_terrace", f(0, 0), 0),
    ("firepit_hedge_ring", f(0, 0), 0),
    ("firepit_bench", f(0, 0, TZ), 0),
    ("firepit_bowl", f(0, 0, TZ), 0),
    # paths: south (from the house terrace y = 25 to the terrace), west (court), north (stele), east
    ("firepit_path_long", w(FX, 29.5), 0),
    ("firepit_path_long", w(-27.4, FY), 90),
    ("firepit_path_long", w(FX, 48.3), 0),
    ("firepit_path_short", w(-10.85, FY), 90),
    # petanque court west of the west path (its sleeper meets the path end at x = -31.9)
    ("firepit_court", w(-38.05, FY), 0),
    ("firepit_teak_bench", w(-35.0, FY + 2.75), 0),
    # north terminus
    ("firepit_stele", w(FX, 54.3), 0),
    ("plant_tree_cypress", w(FX - 2.3, 54.3), 0),
    ("plant_tree_cypress", w(FX + 2.3, 54.3), 0),
]

# four lounge chairs facing the fire, flanking the south entrance
for _az in (205, 235, 305, 335):
    PLACEMENTS.append(("firepit_lounge_chair",
                       f(2.9 * _m.cos(_m.radians(_az)), 2.9 * _m.sin(_m.radians(_az)), TZ), _az - 90))

# bollards along the south path
for _sx in (-1.35, 1.35):
    for _y in (28.5,):
        PLACEMENTS.append(("firepit_bollard", w(FX + _sx, _y), 0))

# planting beds flanking the south and west paths, drifts of grass and lavender
BED_Z = 0.05
for _sx, _kinds in ((-2.25, ("lavender", "grass", "lavender")), (2.25, ("grass", "lavender", "grass"))):
    PLACEMENTS.append(("firepit_bed", w(FX + _sx, 28.5), 0))
    for _k, _dy in zip(_kinds, (-1.35, 0.0, 1.35)):
        PLACEMENTS.append((f"plant_shrub_{_k}", w(FX + _sx, 28.5 + _dy, BED_Z), (60 * int(_dy * 3)) % 360))
for _sy, _kinds in ((-2.25, ("grass", "lavender", "grass")), (2.25, ("lavender", "grass", "lavender"))):
    PLACEMENTS.append(("firepit_bed", w(-29.0, FY + _sy), 90))
    for _k, _dx in zip(_kinds[:2], (-0.7, 0.7)):
        PLACEMENTS.append((f"plant_shrub_{_k}", w(-29.0 + _dx, FY + _sy, BED_Z), (75 * int(_dx * 3) + 20) % 360))
