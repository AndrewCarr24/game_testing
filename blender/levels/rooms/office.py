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
    ("art_cyanotype_fern", (-6.6, -0.4, 1.75), 90),      # cyanotype pair between the lamps
    ("art_cyanotype_umbel", (-6.6, 0.4, 1.75), 90),
    ("library_lamp", (-6.35, -0.85, 0.78), 90),
    ("library_lamp", (-6.35, 0.85, 0.78), 90),
    # second seating on the south wall: sofa, coffee table, armchair, rug
    ("rug", (4.1, -3.2), 0),
    ("library_sofa", (4.1, -4.1), 180),
    ("coffee_table", (4.1, -2.85), 0),
    ("library_armchair", (6.0, -2.85), -90),
    ("library_sidetable", (2.35, -4.2), 0),
    ("library_lamp", (2.35, -4.2, 0.56), 180),
    ("art_calligraphy", (4.1, -4.6, 1.6), 180),          # brush stroke on paper, box frame
    # south wall, west of the door: credenza with art and a vase
    ("library_credenza", (-4.0, -4.35), 180),
    ("vase", (-4.9, -4.3, 0.78), 0),
    ("art_salt_ponds", (-4.0, -4.6, 1.65), 180),         # aerial photograph over the credenza
    # east wall art, plants
    ("art_geometric_b", (6.6, -0.8, 1.7), -90),
    ("library_plant", (1.65, -4.15), 0),
    ("library_plant", (-1.9, -4.15), 0),
    ("library_plant", (-4.4, 4.05), 0),
    ("library_plant", (4.6, 4.05), 0),
]

# --- lighting --------------------------------------------------------------------------------
# Two bronze halo rings (light_u_halo) float over the two seating groups at 2.4 m, each a soft
# pool on its rug and a ring of uplight on the ceiling: the room's sculpture. Around them the
# walls carry the light: small downlights (light_u_downlight) graze the west book wall bay by
# bay and wash the art on the south and east walls; a banker's lamp on the desk, the credenza
# lamps and the sofa lamp add warm pools at hand height. Daylight does the rest through the
# north glass. No ceiling strips.
CEIL = 3.8
_WASH = [   # (downlight x, y), aim (x, y, z): the book bays, the credenza's two pictures, the art
    ((-5.74, -2.97), (-6.24, -2.97, 1.5)), ((-5.74, -1.79), (-6.24, -1.79, 1.5)),
    ((-5.74, 1.79), (-6.24, 1.79, 1.5)), ((-5.74, 2.97), (-6.24, 2.97, 1.5)),
    ((-5.85, 0.0), (-6.6, 0.0, 1.6)),                                  # credenza art pair
    ((-4.0, -3.8), (-4.0, -4.6, 1.5)), ((4.1, -3.8), (4.1, -4.6, 1.6)),  # south wall art
    ((5.8, -0.8), (6.6, -0.8, 1.5)),                                   # east wall art
]
PLACEMENTS += (
    [("light_u_downlight", (x, y, CEIL), 0) for (x, y), _ in _WASH]
    + [
        ("light_u_halo", (-3.4, -0.6, CEIL - 1.4), 0),        # over the lounge chairs, bottom at 2.4 m
        ("light_u_halo", (4.1, -3.05, CEIL - 1.4), 0),        # over the sofa group
        ("library_lamp", (1.3, 2.2, 0.74), 180),              # on the desk, facing the sitter
    ]
)


def _halo(x, y):
    # a ring-shaped source: four soft area lights round the ring (down onto the rug) and a
    # bulb at its centre for the uplight halo on the ceiling; one big square area light would
    # show as a square in the glossy floor
    out = [dict(kind="point", pos=(x, y, 2.46), power=140.0, color=(1.0, 0.84, 0.64))]
    for dx, dy, w, d in ((0.6, 0, 0.04, 0.7), (-0.6, 0, 0.04, 0.7), (0, 0.6, 0.7, 0.04), (0, -0.6, 0.7, 0.04)):
        out.append(dict(kind="area", pos=(x + dx, y + dy, 2.39), size=(w, d), aim=(x + dx, y + dy, 0.0), power=60.0,
                        color=(1.0, 0.82, 0.60)))
    return out


LIGHTS = (
    [dict(kind="spot", pos=(x, y, CEIL - 0.03), aim=aim, power=200.0, angle=55.0, blend=0.75, color=(1.0, 0.82, 0.62))
     for (x, y), aim in _WASH]
    + _halo(-3.4, -0.6) + _halo(4.1, -3.05)
    + [
        dict(kind="point", pos=(1.3, 2.2, 1.04), power=45.0, color=(1.0, 0.8, 0.5)),         # desk banker's lamp
        dict(kind="point", pos=(-6.35, -0.85, 1.08), power=50.0, color=(1.0, 0.75, 0.48)),   # credenza lamps
        dict(kind="point", pos=(-6.35, 0.85, 1.08), power=50.0, color=(1.0, 0.75, 0.48)),
        dict(kind="point", pos=(2.35, -4.2, 0.86), power=45.0, color=(1.0, 0.75, 0.48)),     # sofa side lamp
    ]
)
