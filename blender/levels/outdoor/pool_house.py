"""Pool house zone (rect x 24..66, y 25..58; zone-local (0, 0) = its centre, world (45, 41.5)).

The pool house is now the bathhouse, a building of the house's plan (blender/levels/
bathhouse_plan.py: footprint world x 27..45, y 31..48.5 = local x -18..0, y -10.5..7; its rooms
are lit and dressed like the house's). This zone dresses what's round it (design:
design/grounds/pool_house.md):

  west     stepping slabs across the lawn from the lap pool deck's east steps to the bath hall's
           glass door; a cedar lattice veil hung on the hall's glass above head height (its stripes
           of low sun fall across the hall; the lower glass stays clear: the view down the water)
  south    stepping slabs from the house's terrace to the bathhouse door
  east     the garden court (limestone), the outdoor kitchen and the dining pergola, off the fire
           bath's door; a river birch outside the cold room's slit window
  north    a long black reflecting pool under the rest room's window, cypresses beyond
"""


def W(x, y):
    """World -> zone-local."""
    return (x - 45.0, y - 41.5)


COURT = W(52.5, 34.5)          # garden court centre (14.6 x 11 m: x 45.2..59.8, y 29..40)
PERG = COURT

PLACEMENTS = [
    # --- west: the veil on the hall's glass (its frame: x 27, y 31..44.5)
    ("cabana_veil", W(27.0, 37.75), 0),
    # stepping slabs from the deck's east steps (world x 22.6, y 30..35) to the hall's door (y 32.5..34)
    *[("cabana_slab", W(x, 33.25 + (0.1 if i % 2 else -0.1)), 90) for i, x in enumerate((23.35, 24.55, 25.75))],
    # --- south: from the house terrace (y 25) to the door (x 29.6..30.7)
    *[("cabana_slab", W(30.15 + (0.12 if i % 2 else -0.12), y), 0) for i, y in enumerate((25.8, 27.0, 28.2, 29.4, 30.5))],
    # --- east: the court off the fire bath's door (x 45, y 32.35..33.45)
    ("cabana_court", COURT, 0),
    ("cabana_pergola", (PERG[0], PERG[1], 0.12), 0),
    ("cabana_kitchen", (PERG[0], PERG[1] + 2.2, 0.12), 0),
    ("cabana_dining", (PERG[0], PERG[1] - 0.6, 0.12), 0),
    *[("plant_tree_cypress", W(61.2, y), 0) for y in (37.0, 32.5, 28.0)],
    ("plant_tree_multistem", W(49.2, 41.6), 40),     # framed by the cold room's slit (world y 41.35..41.85)
    # --- north: the reflecting pool under the rest room's window (x 28.5..43.5 at y 48.5)
    ("cabana_mirror_pool", W(36.0, 51.4), 0),
    ("plant_tree_cypress", W(31.5, 55.2), 0),
    ("plant_tree_cypress", W(47.5, 54.6), 0),
    ("plant_tree_multistem_b", W(40.5, 55.6), 200),
]
