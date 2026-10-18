"""South lawn: a sculpture lawn south-west of the entry, between the motor court (east) and
the west garden (north-west). Zone-local metres, (0, 0) = centre of the rect (-66..-14,
-60..-25); +x east, +y north (towards the house terrace).

Composition
  * three sculptures staggered on a diagonal so none hides another from the entry
    (bearing from the north-east): the bronze ring (hero) nearest the entry, standing on the
    open lawn beyond the walk's east end, the torqued steel walls and the pierced stone stele
    inside the loop; the walk passes between the ring and the steel;
  * a gravel walk loops round them, with a spur up to the terrace edge and an apron at the
    bench;
  * a limestone seat wall on the south side retains a raised lawn carrying the grove, a dark
    backdrop (multi-stem trees and columnar cypress) in front of the hedge.
Everything but the walk is placed here; the walk is authored in these same coordinates."""

GZ = 0.55      # height of the raised lawn behind the seat wall

PLACEMENTS = [
    ("lawn_gravel_walk", (0, 0), 0),

    # sculptures: (x, y), rotation so the faces are shown to the entry and the library
    ("lawn_sculpture_ring", (20.5, 1.5), 150),
    ("lawn_sculpture_torque", (-1.5, -2.2), 12),
    ("lawn_sculpture_stele", (-11.0, 1.0), 118),

    # seat wall (rot 180: the seat faces north, the raised lawn runs south behind it);
    # its bench is at x = wall x + 0.6, where the walk's apron meets it
    ("lawn_seat_wall", (-12.0, -12.2), 180),

    # the grove on the raised lawn: two multi-stem trees, columnar cypress between and at the ends
    ("plant_tree_multistem", (-15.0, -14.9, GZ), 20),
    ("plant_tree_multistem", (-8.2, -15.2, GZ), 200),
    ("plant_tree_cypress", (-18.6, -15.8, GZ), 0),
    ("plant_tree_cypress", (-11.6, -16.2, GZ), 0),
    ("plant_tree_cypress", (-5.0, -15.6, GZ), 0),
]
