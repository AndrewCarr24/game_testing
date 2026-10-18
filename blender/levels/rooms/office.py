"""Office (upper floor, north wing): 13.2 x 9.2 m inside, north wall glazed.
Local coords: (0, 0) = room centre; the window wall is y = +4.6, the gallery door
is on y = -4.6 at x = 0, the gym door on the east wall (x = +6.6) at y = +1.75."""

PLACEMENTS = [
    ("desk", (2.0, 2.4), 0),                 # sitter faces the room, back to the window
    ("desk_chair", (2.0, 3.4), 0),
    ("rug", (-3.4, -0.6), 0),
    ("coffee_table", (-3.4, -0.6), 90),
    ("lounge_chair", (-4.35, -0.6), 90),
    ("lounge_chair", (-2.45, -0.6), -90),
    ("vase", (-3.42, -0.38, 0.38), 0),       # on the coffee table
    # in the desk drawer (drawer-local): the keycard that opens the primary suite
    ("keycard", (0.09, -0.16, -0.0185), 18, {"attach": ("desk", "Desk_Drawer")}),

    # --- furnishing (added): west wall of books, credenza and art ---------------------------
    ("library_bookcase_o", (-6.42, -2.38), 90),
    ("library_credenza", (-6.35, 0.0), 90),
    ("library_bookcase_o", (-6.42, 2.38), 90),
    ("art_colorfield_a", (-6.6, -0.55, 1.75), 90),
    ("art_linework_a", (-6.6, 0.55, 1.75), 90),
    ("library_lamp", (-6.35, -0.85, 0.78), 90),
    ("library_lamp", (-6.35, 0.85, 0.78), 90),
    # second seating on the south wall: sofa, coffee table, armchair, rug
    ("rug", (4.1, -3.2), 0),
    ("library_sofa", (4.1, -4.1), 180),
    ("coffee_table", (4.1, -2.85), 0),
    ("library_armchair", (6.0, -2.85), -90),
    ("library_sidetable", (2.35, -4.2), 0),
    ("library_lamp", (2.35, -4.2, 0.56), 180),
    ("art_colorfield_b", (4.1, -4.6, 1.75), 180),
    # south wall, west of the door: credenza with art and a vase
    ("library_credenza", (-4.0, -4.35), 180),
    ("vase", (-4.9, -4.3, 0.78), 0),
    ("art_geometric_a", (-4.0, -4.6, 1.75), 180),
    # east wall art, plants
    ("art_geometric_b", (6.6, -0.8, 1.7), -90),
    ("library_plant", (1.65, -4.15), 0),
    ("library_plant", (-1.9, -4.15), 0),
    ("library_plant", (-4.4, 4.05), 0),
    ("library_plant", (4.6, 4.05), 0),
]

LIGHTS = [
    dict(kind="strip", pos=(-3.4, 0.0), size=(5.0, 0.08), power=90.0),
    dict(kind="strip", pos=(3.0, 1.0), size=(5.0, 0.08), power=90.0),
    dict(kind="strip", pos=(0.0, -3.2), size=(9.0, 0.08), power=70.0),
    dict(kind="strip", pos=(4.1, -3.4), size=(3.6, 0.08), power=60.0),               # over the sofa group
    dict(kind="point", pos=(-6.35, -0.85, 1.1), power=40.0, color=(1.0, 0.75, 0.48)),  # credenza lamps
    dict(kind="point", pos=(-6.35, 0.85, 1.1), power=40.0, color=(1.0, 0.75, 0.48)),
    dict(kind="point", pos=(2.35, -4.2, 0.88), power=35.0, color=(1.0, 0.75, 0.48)),   # sofa side lamp
]
