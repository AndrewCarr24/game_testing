"""Tennis court east of the house (zone rect x 33..68, y -22..25; (0, 0) = its centre,
world (50.5, 1.5)). The court runs north-south, seen side-on from the guest room and
mudroom windows: fence and net in front, the pavilion as the backdrop on the far (east)
side. Anything that stands on the court surface is placed at z = 0.05."""
Z = 0.05          # court surface above the lawn
GATE_Y = 4.04     # the gate bay's centre (y 2..6 m), level with the mudroom

PLACEMENTS = [
    ("tennis_court", (0, 0, 0), 0),
    ("tennis_fence", (0, 0, Z), 0),
    ("tennis_net", (0, 0, Z), 0),
    # umpire at the west net post, facing across the court
    ("tennis_umpire_chair", (-7.75, 0, Z), 90),
    # players' benches, east side by the net, facing the court
    ("tennis_bench", (7.7, -3.2, Z), -90),
    ("tennis_bench", (7.7, -5.4, Z), -90),
    # path from the terrace to the west gate
    ("tennis_path", (-14.325, GATE_Y, 0), 0),
    # floodlight masts outside the fence
    ("tennis_floodlight", (-10.7, -8.0, 0), 90),
    ("tennis_floodlight", (-10.7, 8.0, 0), 90),
    ("tennis_floodlight", (10.7, -8.0, 0), -90),
    ("tennis_floodlight", (10.7, 8.0, 0), -90),
    # pavilion behind the east fence, forecourt meeting the court edge at the east gate
    ("tennis_pavilion", (12.85, 2.0, 0), -90),
    ("tennis_bench", (13.62, 4.0, 0.15), -90),
    ("tennis_bench", (13.62, 2.05, 0.15), -90),
    # a pair of cypress flanking the pavilion
    ("plant_tree_cypress", (13.2, -2.5), 0),
    ("plant_tree_cypress", (13.2, 6.5), 0),
]
