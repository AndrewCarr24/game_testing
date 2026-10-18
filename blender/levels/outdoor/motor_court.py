"""Motor court: the arrival court in front of the entry glass wall and the garage door.

Zone rect x -14..30, y -46..-25 (world); zone-local (0, 0) = (8, -35.5) world, +x east,
+y north. World -> local: x - 8, y + 35.5. The paving asset is built in these local
coordinates (field x -21..21, y -10.5..10.5), the fountain sits on the entry's centre line
(world x 0 = local -8), the canopy is on the terrace band in front of the glass (world
(0, -22.5) = local (-8, 13)), and the garage door (world x 15.5..24) is local x 7.5..16.
The drive from drive_gate arrives through the south band's opening, local x 7.75..15.75
(world 15.75..23.75, centre 19.75), at local y -10.5 (world y -46).
"""

CX, CY = 8.0, -35.5


def W(x, y):
    """World plan coordinates -> zone-local."""
    return (round(x - CX, 3), round(y - CY, 3))


PLANTER_SOIL = 0.88          # top of the soil in court_planter (m above the planter's base: 0.95 - 0.07)
GRAVEL = 0.04              # gravel surface (the limestone banding and the terrace are at 0.06)

PLACEMENTS = [
    ("court_paving", (0, 0), 0),
    ("court_fountain", (-8, 0), 0),
    ("court_canopy", (-8, 13, 0.06), 0),
]

# stone benches on the plaza, facing the fountain (west, east, south; the path comes in from the north)
for (bx, by, rot) in [(-13.2, 0.0, 90), (-2.8, 0.0, -90), (-8.0, -5.2, 180)]:
    PLACEMENTS.append(("court_bench", (bx, by, 0.06), rot))

# four multi-stem trees in limestone planters round the fountain, world x = +/-10.5 (outside
# the entry glass, framing the view down its axis), world y -30 and -41
for (px, py) in [(-18.5, 5.5), (-18.5, -5.5), (2.5, 5.5), (2.5, -5.5)]:
    PLACEMENTS.append(("court_planter", (px, py, GRAVEL), 0))
    PLACEMENTS.append(("plant_tree_multistem", (px, py, GRAVEL + PLANTER_SOIL), 0))

# clipped boxwood balls lining the drive lane to the garage apron, outside the stone edging
for by in (-5.5, -1.5, 2.5):
    for bx in (7.0, 16.5):
        PLACEMENTS.append(("plant_shrub_round", (bx, by, GRAVEL), 0))

# bollard lights on the court's edges: along the entry path, drive mouth, apron, borders
for (bx, by) in [(-11.7, 9.3), (-4.3, 9.3),                 # entry path
                 (6.4, 5.0), (17.1, 5.0),                   # apron ends
                 (7.3, -9.0), (16.2, -9.0),                 # drive mouth
                 (-19.3, 0.0), (19.3, -6.5), (19.3, 0.0), (19.3, 6.5)]:   # side borders
    PLACEMENTS.append(("court_bollard", (bx, by, 0), 0))
