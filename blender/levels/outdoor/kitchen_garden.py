"""Kitchen garden (south-east): zone-local metres, (0, 0) = centre of x 30..68, y -60..-25.
+x east, +y north (towards the house), rotation 0 = front faces -y (south).

Layout: a gravel cross of walks (dark-metal edged) with the main E-W axis ending at the
greenhouse door and the N-S axis ending at a bench under a clipped yew hedge. Eight
raised beds fill the four blocks between the walks (tall bean A-frames at the back), the
potting shed sits at the end of the north walk, and the orchard stands to the north and
south of the beds.
"""

PLACEMENTS = [
    # ---- greenhouse (door in the west gable, facing the main axis) -------------------
    ("kgarden_greenhouse", (9.0, 0.0), -90),
    ("kgarden_trough", (1.65, 2.5), 0),

    # ---- walks ----------------------------------------------------------------------
    ("kgarden_path_main", (-14.125, 0.0), 0),
    ("kgarden_path_main", (-3.875, 0.0), 0),
    ("kgarden_path_node", (-9.0, 0.0), 0),
    ("kgarden_path_main", (-14.125, 7.9), 0),
    ("kgarden_path_north", (1.025, 7.9), 0),
    ("kgarden_path_node", (-9.0, 7.9), 0),
    ("kgarden_path_main", (-9.0, -5.125), 90),
    ("kgarden_path_arm_mid", (-9.0, 3.95), 90),
    ("kgarden_path_arm_end", (-9.0, 12.075), 90),
    ("kgarden_bollard", (-16.6, 1.2), 0),
    ("kgarden_bollard", (-5.0, -1.2), 0),

    # ---- raised beds: north block (near the house) then south block ----------------------
    ("kgarden_bed_herb", (-13.9, 5.19), 0),
    ("kgarden_bed_flower", (-4.1, 5.19), 0),
    ("kgarden_bed_leaf", (-13.9, 2.72), 0),
    ("kgarden_bed_brassica", (-4.1, 2.72), 0),
    ("kgarden_bed_brassica", (-13.9, -2.72), 0),
    ("kgarden_bed_leaf", (-4.1, -2.72), 0),
    ("kgarden_bed_beans", (-13.9, -5.19), 0),
    ("kgarden_bed_beans", (-4.1, -5.19), 0),

    # ---- potting shed at the end of the north walk ----------------------------------
    ("kgarden_shed", (12.6, 9.05), -90),

    # ---- north end of the cross walk: bench against the clipped yew hedge ---------------------
    ("kgarden_hedge", (-15.0, 16.9), 0),
    ("kgarden_hedge", (-9.0, 16.9), 0),
    ("kgarden_hedge", (-3.0, 16.9), 0),
    ("kgarden_bench", (-9.0, 16.25), 0),

    # ---- orchard ------------------------------------------------------------------------
    ("plant_tree_fruit", (-15.0, 12.5), 0),
    ("plant_tree_fruit", (-3.0, 12.8), 40),
    ("plant_tree_fruit", (-9.0, -12.5), 120),
]
