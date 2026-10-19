"""Courtyard (ground level, open to the sky): 20 x 14 m inside, glass on all four sides,
the only doorway on the south wall at x -1.5..1.5. Local coords: (0, 0) = centre,
+y north.

A garden room for eating outside: warm-grey sandstone flags; deep raised beds of layered
planting along the north, west and south glass (grasses, silver shrubs, ferns, boxwood,
jasmine trailing over the copings), a Japanese maple in the north bed on the doorway's axis
and another over the west end of the table; a long teak table for ten under festoon lights
strung on four black masts (three in the beds, one in a big terracotta pot), the strings
criss-crossing over the table; on the east, the lounge (sofa, armchairs, rug, stone table)
under an old olive; terracotta pot groups either side of the door.

Light: the level is set at golden hour with the sun low in the west, behind the galleries,
so the court sits in their shade; the festoon bulbs and the table candles are its warm
light (LIGHTS below are baked; the bulbs themselves are emissive)."""
import importlib


def _paving():
    import courtyard_common
    importlib.reload(courtyard_common)
    return courtyard_common.paving_mat()


FINISHES = dict(
    floor=_paving,
    floor_uv_tile=3.0,
)

# festoon masts: NW and SW in the west bed / north bed corner, NE in the north bed, SE in a pot
FESTOON_AT = (-3.75, 1.8)
FESTOON = dict(half=(5.55, 4.4), mast_h=3.7)          # must match courtyard_festoon.P
TABLE = (-3.75, 1.55)
LANTERNS = ((8.45, -0.72), (8.45, -4.12))          # candle lanterns at the sofa's ends

PLACEMENTS = [
    # raised beds round the glass (front faces into the court)
    ("courtyard_bed_north", (0.0, 6.35), 0),
    ("courtyard_bed_west", (-9.35, 0.0), 90),
    ("courtyard_bed_south", (-6.175, -6.35), 180),
    ("courtyard_bed_south", (6.175, -6.35), 180),
    # Japanese maples planted in the beds (z = the beds' soil)
    # (local +y, the side trained flat, faces the glass)
    ("courtyard_maple", (0.0, 6.40, 0.41), 0),
    ("courtyard_maple", (-9.30, 2.0, 0.41), 90),
    # the dining table for ten under the festoons, on a big jute rug
    ("courtyard_rug_dining", TABLE, 0),
    ("courtyard_dining_table", TABLE, 0),
    # festoon lights: four masts, strings along north and south and an X over the table
    ("courtyard_festoon", FESTOON_AT, 0),
    ("courtyard_pots_mast", (1.80, -2.60), 30),
    # the east lounge under the olive: rug, sofa facing west, two armchairs, a stone table
    ("courtyard_olive_tree", (7.0, 3.7), 137),
    ("courtyard_rug", (7.4, -2.4), 0),
    ("courtyard_sofa", (8.3, -2.4), -90),
    ("courtyard_coffee_table", (6.9, -2.4), 90),
    ("courtyard_armchair", (6.9, -0.8), 0),
    ("courtyard_armchair", (6.9, -4.0), 180),
    ("courtyard_lantern", LANTERNS[0], 10),
    ("courtyard_lantern", LANTERNS[1], -25),
    # a pot group in the middle of the court, between the table and the lounge
    ("courtyard_pots_corner", (0.9, 2.5), 200),
    # terracotta pot groups either side of the doorway
    ("courtyard_pots_door", (-2.05, -4.9), 0),
    ("courtyard_pots_door", (2.05, -4.9), 180),
]

# ten chairs: four a side (0.82 m apart) facing the table and one at each end, pulled out a
# little unevenly
for i, dx in enumerate((-1.23, -0.41, 0.41, 1.23)):
    for side, (dy, rot) in enumerate(((-0.70, 180), (0.70, 0))):
        jig = ((i * 7 + side * 3) % 5 - 2) * 0.012
        PLACEMENTS.append(("courtyard_dining_chair", (TABLE[0] + dx + jig, TABLE[1] + dy * (1 + 2 * abs(jig))),
                           rot + (i - 1.5) * (1 if side else -1) * 1.5))
PLACEMENTS.append(("courtyard_dining_chair", (TABLE[0] - 2.12, TABLE[1]), 90))
PLACEMENTS.append(("courtyard_dining_chair", (TABLE[0] + 2.14, TABLE[1] + 0.03), -88))


def _festoon_lights():
    """A few baked point lights along the strings (not one per bulb), warm 2200 K."""
    hx, hy = FESTOON["half"]
    cx, cy = FESTOON_AT
    z = FESTOON["mast_h"] - 0.10
    ms = [(cx - hx, cy - hy), (cx + hx, cy - hy), (cx - hx, cy + hy), (cx + hx, cy + hy)]
    out = []
    for (i, j, sag), ts in (((0, 1, 0.55), (0.3, 0.7)), ((2, 3, 0.55), (0.3, 0.7)),
                            ((0, 3, 0.85), (0.25, 0.5, 0.75)), ((1, 2, 0.85), (0.25, 0.75))):
        (ax, ay), (bx, by) = ms[i], ms[j]
        for t in ts:
            out.append(dict(kind="point", pos=(ax + (bx - ax) * t, ay + (by - ay) * t, z - 4 * sag * t * (1 - t) - 0.08),
                            power=15.0, color=(1.0, 0.70, 0.42)))
    return out


LIGHTS = _festoon_lights() + [
    # candle glow on the table and in the lanterns
    dict(kind="point", pos=(TABLE[0], TABLE[1], 0.98), power=4.0, color=(1.0, 0.62, 0.32)),
] + [dict(kind="point", pos=(x, y, 0.26), power=2.5, color=(1.0, 0.60, 0.30)) for x, y in LANTERNS]

PROBE = (0.0, 0.0, 1.6)
