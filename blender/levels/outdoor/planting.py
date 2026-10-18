"""Estate planting: trees along the perimeter hedge and in the free corners between zones,
plus low beds just outside the east terrace edge. Zone-local = plan coordinates (the
estate centre is (0, 0)); trunks stay inside the hedge and outside every other zone's rect
(canopies may overhang them), and the big windows' views are left open.

Free ground used (everything else belongs to another zone):
  north band   y 58..61 behind fire_garden / pool_house, y 52..61 behind the pool terrace
  NW corner    x -66..-48, y 25..58          west band  x -70..-66
  south centre x -14..12, y -66..-46 (in front of the entry glass)
  east band    x 68..69.3 behind the tennis court;  x 31..33 strip outside the east terrace
"""

R, RB = "plant_tree_round", "plant_tree_round_b"
O, OB, OC = "plant_tree_olive", "plant_tree_olive_b", "plant_tree_olive_c"
M, MB = "plant_tree_multistem", "plant_tree_multistem_b"
C, CB = "plant_tree_cypress", "plant_tree_cypress_b"
SR, SB = "plant_shrub_round", "plant_shrub_box"
G, GB = "plant_shrub_grass", "plant_shrub_grass_b"
L, LB = "plant_shrub_lavender", "plant_shrub_lavender_b"

PLACEMENTS = [
    # ---- north: the view from the kitchen / office / gym / dining / primary bedroom ----------
    # behind the fire garden (x -48..-8): a loose screen against the hedge
    (C, (-46.5, 60.3), 20), (CB, (-43.6, 59.5), 130), (OB, (-39.0, 58.9), 40), (CB, (-27.8, 60.4), 70),
    # behind the pool terrace (x -8..24): deeper bosque, off the office's centre line
    (OC, (-4.5, 56.2), 300), (C, (-1.3, 60.4), 10), (CB, (1.2, 60.9), 160),
    (MB, (8.5, 58.3), 120), (C, (12.5, 60.6), 330), (R, (18.5, 56.5), 35),
    # behind the pool house (x 24..66)
    (C, (29.5, 60.2), 200), (CB, (32.6, 59.6), 20), (O, (38.5, 59.4), 150),
    (C, (59.8, 59.5), 110),
    # ---- NW corner (x -66..-48, y 25..58) ------------------------------------------------------
    (RB, (-57.5, 41.0), 80), (OC, (-52.5, 31.5), 10), (MB, (-53.0, 52.5), 150), (C, (-65.0, 56.5), 300),
    # ---- west band (x -69..-66): frames the great room's view, centre kept open ------------------
    (C, (-68.3, -7.4), 15), (O, (-67.4, -14.0), 255),
    (CB, (-68.0, 11.8), 200), (M, (-67.3, 15.4), 20), (C, (-67.2, 20.2), 330),
    # ---- south-west: the south lawn's edge --------------------------------------------------------
    (CB, (-68.1, -56.0), 140), (C, (-30.2, -60.6), 100),
    # ---- south centre, in front of the entry glass: two groups, the axis kept open --------------
    (R, (-9.5, -57.0), 250), (CB, (-13.0, -59.0), 170),
    (OB, (9.0, -52.5), 130), (M, (6.0, -58.0), 300), (C, (11.0, -58.9), 60),
    # ---- south-east hedge (kitchen garden's edge) ------------------------------------------------
    (CB, (40.0, -60.7), 70),
    # ---- east band behind the tennis court (x 68..69.3) --------------------------------------------
    (C, (68.9, -10.0), 10), (CB, (68.9, 11.5), 300), (MB, (68.4, 2.5), 160),
    # ---- beds just outside the east terrace edge (x 31..33), low so the windows stay open --------
    (SB, (32.0, -17.5), 0), (G, (32.1, -14.6), 20), (L, (32.0, -12.9), 0),
    (SR, (32.0, 11.5), 0), (LB, (32.0, 13.3), 30), (G, (32.0, 15.4), 160),
    (SB, (32.0, 19.0), 0),
    # ---- the gap south-west of the terrace (x -66..-31, y -25..-22) -------------------------------
    (GB, (-33.0, -23.6), 200), (LB, (-35.6, -23.8), 20), (SR, (-37.6, -23.5), 0),
]
