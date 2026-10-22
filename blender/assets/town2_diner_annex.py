"""The annex behind the car (town2_diner.py): the kitchen, the restroom hall and two restrooms,
the walk-in cooler, as relocated cars always get them (a cinder-block kitchen built on behind;
here a black board-and-batten box on the car's fieldstone, under a standing-seam shed roof that
tucks under the car's eave visor). The shell and its rooms' linings; the equipment is
town2_diner_kitchen.py."""
import math

import town2_diner_car as CAR
import town2_diner_geo as G


def build(k, M, p):
    A = p["annex"]
    fz = p["fz"]
    ax0, ax1, ay0, ay1 = A["x0"], A["x1"], A["y0"], A["y1"]
    t = 0.2
    ix0, ix1, iy1 = ax0 + t, ax1 - t, ay1 - t          # interior faces (iy0 = the car's back wall face, ay0)
    cz = fz + 2.45                                      # the ceiling
    zr0, zr1 = fz + 2.62, fz + 2.40                     # roof top at the car and at the north eave
    BLACK, CREAM = p["black"], p["cream"]
    W = dict(rest_x=-3.2, corr_y=7.0, r1=(-8.65, -6.0), r2=(-5.85, -3.2), line_y=7.95, line_x1=4.0,
             cooler=(5.0, 8.6, ix1, iy1), back_door=(1.2, 2.2), staff_door=(5.6, 6.5))
    A.update(ix0=ix0, ix1=ix1, iy1=iy1, cz=cz, **W)

    # ------------------------------------------------ outside: stone base, board-and-batten, trim
    zb = fz + 0.12
    base = [(ax0, ay0 + 0.05), (ax0, ay1), (ax1, ay1), (ax1, ay0 + 0.05)]
    k.add("Annex_Base", G.path_sweep(base, [(0.03, 0.0), (0.03, zb)]), M["stone"], tile=2.0)
    k.add("Annex_BaseCap", G.path_sweep(base, [(0.03, zb), (0.06, zb + 0.005), (0.06, zb + 0.04), (0.0, zb + 0.045)]), M["concrete"], tile=1.0)
    doors_n = [(W["back_door"][0], W["back_door"][1], zb, fz + 2.12)]
    wins_n = [(-7.9, -6.9, fz + 1.65, fz + 2.1), (-5.1, -4.1, fz + 1.65, fz + 2.1), (-1.9, -0.3, fz + 1.35, fz + 2.1)]
    # the north wall (outer skin + battens), the two ends
    def skin(ax, c0, c1, a0, a1, z0, z1, ops, name, roofz):
        for lo, hi in CAR.wall_boxes(ax, c0, c1, a0, a1, z0, z1, ops):
            k.add(name, G.box_lohi(lo, hi), M["paint"], tint=BLACK, tile=1.0, lm=0.8)
    skin("x", ay1 - 0.03, ay1, ax0, ax1, zb + 0.04, zr1 - 0.06, doors_n + wins_n, "Annex_Skin", zr1)
    # ends: a skin whose top follows the roof's slope (stepped in 4 pieces under the fascia)
    for xs in (ax0, ax1 - 0.03):
        n = 6
        for i in range(n):
            ya, yb = ay0 + (ay1 - ay0) * i / n, ay0 + (ay1 - ay0) * (i + 1) / n
            ztop = zr0 + (zr1 - zr0) * ((i + 1) / n) - 0.06
            k.add("Annex_Skin", G.box_lohi((xs, ya, zb + 0.04), (xs + 0.03, yb, ztop)), M["paint"], tint=BLACK, tile=1.0, lm=0.8)
    # battens every 0.4 m
    def battens_x(y, a0, a1, z0, z1, ops, out):
        nb = int((a1 - a0) / 0.4)
        for i in range(nb + 1):
            xb = a0 + 0.02 + i * (a1 - a0 - 0.04) / nb
            hole = [o for o in ops if o[0] - 0.05 < xb < o[1] + 0.05]
            segs = [(z0, z1)]
            for o in hole:
                segs = [s for seg in segs for s in ((seg[0], min(seg[1], o[2])), (max(seg[0], o[3]), seg[1])) if s[1] - s[0] > 0.05]
            for za, zz in segs:
                k.add("Annex_Batten", G.box_lohi((xb - 0.03, y, za), (xb + 0.03, y + out * 0.025, zz), bevel=0.004), M["paint"], tint=BLACK, tile=1.0, lm=0.4)
    battens_x(ay1, ax0, ax1, zb + 0.04, zr1 - 0.06, doors_n + wins_n, 1)
    for xs, out in ((ax0, -1), (ax1, 1)):
        nb = int((ay1 - ay0 - 0.2) / 0.4)
        for i in range(nb + 1):
            yb_ = ay0 + 0.2 + i * (ay1 - ay0 - 0.3) / nb
            ztop = zr0 + (zr1 - zr0) * ((yb_ - ay0) / (ay1 - ay0)) - 0.07
            k.add("Annex_Batten", G.box_lohi((xs, yb_ - 0.03, zb + 0.04), (xs + out * 0.025, yb_ + 0.03, ztop), bevel=0.004), M["paint"], tint=BLACK, tile=1.0, lm=0.4)
    # trims: window frames (black aluminium) with frosted / clear glass, the back door
    for x0w, x1w, z0w, z1w in wins_n:
        for lo, hi in (((x0w - 0.05, ay1 - 0.12, z0w - 0.05), (x1w + 0.05, ay1 + 0.04, z0w)), ((x0w - 0.05, ay1 - 0.12, z1w), (x1w + 0.05, ay1 + 0.04, z1w + 0.05)),
                       ((x0w - 0.05, ay1 - 0.12, z0w), (x0w, ay1 + 0.04, z1w)), ((x1w, ay1 - 0.12, z0w), (x1w + 0.05, ay1 + 0.04, z1w))):
            k.add("Annex_WinFrame", G.box_lohi(lo, hi), M["paint"], tint=BLACK, tile=1.0, lm=0.5)
        k.add("Annex_WinGlass", G.box_lohi((x0w, ay1 - 0.07, z0w), (x1w, ay1 - 0.06, z1w)), M["glass"], tile=None, bake=False)
        if x1w < -3:     # restrooms: frosted (an opal pane behind the glass)
            k.add("Annex_Frost", G.box_lohi((x0w, ay1 - 0.09, z0w), (x1w, ay1 - 0.085, z1w)), M["paint"], tint=(0.75, 0.76, 0.74), tile=1.0, lm=0.4)
    bx0, bx1 = W["back_door"]
    k.entrances.append(dict(name="kitchen_back", at=[round((bx0 + bx1) / 2, 3), ay1], facing=[0, 1], note="the staff door, ajar, three steps down to the yard"))
    for lo, hi in (((bx0 - 0.07, ay1 - 0.2, zb), (bx0, ay1 + 0.03, fz + 2.19)), ((bx1, ay1 - 0.2, zb), (bx1 + 0.07, ay1 + 0.03, fz + 2.19)),
                   ((bx0 - 0.07, ay1 - 0.2, fz + 2.12), (bx1 + 0.07, ay1 + 0.03, fz + 2.19))):
        k.add("Annex_DoorFrame", G.box_lohi(lo, hi), M["paint"], tint=BLACK, tile=1.0)
    # the back door: a steel door ajar 35 deg outward (the staff's smoke break), a kick plate
    hz = (bx0, ay1)
    ang = math.radians(100)       # (propped wide open on its closer arm: the staff go in and out)
    leaf = G.box_lohi((0, 0, fz + 0.005), (bx1 - bx0 - 0.02, 0.045, fz + 2.1), bevel=0.006)
    G.xform(leaf, loc=(bx0 + 0.01, ay1 + 0.0, 0), rz=ang)
    k.add("Annex_BackDoor", leaf, M["paint"], tint=(0.05, 0.05, 0.055), tile=1.0)
    plate = G.box_lohi((0.05, 0.045, fz + 0.03), (bx1 - bx0 - 0.07, 0.05, fz + 0.3))
    G.xform(plate, loc=(bx0 + 0.01, ay1, 0), rz=ang)
    k.add("Annex_BackDoorPlate", plate, M["steel"], tile=0.5)
    lever = G.box_lohi((bx1 - bx0 - 0.16, 0.05, fz + 1.0), (bx1 - bx0 - 0.04, 0.08, fz + 1.03), bevel=0.006)
    G.xform(lever, loc=(bx0 + 0.01, ay1, 0), rz=ang)
    k.add("Annex_BackDoorLever", lever, M["chrome"], tile=0.5)
    ex = (bx1 - bx0) * math.cos(ang)
    k.collider((bx0 + min(0.0, ex) - 0.05, ay1, fz), (bx0 + max(0.0, ex) + 0.06, ay1 + (bx1 - bx0) * math.sin(ang) + 0.05, fz + 2.1))
    # the stoop: three concrete risers down to the yard, a pipe rail
    sz = p["lot_z"]
    for top, ye in ((fz - 0.02, ay1 + 1.0), (sz + (fz - sz) * 2 / 3, ay1 + 1.32), (sz + (fz - sz) / 3, ay1 + 1.64)):
        k.add("Annex_Stoop", G.box_lohi((bx0 - 0.4, ay1, 0.0), (bx1 + 0.5, ye, top), bevel=0.01), M["concrete"], tile=1.0, lm=0.6, collide=True)
    # a caged wall light over the door
    k.add("Annex_LampBox", G.box_lohi(((bx0 + bx1) / 2 - 0.09, ay1, fz + 2.3), ((bx0 + bx1) / 2 + 0.09, ay1 + 0.1, fz + 2.42), bevel=0.01), M["paint"], tint=BLACK, tile=1.0)
    k.add("Annex_LampGlobe", G.cyl(((bx0 + bx1) / 2, ay1 + 0.1, fz + 2.3), 0.07, 0.12, n=12), M["globe"], tile=None, bake=False, smooth=True)
    k.light(kind="point", loc=((bx0 + bx1) / 2, ay1 + 0.16, fz + 2.26), power=25.0, color=(1.0, 0.8, 0.55), radius=0.04)

    # ------------------------------------------------ the roof: standing seam, fascia, gutter, kit
    ov = 0.25
    def rz(y):
        return zr0 + (zr1 - zr0) * (y - ay0) / (ay1 - ay0)
    ry0, ry1 = ay0 - 0.02, ay1 + ov
    rxa, rxb = ax0 - ov, ax1 + ov
    roof = G.quad((rxa, ry0, rz(ry0)), (rxb, ry0, rz(ry0)), (rxb, ry1, rz(ry1)), (rxa, ry1, rz(ry1)))
    roof = G.join(roof, G.quad((rxa, ry1, rz(ry1) - 0.18), (rxb, ry1, rz(ry1) - 0.18), (rxb, ry0, rz(ry0) - 0.18), (rxa, ry0, rz(ry0) - 0.18)))
    k.add("Annex_Roof", roof, M["paint"], tint=(0.035, 0.036, 0.04), tile=1.0, lm=0.5, zone="out")
    nseam = int((rxb - rxa) / 0.45)
    for i in range(1, nseam):
        xs = rxa + i * (rxb - rxa) / nseam
        seam = G.prism([(xs - 0.012, ry0), (xs + 0.012, ry0), (xs + 0.012, ry1), (xs - 0.012, ry1)], 0, 0.04)
        for v in seam.verts:
            v.co.z += rz(v.co.y)
        k.add("Annex_Seam", seam, M["paint"], tint=(0.045, 0.046, 0.05), tile=1.0, lm=0.25, zone="out")
    # fascia boards (ends + north) and the gutter with two downspouts
    for xs in (rxa, rxb - 0.04):
        fas = G.prism([(xs, ry0), (xs + 0.04, ry0), (xs + 0.04, ry1), (xs, ry1)], 0, 0.22)
        for v in fas.verts:
            v.co.z += rz(v.co.y) - 0.19
        k.add("Annex_Fascia", fas, M["paint"], tint=BLACK, tile=1.0, lm=0.5, zone="out")
    k.add("Annex_Fascia", G.box_lohi((rxa, ry1 - 0.04, rz(ry1) - 0.2), (rxb, ry1, rz(ry1) + 0.03)), M["paint"], tint=BLACK, tile=1.0, lm=0.5, zone="out")
    gut = [(0.0, 0.0), (0.12, 0.0), (0.14, 0.11), (0.125, 0.11), (0.11, 0.015), (0.015, 0.015), (0.015, 0.09), (0.0, 0.09)]
    k.add("Annex_Gutter", G.sweep([(ry1 + a, rz(ry1) - 0.16 + b) for a, b in gut], rxa, rxb, axis="x"), M["paint"], tint=BLACK, tile=1.0, lm=0.4, zone="out")
    for xs in (rxa + 0.35, rxb - 0.35):
        k.add("Annex_Downspout", G.box_lohi((xs - 0.04, ry1 + 0.03, 0.05), (xs + 0.04, ry1 + 0.11, rz(ry1) - 0.14)), M["paint"], tint=BLACK, tile=1.0, lm=0.4, zone="out")
        k.add("Annex_Splash", G.box_lohi((xs - 0.12, ry1, 0.0), (xs + 0.12, ry1 + 0.55, 0.06), bevel=0.01), M["concrete"], tile=1.0, lm=0.3, zone="out")
    # the flashing where the roof meets the car (a stainless counter-flashing under the visor)
    k.add("Annex_Flashing", G.box_lohi((ax0 - ov, ay0 - 0.04, zr0 - 0.02), (ax1 + ov, ay0 + 0.12, zr0 + 0.05)), M["steel"], tile=0.5, lm=0.4, zone="out")
    # the kitchen's exhaust fan over the hood, a make-up air unit, the cooler's condenser
    fx, fy = 0.5, 7.6
    k.add("Annex_FanCurb", G.box_lohi((fx - 0.45, fy - 0.45, rz(fy)), (fx + 0.45, fy + 0.45, rz(fy) + 0.4), bevel=0.02), M["steel"], tile=0.5, lm=0.5, zone="out")
    k.add("Annex_Fan", G.lathe([(0.001, 0.0), (0.42, 0.0), (0.5, 0.06), (0.5, 0.1), (0.3, 0.32), (0.08, 0.4), (0.001, 0.41)],
                              c=(fx, fy, rz(fy) + 0.4), n=20), M["steel"], tile=0.5, smooth=True, lm=0.5)
    k.add("Annex_FanBand", G.cyl((fx, fy, rz(fy) + 0.48), 0.4, 0.08, n=20, cap=False), M["paint"], tint=(0.1, 0.1, 0.11), tile=1.0, smooth=True, lm=0.4, zone="out")
    cx_, cy_ = 6.8, 9.9
    k.add("Annex_Condenser", G.box_lohi((cx_ - 0.55, cy_ - 0.4, rz(cy_) + 0.08), (cx_ + 0.55, cy_ + 0.4, rz(cy_) + 0.9), bevel=0.02), M["paint"], tint=(0.55, 0.56, 0.55), tile=1.0, lm=0.5, zone="out")
    k.add("Annex_CondFan", G.cyl((cx_, cy_, rz(cy_) + 0.91), 0.32, 0.02, n=20), M["paint"], tint=(0.06, 0.06, 0.06), tile=1.0, lm=0.3, zone="out")
    for dx in (-0.4, 0.4):
        k.add("Annex_CondRail", G.box_lohi((cx_ + dx - 0.04, cy_ - 0.45, rz(cy_)), (cx_ + dx + 0.04, cy_ + 0.45, rz(cy_) + 0.08)), M["steel"], tile=0.5, lm=0.3, zone="out")
    k.add("Annex_Pipe", G.tube([(cx_ - 0.55, cy_, rz(cy_) + 0.3), (cx_ - 1.4, cy_, rz(cy_) + 0.3), (cx_ - 1.4, cy_, rz(cy_) + 0.04)], 0.02, n=6), M["paint"], tint=BLACK, tile=1.0, lm=0.2, zone="out")

    # ------------------------------------------------ inside: floors, ceilings, linings
    # floor slab collider + finishes: hall (terrazzo, as the car), restrooms (checker), kitchen (quarry)
    k.collider((ax0, ay0, 0.0), (ax1, ay1, fz))
    rx = W["rest_x"]
    k.add("Annex_FloorHall", G.box_lohi((ix0, ay0, fz - 0.05), (rx, W["corr_y"], fz)), M["terrazzo"], tile=1.0)
    k.add("Annex_FloorRest", G.box_lohi((ix0, W["corr_y"], fz - 0.05), (rx, iy1, fz)), M["checker"], tile=0.6)
    k.add("Annex_FloorKitchen", G.box_lohi((rx, ay0, fz - 0.05), (ix1, iy1, fz)), M["quarry"], tile=0.6)
    k.add("Annex_Ceiling", G.box_lohi((ix0, ay0, cz), (ix1, iy1, cz + 0.03)), M["paint"], tint=(0.72, 0.72, 0.70), tile=1.0, lm=0.8)
    # exterior walls' inner linings (subway tile to 1.8 m, painted above), and the car's back face
    def lining(lo, hi, tile_top=fz + 1.8, all_tile=False):
        (x0_, y0_, z0_), (x1_, y1_, z1_) = lo, hi
        if all_tile or z1_ <= tile_top:
            k.add("Annex_Lining", G.box_lohi(lo, hi), M["subway"], tile=0.6)
        else:
            if z0_ < tile_top:
                k.add("Annex_Lining", G.box_lohi(lo, (x1_, y1_, tile_top)), M["subway"], tile=0.6)
            k.add("Annex_LiningPaint", G.box_lohi((x0_, y0_, max(z0_, tile_top)), hi), M["paint"], tint=(0.70, 0.70, 0.67), tile=1.0)
    # north wall (with the window and door openings), the east and west walls, the car's back face
    for lo, hi in CAR.wall_boxes("x", iy1, ay1 - 0.03, ix0, ix1, fz, cz, [(o[0], o[1], max(fz, o[2]), o[3]) for o in doors_n + wins_n]):
        lining(lo, hi)
    for lo, hi in CAR.wall_boxes("x", iy1, ay1, ax0, ax1, 0.0, cz, [(W["back_door"][0], W["back_door"][1], 0.0, fz + 2.12)]):
        k.collider(lo, hi)
    for xa, xb in ((ax0 + 0.03, ix0), (ix1, ax1 - 0.03)):
        lining((xa, ay0, fz), (xb, iy1, cz))
        k.collider((xa - 0.03, ay0, 0.0), (xb + 0.03, ay1, cz))
    C = p["car"]
    back_ops = [(p["rest_door"][0], p["rest_door"][1], fz - 0.01, fz + 2.12), (p["kitchen_door"][0], p["kitchen_door"][1], fz - 0.01, fz + 2.12),
                (p["pass"][0], p["pass"][1], p["pass_z"][0], p["pass_z"][1])]
    for lo, hi in CAR.wall_boxes("x", ay0, ay0 + 0.01, ix0, ix1, fz, cz, back_ops):
        lining(lo, hi)
    # window reveals inside (the wall's depth round each opening)
    for x0w, x1w, z0w, z1w in wins_n:
        k.add("Annex_Reveal", G.box_lohi((x0w, iy1 - 0.02, z0w - 0.02), (x1w, ay1 - 0.07, z0w)), M["steel"], tile=0.5)
    # ---- partitions: the restroom block, the corridor wall, the hood wall, the walk-in cooler
    cy = W["corr_y"]
    r1, r2 = W["r1"], W["r2"]
    d1, d2 = (-7.75, -6.75), (-5.2, -4.2)
    sd = W["staff_door"]
    parts = [
        ("x", cy, cy + 0.15, ix0, rx + 0.15, [(d1[0], d1[1], fz - 0.01, fz + 2.1), (d2[0], d2[1], fz - 0.01, fz + 2.1)], "both"),
        ("y", r1[1], r2[0], cy + 0.15, iy1, [], "tile"),
        ("y", rx, rx + 0.15, ay0, iy1, [(sd[0] - 0.0, sd[1], fz - 0.01, fz + 2.1)], "both"),
    ]
    for ax, c0, c1, a0, a1, ops, fin in parts:
        for lo, hi in CAR.wall_boxes(ax, c0, c1, a0, a1, fz, cz, ops):
            lining(lo, hi, all_tile=(fin == "tile"))
        for lo, hi in CAR.wall_boxes(ax, c0, c1, a0, a1, fz, cz, [(o[0], o[1], fz - 0.01, fz + 2.1) for o in ops]):
            k.collider(lo, hi)
    # interior door leaves, swung open (restrooms inward 75 deg, the staff door 80 deg)
    for (a0, a1), ang in ((d1, 92), (d2, 92)):
        leaf = G.box_lohi((0, -0.02, fz + 0.01), (a1 - a0 - 0.02, 0.02, fz + 2.08), bevel=0.005)
        G.xform(leaf, loc=(a0 + 0.01, cy + 0.15, 0), rz=math.radians(ang))
        k.add("Annex_Door", leaf, M["paint"], tint=(0.10, 0.20, 0.16), tile=1.0)
        kn = G.box_lohi((a1 - a0 - 0.1, 0.02, fz + 1.0), (a1 - a0 - 0.06, 0.07, fz + 1.04))
        G.xform(kn, loc=(a0 + 0.01, cy + 0.15, 0), rz=math.radians(ang))
        k.add("Annex_DoorLever", kn, M["chrome"], tile=0.5)
        e = a1 - a0
        k.collider((a0, cy + 0.15, fz), (a0 + e * math.cos(math.radians(ang)) + 0.04, cy + 0.15 + e * math.sin(math.radians(ang)) + 0.04, fz + 2.1))
        # a pictogram plaque beside the door (a figure: no lettering)
        k.add("Annex_Plaque", G.box_lohi((a1 + 0.08, cy - 0.012, fz + 1.45), (a1 + 0.26, cy, fz + 1.63), bevel=0.004), M["steel"], tile=0.5, lm=0.3)
        k.add("Annex_PlaqueFig", G.cyl((a1 + 0.17, cy - 0.014, fz + 1.59), 0.018, 0.004, n=10, axis="y"), M["paint"], tint=BLACK, tile=1.0, lm=0.2)
        k.add("Annex_PlaqueFig", G.box_lohi((a1 + 0.15, cy - 0.016, fz + 1.48), (a1 + 0.19, cy - 0.012, fz + 1.56)), M["paint"], tint=BLACK, tile=1.0, lm=0.2)
    # door frames (stainless) for the three interior doors
    for (a0, a1) in (d1, d2):
        for xa in (a0 - 0.05, a1):
            k.add("Annex_Casing", G.box_lohi((xa, cy - 0.015, fz), (xa + 0.05, cy + 0.165, fz + 2.15)), M["steel"], tile=0.5)
        k.add("Annex_Casing", G.box_lohi((a0 - 0.05, cy - 0.015, fz + 2.1), (a1 + 0.05, cy + 0.165, fz + 2.15)), M["steel"], tile=0.5)
    for ya in (sd[0] - 0.05, sd[1]):
        k.add("Annex_Casing", G.box_lohi((rx - 0.015, ya, fz), (rx + 0.165, ya + 0.05, fz + 2.15)), M["steel"], tile=0.5)
    k.add("Annex_Casing", G.box_lohi((rx - 0.015, sd[0] - 0.05, fz + 2.1), (rx + 0.165, sd[1] + 0.05, fz + 2.15)), M["steel"], tile=0.5)
    leaf = G.box_lohi((-0.02, 0, fz + 0.01), (0.02, sd[1] - sd[0] - 0.02, fz + 2.08), bevel=0.005)
    G.xform(leaf, loc=(rx + 0.15, sd[0] + 0.01, 0), rz=math.radians(-80))
    k.add("Annex_Door", leaf, M["paint"], tint=(0.10, 0.20, 0.16), tile=1.0)
    e = sd[1] - sd[0]
    k.collider((rx + 0.15, sd[0] + 0.01 - 0.04, fz), (rx + 0.15 + e * math.sin(math.radians(80)) + 0.04, sd[0] + 0.01 + e * math.cos(math.radians(80)), fz + 2.1))
    # the hood wall (behind the cook line): tile both sides
    for lo, hi in CAR.wall_boxes("x", W["line_y"], W["line_y"] + 0.15, rx + 0.15, W["line_x1"], fz, cz, []):
        lining(lo, hi, all_tile=True)
        k.collider(lo, hi)
    # the walk-in cooler: white insulated panels with a stainless kick, a door on its west face
    c0x, c0y, c1x, c1y = W["cooler"]
    ch = fz + 2.3
    cd = (9.25, 10.25)
    for lo, hi in ((((c0x, c0y, fz), (c1x, c0y + 0.1, ch))), ((c0x, c0y, fz), (c0x + 0.1, cd[0], ch)), ((c0x, cd[1], fz), (c0x + 0.1, c1y, ch)),
                   ((c0x, cd[0], fz + 2.08), (c0x + 0.1, cd[1], ch))):
        k.add("Cooler_Panel", G.box_lohi(lo, hi, bevel=0.01), M["paint"], tint=(0.74, 0.74, 0.72), tile=1.0)
        k.collider(lo, hi)
    k.add("Cooler_Top", G.box_lohi((c0x, c0y, ch), (c1x, c1y, ch + 0.08)), M["paint"], tint=(0.7, 0.7, 0.68), tile=1.0, lm=0.5)
    k.add("Cooler_Kick", G.box_lohi((c0x - 0.01, c0y - 0.01, fz), (c1x, c0y + 0.11, fz + 0.15)), M["steel"], tile=0.5)
    k.add("Cooler_Kick", G.box_lohi((c0x - 0.01, c0y, fz), (c0x + 0.11, c1y, fz + 0.15)), M["steel"], tile=0.5)
    # the door: closed, heavy hinges and the big latch, a strip curtain behind (seen ajar: no)
    k.add("Cooler_Door", G.box_lohi((c0x - 0.09, cd[0] + 0.02, fz + 0.02), (c0x - 0.0, cd[1] - 0.02, fz + 2.06), bevel=0.012), M["steel"], tile=0.5, collide=True)
    for zz in (fz + 0.35, fz + 1.75):
        k.add("Cooler_Hinge", G.box_lohi((c0x - 0.13, cd[1] - 0.12, zz), (c0x - 0.08, cd[1] + 0.02, zz + 0.16), bevel=0.01), M["chrome"], tile=0.5)
    k.add("Cooler_Latch", G.box_lohi((c0x - 0.16, cd[0] + 0.06, fz + 0.98), (c0x - 0.08, cd[0] + 0.3, fz + 1.12), bevel=0.012), M["chrome"], tile=0.5)
    k.add("Cooler_Latch", G.box_lohi((c0x - 0.11, cd[0] + 0.02, fz + 1.0), (c0x - 0.08, cd[0] + 0.1, fz + 1.1)), M["chrome"], tile=0.5)
    k.add("Cooler_Thermo", G.cyl((c0x - 0.005, cd[1] + 0.25, fz + 1.6), 0.05, 0.02, n=12, axis="x"), M["chrome"], tile=0.5)
    # (inside the cooler: closed, unlit, not modelled)

    # ceiling lights: 2x4 LED troffers in the kitchen, a disc in the hall and each restroom
    trof = [(-1.5, 6.55), (1.5, 6.55), (6.0, 6.6), (-1.5, 9.6), (2.5, 9.6)]
    for x_, y_ in trof:
        k.add("Annex_Troffer", G.box_lohi((x_ - 0.62, y_ - 0.31, cz - 0.03), (x_ + 0.62, y_ + 0.31, cz)), M["paint"], tint=(0.8, 0.8, 0.8), tile=1.0, lm=0.3)
        k.add("Annex_TrofferLens", G.box_lohi((x_ - 0.56, y_ - 0.25, cz - 0.035), (x_ + 0.56, y_ + 0.25, cz - 0.03)), M["globe_cool"], tile=None, bake=False)
        k.light(kind="area", loc=(x_, y_, cz - 0.05), size=(1.1, 0.5), power=120.0, color=(1.0, 0.95, 0.88), dir=(0, 0, -1))
    for x_, y_ in ((-6.0, 6.2), ((r1[0] + r1[1]) / 2, 9.4), ((r2[0] + r2[1]) / 2, 9.4)):
        k.add("Annex_Disc", G.cyl((x_, y_, cz - 0.02), 0.17, 0.04, n=16), M["globe"], tile=None, bake=False, smooth=True)
        k.light(kind="area", loc=(x_, y_, cz - 0.05), size=(0.3, 0.3), power=70.0, color=(1.0, 0.9, 0.78), dir=(0, 0, -1))
    return A
