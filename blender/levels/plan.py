"""Floor plan of the main house, as data (no Blender code here).

Coordinates are Blender metres: x east, y north, z up; the house is centred on the
origin. Rooms are axis-aligned rectangles (x0, y0, x1, y1) on a level; walls are
generated from them (blender/lib/house.py): every room lines its own side of each
wall with a 0.15 m lining, so two rooms back to back make a 0.3 m wall and each room
chooses its own finishes. Openings, windows and balustrades are cut through every
lining on their line, whichever rooms own them.

Future wings attach through the outer facades (x = ±26, y = ±20): add rooms outside
the main block and an opening on the facade line.
"""

T = 0.15                 # wall lining thickness, per room side
KB = 14.0 / 9.0          # the kitchen's glass wall (14 m) is nine window bays
LEVEL_Z = {0: 0.0, 1: 4.6}
HEIGHT = {0: 4.2, 1: 3.8}    # floor to ceiling
TOP = 8.4                # roof underside; double-height rooms go from 0 to here
SLAB = 0.2               # floor and ceiling box thickness

# name: rect, level, kind ("room" | "gallery" | "courtyard"), double (height 0..TOP),
# module (blender/levels/rooms/<module>.py dresses it; galleries share one)
ROOMS = {
    # ---- ground floor -------------------------------------------------------
    "entry":       dict(rect=(-8, -20, 8, -10.5), level=0, double=True),
    "powder":      dict(rect=(-13.5, -20, -8, -10.5), level=0),
    "cloak":       dict(rect=(8, -20, 13.5, -10.5), level=0),
    "den":         dict(rect=(-26, -20, -13.5, -10.5), level=0),
    "great_room":  dict(rect=(-26, -10.5, -13.5, 10.5), level=0, double=True),
    "dining":      dict(rect=(-26, 10.5, -10, 20), level=0),
    "kitchen":     dict(rect=(-10, 10.5, 8, 20), level=0),
    "scullery":    dict(rect=(8, 10.5, 13.5, 20), level=0),
    "wine_room":   dict(rect=(13.5, 10.5, 26, 20), level=0),
    "mudroom":     dict(rect=(13.5, 0, 26, 10.5), level=0),
    "garage":      dict(rect=(13.5, -20, 26, 0), level=0),
    "gallery_s":   dict(rect=(-13.5, -10.5, 13.5, -7), level=0, kind="gallery", module="galleries"),
    "gallery_n":   dict(rect=(-13.5, 7, 13.5, 10.5), level=0, kind="gallery", module="galleries"),
    "gallery_w":   dict(rect=(-13.5, -7, -10, 7), level=0, kind="gallery", module="galleries"),
    "gallery_e":   dict(rect=(10, -7, 13.5, 7), level=0, kind="gallery", module="galleries"),
    "courtyard":   dict(rect=(-10, -7, 10, 7), level=0, kind="courtyard"),
    # ---- upper floor ----------------------------------------------------------
    "library":         dict(rect=(-26, -20, -8, -10.5), level=1),
    "primary_bedroom": dict(rect=(-26, 10.5, -10, 20), level=1),
    "primary_bath":    dict(rect=(-10, 10.5, 0, 20), level=1),
    "office":          dict(rect=(0, 10.5, 13.5, 20), level=1),
    "gym":             dict(rect=(13.5, 10.5, 26, 20), level=1),
    "guest_room":      dict(rect=(13.5, 0, 26, 10.5), level=1),
    "ugallery_s":  dict(rect=(-13.5, -10.5, 13.5, -7), level=1, kind="gallery", module="galleries"),
    "ugallery_n":  dict(rect=(-13.5, 7, 13.5, 10.5), level=1, kind="gallery", module="galleries"),
    "ugallery_w":  dict(rect=(-13.5, -7, -10, 7), level=1, kind="gallery", module="galleries"),
    "ugallery_e":  dict(rect=(10, -7, 13.5, 7), level=1, kind="gallery", module="galleries"),
}

# room pairs whose shared boundary has no wall at all (the gallery ring's corners)
OPEN = [
    ("gallery_s", "gallery_w"), ("gallery_s", "gallery_e"), ("gallery_n", "gallery_w"), ("gallery_n", "gallery_e"),
    ("ugallery_s", "ugallery_w"), ("ugallery_s", "ugallery_e"), ("ugallery_n", "ugallery_w"), ("ugallery_n", "ugallery_e"),
]

# Cuts through the walls on a line. axis "x" = a wall running along x at y = line;
# axis "y" = a wall running along y at x = line. span = (a0, a1) along the wall;
# z = absolute (z0, z1).
#   opening:    a gap; with door=<asset> a door is placed in it, swinging into `swing`
#               (a room name); lock=<item id> locks it (needs that item, armed)
#   window:     floor-to-ceiling style glazing (frame, mullions, glass, one collider)
#   garage_door: a closed panel door
#   balustrade: open above floor level with a glass rail (overlooking a double-height room)
CUTS = [
    # ground floor: entry
    dict(kind="opening", axis="x", line=-10.5, span=(2.5, 7.0), z=(0, 3.6)),                 # entry -> gallery
    dict(kind="opening", axis="y", line=-8, span=(-18.05, -16.95), z=(0, 2.5), door="door_plain", swing="powder"),
    dict(kind="opening", axis="y", line=8, span=(-18.05, -16.95), z=(0, 2.5), door="door_plain", swing="cloak"),
    # 8.4 m glass front, with the front doors in its middle two bays (see "exterior doors" below)
    dict(kind="window", axis="x", line=-20, span=(-6, -1.5), z=(0, TOP)),
    dict(kind="window", axis="x", line=-20, span=(1.5, 6), z=(0, TOP)),
    # great room
    dict(kind="opening", axis="y", line=-13.5, span=(-5.5, -1.5), z=(0, 3.6)),               # -> west gallery
    dict(kind="opening", axis="y", line=-13.5, span=(1.5, 5.5), z=(0, 3.6)),
    dict(kind="opening", axis="x", line=-10.5, span=(-20.3, -19.2), z=(0, 2.5), door="door_plain", swing="den"),
    dict(kind="opening", axis="x", line=10.5, span=(-23, -17), z=(0, 3.6)),                  # -> dining
    dict(kind="window", axis="y", line=-26, span=(-8, 8), z=(0, TOP), breakable=(4, 7)),       # west glass wall (the Grimble smashes bays 4-7)
    # dining, kitchen, scullery, wine
    dict(kind="opening", axis="y", line=-10, span=(12.75, 17.75), z=(0, 3.6)),               # dining <-> kitchen
    dict(kind="opening", axis="x", line=10.5, span=(-13, -10.5), z=(0, 3.0)),                # dining -> gallery
    dict(kind="opening", axis="x", line=10.5, span=(-3, 3), z=(0, 3.6)),                     # kitchen -> gallery
    dict(kind="opening", axis="y", line=8, span=(14.25, 16.25), z=(0, 3.0)),                 # kitchen <-> scullery
    dict(kind="opening", axis="y", line=13.5, span=(16.45, 17.55), z=(0, 2.5), door="door_plain", swing="wine_room"),
    dict(kind="window", axis="x", line=20, span=(-24, -19.5), z=(0, 4.2)),                   # dining (doors in the middle)
    dict(kind="window", axis="x", line=20, span=(-16.5, -12), z=(0, 4.2)),
    dict(kind="window", axis="x", line=20, span=(-8, -8 + 4 * KB), z=(0, 4.2)),               # kitchen (a door in bay 5 of 9)
    dict(kind="window", axis="x", line=20, span=(-8 + 5 * KB, 6), z=(0, 4.2)),
    # mudroom, garage
    dict(kind="opening", axis="y", line=13.5, span=(2.95, 4.05), z=(0, 2.5), door="door_plain", swing="mudroom"),
    dict(kind="opening", axis="x", line=0, span=(19.2, 20.3), z=(0, 2.5), door="door_plain", swing="garage"),
    dict(kind="window", axis="y", line=26, span=(3, 7.5), z=(0.9, 3.3)),                     # mudroom
    dict(kind="garage_door", axis="x", line=-20, span=(15.5, 24), z=(0, 3.2)),
    # ---- exterior doors (going outside): glass doors in the glass walls open outward, on the
    # glass line (inset 0, no reveals: each door's own surround meets the mullions), 3 m high
    # with a transom over them; they keep the walls' 1.5 m bay rhythm (the blinds' bays too)
    # front doors, a pair on the entry's centre line, onto the motor court
    dict(kind="opening", axis="x", line=-20, span=(-1.5, 0.0), z=(0, 3.0), door="door_glass_r", swing="entry",
         swing_out=True, inset=0.0, reveal=False),
    dict(kind="opening", axis="x", line=-20, span=(0.0, 1.5), z=(0, 3.0), door="door_glass", swing="entry",
         swing_out=True, inset=0.0, reveal=False),
    dict(kind="window", axis="x", line=-20, span=(-1.5, 1.5), z=(3.0, TOP)),
    # dining room: a pair onto the north terrace, on the fire garden's axis (x = -18)
    dict(kind="opening", axis="x", line=20, span=(-19.5, -18.0), z=(0, 3.0), door="door_glass", swing="dining",
         swing_out=True, inset=0.0, reveal=False),
    dict(kind="opening", axis="x", line=20, span=(-18.0, -16.5), z=(0, 3.0), door="door_glass_r", swing="dining",
         swing_out=True, inset=0.0, reveal=False),
    dict(kind="window", axis="x", line=20, span=(-19.5, -16.5), z=(3.0, 4.2)),
    # kitchen: one door in the middle bay, onto the north terrace and the pool
    dict(kind="opening", axis="x", line=20, span=(-8 + 4 * KB, -8 + 5 * KB), z=(0, 3.0), door="door_glass_wide",
         swing="kitchen", swing_out=True, inset=0.0, reveal=False),
    dict(kind="window", axis="x", line=20, span=(-8 + 4 * KB, -8 + 5 * KB), z=(3.0, 4.2)),
    # mudroom: a side door in the east wall, north of the window seat (the tennis lawn, the
    # kitchen garden); an ordinary door, in the middle of the 0.15 m lining
    dict(kind="opening", axis="y", line=26, span=(8.35, 9.45), z=(0, 2.5), door="door_plain", swing="mudroom"),
    # courtyard: glass on all four sides, both floors; a doorway on the south side
    dict(kind="window", axis="x", line=-7, span=(-10, -1.5), z=(0, 4.2)),
    dict(kind="window", axis="x", line=-7, span=(1.5, 10), z=(0, 4.2)),
    dict(kind="opening", axis="x", line=-7, span=(-1.5, 1.5), z=(0, 3.0)),
    dict(kind="window", axis="x", line=7, span=(-10, 10), z=(0, 4.2)),
    dict(kind="window", axis="y", line=-10, span=(-7, 7), z=(0, 4.2)),
    dict(kind="window", axis="y", line=10, span=(-7, 7), z=(0, 4.2)),
    dict(kind="window", axis="x", line=-7, span=(-10, 10), z=(4.6, TOP)),
    dict(kind="window", axis="x", line=7, span=(-10, 10), z=(4.6, TOP)),
    dict(kind="window", axis="y", line=-10, span=(-7, 7), z=(4.6, TOP)),
    dict(kind="window", axis="y", line=10, span=(-7, 7), z=(4.6, TOP)),
    # upper floor: galleries overlooking the entry and great room; the stair arrives at x 1.5..4.5
    dict(kind="balustrade", axis="x", line=-10.5, span=(-8, 1.5), z=(4.6, TOP)),
    dict(kind="opening", axis="x", line=-10.5, span=(1.5, 4.5), z=(4.6, TOP)),               # stair landing (open to the roof: no block over the stair top)
    dict(kind="balustrade", axis="x", line=-10.5, span=(4.5, 8), z=(4.6, TOP)),
    dict(kind="balustrade", axis="y", line=-13.5, span=(-7, 7), z=(4.6, TOP)),
    dict(kind="window", axis="x", line=-10.5, span=(-25, -14.5), z=(4.6, TOP)),              # library -> great room
    dict(kind="window", axis="y", line=-26, span=(-19, -11.5), z=(4.6, TOP)),                # library west
    dict(kind="window", axis="x", line=-10.5, span=(8.5, 13), z=(4.6, TOP)),                 # gallery over cloak roof
    dict(kind="window", axis="y", line=13.5, span=(-6.5, -0.5), z=(4.6, TOP)),               # gallery over garage roof
    dict(kind="opening", axis="x", line=-10.5, span=(-11.3, -10.2), z=(4.6, 7.1), door="door_plain", swing="library"),
    dict(kind="opening", axis="x", line=10.5, span=(-12.3, -11.2), z=(4.6, 7.1), door="door", swing="ugallery_n",
         lock="keycard"),                                                                       # primary suite: keycard
    dict(kind="opening", axis="x", line=10.5, span=(6.2, 7.3), z=(4.6, 7.1), door="door_plain", swing="office",
         lock="key_office"),                                                                    # office: its key is in the guest room (caches.py)
    dict(kind="opening", axis="y", line=-10, span=(16.45, 17.55), z=(4.6, 7.1), door="door_plain", swing="primary_bath"),
    dict(kind="opening", axis="y", line=13.5, span=(16.45, 17.55), z=(4.6, 7.1), door="door_plain", swing="gym"),
    dict(kind="opening", axis="y", line=13.5, span=(2.95, 4.05), z=(4.6, 7.1), door="door_plain", swing="guest_room"),
    dict(kind="window", axis="x", line=20, span=(-24, -12), z=(4.6, TOP)),                   # primary bedroom
    dict(kind="window", axis="x", line=20, span=(1, 12.5), z=(4.6, TOP)),                    # office
    dict(kind="window", axis="x", line=20, span=(15, 24.5), z=(4.6, TOP)),                   # gym
    dict(kind="window", axis="y", line=26, span=(1.5, 9), z=(4.6, TOP)),                     # guest room
]

# floating stair in the entry, along its north wall, rising east to the upper gallery
STAIR = dict(room="entry", x=(-6.0, 1.5), y=(-13.05, -10.65), landing=(1.5, 4.5), risers=26)

SPAWN = dict(position=(0.0, -17.0), look=(0.0, 0.0, 1.5))   # in the entry, facing the courtyard

# Grounds around the main block, seen through the windows and walkable (ground_colliders.py:
# the exterior doors above lead out; the perimeter hedge bounds it). The lawn
# (z = 0 of every zone, 8 cm below the house floor) reaches past the perimeter hedge so the
# upper floor looks over it; a stone terrace rings the house; there is a gap in the hedge
# for the drive. Everything beyond the hedge is the horizon panorama (horizon.py).
# ZONES are dressed by blender/levels/outdoor/<zone>.py (like rooms): rect in plan metres,
# tris = triangle budget for everything the zone places (the whole estate shares ~70k).
GROUNDS = dict(
    lawn=(-90, -80, 90, 80),
    terrace=[(-31, -25, 31, -20), (-31, 20, 31, 25), (-31, -20, -26, 20), (26, -20, 31, 20)],
    hedge=dict(rect=(-70, -62, 70, 62), thick=1.4, height=2.8, gaps=[("s", 14.0, 25.5)]),
    zones={
        "pool_terrace":   dict(rect=(-8, 25, 24, 52), tris=7000),     # north, below kitchen / office / gym
        "pool_house":     dict(rect=(24, 25, 66, 58), tris=7000),     # north-east: cabana, outdoor kitchen
        "fire_garden":    dict(rect=(-48, 25, -8, 58), tris=5000),    # north-west, below dining / bedroom
        "west_garden":    dict(rect=(-66, -22, -31, 25), tris=6000),  # outside the great room's glass wall
        "motor_court":    dict(rect=(-14, -46, 30, -25), tris=6000),  # south: arrival court at the front
        "drive_gate":     dict(rect=(12, -66, 30, -46), tris=5000),   # the drive down to the gate in the hedge
        "south_lawn":     dict(rect=(-66, -60, -14, -25), tris=4000), # south-west: sculpture lawn
        "tennis":         dict(rect=(33, -22, 68, 25), tris=4000),    # east, below the guest room
        "kitchen_garden": dict(rect=(30, -60, 68, -25), tris=6000),   # south-east: greenhouse, beds, orchard
        "planting":       dict(rect=(-70, -62, 70, 62), tris=16000),  # trees + shrubs estate-wide (see brief)
    },
)
LAWN_Z = -0.08            # world z of the lawn surface = z 0 in every zone
