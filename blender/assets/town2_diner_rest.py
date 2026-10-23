"""The restrooms and the hall (town2_diner.py, in the annex), as a restoration fits them: two
single-occupancy rooms in white subway tile on the black-and-white checker floor, each with a
wall-hung toilet and its chrome flush valve, a wall-hung basin, a mirror, grab bars, a paper towel
dispenser, a waste bin; a fold-down changing table in the second. The swinging stainless door
between the car and the kitchen, propped open. The hall's coat hooks."""
import math

import lib.common as common
import town2_diner_geo as G


def build(k, M, p):
    A = p["annex"]
    fz = p["fz"]
    iy1 = A["iy1"]
    cy = A["corr_y"] + 0.15
    for (x0, x1), mirror_side in ((A["r1"], -1), (A["r2"], 1)):
        # toilet on the north wall, under the window, nearer the outer wall
        tx = x0 + 0.55 if mirror_side < 0 else x1 - 0.55
        toilet(k, M, p, tx, iy1)
        # grab bars: behind the toilet and on the near side wall
        k.add("Rest_Grab", G.tube([(tx - 0.45, iy1 - 0.05, fz + 0.85), (tx + 0.45, iy1 - 0.05, fz + 0.85)], 0.018, n=8), M["chrome"], tile=0.5, smooth=True)
        sw = x0 if mirror_side < 0 else x1
        k.add("Rest_Grab", G.tube([(sw - mirror_side * 0.05, iy1 - 1.2, fz + 0.85), (sw - mirror_side * 0.05, iy1 - 0.3, fz + 0.85)], 0.018, n=8), M["chrome"], tile=0.5, smooth=True)
        for yy in (iy1 - 1.2, iy1 - 0.3):
            k.add("Rest_GrabPost", G.box_lohi((min(sw, sw - mirror_side * 0.06), yy - 0.02, fz + 0.83), (max(sw, sw - mirror_side * 0.06), yy + 0.02, fz + 0.87)), M["chrome"], tile=0.5, lm=0.3)
        # the basin on the other side wall, its mirror, the towel dispenser, the bin
        bw = x1 if mirror_side < 0 else x0
        d = -1 if mirror_side < 0 else 1     # into the room from that wall
        by = cy + 1.0
        basin(k, M, p, bw, by, d)
        k.add("Rest_Mirror", G.box_lohi((min(bw, bw + d * 0.02), by - 0.3, fz + 1.05), (max(bw, bw + d * 0.02), by + 0.3, fz + 1.85)), M["chrome"], tint=(0.75, 0.78, 0.8), tile=0.5)
        k.add("Rest_MirrorFrame", G.box_lohi((min(bw, bw + d * 0.025), by - 0.32, fz + 1.03), (max(bw, bw + d * 0.025), by + 0.32, fz + 1.05)), M["steel"], tile=0.5, lm=0.3)
        k.add("Rest_Towels", G.box_lohi((min(bw, bw + d * 0.12), by + 0.5, fz + 1.2), (max(bw, bw + d * 0.12), by + 0.8, fz + 1.6), bevel=0.01), M["steel"], tile=0.5)
        k.add("Rest_Bin", G.box_lohi((min(bw, bw + d * 0.3), by + 0.5, fz), (max(bw, bw + d * 0.3), by + 0.8, fz + 0.65), bevel=0.01), M["steel"], tile=0.5)
        k.add("Rest_Paper", G.cyl((tx - mirror_side * 0.45, iy1 - 0.08, fz + 0.75), 0.07, 0.12, n=10, axis="x"), M["paint"], tint=(0.85, 0.84, 0.8), tile=1.0, lm=0.3)
        k.collider((tx - 0.22, iy1 - 0.65, fz), (tx + 0.22, iy1, fz + 0.42))
    # the second room's fold-down changing table on the corridor wall
    x0, x1 = A["r2"]
    k.add("Rest_Changer", G.box_lohi((x0 + 0.5, cy, fz + 0.9), (x0 + 1.4, cy + 0.12, fz + 1.45), bevel=0.02), M["paint"], tint=(0.6, 0.6, 0.58), tile=1.0)
    # hooks and a framed photograph in the hall
    hx0 = A["ix0"]
    for j in range(4):
        k.add("Hall_Hook", G.tube([(hx0 + 0.02, 6.0 + j * 0.25, fz + 1.65), (hx0 + 0.08, 6.0 + j * 0.25, fz + 1.62), (hx0 + 0.09, 6.0 + j * 0.25, fz + 1.68)], 0.008, n=6), M["chrome"], tile=0.5, lm=0.2)
    k.add("Hall_Jacket", G.box_lohi((hx0 + 0.04, 6.2, fz + 0.95), (hx0 + 0.2, 6.55, fz + 1.64), bevel=0.05, seg=2), M["paint"], tint=(0.08, 0.1, 0.12), tile=1.0, smooth=50)
    k.add("Hall_PhotoFrame", G.box_lohi((A["rest_x"] - 0.03, 5.8, fz + 1.35), (A["rest_x"], 6.4, fz + 1.8), bevel=0.006), M["wood"], tile=0.5, lm=0.4)
    k.add("Hall_Photo", G.decal((A["rest_x"] - 0.032, 6.35, fz + 1.39), (A["rest_x"] - 0.032, 5.85, fz + 1.39), (A["rest_x"] - 0.032, 5.85, fz + 1.76), (A["rest_x"] - 0.032, 6.35, fz + 1.76), "photo"),
          M["decal"], tile=None)

    # the kitchen door: stainless, a round window, hooked open against the kitchen side
    kx0, kx1 = p["kitchen_door"]
    yb = p["car"]["yb"]
    leaf_w = kx1 - kx0 - 0.02
    # hinge at kx1 (east jamb), swung 90 deg into the kitchen: the leaf stands along +y at
    # x = kx1, out of the way between the doorway and the reach-ins
    hx = kx1
    k.add("KDoor_Leaf", G.box_lohi((hx, yb + 0.02, fz + 0.02), (hx + 0.045, yb + 0.02 + leaf_w, fz + 2.06), bevel=0.006), M["steel"], tile=0.5)
    k.add("KDoor_Porthole", G.cyl((hx + 0.0225, yb + 0.02 + leaf_w / 2, fz + 1.55), 0.17, 0.05, n=20, axis="x"), M["chrome"], tile=0.5)
    k.add("KDoor_Glass", G.cyl((hx + 0.0225, yb + 0.02 + leaf_w / 2, fz + 1.55), 0.14, 0.052, n=20, axis="x"), M["glass"], tile=None)
    k.add("KDoor_Kick", G.box_lohi((hx - 0.005, yb + 0.05, fz + 0.03), (hx + 0.05, yb + leaf_w - 0.03, fz + 0.32)), M["chrome"], tile=0.5, lm=0.4)
    k.collider((hx - 0.005, yb, fz), (hx + 0.05, yb + 0.02 + leaf_w, fz + 2.06))


def toilet(k, M, p, x, yw):
    """A wall-hung vitreous china toilet with an open-front black seat and a chrome flush valve."""
    fz = p["fz"]
    bowl = G.lathe([(0.001, 0.0), (0.14, 0.0), (0.18, 0.1), (0.2, 0.25), (0.19, 0.36), (0.15, 0.37), (0.001, 0.3)], c=(0, 0, 0), n=16)
    G.xform(bowl, scale=(1.0, 1.35, 1.0))
    G.xform(bowl, loc=(x, yw - 0.33, fz + 0.03))
    k.add("Toilet_Bowl", bowl, M["paint"], tint=(0.82, 0.82, 0.8), tile=1.0, smooth=60)
    k.add("Toilet_Carrier", G.box_lohi((x - 0.17, yw - 0.18, fz + 0.15), (x + 0.17, yw, fz + 0.41), bevel=0.04, seg=2), M["paint"], tint=(0.82, 0.82, 0.8), tile=1.0, smooth=60)
    seat = G.lathe([(0.14, 0.0), (0.2, 0.0), (0.205, 0.02), (0.15, 0.025)], c=(0, 0, 0), n=16, angle=math.pi * 1.7)
    G.xform(seat, rz=-math.pi * 0.85 - math.pi / 2)
    G.xform(seat, scale=(1.0, 1.35, 1.0))
    G.xform(seat, loc=(x, yw - 0.33, fz + 0.41))
    k.add("Toilet_Seat", seat, M["paint"], tint=(0.03, 0.03, 0.03), tile=1.0, smooth=60)
    k.add("Toilet_Valve", G.tube([(x - 0.12, yw - 0.04, fz + 0.9), (x - 0.12, yw - 0.12, fz + 0.9), (x - 0.12, yw - 0.12, fz + 0.62), (x, yw - 0.12, fz + 0.55), (x, yw - 0.16, fz + 0.4)], 0.016, n=8), M["chrome"], tile=0.5, smooth=True)
    k.add("Toilet_ValveBody", G.cyl((x - 0.12, yw - 0.12, fz + 0.8), 0.035, 0.14, n=10), M["chrome"], tile=0.5, smooth=True)


def basin(k, M, p, xw, y, d):
    """A wall-hung basin on wall x = xw, facing into the room (d = +1: +x)."""
    fz = p["fz"]
    xa, xb = sorted((xw, xw + d * 0.48))
    k.add("Basin", G.box_lohi((xa, y - 0.25, fz + 0.72), (xb, y + 0.25, fz + 0.86), bevel=0.04, seg=2), M["paint"], tint=(0.82, 0.82, 0.8), tile=1.0, smooth=50)
    ba, bb = sorted((xw + d * 0.12, xw + d * 0.42))
    k.add("Basin_Bowl", G.box_lohi((ba, y - 0.18, fz + 0.861), (bb, y + 0.18, fz + 0.862)), M["paint"], tint=(0.6, 0.6, 0.58), tile=1.0, lm=0.3)
    k.add("Basin_Faucet", G.tube([(xw + d * 0.06, y, fz + 0.86), (xw + d * 0.06, y, fz + 1.0), (xw + d * 0.2, y, fz + 1.0), (xw + d * 0.2, y, fz + 0.95)], 0.012, n=8), M["chrome"], tile=0.5, smooth=True)
    k.add("Basin_Trap", G.tube([(xw + d * 0.25, y, fz + 0.72), (xw + d * 0.25, y, fz + 0.55), (xw + d * 0.02, y, fz + 0.55)], 0.018, n=8), M["chrome"], tile=0.5, smooth=True)
    k.add("Basin_Soap", G.box_lohi((min(xw, xw + d * 0.1), y + 0.3, fz + 1.05), (max(xw, xw + d * 0.1), y + 0.42, fz + 1.25), bevel=0.01), M["steel"], tile=0.5, lm=0.3)
    k.collider((xa, y - 0.25, fz + 0.5), (xb, y + 0.25, fz + 0.86))
