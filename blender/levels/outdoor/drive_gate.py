"""drive_gate: the drive from the motor court south to the gate in the hedge.

Zone rect x 12..30, y -66..-46, centre world (21, -56). The drive is 8 m overall (7 m gravel
between 0.5 m limestone kerbs, the same as court_paving's drive lane and its 8 m mouth at
world y -46), centred on the garage door (world x 19.75, zone x -1.25). It runs the full 20 m
of the rect and passes through the hedge gap (x 14..25.5) at y -62 (zone y -6). An avenue of
Italian cypress with low bollard lights lines it; two limestone piers with wing walls close
the gap, two slatted steel leaves slide across a limestone apron; the gatehouse stands just
inside, east of the drive, reached by a stepping path.
"""
DX = -1.25                      # drive centre line (zone x)
GATE_Y = -6.0                   # the hedge line (zone y)
PIER = 4.6                      # pier centre from the drive centre line (inner faces at +-4.0)

PLACEMENTS = [
    ("gate_drive", (DX, 0), 0),
    # gate
    ("gate_pier", (DX - PIER, GATE_Y), 0),
    ("gate_pier", (DX + PIER, GATE_Y), 180),
    ("gate_leaf", (DX - 1.98, GATE_Y), 0),
    ("gate_leaf", (DX + 1.98, GATE_Y), 0),
    ("gate_keypad", (DX - 4.5, GATE_Y - 2.2), 90),
    # gatehouse, east of the drive, door facing west onto a stepping path from the kerb
    ("gate_gatehouse", (7.1, -1.0), -90),
    ("gate_path", (DX + 4.0, -1.0), -90),
]

# bollards between the cypresses, just outside the kerbs (the east one at y -1 gives way to the path)
for _y in (7, 3, -1, -9.5):
    PLACEMENTS.append(("gate_bollard", (DX - 4.3, _y), 0))
    PLACEMENTS.append(("gate_bollard", (DX + 4.3, _y if _y != -1 else -2.5), 0))

# the cypress avenue: four pairs, 4 m apart
for _y in (9, 5, 1, -3):
    PLACEMENTS.append(("plant_tree_cypress", (DX - 5.2, _y), 0))
    PLACEMENTS.append(("plant_tree_cypress", (DX + 5.2, _y), 0))

# ornamental grass drifts at the cypress feet, between the bollards
for _y in (7, 3, -1):
    PLACEMENTS.append(("plant_shrub_grass", (DX - 5.2, _y), 17 * _y))
for _y in (7, 3):
    PLACEMENTS.append(("plant_shrub_grass_b", (DX + 5.2, _y), 31 * _y))

# clipped box either side of the gatehouse
for _x in (5.8, 7.1, 8.4):
    PLACEMENTS.append(("plant_shrub_box", (_x, 1.8), 0))
    PLACEMENTS.append(("plant_shrub_box", (_x, -3.8), 0))
