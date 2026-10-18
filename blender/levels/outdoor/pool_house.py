"""Pool house zone (rect x 24..66, y 25..58; zone-local (0, 0) = its centre, world (45, 41.5)).

Layout (zone-local metres, +x east, +y north):
  pavilion   14 x 7 m glass-fronted pool pavilion on a stone plinth, glass facing WEST (the lap
             pool), its long axis north-south at x -8 (world 37), y -3..11 (world 38.5..52.5)
  forecourt  limestone terrace x -14.2..13.5, y -14.5..-3.4 (south of the pavilion, nearest the
             house): the outdoor kitchen (counter + back wall) and the dining table for ten under
             a teak-and-metal pergola
  slabs      stone stepping slabs in the lawn from the pool deck (east edge x -21) to the pavilion
             terrace and to the forecourt
"""
PAV = (-8.0, 4.0)          # pavilion centre; the asset is turned -90 so its glass front faces west
PERG = (6.5, -8.95)        # pergola / dining centre on the forecourt
ROT = -90.0
FLOOR = 0.30


def pav(ax, ay, rot=0.0, z=FLOOR):
    """A point (ax, ay) in the pavilion's own frame (front/glass toward -y) -> zone placement."""
    return (PAV[0] + ay, PAV[1] - ax, z), ROT + rot


def at(asset, ax, ay, rot=0.0, z=FLOOR):
    p, r = pav(ax, ay, rot, z)
    return (asset, p, r)


PLACEMENTS = [
    # --- the pavilion and what is glimpsed through its glass
    ("cabana_pavilion", (PAV[0], PAV[1]), ROT),
    at("cabana_lounge", -3.6, -0.1),
    at("cabana_daybed", 1.7, 2.1),
    at("cabana_bar", 4.7, 0.0, -90),
    # covered terrace in front of the glass
    at("cabana_armchair", -5.4, -4.7, 20),
    at("cabana_side_table", -4.3, -4.9),
    at("cabana_armchair", -3.2, -4.7, -20),
    # --- forecourt: paving, pergola, outdoor kitchen, dining
    ("cabana_paving", (-0.35, -8.95), 0),
    ("cabana_pergola", (PERG[0], PERG[1], 0.12), 0),
    ("cabana_kitchen", (PERG[0], PERG[1] + 2.2, 0.12), 0),
    ("cabana_dining", (PERG[0], PERG[1] - 0.6, 0.12), 0),
    # --- stepping slabs from the pool deck
    *[("cabana_slab", (x, 4.0 + (0.12 if i % 2 else -0.12)), 0) for i, x in enumerate((-20.2, -18.8, -17.4, -16.0))],
    *[("cabana_slab", (x, -9.0 + (0.12 if i % 2 else -0.12)), 0) for i, x in enumerate((-20.4, -19.0, -17.6, -16.2, -14.9))],
    # --- planting: cypress rhythm east of the forecourt, clipped box cubes along its north edge
    *[("plant_tree_cypress", (16.2, y), 0) for y in (-4.5, -9.0, -13.5)],
    *[("plant_shrub_box", (x, -2.2), 0) for x in (-1.0, 1.6, 4.2, 6.8, 9.4, 12.0)],
    # clipped box cubes either side of the stepping-slab entry to the pavilion terrace, one cypress behind
    ("plant_shrub_box", (-17.4, 6.6), 0),
    ("plant_shrub_box", (-17.4, 1.4), 0),
    ("plant_tree_cypress", (-2.0, 11.0), 0),
]
