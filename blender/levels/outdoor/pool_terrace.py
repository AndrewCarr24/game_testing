"""Pool terrace: zone-local metres, (0, 0) = rect centre (world 8, 38.5), z = 0 the lawn.
A raised limestone deck (0.45 m) carrying a 25 x 6 m lap pool whose north long side is an
infinity edge, a sun shelf at the west end, teak loungers in pairs with two cantilever
umbrellas, parapet bench walls, and a pair of planters flanking the broad south steps."""
DECK = 0.45
SHELF = 0.31

PLACEMENTS = [
    ("pool_deck", (0, 0), 0),
    # parapet bench walls along the south edge, either side of the steps
    ("pool_bench_wall", (-10.2, -9.75, DECK), 0),
    ("pool_bench_wall", (10.2, -9.75, DECK), 0),
    # planters flanking the steps
    ("pool_planter", (-5.5, -9.3, DECK), 0),
    ("pool_planter", (5.5, -9.3, DECK), 0),
    # lounger pairs facing the pool (rotation 180: feet to the north)
    ("pool_lounger_pair", (-10.0, -6.5, DECK), 180),
    ("pool_lounger_pair", (-3.5, -6.5, DECK), 180),
    ("pool_lounger_pair", (3.5, -6.5, DECK), 180),
    ("pool_lounger_pair", (10.0, -6.5, DECK), 180),
    # cantilever umbrellas behind two pairs, canopy reaching over the loungers
    ("pool_umbrella", (-10.0, -8.4, DECK), 0),
    ("pool_umbrella", (10.0, -8.4, DECK), 0),
    # in-water loungers on the sun shelf, head at the west wall, feet east
    ("pool_lounger_low", (-12.3, -1.8, SHELF), 90),
    ("pool_lounger_low", (-12.3, 0.6, SHELF), 90),
    # outdoor shower at the east end of the deck
    ("pool_shower", (14.2, 0.6, DECK), -90),
    # beyond the infinity edge: clipped yew hedge with a gap on the office's axis, grasses in front
    ("pool_hedge", (-7.5, 10.2), 0),
    ("pool_hedge", (8.0, 10.2), 0),
    ("plant_shrub_grass", (-11.6, 8.6), 20), ("plant_shrub_grass_b", (-9.9, 8.4), 150),
    ("plant_shrub_grass", (-8.3, 8.6), 80), ("plant_shrub_grass_b", (-6.6, 8.5), 250),
    ("plant_shrub_grass_b", (5.3, 8.5), 40), ("plant_shrub_grass", (7.0, 8.6), 200),
    ("plant_shrub_grass_b", (8.7, 8.4), 110), ("plant_shrub_grass", (10.4, 8.6), 300),
]
